#!/usr/bin/env bash
# Verify bd → br migration is complete for a file.
#
# Checks:
#   - No leftover bd commands / sync / IDs
#   - No phantom br commands (br prime, br compact, br doctor --fix, --add-note, --description-file)
#   - Required br patterns present (sync --flush-only paired with git add .beads/)
#   - Non-invasive note present (in files that mention beads)
#
# Usage: ./verify-migration.sh <file.md>
# Exit codes:
#   0 — clean
#   1 — argument / file error
#   2 — migration incomplete

set -euo pipefail

file="${1:?Usage: verify-migration.sh <file.md>}"

if [[ ! -f "$file" ]]; then
    echo "ERROR: File not found: $file" >&2
    exit 1
fi

echo "=== Migration verification: $file ==="
echo ""

errors=0
warnings=0

count() { local n; n=$(grep -cF -- "$1" "$file" 2>/dev/null || true); echo "${n:-0}"; }
ecount() { local n; n=$(grep -cE -- "$1" "$file" 2>/dev/null || true); echo "${n:-0}"; }
fail() { echo "  ✗ FAIL: $1"; errors=$((errors + 1)); }
warn() { echo "  ⚠ WARN: $1"; warnings=$((warnings + 1)); }
pass() { echo "  ✓ PASS: $1"; }
banned_lines() { grep -nE -- "$1" "$file" 2>/dev/null | head -3 | sed 's/^/      /'; }

# ─── 1. Leftover bd references (MUST be 0) ──────────────────────────────────
echo "Checking for leftover bd references..."

n=$(count '`bd ')
if [[ "$n" -gt 0 ]]; then fail "$n \`bd\` command references"; banned_lines '`bd '
else pass "no \`bd\` command references"; fi

n=$(count 'bd sync')
if [[ "$n" -gt 0 ]]; then fail "$n 'bd sync' references"; banned_lines 'bd sync'
else pass "no 'bd sync' references"; fi

n=$(ecount 'bd-[0-9a-z]{3,}')
if [[ "$n" -gt 0 ]]; then fail "$n 'bd-NNNN' issue ID references"; banned_lines 'bd-[0-9a-z]{3,}'
else pass "no 'bd-NNNN' issue IDs"; fi

# ─── 2. Phantom br commands (MUST be 0) ─────────────────────────────────────
echo ""
echo "Checking for phantom br commands (don't exist in real binary)..."

n=$(count 'br prime')
if [[ "$n" -gt 0 ]]; then fail "BANNED: $n 'br prime' references — strip and use 'bv --robot-triage'"; banned_lines 'br prime'
else pass "no 'br prime'"; fi

n=$(count 'br compact')
if [[ "$n" -gt 0 ]]; then fail "BANNED: $n 'br compact' references — no compact subcommand exists"; banned_lines 'br compact'
else pass "no 'br compact'"; fi

n=$(count 'br doctor --fix')
if [[ "$n" -gt 0 ]]; then fail "BANNED: $n 'br doctor --fix' — flag is '--repair'"; banned_lines 'br doctor --fix'
else pass "no 'br doctor --fix'"; fi

n=$(count '--add-note')
if [[ "$n" -gt 0 ]]; then fail "BANNED: $n '--add-note' — flag does not exist; use read-modify-write with --notes"; banned_lines '\-\-add-note'
else pass "no '--add-note'"; fi

n=$(count '--description-file')
if [[ "$n" -gt 0 ]]; then fail "BANNED: $n '--description-file' — use 'br create -f <md>' or heredoc"; banned_lines '\-\-description-file'
else pass "no '--description-file'"; fi

# bare `br sync` without a mode flag
n=$( { grep -nE 'br sync($|[^-])' "$file" 2>/dev/null || true; } | { grep -vE -- '--flush-only|--import-only|--merge|--status' || true; } | wc -l | tr -d ' ')
if [[ "${n:-0}" -gt 0 ]]; then fail "$n 'br sync' without a mode flag — needs --flush-only / --import-only / --merge / --status"
else pass "no bare 'br sync'"; fi

# ─── 3. Removed bd-only sections (warnings) ─────────────────────────────────
echo ""
echo "Checking for bd-only concepts (br has no daemon/hooks/auto-commit)..."

n=$(grep -ci 'daemon' "$file" 2>/dev/null || true); n="${n:-0}"
if [[ "$n" -gt 0 ]]; then warn "$n 'daemon' references (br has no daemon)"; fi

n=$(grep -ciE 'auto-commit|auto commit' "$file" 2>/dev/null || true); n="${n:-0}"
if [[ "$n" -gt 0 ]]; then warn "$n 'auto-commit' references (br does not auto-commit)"; fi

# ─── 4. Required br patterns (only if file has beads content) ───────────────
echo ""
has_beads=$(ecount 'beads|\.beads|br ready|br sync|br create|br update|br close')
if [[ "$has_beads" -gt 0 ]]; then
    echo "File has beads content — checking required br patterns..."

    syncs=$(count 'br sync --flush-only')
    if [[ "$syncs" -eq 0 ]]; then
        warn "no 'br sync --flush-only' (expected if file documents sync)"
    else
        pass "$syncs 'br sync --flush-only' references"
    fi

    adds=$(count 'git add .beads/')
    if [[ "$syncs" -gt 0 && "$adds" -lt "$syncs" ]]; then
        fail "$syncs syncs but only $adds 'git add .beads/' — every sync needs a paired git add"
    elif [[ "$adds" -gt 0 ]]; then
        pass "$adds 'git add .beads/' references"
    fi

    note=$(count 'non-invasive')
    if [[ "$note" -eq 0 ]]; then
        warn "no non-invasive note (template in SKILL.md §3)"
    else
        pass "non-invasive note present"
    fi
else
    echo "File has no beads content — skipping required-pattern checks"
fi

# ─── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "=== Summary ==="
if [[ "$errors" -eq 0 && "$warnings" -eq 0 ]]; then
    echo "✓ PASS: migration verified clean"
    exit 0
elif [[ "$errors" -eq 0 ]]; then
    echo "✓ PASS with $warnings warning(s) — review before declaring done"
    exit 0
else
    echo "✗ FAIL: $errors error(s), $warnings warning(s)"
    echo "  Fix the errors above and re-run."
    exit 2
fi
