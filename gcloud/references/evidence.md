# gcloud in past sessions: evidence

Source: every `gcloud`, `bq`, `gsutil` and `firebase` command in Claude Code and Codex session
logs on this VPS (extracted 2026-11-16 with its output): 2,716 commands in 38 sessions, March to
November 2026, almost all in two projects (scry: Cloud Functions gen2, Cloud Tasks, BigQuery;
philomena-agent: Cloud Run). Three readers then went through the sessions in context, with the
owner's messages. `co:` is a Codex session (`~/.codex/sessions/2026/MM/DD/rollout-<stem>`),
`cl:` a Claude Code session id prefix. Project IDs and account emails are left out on purpose:
this repository is public.

None of the existing Google Cloud skills (cloud-build, firebase-stack, firebase-basics,
firebase-emulator-e2e-harness) was ever loaded in any logged session.

## Owner rulings (verbatim)

| Ruling | Where |
| --- | --- |
| "Deployment is done via GH main -> Could Build" | co:03-13T19-59-50, 03-14 11:21 |
| "whenever i push to main it pushed to deploy so i know the code is deployed" | co:03-14T22-50-23 |
| "Always push to remote main since that is what triggers the deploy via the GCLoud CI Build" (after two deploys of uncommitted code) | co:04-04T02-00-00, 17:40 |
| "Isn't this deployed when pushed to remote main?" (rejecting a local docker push after a failed `builds submit`) | cl:9d9f4ee7, 10-29 12:45 |
| One-off repairs approved by name: "Do a one off prod repair", "do the one off refresh manual way" | co:05-12, co:04-27 |
| "Why do we need to update these permissions? ... Change it back to the original service account then" | co:03-25T01-35-57, 18:09 |

## Failures and how often

| Problem | Count | Examples |
| --- | ---: | --- |
| Shared global config changed (`auth activate-service-account`, `config set project`); bare calls then ran as another project's service account | 17 changes; 17 bare calls as the wrong account | co:04-09, co:03-14; cl:9d9f 10-29 12:42 |
| Expired owner login ("Reauthentication failed ... cannot prompt during non-interactive execution"), then credential hunting (key files to `/tmp`, legacy credential files, impersonation) | 19 of 20 scry Codex sessions; 3 philomena | co:04-04 00:09-00:40; cl:d72a5f4c 09-23 11:49 |
| PERMISSION_DENIED as a least-privilege deploy account (logs, IAM policy, backups, secrets, `builds submit`) | 26 | cl:9d9f, cl:4b05 |
| Writes made before or without approval: IAM grants, trigger service-account switches (3x in one session), `allUsers` invoker, 28 direct function deploys, BigQuery DELETE + load, 78 Firestore REST writes | about 20 sessions | co:03-28T19-14-15 19:43; co:03-25T01-35-57; co:04-27 17:25 |
| Owner's account used for writes without asking | 3 | cl:822561a0 09-24 06:38; cl:4b05 11-15 16:24 |
| `firebase deploy` / `builds submit` from the shared tree or rsync'd `/tmp` copies | 17 firebase deploys, 8 submits | co:04-01, co:04-04 |
| Hand-written polling loops (30 uncapped `until` loops) | 131 | cl:9d9f 10-29; co:05-12 (579 leaked exec warnings) |
| Green build read as "deployed"; older build ran last and rolled production back for a day | 1 incident, 48 reads of the wrong field | cl:9d9f 10-31 to 11-01 |
| Build FAILURE seen but `builds log` never read | 9 | cl:9d9f |
| `builds triggers list` without `--region` (regional trigger invisible; agent said none existed) | 15 of 35 | co:04-04 01:12 |
| Guessed flags: `--gen2`, `--stream=never`, `firestore documents`, `restore --backup`, `clone --source-timestamp`, missing `--region` | about 15 | see the flag table |
| A write used to test flags (`run services update` on a made-up service) | 1 | cl:9d9f 11-02 00:47 |
| Secrets printed or stored: `| head -c 20`, values in `/tmp` files, service env dump with plaintext values, `.env` grep showing key JSON | 14 commands, 6 sessions | co:03-25, co:05-15, cl:822561a0 06:36 |
| Pipes hiding failures (rc 0 on PERMISSION_DENIED or reauth) | about 12 | cl:9d9f; cl:59faaf30 |
| `logging read` without `resource.type`, freshness or order; `cloud_function` instead of `cloud_run_revision` for gen2 | 69 / 482 / 454 of 582 | co:04-04 00:10 |
| `bq query` without standard SQL flag; no byte cap ever | 65 of 155; 0 | co:05-15 02:00 (backticks run by the shell) |
| `pkill -f` of every emulator on the host | 1 | cl:9d9f 10-29 12:42 |

## Workarounds made official

- Explicit identity on every command (`--project`, `--account`; or a one-command
  `CLOUDSDK_CORE_*` prefix): philomena-agent sessions did this on about 450 commands and avoided
  every wrong-account error after adopting it.
- Proving live by the serving revision's SHA (cl:4b05 11-15 15:52, 11-16 01:35), documented in
  the project README after the rollback incident.
- Finding the build by `substitutions.SHORT_SHA` (64 working uses), then describe, then log.
- Secrets captured into a variable and compared by hash prefix (about 25 uses, cl:822561a0).
- Private emulator config on a free port with the UI off and a `demo-` project ID, waiting on the
  log line with a cap (cl:9d9f, about 50 starts; cl:d613b091).
- Describe before and after a manual change; `update-traffic` after `services update` (the
  revision otherwise gets 0% traffic).

## Tested against gcloud 593 (`scripts/test_gcloud.py`)

- The guessed forms fail in gcloud's parser; their fixes parse. Checked with an empty throwaway
  `CLOUDSDK_CONFIG`, so no command reached Google.
- Every gcloud command written in SKILL.md parses; the `bq` flags exist.
- `CLOUDSDK_CORE_PROJECT` on one command overrides the config and writes nothing; `config set`
  persists for every later command.
- The deploy watcher, against a stub gcloud: live by revision name or image tag; green but not
  serving (the rollback); 0% tagged revision not counted; failure with step, `failureInfo` and log
  tail; no build; still running at the cap; expired login; permission denied; unreadable log.
  Every call pins project, account and region; no writes.
- A Firestore emulator on a private port with a `demo-` ID starts within the cap and stops
  cleanly when only our own process group is signalled.
