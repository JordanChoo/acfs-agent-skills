#!/usr/bin/env bash
# Regression cases and live UBS probes; fixtures are retained, never deleted.
set -euo pipefail
skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if python3 "$skill_dir/scripts/test_scan.py"; then
  echo 'PASS: UBS capture, coverage, scope, regression replay, and live CLI checks'
else
  scan_test_rc=$?
  echo 'FAIL: UBS skill self-test; inspect the retained artifact paths above'
  exit "$scan_test_rc"
fi
