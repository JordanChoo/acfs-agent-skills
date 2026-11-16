---
name: gcloud
description: >-
  Operate Google Cloud and Firebase projects from this shared VPS without the mistakes agents
  repeat: deploying (push to main, then prove the commit is live), watching Cloud Build, Cloud
  Run and Cloud Functions, reading logs, Secret Manager, Cloud Tasks, Scheduler, Firestore,
  BigQuery (`bq`) and Firebase emulators. Use before any `gcloud`, `bq`, `gsutil` or `firebase`
  command; when asked to deploy, "check the build", "is it live", or debug production; and on
  errors like PERMISSION_DENIED, "Reauthentication failed", "You must specify a region",
  "unrecognized arguments", an empty `builds triggers list`, or a build that is green but not
  serving. For writing cloudbuild.yaml see cloud-build; for rules, indexes and emulator test
  harnesses see firebase-stack.
---

# gcloud

Built from about 2,700 gcloud, bq and firebase commands in 38 past sessions (philomena-agent and
scry, March to November 2026), owner rulings, and checks against gcloud 593. Every failure below
is replayed by `scripts/test_gcloud.py`. Evidence: [references/evidence.md](references/evidence.md).

## Facts about this machine

- **One gcloud config is shared by every agent and project.** Its active account and default
  project change when anyone runs `gcloud config set` or `gcloud auth activate-service-account`
  (both happened; for weeks a bare `gcloud` call ran as one project's service account inside the
  other project). **Never rely on the defaults; never change them.**
- Several accounts are credentialed: the owner's user account (the one in `gcloud auth list`
  that does not end in `gserviceaccount.com`) and per-project service accounts.
- Deploys are wired to git: **pushing `main` starts a Cloud Build trigger that deploys.**

## Find the project's facts first (once per session)

Get these from the repo, not from memory or the gcloud defaults, and pass them on every command:

| Fact | Where to find it |
| --- | --- |
| Project ID `P` | `.firebaserc`, the README's deploy section, `cloudbuild.yaml` |
| Region `R` | `_REGION` in `cloudbuild.yaml`, the README (Scheduler and Tasks call it `--location`) |
| Account `A` | the project docs; else `gcloud auth list --format='value(account)'` (no flags needed) and pick the project's deploy service account (its address contains the project ID) |
| Trigger and its account | `gcloud builds triggers list --region "$R" --project "$P" --account "$A" --format='table(name,github.push.branch,filename,serviceAccount)'`; if empty, try `--region=global` before concluding there is none |
| Service to verify `S` | the Cloud Run service the build deploys (README, `_SERVICE_NAME`) |

**Which account for reads:** the deploy service account first. Deploy accounts are
least-privilege, so some reads (logs, IAM policy, some secrets) fail; use the owner's account for
those reads when the project docs say so, otherwise ask the owner once per session. Writes as the
owner's account always need their approval (see Writes).

If the project's docs lack these facts, offer the owner a short "Google Cloud" block for its
AGENTS.md so the next agent does not rediscover them.

## The happy path: deploy and prove it is live

```bash
P=<project-id>; R=<region>; A=<account>; S=<cloud-run-service>   # one word per variable (zsh)
git pull --rebase && git push origin HEAD:main                     # 1. deploying IS pushing main
python3 ~/.claude/skills/gcloud/scripts/watch_deploy.py \
  --project "$P" --region "$R" --account "$A" --sha "$(git rev-parse HEAD)" --service "$S"
                                                                   # 2. one bounded watch (exit 0 = live)
curl -sS -m 20 https://<service-url>/health                        # 3. then one smoke call
```

(Codex: `~/.codex/skills/gcloud/scripts/watch_deploy.py`; the source is
`~/src/acfs-agent-skills/gcloud/scripts/watch_deploy.py`.) Other agents' pushed commits deploy
with yours: that is normal on a shared `main`. Follow the project's push rules (some mirror
`main:master`). The watcher finds the build for your commit, waits with a cap, prints `failureInfo`, the failed
step and the log tail on failure, and with `--service` checks that a revision **serving traffic**
carries your short SHA. Exit codes: 0 live, 1 build failed, 2 no build for the commit, 3 build
green but not serving, 4 still running, 5 gcloud error (expired login, permission, bad flag).
Run it in the background when your harness supports that. On exit 4, run the same command again
(it picks up the same build); if the owner is waiting, tell them "built, not yet live" rather than
"deployed". Projects that deploy only Cloud Functions omit `--service`; then also confirm no
later build of the same trigger finished after yours with an older commit:
`gcloud builds list --region "$R" --project "$P" --account "$A" --limit=5 --format='table(id,status,substitutions.SHORT_SHA,finishTime)'`.

Report: build ID, final status, serving revision. Before any change to traffic, note the revision
serving now so you can roll back.

## Rules

### Deploying
- **Deploy = commit + push `main` + watch.** The owner, repeatedly: "Always push to remote main
  since that is what triggers the deploy". Never `gcloud builds submit`, `gcloud run deploy`,
  `gcloud functions deploy`, `firebase deploy` (including rules and indexes) or a local docker
  push, unless the owner approves that named one-off in this session. Agents who did deployed
  uncommitted code, other agents' work, and settings the next push silently reverted.
- **`gcloud builds submit .` uploads the shared working tree**, other agents' uncommitted edits
  included. Never "fix" that with rsync copies into `/tmp` or private ignore files.
- **A green build is not proof, and `/health` is not proof.** Builds can finish out of order (one
  older build rolled production back for a day while every build showed SUCCESS), and a pipeline
  may skip its deploy when a newer build exists. Live means a revision with traffic carries your
  SHA: read `status.traffic`, not `latestReadyRevisionName` (traffic can be pinned elsewhere).
- **Exit 2 (no build)** usually means the push did not land, or you looked in the wrong region:
  triggers are regional, and `gcloud builds triggers list` without `--region` shows none (an agent
  told the owner no trigger existed). **Exit 1:** read the printed failed step and log; fix and push
  again. Do not resubmit by hand. When the pipeline deploys functions, a function's own source
  build can fail inside it: the trigger's log usually shows the error; otherwise the function's
  last build ID is `buildConfig.build` in `gcloud functions describe <fn> --region "$R" --project "$P" --account "$A" --format=json`.

### Identity on every command
- Pass `--project` and `--account` on every gcloud command (`--project_id` for `bq`), plus
  `--region` or `--location` where the command is regional. Alternatively prefix one command with
  `CLOUDSDK_CORE_PROJECT=... CLOUDSDK_CORE_ACCOUNT=...`; that changes nothing on disk.
- **Never run** `gcloud config set`, `gcloud auth activate-service-account`, `gcloud auth login`,
  or `gcloud auth application-default login` against the shared config, and never copy
  service-account keys out of `.env` files into `/tmp`. If the owner approves using a key, use a
  throwaway config: `CLOUDSDK_CONFIG=<scratchpad>/gcloud-cfg` for those commands only.
- **"Reauthentication failed" or "cannot prompt during non-interactive execution"**: the owner's
  login expired. Stop and ask the owner to run `gcloud auth login --no-launch-browser` in their own
  terminal on this host (the `!` prompt prefix cannot take the pasted code). Only user accounts
  expire this way; if the error names a service account, your `--account` is wrong. Meanwhile,
  reads that other accounts are allowed may continue. Do not hunt for other credentials, legacy
  credential files or keys. Never ask the owner to paste a credential or OAuth
  code into the chat; if they choose to, warn that it is now in the transcript.
- **PERMISSION_DENIED**: read which account the error names. If it is not the account you meant,
  your flags are missing. If it is, the account lacks the role: report it. Never grant yourself a
  role, change a trigger's service account, or switch to the owner's account without asking.
  Tell the owner which account lacks which permission and the options (grant that one role, or
  run the step another way); a trigger with its own service account also needs
  `options.logging: CLOUD_LOGGING_ONLY` (see cloud-build).
  Deploy service accounts are least-privilege by design (in one project they cannot read logs,
  IAM policy, Firestore backups, some secrets, or run `builds submit`).

### Reads are free, writes need the owner
- **Reads** (`list`, `describe`, `logging read`, `bq query` SELECT, `secrets versions list`):
  go ahead, with the identity flags.
- **Writes need explicit owner approval in this session, for that specific change**: IAM bindings,
  trigger edits, `run services update`/`update-traffic`, function deploys, Scheduler
  `pause`/`resume`/`run`, Tasks queue changes, `secrets create`/`versions add`, Firestore or
  BigQuery data writes (REST PATCH/commit, DML, `bq load`), index or rules deploys, and calls to
  your own production API that create work or spend money. A "go ahead" on a plan that named the
  exact change approves that change (and the `update-traffic` that completes it); it does not
  approve switching to the owner's account: ask for that separately.
- **Prefer the repo route:** a configuration change (env var, memory, secret mount) goes into the
  repo and ships by pushing `main`. Change the live service directly only when the owner wants it
  live before the next deploy, and then still put it in the repo.
- **Writing safely:** describe the resource first and save it; make the minimal change; describe
  again and compare; if the change is configuration (memory, env, secrets, service account), put
  it in the repo (cloudbuild.yaml, function config) in the same session, or the next deploy
  reverts it.
- **Never test a flag with a write** (an agent fired `run services update` at a made-up service
  to see if flags parsed). Use `--help`.
- **Cloud Run:** `services update` creates a revision that gets **0% traffic** when traffic is
  pinned. Follow it with
  `gcloud run services update-traffic "$S" --to-revisions=<rev>=100 --region "$R" --project "$P" --account "$A"`,
  then confirm with the watcher or `describe`. Roll back the same way to the revision you noted.
- Never act as an end user (minting custom tokens for a real user's UID), and never call paid
  endpoints or replay whole batches to "test": replay one record, with approval.

### Secrets
- Never print a secret: not with `echo`, not as `| head -c 20`, not by dumping a service's env
  (plaintext env values leak), not by grepping `.env` lines holding keys or service-account JSON.
- Use a value only inside a pipe or a variable in the same command:
  `TOKEN=$(gcloud secrets versions access latest --secret=NAME --project "$P" --account "$A")`.
  Keep `2>&1` out of that capture, or an error message becomes the "secret". Never write values to
  `/tmp` files. On this shared host, keep tokens out of command lines (`ps` shows them): send the
  header on stdin, `printf 'Authorization: Bearer %s\n' "$TOKEN" | curl -sS -H @- <url>`.
- To check a secret exists or matches, use `gcloud secrets versions list NAME`, or compare hashes
  (`printf %s "$TOKEN" | sha256sum | cut -c1-12`). Reading a `.env` value into a variable to hash
  it is fine (`L=$(sed -n 's/^NAME=//p' .env)`, strip surrounding quotes); printing the line is
  not. New values go in with
  `printf %s "$VALUE" | gcloud secrets versions add NAME --data-file=- ...` (a write: approval).

### Read errors honestly
- `2>&1 | head` and `| tail` hide gcloud's exit code: about a dozen "successful" commands were
  PERMISSION_DENIED or expired logins. Use `set -o pipefail`, or capture first and look for
  `ERROR: (` lines.
- **Empty output is unknown, not "nothing there"**: wrong region, wrong project, wrong log
  resource type, too short `--freshness`, or an error you filtered away.

## Reading recipes (all checked against gcloud 593)

```bash
# Builds for a commit, newest first; failure details; log
gcloud builds list --region "$R" --project "$P" --account "$A" --filter="substitutions.SHORT_SHA=$(git rev-parse --short=7 HEAD)" --format='table(id,status,createTime)' --limit=5
gcloud builds describe <BUILD_ID> --region "$R" --project "$P" --account "$A" --format='value(status,failureInfo.detail,statusDetail)'
gcloud builds log <BUILD_ID> --region "$R" --project "$P" --account "$A"

# Cloud Run: what is serving (traffic), revisions
gcloud run services describe "$S" --region "$R" --project "$P" --account "$A" --format='value(status.traffic)'
gcloud run revisions list --service "$S" --region "$R" --project "$P" --account "$A" --limit=5

# Logs: Cloud Run and gen2 functions (resource type cloud_run_revision, service = lowercase function name)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="<svc>" AND severity>=WARNING' --project "$P" --account "$A" --freshness=1h --order=desc --limit=50 --format=json

# Functions (gen2 functions are Cloud Run services), Tasks, Scheduler
gcloud functions describe <fn> --region "$R" --project "$P" --account "$A"
gcloud functions list --v2 --project "$P" --account "$A"
gcloud tasks queues describe <queue> --location "$R" --project "$P" --account "$A"
gcloud scheduler jobs describe <job> --location "$R" --project "$P" --account "$A"

# Firestore admin (there is no `gcloud firestore documents`; read documents with the project's admin scripts or the REST API)
gcloud firestore indexes composite list --project "$P" --account "$A"
gcloud firestore databases restore --source-backup=<backup-path> --destination-database=<new-db> --project "$P" --account "$A"
gcloud firestore databases clone --source-database=<db-path> --snapshot-time=<RFC3339> --destination-database=<new-db> --project "$P" --account "$A"

# BigQuery: standard SQL, pinned project and location, a byte cap, and a dry run before big scans
bq --project_id="$P" --location=US query --nouse_legacy_sql --dry_run 'SELECT ...'
bq --project_id="$P" --location=US query --nouse_legacy_sql --maximum_bytes_billed=1000000000 --format=prettyjson 'SELECT ... LIMIT 100'
```

The two `firestore databases` commands are writes (they create a database): approval first.
Logs: widen `--freshness` before concluding "no errors"; keep `--limit` modest (not 20000). A gen2
function's Cloud Run service name is usually its lowercased name; confirm it with
`gcloud functions describe <fn> --region "$R" --project "$P" --account "$A" --format='value(serviceConfig.service)'`.
`bq` has no `--account` flag: prefix the command with `CLOUDSDK_CORE_ACCOUNT=<account>`. Find a
dataset's location with `bq --project_id="$P" show --format=prettyjson <dataset>` (field
`location`) instead of assuming US. In `bq`, single-quote the SQL so the shell does not run backticked table names; DML and `bq load`
are writes, and need a `SELECT COUNT(*)` before and after.

## Flags agents guessed wrong

| Wrong | Right |
| --- | --- |
| `gcloud functions list --gen2` | `--v2` |
| `gcloud builds log --stream=never <id>` | `gcloud builds log <id>` (`--stream` takes no value) |
| `gcloud firestore documents ...` | no such group: admin script or REST |
| `firestore databases restore --backup=` | `--source-backup=` plus `--destination-database=` |
| `firestore databases clone --source-timestamp=` | `--source-database=` plus `--snapshot-time=` |
| `run services describe` without `--region` | add `--region` |
| `builds triggers list` without `--region` | add `--region` (it silently lists only global triggers) |
| `gcloud beta emulators firestore start` | `firebase emulators:start --only firestore` |

## Firebase emulators (shared host)

Other agents use the default ports (8080 and friends). Run your own copy:

1. Check Java (`java -version`, 21 on this host). Use the repo's CLI (`node_modules/.bin/firebase`)
   if present, else `firebase`.
2. Write a config in your scratchpad that moves every port off the defaults (Firestore, its
   websocket, the hub on 4400 and logging on 4500 all collide otherwise), with the UI off and the
   repo's rules:
   `{"firestore": {"rules": "<abs path>/firestore.rules"}, "emulators": {"firestore": {"host": "127.0.0.1", "port": <p1>, "websocketPort": <p2>}, "hub": {"host": "127.0.0.1", "port": <p3>}, "logging": {"host": "127.0.0.1", "port": <p4>}, "ui": {"enabled": false}}}`.
   Pick ports above 20000 and check each: `ss -ltn | grep -q ":<port> "` must find nothing.
3. Start it in the background with a `demo-` project ID (never a real one), logging to a file:
   `firebase emulators:start --only firestore --project demo-<repo>-<n> --config <cfg> > <log> 2>&1`.
4. Wait with a cap: poll the log for `All emulators ready`, fail on `Error:`, give up after 120 s.
5. `export FIRESTORE_EMULATOR_HOST=127.0.0.1:<port>` and run the tests.
6. Stop only your own process (its PID, or your harness's task stop), then check the port is free.
   **Never `pkill -f` emulators or java**: that kills other agents' runs. An emulator you did not
   start is someone else's: leave it, use other ports, and mention it to the owner if it looks
   abandoned.

For one-shot test runs, `firebase emulators:exec --only firestore --project demo-<id> --config <cfg> '<test cmd>'`
starts and stops it for you. Rules and index work: see firebase-stack.

## Self-test

`bash scripts/self-test.sh` runs `scripts/test_gcloud.py`: every wrong form above must fail in
gcloud's parser, every command in this file must parse, identity flags must work without touching
the shared config, the watcher must handle each deploy outcome (against a stub gcloud), and the
emulator recipe must start and stop cleanly. It runs gcloud only with an empty throwaway config,
so nothing reaches Google.
