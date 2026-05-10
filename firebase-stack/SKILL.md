---
name: firebase-stack
description: >-
  Discipline for Firebase + GCP projects (Firestore, Functions, Hosting, Storage,
  Auth, Cloud Tasks, Cloud Scheduler, Secret Manager, BigQuery). Use when the repo
  contains firebase.json / firestore.rules / firestore.indexes.json, when running
  `firebase deploy`, editing rules or indexes, working with emulators, provisioning
  GCP infra, or rotating secrets. Enforces emulator-first testing, rules-test-before-deploy,
  index/query consistency, secrets hygiene, and scripted pre-flight gates.
---

# firebase-stack

Decision logic for working safely in Firebase + GCP repos. The goal is to prevent the recurring traps: deploying broken rules, deploying without indexes the queries need, leaking secrets, and skipping emulator validation.

## Triggers

Load this skill when ANY of:
- Files present: `firebase.json`, `firestore.rules`, `firestore.indexes.json`, `storage.rules`, `functions/` directory, `.firebaserc`
- Deps include `firebase`, `firebase-admin`, `firebase-functions`, `firebase-tools`, `@firebase/rules-unit-testing`
- User mentions: firebase deploy, firestore, security rules, emulator, indexes, cloud functions, cloud tasks, cloud scheduler, secret manager, bigquery, gcloud

## Pre-Flight: discover the project's existing tooling

Real Firebase repos in this environment ship their own scripts. **Always look first; don't reinvent.** Common paths:

```
scripts/verify-env.sh                          # required env vars present + match secrets
scripts/check-firebase-deploy-prereqs.sh       # required APIs enabled, billing on
scripts/run-e2e-local-with-emulators.sh        # emulator-backed E2E
scripts/run-firestore-integration.sh           # rules/data integration tests
scripts/provision-{queues,buckets,bigquery}.sh # GCP infra
scripts/update-secrets.sh / create-secrets.sh  # Secret Manager
scripts/deploy-production.sh / rollback-production.sh
```

If a script exists, **run it**. If a script is missing for an operation listed below, flag it before improvising.

## Required GCP APIs (deploy will fail without these)

cloudbilling, cloudtasks, secretmanager, firebaseextensions, cloudfunctions, cloudbuild, artifactregistry, run, eventarc, pubsub, cloudscheduler, firestore, firebasestorage. The project's `check-firebase-deploy-prereqs.sh` enumerates these — run it before any `firebase deploy` in a fresh project or after API churn.

---

## Playbooks

### Deploying

1. Identify the deploy target: `hosting`, `functions`, `firestore:rules`, `firestore:indexes`, `storage` — never bare `firebase deploy` unless the user explicitly said "all".
2. Pre-flight gates, in order:
   - `scripts/verify-env.sh` (or `--strict` in CI) — env/secret divergence is the #1 cause of broken deploys
   - Lint + typecheck + unit tests + build
   - For rules: see "Editing security rules" below — rules-unit tests must pass
   - For functions: build inside `functions/` (the `predeploy` hook in `firebase.json` runs `npm --prefix "$RESOURCE_DIR" run build`)
   - `secretlint` / equivalent secret scan if the repo has it
3. Deploy with `--only <target>`. Never `--force` unless the user explicitly asked.
4. After deploy: smoke-test the affected surface. Many repos have `scripts/smoke-test.sh`.

If the repo has a `deploy-production.sh`, defer to it. It usually encodes a stricter ordering (rules → indexes → functions → hosting) than ad-hoc `firebase deploy --only`.

### Editing security rules (`firestore.rules`, `storage.rules`)

This is the highest-risk surface. Recurring failure mode in this environment: rules edits ship without tests and leak cross-org data.

**Required before deploying rules:**
- Rules-unit tests pass against `@firebase/rules-unit-testing` (ports from `firebase.json` emulators block)
- Tests cover both the allow path and the deny path for every changed rule
- For org/tenant-boundary rules: explicit test that user-from-org-A cannot read/write resource-from-org-B
- Diff review: any new `request.auth != null` without a matching `resource.data.<owner-field>` check is suspicious

**Refuse to deploy rules if:** there is no rules-test file, OR tests fail, OR the diff weakens an existing condition without a stated reason.

### Editing queries / indexes (`firestore.indexes.json`)

Composite-index requirements are inferred from query shape. Common trap: developer adds a `where(...).where(...).orderBy(...)` query in code, app works in emulator (auto-creates indexes) but fails in prod.

**On every query change:**
1. Identify the new query shape (fields used in `where`, `orderBy`, `array-contains`, `in`).
2. Check `firestore.indexes.json` covers it. If not, add the index entry.
3. Deploy indexes BEFORE deploying functions/hosting that issues the new query: `firebase deploy --only firestore:indexes`.
4. Wait for index build (can be minutes-hours on large collections) — `gcloud firestore indexes composite list` to verify state.

### Local development with emulators

Emulator suite from `firebase.json`: functions=5001, auth=9099, firestore=8080, storage=9199, ui=4000 (verify the project's actual ports — they differ for parallel test runs, e.g. integration uses 18080/19199).

- `firebase emulators:start --project demo-test` for a clean dev session (`demo-*` project IDs are local-only and can't accidentally hit prod).
- For tests, use the project's wrapper (`scripts/run-e2e-local-with-emulators.sh`, `scripts/run-firestore-integration.sh`) — they handle Java 21, port allocation, and cleanup.
- **Never** run integration tests against prod or staging Firestore. If `GCLOUD_PROJECT` or `FIREBASE_PROJECT` points at a real project, stop.

### Secrets and env vars

Three places secrets live in Firebase repos; keep them in sync:
1. `.env` files (local dev, never committed) — verify `.env*` in `.gitignore` before any commit
2. `functions/.env.<project-id>` — runtime env for functions
3. Secret Manager (`gcloud secrets`) — production secrets, accessed via `defineSecret()` in functions

`scripts/update-secrets.sh` (when present) is the only correct way to rotate. It diffs Secret Manager against the repo's required list.

**Never:**
- Print secret values to logs or chat
- Commit `.env` or `functions/.env.*`
- Set secrets via `firebase functions:config:set` (legacy; deprecated for v2 functions)

### Infra provisioning (Cloud Tasks, Scheduler, Storage, BigQuery)

These are typically scripted as `scripts/provision-*.sh`. Run them; don't `gcloud` ad-hoc. Provisioning is idempotent in well-written scripts but ad-hoc commands miss IAM bindings and create drift.

### Cloud Functions

- Functions live in their own package (`functions/package.json`) with a separate lockfile. Run `npm ci` (or `bun install`) inside `functions/`, not at the repo root.
- For v2 functions: secrets via `defineSecret`, region pinning explicit, memory/timeout in the function definition.
- Test functions with `firebase emulators:exec` or the integration wrapper script.

---

## Red flags — stop and ask

- Any deploy command without `--only <target>` on a non-trivial change
- Rules diff with no test diff
- Query changes with no `firestore.indexes.json` diff
- `firebase use <prod-project-id>` followed by destructive commands (delete, write, import)
- `gcloud projects delete`, `firebase projects:delete`, `gcloud firestore databases delete`
- `firebase deploy --force`, `firebase functions:delete` without naming the function
- Anything writing to Secret Manager from a script that wasn't written for this repo

---

## What to read first in an unfamiliar Firebase repo

In order:
1. `firebase.json` — surfaces, emulator ports, predeploy hooks
2. `.firebaserc` — project aliases (which project is `default`, `staging`, `prod`)
3. `firestore.rules` + `storage.rules` — auth model
4. `package.json` scripts (top level) — deploy/test conventions
5. `scripts/` — pre-flight, provisioning, deploy, rollback wrappers
6. `functions/package.json` and `functions/src/index.ts` — function surface and entrypoints

Defer to the project's `CLAUDE.md` / `AGENTS.md` if they specify additional gates.
