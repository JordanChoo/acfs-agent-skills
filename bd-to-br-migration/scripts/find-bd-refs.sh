#!/usr/bin/env bash
# Find files containing bd (beads) references OR phantom br commands
# that need migration to the real br binary.
#
# Usage: ./find-bd-refs.sh [path]
# Exit codes:
#   0 — no migration needed
#   1 — migration needed

set -euo pipefail

path="${1:-.}"

echo "=== bd → br Migration Discovery ==="
echo "Scanning: $path"
echo ""

# bd command refs (backtick-prefixed)
bd_files=$(grep -rl '`bd ' "$path" --include="*.md" 2>/dev/null || true)
if [[ -n "$bd_files" ]]; then
    echo "Files with \`bd\` command references:"
    echo "$bd_files" | sed 's/^/  /'
    echo ""
fi

# bd sync (high-stakes)
sync_files=$(grep -rl 'bd sync' "$path" --include="*.md" 2>/dev/null || true)
if [[ -n "$sync_files" ]]; then
    echo "Files with 'bd sync' (critical — work-loss risk):"
    echo "$sync_files" | sed 's/^/  /'
    echo ""
fi

# bd-NNNN IDs
id_files=$(grep -rlE 'bd-[0-9a-z]{3,}' "$path" --include="*.md" 2>/dev/null || true)
if [[ -n "$id_files" ]]; then
    echo "Files with bd-NNNN issue IDs:"
    echo "$id_files" | sed 's/^/  /'
    echo ""
fi

# Phantom commands in files that LOOK migrated (still need fixing)
phantom_files=$(grep -rlE 'br prime|br compact|br doctor --fix|--add-note|--description-file' \
                "$path" --include="*.md" 2>/dev/null || true)
if [[ -n "$phantom_files" ]]; then
    echo "Files with phantom br commands (don't exist in real binary):"
    echo "$phantom_files" | sed 's/^/  /'
    echo ""
fi

# Bare `br sync` without mode flag
bare_sync_files=$(grep -rlE 'br sync($|[^-])' "$path" --include="*.md" 2>/dev/null \
                  | xargs -r grep -L -- '--flush-only\|--import-only\|--merge\|--status' || true)
if [[ -n "$bare_sync_files" ]]; then
    echo "Files with bare 'br sync' (missing mode flag):"
    echo "$bare_sync_files" | sed 's/^/  /'
    echo ""
fi

# Combined unique list
all_files=$(printf '%s\n' "$bd_files" "$sync_files" "$id_files" "$phantom_files" "$bare_sync_files" \
            | grep -v '^$' | sort -u || true)
total=$(printf '%s\n' "$all_files" | grep -c . 2>/dev/null || echo "0")

echo "=== Summary ==="
[[ -n "$bd_files" ]]      && echo "Files with bd commands:           $(echo "$bd_files" | grep -c .)"
[[ -n "$sync_files" ]]    && echo "Files with bd sync:               $(echo "$sync_files" | grep -c .)"
[[ -n "$id_files" ]]      && echo "Files with bd-NNNN IDs:           $(echo "$id_files" | grep -c .)"
[[ -n "$phantom_files" ]] && echo "Files with phantom br commands:   $(echo "$phantom_files" | grep -c .)"
[[ -n "$bare_sync_files" ]] && echo "Files with bare 'br sync':       $(echo "$bare_sync_files" | grep -c .)"
echo ""
echo "Total unique files needing migration: $total"

if [[ "$total" -gt 0 ]]; then
    echo ""
    echo "=== Strategy ==="
    if   [[ "$total" -le 5 ]];  then echo "Sequential ($total files)"
    elif [[ "$total" -le 15 ]]; then echo "2 parallel subagents (~$((total/2)) files each)"
    elif [[ "$total" -le 50 ]]; then echo "5 parallel subagents (~$((total/5)) files each)"
    else                              echo "8 parallel subagents (~$((total/8)) files each)"
    fi
    exit 1
else
    echo ""
    echo "✓ No migration needed."
    exit 0
fi
