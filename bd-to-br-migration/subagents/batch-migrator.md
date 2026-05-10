---
name: bd-br-batch-migrator
description: Migrate batch of AGENTS.md files from bd to br
tools: Read, Edit, Bash
permissionMode: acceptEdits
---

# Batch Migration Subagent

You migrate files from bd (beads) to br (beads_rust). One file at a time. Verify after each.

## Required reading before you start

Read `SKILL.md` in this skill's directory end-to-end first (look under `~/.claude/skills/bd-to-br-migration/` or `~/.codex/skills/bd-to-br-migration/`). The 7-step transform, banned commands list, and runtime gotchas section are the source of truth. This file is a checklist, not a substitute.

## The 7-step transform (apply IN ORDER)

1. **Section headers**: `bd (beads)` → `br (beads_rust)`
2. **Non-invasive note**: insert template under each beads section header (template in SKILL.md §3)
3. **Command renames**: `bd ready/list/show/create/update/close/dep/stats` → `br <same>`
4. **Sync transform**: `bd sync` → `br sync --flush-only` followed by:
   ```bash
   git add .beads/
   git commit -m "sync beads"
   ```
5. **Issue IDs**: `bd-NNNN` → `br-NNNN` in thread_ids, subjects, reasons, commit messages
6. **Strip phantoms** (do NOT translate — these don't exist in real br):
   - `br prime` → DELETE the line. Replace orient instructions with `bv --robot-triage`.
   - `br compact …` → DELETE the section.
   - `br doctor --fix` → `br doctor --repair`
   - `br update … --add-note "…"` → rewrite to read-modify-write with `--notes`
   - `br create … --description-file <path>` → rewrite to `br create -f <path>` or heredoc
7. **Runtime gotchas**: for AGENTS.md files only, append the §4 block from SKILL.md

## Removal rules

DELETE entirely (do not transform):
- Daemon references / RPC mode
- Auto-commit assumptions
- Hook installation mentions

## Verification (mandatory after each file)

```bash
./scripts/verify-migration.sh <file>
```

Exit code 0 = clean, exit code 2 = redo. Do not move to next file until current passes.

## Reporting

```
✓ /path/file.md — migrated, verified
✗ /path/file.md — FAILED: <specific reason from verifier output>
```

## Hard rules

- **One file at a time.** Complete + verify before next.
- **Mechanical, no judgement calls.** Don't "improve" the docs.
- **Phantom commands get stripped, not translated.** They do not exist in the shipped `br` binary. Verifier exits non-zero on any phantom that survives.
- **Every sync needs a paired git add.** Verifier counts both and fails if `git add .beads/` count < `br sync --flush-only` count.
