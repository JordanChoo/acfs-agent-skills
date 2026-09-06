---
name: agent-mail-ops
description: >-
  Diagnose and recover Agent Mail when agents report "AM is down", MCP Agent
  Mail is disconnected, the health_check tool is red (corrupt SQLite), or local
  configs drift away from the managed endpoint. Use when checking
  `agent-mail.service`, `127.0.0.1:8765`, rogue `mcp-agent-mail serve`
  processes, split-brain caused by manual servers, a failed nightly `am`
  update, or a mailbox rebuild from the git archive.
---

# agent-mail-ops

Use this skill for Agent Mail incidents in the ACFS environment.

## Contract

- Production Agent Mail is the managed user service `agent-mail.service`.
- The production MCP endpoint is `http://127.0.0.1:8765/mcp/`.
- The production mailbox is the default shared archive under `~/.mcp_agent_mail_git_mailbox_repo`.
- The `am` binary lives in `~/mcp_agent_mail/` and is upgraded by the ACFS nightly job; upgrades never restart or hand-launch the service (see Hazards).
- Never "fix" AM by launching `mcp-agent-mail serve` or `am serve-http` manually against the production mailbox.
- Never rewrite live MCP configs to a random localhost port unless the user explicitly wants an isolated sandbox.

## Fast triage

Run these first:

```bash
systemctl --user status agent-mail.service --no-pager
ss -ltnp | rg '127\.0\.0\.1:8765|:8765'
curl -fsS http://127.0.0.1:8765/health
ps -ef | rg 'mcp-agent-mail serve|am serve-http' | rg -v rg
```

`/health` is only a liveness probe: it says `ready` even on a corrupt mailbox. The verdict agents act on is the `health_check` MCP tool:

```bash
curl -sS -X POST http://127.0.0.1:8765/mcp/ -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"health_check","arguments":{}}}' \
  | rg -o '"health_level":"[a-z]+"|"failing_verdicts":\[[^]]*\]'
```

Then check the version and the nightly update, which is where regressions and stuck upgrades come from:

```bash
am --version && am update --check
journalctl --user -u agent-mail.service --since -3h --no-pager | rg -i 'malformed|corrupt|integrity|quarantin|reconstruct' | tail -20
tail -25 "$(ls -t ~/.acfs/logs/updates/nightly-*.log | head -1)" | rg -i 'agent mail|minisign|checksum'
```

Then inspect config drift in live or backup MCP config files:

```bash
rg -n '127\.0\.0\.1:[0-9]+/(mcp|api)/' /data/projects /home/ubuntu \
  -g 'settings.local.json' -g '*.mcp.json' -g '*.bak' -g 'settings.json' -g 'config.toml' -g '.claude.json'
rg -l 'server_url' ~/.mcp_agent_mail_git_mailbox_repo/.setup-self-heal/ | xargs rg -o '127\.0\.0\.1:[0-9]+' | sort | uniq -c
```

If the incident is isolated to one harness, or follows shared skill changes, also audit shared skill drift:

```bash
cd ~/src/acfs-agent-skills
bash scripts/audit-drift.sh
```

## Decision rule

- `/health` fails and a rogue `mcp-agent-mail serve` exists: likely split-brain from a manual server.
- `/health` is `ready` but `health_check` reports `health_level: red` with `integrity_check` failing: the SQLite file is corrupt. Transport is fine; agents refuse to work on a red verdict. Go to "Corrupt mailbox recovery". This is an upstream FrankenSQLite engine bug (mcp_agent_mail_rust #278, #291) and recurs; do not blame or restart clients.
- `/health` is healthy but agents still complain: likely client config drift or a stale client session. Codex, Cursor, Gemini and Factory read their own config files; Claude Code reads `~/.claude.json`, so Claude can work while the others cannot.
- `am update --check` shows a newer release and the nightly log says `[fail] MCP Agent Mail`: the box is stuck on an old build. Common causes are a stale ACFS checksum for `install.sh` and a missing `minisign` binary.
- `scripts/audit-drift.sh` fails: Claude/Codex skill installation drift exists and one harness may be operating on stale instructions even if AM itself is healthy.
- `am doctor check` warnings immediately after recovery are secondary evidence; direct `/health`, listener checks, and config inspection are more authoritative.

## Safe remediation order

- Do not kill processes or restart services without user approval.
- Preferred order:
  1. Stop the rogue manual server by notifying the owning pane/session or via explicit operator action.
  2. Restore live MCP configs to `http://127.0.0.1:8765/mcp/` with `am setup run --yes --agent codex,cursor,gemini,factory,windsurf` (add `--no-user-config --project-dir <dir>` per affected project). Fix inert `mcpServers` blocks in `~/.claude/settings.json` and `.claude/settings.local.json` by editing the URL only.
  3. Restart `agent-mail.service` only if it remains unhealthy after the rogue owner is gone.
  4. If only one harness still behaves incorrectly, run `bash ~/src/acfs-agent-skills/scripts/audit-drift.sh` and normalize shared skill drift before doing more AM surgery.
  5. Recheck `/health`, then have affected agents restart or reopen their client sessions.

## Corrupt mailbox recovery

Validated 2026-09-03 (0.3.30 corrupt since Sep 1, upgraded to 0.3.32, rebuilt from archive with zero parse errors).

1. Snapshot outside the mailbox root: `storage.sqlite3`, `storage.sqlite3-wal`, `storage.sqlite3.bak`, the `am` binary, the unit and its drop-ins, and every MCP config you may touch.
2. Confirm on a copy, never on the live file: `cp storage.sqlite3 /tmp/x.sqlite3 && sqlite3 /tmp/x.sqlite3 'PRAGMA integrity_check;'`. "2nd reference to page N" and "Page N: never used" are the upstream signature.
3. If the `health_check` payload shows `reclaimable_attention: true`, run `am doctor reclaim --yes` first. It is move-only and safe while live.
4. Stop through systemd only, then confirm the drain: `systemctl --user stop agent-mail.service` and `am doctor drain` must report `safe_to_mutate: true`. The unit has `Restart=always`, so a killed PID comes straight back.
5. If `am update --check` shows a newer release, upgrade while stopped: `AM_INSTALL_SKIP_MCP_SETUP=1 AM_INSTALL_SKIP_REMOTE_HTTP_READINESS=1 bash install.sh --dest ~/mcp_agent_mail --yes --no-service`. It needs `minisign`. Diff config checksums before and after; the installer must touch only the two binaries.
6. `am doctor reconstruct --dry-run`, then `--yes`. On 0.3.32 it may refuse with "reconstruct salvage source ... failed validation; refusing an archive-only candidate" (upstream #302). That is expected: `systemctl --user start agent-mail.service` and let startup self-heal do the archive rebuild. It logs `database reconstruction from archive complete`, `durably promoted recovery candidate`, quarantines the old file as `storage.sqlite3.corrupt-<ts>`, and reaches `Startup readiness self-probe passed` in about two minutes.
7. Verify in this order: `curl /health` says `ready`, the `health_check` tool is green with no failing verdicts, canonical `integrity_check` on a fresh copy says `ok`, `am doctor check` shows every Live Operational Check OK, and the ATC agent has re-registered (a real write).
8. If the journal then says the backup destination "has companion SQLite or FrankenSQLite state", the recovery left `storage.sqlite3.bak-wal` and `-shm` beside the old backup; move the empty companions aside so the hourly backup resumes.
9. Re-converge clients (step 2 above), move any `.setup-self-heal/*.json` record that still names a dead port aside, then restart Codex/Cursor/Gemini sessions so they reload config.

## Hazards

- The ACFS nightly job (`acfs-nightly-update.timer`, 04:00) reinstalls `am` and then runs `_stack_configure_agent_mail_service`, whose fallback launcher starts a second `am serve-http` whenever `/health` is not ready. Two writers on one mailbox is the upstream corruption scenario. `ACFS_SKIP_AGENT_MAIL=1` (drop-in on `acfs-nightly-update.service`) disables that function; the binary still updates. A binary swap under the live process is harmless.
- Never run bare `am doctor fix` while agents are live: it also stops the listener and reconstructs. Use `--dry-run`, `--only <fm-id>` (ids from `am doctor fixers`), or `am setup run`.
- Every fsqlite restart is a recovery cycle (#291); do not restart "to be safe".
- Old ntm-spawned servers wrote random ports into `<agent>.mcp.json`, `.claude/settings.local.json`, `~/.codex/config.toml`, and the mailbox's `.setup-self-heal/*.json`; sweep all of them, not just the project you are in.

## Local evidence paths

Open these when you need authoritative machine-local evidence:

- `/home/ubuntu/.config/systemd/user/agent-mail.service` and `agent-mail.service.d/`
- `/home/ubuntu/.config/systemd/user/acfs-nightly-update.service.d/`
- `/home/ubuntu/.acfs/logs/updates/nightly-*.log`
- `/home/ubuntu/AM_NEXT_STEPS.md`
- `/home/ubuntu/.mcp_agent_mail_git_mailbox_repo/doctor/forensics/storage.sqlite3/<verb>-<ts>/summary.json`
- `/home/ubuntu/am-recovery-20260903/` (snapshots and moved-aside files from the Sep 2026 incident)
- `/data/projects/<project>/.ntm/logs/am-*.log`

## Anti-patterns

- Starting a second Agent Mail server on a random port.
- Pointing project-local MCP configs at that random port.
- Treating `am doctor check` alone as proof that AM is down.
- Treating `/health` `status: ready` as proof the mailbox is healthy.
- Opening the live `storage.sqlite3` with the `sqlite3` CLI; work on copies.
- Ignoring shared skill drift when only Claude or only Codex is affected.
- Editing the managed Agent Mail codebase from a consumer repo without owner approval.
