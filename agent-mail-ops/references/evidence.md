# Agent Mail audit evidence

## Follow-up audit: 2026-11-16

The follow-up examined actual skill launches/reads separately from catalogs,
authoring sessions and general Agent Mail usage. CASS health reported lexical
ready with semantic assets catching up; all searches used lexical mode. Nothing
was repaired/reindexed, and the mailbox database was never opened.

### Search scope and completeness limits

- `agent-mail-ops`: 111 metadata/content hits across 20 session paths.
- `"agent mail"` and `"agent_mail"`: 13,074 metadata hits across 453 session
  paths each (normalization gives the same broad usage set, not independent sets).
- `"agent mail" AND skill`: 494 metadata hits across 225 session paths; content
  search returned 343. All 151 missing hits were expanded individually with zero
  failed expansions. They added no explicit skill loads.
- `mcp_agent_mail/SKILL.md`: searched separately to catch upstream documentation
  reads, not only the shared skill's name. Its home-directory authoring session
  reads a different upstream skill; it is not counted as a shared-skill launch.
  The moving index returned 350 metadata hits versus an earlier 197 content hits;
  all 153 differences were expanded, with zero failures and no extra load markers.

All four explicit `Launching skill: agent-mail-ops` events and four direct shared
skill reads were expanded with 35 messages of surrounding context. Four of the
eight are authoring/cold-review activity, not independent operational adoption.
The relevant upstream read was expanded separately. This is all identifiable
shared-skill load evidence in these indexed search results, not proof of every
possible skill use: transcripts may omit load markers, current sessions can
postdate the index, and broad tool mentions do not prove skill invocation.

A broader OR workflow query returned 2,985 of 195,606 matches and did not reliably
respect the intended session restriction. It was **not** used as an exhaustive
count or the basis of claims about skill usage. Exact load markers plus bounded
expansion supplied the primary evidence instead.

Current CASS coordinates are message ordinals: use `cass expand <source_path>
--message-index <N> --conversation-id <ID> -C <context> --json`, obtaining the
conversation ID from search results. Do not use a physical JSONL line number.
Local research artifacts are `/tmp/am-skill-hits.json`,
`/tmp/am-skill-content.json`, `/tmp/am-load-expansions.json`,
`/tmp/am-skill-alias-summary.json`, `/tmp/am-alias-recovered.json`, and
`/tmp/am-upstream-expansion.json`; they are not required runtime files.

### Explicit shared-skill use

Source paths below use the prefix `/home/ubuntu/.claude/projects/`.

| Session suffix | Load message | Evidence checked |
|---|---:|---|
| `-data-projects-rusty-manus/24b2aa16-8a7b-49d9-ba5f-c6b153e79aa2.jsonl` | 135 | Pool-acquire timeouts at 129-131 and 161; bounded diagnostic need. Repeated failures did not establish that mutations had failed. |
| `-data-projects-csv-mcp/93a216a8-2eac-4dfb-9096-ed8ea3c40b89.jsonl` | 2097 | 2087 inferred a timed-out message was not sent. 2108 called the DB not corrupt from earlier checks; 2114 dismissed snapshot errors as a copy artifact; 2123 reversed the diagnosis after startup checks confirmed corruption. 2125-2131 used a bounded background readiness wait and independent work: useful practice retained. |
| `-data-projects-rusty-manus/73ff61da-e028-416a-9e1a-a51a9d542cd8.jsonl` | 573 | Replaying queued mail while service was degraded; loaded skill and performed read-only triage at 575. Add uncertain-delivery reconciliation and idempotent retries rather than assuming unsent. |
| `-data-projects-philomena-agent/efd2ae80-f71a-410e-96e2-a47c19a3b12c.jsonl` | 131 | At 119 preserved a peer's live changes and delivered a separately tested patch when reservation checks failed. Good isolation/work fallback retained, not permission to override known ownership. |
| `-data-projects-cunk-agent/aa48c08f-3262-4799-9e90-936ec13d5936.jsonl` | 123 | Direct skill read in recovery/authoring session; 126 reads its self-test. Distinguish maintenance of guidance from ordinary use. |
| `-data-projects-rusty-jev/5f3d3411-8898-40e8-949a-31cf4b13f4e1.jsonl` | 6494 | Prior authoring audit; secondary incident reports are preserved below with their original approximate counts. |
| Same session, `/subagents/agent-a1e511153d4d6ce76.jsonl` | 2 | Prior cold test repeated the unsafe recent-program/model identity adoption and unrelated-thread contact workaround. |
| Same session, `/subagents/agent-a27322f2d54a69686.jsonl` | 2 | Prior cold test guessed nonexistent `list_agents` and followed registration-after-compaction guidance. Current schemas/discovery and valid-identity reuse replace those guesses. |

Additional upstream read: `-home-ubuntu/5152a22a-1111-4173-a2eb-6d4cc17f7053.jsonl`,
134 (`/home/ubuntu/mcp_agent_mail/SKILL.md`), with review at 139. It records mixed
grant/conflict handling and UTC/local expiry confusion, but promotes archive
grepping and activity-based force-release heuristics. Keep the first lessons,
reject the latter as unsupported shortcuts. Historical audit prose is secondary
evidence, not new operational outcomes.

### Changes and regression mapping

The baseline suite passed **66 checks** despite these gaps. It checked prose
needles, CLI help and tool names, not argument schemas or behavioral correctness.

| Gap | Revised guidance and regression case |
|---|---|
| Adopt a recent identity by program/model; register again after compaction | Proven session ownership only, reuse valid identity (`registration-timeout-ambiguous`, `compaction-valid-identity`) |
| Generic retry after a timed-out mutation | Unknown outcome, supported same-key identical retry or reconciliation (`reservation-timeout`, `message-timeout`) |
| Clear precheck treated as sufficient or grant hides conflicts | Inspect both arrays; no atomic lock assumption (`mixed-grant-conflict`) |
| Old thread used to avoid contact approval | No unrelated-thread routing; request contact once (`contact-old-thread`) |
| Full inbox page and timestamp ties silently dropped; ack without bodies | Bounded backlog drain, event cursor discipline, read before ack (`inbox-full-page`) |
| Historical integrity success used as current clean bill of health | Fresh structured evidence; retain uncertainty (`stale-health`) |
| Live DB/WAL/SHM copies treated as consistent | Stable snapshot or supported backup; quiesce/drain before offline mutation (`inconsistent-copy`) |
| Archive-only reconstruction forced after refusal | Assess DB-only messages; preserve salvage and stop on coverage uncertainty (`retention-and-archive-gap`, `archive-rebuild-refusal`) |
| Rebase advice assumes clean shared tree | Preserve peer WIP, no autostash, conditional fast-forward (`shared-wip-rebase`) |
| Mail outage overrides known holder | Independent work/fallback only (`outage-known-holder`) |
| Blanket sender-token arguments, guessed tool names | Current schema, supported fields (`token-schema`) |
| Placeholder sends, force release, zero-result assumptions | Read-only discovery and lease reconciliation (`wrong-recipient`, `force-release-heuristic`, `release-zero`) |
| Unbounded waits or repeated restarts | Overall deadline plus per-request bounds (`startup-not-ready`) |

These cases are stored in `tests/scenarios.json`. Static checks verify the named
guidance remains present; they do **not** prove agents follow prose. Independent
old/new dry runs use the first 12 scenarios, with no live workflow actions. The
baseline reviewer found unsafe/underspecified advice on identity, retries,
contacts, inbox pagination, snapshots and shared-WIP rebase. The revised reviewer
selected the intended safe action and stop condition in all 12. This is one
qualitative run per version, not a statistical benchmark or adversarial proof.

### Current schema observations and test scope

Connected tool metadata now exposes `idempotency_key` on send/reply/reserve,
`mark_read` and ack-backlog filters on inbox fetch, and durable inbox event
cursors. Sender-token fields are not present on every mutation. Those are
current contract observations, not claims that all historical versions had them.
One necessary real session identity and exact skill-file leases were created for
this task; no dummy recipient or message was created. `health_check` showed
retention-only yellow with critical verdicts green. No repair was performed.

The replacement self-test keeps frontmatter/link checks, adds 18 failure-case
regressions and JSON/SSE/error/incomplete-schema parser checks. Optional `--live`
checks current argument schemas and bounded CLI help. Unavailable live checks
are not silently passed. Tests never register agents, send mail, acquire/release
leases, change contacts, or mutate the service. Only `tools/list` introspection
uses HTTP, with a named User-Agent and timeout; it is not a tool-call fallback.

Validation performed: all 18 static scenario checks and four unittest methods
passed; live argument-schema checks passed for 14 tools and six bounded CLI
version/help probes. No tests executed the hypothetical workflow actions.
Old/new dry-run outputs and a generated review page are retained locally under
`/data/tmp/agent-mail-ops-eval-20261116/`. Its viewer's `without_skill` folder is
explicitly labeled as the **old skill baseline**, not a no-skill control.

UBS 5.5.26 scanned `scripts/test_skill.py` and `scripts/self-test.sh` against HEAD:
exit 0, zero criticals, two warnings and three informational notes. The warnings
(`py.parsing.json-loads-no-try`) concern fixture JSON at line 14 and SSE JSON at
line 27: malformed fixtures should fail setup; malformed SSE should raise and
fail the live check, as the parser tests verify. Neither is swallowed as success.
The three `py.functions.missing-returns` notes concern `decode_tools` (explicit
return or raise), `test_frontmatter_and_links` and `test_failure_case_guidance`
(unittest methods intentionally return None). No suppressions were added.
Markdown and JSON fixtures were reviewed/parsed separately; UBS does not validate
the prose. These were reviewed warnings, not a zero-finding claim.

## Prior audit (historical approximate counts, not fresh measurements)

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
| Duplicate and orphan identities: repeated nameless registrations within a session or after timeouts | 12 events; about 790 agents on the server (roster size alone does not prove duplicates) | C:twenty-multi-pipeline a037c201 (1 macro + 9 register calls); C:rusty-manus 24b2aa16 (timed-out calls landed, `retire_agent` then needed the lost token); C:philomena-agent 822561a0 (memory file tracking renamed identities) |
| Sending to unregistered, made-up or doc-example names | 6 | X:03-07 (BlueLake not registered); X:05-06 (`Invalid agent name 'Pascal'`, then BlueLake) |
| "Contact approval required" blocking a first message | 36 sessions | X:05-21 (then `request_contact` hit "Resource is temporarily busy") |
| Choosing a name: `INVALID_AGENT_NAME` | several | C:csv-mcp 0ee3eed6 (SlateHarbor rejected); X:05-23 (`CodexReadOnly`) |
| Lost or unknown `sender_token`, 403 on writes | 6 | C:rusty-seo fe22493e, c948cef3 |
| One identity shared by sessions through memory | 3 | C:philomena-agent 822561a0, e049b4b5 |
| Inbox polling | 4 sessions | X:04-10 (103 `fetch_inbox` calls with bodies, no `since_ts`) |
| Project key / URI confusion; raw curl or SQLite as a workaround | 6 | X:03-06 (`resource://agents//data/...` unknown, slug works); X:05-23 (curl JSON-RPC); X:05-22 (SQLite reads) |
| Acknowledgement volume (requirement rate unknown) | about 1 per 9 sends; not an omission rate without ack_required counts | about 3,500 `send_message`, 400 `acknowledge_message`, 0 `macro_prepare_thread` |
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

In the prior audit's four cited examples, agents asked before restarting the service
(C:csv-mcp 93a216a8, C:philomena-agent efd2ae80, C:cunk-agent 12db6887, C:rusty-manus 24b2aa16).
