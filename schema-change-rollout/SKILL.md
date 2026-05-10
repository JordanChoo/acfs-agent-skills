---
name: schema-change-rollout
description: >-
  Roll out schema changes safely across storage, types, APIs, jobs, UI,
  exports, and tests. Use when adding, renaming, removing, or reinterpreting
  fields or entities that must stay compatible across mixed versions during a
  migration window.
---

# Schema Change Rollout

Use this skill when a data shape changes and more than one surface depends on it.

Typical triggers:
- adding a field
- renaming a field
- removing a field
- changing nullability or cardinality
- splitting one entity into several
- changing export or event payload shapes
- introducing backfills, migrations, or compatibility windows

## Core Principle

Most schema failures are rollout failures, not syntax failures.

The dangerous question is not "does the new schema compile?" It is:

`What happens while old readers, new writers, old data, new data, exports, and tests all coexist?`

Prefer expand, migrate, contract:

1. Expand
2. Migrate
3. Contract

Avoid single-shot flips unless the system is truly offline during the change.

## Load References Only When Needed

- Read [references/migration-patterns.md](references/migration-patterns.md) when you need detailed rollout sequences for additive, rename, removal, or semantic changes.
- Read [references/verification-checklist.md](references/verification-checklist.md) when you need a broader mixed-version verification matrix, backfill checks, or contract-phase exit criteria.

## First Pass: Build the Surface Inventory

Before editing anything, list every surface that touches the shape:
- storage schema
- application types
- serializers and deserializers
- API request and response contracts
- queue payloads and event messages
- caches and derived views
- imports and exports
- backfill or migration scripts
- validation rules
- UI or reporting surfaces
- tests and fixtures
- docs or operator runbooks

If you skip the inventory, the migration plan is incomplete.

## Choose the Migration Shape

Pick one of these change types and then open the migration reference if the rollout is nontrivial:
- additive change
- rename
- removal
- semantic change disguised as compatibility

## Compatibility Rules

- Readers should usually become tolerant before writers become strict.
- Writers should not emit values readers cannot parse.
- Backfills must be idempotent.
- Mixed old/new data must be a planned state, not an accident.
- Null, missing, empty, and default are different states. Treat them deliberately.
- Derived views, exports, and analytics are part of the schema surface.

## Rollout Checklist

### Expand

- add storage support
- add type definitions
- make parsers and readers tolerant
- add feature flags or guards if a staged rollout is needed

### Migrate

- update write paths
- dual-read or dual-write when required
- add a backfill or recomputation plan
- update fixtures and seeded data
- verify exports, webhooks, and background jobs

### Contract

- remove fallback reads only after backfill completion
- remove old writes only after all active writers are migrated
- tighten validators after the mixed-version window closes
- delete obsolete fields, indexes, views, and docs last

## What to Verify

Test all of these if they exist:
- old data read by new code
- new data read by still-compatible code paths
- partial backfill state
- mixed records in the same list, export, or API response
- retries or replay of old queue payloads
- imports and exports
- UI rendering with field absent, field present, and field malformed
- analytics or reporting queries using old views

## Common Smells

- migration plan only mentions one file or one table
- UI updated before storage or API compatibility exists
- new field required immediately with no compatibility window
- export or queue contracts forgotten
- fixtures still represent the old world
- backfill has no checkpointing or rerun safety
- removal happens in the same change as introduction

## Review Questions

Ask these directly:

1. What old data still exists after deploy?
2. What old code can still read or emit this shape?
3. Which async jobs or exports still consume the old shape?
4. Is the backfill idempotent and observable?
5. What tells us the contract phase is safe?

## Deliverables This Skill Should Push Toward

- surface inventory
- expand/migrate/contract plan
- compatibility rules
- backfill strategy
- verification matrix
- explicit cleanup criteria for the contract phase
