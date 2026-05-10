# Bulk Migration

For 10+ files, dispatch parallel subagents at ~10 files per batch. Verify each batch before starting the next.

---

## Discovery

```bash
./scripts/find-bd-refs.sh /data/projects
```

Output includes a recommended strategy based on file count:
- 1–5 files → sequential (overhead not worth it)
- 6–15 → 2 subagents
- 16–50 → 5 subagents (~10 each)
- 50+ → 8 subagents

The discovery script also flags files that already have *phantom commands* (`br prime`, `br compact`, etc.) — these need migration even if they look "post-bd".

---

## The Subagent Prompt

Use the [batch-migrator subagent](../subagents/batch-migrator.md) (definition for Claude Code subagents). For one-off invocations, paste the following into a Task tool call:

```
Migrate these files from bd (beads) to br (beads_rust):

FILES:
- /data/projects/proj1/AGENTS.md
- /data/projects/proj2/AGENTS.md
[…up to ~10…]

Apply the 7-step transform from
the SKILL.md in this skill directory (~/.claude/skills/bd-to-br-migration or ~/.codex/skills/bd-to-br-migration) — read it first.

Required output for each file:
1. All bd commands renamed to br
2. All `bd sync` → `br sync --flush-only` followed immediately by:
     git add .beads/
     git commit -m "sync beads"
3. All bd-NNNN IDs in doc text rewritten to br-NNNN
4. Phantom commands STRIPPED (do NOT translate them):
     - `br prime` → delete line, replace orient instructions with `bv --robot-triage`
     - `br compact …` → delete the section/line
     - `br doctor --fix` → `br doctor --repair`
     - `br update … --add-note …` → read-modify-write with `br show --json | jq` then `--notes`
     - `br create … --description-file <path>` → `br create -f <path>` or heredoc
5. Non-invasive note inserted under each beads section header (template in SKILL.md §3)
6. Daemon / RPC / auto-commit / git-hook sections DELETED
7. (For AGENTS.md files only) Runtime gotchas section appended (template in SKILL.md §4)

After EACH file, run:
  ./scripts/verify-migration.sh <file>

Do not proceed to the next file if verification exits non-zero.

Report one line per file:
  ✓ /path/file.md — migrated, verified
  ✗ /path/file.md — FAILED: <specific reason>

When all files in your batch pass, return the report.
```

---

## Batching Rules

1. **One agent per batch** — never overlap files between agents.
2. **~10 files max per batch** — context size + verification overhead.
3. **Group similar files** — projects in the same family migrate the same way.
4. **Verify each batch before the next** — `./scripts/verify-migration.sh batch/*.md`.

---

## Per-Batch Verification

```bash
fail=0
for f in /data/projects/{proj1,proj2,…}/AGENTS.md; do
  ./scripts/verify-migration.sh "$f" || { echo "FAIL: $f"; fail=1; }
done
[ "$fail" -eq 0 ] && echo "Batch clean" || echo "Batch has failures"
```

---

## Commit Strategy

### Option A — One commit per batch (recommended for traceability)

```bash
git add /data/projects/proj{1..10}/AGENTS.md
git commit -m "$(cat <<'EOF'
docs: migrate AGENTS.md from bd → br (batch 1/N)

Files: 10 AGENTS.md across proj1..proj10
Transforms: bd→br renames; bd sync → br sync --flush-only + manual git;
            bd-### → br-###; phantom commands stripped (br prime, br compact,
            br doctor --fix, --add-note, --description-file); runtime gotchas
            section appended.
EOF
)"
```

### Option B — Per-project commits

```bash
for project in /data/projects/*/; do
  [ -f "$project/AGENTS.md" ] || continue
  git add "$project/AGENTS.md"
  git commit -m "docs($(basename "$project")): migrate AGENTS.md bd → br"
done
```

---

## Rollback

```bash
# Single file
git checkout -- /data/projects/PROJECT/AGENTS.md

# Restore everything that fails verification
for f in /data/projects/*/AGENTS.md; do
  ./scripts/verify-migration.sh "$f" >/dev/null 2>&1 || git checkout -- "$f"
done
```

---

## Progress Tracking (for very large migrations)

Keep a scratch file:

```markdown
# bd → br Migration Progress

| Batch | Files | Status | Verified |
|---|---|---|---|
| 1 | proj1..proj10 | done | 10/10 |
| 2 | proj11..proj20 | in progress | 4/10 |
| 3 | proj21..proj30 | queued | – |

## Issues encountered
- proj_x: no beads section — skipped
- proj_y: custom bd wrapper script — manual review queued
```
