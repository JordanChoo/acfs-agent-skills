# Failure Patterns

Use this reference when the async workflow has real complexity or when a review already smells wrong but the exact bug class is still unclear.

## TOCTOU and Stale Reads

Look for:
- status checks outside transactions
- read-then-write logic split across multiple calls
- transition decisions computed before entering the write boundary

Typical bug:
- worker reads `queued`
- another worker changes the record
- first worker still writes `processing` based on stale assumptions

Preferred fixes:
- move the decision inside the transaction or atomic compare-and-set boundary
- re-read current status at the last responsible moment
- reject illegal transitions explicitly instead of silently overwriting them

## Idempotency and Dedupe

Look for:
- webhook handlers
- queue consumers
- deterministic task IDs
- retries that can recreate records, counters, or exports

Typical bug:
- duplicate delivery is treated as a hard failure even though the original task is already queued or running

Preferred fixes:
- define an idempotency key
- decide whether duplicate work is `success`, `noop`, or `conflict`
- make that behavior explicit in code and tests

`ALREADY_EXISTS` is often a dedupe success path, not an error path.

## Retry Semantics

Look for:
- retry loops that never persist next attempt metadata
- permanent errors treated as retryable
- retryable errors pushed directly to terminal failure
- polling paths that consume quota before dedupe or reuse checks

Preferred fixes:
- separate transient vs permanent error classes
- persist attempt count, next-attempt time, and last error classification
- charge quotas only for new work, not harmless polling or replay

## Partial Failure and Orphaned Work

Look for:
- batch handlers where one item poisons the whole operation
- side effects completed without matching status updates
- status written optimistically before enqueue or persistence succeeds

Preferred fixes:
- define the unit of truth: item, batch, or run
- represent partial success explicitly
- add a reconciliation path for orphaned side effects or drifted status

## Observability, Redaction, and Drift

Look for:
- logs that explain errors but not transitions
- top-level log fields that bypass sanitizers
- stack traces or raw payloads written in production logs
- counters or progress docs that can diverge from source truth

Preferred fixes:
- log transition reason, actor, and idempotency key
- keep sensitive payloads nested behind a sanitizer path
- prefer recompute-capable derived state over hand-maintained counters without repair logic

## Review Order

When reviewing a risky async workflow, check in this order:

1. Illegal transition risk
2. Duplicate delivery semantics
3. Retry classification
4. Partial side-effect corruption
5. Logging and audit leaks
6. Derived-state drift and reconciliation
