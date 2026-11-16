# Agent Mail in past sessions: evidence

Source: `cass` over Claude Code and Codex sessions on this VPS (2026-11-16): about 115 events
read in context across 12 projects, split into incidents (23), identity and messaging (about 45)
and reservations and coordination (about 45). Session references are shortened: `C:<project>
<id>` is a Claude Code session under `~/.claude/projects/`, `X:<date> <id>` a Codex rollout under
`~/.codex/sessions/2026/`. Line numbers are cass message indices (`cass expand --message-index`).

## Live checks against the server (2026-11-16, am 0.3.40)

| Check | Result |
| --- | --- |
| `health_check` | `health_level` yellow from `retention` only (about 242 GB resident, mostly staging); 44 projects, 786 agents; all critical verdicts green |
| `check_file_reservation_conflicts` | Read-only; returns `conflict_free`, `conflicts`, `own_active`, `clear_paths` |
| `acquire_build_slot` | `FEATURE_DISABLED`: "Build slots are disabled. Enable WORKTREES_ENABLED to use this tool." |
| `send_message` to an unconfirmed name (`BlueLake`) | **Delivered.** `whois BlueLake` then showed an agent created the same second with program and model `unknown`: sending to an unknown name auto-creates a placeholder. (This probe created that placeholder; the older "recipients are not registered" error in the logs is from earlier builds.) |
| `whois` on a missing name | `AGENT_NOT_FOUND`: "Agent '<name>' not found in project '<slug>'" |
| `am serve-http --help` | Refuses while a live server answers the same host:port; `--takeover` kills it |
| `am doctor drain`, `am doctor health`, `am doctor reclaim` (no `--yes`), `am agent start`, `am file_reservations conflicts`, `am acks pending` | Read-only by their help text |

## Using Agent Mail

| Problem | Count | Examples |
| --- | ---: | --- |
| Duplicate and orphan identities: retried registrations after timeouts, a new identity every session | 12 events; about 790 agents on the server | C:twenty-multi-pipeline a037c201 (1 macro + 9 register calls); C:rusty-manus 24b2aa16 (timed-out calls landed, `retire_agent` then needed the lost token); C:philomena-agent 822561a0 (memory file tracking renamed identities) |
| Sending to unregistered, made-up or doc-example names | 6 | X:03-07 (BlueLake not registered); X:05-06 (`Invalid agent name 'Pascal'`, then BlueLake) |
| "Contact approval required" blocking a first message | 36 sessions | X:05-21 (then `request_contact` hit "Resource is temporarily busy") |
| Choosing a name: `INVALID_AGENT_NAME` | several | C:csv-mcp 0ee3eed6 (SlateHarbor rejected); X:05-23 (`CodexReadOnly`) |
| Lost or unknown `sender_token`, 403 on writes | 6 | C:rusty-seo fe22493e, c948cef3 |
| One identity shared by sessions through memory | 3 | C:philomena-agent 822561a0, e049b4b5 |
| Inbox polling | 4 sessions | X:04-10 (103 `fetch_inbox` calls with bodies, no `since_ts`) |
| Project key / URI confusion; raw curl or SQLite as a workaround | 6 | X:03-06 (`resource://agents//data/...` unknown, slug works); X:05-23 (curl JSON-RPC); X:05-22 (SQLite reads) |
| Acks rare | about 1 per 9 sends | about 3,500 `send_message`, 400 `acknowledge_message`, 0 `macro_prepare_thread` |
| Reading another agent's inbox | 1 | X:05-23 |
| Editing despite a conflict | 4 | X:05-21 019e479b (node script edited `.beads/issues.jsonl` after a refused force-release); X:05-19 019e422f ("advisory only") |
| Force-release refused, from the `last_active_ts == inception_ts` heuristic in one project's AGENTS.md | 14 calls, 6 sessions | X:03-13 019ce929; X:05-12 019e19ed (the "dead" holder registered 23 s earlier) |
| Grepping the mailbox archive for reservation ids | 8 sessions | X:03-06 019cc342 (6 turns, then gave up) |
| `.beads/issues.jsonl` held exclusively for 1 to 2 hours | about 8 | X:05-21 019e479a; X:05-15 019e2bef (`.beads/**`, 7200 s) |
| Releasing nothing (`released: 0`): never reserved | about 10 | X:03-05 019cc020; C:scry d72a5f4c |
| Globs too broad (`src/**`, `tests/**`) | about 6 | C:rusty-jev 06c74ad3; X:03-06 019cc342 |
| Shared-tree git races (stash swept a peer's work, commits absorbing changes) | about 10 | C:scry 48ca26aa, 6fd0698b; C:arp-astro 32a14566 |
| Build slots disabled, call fired and not awaited | 3 of 3 | C:rusty-jev 06c74ad3; X:05-23 019e5278 |

**Done well (now official steps):** messaging the holder in the bead thread and switching work on
a conflict (9 cases); staging only your own hunks; checking peers' pushes before rebasing;
re-reserving after an expiry or reaper notice; `resolve_pane_identity` with an explicit
`pane_id`; reusing a server-issued name to resume (same id, new token); falling back to bead
comments when Agent Mail was down.

## Fixing Agent Mail

| Problem | Sessions | Examples |
| --- | ---: | --- |
| Servers on random ports, configs pointed at them, a node TCP bridge | 7 | C:scry c1198dba, b02bcf84; C:rusty-seo 53cca603 (unit crash-looped 1181 times on the taken port); X:05-23 (bridge 36569 to 8765) |
| Manual restarts and kills, manual server launch, a second hand-written unit | 6 (all before the skill) | X:05-06 (manual `am serve-http` stopped the managed server; health went red); C:acfs 66f863ba (killed 5 times) |
| Wedged or saturated server (`pool_acquire` timeouts, zombie dispatch, `/health` hangs) | 4 (after the skill) | C:rusty-manus 24b2aa16, 73ff61da; C:csv-mcp 93a216a8 (systemd restart, self-heal about 2 min), 0ee3eed6 |
| Probing every turn instead of retry once then proceed | 4 | X:05-22 (about 15 and 12 probes) |
| Live SQLite opened or written | 4 | X:05-06 (`pragma wal_checkpoint` on the live DB); `-home-ubuntu` b3af630f (row deletes restored by the archive) |
| Stale `am` CLI processes holding the activity lock | 3 | C:rusty-seo 53cca603 (11-hour-old `am mail send`) |
| Bare `am doctor fix` | 2 | b3af630f, C:acfs 66f863ba |
| Chasing a source build for an up-to-date binary | 1 (about 50 messages) | C:rusty-seo 53cca603 |
| Recovery step errors: copy without `-wal`; red verdict from GH#151 after a good recovery | 1 | C:csv-mcp 93a216a8 |

After the original skill existed, every agent asked before restarting the service
(C:csv-mcp 93a216a8, C:philomena-agent efd2ae80, C:cunk-agent 12db6887, C:rusty-manus 24b2aa16).
