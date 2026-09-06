#!/usr/bin/env bash
# install.sh — symlink every skill in this repo into ~/.claude/skills/ and
# ~/.codex/skills/. Idempotent. Safe: refuses to overwrite a real (non-symlink)
# directory at the target without --force.
#
# Usage:
#   bash scripts/install.sh                # link into both Claude Code + Codex
#   bash scripts/install.sh --claude-only
#   bash scripts/install.sh --codex-only
#   bash scripts/install.sh --force        # backup + replace any real dirs at target
#   bash scripts/install.sh --dry-run      # print what would happen, change nothing
#   bash scripts/install.sh --uninstall    # remove only the symlinks we own (skip real dirs)
#
# Skills listed in scripts/tool-managed.txt (installer-owned, e.g. rch) are
# never linked or unlinked, even with --force: their installers own the copies
# under ~/.<harness>/skills and would clobber (or write through) a symlink.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HARNESSES=(claude codex)
FORCE=0
DRY=0
UNINSTALL=0

usage() { sed -n '/^# install.sh/,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

for a in "$@"; do
  case "$a" in
    --claude-only)  HARNESSES=(claude) ;;
    --codex-only)   HARNESSES=(codex)  ;;
    --force)        FORCE=1            ;;
    --dry-run|-n)   DRY=1              ;;
    --uninstall)    UNINSTALL=1        ;;
    -h|--help)      usage 0            ;;
    *)              echo "unknown flag: $a" >&2; usage 2 ;;
  esac
done

run() { if [ "$DRY" -eq 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

TOOL_MANAGED_FILE="$REPO_DIR/scripts/tool-managed.txt"

tool_managed() {
  # True when $1 is owned by its own installer (see scripts/tool-managed.txt).
  # Pure bash on purpose: a `grep -q` pipeline under pipefail can report a
  # SIGPIPE'd sed as failure even when the name matched.
  local name="$1" line
  [ -f "$TOOL_MANAGED_FILE" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="${line//[[:space:]]/}"
    [ "$line" = "$name" ] && return 0
  done < "$TOOL_MANAGED_FILE"
  return 1
}

skill_dirs() {
  # Anything at the repo root that contains a SKILL.md
  for d in "$REPO_DIR"/*/; do
    [ -f "$d/SKILL.md" ] && basename "$d" || true
  done
}

link_one() {
  local harness="$1" name="$2"
  local target="$HOME/.${harness}/skills/$name"
  local source_path="$REPO_DIR/$name"
  mkdir -p "$(dirname "$target")"

  if tool_managed "$name"; then
    echo "  ◦ $harness/$name (tool-managed; owned by its installer — skipped)"
    return 0
  fi

  if [ -L "$target" ]; then
    local current; current="$(readlink -f "$target" 2>/dev/null || readlink "$target")"
    if [ "$current" = "$source_path" ]; then
      echo "  ~ $harness/$name (already linked)"
      return 0
    fi
    echo "  ↻ $harness/$name (relinking; was $current)"
    run rm "$target"
  elif [ -d "$target" ]; then
    if [ "$FORCE" -eq 1 ]; then
      local backup="$HOME/.${harness}-skills-backup-$(date +%s)"
      mkdir -p "$backup"
      echo "  ⚠ $harness/$name is a real dir; moving to $backup/$name"
      run mv "$target" "$backup/$name"
    else
      echo "  ✗ $harness/$name is a real dir (not a symlink). Use --force to back it up and replace, or add it to scripts/tool-managed.txt if an installer owns it." >&2
      return 1
    fi
  fi
  run ln -s "$source_path" "$target"
  echo "  ✓ $harness/$name → $source_path"
}

unlink_one() {
  local harness="$1" name="$2"
  local target="$HOME/.${harness}/skills/$name"
  if tool_managed "$name"; then
    echo "  ◦ $harness/$name (tool-managed; leaving it alone)"
    return 0
  fi
  if [ -L "$target" ]; then
    run rm "$target"
    echo "  ✓ removed symlink $harness/$name"
  elif [ -d "$target" ]; then
    echo "  ~ $harness/$name is a real dir; leaving it alone"
  fi
}

main() {
  local skills; skills=$(skill_dirs | sort)
  if [ -z "$skills" ]; then
    echo "No skills found under $REPO_DIR" >&2
    exit 1
  fi

  if [ "$UNINSTALL" -eq 1 ]; then
    echo "Uninstalling symlinks for ${#HARNESSES[@]} harness(es)..."
    for h in "${HARNESSES[@]}"; do
      while IFS= read -r name; do unlink_one "$h" "$name"; done <<<"$skills"
    done
    return 0
  fi

  echo "Repo:     $REPO_DIR"
  echo "Skills:   $(echo "$skills" | wc -l | tr -d ' ')"
  echo "Targets:  ${HARNESSES[*]}"
  [ "$DRY" -eq 1 ]   && echo "Mode:     DRY RUN"
  [ "$FORCE" -eq 1 ] && echo "Mode:     FORCE (will back up real dirs)"
  echo

  local failed=0
  for h in "${HARNESSES[@]}"; do
    while IFS= read -r name; do
      # One blocked skill must not abort the rest of the run.
      link_one "$h" "$name" || failed=$((failed+1))
    done <<<"$skills"
  done

  echo
  if [ "$failed" -gt 0 ]; then
    echo "Done, but $failed target(s) were NOT linked (real dirs). Rerun with --force to back them up, or list installer-owned ones in scripts/tool-managed.txt." >&2
    echo "Verify with: bash scripts/audit-drift.sh"
    exit 1
  fi
  echo "Done. Verify with: ls -la ~/.claude/skills/ ~/.codex/skills/"
}

main
