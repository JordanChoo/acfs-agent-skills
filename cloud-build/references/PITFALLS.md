# cloud-build — Pitfalls Catalog

Deeper pitfall entries referenced by SKILL.md's troubleshooting table. Each entry: how to reproduce, why it happens, exact fix.

## P1. User SA without explicit logging config

**Repro**: take a working `cloudbuild.yaml` with the default SA, add `serviceAccount: projects/P/serviceAccounts/build-sa@P.iam.gserviceaccount.com`, submit.

**Error message**:
```
ERROR: (gcloud.builds.submit) INVALID_ARGUMENT: if 'build.service_account' is specified, the build must either (a) specify 'build.logs_bucket', (b) use the REGIONAL_USER_OWNED_BUCKET default_logs_bucket_behavior option, or (c) specify 'build.options.logging' as 'CLOUD_LOGGING_ONLY', 'NONE', or 'STACKDRIVER_ONLY'.
```

**Why**: The default logs bucket is owned by the legacy Cloud Build service agent; only it can write there. User SAs can't, and CB refuses to silently lose your logs.

**Fix**:
```yaml
options:
  logging: CLOUD_LOGGING_ONLY
```
And on the SA: `gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:build-sa@... --role=roles/logging.logWriter`.

## P2. `$SHORT_SHA` is empty in submitted (non-trigger) builds

**Repro**: `gcloud builds submit --config=cloudbuild.yaml .` where the YAML references `${SHORT_SHA}`. Image gets tagged `:` and pushed to a junk tag.

**Why**: `$COMMIT_SHA` / `$SHORT_SHA` are only injected for trigger-invoked builds. Manual `submit` doesn't auto-populate them.

**Fix**:
```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD),COMMIT_SHA=$(git rev-parse HEAD) .
```
Or set `substitutionOption: ALLOW_LOOSE` and accept empty defaults during manual runs.

## P3. Secret appears blank inside a step

**Repro**:
```yaml
- name: node:22
  entrypoint: bash
  args: ['-c', 'echo "key=$API_KEY"']
  secretEnv: ['API_KEY']
availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/MY_KEY/versions/latest
      env: API_KEY
```
`echo` prints `key=`.

**Possible causes**:
1. **Build SA missing `roles/secretmanager.secretAccessor`** on the secret (most common). Check with `gcloud secrets get-iam-policy MY_KEY`.
2. **Secret name typo** — CB doesn't 404 on a missing secret at parse time; the resolution fails silently.
3. **Wrong project** in the `versionName` — `projects/$PROJECT_ID/secrets/...` only works when the secret lives in the *build's* project.

**Fix**: grant the role, fix the name, or specify the full foreign project.

## P4. Secret leaks in build logs via `args:`

**Repro**:
```yaml
- name: gcr.io/cloud-builders/curl
  args: ['-H', 'Authorization: Bearer ${API_KEY}', 'https://api.example.com']
  secretEnv: ['API_KEY']
```
`args:` are logged as part of the step preamble — your secret ends up in Cloud Logging.

**Why**: CB logs the literal `args:` array as it appears in the resolved config; the secret value is substituted in by the time logging captures it.

**Fix**: use `$$API_KEY` to escape (CB won't substitute; it stays as the literal string `$API_KEY` in args, and the shell — if `entrypoint: bash` — expands it at runtime):
```yaml
- name: gcr.io/cloud-builders/curl
  entrypoint: bash
  args: ['-c', 'curl -H "Authorization: Bearer $API_KEY" https://api.example.com']
  secretEnv: ['API_KEY']
```

## P5. Trigger fires on wrong branches

**Repro**: `--branch-pattern='main'` (no anchors). Trigger fires on `release/main-fix`, `mainline`, etc.

**Why**: Patterns are full-regex matches without implicit anchors. `main` matches anywhere in the ref name.

**Fix**: `--branch-pattern='^main$'`. Always anchor patterns. Test with:
```bash
echo refs/heads/main | grep -E '^refs/heads/main$'
```

## P6. Trigger doesn't fire on push

**Symptoms**: Push to main happens, no build appears.

**Diagnose**:
```bash
gcloud builds triggers describe TRIGGER --region=REGION
```
Check:
1. **Region matches** where the build will run. A trigger in `us-central1` won't appear in the global UI listing.
2. **`includedFiles` / `ignoredFiles`** masks aren't excluding everything. `includedFiles: ['src/**']` plus a PR that only touched `docs/` will not fire.
3. **Repo connection is healthy**. `gcloud builds repositories list --connection=CONN --region=R` — connection state should be `OK`.
4. **Branch protection / webhook delivery**. In GitHub: Settings → Webhooks → look for the Cloud Build webhook; check recent deliveries for 4xx responses.

## P7. Build runs out of memory (exit code 137)

**Symptom**: A step dies with no clear error; `gcloud builds describe` shows `exit code 137` (SIGKILL).

**Why**: Default `E2_STANDARD_2` is 2 vCPU / 8GB RAM. Node `vue-tsc`, large webpack builds, and Playwright with multiple browsers regularly hit the ceiling.

**Fix**: `options.machineType: E2_HIGHCPU_8` (8 vCPU / 8GB) or `E2_STANDARD_4` (4 vCPU / 16GB). The `E2_HIGHCPU_*` family is CPU-rich but RAM-equal to STANDARD_2; for memory-bound steps, prefer `STANDARD_4`/`STANDARD_8` (when available in your region).

## P8. Build hits 60-minute timeout

**Symptom**: Build status `TIMEOUT` at exactly 1h.

**Why**: Default `timeout` is `'3600s'` (60m). It's not the trigger's fault — it's a build-level field.

**Fix**: Set explicitly at the top of the YAML. Don't go higher than you need (you pay for the queued slot):
```yaml
timeout: '7200s'   # 2h
```

## P9. Can't `gcloud run deploy` from a step

**Common causes**:
1. **Wrong image** in the step. Use `gcr.io/google.com/cloudsdktool/cloud-sdk:slim` (not `cloud-builders/gcloud` — deprecated, missing newer subcommands).
2. **Build SA missing `roles/run.admin`** or the runtime-SA `roles/iam.serviceAccountUser`. Cloud Run deploy requires both.
3. **Region mismatch** between the deploy command and the existing service. `gcloud run deploy NAME --region=R` must match.

## P10. `gcloud builds list` shows nothing

**Probably**: you're querying global, but your builds are regional. `--region=us-central1` (or whichever).

```bash
gcloud builds list --region=us-central1 --limit=10
# Or scan everywhere:
for R in us-central1 us-east1 europe-west1; do
  echo "=== $R ===" ; gcloud builds list --region=$R --limit=3
done
```

## P11. `.gcloudignore` not respected

**Symptom**: Build uploads `node_modules/` despite `.gcloudignore` listing it.

**Why**: When both `.gitignore` and `.gcloudignore` exist, only `.gcloudignore` is consulted. If `.gcloudignore` is brand-new and doesn't mention `node_modules`, the upload includes it.

**Fix**: ensure `.gcloudignore` includes `.gitignore` semantics by adding `#!include:.gitignore` near the top. Recommended baseline:
```
.gcloudignore
.git
.gitignore
#!include:.gitignore
```

## P12. Dynamic substitutions silently disabled

**Repro**:
```yaml
substitutions:
  _IMAGE: '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/r/img'
```
Submitted manually. Build fails with image name literally containing `${_LOCATION}`.

**Why**: `dynamicSubstitutions` is `false` by default for manual submits and `true` for trigger-invoked builds.

**Fix**:
```yaml
options:
  dynamicSubstitutions: true
```

## P13. Trigger's `--substitutions` shadows YAML defaults

**Repro**: YAML has `substitutions: { _ENV: dev }`. Trigger has `--substitutions=_ENV=prod`. You change the YAML default to `staging`. Builds still come out `prod`.

**Why**: Trigger-level subs always win. The YAML default is only used when nothing else sets it.

**Fix**: Trigger subs are authoritative for trigger-invoked builds. Either remove the trigger sub, set it via `gcloud builds triggers describe` + `--substitutions=...` on the trigger, or accept that the YAML default is only for manual runs.

## P14. "Build trigger already exists" when re-importing

**Repro**: `gcloud builds triggers import --source=trigger.yaml` fails because the trigger already exists.

**Fix**: Imports are create-only. To update an existing trigger:
```bash
gcloud builds triggers describe NAME --region=R --format=yaml > current.yaml
# edit current.yaml
# Note: the YAML format from describe is import-compatible
gcloud builds triggers delete NAME --region=R --quiet
gcloud builds triggers import --source=current.yaml --region=R
```
For zero-downtime updates, prefer the targeted flag form (`gcloud builds triggers update github NAME --branch-pattern='^prod$'`).

## P15. Build pushes image but `images:` field returned empty

**Symptom**: Build succeeds, image is in Artifact Registry, but `gcloud builds describe` shows `images: []`. Provenance/attestation features misbehave.

**Why**: Only images listed in the top-level `images:` field are recorded in the build record. If you only do `docker push` inside a step, CB doesn't know about it.

**Fix**: list the pushed images explicitly:
```yaml
images:
  - 'us-central1-docker.pkg.dev/${PROJECT_ID}/repo/app:${SHORT_SHA}'
  - 'us-central1-docker.pkg.dev/${PROJECT_ID}/repo/app:latest'
```
CB will push these for you at the end of the build (or verify they exist if a step already pushed them).
