---
name: cass
description: >-
  Search the user's past Claude/Codex/Gemini coding sessions via the `cass` CLI.
  Use when the user asks to recall prior work — "find that conversation about X",
  "what did I do last week", "search my history for the auth bug", "show recent
  sessions in this repo", or anytime the answer requires context from a previous
  session that isn't in the current conversation. Also handles `cass` health
  diagnostics, index rebuilds, and follow-up file/line lookups.
---

<!-- TOC: TL;DR | Decision Tree | Health Preflight | Real Command Surface | Recipes | Anti-Patterns | Troubleshooting | References -->

# cass — Cross Agent Session Search

> **Premise:** `cass` indexes your local AI coding-agent session files (`~/.claude/projects`, `~/.codex/sessions`, etc.) into SQLite + Tantivy. The CLI is robot-friendly: every command has a `--json`/`--robot` mode and a stable schema. **Use the CLI; do not query the SQLite DB directly** — the schema isn't a stable contract and you'll miss ranking, snippet generation, and the ergonomics that already exist.

## When to reach for this skill (active-project use)

Agents should pull cass into the *current* task, not just retrospectively. The five high-value moments:

1. **Session prime** — picking up a project after a gap (a day, a week, a context-compact). Run §Recipe #0 before doing anything else.
2. **"Have I solved this before?"** — symptom matches something familiar; spend 10 seconds checking before re-deriving.
3. **Cross-project transfer** — implementing X for the first time in this repo; you've done it elsewhere. Find the prior work and lift the pattern.
4. **Onboarding/handoff** — explaining what was tried, what failed, what the trade-offs were. Sessions remember rationale that commits don't.
5. **Recurrence detection** — "is this the third time I've hit this?" → file a real fix instead of patching again.

In all five, the answer to "should I search?" is yes, and the cost is one short command. The skill makes that command cheap and habitual.

---

## TL;DR — fastest correct path

```bash
# 1. Preflight (1 line, <100ms)
cass health --json | jq -r '.recommended_action // "ready"'

# 2. Search — token-cheap, agent-friendly defaults
cass search "your query" --robot --limit 10 --fields summary --max-content-length 200

# 3. Drill in on a hit
cass view  <source_path> -n <line>            # 5 lines context
cass expand <source_path> --line <line> -C 5  # ±5 messages around the hit
```

If you only do those three, you'll be right 90% of the time.

---

## Decision Tree

```
What does the user want?
│
├─ "Recall a past session / what did I do"
│   → Search recipe (§Recipes #1)
│
├─ "List recent sessions in this project"
│   → cass sessions --current --json   (or --workspace <path> --limit N)
│
├─ "Overview / counts / breakdown"
│   → Aggregate recipe (§Recipes #2) — `--aggregate agent,workspace,date`
│
├─ "Show activity over time"
│   → cass timeline --since '-7d' --json
│
├─ "cass is broken / no results / index rebuilding"
│   → Health & repair recipe (§Troubleshooting)
│
└─ "Resume that conversation in <agent>"
    → cass resume <session-path>   (returns the harness command)
```

---

## Health Preflight — DO THIS FIRST

The index can be **rebuilding**, **stale**, **missing**, or **healthy**. Searching a broken index returns 0 results with a stderr warning that's easy to miss. Always check first:

```bash
cass health --json
# {"status":"rebuilding"|"healthy"|"unhealthy","healthy":bool,"recommended_action":"...",...}
```

Authoritative fields (per `cass robot-docs guide`):
- `recommended_action` — if non-null, **show it to the user and follow it before searching**.
- `status` — `healthy` / `rebuilding` / `unhealthy`.
- `state.index.rebuilding` — true while a rebuild is in progress (search will be lexical-only or empty).

When `status == "rebuilding"`:
- Don't bypass to SQLite. Don't loop and retry hard.
- Add `--mode lexical` to your search — it often still works because lexical assets are written incrementally.
- Or wait: `cass status --json | jq '.rebuild.processed_conversations, .rebuild.total_conversations'` (run twice to estimate ETA).

When `status == "unhealthy"` AND `recommended_action` mentions `--fix`:
```bash
cass doctor --fix      # rebuilds derived data only; never deletes user sessions
```

---

## Real Command Surface (verified against `cass --version`)

Run `cass capabilities --json` once to see what your local binary supports — feature names below match the `features` array.

### Search & navigation
| Command | Use it for |
|---|---|
| `cass search "<q>" --robot` | Default: search everything, JSON output |
| `cass search "<q>" --robot --aggregate agent` | Counts by field — **99% token reduction** vs full results |
| `cass search "<q>" --robot --fields summary` | `path,line_number,agent,title,score` only |
| `cass search "<q>" --robot --max-content-length 200` | Cap each snippet (UTF-8 safe; adds `_truncated` indicator) |
| `cass search "<q>" --robot --robot-meta` | Adds `elapsed_ms`, mode used, fallback reason — **use when results are surprising** |
| `cass search "<q>" --robot --explain` | Show parsed query + cost estimate |
| `cass search "<q>" --robot --dry-run` | Validate without executing |
| `cass search "<q>" --robot --mode lexical` | Force BM25 (works while semantic/index is rebuilding) |
| `cass sessions --current --json` | Best match for current cwd |
| `cass sessions --workspace <path> --json --limit 20` | Recent sessions for a project |
| `cass view <source_path> -n <line> [-C N]` | Read N lines around a search hit |
| `cass expand <source_path> --line <line> [-C N]` | Read N messages around a search hit (better for transcripts) |
| `cass timeline --since '-7d' --json` | Activity over a time range |
| `cass resume <source_path>` | Print the harness command to resume that session |
| `cass export <source_path> --format markdown` | Convert a session to markdown |

### Filters that work on `search` and `timeline`
| Flag | Notes |
|---|---|
| `--agent <slug>` | repeatable (e.g. `--agent codex --agent claude_code`) |
| `--workspace <path>` | repeatable |
| `--source local|remote|all|<host>` | for multi-machine setups |
| `--today` / `--yesterday` / `--week` | shortcuts |
| `--days N` | last N days |
| `--since <when>` / `--until <when>` | ISO date `YYYY-MM-DD`, keyword (`today`/`yesterday`/`now`), or relative `'-7d'`/`'-24h'`/`'-30m'`/`'-1w'` (quote it) |

### Output controls (search)
| Flag | Effect |
|---|---|
| `--limit N` | Default 0 = no cap (auto-clamped to RAM-proportional ceiling) — **set this** for token control |
| `--offset N` / `--cursor <c>` | Pagination |
| `--max-tokens N` | Soft token budget (≈ 4 chars / token) |
| `--robot-format json|jsonl|compact|sessions|toon` | `sessions` = one source_path per line — pipe into another `cass search --sessions-from -` |
| `--display table|lines|markdown` | Human-readable formats |
| `--highlight` | `**bold**` markers around matched terms |
| `--fields <list>` or `minimal`/`summary` preset | Token control |
| `--request-id <id>` | Echoed in `_meta` for log correlation |

### Health & maintenance
| Command | Use it for |
|---|---|
| `cass health --json` | <50ms readiness probe (preflight) |
| `cass status --json` | Full state: rebuild progress, semantic readiness, DB counts |
| `cass diag --json` | Versions, paths, platform |
| `cass doctor --json` | Diagnostic checks; safe by default |
| `cass doctor --fix` | Rebuild derived data (preserves source sessions) |
| `cass doctor --force-rebuild` | Force lexical rebuild |
| `cass index` / `cass index --full` / `cass index --watch` | Manual / full / live reindex |
| `cass stats --json` | Conversation/message counts |
| `cass sources agents list --json` | List indexing exclusions |

### Robot docs (machine-readable instructions)
```bash
cass robot-docs <topic>
# topics: commands env paths schemas guide exit-codes examples contracts wrap sources analytics
```
When in doubt, `cass robot-docs guide` or `cass robot-docs examples` is the fastest unblock.

---

## Recipes — paste & adapt

### 0. Session prime (run at the start of an active-project task)

When the user kicks off work in a project — *especially* after a gap — these three calls give you ~80% of the prior context for the cost of ~500 tokens:

```bash
# (a) Most recent session in this cwd — picks up where you left off
cass sessions --current --json --limit 1 | jq '.sessions[0] | {path, agent, modified, title, message_count}'

# (b) What's been touched in this project lately (counts, no content)
cass search "*" --robot --workspace "$(pwd)" --aggregate date --week | jq '.aggregations'

# (c) Pull recent activity around the topic you're about to work on
cass search "<topic from user's prompt>" --robot --workspace "$(pwd)" --week \
  --limit 5 --fields summary --max-content-length 200 \
  | jq '.hits[] | {agent, source_path, line_number, snippet: .snippet // .content[:200]}'
```

Then drill into the most relevant hit with `cass view` / `cass expand` (recipe #1). Don't summarize the prime back to the user — they know their own history; just use it to make better suggestions.

### 1. Recall a past session
```bash
cass search "auth bug retry logic" --robot --limit 10 --fields summary --max-content-length 200 \
  | jq '.hits[] | {score, agent, source_path, line_number, snippet: .snippet // .content}'
```
Then drill into the top hit:
```bash
cass view "<source_path>" -n <line_number> -C 10
# or for transcripts (multi-message context):
cass expand "<source_path>" --line <line_number> -C 5
```

### 2. Overview without spending tokens (the aggregate trick)
```bash
# How many sessions touched X, broken down by project?
cass search "stripe webhook" --robot --aggregate workspace
# Multi-field
cass search "*" --robot --aggregate agent,date --week
```
Use this **before** a wide search so you know whether to scope or pivot.

### 3. Recent sessions in this repo
```bash
cass sessions --current --json --limit 20
# OR explicit:
cass sessions --workspace "$(pwd)" --json --limit 20
```

### 4. Time-window search
```bash
cass search "regression" --robot --since '-14d' --limit 10 --fields summary
cass search "fixed"      --robot --today --agent codex
```
**Quote relative offsets** (`'-7d'`) — without quotes the shell will mistake the dash for a flag in some pipelines.

### 5. Chained search (intersection)
```bash
# Sessions that mention "playwright", then within those, find "flaky"
cass search "playwright" --robot --robot-format sessions \
  | cass search "flaky" --robot --sessions-from -
```

### 6. Two-phase exploration (cheap → focused)
```bash
# Phase 1 — counts only (tiny output)
cass search "deploy" --robot --aggregate agent,workspace --week

# Phase 2 — narrow + read
cass search "deploy" --robot --workspace /data/projects/scry --limit 5 --fields summary
```

### 7. Force lexical when semantic is unavailable
```bash
cass search "<q>" --robot --mode lexical --robot-meta
# Inspect _meta.search_mode and _meta.fallback_reason
```

### 8. Resume a prior session in another agent
```bash
sp=$(cass sessions --current --json --limit 1 | jq -r '.sessions[0].path')
cass resume "$sp"   # prints the resume command for the source's native harness
```

> **Note on JSON shape:** `cass sessions --json` returns `{ "sessions": [ { "path", "workspace", "agent", "title", "modified", "size_bytes", "message_count", "human_turns", ... } ] }`. The session file path is `.path` (not `.source_path` — that's what `cass search` uses for hits).

---

## Anti-Patterns — DO NOT do these

These came from real session logs. The skill exists to keep them from happening again.

### A1. Bypassing cass to query SQLite directly
**Symptom:** running `sqlite3 ~/.local/share/coding-agent-search/agent_search.db "SELECT ..."`
**Why it's wrong:** schema isn't a stable contract; you lose ranking, snippets, robot envelope, mode-aware fallback, and lose ability to roll forward when cass changes.
**Correct:** `cass search` with appropriate filters. If you genuinely need raw counts, use `cass stats --json` or `cass search '*' --aggregate <field>`.

### A2. `cass search robot "<query>"`
**Symptom:** `Could not parse arguments` (exit 2).
**Cause:** `robot` is not a subcommand. The flag is `--robot` (alias of `--json`).
**Correct:** `cass search "<query>" --robot`.

### A3. Ambiguous time arguments
**Correct:** prefer `--days 7` (least ambiguous), `--week`, ISO `--since 2026-04-01`, or quoted `--since '-7d'`. Don't rely on bare `--since=7d` — it works on current cass but is brittle across wrappers/versions.

### A4. Forgetting `--limit` and `--max-content-length`
**Symptom:** 50k-token search response that blows context. The default `--limit 0` means "no limit" — clamped only by RAM.
**Correct:** always set `--limit 10` (or smaller) and `--max-content-length 200` for agent use.

### A5. Reading 0 results as "nothing exists"
**Symptom:** "I checked cass and there are no past sessions about X."
**Cause:** index is rebuilding, semantic embedder is missing, or query too narrow. The stderr warning is easy to miss.
**Correct:** rerun with `--robot-meta` and inspect `_meta.search_mode` / `_meta.fallback_reason` / `_meta.fallback_tier`. If rebuilding, retry with `--mode lexical` or wait.

### A6. Searching when the index is broken
**Symptom:** 0 hits, weird latencies, repeated stderr warnings about missing index.
**Correct:** `cass health --json` first. If `recommended_action` mentions `cass doctor --fix` or `cass index --full`, show it to the user and run it (with permission).

### A7. Reading entire session JSONL files for context
**Symptom:** `Read` tool on a 10MB session file.
**Correct:** `cass view <path> -n <line> -C 10` (file lines) or `cass expand <path> --line <line> -C 5` (whole messages).

### A8. Ignoring the `--aggregate` superpower
**Symptom:** Asking "how many times did agents hit X?" by paginating full hits.
**Correct:** `cass search "X" --robot --aggregate agent,workspace,date`. This is server-side and tiny.

### A9. Calling `cass tui` from an agent
**Symptom:** session hangs.
**Cause:** `cass tui` is interactive (Bubble-Tea-style); non-TTY agents can't drive it.
**Correct:** never. Use `cass search` / `cass sessions` instead.

### A10. Inventing flags / subcommands
**Don't exist:** `cass robot search ...`, `cass --query ...`, anything with a TUI in agent mode.
**Verify what does exist:** `cass capabilities --json` and `cass robot-docs commands`.

---

## Troubleshooting

### "Tantivy search index not found" warning on stderr
Index hasn't been built or was deleted. Run:
```bash
cass index --full
# Watch progress in another shell:
cass status --json | jq '.rebuild'
```

### `cass search` returns 0 hits but you know there's data
1. `cass health --json` — index status?
2. `cass stats --json` — conversations indexed > 0?
3. `cass search "<q>" --robot --robot-meta` — read `_meta.fallback_reason`
4. Try `--mode lexical` and a broader query (e.g. shorter terms, no quotes)
5. Try `cass search "*" --aggregate workspace` to confirm data exists

### Exit codes (per `cass robot-docs exit-codes`)
| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | health-failed |
| 2 | usage error (you passed bad args) |
| 3 | missing index/db |
| 5 | data-corrupt |
| 7 | lock/busy (try again) |
| 15 | semantic/embedder unavailable (retry with `--mode lexical`) |

For codes ≥ 10, branch on `err.kind` (kebab-case string in JSON envelope), not the numeric code.

---

## References

| File | When to open |
|---|---|
| [RECIPES.md](references/RECIPES.md) | More copy-paste recipes (chained, scoped, time-window, multi-source) |
| [PITFALLS.md](references/PITFALLS.md) | Detailed pitfalls catalog with diagnose/fix |
| [SELF-TEST.md](SELF-TEST.md) | Failure-case tests tied to CASS session logs |

If you're ever stuck, run `cass robot-docs examples` and `cass robot-docs guide` — they're authoritative and current.

---

## Provenance of this skill

Be honest with yourself about where each rule came from:

- **Grounded in observed agent failures (CASS sessions 437/473/474/665/679/1270):** A1 (sqlite bypass), A2 (`cass search robot "<q>"`), A6/P6 (broken-index searches), A9/P7 (`cass tui` hangs), P10 (`cass health` vs `status` confusion). The historical CASS record is mostly *agents fixing cass itself*, not *agents using cass*; deep tool-debugging guidance has been intentionally left out — this skill is for using cass, not repairing it.
- **Grounded in this skill's own author's recent usage (the immediately prior CASS rewrite session):** A1 (sqlite bypass — I did this), A4 (no `--limit`/`--max-content-length` — I did this), A8 (skipping `--aggregate` — I did this), A7 (reading whole JSONL — I did this), the §"When to reach for this skill" framing.
- **Extrapolated from the binary + `cass robot-docs`:** the recipe specifics, JSON shapes, exit-code mappings, time-window semantics. Self-test verifies these against the live binary.

If you find a usage failure mode the skill doesn't catch, treat that as a contribution back, not a failure of the skill — add it to PITFALLS.md with a session ID or a reproducer, then add a check to `scripts/self-test.sh`.
