---
name: agent-mail-ops
description: >-
  How to use MCP Agent Mail (the mcp__mcp-agent-mail__* tools) correctly, and how to diagnose and
  recover it when it breaks. Use at the start of work in any project with Agent Mail, before
  editing files other agents may touch (file reservations), when sending or answering agent
  messages, on errors such as "Contact approval required", INVALID_AGENT_NAME, AGENT_NOT_FOUND,
  FILE_RESERVATION_CONFLICT, "refusing forced release", FEATURE_DISABLED or a missing
  sender_token, and when Agent Mail is slow, timing out or down: "AM is down", MCP disconnected,
  health_check red, agent-mail.service, 127.0.0.1:8765, rogue `am serve-http` /
  `mcp-agent-mail serve`, random-port configs, a failed nightly `am` update, or a mailbox rebuild.
---

# Agent Mail

Agent Mail lets agents on this VPS claim files and talk to each other. Part 1 is for every agent.
Part 2 is for fixing the service, and every change there needs the owner's approval.

Evidence behind each rule (from past sessions): [references/evidence.md](references/evidence.md).
Mailbox recovery procedure: [references/recovery.md](references/recovery.md).

# Part 1: Using Agent Mail

## The happy path

1. **Start once.** `macro_start_session(human_key="/abs/repo/path", program, model,
   task_description)`. Omit any name; the server issues one (adjective+noun). Keep the returned
   `agent.name` and `agent.registration_token` for the whole session, in your working notes, not
   in shared memory files. Read the returned `inbox`.
2. **Before editing, check, then reserve.**
   `check_file_reservation_conflicts(project_key, agent_name, paths)` is read-only. If clear,
   `file_reservation_paths(project_key, agent_name, paths=[exact files], ttl_seconds=3600,
   exclusive=true, reason="<bead-id>")`. Save the `id` of each entry in `granted`.
3. **Announce in the bead's thread.** `send_message(..., to=[names you just confirmed],
   thread_id="<bead-id>", subject="[<bead-id>] Start: ...", sender_token=<token>)`. Reply to
   existing threads with `reply_message`; do not start a new thread for the same work.
4. **Check the inbox at natural checkpoints** (after a commit, before finishing):
   `fetch_inbox(project_key, agent_name, since_ts=<last check>)`. Acknowledge every message with
   `ack_required` (`acknowledge_message`).
5. **Finish.** Push, then `release_file_reservations(project_key, agent_name,
   file_reservation_ids=[your ids])` (or `paths=[the same paths]`), then `[<bead-id>] Completed`
   in the thread.

`project_key` / `human_key` is always the **main repo's absolute path**, even inside a worktree.
Resource URIs use the slug instead (the path without its leading `/`, with `/` turned into `-`):
`resource://agents/data-projects-scry` lists agents, and
`resource://file_reservations/data-projects-scry` lists reservations.

## Identity rules

- **One identity per session.** Never create a second one: every `macro_start_session` or
  `register_agent` call *without* your name makes a new agent (the server holds about 790).
  Calling `register_agent` *with* your own name is fine; it updates the same agent.
- **A registration that timed out may have succeeded.** Do not fire it again straight away. Run
  `health_check`, then read `resource://agents/<slug>` and look for an agent created in the last
  few minutes with your program and model. Found it: that is you; adopt it by calling
  `register_agent` with its name (that returns the token). Not found: register once more.
- **Resuming** (new turn, after context compaction, or a 403 on writes because the token went
  stale): call `register_agent` with your own server-issued `name` and the same program/model.
  It returns the same agent with a new token. With tmux,
  `resolve_pane_identity(project_key, pane_id="%N")` recovers it.
- **Never choose a name yourself** (`INVALID_AGENT_NAME`), and never share one identity between
  sessions through a memory file.
- **Pass `sender_token`** on every write call that takes it. Do not fall back to raw HTTP.

## Messaging rules

- **Confirm every recipient first** with `whois(project_key, agent_name)`. On this server,
  sending to a name that does not exist **silently creates a placeholder agent** and delivers
  to it, so a typo or an example name from the docs (`BlueLake`, `GreenLake`) reaches no one.
- **"Contact approval required"**: reply in an existing thread that already includes them (even
  another bead's thread; one line pointing at your bead's thread is enough). Get a message id for
  `reply_message` from `resource://thread/<thread_id>` or `search_messages`. Otherwise call
  `request_contact` once and wait. Do not loop on it. The same applies to any first message,
  including to a reservation holder.
- **No "I'm online" messages** or broadcasts to everyone. Message the agents whose work you touch:
  the holders in `resource://file_reservations/<slug>` and the people in the bead's thread.
- **Keep bodies short**; link to a bead, file or commit instead of pasting logs.
- **Never read another agent's inbox**, and never poll: no `fetch_inbox` in a loop, no
  `include_bodies` without `since_ts`.
- Owed acknowledgements: `resource://inbox/<your name>?project=<abs path>`, or `am acks pending`
  (read-only; CLI calls can hang when the server is struggling).

## Reservation rules

- **Reserve before the first edit**, not after. A `released: 0` at the end means you never held
  anything.
- **Narrow paths.** Exact files, not `src/**` or `tests/**`. A glob conflicts with every file under
  it, in both directions.
- **`.beads/issues.jsonl`**: hold it only for `br sync --flush-only` plus the commit, with a short
  TTL (300 s). Long leases on it block every agent.
- **On a conflict, never edit the file anyway**, never edit it through a script, and never
  "proceed advisory". Message the holder in the bead thread (`importance="high"`,
  `ack_required=true`), add a bead comment, and switch to other work. If the holder has not
  replied by the time the lease expires and you are still blocked, tell the owner in your reply
  to them (name the file, holder and bead).
- **A refused force-release is final** ("Reservation still shows recent activity; refusing
  forced release"). `last_active_ts == inception_ts` does **not** prove an agent is dead; let
  the lease expire or the server's reaper handle it.
- **Find reservation ids** in your `granted` reply, in `resource://file_reservations/<slug>`, or
  with `am file_reservations active` (read-only, but CLI calls can hang when the server is
  struggling; prefer the resource). Never grep the mailbox archive.
- **Renew** before expiry: `renew_file_reservations(file_reservation_ids=[...],
  extend_seconds=1800)`; ids are a list, not a string. After an expiry or a reaper notice,
  re-check your work and reserve again.
- **Build slots are disabled** on this server (`FEATURE_DISABLED`). Before a heavy build, tell
  the agents holding reservations in the project, in your bead's thread.
- **Waiting for a reply**: do other work and check the inbox at your next checkpoint. There is no
  need to wait in a loop.

## Shared git working tree

- Stage only your own paths; check `git diff --cached --stat` before every commit. If other
  agents' changes are already staged, leave them staged (the index is shared) and commit only
  yours with a pathspec: `git commit -m "..." -- <your paths>`. That commits the whole current
  content of those paths, so first check `git diff -- <your paths>` holds only your hunks.
- Never stash, revert or reset to "isolate" changes: it sweeps up other agents' work. If your
  commit picked up another agent's change, push it and say so; do not revert it.
- Before pushing, check whether peers pushed, then `git pull --rebase`.

## When Agent Mail is slow or down

1. Retry the call **once** after a pause.
2. Still failing: carry on without it, as AGENTS.md says. Record coordination as bead comments
   (`br comments add`), keep to files you clearly own, and re-sync when it returns.
3. Do not probe it every turn, and do not work around it: no `curl` JSON-RPC calls in place of
   the tools, no reading or writing `storage.sqlite3`, no manual server, no restart. Fixing the
   service is Part 2, with the owner's approval.

# Part 2: Fixing Agent Mail

## Contract

- Production Agent Mail is the managed user service `agent-mail.service`
  (`Restart=always`), endpoint `http://127.0.0.1:8765/mcp/`, mailbox
  `~/.mcp_agent_mail_git_mailbox_repo`. The `am` binary in `~/mcp_agent_mail/` is upgraded by the
  ACFS nightly job.
- **Never** launch `am serve-http` or `mcp-agent-mail serve` by hand. Older builds stopped the
  managed server to take over (and systemd fought back); 0.3.40 refuses while a live server
  answers on the same port, `--takeover` kills it, and another port gives two writers on one
  mailbox, the known corruption path. Never write a second unit, never kill the PID (systemd
  restarts it), never bridge a stale port to 8765.
- Never point configs at a random localhost port unless the owner wants an isolated sandbox with
  its own storage.
- Do not kill processes or restart services without the owner's approval.

## Fast triage (read-only; every network call has a timeout)

```bash
systemctl --user status agent-mail.service --no-pager
systemctl --user show agent-mail.service -p NRestarts -p ActiveEnterTimestamp
ss -ltnp | rg ':8765'
curl -m 10 -fsS http://127.0.0.1:8765/health
ps -ef | rg 'mcp-agent-mail serve|am serve-http|am (mail|robot|doctor|file_reservations)' | rg -v rg
am doctor health
am doctor drain
```

`/health` is liveness only; it says `ready` even on a corrupt mailbox. The verdict agents act on
is the `health_check` tool (`health_level`, `verdicts`, `health_level_contributors`):

```bash
curl -m 20 -sS -X POST http://127.0.0.1:8765/mcp/ -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"health_check","arguments":{}}}' \
  | rg -o '"health_level":"[a-z]+"|"failing_verdicts":\[[^]]*\]'
```

Then the journal, version and nightly update:

```bash
journalctl --user -u agent-mail.service --since -3h --no-pager | rg -i 'malformed|corrupt|integrity|quarantin|reconstruct|zombie|pool_acquire|blocking dispatch' | tail -20
am --version && am update --check
tail -25 "$(ls -t ~/.acfs/logs/updates/nightly-*.log | head -1)" | rg -i 'agent mail|minisign|checksum'
```

Config drift (stale ports in live or backup configs):

```bash
rg -n '127\.0\.0\.1:[0-9]+/(mcp|api)/' /data/projects /home/ubuntu \
  -g 'settings.local.json' -g '*.mcp.json' -g '*.bak' -g 'settings.json' -g 'config.toml' -g '.claude.json'
```

## Decision rule

| Symptom | Likely cause | Next step |
| --- | --- | --- |
| `/health` fails, a rogue `am serve-http` / `mcp-agent-mail serve` exists, or `NRestarts` is high | Split brain from a manual server; the unit crash-loops on the taken port | Ask the owning session to stop it, or ask the owner; then let systemd recover |
| `/health` times out or tool calls hang; journal shows `zombie`, `pool_acquire` or `blocking dispatch` | Wedged or saturated server | With approval: `systemctl --user restart agent-mail.service`, then wait about 2 minutes (self-heal refuses connections meanwhile) and recheck |
| `/health` ready, `health_check` red with `integrity_check` failing | Corrupt SQLite (upstream FrankenSQLite bug, recurs) | [references/recovery.md](references/recovery.md). Exception: after a completed recovery, red with `functionally_degraded: false`, working writes, and `ok` from an integrity check on a complete copy (with `-wal` and `-shm`) is the known GH#151 false positive; record it, do not recover again |
| `health_check` yellow on `retention` only | Recovery debris and staging on disk, not corruption | `am doctor reclaim --dry-run`, show the owner; it moves, never deletes |
| `/health` fine, one harness still failing | Client config drift or a stale client session (Claude reads `~/.claude.json`; Codex, Cursor, Gemini, Factory read their own configs) | Fix the config (below), restart that client |
| `am` CLI commands hang or say the mailbox is locked | Stale `am mail` / `am robot` processes holding the activity lock | Show the owner the processes from triage; prefer the MCP tools or `am robot` |
| Nightly log says `[fail] MCP Agent Mail` and `am update --check` shows a newer release | Stuck upgrade (stale installer checksum, missing `minisign`) | Report to the owner; never build `am` from source or reset `~/mcp_agent_mail` |

`am doctor check` warnings right after a recovery are secondary evidence; `/health`, the
listener and `health_check` are authoritative.

## Safe remediation order (each step with the owner's approval)

1. Stop the rogue server through its owning session.
2. Restore configs to `http://127.0.0.1:8765/mcp/`:
   `am setup run --yes --agent codex,cursor,gemini,factory,windsurf` (add
   `--no-user-config --project-dir <dir>` per project). It **skips entries that have no bearer
   token**; fix those, and inert `mcpServers` blocks in `~/.claude/settings.json` and
   `.claude/settings.local.json`, by editing the URL only. Old ntm-spawned servers left ports in
   `<agent>.mcp.json`, `.claude/settings.local.json`, `~/.codex/config.toml` and the mailbox's
   `.setup-self-heal/*.json`: sweep all of them.
3. Restart `agent-mail.service` only if it is still unhealthy, and wait about 2 minutes.
4. If only one harness misbehaves: `bash ~/src/acfs-agent-skills/scripts/audit-drift.sh`.
5. Recheck `/health` and `health_check`, then have affected agents reopen their clients.

## Hazards

- The ACFS nightly job (04:00) reinstalls `am`; its fallback launcher can start a second server
  when `/health` is not ready. `ACFS_SKIP_AGENT_MAIL=1` (drop-in on `acfs-nightly-update.service`)
  disables that; the binary still updates.
- Never run bare `am doctor fix` while agents are live: it rewrites configs, stops the listener
  and reconstructs. Use `--dry-run` or `--only <id>` (ids from `am doctor fixers`).
- Never open the live `storage.sqlite3` with `sqlite3`, not even a `pragma`, and never edit rows:
  the archive restores them and the writes risk corruption. Work on a copy that includes `-wal`
  and `-shm`.
- Every restart is a recovery cycle; do not restart "to be safe".

## Local evidence paths

- `~/.config/systemd/user/agent-mail.service` and `agent-mail.service.d/`
- `~/.config/systemd/user/acfs-nightly-update.service.d/`
- `~/.acfs/logs/updates/nightly-*.log`
- `~/AM_NEXT_STEPS.md`
- `~/.mcp_agent_mail_git_mailbox_repo/doctor/forensics/storage.sqlite3/<verb>-<ts>/summary.json`
- `~/am-recovery-20260903/` (Sep 2026 incident snapshots)
- `/data/projects/<project>/.ntm/logs/am-*.log`

## Anti-patterns

Using it:
- Registering again after a timeout, or once per turn.
- Sending to a name you did not just confirm with `whois` (creates a ghost agent).
- Editing a file someone else holds, by any route.
- Force-releasing because `last_active_ts == inception_ts`.
- Grepping the mailbox archive for reservation ids.
- Polling `fetch_inbox`; reading another agent's inbox.
- Raw `curl` JSON-RPC or SQLite in place of the tools.

Fixing it:
- A second server on any port, a second unit, a port bridge, killing the PID.
- Treating `/health` `ready` as healthy, or `am doctor check` alone as down.
- Bare `am doctor fix`; touching the live database.
- Restarting without approval; building `am` from source.
