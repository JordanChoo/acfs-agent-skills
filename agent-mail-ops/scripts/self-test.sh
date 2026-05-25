#!/usr/bin/env bash
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_MD="$SKILL_DIR/SKILL.md"

PASS=0
FAIL=0

ok()  { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }

echo "=== agent-mail-ops skill self-test ==="
echo

[ -f "$SKILL_MD" ] && ok "exists: SKILL.md" || bad "missing: SKILL.md"

for needle in \
  "agent-mail.service" \
  "127.0.0.1:8765" \
  "mcp-agent-mail serve" \
  "am serve-http" \
  "http://127.0.0.1:8765/mcp/" \
  "AM_NEXT_STEPS.md"; do
  if grep -Fq "$needle" "$SKILL_MD"; then
    ok "documents: $needle"
  else
    bad "missing guidance for: $needle"
  fi
done

echo
echo "PASS: $PASS    FAIL: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 2
