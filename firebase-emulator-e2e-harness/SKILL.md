---
name: firebase-emulator-e2e-harness
description: >-
  Build or repair deterministic E2E and integration harnesses around Firebase
  emulators. Use when Playwright, Vitest, or similar tests need seeded Auth,
  Firestore, Storage, or Functions state without depending on live Firebase
  services.
---

# Firebase Emulator E2E Harness

Use this skill when the test environment must behave like Firebase without using production or shared cloud state.

Typical triggers:
- browser E2E against Firestore, Auth, Storage, or Functions
- flaky local or CI tests caused by emulator startup or seeding problems
- test suites that still depend on live Firebase
- hard-to-reproduce auth, rules, or callable behavior
- repeated pain around fixture loading, project IDs, or emulator ports

## Core Principle

A useful emulator harness is deterministic, isolated, and fast to explain.

The harness should make it obvious:
- which emulators are required
- how test data is seeded
- how the app is pointed at the emulators
- when the system is ready
- how state is cleaned up between runs

## Load References Only When Needed

- Read [references/startup-and-seeding.md](references/startup-and-seeding.md) when you need more detailed startup, readiness, seeding, or emulator wiring guidance.
- Read [references/ci-and-fixtures.md](references/ci-and-fixtures.md) when you need CI parity rules, fixture guidance, or a sharper list of harness failure modes.

## Repo Signals

Look for:
- `firebase.json`
- `.firebaserc`
- emulator scripts in `package.json`
- Playwright or browser E2E config
- rules files for Firestore or Storage
- local env files or test env bootstrap code

If the repo does not already use Firebase emulators, do not force this skill onto a different stack.

## Harness Workflow

### 1. Fix the test boundary first

Decide what the test is proving:
- browser flow only
- browser plus callable functions
- rules enforcement
- data import or export flow

Do not use full browser E2E for problems that should be covered by emulator-backed integration tests.

### 2. Make startup deterministic

Use fixed project IDs and fixed ports where practical.

Avoid:
- random ports unless the harness propagates them correctly
- hidden global state from previous runs
- tests that assume emulators are ready immediately after process start

Add an explicit readiness check for every required surface:
- Auth
- Firestore
- Storage
- Functions

### 3. Seed state directly

Prefer direct seeding over UI setup.

Seed:
- Auth users
- Firestore documents
- Storage fixtures
- any required metadata documents or indexes used by the app

Keep fixtures minimal and explicit. The test should explain why each seeded artifact exists.

### 4. Point the app at emulators explicitly

Make emulator routing unambiguous in test mode.

Common needs:
- emulator host and port env vars
- fixed project ID
- auth domain or app config override
- browser-safe callable and storage endpoints

Do not rely on "it picks emulators automatically" unless the code proves it.

### 5. Write tests against stable waits

Wait on real state changes, not arbitrary sleeps.

Prefer:
- visible UI that depends on seeded data
- network completion tied to emulator-backed calls
- document or callable outcomes reflected in the UI

Avoid:
- timing assumptions
- optimistic clicks before auth or hydration completes
- assertions that depend on animation timing instead of system state

### 6. Control reset and teardown

Choose one of these models and state it clearly:
- full reset per test
- reset per file
- seeded baseline reused read-only across tests

If tests mutate shared seeded data, isolation is already broken.

## Review Checklist

1. Can this suite run without live Firebase access?
2. Are all required emulator services started and checked for readiness?
3. Is auth seeded directly instead of through the UI?
4. Can the app only talk to emulators in test mode?
5. Is data reset or recreated in a deterministic way?
6. Are waits tied to state, not sleep calls?
7. Are fixtures versioned and small enough to understand?

## Deliverables This Skill Should Push Toward

- a clear emulator startup path
- deterministic seeding helpers
- explicit app-to-emulator wiring
- stable browser waits
- local and CI parity notes
- fixture-backed tests that do not hit live services
