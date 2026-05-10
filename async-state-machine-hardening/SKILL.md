---
name: async-state-machine-hardening
description: >-
  Harden async workflows with queues, webhooks, cron jobs, pollers, retries,
  and multi-stage state transitions. Use when designing or reviewing status
  machines, dedupe behavior, idempotency, retry semantics, partial-failure
  handling, or race-prone background processing.
---

# Async State Machine Hardening

Use this skill when a system does work later, elsewhere, or more than once.

Typical triggers:
- Queue or task processors
- Webhook receivers
- Pollers and reconcilers
- Cron-triggered workflows
- Multi-stage jobs with persisted status
- Bugs involving retries, duplicate delivery, stuck states, or race conditions

## Core Principle

Treat every async boundary as hostile:
- Messages can arrive twice.
- Workers can crash after side effects but before state writes.
- State can change between read and write.
- Retries can replay stale intent.
- Partial success is normal, not exceptional.

## Load References Only When Needed

- Read [references/failure-patterns.md](references/failure-patterns.md) when you need deeper review guidance for TOCTOU, dedupe, retry, partial-failure, logging, or counter drift bugs.
- Read [references/test-matrix.md](references/test-matrix.md) when you need a more detailed failure-path test plan.

## Hardening Workflow

### 1. Map the state machine first

Write down:
- States
- Allowed transitions
- Terminal states
- Re-entry rules
- Ownership of each transition

If you cannot state which component owns a transition, the design is already weak.

Use a compact format like:

```text
queued -> processing -> completed
queued -> processing -> failed_retryable -> queued
processing -> cancel_requested -> cancelled
processing -> failed_permanent
```

Then add invariants:

```text
- completed is terminal
- cancel_requested is not reusable as active work
- duplicate enqueue must not count as failure
- retries must not double-apply side effects
```

### 2. Check the critical failure surfaces

Always review:
- TOCTOU and stale reads
- idempotency and dedupe
- retry semantics
- partial failure and orphaned work
- observability, redaction, and derived-state drift

Do not guess here. If the implementation is nontrivial, open the deeper reference.

## Design Rules

- One component should own each transition.
- Terminal means terminal. Do not reuse terminal or cancelling work as active work.
- Duplicate delivery must have explicit semantics.
- Side effects and status changes must be ordered intentionally.
- Reconciliation is part of the design, not a cleanup script of shame.
- Error taxonomy must drive behavior. "failed" is usually too vague.

## Code Review Checklist

Ask these in order:

1. Can this handler run twice without corrupting state?
2. Can it crash after the side effect but before the state write?
3. Can another worker mutate the same record between read and write?
4. Does retry preserve correctness, not just eventual completion?
5. Are duplicate tasks or duplicate webhooks classified correctly?
6. Can counters, summaries, or progress totals drift from source records?
7. Are cancellation states and retry states distinct?
8. Is sensitive data kept out of logs and error payloads?

## Common Smells

- single `status` field with no attempt metadata
- broad `catch` that overwrites the original error contract
- reads outside transactions followed by guarded writes
- "not found" and "not yours" returning distinguishable messages when that leaks existence
- state transitions inferred from logs instead of persisted facts
- counters updated optimistically with no recompute path

## Deliverables This Skill Should Push Toward

- a transition map
- explicit invariants
- an error taxonomy
- idempotency and dedupe rules
- targeted failure-path tests
- a reconciliation plan for derived state
