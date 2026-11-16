# Corrupt mailbox recovery

Use only when `health_check` is red with `integrity_check` failing, and only with the owner's
approval at each mutating step. Validated 2026-09-03 (0.3.30 corrupt, upgraded to 0.3.32,
rebuilt from archive with zero parse errors), with corrections from later incidents.

1. **Snapshot** outside the mailbox root: `storage.sqlite3` **with** its `-wal` and `-shm`, the
   `.bak`, the `am` binary, the unit and its drop-ins, and every MCP config you may touch.
2. **Confirm on a copy, never the live file.** Copy the database together with `-wal` and `-shm`
   (copying the main file alone shows false "never used" pages), then
   `sqlite3 /tmp/x/storage.sqlite3 'PRAGMA integrity_check;'`. "2nd reference to page N" and
   "Page N: never used" on a complete copy are the upstream signature. Or trust the server's own
   probe (`am doctor health`, the `integrity_check` verdict).
3. If `health_check` shows `reclaimable_attention: true`, run `am doctor reclaim --yes` first
   (move-only, safe while live; preview with `--dry-run`).
4. **Stop through systemd only**, then confirm the drain: `systemctl --user stop
   agent-mail.service`, and `am doctor drain` must report `safe_to_mutate: true`. A killed PID
   comes straight back (`Restart=always`).
5. If `am update --check` shows a newer release, upgrade while stopped:
   `AM_INSTALL_SKIP_MCP_SETUP=1 AM_INSTALL_SKIP_REMOTE_HTTP_READINESS=1 bash install.sh --dest
   ~/mcp_agent_mail --yes --no-service`. It needs `minisign`. Diff config checksums before and
   after; it must touch only the two binaries. Never build from source.
6. `am doctor reconstruct --dry-run`, then `--yes`. It may refuse with "reconstruct salvage source
   ... failed validation; refusing an archive-only candidate" (upstream #302). Then start the
   service and let startup self-heal rebuild from the archive: it logs `database reconstruction
   from archive complete`, quarantines the old file as `storage.sqlite3.corrupt-<ts>` and reaches
   `Startup readiness self-probe passed` in about two minutes. `/health` refuses connections
   meanwhile; that is not a failed restart. Wait with a loop, not by retrying calls.
7. **Verify:** `/health` ready; integrity on a fresh complete copy says `ok`; `am doctor check`
   Live Operational Checks OK; the ATC agent has re-registered; `health_check` with no failing
   critical verdicts, **except** that a known integrity false positive (upstream GH#151) can keep
   the `integrity_check` verdict red while `functionally_degraded` is `false` and writes succeed.
   If the complete copy says `ok`, that red verdict is the false positive: record it and stop;
   do not start another recovery.
8. If the journal says the backup destination "has companion SQLite or FrankenSQLite state", move
   the leftover `storage.sqlite3.bak-wal` / `-shm` aside so the hourly backup resumes.
9. Re-converge clients (Part 2, "Safe remediation order", step 2), move any
   `.setup-self-heal/*.json` record that names a dead port aside, and restart Codex, Cursor and
   Gemini sessions.

Each recovery leaves forensic bundles and quarantined databases on disk. `health_check`
`retention` turning yellow means debris to consolidate (`am doctor reclaim --dry-run`), not
corruption. One box reached about 240 GB this way.
