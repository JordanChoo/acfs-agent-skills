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
      echo "  ✗ $harness/$name is a real dir (not a symlink). Use --force to back it up and replace." >&2
      return 1
    fi
  fi
  run ln -s "$source_path" "$target"
  echo "  ✓ $harness/$name → $source_path"
}

unlink_one() {
  local harness="$1" name="$2"
  local target="$HOME/.${harness}/skills/$name"
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

  for h in "${HARNESSES[@]}"; do
    while IFS= read -r name; do link_one "$h" "$name"; done <<<"$skills"
  done

  echo
  echo "Done. Verify with: ls -la ~/.claude/skills/ ~/.codex/skills/"
}

main
