# CI and Fixtures

Use this reference when the harness works locally but drifts in CI, or when fixture strategy is the real source of flakiness.

## Local and CI Rules

- Keep local and CI startup paths as close as possible.
- If CI is authoritative, state that explicitly in scripts or docs.
- Do not let local-only shortcuts become hidden CI dependencies.
- Prefer checked-in fixtures over live third-party calls.

## Stable Waits

Wait on real state changes, not arbitrary sleeps.

Prefer:
- visible UI backed by seeded emulator state
- completion of emulator-backed calls
- durable UI state that reflects document or callable outcomes

Avoid:
- blind sleeps
- racing auth hydration
- assertions tied to animation timing instead of system state

## Common Failure Modes

- emulator process starts but one service is not ready
- tests seed Firestore but forget Auth, causing permission failures
- app still points at live Firebase in one code path
- seeded data shape no longer matches current app assumptions
- browser tests depend on leftover state from prior runs
- callable functions use a different project ID than Firestore or Auth
- fixture paths break under ESM or changed working directories
