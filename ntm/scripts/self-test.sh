#!/usr/bin/env bash
# ntm skill self-test. Read-only — verifies the binary's command surface
# still matches what the skill documents. Maps 1:1 to SELF-TEST.md.
#
# Self-locating: works whether this skill is installed under
# ~/.claude/skills/ntm or ~/.codex/skills/ntm.

set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

PASS=0
FAIL=0
SKIP=0

ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
skip() { echo "  - $1"; SKIP=$((SKIP+1)); }

echo "=== ntm skill self-test ==="
echo

command -v ntm >/dev/null || { echo "FATAL: ntm not on PATH"; exit 1; }

# Cache help output once — `ntm <subcmd> --help` has shown partial-output races
# (color/TTY detection). Cache, retry-on-empty, then grep is deterministic.
help_for() {
  local out attempt
  for attempt in 1 2 3; do
    out="$(ntm "$@" --help 2>&1)"
    # `ntm <sub> --help` reliably mentions "Usage" when complete; retry on partials.
    if echo "$out" | grep -q '^Usage:'; then
      printf '%s' "$out"
      return 0
    fi
  done
  printf '%s' "$out"   # last attempt, even if partial
}

# Structure
echo "[Structure]"
for f in \
  "$SKILL_DIR/SKILL.md" \
  "$SKILL_DIR/SELF-TEST.md" \
  "$SKILL_DIR/references/PITFALLS.md" \
  "$SKILL_DIR/references/RECIPES.md"; do
  [ -f "$f" ] && ok "exists: $f" || bad "missing: $f"
done
echo

# F1 — `ntm spawn` requires a session name
echo "[F1] ntm spawn requires a session name"
out=$(ntm spawn 2>&1; echo "EXIT=$?")
ec=$(echo "$out" | tail -1 | grep -oE 'EXIT=[0-9]+' | cut -d= -f2)
if [ "${ec:-0}" -ne 0 ]; then
  ok "exit code $ec (rejected)"
else
  bad "expected non-zero, got $ec"
fi
echo

# F2 — `ntm send` requires a session name
echo "[F2] ntm send requires a session name"
out=$(ntm send --cod "test" 2>&1; echo "EXIT=$?")
ec=$(echo "$out" | tail -1 | grep -oE 'EXIT=[0-9]+' | cut -d= -f2)
if [ "${ec:-0}" -ne 0 ]; then
  ok "exit code $ec (rejected)"
else
  bad "expected non-zero, got $ec"
fi
echo

# F3 — Recipes
echo "[F3] built-in recipes"
recipes_out=$(ntm recipes list 2>/dev/null)
for r in quick-claude full-stack minimal codex-heavy balanced review-team; do
  echo "$recipes_out" | grep -q "$r" && ok "$r" || bad "$r missing"
done
echo

# F4 — Workflow templates
echo "[F4] built-in workflow templates"
wf_out=$(ntm workflows list 2>/dev/null)
for t in red-green review-pipeline specialist-team parallel-explore; do
  echo "$wf_out" | grep -q "$t" && ok "$t" || bad "$t missing"
done
echo

# F5 — projects_base in config (retry once on flake)
echo "[F5] ntm config show exposes projects_base"
get_cfg() { ntm config show 2>/dev/null; }
CFG="$(get_cfg)"
[ -z "$CFG" ] && CFG="$(get_cfg)"   # one retry
if echo "$CFG" | grep -q '^projects_base'; then
  pb=$(echo "$CFG" | awk -F'"' '/^projects_base/{print $2}')
  ok "projects_base = $pb"
else
  bad "no 'projects_base =' line in config"
fi
echo

SEND_HELP="$(help_for send)"
ACTIVITY_HELP="$(help_for activity)"
DASHBOARD_HELP="$(help_for dashboard)"

# F6 — send documents --cass-check / --no-cass-check
echo "[F6] ntm send: --cass-check / --no-cass-check"
echo "$SEND_HELP" | grep -q -- '--cass-check'    && ok '--cass-check documented'    || bad '--cass-check missing'
echo "$SEND_HELP" | grep -q -- '--no-cass-check' && ok '--no-cass-check documented' || bad '--no-cass-check missing'
echo

SPAWN_HELP="$(help_for spawn)"

# F7 — spawn documents --stagger-mode
echo "[F7] ntm spawn: --stagger-mode"
echo "$SPAWN_HELP" | grep -q -- '--stagger-mode' && ok '--stagger-mode documented' || bad '--stagger-mode missing'
echo

# F8 — activity / dashboard have --json
echo "[F8] activity / dashboard expose --json for headless use"
echo "$ACTIVITY_HELP"  | grep -q -- '--json' && ok 'activity --json'  || bad 'activity --json missing'
echo "$DASHBOARD_HELP" | grep -q -- '--json' && ok 'dashboard --json' || bad 'dashboard --json missing'
echo

# F9 — spawn documents key flags
echo "[F9] ntm spawn: key flags present"
for f in '--worktrees' '--label' '--auto-restart' '--persona' '--no-user' '--safety' '--cc' '--cod' '--gmi' '--prompt'; do
  echo "$SPAWN_HELP" | grep -q -- "$f" && ok "$f" || bad "$f missing"
done
echo

# F10 — send documents key flags
echo "[F10] ntm send: key flags present"
for f in '--cc' '--cod' '--gmi' '--all' '--skip-first' '--pane' '--panes' '--tag' '--smart' '--dry-run' '--file' '--context' '--template'; do
  echo "$SEND_HELP" | grep -q -- "$f" && ok "$f" || bad "$f missing"
done
echo

# === Summary ===
echo "=== Summary ==="
echo "PASS: $PASS    FAIL: $FAIL    SKIP: $SKIP"
[ "$FAIL" -eq 0 ] && exit 0 || exit 2
