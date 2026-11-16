---
name: agent-mail-ops
description: >-
  Coordinate coding agents through MCP Agent Mail: session identity, inbox and acknowledgements,
  targeted messages, file reservations and shared-tree handoffs. Use at session start in an
  Agent Mail project, before shared-file edits, or for registration/token/contact/conflict errors,
  ambiguous write timeouts, FEATURE_DISABLED, outages and service recovery. Prevent duplicate
  identities/messages, preserve peers' work, and separate ordinary coordination from operator repair.
---

# Agent Mail: coordinate, then keep working

Use the connected MCP tools and their **current schemas**. Names below are the
server's tool names; discover their harness-specific prefix. Repository rules and
existing user authorization take precedence. Routine coordination is authorized
when the user/project requests it; this skill does not authorize unsolicited mail.
Service repair is a separate operator task, never an automatic response to a tool error.

## Happy path

1. **Resolve project and identity once.** Use the main repository's absolute path
   for `project_key` / `human_key`, including from a worktree. If this session has
   no identity, call `macro_start_session(human_key, program, model,
   task_description)` once, omitting a name. Save the returned `agent.name` and
   `agent.registration_token` in private session context, never git or shared
   memory. Read its inbox. If you already have a valid session identity, reuse it.
2. **Read before editing; reserve before writing.** Inspect existing diffs and
   ownership. Call `check_file_reservation_conflicts(project_key, agent_name,
   paths=[exact project-relative files])`, then `file_reservation_paths` with
   those paths, `ttl_seconds=3600`, `exclusive=true`, and the bead/task as `reason`.
   Supply a stable `idempotency_key` when the schema supports it. Inspect **both
   `granted` and `conflicts`**; the precheck is not an atomic lock. Save actual
   grant IDs and expiry; a request or partial grant is not full ownership.
3. **Tell affected agents.** Confirm real recipients with `whois`; use the
   existing task thread or `thread_id="<bead-id>"` and subject `[<bead-id>] Start`.
   Use `reply_message(message_id=...)` for the same discussion. Keep the message
   short: paths, intended change, expected handoff. If no relevant peer exists,
   do useful work without inventing recipients or sending an online broadcast.
4. **Check your inbox at checkpoints.** Before a conflicting edit, after a
   meaningful milestone, and before handoff, fetch a bounded page for your own
   identity. Read actionable bodies, act/reply if needed, then acknowledge each
   read message whose `ack_required` is true. Reading is not acknowledgement;
   acknowledging is not the same as answering a request.
5. **Finish deliberately.** Verify diffs, tests, staged paths and current leases.
   Land your authorized changes, then release only your grant IDs or exact paths
   with `release_file_reservations`. Report the commit, checks and unfinished work
   in the task thread. If blocked/abandoning, release what you no longer use and
   update the bead; do not hold leases while waiting indefinitely.

If an operation's result is unclear, follow the table below **before retrying**.
Never print tokens, approval bundles, config credentials or full private bodies.

## Errors and uncertain outcomes

| Situation | Next action and stop condition |
|---|---|
| Nameless registration timed out | It **may have succeeded**. Check health once; use a session-bound `resolve_pane_identity(project_key, pane_id)` when available. Only resume an identity proven yours by saved session state or pane binding. Matching program/model/time/task is discovery evidence, **not ownership proof**. If ownership is ambiguous, record that and continue independent work; don't adopt a peer or create repeated identities. |
| Context compacted; name/token retained | Reuse the same identity. Do not register every turn or after every compaction. If writes actually reject a stale token, use the supported registration/resume flow for your **own server-issued name**, preserving any required proof. A genuine new concurrent session gets its own identity. |
| `INVALID_AGENT_NAME`, proof-gate rejection | Omit a name for first registration. Never invent role names or select an example from documentation. Supply operator-issued `registration_proof` only when required and available; do not fabricate proof or disable the gate. |
| `sender_token` absent/rejected | Read the current schema. Pass the private registration token on writes **that accept `sender_token`**; not every mutation accepts that field. Current send/reply can be unverified when omitted; that is not verified identity. Do not inject unsupported arguments or switch to raw HTTP. |
| Reservation conflicts | Stop editing affected paths, including script/editor routes. A reply that includes a grant **and** an overlapping conflict is still contended. Release unused grants if appropriate, contact the holder in the task thread and switch work. Never convert to non-exclusive merely to get past an exclusive holder. |
| Lease expired / reaper notice | Re-read current files/diffs, recheck conflicts and reserve again before writing. Renew your active IDs with `renew_file_reservations(file_reservation_ids=[...], extend_seconds=1800)` before expiry. A zero renewal/release count is a reconciliation signal, not proof of ownership or successful cleanup. |
| Reservation/send/reply timed out | Delivery/grant is **unknown**, not failed. If a supported `idempotency_key` was included, retry at most once with the **same key and identical arguments** within its retention window. Never change payload under that key (`IDEMPOTENCY_KEY_CONFLICT`), generate a fresh key to replay, or assume a send was not delivered from generic timeout wording. Without a key, reconcile via supported reservation/thread/message reads before deciding whether another write is needed. |
| `Contact approval required`, `CONTACT_REQUIRED` or `CONTACT_BLOCKED` | Confirm recipient/project, request contact once if permitted, then wait while doing other work. An existing thread is appropriate for the same discussion **only if the server permits the reply**; it is not a contact-policy bypass. Do not route through unrelated threads, alternate identities or broad contact-policy changes. |
| Tool returns `isError` / error text in content | Inspect the tool envelope and payload; transport success is not operation success. Do not mark a message sent, lease acquired, or gate passed on a returned error. |
| Tool schema differs / tool unavailable | Discover supported tools/resources or inspect local help. Do not invent `list_agents`, paths, arguments or CLI subcommands. Use supported project roster/resource reads where exposed; unavailable tools are a coverage gap, not permission to inspect the mailbox database. |

### Reservations and shared files

- Use exact files; avoid broad `src/**`, `tests/**`, `.beads/**` leases. Hold
  `.beads/issues.jsonl` only for sync/commit with a short TTL (for example 300s).
- A reservation is **advisory coordination**, not a filesystem lock, exclusive
  Git index, or permission to overwrite existing peer edits. Recheck before
  commit/push when concurrent changes or lease expiry make the snapshot stale.
- Compare `expires_ts` as an offset-aware timestamp against current UTC; do not
  subtract Berlin local clock text from UTC or infer expiry from an old message.
- Do not force-release another agent based on `last_active_ts == inception_ts`.
  A refused force-release is final; recent filesystem/git/mail activity matters.
  Wait for expiry/reaper, get the holder's cooperation, or report the blocker.
- Find IDs in your grant response, the supported reservations resource, or the
  bounded read-only `am file_reservations active` CLI. Never grep the mailbox
  archive or read live SQLite to recover coordination state.
- Escalate a real blocking dependency with file, holder, expiry and task; do not
  wait out a long lease before telling the owner when no useful work remains.
- Build slots were `FEATURE_DISABLED` on this VPS at audit time. Do not enable
  worktrees/features or fire an unawaited acquisition. Coordinate heavy builds
  with relevant peers and follow the project's local/remote build policy.

### Messaging and inbox cursors

- `whois` confirms identity, not availability/ownership. Unknown recipients may
  auto-register placeholders depending on server policy, so never probe by send.
  A plain name is project-local; qualified cross-project recipients need approved
  contact links. Do not mix local and cross-project destinations in one send.
- Treat project-wide mailbox addresses and `broadcast` as broad delivery. Use
  only when scope and authorization justify it; prefer affected named peers.
- Resource URIs may use a **returned project slug**, while tool calls use its
  main absolute path. Discover the resource template; do not guess a slug by
  blindly replacing punctuation. Example only: `resource://agents/data-projects-scry`.
- Initial inbox fetch may omit `since_ts` with a small explicit limit. Fetch
  bodies only for the bounded actionable backlog; do not blindly ack subject-only
  results, read someone else's inbox, or repeatedly request all history.
- `fetch_inbox` normally marks returned messages read; use `mark_read=false` for
  non-consuming checks when supported. `unread_only` does not find already-read
  but unacknowledged messages. Use your overdue/pending-ack view too.
- A full page is not a drained inbox. `since_ts` is strictly newer, and timestamp
  ties can hide messages. Do not advance it to wall-clock now or past an unprocessed
  full page. Use supported pagination or inbox delivery events when available;
  for events, persist `next_cursor` **only after processing**, use `has_more`, and
  never substitute a message ID for an event cursor. Otherwise fetch overlapping
  bounded windows, deduplicate by message ID, and reconcile backlog before
  advancing. If the API cannot enumerate a capped backlog, report the gap instead
  of claiming all mail read. Drain pages as finite work, not an idle polling loop.
- Reply/ack flags can be inherited. Set `ack_required=false` on an informational
  reply when no acknowledgement is needed; avoid acknowledgement ping-pong.

### Shared Git tree

Review `git diff` and `git diff --cached` for your paths before committing.
Stage only your own changes. If unrelated paths are staged, leave them intact;
a path-limited commit still includes **all current content of those paths**, so
coordinate any mixed-file edits first. Never stash, reset, revert, or discard peer
work to manufacture a clean tree. Do not push an accidentally absorbed change
blindly: inspect what landed and coordinate the next step; avoid rewriting history.

Fetch and inspect upstream before pushing. Rebase only when the tree/index is
suitable and the operation is authorized. If `git pull --rebase` refuses peer WIP,
do not use autostash or force cleanup. Preserve it, coordinate, or use a fresh
isolated worktree when appropriate. A verified fast-forward push of your intended
commit can proceed without a rebase; a rejected push needs reconciliation.

## Outage: bounded retry, useful fallback

Retry a failed read **once** after a short pause; writes use the reconciliation
rules above. After continued failure, stop probing every turn. Record affected
tasks, uncertain deliveries/grants and coordination in bead comments or the
project's agreed fallback, keeping secrets out. Continue useful independent work
according to AGENTS.md, but **do not override a known conflict** because mail is
down. Use read-only investigation or a separate fresh patch/worktree if shared
ownership is unclear. Reconcile outstanding mail/leases when service returns.

Do not bypass tools using raw JSON-RPC, CLI writes, a database editor, second
server, or a new port. CLI help and bounded diagnostics below are distinct from
using an alternate transport to repeat a failed mutation.

## Operator diagnostics and recovery

Production on this VPS is the managed user `agent-mail.service`, endpoint
`http://127.0.0.1:8765/mcp/`, archive `~/.mcp_agent_mail_git_mailbox_repo`.
Check local configuration/version rather than treating this as portable setup.
Never hand-launch `am serve-http` / `mcp-agent-mail serve`, use `--takeover`, write
a second unit, bridge ports, kill the PID, or change live client ports to repair
an outage. Two writers on one mailbox are a corruption risk.

For a repair request, gather bounded read-only evidence, then prepare the exact
change and affected service/configs for approval **unless already explicitly
covered by the user's authorization**. Obey stricter project prohibitions. A
routine coding task is not service-restart authority.

```bash
systemctl --user status agent-mail.service --no-pager
systemctl --user show agent-mail.service -p NRestarts -p ActiveEnterTimestamp
ss -ltnp | rg ':8765'
curl -m 10 -fsS -A 'agent-mail-ops-skill' http://127.0.0.1:8765/health
timeout 15s am doctor health
timeout 15s am doctor drain
```

Use the connected `health_check` tool for its structured `verdicts`, contributors,
queue/pool pressure, integrity timestamps and archive lag. `/health` readiness is
liveness, not proof of integrity. Do not raw-curl a tool call when MCP is down.
Bound CLI/network diagnostics; a hung `am mail`/`am robot` can hold activity locks.
Read only the needed journal excerpt; redact config/log secrets before sharing.

| Evidence | Decision |
|---|---|
| Yellow solely from retention, critical verdicts green | Inspect bounded `am doctor reclaim --dry-run` if relevant. No reconstruction/restart. Consolidation can preserve evidence without freeing space; no automatic `--yes`. |
| Timeout with `pool_acquire`, zombie dispatch, no fresh integrity evidence | Availability is degraded; corruption is **unconfirmed**. Historical successful integrity checks do not rule out later corruption. Prepare scoped operator intervention; don't declare the DB clean or rebuild speculatively. |
| `/health` ready but current integrity verdict red | Follow [recovery.md](references/recovery.md) only under authorized operator scope. Verify evidence and archive completeness first. |
| Single client fails while service works | Inspect that client's actual config/session. Claude may use `~/.claude.json`; other harnesses have their own files. Read URLs with credentials redacted, not a filesystem-wide config dump. |
| Manual competing server or crash loop | Identify unit/listener/owner with read-only checks. Ask the owning session/operator; don't kill it or start another listener. |
| Known post-recovery GH#151 pattern | A consistent fresh snapshot, fresh server evidence and working authorized operations may corroborate a false positive. Do not assume every red verdict is that bug or repeat recovery solely for a color. |

Config setup can skip tokenless entries; broad `am setup run` or doctor fix can
rewrite unrelated clients. If configuration repair is authorized, back up exact
files, change only intended URLs, inspect diffs and reconnect affected clients.
Never dump credentials or run bare `am doctor fix`. Updates belong to the existing
managed release path; check version/help and nightly logs, never chase a source
build or reset the tool checkout during a coding task.

Read [recovery.md](references/recovery.md) before any mailbox recovery proposal.
It covers consistent snapshots, drain checks, archive-only data-loss risks,
startup wait bounds and the verification/stop criteria. No live repair is part
of this skill's tests.

## Evidence and tests

[references/evidence.md](references/evidence.md) distinguishes observed skill
loads, broader historical failures, live schema observations and inference.
[tests/scenarios.json](tests/scenarios.json) preserves scenario prompts and
expected decisions. Run `bash scripts/test-all.sh --skill agent-mail-ops` for
static regressions and optional `--live` schema/help checks via the self-test
runner. Missing live infrastructure is reported **not run**, never a live pass.
Independent dry-run answers are useful behavioral evidence, not a statistical
benchmark. Tests never send mail, register probe identities, grant/release leases,
change contacts, or repair the service.
The optional live test uses only HTTP `tools/list` schema discovery with bounded
timeouts and a named User-Agent; it never calls a tool through raw HTTP.
