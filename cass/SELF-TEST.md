# Self-Test: cass skill

Each test maps to a failure pattern observed in CASS sessions or in the prior session that motivated this skill.

Run via:
```bash
bash "$(dirname "$(realpath "$0" 2>/dev/null || echo .)")/scripts/self-test.sh"
# Or just (works from anywhere):
bash ~/.claude/skills/cass/scripts/self-test.sh   # Claude Code
bash ~/.codex/skills/cass/scripts/self-test.sh    # Codex
```

---

## Trigger Phrases (must activate the skill)

| Phrase | Expected |
|---|---|
| "search my past sessions for X" | Activates |
| "find that conversation about the auth bug" | Activates |
| "what did I work on last week?" | Activates |
| "show me recent sessions in this repo" | Activates |
| "look up cass history" | Activates |
| "cass index is broken" | Activates |
| "use cass to find X" | Activates |

---

## Structure

```bash
SKILL_DIR=~/.claude/skills/cass        # or ~/.codex/skills/cass
test -f "$SKILL_DIR/SKILL.md"
test -f "$SKILL_DIR/references/RECIPES.md"
test -f "$SKILL_DIR/references/PITFALLS.md"
test -x "$SKILL_DIR/scripts/self-test.sh"
```

---

## Behavioural Checks (the skill should produce these results)

### B1 — Health preflight runs first
The agent's first command for any search task should be `cass health --json` (or `cass status --json`).

Spot check: grep the agent's bash invocations for `cass search` *before* `cass health|status` — that ordering is the antipattern.

### B2 — `--limit` and `--max-content-length` are set
Any `cass search` issued by the agent should include both.

### B3 — Direct sqlite3 against the DB is **not used**
Match anything like `sqlite3 .*agent_search.db` — that's an A1 violation (see SKILL.md §Anti-Patterns).

### B4 — No `cass tui` from a non-interactive context
Match `cass tui` and confirm it's only mentioned as documentation, never executed.

---

## Failure-Case Tests

The skill must guide the agent away from each. Self-test script exercises the cass binary against the failure inputs.

### F1 — `cass search robot "<q>"` fails the right way
Should exit 2 with a usage error (not a hang or mystery).
```bash
cass search robot "hello" 2>&1 | head -3
echo "exit=$?  expect:2"
```

### F2 — `--since` accepts both ISO dates and relative offsets
Modern cass (≥ 0.4) accepts both forms. The skill's recipes recommend `--days N` or quoted `'-7d'` for portability.
```bash
cass search "x" --since 2026-01-01 --robot --limit 1 >/dev/null; echo "iso exit=$?  expect:0"
cass search "x" --since '-7d'      --robot --limit 1 >/dev/null; echo "rel exit=$?  expect:0"
```

### F3 — Index rebuilding is detectable via health
```bash
cass health --json | jq -r '.status'
# Either "healthy", "rebuilding", or "unhealthy" — always one of these.
```

### F4 — Aggregations work and are token-cheap
```bash
agg=$(cass search "*" --robot --aggregate agent --limit 0 2>/dev/null)
echo "$agg" | jq -e '.aggregations // .data // .' >/dev/null && echo "F4 PASS" || echo "F4 FAIL"
```

### F5 — `--robot-meta` returns diagnostic fields
```bash
meta=$(cass search "anything" --robot --robot-meta --limit 1 2>/dev/null | jq -c '._meta // {}')
echo "$meta" | jq -e 'has("elapsed_ms") or has("search_mode") or has("requested_search_mode")' >/dev/null \
  && echo "F5 PASS" || echo "F5 FAIL ($meta)"
```

### F6 — `cass view` works on a session path
```bash
sp=$(cass sessions --json --limit 1 2>/dev/null | jq -r '.sessions[0].path // empty')
[ -n "$sp" ] && cass view "$sp" -n 1 -C 0 >/dev/null 2>&1 && echo "F6 PASS" || echo "F6 SKIP/FAIL"
```

### F7 — `cass capabilities` has expected features
```bash
cass capabilities --json | jq -e '
  .features as $f
  | ($f | index("json_output")) and
    ($f | index("aggregations")) and
    ($f | index("field_selection"))
' >/dev/null && echo "F7 PASS" || echo "F7 FAIL"
```

### F8 — Robot docs are present for the topics referenced in the skill
```bash
for topic in commands env paths schemas guide exit-codes examples contracts wrap sources analytics; do
  cass robot-docs "$topic" >/dev/null 2>&1 \
    && echo "  ✓ $topic" \
    || echo "  ✗ $topic missing"
done
```

### F9 — Doctor returns structured diagnostics
`cass doctor` may exit non-zero when issues are detected (that's normal during rebuilds), but always produces a structured JSON envelope.
```bash
cass doctor --json 2>/dev/null | jq -e 'has("healthy") and has("status") and has("checks")' >/dev/null \
  && echo "F9 PASS (envelope intact)" \
  || echo "F9 FAIL"
```

---

## Cleanup

The tests above are read-only. No cleanup needed.
