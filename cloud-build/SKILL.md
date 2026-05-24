---
name: cloud-build
description: >-
  Discipline for Google Cloud Build CI/CD. Use when the repo contains
  `cloudbuild.yaml` / `cloudbuild.*.yaml` / `.gcloudignore`, when running
  `gcloud builds submit` or `gcloud builds triggers ...`, when authoring or
  debugging a Cloud Build pipeline, when wiring CB to Artifact Registry, Cloud
  Run, Cloud Run Jobs, GKE, or Firebase deploys, or when the user mentions
  cloudbuild, build triggers, build steps, substitutions, or build pools.
  Encodes the schema, the trigger surface, the user-SA + logging trap, secret
  manager wiring, DAG step ordering (waitFor), substitutions ($$ escaping +
  dynamic), and the scry-style gold-standard multi-stage pipeline.
---

# cloud-build

Discipline for working with Google Cloud Build CI/CD. The goal is to prevent the recurring traps: misordered `waitFor` DAGs, the user-service-account logging trap, secret references that silently expand to empty, triggers that don't fire because of branch/region mismatch, and pipelines that exceed the default 60-min timeout.

## Triggers

Load this skill when ANY of:
- Files present: `cloudbuild.yaml`, `cloudbuild.*.yaml`, `cloudbuild.*.json`, `.gcloudignore`, a `deploy/cloudbuild*` directory
- User mentions: cloud build, cloudbuild, gcloud builds, build trigger, build step, build pool, substitutions, secretEnv, BUILD_ID, SHORT_SHA, Cloud Run deploy from CB, Firebase deploy via CB, Artifact Registry push from CB
- A `gcloud builds` command is about to be run or has just failed

## Pre-Flight: discover the project's existing pipeline

Before writing new YAML, **read what already exists**. Repos in this environment usually have multiple cloudbuild files for distinct flows:

```
cloudbuild.yaml                    # main CI/CD on push to main
cloudbuild.validate.yaml           # PR / branch validation (no deploy)
cloudbuild.function-deploy.yaml    # parameterized per-function deploy
deploy/cloudbuild.yaml             # release pipeline (container build → push → Cloud Run)
```

A `cloudbuild.*.yaml` is the source of truth — don't infer the pipeline from CI scripts. Read it.

If the repo ships its own scripts (`scripts/run-ci-e2e-with-emulators.sh`, `scripts/check-firebase-deploy-prereqs.sh`, `scripts/provision-queues.sh`), the cloudbuild file will call them via `entrypoint: bash`. Don't reimplement what the scripts already encode.

## Decision Tree

```
What is the task?
│
├─ "Run a build now, locally"
│   → gcloud builds submit --config=cloudbuild.yaml --region=<region> . (§Recipes #1)
│
├─ "Build & push a Docker image, nothing else"
│   → gcloud builds submit --tag=LOCATION-docker.pkg.dev/PROJECT/REPO/IMG . (§Recipes #2)
│
├─ "Author a multi-step pipeline"
│   → §Recipes #3 (DAG with id/waitFor) + §Schema cheat sheet
│
├─ "Wire secrets into a step"
│   → §Recipes #4 (availableSecrets + secretEnv)
│
├─ "Deploy to Cloud Run / Functions / Firebase from CB"
│   → §Recipes #5 (impersonated cloud-sdk step)
│
├─ "Create a trigger on push / PR / tag"
│   → §Recipes #6 (gcloud builds triggers create github)
│
├─ "Build failed — what now?"
│   → §Troubleshooting (parse the error class first)
│
└─ "Move from default to user-specified service account"
    → §Pitfall P1 BEFORE editing anything else
```

---

## Schema cheat sheet (the parts that matter)

Top-level keys, in order of how often you touch them:

```yaml
steps: [ ... ]               # required; up to 300 steps
substitutions: { _KEY: val } # user-defined; must start with _, [A-Z0-9_]+
availableSecrets:            # preferred; integrates Secret Manager
  secretManager:
    - versionName: projects/PROJECT_ID/secrets/NAME/versions/latest
      env: VAR_NAME
options:
  logging: CLOUD_LOGGING_ONLY        # see Pitfall P1 — required with user SA
  machineType: E2_HIGHCPU_8          # default E2_STANDARD_2 (2 vCPU)
  diskSizeGb: 100                    # default 100, max 4000
  dynamicSubstitutions: true         # enable ${_VAR} expansion in substitutions
  substitutionOption: ALLOW_LOOSE    # tolerate undefined subs (auto for triggers)
  pool: { name: projects/P/locations/L/workerPools/POOL }   # private pool
timeout: '3600s'             # default 60m; raise BEFORE the build hits 1h
queueTtl: '3600s'            # default 1h queued wait
tags: [ ci, prod-deploy ]    # for filtering in `gcloud builds list`
images: [ gcr.io/P/img ]     # images CB should push on success
artifacts: { objects: { location: gs://..., paths: [...] } }
logsBucket: gs://my-logs     # ONLY if not using CLOUD_LOGGING_ONLY
serviceAccount: projects/P/serviceAccounts/SA@P.iam.gserviceaccount.com
```

Per-step fields:

```yaml
- name: node:22                  # required; builder image
  entrypoint: bash               # override; common for inline shell
  args: ['-c', '|', ...]         # OR `script:` (but not both)
  dir: functions                 # cwd within /workspace
  id: build-functions            # name this step (required for waitFor)
  waitFor: ['install-functions'] # DAG: only after these complete; ['-'] = run at start
  env: ['FOO=bar']               # plaintext env
  secretEnv: ['API_KEY']         # secret env (must appear in availableSecrets)
  timeout: '1200s'               # step-level timeout
  allowFailure: true             # don't fail the build if this step fails
  allowExitCodes: [0, 2]         # treat these as success
  volumes: [{ name: cache, path: /workspace/.cache }]
```

**`waitFor` rules**:
- Default (omitted): waits for all earlier steps to finish.
- `waitFor: ['-']`: runs immediately, in parallel with the first step (no deps).
- `waitFor: [id1, id2]`: runs after those step IDs complete successfully.
- Use `id:` everywhere if you want explicit DAG control — implicit ordering is footgun-prone.

## Default substitutions

Always available:
| Variable | Contains |
|---|---|
| `$PROJECT_ID` | Project ID |
| `$BUILD_ID` | This build's UUID |
| `$PROJECT_NUMBER` | Numeric project ID |
| `$LOCATION` | Build region |

**Trigger-only** (empty in `gcloud builds submit` runs without a connected repo):
| Variable | Contains |
|---|---|
| `$COMMIT_SHA` / `$REVISION_ID` | Full git SHA |
| `$SHORT_SHA` | First 7 chars of `$COMMIT_SHA` |
| `$BRANCH_NAME` / `$TAG_NAME` / `$REF_NAME` | Git ref |
| `$REPO_NAME` / `$REPO_FULL_NAME` | Repo identity |
| `$TRIGGER_NAME` | Name of invoking trigger |
| `$_HEAD_BRANCH` / `$_BASE_BRANCH` / `$_HEAD_REPO_URL` / `$_PR_NUMBER` | PR triggers only |

User subs: must match `_[A-Z0-9_]+`, max 200 per build. Override at submit time with `--substitutions=_KEY=val,_OTHER=val2`. `$PROJECT_ID` and `$BUILD_ID` cannot be overridden.

**Dollar-sign rules** (the #1 source of "why is my secret empty" confusion):
- `$_FOO` → substitution value (CB substitutes BEFORE the step runs)
- `$$_FOO` → literal `$_FOO` (escapes CB substitution; shell still sees `$_FOO`)
- `${_FOO}` → same as `$_FOO` but lets you concat: `${_FOO}BAR`
- **When using `secretEnv`, reference the secret as `$$VAR` in `args:` strings** so CB doesn't try to substitute it at config-parse time. In `entrypoint: bash` scripts the shell expansion takes over and `$VAR` works normally inside the script body.

---

## Real Command Surface

### Submit & inspect
| Command | Use it for |
|---|---|
| `gcloud builds submit --config=cloudbuild.yaml --region=<r> .` | Run the YAML against the current dir |
| `gcloud builds submit --tag=LOC-docker.pkg.dev/P/R/IMG .` | Dockerfile-only build & push |
| `gcloud builds submit --pack image=LOC.../IMG .` | Buildpacks build (no Dockerfile) |
| `gcloud builds submit --no-source --config=cloudbuild.yaml` | Sourceless build (no upload) |
| `gcloud builds submit ... --substitutions=_KEY=val,_OTHER=val2` | Override user subs |
| `gcloud builds submit ... --async` | Don't block on completion |
| `gcloud builds submit ... --service-account=projects/P/serviceAccounts/SA --default-buckets-behavior=REGIONAL_USER_OWNED_BUCKET` | Use a user SA |
| `gcloud builds list --region=<r> --ongoing --limit=10` | What's running right now |
| `gcloud builds describe <BUILD_ID> --region=<r>` | Full build record |
| `gcloud builds log <BUILD_ID> --region=<r>` | Print logs for a finished build |
| `gcloud builds log <BUILD_ID> --region=<r> --stream` | Tail logs of a running build |
| `gcloud builds cancel <BUILD_ID> --region=<r>` | Stop a running build |

**Always set `--region`** if the trigger or build is regional (default is `global`). Mismatched region is a top cause of "I don't see my build."

### Triggers
| Command | Use it for |
|---|---|
| `gcloud builds triggers create github --name=N --repo-owner=O --repo-name=R --branch-pattern='^main$' --build-config=cloudbuild.yaml --region=<r>` | Create push trigger on main |
| `... --tag-pattern='^v\d+\.\d+\.\d+$'` | Create tag-release trigger |
| `... --pull-request-pattern='^main$'` | Create PR trigger (GitHub App) |
| `... --service-account=projects/P/serviceAccounts/SA` | Bind a user SA (overrides config) |
| `... --require-approval` | Manual approval gate before execution |
| `... --included-files='src/**' --ignored-files='docs/**'` | Path filters |
| `... --substitutions=_ENV=prod` | Trigger-level substitution overrides |
| `gcloud builds triggers list --region=<r>` | List triggers |
| `gcloud builds triggers describe <T> --region=<r>` | Full trigger record |
| `gcloud builds triggers run <T> --branch=main --region=<r>` | Manually fire |
| `gcloud builds triggers export <T> --destination=trigger.yaml --region=<r>` | Round-trip to YAML |
| `gcloud builds triggers import --source=trigger.yaml --region=<r>` | Re-apply edited YAML |
| `gcloud builds triggers delete <T> --region=<r>` | Remove |

**Trigger gotcha**: when a trigger has its own `--service-account`, the `serviceAccount:` in the build config is ignored. Edit the trigger, not the YAML.

### Pools
| Command | Use it for |
|---|---|
| `gcloud builds worker-pools create POOL --region=<r> --peered-network=projects/P/global/networks/VPC` | Create private pool (VPC-attached) |
| `gcloud builds worker-pools describe POOL --region=<r>` | Pool details |

---

## Recipes

### 1. Run an existing pipeline locally
```bash
gcloud builds submit --config=cloudbuild.yaml --region=us-central1 .
# Override a sub:
gcloud builds submit --config=cloudbuild.yaml --region=us-central1 \
  --substitutions=_ENV=staging,_IMAGE_TAG=$(git rev-parse --short HEAD) .
```
Files are uploaded per `.gcloudignore` (auto-derived from `.gitignore` if missing). Add `.git/` and large fixtures explicitly if your tarball is huge.

### 2. Minimal Docker build & push (no YAML needed)
```bash
gcloud builds submit \
  --tag=us-central1-docker.pkg.dev/$PROJECT/my-repo/app:$(git rev-parse --short HEAD) \
  --region=us-central1 .
```
Cloud Build runs `docker build` against the local Dockerfile, pushes to Artifact Registry, and tags with the value you supplied. Use this for the simplest case; switch to a `cloudbuild.yaml` the moment you need a second step.

### 3. Multi-step pipeline with DAG ordering
```yaml
steps:
  - name: 'node:22'
    entrypoint: 'npm'
    args: ['ci']
    id: 'install'

  # These three run in parallel after install
  - name: 'node:22'
    entrypoint: 'npm'
    args: ['run', 'lint']
    id: 'lint'
    waitFor: ['install']

  - name: 'node:22'
    entrypoint: 'npm'
    args: ['run', 'test']
    id: 'test'
    waitFor: ['install']

  - name: 'node:22'
    entrypoint: 'npm'
    args: ['run', 'build']
    id: 'build'
    waitFor: ['install']

  # Fan-in: deploy only after all three pass
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        set -euo pipefail
        gcloud run deploy app --image=us-central1-docker.pkg.dev/$PROJECT_ID/repo/app:$SHORT_SHA --region=us-central1
    id: 'deploy'
    waitFor: ['lint', 'test', 'build']

options:
  logging: CLOUD_LOGGING_ONLY
timeout: '1800s'
```

**Discipline**: every step gets `id:` and explicit `waitFor:`. Implicit ordering bites the moment someone reorders steps in a PR.

### 4. Secret Manager wiring
```yaml
steps:
  - name: 'node:22'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        set -euo pipefail
        # In a bash script the shell expands env normally:
        echo "Building with API key: ${API_KEY:0:4}..." # don't actually log keys
        npm run build
    id: 'build'
    secretEnv: ['API_KEY']

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/MY_API_KEY/versions/latest
      env: 'API_KEY'
```
Required IAM: the *build service account* (default or user-specified) needs `roles/secretmanager.secretAccessor` on the secret (or project-wide). Without it, the secret silently resolves to empty and your step gets a blank string.

When passing a secret to a tool via `args:` *without* `entrypoint: bash`, escape with `$$`:
```yaml
- name: 'gcr.io/cloud-builders/docker'
  args: ['login', '-u', 'user', '-p', '$$DOCKER_PW']
  secretEnv: ['DOCKER_PW']
```

### 5. Deploy to Cloud Run (or Functions/Firebase) from a CB step
```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      set -euo pipefail
      gcloud run deploy my-service \
        --image="us-central1-docker.pkg.dev/${PROJECT_ID}/my-repo/app:${SHORT_SHA}" \
        --region=us-central1 \
        --service-account="runtime-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --quiet
  id: 'deploy-cloud-run'
  env:
    # Use this to delegate to a deploy SA *from within the step*:
    - 'CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT=deployer@${PROJECT_ID}.iam.gserviceaccount.com'
```
The build SA needs `roles/iam.serviceAccountTokenCreator` on the impersonated SA, and the impersonated SA needs the deploy roles (`roles/run.admin` + `roles/iam.serviceAccountUser` on the runtime SA).

For **Firebase deploys**, use a `node:22` step that runs `./node_modules/.bin/firebase deploy --project=PROJECT --only=<targets> --non-interactive --force`. The CB SA needs Firebase Admin and the same Service Account User role on the Functions runtime SA.

### 6. Create a push trigger on main
```bash
gcloud builds triggers create github \
  --name=ci-main \
  --region=us-central1 \
  --repo-owner=YourOrg --repo-name=YourRepo \
  --branch-pattern='^main$' \
  --build-config=cloudbuild.yaml \
  --service-account=projects/$PROJECT_ID/serviceAccounts/ci-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --included-files='src/**,cloudbuild.yaml' \
  --ignored-files='docs/**,**/*.md'
```
Then a PR-only validation trigger pointing to a thinner config:
```bash
gcloud builds triggers create github \
  --name=ci-pr-validate \
  --region=us-central1 \
  --repo-owner=YourOrg --repo-name=YourRepo \
  --pull-request-pattern='^main$' \
  --build-config=cloudbuild.validate.yaml \
  --comment-control=COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY
```
**Edit triggers via export/import**, not click-ops:
```bash
gcloud builds triggers export ci-main --destination=triggers/ci-main.yaml --region=us-central1
# edit triggers/ci-main.yaml
gcloud builds triggers import --source=triggers/ci-main.yaml --region=us-central1
```

### 7. Manual approval gate
Add `--require-approval` to the trigger. Approvers need `roles/cloudbuild.builds.approver`. The build sits in `PENDING` until an approver acts via console, `gcloud builds approve <BUILD_ID>`, or API.

### 8. Parameterized config (one YAML, many invocations)
```yaml
substitutions:
  _PROJECT_ID: 'my-project'
  _FUNCTION: ''   # required; caller supplies

steps:
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk:slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        set -euo pipefail
        if [[ -z "${_FUNCTION}" ]]; then
          echo "_FUNCTION substitution is required" >&2
          exit 1
        fi
        gcloud functions deploy "${_FUNCTION}" --project="${_PROJECT_ID}" ...
```
Caller: `gcloud builds submit --config=cloudbuild.function-deploy.yaml --substitutions=_FUNCTION=myFunc . --no-source` (use `--no-source` when the step doesn't need the repo).

---

## Anti-Patterns

### A1. Using a user-specified service account without setting `options.logging`
**Symptom**: Build dies immediately with `you must specify either logsBucket or set options.logging to CLOUD_LOGGING_ONLY`.
**Cause**: Default logging requires write access to the default logs bucket, which only the legacy CB SA has.
**Fix**: Add `options: { logging: CLOUD_LOGGING_ONLY }` (or specify your own `logsBucket: gs://...`). Grant `roles/logging.logWriter` to the user SA. See §Pitfall P1.

### A2. Reordering steps without checking `waitFor`
**Symptom**: A step suddenly fails because a dependency it implicitly relied on isn't done yet.
**Fix**: Always give every step an `id:` and an explicit `waitFor:`. If you intend "no dependency, run at start," use `waitFor: ['-']`. Treat implicit ordering as a code smell.

### A3. Referencing `$COMMIT_SHA` in a manually-submitted build
**Symptom**: Empty string substituted; image gets tagged `:` or `:latest` accidentally.
**Cause**: `$COMMIT_SHA` is only set for trigger-invoked builds. Manual `gcloud builds submit` leaves it empty.
**Fix**: Pass it explicitly: `--substitutions=COMMIT_SHA=$(git rev-parse HEAD),SHORT_SHA=$(git rev-parse --short HEAD)`. Or use `substitutionOption: ALLOW_LOOSE` and a sane default sub.

### A4. Forgetting `$$` when passing secrets through `args:`
**Symptom**: Secret value appears in build logs (logged before being injected) OR resolves to empty.
**Fix**: In raw `args:` strings, use `$$SECRET_NAME` so CB doesn't try to substitute it as a user variable. Inside `entrypoint: bash` scripts, the secret is in the runtime env — use normal `$SECRET_NAME`.

### A5. Timeouts: default is 60 minutes
**Symptom**: Build dies at exactly 1h with `TIMEOUT`.
**Fix**: Set `timeout: '3600s'` (1h, explicit), `'7200s'` (2h), or whatever you need. The hard ceiling is 24h. Don't discover this in production — set it from day one for any pipeline that includes container builds or e2e tests.

### A6. Building on the default machine and wondering why it's slow
**Symptom**: `npm ci` or `cargo build` takes 15+ min.
**Fix**: `options.machineType: E2_HIGHCPU_8` (or `E2_HIGHCPU_32` for heavy builds). Costs more per minute but usually finishes faster, and CB bills per minute on the machine size you chose.

### A7. Hand-clicking triggers in the console
**Symptom**: Trigger state is undocumented; nobody knows why it fires on `develop` instead of `main`; "what changed?" has no answer.
**Fix**: `gcloud builds triggers export` to YAML, commit it under `triggers/`, edit and `import`. Triggers belong in version control like everything else.

### A8. `cloudbuild.yaml` for "build & push image" when `--tag` would do
**Symptom**: 50-line YAML for what is literally `docker build && docker push`.
**Fix**: Use `gcloud builds submit --tag=...` until you actually need a second step. Don't add YAML preemptively.

### A9. Hard-coding `PROJECT_ID` instead of using `$PROJECT_ID`
**Symptom**: YAML can't be promoted between dev/staging/prod projects without editing.
**Fix**: Always use the default substitution `$PROJECT_ID`. For other project-specific knobs, use user subs (`_REGION`, `_ARTIFACT_REPO`) and pass per-environment via trigger substitutions.

### A10. Not understanding `dynamicSubstitutions`
**Symptom**: `_IMAGE_NAME: '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/...'` produces the literal string, not the expanded path.
**Fix**: Set `options.dynamicSubstitutions: true`. (It's `true` by default for trigger-invoked builds, `false` by default for `gcloud builds submit`.)

---

## Pitfall P1: User-specified service account (detailed)

This is the single biggest trap. Default SA → custom SA migration usually fails on first build.

**Required roles on the new build SA**:
- `roles/cloudbuild.builds.builder` — execute builds
- `roles/logging.logWriter` — required by `CLOUD_LOGGING_ONLY`
- `roles/storage.objectAdmin` — on the staging bucket (for source uploads)
- `roles/artifactregistry.writer` — to push images
- `roles/secretmanager.secretAccessor` — per secret (or project-wide) for `availableSecrets`
- `roles/iam.serviceAccountTokenCreator` — on any SAs you impersonate in steps

**Required in the YAML**:
```yaml
options:
  logging: CLOUD_LOGGING_ONLY    # OR set `logsBucket: gs://...`
serviceAccount: projects/${PROJECT_ID}/serviceAccounts/build-sa@${PROJECT_ID}.iam.gserviceaccount.com
```
If you specify the SA on a **trigger** instead, the SA in the YAML is ignored.

**Cross-project SAs**: org policy `iam.disableCrossProjectServiceAccountUsage` must be off, and the Cloud Build service agent needs `roles/iam.serviceAccountTokenCreator` on the foreign SA. The console doesn't support this — use `gcloud`.

---

## Troubleshooting

| Symptom | Diagnose | Fix |
|---|---|---|
| `you must specify either logsBucket or set options.logging` | Using a user SA without log config | Add `options.logging: CLOUD_LOGGING_ONLY`; grant `roles/logging.logWriter` |
| `PERMISSION_DENIED` on a `gcloud` call inside a step | Build SA missing the role | Identify which SA (build SA, not your user) and grant the role |
| `Permission denied while pushing to Artifact Registry` | Build SA missing `roles/artifactregistry.writer` | Grant it on the AR repo |
| `Token exchange failed for SA X` | Trying to impersonate without `roles/iam.serviceAccountTokenCreator` | Grant token-creator on the target SA to the build SA |
| Secret resolves to empty string | Secret accessor role missing OR variable referenced before injection | Verify `roles/secretmanager.secretAccessor`; use `$$VAR` in args |
| Step hangs forever | Default 60-min build timeout OR step lacks its own timeout | Set `timeout:` at build + per-step |
| `Build trigger could not be triggered` | Branch/tag pattern doesn't match the ref | Test pattern locally: `echo refs/heads/main \| grep -E '^refs/heads/main$'` |
| Trigger never fires on push | Wrong region OR wrong `--included-files` mask | `gcloud builds triggers describe T --region=<r>`; check `filter:`, `includedFiles:` |
| Build runs but nothing in the UI | Region mismatch — UI defaults to global, your build is regional | `gcloud builds list --region=us-central1 --limit=20` |
| OOM in a step | Default 4GB on `E2_STANDARD_2` | Bump `options.machineType` |
| `Forbidden by org policy: iam.allowedPolicyMemberDomains` | Cross-org SA usage blocked | Talk to org admin; consider keeping SAs in-project |
| Logs streaming hangs in `--stream` | Build is queued behind concurrent quota | `gcloud builds list --ongoing --region=<r>`; raise concurrent-build quota |
| `Step failed: exit code 137` | OOM killed the container | Bump machine type or refactor the step |

**First-line debugging recipe**:
```bash
# 1. Find the build
gcloud builds list --region=us-central1 --limit=5 --filter='status!=SUCCESS'

# 2. Read its full record
gcloud builds describe <BUILD_ID> --region=us-central1

# 3. Pull logs (don't go to the console first — log output is faster from CLI)
gcloud builds log <BUILD_ID> --region=us-central1 | tail -200
```

---

## House Style (observed in this user's repos)

These patterns recur across `scry/cloudbuild.yaml`, `cloudbuild.validate.yaml`, and `cloudbuild.function-deploy.yaml`. When in doubt, match this style:

1. **Every step has `id:` and explicit `waitFor:`**. No implicit DAG.
2. **Inline bash steps start with `set -euo pipefail`**. Always.
3. **`node:22` is the default builder image** for npm/Node work; **`gcr.io/google.com/cloudsdktool/cloud-sdk:slim`** is the default for steps that call `gcloud` / `gsutil` / `bq`.
4. **`options.logging: CLOUD_LOGGING_ONLY`** is set in every file.
5. **Pre-deploy gates use `CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT`** to delegate to a deploy SA — the build SA holds `roles/iam.serviceAccountTokenCreator` on the deploy SA.
6. **Long pipelines use `timeout: '3600s'`**; validation-only pipelines use `'1800s'`.
7. **Secrets are wired via `availableSecrets.secretManager`** with `versions/latest`, then pulled into the relevant steps with `secretEnv:`.
8. **Parameterized configs use `_PROJECT_ID` + `_FUNCTION`-style substitutions** and validate them at the top of the step body (`if [[ -z "${_FUNCTION}" ]]; then exit 1; fi`).
9. **`.gcloudignore` keeps `.git`, `.beads/`, and other developer chaff out** of the upload tarball.

---

## References

| File | When to open |
|---|---|
| [references/RECIPES.md](references/RECIPES.md) | Long-form recipes: Cloud Run + Cloud Run Jobs deploy, Terraform-gated approval pipelines, GitOps with trigger YAML, blue/green via revision tags |
| [references/PITFALLS.md](references/PITFALLS.md) | Deeper troubleshooting catalog with reproducers |

Official docs (always-fresh, prefer over recall):
- Schema: https://docs.cloud.google.com/build/docs/build-config-file-schema
- Substitutions: https://docs.cloud.google.com/build/docs/configuring-builds/substitute-variable-values
- Triggers: https://docs.cloud.google.com/build/docs/automating-builds/create-manage-triggers
- User SA setup: https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts
- Secret Manager: https://docs.cloud.google.com/build/docs/securing-builds/use-secrets
- Private pools: https://docs.cloud.google.com/build/docs/private-pools/private-pools-overview
- `gcloud builds` reference: https://docs.cloud.google.com/sdk/gcloud/reference/builds
