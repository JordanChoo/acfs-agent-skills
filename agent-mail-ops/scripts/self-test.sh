#!/usr/bin/env bash
# Static guidance checks; --live adds bounded, read-only schema/help probes.
set -euo pipefail
SKILL_DIR="$(cd -P "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
python3 "$SKILL_DIR/scripts/test_skill.py" "$@"
