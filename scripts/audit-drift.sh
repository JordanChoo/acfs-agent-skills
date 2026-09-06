#!/usr/bin/env bash
# audit-drift.sh — inspect ~/.claude/skills and ~/.codex/skills for drift from
# this repo's canonical skill directories. Read-only.
#
# Usage:
#   bash scripts/audit-drift.sh
#   bash scripts/audit-drift.sh --claude-only
#   bash scripts/audit-drift.sh --codex-only
#   bash scripts/audit-drift.sh --json
#
# Skills listed in scripts/tool-managed.txt (installer-owned, e.g. rch) are
# expected to be real directories; they report as "◦ tool-managed" and count
# as pass. A tool-managed skill that is a SYMLINK is reported as drift, since
# its installer will replace or write through it on the next run.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HARNESSES=(claude codex)
JSON=0

usage() { sed -n '/^# audit-drift.sh/,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

for a in "$@"; do
  case "$a" in
    --claude-only) HARNESSES=(claude) ;;
    --codex-only) HARNESSES=(codex) ;;
    --json) JSON=1 ;;
    -h|--help) usage 0 ;;
    *) echo "unknown flag: $a" >&2; usage 2 ;;
  esac
done

skill_dirs() {
  for d in "$REPO_DIR"/*/; do
    [ -f "$d/SKILL.md" ] && basename "$d" || true
  done | sort
}

TOOL_MANAGED_FILE="$REPO_DIR/scripts/tool-managed.txt"

tool_managed() {
  # True when $1 is owned by its own installer (see scripts/tool-managed.txt).
  local name="$1" line
  [ -f "$TOOL_MANAGED_FILE" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="${line//[[:space:]]/}"
    [ "$line" = "$name" ] && return 0
  done < "$TOOL_MANAGED_FILE"
  return 1
}

snapshot_current() {
  # 0 when every file in the live harness copy ($1) exists byte-identically
  # in the canonical snapshot ($2). Files that exist only in canonical (e.g.
  # a locally-authored helper script) are allowed, so this is deliberately
  # not `diff -rq`.
  local live="$1" canon="$2" f rel
  while IFS= read -r -d '' f; do
    rel="${f#"$live"/}"
    [ -f "$canon/$rel" ] && cmp -s "$f" "$canon/$rel" || return 1
  done < <(find "$live" -type f -print0)
  return 0
}

json_escape() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  printf '%s' "$value"
}

PASS=0
FAIL=0
declare -a ROWS

record() {
  local harness="$1" skill="$2" status="$3" detail="$4"
  case "$status" in
    ok|tool-managed) PASS=$((PASS+1)) ;;
    *) FAIL=$((FAIL+1)) ;;
  esac

  if [ "$JSON" -eq 1 ]; then
    ROWS+=("$(printf '{"harness":"%s","skill":"%s","status":"%s","detail":"%s"}' \
      "$(json_escape "$harness")" \
      "$(json_escape "$skill")" \
      "$(json_escape "$status")" \
      "$(json_escape "$detail")")")
  else
    case "$status" in
      ok)           printf '  ✓ %s/%s — %s\n' "$harness" "$skill" "$detail" ;;
      tool-managed) printf '  ◦ %s/%s — %s\n' "$harness" "$skill" "$detail" ;;
      *)            printf '  ✗ %s/%s — %s\n' "$harness" "$skill" "$detail" ;;
    esac
  fi
}

audit_skill() {
  local harness="$1" skill="$2"
  local target="$HOME/.${harness}/skills/$skill"
  local expected="$REPO_DIR/$skill"

  if tool_managed "$skill"; then
    if [ ! -e "$target" ]; then
      record "$harness" "$skill" "tool-managed" "installer-owned; not installed on this machine"
    elif [ -L "$target" ]; then
      record "$harness" "$skill" "drift" "tool-managed skill is a symlink — its installer will replace or write through it; restore the real dir"
    elif snapshot_current "$target" "$expected"; then
      record "$harness" "$skill" "tool-managed" "installer-owned real dir; canonical snapshot is current"
    else
      record "$harness" "$skill" "tool-managed" "installer-owned real dir; canonical snapshot is behind (refresh: cp -R ~/.${harness}/skills/${skill}/. ${skill}/)"
    fi
    return
  fi

  if [ ! -e "$target" ]; then
    record "$harness" "$skill" "drift" "missing target"
    return
  fi

  if [ -L "$target" ]; then
    local resolved
    resolved="$(readlink -f "$target" 2>/dev/null || readlink "$target")"
    if [ "$resolved" = "$expected" ]; then
      record "$harness" "$skill" "ok" "symlinked to canonical repo"
    else
      record "$harness" "$skill" "drift" "symlink target mismatch ($resolved)"
    fi
    return
  fi

  if [ -d "$target" ]; then
    if diff -rq "$target" "$expected" >/dev/null 2>&1; then
      record "$harness" "$skill" "drift" "real directory blocks installer but contents match canonical repo"
    else
      record "$harness" "$skill" "drift" "real directory differs from canonical repo"
    fi
    return
  fi

  record "$harness" "$skill" "drift" "unexpected non-directory file at target"
}

audit_extras() {
  local harness="$1"
  local root="$HOME/.${harness}/skills"
  [ -d "$root" ] || return

  local p name
  for p in "$root"/*; do
    [ -e "$p" ] || continue
    name="$(basename "$p")"
    if [ ! -f "$REPO_DIR/$name/SKILL.md" ]; then
      if tool_managed "$name"; then
        record "$harness" "$name" "tool-managed" "installer-owned; not tracked in canonical repo (expected)"
      else
        record "$harness" "$name" "drift" "extra harness-local entry not present in canonical repo"
      fi
    fi
  done
}

main() {
  local skills
  skills="$(skill_dirs)"

  if [ "$JSON" -eq 0 ]; then
    echo "Repo:    $REPO_DIR"
    echo "Skills:  $(echo "$skills" | wc -l | tr -d ' ')"
    echo "Targets: ${HARNESSES[*]}"
    echo
  fi

  local harness skill
  for harness in "${HARNESSES[@]}"; do
    if [ "$JSON" -eq 0 ]; then
      echo "[$harness]"
    fi
    while IFS= read -r skill; do
      [ -n "$skill" ] || continue
      audit_skill "$harness" "$skill"
    done <<<"$skills"
    audit_extras "$harness"
    if [ "$JSON" -eq 0 ]; then
      echo
    fi
  done

  if [ "$JSON" -eq 1 ]; then
    printf '{"pass":%d,"fail":%d,"results":[%s]}\n' \
      "$PASS" "$FAIL" "$(IFS=,; echo "${ROWS[*]}")"
  else
    echo "Summary: PASS $PASS    FAIL $FAIL"
  fi

  [ "$FAIL" -eq 0 ] && exit 0 || exit 1
}

main
