#!/usr/bin/env bash
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_MD="$SKILL_DIR/SKILL.md"
REPO_DIR="$(cd "$SKILL_DIR/.." && pwd)"
AUDIT_SCRIPT="$REPO_DIR/scripts/audit-drift.sh"

PASS=0
FAIL=0

ok()  { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }

echo "=== shared-skill-authoring self-test ==="
echo

[ -f "$SKILL_MD" ] && ok "exists: SKILL.md" || bad "missing: SKILL.md"
[ -x "$AUDIT_SCRIPT" ] && ok "exists: scripts/audit-drift.sh" || bad "missing executable audit-drift.sh"

for needle in \
  "~/src/acfs-agent-skills" \
  "~/.claude/skills" \
  "~/.codex/skills" \
  "scripts/audit-drift.sh" \
  "scripts/install.sh" \
  "scripts/test-all.sh"; do
  if grep -Fq "$needle" "$SKILL_MD"; then
    ok "documents: $needle"
  else
    bad "missing guidance for: $needle"
  fi
done

echo
echo "PASS: $PASS    FAIL: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 2
