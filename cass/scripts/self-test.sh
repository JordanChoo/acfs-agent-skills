#!/usr/bin/env bash
# cass skill self-test. Read-only checks against the installed cass binary.
# Maps 1:1 to SELF-TEST.md.
#
# Self-locating: works whether this skill is installed under
# ~/.claude/skills/cass or ~/.codex/skills/cass.

set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

PASS=0
FAIL=0
SKIP=0

ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
skip() { echo "  - $1"; SKIP=$((SKIP+1)); }

echo "=== cass skill self-test ==="
echo

# Sanity
command -v cass >/dev/null || { echo "FATAL: cass not on PATH"; exit 1; }

# Files
echo "[Structure]"
for f in \
  "$SKILL_DIR/SKILL.md" \
  "$SKILL_DIR/references/RECIPES.md" \
  "$SKILL_DIR/references/PITFALLS.md" \
  "$SKILL_DIR/SELF-TEST.md"; do
  [ -f "$f" ] && ok "exists: $f" || bad "missing: $f"
done
echo

# F1 — bad usage rejected
echo "[F1] 'cass search robot \"q\"' must fail with usage error"
out=$(cass search robot "hello" 2>&1; echo "EXIT=$?")
ec=$(echo "$out" | tail -1 | grep -oE 'EXIT=[0-9]+' | cut -d= -f2)
if [ "$ec" -eq 2 ]; then
  ok "exit code 2 (usage)"
else
  bad "exit code was '$ec' (expected 2). Output: $(echo "$out" | head -2)"
fi
echo

# F2 — --since accepts ISO dates and relative offsets (cass ≥ 0.4)
echo "[F2] --since accepts ISO date and quoted relative offset"
ec1=$(cass search "x" --since 2026-01-01 --robot --limit 1 >/dev/null 2>&1; echo $?)
ec2=$(cass search "x" --since '-7d'      --robot --limit 1 >/dev/null 2>&1; echo $?)
if [ "$ec1" -eq 0 ] && [ "$ec2" -eq 0 ]; then
  ok "ISO date and '-7d' both accepted"
else
  bad "ISO=$ec1 relative=$ec2 (both should be 0)"
fi
echo

# F3 — health returns a known status
echo "[F3] cass health --json returns a known status"
status=$(cass health --json 2>/dev/null | jq -r '.status // "missing"')
case "$status" in
  healthy|rebuilding|unhealthy)
    ok "status='$status'"
    ;;
  *)
    bad "unexpected status='$status'"
    ;;
esac
echo

# F4 — aggregations work
echo "[F4] aggregations return a parseable structure"
agg=$(cass search "*" --robot --aggregate agent --limit 0 2>/dev/null)
if echo "$agg" | jq -e '.aggregations // .buckets // .' >/dev/null 2>&1; then
  ok "aggregate output parses"
else
  bad "aggregate output not parseable"
fi
echo

# F5 — --robot-meta provides diagnostics
echo "[F5] --robot-meta exposes search-mode/elapsed_ms"
meta=$(cass search "anything" --robot --robot-meta --limit 1 2>/dev/null | jq -c '._meta // {}')
if echo "$meta" | jq -e 'has("elapsed_ms") or has("search_mode") or has("requested_search_mode")' >/dev/null; then
  ok "meta has diagnostic fields ($(echo "$meta" | jq -c 'keys'))"
else
  bad "meta missing diagnostics: $meta"
fi
echo

# F6 — cass view works on a real session
echo "[F6] cass view works on the most recent session"
sp=$(cass sessions --json --limit 1 2>/dev/null | jq -r '.sessions[0].path // empty')
if [ -n "$sp" ] && [ -f "$sp" ]; then
  if cass view "$sp" -n 1 -C 0 >/dev/null 2>&1; then
    ok "viewed $sp:1"
  else
    bad "view failed for $sp"
  fi
else
  skip "no sessions available to view"
fi
echo

# F7 — capabilities reports the features the skill relies on
echo "[F7] capabilities reports json_output, aggregations, field_selection"
caps=$(cass capabilities --json 2>/dev/null)
if echo "$caps" | jq -e '
  (.features | index("json_output"))     and
  (.features | index("aggregations"))    and
  (.features | index("field_selection"))
' >/dev/null; then
  ok "all required features present"
else
  bad "missing required features: $(echo "$caps" | jq -c '.features // []')"
fi
echo

# F8 — robot-docs are available for topics referenced in the skill
echo "[F8] robot-docs available for documented topics"
all_topics_ok=1
for topic in commands env paths schemas guide exit-codes examples contracts wrap sources analytics; do
  if cass robot-docs "$topic" >/dev/null 2>&1; then
    :
  else
    bad "topic missing: $topic"
    all_topics_ok=0
  fi
done
[ "$all_topics_ok" -eq 1 ] && ok "all 11 robot-docs topics resolve"
echo

# F9 — doctor returns structured diagnostics without modifying
# Note: cass doctor exits non-zero when unhealthy (which is normal during a rebuild),
# but the JSON envelope is still produced. We care about the structure, not the rc.
echo "[F9] cass doctor --json returns a structured envelope"
out=$(cass doctor --json 2>/dev/null)
if echo "$out" | jq -e 'has("healthy") and has("status") and has("checks")' >/dev/null 2>&1; then
  ok "envelope has healthy/status/checks (.healthy=$(echo "$out" | jq -r '.healthy'), .status=$(echo "$out" | jq -r '.status'))"
else
  bad "doctor JSON missing required keys"
fi
echo

# === Summary ===
echo "=== Summary ==="
echo "PASS: $PASS    FAIL: $FAIL    SKIP: $SKIP"
[ "$FAIL" -eq 0 ] && exit 0 || exit 2
