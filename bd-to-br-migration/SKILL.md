---
name: bd-to-br-migration
description: >-
  Migrate docs from bd (beads) to br (beads_rust). Use when updating AGENTS.md,
  converting bd commands, "bd sync" → "br sync --flush-only", or beads migration.
---

<!-- TOC: TL;DR | Real Command Surface | Banned Commands | The 7-Step Transform | Runtime Gotchas To Encode | Validation | Bulk Mode | References -->

# bd → br Migration

> **Premise:** A migrated `AGENTS.md` is read by agents who then *run the commands in it*. So the migration must produce docs that match the **real `br` binary** and warn about the gotchas agents hit at runtime. Mechanical find-replace is not enough.

---

## TL;DR — Single File

```bash
# 1. Discover
./scripts/find-bd-refs.sh /path/to/dir

# 2. Apply the 7-step transform (see below) using your editor

# 3. Verify (must exit 0)
./scripts/verify-migration.sh /path/to/file.md
```

If verifier exits 2 or prints any `BANNED` line, the file is not done — re-edit and re-run.

---

## Real Command Surface (br v0.2+)

Verified by running `br --help` against the installed binary. Use **only** these in migrated docs.

| Real command | Notes |
|---|---|
| `br ready` / `br ready --json` | List ready (open, unblocked) issues |
| `br list` / `br list --status open --json` | Filter listing |
| `br show <id> --json` | Issue details |
| `br create -t task -p 2 -d "…"` | Inline description (see escaping gotcha §4) |
| `br create -f <markdown>` | **Bulk import** from a markdown file — preferred for multi-line descriptions |
| `br q <title>` | Quick capture; prints ID only |
| `br update <id> --status in_progress` | Change status |
| `br update <id> --notes "…"` | **REPLACES** notes (no append flag exists; see §4) |
| `br update <id> --claim` | Atomic: assignee=actor + status=in_progress |
| `br close <id> -r "Done"` | Close; supports multiple IDs |
| `br close <id> --suggest-next` | Returns newly unblocked issue |
| `br dep add <from> <to>` | Add dependency |
| `br stats` | Project stats |
| `br doctor` / `br doctor --repair` | Diagnostics; `--repair` (NOT `--fix`) rebuilds DB from JSONL |
| `br sync --flush-only` | Export DB → JSONL (no git ops) |
| `br sync --import-only` | Import JSONL → DB |
| `br sync --status` | Read-only sync status |
| `br where` / `br info` | Locate `.beads/` workspace |
| `br --no-auto-flush <cmd>` | Default is **auto-flush on**; this disables it |

Querying/triage is delegated to `bv` (sidecar). In migrated docs, prefer `bv --robot-triage` / `bv --robot-next` for *what to work on*; use `br` for mutations and single-issue detail.

---

## Banned Commands — DO NOT propagate (they don't exist)

The migration target docs frequently contain phantoms inherited from drafts or old versions of beads. **Strip them.** The verifier fails on any of these:

| Phantom | Reality | Replace with |
|---|---|---|
| `br prime` | Unrecognized subcommand | Delete the line. Use `bv --robot-triage` for orient/triage. |
| `br compact …` | No `compact` subcommand | Delete the section. (br has no compaction yet.) |
| `br doctor --fix` | Flag is `--repair` | `br doctor --repair` |
| `br update … --add-note "…"` | No append flag exists | See §4 — read current `--notes`, append, write back |
| `br create … --description-file <path>` | No such flag | Use `br create -f <markdown>` (bulk) **or** `br create -d "$(cat /tmp/desc.md)"` |
| `bd …` (any bd command after migration) | bd is the old binary | `br …` |
| `bd sync` | bd auto-committed; br does not | `br sync --flush-only` + manual `git add .beads/ && git commit` |
| `bd-NNNN` issue IDs in new content | Stale ID convention | `br-NNNN` |

**Why these slipped in:** the original AGENTS.md template across this user's projects propagated `br prime`, `br compact`, `br doctor --fix`, and `br update --add-note` from an aspirational design doc. CASS sessions show agents repeatedly hitting "unrecognized command" errors on these in production. Treat them as real bugs to fix during migration, not as commands to translate.

---

## The 7-Step Transform

Apply **in order** (later steps depend on earlier ones).

```
1. Section headers       "bd (beads)" → "br (beads_rust)"
2. Non-invasive note     Insert immediately under the beads section header (see template)
3. Command renames       bd ready/list/show/create/update/close/dep/stats → br <same>
4. Sync transform        bd sync → br sync --flush-only  + git add .beads/ + git commit
5. Issue IDs             bd-NNNN → br-NNNN  (thread_ids, subjects, reasons, commit msgs)
6. Strip phantoms        br prime / br compact / br doctor --fix / --add-note / --description-file
7. Add runtime gotchas   skip-worktree, lint-staged, br edit, bare bv, worktree+DB (see §4)
```

### Step 2 — The non-invasive note (required template)

Paste verbatim under the migrated section header:

```markdown
**Note:** `br` is non-invasive — it never executes git commands. After every `br sync --flush-only` (or any mutation, since auto-flush is on by default), you must manually:

```bash
git add .beads/
git commit -m "sync beads"
```

If `git status` shows no `.beads/` changes after a mutation, see §4 (skip-worktree gotcha).
```

### Step 4 — Sync transform (the high-stakes one)

```
bd sync                           br sync --flush-only
                          →       git add .beads/
                                  git commit -m "sync beads"
```

Two reasons agents lose work here:
- They translate `bd sync` to `br sync` (missing `--flush-only`) — verifier catches this.
- They translate `bd sync` to `br sync --flush-only` but forget the `git add` lines — verifier catches this when sync count > 0 and `git add .beads/` count == 0.

### Step 6 — Strip phantoms (mechanical)

```bash
# In the migrated file, delete any line matching:
sed -i '/br prime/d;          /br compact/d' file.md
sed -i 's/br doctor --fix/br doctor --repair/g' file.md
# --add-note and --description-file: rewrite in editor (see §4 for replacement patterns)
```

### Step 7 — Add the runtime gotchas section

If the file is an `AGENTS.md` (vs. a one-off doc), append the §4 block below to the beads section. Skip for short reference snippets.

---

## §4 — Runtime Gotchas To Encode in Migrated Docs

These are the mistakes agents made in CASS sessions when running migrated docs. Migrated `AGENTS.md` files should include this material verbatim.

### 4.1 `.beads/issues.jsonl` invisible after sync (skip-worktree)

**Symptom:** `br sync --flush-only` succeeds; `git status` shows no `.beads/` changes; commit fails or is empty.

**Cause:** `.beads/issues.jsonl` has the `skip-worktree` bit set (or is in `.git/info/exclude`), so git ignores modifications.

**Diagnose & fix:**
```bash
git ls-files -v .beads/ | grep -i '^[sS]'   # 'S' = skip-worktree set
git update-index --no-skip-worktree .beads/issues.jsonl
git add -f .beads/issues.jsonl              # -f bypasses excludes
```

### 4.2 lint-staged / Husky drops `.beads/` from the commit

**Symptom:** Commit reports "no changes added"; or `.beads/issues.jsonl` is staged but absent from the resulting commit.

**Cause:** lint-staged stashes-and-restores worktree state around hooks; `.beads/` files outside its glob get dropped. Husky may also re-stage and clobber.

**Workaround:** stage and commit `.beads/` in a **separate commit** with hooks disabled:
```bash
git add .beads/
HUSKY=0 git commit -m "sync beads" --no-verify -- .beads/
```
Then make the code commit separately. Don't bypass hooks for code commits.

### 4.3 `br create -d "…"` shell-escaping breaks JSONL

**Symptom:** `br create` "succeeds" but later commands fail with `invalid JSON at line N in .beads/issues.jsonl`.

**Cause:** Backticks in `-d` trigger shell command substitution; literal newlines / unescaped `<`, `>`, `!` in the description corrupt the JSONL row written by `br`.

**Safe patterns (in order of preference):**

```bash
# A. Bulk import from a markdown file — best for any non-trivial description
cat > /tmp/issue.md <<'EOF'
# Title here

## Description
Full multi-line text with `backticks`, "quotes", and $shell-like content.
EOF
br create -f /tmp/issue.md

# B. Heredoc → command substitution (single issue, inline)
DESC="$(cat <<'EOF'
Multi-line text with `backticks` and special chars.
EOF
)"
br create -t task -p 2 -d "$DESC" "Title"

# C. Last resort: -d "…" for a one-line ASCII description with no special chars
br create -t task -p 2 -d "Simple description" "Title"
```

Always **single-quote** the heredoc terminator (`<<'EOF'`) to disable interpolation.

If a prior bad call corrupted the JSONL, run `br doctor --repair` (rebuilds DB from a clean JSONL) or `git checkout -- .beads/issues.jsonl` and re-run.

### 4.4 `br update --notes` REPLACES — there is no append

**Symptom:** Agent uses `--add-note` (from old docs); `br` errors with "unexpected argument". Or agent uses `--notes` and overwrites earlier session notes.

**Append pattern:**
```bash
existing=$(br show <id> --json | jq -r '.notes // ""')
br update <id> --notes "$(printf '%s\n\n%s' "$existing" "New note")"
```

### 4.5 `br edit` hangs Claude Code / Codex

`br edit` opens `$EDITOR` interactively — non-TTY agent sessions hang forever. **Never use it.** Use `br update <id> --title/--description/--design/--acceptance-criteria/--notes …` instead.

### 4.6 Bare `bv` launches a blocking TUI

Always use `bv --robot-*` flags. Bare `bv` opens a curses UI and the session deadlocks. Common entry points:
```bash
bv --robot-triage     # Prioritized work + recommendations
bv --robot-next       # Single top pick + claim command
bv --robot-plan       # Parallel-execution tracks
```

### 4.7 Git worktrees + `.beads/*.db`

The SQLite DB lives in the **main repo's** `.beads/` directory. Running `br create` from a worktree often hits a partial / empty DB and fails.

**Rule:** all `br` mutations happen in the main repo. Then `git pull` (or copy `.beads/issues.jsonl`) into the worktree before committing there.

### 4.8 Auto-flush is on by default

br auto-flushes JSONL after every mutation (`--no-auto-flush` to disable). The explicit `br sync --flush-only` is a belt-and-suspenders barrier before commit — keep it in migrated docs even though many writes already flushed.

---

## Validation

```bash
./scripts/verify-migration.sh path/to/AGENTS.md
```

Exit codes:
- `0` — clean
- `1` — argument / file error
- `2` — migration incomplete: bd refs left, banned commands present, or required pattern missing

The verifier checks for: leftover `` `bd ` ``, leftover `bd sync`, `bd-NNNN` IDs, banned commands (`br prime`, `br compact`, `br doctor --fix`, `--add-note`, `--description-file`), the non-invasive note, and `git add .beads/` paired with each `br sync --flush-only`.

**Don't trust "PASS with warnings".** If you see warnings, read each one and decide — they often indicate genuine misses (e.g., file has `br sync --flush-only` but no `git add .beads/` because it's in a separate code block).

---

## Bulk Mode (10+ files)

```bash
./scripts/find-bd-refs.sh /data/projects   # discovers + recommends batch size
```

For 10+ files, dispatch the [batch-migrator subagent](subagents/batch-migrator.md) at ~10 files per batch. Run the verifier between batches; do not start batch N+1 until batch N is clean.

See [BULK.md](references/BULK.md) for the subagent prompt and commit strategy.

---

## References

| Need | File |
|---|---|
| Full transform examples (before/after blocks) | [TRANSFORMS.md](references/TRANSFORMS.md) |
| Bulk strategy + subagent prompt | [BULK.md](references/BULK.md) |
| Pitfalls catalog with diagnostics | [PITFALLS.md](references/PITFALLS.md) |
| Trigger phrases + functional tests | [SELF-TEST.md](SELF-TEST.md) |

---

## What this skill does NOT do

- It does **not** install or update `br` itself (use `br upgrade`).
- It does **not** migrate existing `bd-NNNN` issue IDs in the live DB — those are stable identifiers and the JSONL stays valid.
- It does **not** fix code references to bd outside docs (search separately if your codebase has them).
