# Transform Reference

Concrete before/after blocks for each transform. Apply step-by-step in the order listed in SKILL.md.

> **Ground truth:** all `br` commands and flags here have been verified against `br --help` on the installed binary (br v0.2.x). If your local `br --help` shows different flags, **trust the binary, not these docs.**

---

## 1. Section Headers

| Before | After |
|---|---|
| `## Issue Tracking with bd (beads)` | `## Issue Tracking with br (beads_rust)` |
| `## Beads (bd)` | `## Beads (br)` |
| `## Beads (bd) — Dependency-Aware Issue Tracking` | `## Beads (br) — Dependency-Aware Issue Tracking` |
| `[beads_viewer](…)` | `[beads_rust](https://github.com/Dicklesworthstone/beads_rust)` |

---

## 2. Non-Invasive Note (insert under each beads section header)

```markdown
**Note:** `br` is non-invasive — it never executes git commands. After every `br sync --flush-only` (or any mutation, since auto-flush is on by default), you must manually:

```bash
git add .beads/
git commit -m "sync beads"
```

If `git status` shows no `.beads/` changes after a mutation, see the [skip-worktree gotcha](#skip-worktree).
```

---

## 3. Command Renames (mechanical)

```
bd ready              → br ready
bd ready --json       → br ready --json
bd list               → br list
bd list --status open → br list --status open
bd show <id>          → br show <id>
bd show <id> --json   → br show <id> --json
bd create -t task -p 2 -d "…" "Title"     → br create -t task -p 2 -d "…" "Title"
bd update <id> --status in_progress       → br update <id> --status in_progress
bd close <id> -r "Done"                   → br close <id> -r "Done"
bd dep add <a> <b>    → br dep add <a> <b>
bd stats              → br stats
```

If the source uses **`--add-note`**: rewrite to read-modify-write (no append flag in `br`):
```bash
existing=$(br show <id> --json | jq -r '.notes // ""')
br update <id> --notes "$(printf '%s\n\n%s' "$existing" "New note")"
```

If the source uses **`--description-file <path>`**: rewrite to bulk-import or heredoc:
```bash
# Option A (preferred for multi-line):
br create -f /tmp/issue.md

# Option B (heredoc):
DESC="$(cat <<'EOF'
…multi-line description…
EOF
)"
br create -t task -p 2 -d "$DESC" "Title"
```

---

## 4. Sync Transform (BEHAVIORAL — high stakes)

### Single sync

```bash
# BEFORE
bd sync

# AFTER
br sync --flush-only
git add .beads/
git commit -m "sync beads"
```

### Sync inside a session-end block

```bash
# BEFORE
git add <files>
bd sync
git push

# AFTER
git add <files>
br sync --flush-only
git add .beads/
git commit -m "feat: <desc> (br-<id>)"
git push
```

### Combined commit (code + beads in one)

```bash
# BEFORE
git add src/foo.ts
bd sync
git commit -m "feat: …"

# AFTER
br sync --flush-only        # ensure JSONL is current (auto-flush usually has it already)
git add src/foo.ts .beads/
git commit -m "feat: … (br-<id>)"
```

---

## 5. Issue ID Rewrites

```
thread_id: bd-123        → thread_id: br-123
subject: [bd-123] …      → subject: [br-123] …
reason: bd-123           → reason: br-123
commit -m "feat: … (bd-123)"  → commit -m "feat: … (br-123)"
```

(Existing IDs in `.beads/*.jsonl` remain stable; this transform only touches **doc references**.)

---

## 6. Strip Phantoms

| Doc snippet (BEFORE) | Action |
|---|---|
| `Run \`br prime\` for workflow context.` | **Delete** the line. Replace orient/triage instructions with `bv --robot-triage`. |
| `br compact --analyze --json` | **Delete** the section/line — no compact subcommand. |
| `br doctor --fix` | **Replace** with `br doctor --repair`. |
| `br update <id> --add-note "…"` | **Rewrite** to read-modify-write (see step 3). |
| `br create … --description-file <path>` | **Rewrite** to `br create -f <path>` or heredoc (see step 3). |
| `bd daemon` / "RPC mode" / "auto-commits" / "git hooks" sections | **Delete**. None apply to `br`. |

### sed one-liners

```bash
sed -i '/br prime/d' file.md
sed -i '/br compact/d' file.md
sed -i 's/br doctor --fix/br doctor --repair/g' file.md
```

(`--add-note` and `--description-file` need editor rewrite — sed can't generate the replacement code.)

---

## 7. Add Runtime Gotchas Section (AGENTS.md only)

For long-form `AGENTS.md` files, append the §4 Runtime Gotchas block from SKILL.md verbatim. For short reference snippets, skip.

---

## Full File Example

### Before
```markdown
## Issue Tracking with bd (beads)

All issue tracking goes through **bd**.

Run `bd prime` for context.

### Commands

- `bd ready` — find work
- `bd create -t task -p 2 -d "Fix auth"`
- `bd update <id> --status in_progress`
- `bd update <id> --add-note "Session end: stuck on retry logic"`
- `bd close <id>`
- `bd sync` — commits and pushes

### Maintenance

- `bd doctor --fix`
- `bd compact --analyze`

### Session End

```bash
git add <files>
bd sync
git push
```
```

### After
```markdown
## Issue Tracking with br (beads_rust)

**Note:** `br` is non-invasive — it never executes git commands. After every `br sync --flush-only` (or any mutation, since auto-flush is on by default), you must manually:

```bash
git add .beads/
git commit -m "sync beads"
```

If `git status` shows no `.beads/` changes after a mutation, see the skip-worktree gotcha in §4.

All issue tracking goes through **br**.

For triage / "what should I work on next?", use `bv --robot-triage` (sidecar; queries the same `.beads/`).

### Commands

- `br ready` — find work
- `br create -t task -p 2 -d "Fix auth" "Title"`
- `br update <id> --status in_progress`
- For appending notes: `existing=$(br show <id> --json | jq -r '.notes // ""'); br update <id> --notes "$(printf '%s\n\n%s' "$existing" "Session end: stuck on retry logic")"`
- `br close <id> -r "Done"`
- `br sync --flush-only` — exports DB → JSONL (no git ops)

### Maintenance

- `br doctor` (run with `--repair` to rebuild DB from JSONL)

### Session End

```bash
git add <files>
br sync --flush-only
git add .beads/
git commit -m "feat: … (br-<id>)"
git push
```
```

---

## Agent Mail Integration (thread IDs)

```
Mail thread_id:  bd-NNNN  → br-NNNN
Mail subject:    [bd-NNNN] …  → [br-NNNN] …
File reservation reason: bd-NNNN → br-NNNN
```

---

## Quick Search Patterns

```bash
# Anything still referencing bd commands
grep -nE '`bd (ready|list|show|create|update|close|dep|stats|sync)' file.md

# Bare `br sync` without a mode flag
grep -nE 'br sync($|[^-])' file.md | grep -v -- '--flush-only\|--import-only\|--merge\|--status'

# Phantoms
grep -nE 'br prime|br compact|br doctor --fix|--add-note|--description-file' file.md

# bd-NNNN IDs (excluding within URLs / br- IDs)
grep -nE '\bbd-[0-9a-z]{3,}\b' file.md
```
