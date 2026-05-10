---
name: playwright-testing
description: >-
  Discipline for Playwright end-to-end tests. Use when the repo has
  `@playwright/test` in deps, a `playwright.config.{ts,cjs}`, a `tests/e2e/`
  directory, or the user mentions e2e, flaky tests, selectors, traces, or
  Playwright. Enforces selector hierarchy, fixtures-first imports, no-mock
  policy in protected paths, emulator-only project IDs, trace-on-failure
  artifact discipline, and structured flake triage.
---

# playwright-testing

Decision logic for working safely in Playwright E2E suites. Goal: prevent the recurring failures — flaky selectors, mocks creeping into E2E, suites that pass locally but fail (or worse, succeed-against-prod) in CI.

## Triggers

Load this skill when ANY of:
- Files: `playwright.config.{ts,cjs,js}`, `tests/e2e/`, `e2e/`, `*.spec.ts` under a tests dir
- Deps: `@playwright/test`
- User mentions: e2e, flaky test, playwright, trace, selector, getByRole, page.goto, fixtures (in test context)

## Pre-flight: discover project conventions

Real Playwright suites in this environment ship discipline as scripts. **Look first; respect them.**

```
tests/e2e/fixtures/index.ts         # custom test/expect re-export
tests/no-mock.protected.txt         # paths where vi.mock / mockX is forbidden
tests/no-mock.allowlist.txt         # path:line | reason exceptions
scripts/check-no-mock.mjs           # CI gate: scans protected paths
scripts/check-e2e-test-logger.mjs   # CI gate: enforces fixtures import + logger hooks
scripts/check-route-coverage.sh     # CI gate: every route has an e2e
scripts/run-e2e-local-with-emulators.sh  # canonical local run
```

If a check script exists, **its rule is non-negotiable** — the script will fail the PR. Read the script before editing tests, not after.

## Project ID safety net (Firebase-emulated suites)

Both scry and philomena pin `VITE_FIREBASE_PROJECT_ID=demo-test` in `playwright.config.*`. The `demo-*` prefix is what tells the Firebase SDK *"emulator only, no real auth/credentials accepted"*. **Never** edit a config to use a real project ID for E2E. If you see one, stop — that suite will hit prod Firestore.

Verification: `grep -E 'PROJECT_ID|projectId' playwright.config.*` — every value must start with `demo-`.

---

## Playbooks

### Writing a new E2E test

1. **Imports**: import `test` and `expect` from `tests/e2e/fixtures` (or whatever the project's fixtures path is), NOT from `@playwright/test` directly. The `check-e2e-test-logger.mjs` gate enforces this — direct imports are rejected unless allowlisted, and allowlisted files must call `attachAllHooks()` / `createTestLogger()`.
2. **Selectors**, in priority order:
   - `page.getByTestId('...')` if `data-testid` is on the element
   - `page.getByRole('button', { name: /save/i })` — semantic, accessibility-friendly
   - `page.getByLabel(...)` for form fields
   - `page.getByText(...)` for static content
   - CSS / XPath only when nothing above works, and add a comment explaining why
3. **Waits**: never `waitForTimeout(<number>)` to "fix" a race. Use `expect(locator).toBeVisible()`, `page.waitForResponse(/api/)`, or `waitForLoadState('networkidle')`. A bare `waitForTimeout` is a flake bomb with a delayed fuse.
4. **Auth**: reuse `storageState` from a setup project — never log in fresh per test. If the project doesn't have one, that's the first thing to add.
5. **Mocks**: defer to project policy. If `tests/no-mock.protected.txt` covers the path you're editing, `vi.mock` / `mockX` is **forbidden** — use the emulator instead. To get an exception, add a `path:line | reason` line to `tests/no-mock.allowlist.txt`; the reason is reviewed.

### Debugging a failing test

Order matters — classify before fixing:

1. **Did it fail in CI but pass locally?** → Pull the trace. Configs use `trace: 'retain-on-failure'` or `'on-first-retry'`; trace is in `playwright-report/` or `test-results/`. `npx playwright show-trace <path>` opens it. Don't guess from stdout.
2. **Classify the flake** before changing anything:
   - **(a) timing** — assertion before the UI settled. Fix: replace `waitForTimeout` with a proper wait, or assert on the post-condition.
   - **(b) shared state** — test N depends on test N-1's leftovers. Fix: per-test fresh emulator data (Firestore emulator REST clear), or `test.describe.serial` if ordering is genuinely required.
   - **(c) port collision** — two emulator suites on the same port. Fix: integration suite uses 18080/19199 (different from default 8080/9199); check the project's `run-firestore-integration.sh`.
   - **(d) real race in app code** — the test is correctly catching a bug. Fix the app, not the test.
3. **Never** disable retries, traces, screenshots, or video to "make CI green." That deletes the diagnostics you need next time.

### Adding a route or feature

If `scripts/check-route-coverage.sh` exists, every new route needs at least one e2e. The gate will block the PR otherwise. Add the spec in the same change, not as a follow-up bead.

### Running locally

- Default: `npm run test:e2e:local` (or whatever the project's wrapper is). It usually starts emulators, waits for them, then runs Playwright.
- For UI debugging: `npm run test:e2e:ui` (Playwright UI mode) or `npx playwright test --debug`.
- Single test: `npx playwright test tests/e2e/foo.spec.ts -g "test name"`.
- Reuse-existing-server: configs set `reuseExistingServer: !process.env.CI`, so a long-running `npm run dev` will be picked up — no need to restart.

### Parallelism and CI

- `fullyParallel: true` is the default; `workers: 1` is set in CI to avoid emulator port contention.
- For emulator-backed integration tests (vitest, not playwright): use `--no-file-parallelism` because they share fixed ports and clear global state.
- If you add a test that mutates a singleton (auth user, global config), put it in its own `test.describe.serial` block.

---

## Red flags — stop and ask

- A spec with `import { test, expect } from '@playwright/test'` (not from fixtures) in a project that has `check-e2e-test-logger.mjs` — the gate will fail
- Adding `vi.mock(...)` to a file in `tests/no-mock.protected.txt`
- Disabling `trace`, `retries`, `screenshot`, or `video` to fix flakiness
- A `playwright.config.*` change that points `PROJECT_ID` at anything other than `demo-*`
- `waitForTimeout(<seconds>)` added to "stabilize" a test
- Replacing `getByRole` / `getByTestId` with brittle CSS to make a test pass faster
- Deleting an e2e spec instead of fixing it (recurring user concern: do not delete tests without permission)

---

## What to read first in an unfamiliar Playwright suite

In order:
1. `playwright.config.*` — testDir, projects, baseURL, env, trace policy, webServer
2. `tests/e2e/fixtures/index.ts` — the custom test/expect contract
3. `scripts/check-*.mjs` and `scripts/check-*.sh` — the discipline gates
4. `tests/no-mock.protected.txt` and `tests/no-mock.allowlist.txt` — mock policy scope
5. One existing spec next to what you're working on — copy its setup/teardown shape
6. The project's `AGENTS.md` / `CLAUDE.md` for any test-discipline overrides
