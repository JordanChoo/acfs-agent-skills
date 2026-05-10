#!/usr/bin/env bash
# test-all.sh — run scripts/self-test.sh (or any test runner that lives at the
# expected path) for every skill in this repo. Read-only.
#
# Usage:
#   bash scripts/test-all.sh
#   bash scripts/test-all.sh --skill cass         # one skill only
#   bash scripts/test-all.sh --quiet              # one-line summary per skill
#   bash scripts/test-all.sh --json               # JSON envelope for CI

set -uo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ONLY=""
QUIET=0
JSON=0

usage() { sed -n '/^# test-all.sh/,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --skill) ONLY="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    --json)  JSON=1;  shift ;;
    -h|--help) usage 0 ;;
    *)       echo "unknown flag: $1" >&2; usage 2 ;;
  esac
done

results_pass=0
results_fail=0
results_skip=0
declare -a rows

run_one() {
  local name="$1"
  local skill_dir="$REPO_DIR/$name"
  local runner="$skill_dir/scripts/self-test.sh"
  local status="skipped"
  local detail="no scripts/self-test.sh"

  if [ -x "$runner" ]; then
    if out=$(bash "$runner" 2>&1); then
      status="pass"
      detail=$(echo "$out" | grep -E '^PASS:' | tail -1)
      results_pass=$((results_pass + 1))
    else
      status="fail"
      detail=$(echo "$out" | grep -E '^PASS:|^FAIL' | tail -1)
      results_fail=$((results_fail + 1))
    fi
  else
    results_skip=$((results_skip + 1))
  fi

  if [ "$JSON" -eq 1 ]; then
    rows+=("$(printf '{"skill":"%s","status":"%s","detail":"%s"}' "$name" "$status" "${detail//\"/\\\"}")")
  elif [ "$QUIET" -eq 1 ]; then
    case "$status" in
      pass) echo "  ✓ $name" ;;
      fail) echo "  ✗ $name — $detail" ;;
      skipped) echo "  - $name (skipped: $detail)" ;;
    esac
  else
    echo "════════════════════════════════════════════"
    echo " $name"
    echo "════════════════════════════════════════════"
    case "$status" in
      pass)    echo "  ✓ $detail" ;;
      fail)    echo "  ✗ $detail"; echo; echo "$out" | tail -20 ;;
      skipped) echo "  - skipped: $detail" ;;
    esac
    echo
  fi
}

skills_to_run() {
  if [ -n "$ONLY" ]; then
    [ -d "$REPO_DIR/$ONLY" ] && echo "$ONLY" || { echo "no skill: $ONLY" >&2; exit 1; }
  else
    for d in "$REPO_DIR"/*/; do
      [ -f "$d/SKILL.md" ] && basename "$d"
    done | sort
  fi
}

list=$(skills_to_run)

if [ "$JSON" -eq 0 ] && [ "$QUIET" -eq 0 ]; then
  echo "Repo:    $REPO_DIR"
  echo "Skills:  $(echo "$list" | wc -l | tr -d ' ')"
  echo
fi

while IFS= read -r name; do run_one "$name"; done <<<"$list"

if [ "$JSON" -eq 1 ]; then
  printf '{"pass":%d,"fail":%d,"skipped":%d,"results":[%s]}\n' \
    "$results_pass" "$results_fail" "$results_skip" \
    "$(IFS=,; echo "${rows[*]}")"
else
  echo "Summary: PASS $results_pass    FAIL $results_fail    SKIP $results_skip"
fi

[ "$results_fail" -eq 0 ] && exit 0 || exit 1
