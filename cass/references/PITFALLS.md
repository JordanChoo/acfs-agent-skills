# cass Pitfalls

Each entry: **symptom → cause → diagnose → fix.** Drawn from real CASS sessions (where agents debugged or used `cass`).

---

## P1 — Bypassing cass and querying SQLite directly

**Symptom:** Agent runs `sqlite3 ~/.local/share/coding-agent-search/agent_search.db "SELECT ..."` and reads/parses raw rows.

**Why bad:**
- Schema isn't a stable contract — breaks across cass versions
- Loses ranking, snippet generation, robot envelope, fallback handling
- No `--robot-meta` to explain why hits are empty
- Misses sources/excludes config

**Diagnose:** look at any prior `Bash` call with `sqlite3` against `agent_search.db`.

**Fix:** use `cass search` (with appropriate filters/aggregations). For raw counts, use `cass stats --json`. For aggregations, `cass search '*' --aggregate <field>`.

---

## P2 — `cass search robot "<query>"` (positional `robot`)

**Symptom:** `Could not parse arguments` (exit 2).

**Cause:** Treating `robot` as a subcommand. It's a *flag* (`--robot`, alias of `--json`), and the query is the positional arg.

**Fix:**
```bash
cass search "<query>" --robot
```

---

## P3 — Time-window flags: pick the safest form

**Symptom (older cass):** "expected ISO date" with bare `--since=7d`. The pre-0.4 binary required ISO dates only.

**Modern cass (≥ 0.4):** accepts ISO dates, keywords (`today`, `yesterday`, `now`), and relative offsets (`-7d`, `-24h`, `-30m`, `-1w`). The dash-prefixed offset works without quotes thanks to `allow_hyphen_values`.

**Recommended forms (in order of robustness):**
```bash
--days 7              # cleanest for "last N days"
--week                # shortcut for last 7 days
--since 2026-04-01    # ISO date — most explicit
--since '-7d'         # quoted relative offset — safe across pipelines/wrappers
--since today --until now
```

**Avoid mixing**: don't use `--since=7d` (no dash) in scripts you share, since older binaries reject it and there's no portable signal that the value was silently misinterpreted. If you have to support both, prefer `--days N`.

Quote relative offsets in pipelines (`'-7d'`) so a downstream argv parser doesn't interpret the dash as a flag prefix.

---

## P4 — No `--limit` and no `--max-content-length`

**Symptom:** Single search response is 30k+ tokens; agent context bloated.

**Cause:** Default `--limit 0` means "no cap" (only RAM-clamped).

**Fix:** for any agent-driven search, *always* include:
```bash
--limit 10 --fields summary --max-content-length 200
```
Or for overview-only queries, `--aggregate <field>` instead of full hits.

---

## P5 — Reading 0 hits as "nothing exists"

**Symptom:** "I checked cass; there's nothing about X" but the user knows there is.

**Causes (in priority order):**
1. Index is rebuilding → `cass health --json` shows `"status": "rebuilding"`
2. Semantic embedder unavailable → falls back to lexical-only; results may be different
3. Query too narrow — over-quoted or rare token
4. Agent excluded → `cass sources agents list --json`

**Diagnose:**
```bash
cass health --json | jq -r '.status, .recommended_action'
cass search "<q>" --robot --robot-meta | jq '._meta'
cass stats --json | jq '.conversations, .messages'
```

**Fix:** retry with `--mode lexical`, broaden the query, drop quotes, or wait for rebuild.

---

## P6 — Searching during index rebuild without knowing

**Symptom:** Slow / empty results, stderr warnings about "Tantivy search index not found".

**Diagnose:** `cass health --json | jq -r .status` shows `"rebuilding"`.

**Fix options:**
- Best: `cass search "<q>" --robot --mode lexical` — often still works on partial assets
- Wait: `cass status --json | jq '.rebuild'` to see progress
- Force: `cass index --full` only if `recommended_action` says so

Never bypass to SQLite — see P1.

---

## P7 — Calling `cass tui` from a non-interactive agent

**Symptom:** Session hangs forever with no output.

**Cause:** `cass tui` is an interactive Bubble-Tea-style TUI; non-TTY harnesses can't drive it.

**Fix:** never call `cass tui` from an agent. Use `cass search` / `cass sessions` / `cass timeline`.

---

## P8 — Reading whole session JSONL files

**Symptom:** `Read` tool used on a 5–50MB session file to find a passage.

**Fix:**
```bash
cass view   <source_path> -n <line> -C 20    # file lines around hit
cass expand <source_path> --line <line> -C 5 # whole messages around hit
cass export <source_path> --format markdown --output /tmp/s.md   # if you really need it all
```

---

## P9 — Aggregations skipped (paginating full hits to count things)

**Symptom:** `cass search ... --limit 1000` then `jq 'length'`.

**Fix:**
```bash
cass search "<q>" --robot --aggregate agent,workspace,date
```
Server-side, ~99% smaller payload, exact counts.

---

## P10 — Confusing `cass health` and `cass status`

**Use:**
- `cass health --json` — fast (<50ms), boolean readiness; `recommended_action` is authoritative.
- `cass status --json` — full state: rebuild progress, semantic readiness, DB counts. Use when health is unhealthy or you need progress info.
- `cass diag --json` — paths, versions, platform (rarely needed for search).

---

## P11 — Wrong assumptions about hit shape

**Symptom:** Code expects fields that aren't there, or misses fields that are.

**Fix:** look at the schema:
```bash
cass robot-docs schemas | sed -n '/search:/,/^[^[:space:]]/p'
# Or run a search and see the envelope:
cass search "x" --robot --limit 1 | jq 'keys, .hits[0] // empty'
```
Common fields: `score, agent, workspace, source_path, snippet, content, title, created_at, line_number, match_type, source_id`.

---

## P12 — Missing the `--robot-meta` diagnostic

**Symptom:** "Why is this returning weird results?"

**Fix:** `--robot-meta` adds `_meta` with `elapsed_ms`, `requested_search_mode`, `search_mode`, `semantic_refinement`, `fallback_tier`, `fallback_reason`, `cursor`. **Always add it when results surprise you.**

---

## Quick Diagnostic Block (paste into a session)

```bash
echo "=== cass quick check ==="
echo "--- version ---";          cass --version
echo "--- health ---";           cass health --json | jq -c '{status, healthy, recommended_action}'
echo "--- status (index) ---";   cass status --json | jq -c '.index | {exists, status, stale, rebuilding, age_seconds}'
echo "--- stats ---";            cass stats  --json | jq -c '{conversations, messages}'
echo "--- sources ---";          cass sources agents list --json 2>/dev/null | jq -c '.disabled // []'
echo "--- features ---";         cass capabilities --json | jq -c '.features'
```
