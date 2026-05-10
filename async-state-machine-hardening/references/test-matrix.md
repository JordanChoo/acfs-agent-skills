# Test Matrix

Do not stop at the happy path.

## Minimum Failure-Path Coverage

Add tests for:
- duplicate delivery
- duplicate enqueue
- retry after partial success
- crash or thrown error between side effect and transition
- stale-state conflict
- cancellation in progress
- permanent external 4xx or not-found failure
- transient external 5xx or timeout failure
- reconciliation of drifted counters or orphaned records

## By Boundary Type

### Queue Consumer

Test:
- same payload delivered twice
- enqueue dedupe returns already-exists
- downstream write fails after task acceptance
- worker retries after partial persistence

### Webhook Receiver

Test:
- duplicate webhook
- malformed payload
- replay after success
- upstream sends terminal-not-found vs transient-timeout

### Poller or Reconciler

Test:
- unknown vendor status
- missing next-attempt metadata
- timeout exhausted
- drift recompute on partially initialized state

### Batch Processor

Test:
- one item fails while others succeed
- retry resumes only failed items
- summary counters match item truth after recompute

## Test Design Rules

- Use fixtures or stubs that force each branch deterministically.
- Assert status transitions, not just returned values.
- Assert duplicate semantics directly.
- Assert counters and summaries against source records after reconciliation.
