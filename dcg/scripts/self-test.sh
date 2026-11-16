#!/usr/bin/env bash
# Candidate commands are evaluated as data, never executed.
set -euo pipefail
SKILL_DIR="$(cd -P "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
if python3 "$SKILL_DIR/scripts/test_skill.py"; then
  echo 'PASS: DCG regression suite; 61 historical candidates evaluated, none executed'
else
  test_rc=$?
  echo 'FAIL: DCG regression suite (missing live coverage is not a pass)'
  exit "$test_rc"
fi
