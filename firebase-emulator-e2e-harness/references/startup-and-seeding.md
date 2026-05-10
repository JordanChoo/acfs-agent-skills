# Startup and Seeding

Use this reference when the harness is failing before the actual test scenario begins.

## Startup Rules

- Use a fixed Firebase project ID in test mode.
- Prefer fixed emulator ports unless the harness propagates dynamic ports correctly.
- Start only the services you need, but verify every one you start.
- Add explicit readiness checks instead of assuming startup completion means readiness.

## Required Readiness Surfaces

Check the surfaces your suite depends on:
- Auth
- Firestore
- Storage
- Functions

If one service is not ready, the whole suite is not ready.

## Seeding Rules

Prefer direct seeding over UI setup.

Seed:
- Auth users
- Firestore docs
- Storage objects
- any metadata docs required by views, rules, or callables

Keep fixtures small and purposeful. A seed should exist because a test needs it, not because an earlier debugging session left it behind.

## App Wiring Rules

Make emulator routing explicit in test mode:
- emulator host and port env vars
- fixed project ID
- auth domain or config override if needed
- callable and storage endpoints that are browser-safe

Do not trust implicit detection unless the code clearly proves it.
