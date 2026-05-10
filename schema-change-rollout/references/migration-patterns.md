# Migration Patterns

Use this reference when the change touches multiple producers or consumers, or when you expect old and new shapes to coexist for any meaningful period.

## Additive Change

Use when adding a field or entity.

Safe default order:
1. Add storage support
2. Make readers tolerate missing data
3. Update writers
4. Backfill if needed
5. Expose in UI, exports, and downstream jobs
6. Tighten validation only after old data is handled

## Rename

Do not perform true rename first.

Safe default order:
1. Introduce new field
2. Dual-read old and new
3. Dual-write if needed
4. Backfill old into new
5. Flip readers to prefer new
6. Remove old only after verification

## Removal

Do not delete first.

Safe default order:
1. Stop new writes to the old field
2. Keep readers tolerant
3. Verify no active producers still emit it
4. Remove downstream dependencies
5. Delete the field only after the compatibility window ends

## Semantic Change

If meaning changes but the field name does not, treat it as a new field anyway.

Silent semantic reuse is worse than a visible rename because the code looks compatible while behavior is not.

## Surface Areas People Forget

- exports
- webhooks
- queues and replayed payloads
- cached or materialized views
- fixtures and seed data
- analytics or reporting jobs
- docs and operator runbooks
