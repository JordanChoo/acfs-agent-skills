# Verification Checklist

Use this reference when the rollout includes backfills, compatibility windows, or multiple readers and writers.

## Mixed-Version Verification

Test all of these if they exist:
- old data read by new code
- new data read by still-compatible code paths
- partial backfill state
- mixed old and new records in the same list, export, or API response
- retries or replay of old queue payloads
- imports and exports
- UI rendering with field absent, field present, and field malformed
- analytics or reporting queries using old views

## Backfill Questions

Ask:
1. Is the backfill idempotent?
2. Can it resume safely?
3. How is progress observed?
4. What state exists if the backfill stops halfway?
5. What proves the contract phase is now safe?

## Contract-Phase Exit Criteria

Do not remove old paths until you can show:
- all active writers have migrated
- old readers are no longer required
- backfill reached completion or an accepted steady state
- exports and async jobs no longer depend on the old shape
- test fixtures and seed data reflect the new world
