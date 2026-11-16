# Mailbox recovery: operator checklist

Read only when current diagnostics justify a recovery proposal. These are
conditional operations, **not commands to run during ordinary coding or tests**.
Existing owner authorization can cover a defined repair scope; otherwise prepare
the exact affected service, mailbox and configs before asking. Project rules may
forbid service mutations entirely. Never evade those rules through another tool.

## Establish evidence before mutation

1. Record service/listener identity, version, recent journal, structured
   `health_check` verdicts, integrity timestamps, pool/queue pressure and archive
   lag. A stale passing integrity check does not rule out corruption now. A hung
   service is not by itself proof of corruption. Retention yellow alone is not a
   rebuild trigger, and move-only consolidation is not a disk-space reclamation
   guarantee. Preview any consolidation; no automatic `reclaim --yes`.
2. Preserve available evidence outside the mailbox in a fresh protected directory:
   unit/drop-ins, binary version, exact configs with secret handling, logs and
   database state. A live sequential copy of DB, WAL and SHM is **best-effort
   forensic evidence, not a transactionally consistent snapshot**. Include all
   companions that exist; don't create missing ones. Never open live SQLite with
   `sqlite3`, checkpoint it manually or edit rows.
3. A trustworthy offline integrity check requires a consistent snapshot. Use a
   supported consistent backup facility, or, within an explicitly authorized
   maintenance window, quiesce **all writers** through their managed lifecycle,
   confirm drain (`safe_to_mutate: true`) and then copy the stable DB and its
   existing `-wal` / `-shm` companions together into a fresh directory. A false
   drain verdict stops offline mutations. Analyze only the copy, retain originals,
   and do not classify a live-copy anomaly as confirmed corruption or dismiss it
   as a harmless artifact without further evidence.
4. Compare DB versus archive coverage. Write-behind may leave **DB-only messages**;
   archive reconstruction can lose them. Preserve salvage sources and validate
   coverage/parse results before accepting an archive-only candidate. If parity
   cannot be established, report the uncertainty and obtain a concrete operator
   decision; do not treat archive refusal as permission to force an alternate
   startup-rebuild route.

## Conditional intervention

- Use only the existing managed unit for an authorized restart/stop/start. Never
  kill a PID, run a second server or use `--takeover`. A restart may itself invoke
  startup reconstruction, so preservation and data-risk assessment come first.
- Inspect local `am doctor reconstruct --help` and a bounded dry run before any
  authorized reconstruct. An archive-only validation refusal (historical #302)
  is a **stop and inspect** condition, not an instruction to defeat the refusal.
- Updates use the verified managed installer/release path only when in scope.
  Do not run an unqualified `bash install.sh` from an arbitrary cwd, source-build
  the tool, reset its checkout or let an updater silently rewrite clients/start
  a second listener. Resolve installer provenance, flags and backups first.
- Stale backup companion files or stale self-heal config records are evidence to
  inspect, not files to delete/move automatically. Any approved relocation needs
  exact paths, a fresh destination, collision checks and retained mapping.
- If config repair is in scope, preserve exact files, change only intended URL
  entries, account for tokenless entries skipped by setup, inspect diffs and ask
  affected clients to reconnect. Do not scan/paste secrets from all home configs.

## Verify and stop

An authorized restart may return before startup is ready. Older incidents took
about two minutes; that is an observation, not an SLA. Use a **bounded** readiness
wait with per-request timeouts, overall deadline and service-failure stop; keep
working on independent tasks and report journal progress without retry storms.
If readiness never arrives, stop and report it rather than restart repeatedly.

Require current `/health` readiness **and** structured tool health, fresh
integrity/coverage evidence, expected records and successful operations already
within authorized scope. Do not send synthetic messages or register dummy agents
just to prove writes work. Record command exits and which checks did not run.
A known GH#151 false positive needs corroboration from a consistent fresh snapshot
and fresh server/operation evidence; `functionally_degraded: false` alone is not
proof. New or conflicting evidence means diagnosis remains open.

Historical reference: 2026-09-03 recovery upgraded 0.3.30 to 0.3.32; later incidents
exposed snapshot inconsistency, stale checks, and red-after-recovery ambiguity.
Those versions are not universal instructions for the current installation.
Retain forensic bundles and quarantines; consolidation/deletion is separate work.
