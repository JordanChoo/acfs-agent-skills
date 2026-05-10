# Pitfalls Catalog

Each entry: **symptom → cause → diagnose → fix.** Drawn from CASS session logs of actual failures.

---

## P1 — Forgotten `git add .beads/` after sync (the work-loss bug)

**Symptom:** End-of-session, agent ran `br sync --flush-only` and `git push`. New issues / status changes are missing on the remote. Coworker agent sees stale state.

**Cause:** Migrated `AGENTS.md` has `br sync --flush-only` but no `git add .beads/` line. Agent followed docs and skipped staging.

**Diagnose across all migrated files:**
```bash
for f in /data/projects/*/AGENTS.md; do
  syncs=$(grep -c 'br sync --flush-only' "$f")
  adds=$(grep -c 'git add .beads/' "$f")
  if [ "$syncs" -gt 0 ] && [ "$adds" -lt "$syncs" ]; then
    echo "MISSING: $f  ($syncs syncs, $adds adds)"
  fi
done
```

**Fix:** every `br sync --flush-only` block must be immediately followed by:
```bash
git add .beads/
git commit -m "sync beads"
```

CASS prevalence: **66 sessions** of agents who synced but never staged.

---

## P2 — `bd sync` left in (incomplete sync transform)

**Symptom:** Agent following migrated docs runs `bd sync` and hits `command not found` (if bd is uninstalled) or, worse, runs the OLD bd binary that auto-commits.

**Cause:** Migration touched commands but missed prose / numbered-list mentions of `bd sync`.

**Diagnose:** `grep -n 'bd sync' file.md` — must return zero matches.

**Fix:** replace every `bd sync` with `br sync --flush-only` followed by the git pair.

CASS prevalence: **51 sessions** with both `bd sync` and `br sync --flush-only` co-resident in the same migrated docs.

---

## P3 — Phantom commands (br prime / br compact / br doctor --fix)

**Symptom:** Agent runs the command from migrated docs, hits "unrecognized subcommand" or "unexpected argument".

**Examples from CASS:**
- `br prime` failing across sessions 11, 16, 17, 18, 26, 29, 37, 49 (and more)
- `br doctor --fix` rejected — flag is `--repair`
- `br compact --analyze` rejected — no compact subcommand

**Cause:** Inherited from an aspirational design doc. Never existed in shipped `br`.

**Fix during migration:**
```bash
sed -i '/br prime/d; /br compact/d' file.md
sed -i 's/br doctor --fix/br doctor --repair/g' file.md
```

For `br prime` specifically, replace the section's "orient yourself" instructions with `bv --robot-triage`.

---

## P4 — `--add-note` doesn't exist

**Symptom:** `br update <id> --add-note "..."` errors with `unexpected argument '--add-note'`.

**Cause:** Migration target has `--add-note` from old docs. The real flag is `--notes`, which **replaces**.

**Fix:** rewrite to a read-modify-write append:
```bash
existing=$(br show <id> --json | jq -r '.notes // ""')
br update <id> --notes "$(printf '%s\n\n%s' "$existing" "New entry")"
```

---

## P5 — `br create -d` corrupts JSONL via shell escaping

**Symptom:** `br create` returns 0 but subsequent `br create` / `br list` fails with `invalid JSON at line N` in `.beads/issues.jsonl`.

**Cause:** The `-d "…"` argument contained backticks (triggering shell substitution), unescaped newlines, or shell metacharacters that `br` wrote literally into the JSONL row.

**Diagnose:**
```bash
jq -c . .beads/issues.jsonl >/dev/null   # finds the bad line
sed -n '<line>p' .beads/issues.jsonl
```

**Fix the corruption:**
```bash
git checkout -- .beads/issues.jsonl   # if untouched on remote
# OR
br doctor --repair                    # rebuilds DB from JSONL after manual edit
```

**Prevent:** use bulk-import or heredoc patterns from SKILL.md §4.3.

---

## P6 — `.beads/issues.jsonl` invisible after sync

**Symptom:** `br sync --flush-only` reports exports; `git status` shows clean tree; `git diff .beads/` is empty; commit fails as empty.

**Cause:** `skip-worktree` bit set on the file (or `.git/info/exclude` lists it). git silently ignores changes.

**Diagnose:**
```bash
git ls-files -v .beads/ | grep -E '^[sS]'    # 'S' = skip-worktree
grep -F '.beads/' .git/info/exclude
```

**Fix:**
```bash
git update-index --no-skip-worktree .beads/issues.jsonl
# Edit .git/info/exclude to remove .beads/ entries if present
git add -f .beads/issues.jsonl
```

CASS prevalence: session 17 spent ~370 messages diagnosing this. The migrated docs should mention it.

---

## P7 — lint-staged drops `.beads/` from commits

**Symptom:** `git add .beads/` then `git commit` reports "nothing to commit" or commit lands without `.beads/` files.

**Cause:** lint-staged stashes the worktree, runs hooks against staged files only, then restores. Files outside its glob (like `.beads/`) get dropped during stash/pop. Husky pre-commit can also re-stage and clobber.

**Workaround (proven across CASS sessions):**
```bash
git add .beads/
HUSKY=0 git commit --no-verify -m "sync beads" -- .beads/
```
**Important:** only bypass hooks for the *beads-only* commit. Code commits should run hooks normally.

---

## P8 — Worktree + beads DB

**Symptom:** `br create` from `/tmp/myrepo-feature-x` (a worktree) errors out, or creates issues that the main checkout can't see.

**Cause:** `.beads/*.db` lives in the main repo's `.beads/` only. Worktrees don't get a separate DB; the auto-discover finds an empty / partial one or fails.

**Fix (rule for migrated docs):** all `br` mutations happen in the main checkout. Pull (or copy) the resulting `.beads/issues.jsonl` into worktrees as needed before committing there.

---

## P9 — Bare `bv` launches blocking TUI

**Symptom:** Agent's session hangs after invoking `bv` (no flags). No output, no prompt.

**Cause:** `bv` defaults to an interactive curses TUI when no `--robot-*` flag is present.

**Fix:** migrated docs must use `bv --robot-triage` / `bv --robot-next` / `bv --robot-plan` etc. Strip any bare `bv` invocations.

---

## P10 — `br edit` hangs the agent

**Symptom:** Session hangs after `br edit <id>`. No prompt return.

**Cause:** Opens `$EDITOR` interactively. Non-TTY agent harnesses (Claude Code, Codex) have nowhere to type.

**Fix:** use `br update <id> --title/--description/--design/--acceptance-criteria/--notes`. Migrated docs should warn explicitly.

---

## P11 — Mixed bd-NNNN / br-NNNN IDs

**Symptom:** Confusing references; commit messages cite both `bd-1234` and `br-1234`.

**Cause:** Step 5 of the transform missed some IDs (often inside Agent Mail examples or commit message templates).

**Diagnose:**
```bash
grep -E 'bd-[0-9a-z]{3,}' file.md     # should be empty
```

**Fix:** rewrite all to `br-NNNN`. (Note: existing IDs in the live DB don't need migrating — they remain stable.)

---

## P12 — Bare `br sync` (without --flush-only)

**Symptom:** Behavior unclear; agent unsure if it imported, exported, or both.

**Cause:** Step 4 transform left `br sync` without `--flush-only`. `br sync` requires a mode flag (`--flush-only`, `--import-only`, `--merge`, or `--status`).

**Diagnose:** `grep -E 'br sync(\s|$)' file.md | grep -v -- '--flush-only\|--import-only\|--merge\|--status'`

**Fix:** in agent workflows, always `br sync --flush-only` (export only).

---

## P13 — False-positive verification PASS

**Symptom:** Verifier exits 0 with warnings; agent assumes done; runtime issues persist.

**Cause:** Warnings indicate genuine misses (most often: `br sync --flush-only` count > `git add .beads/` count, or no non-invasive note in a file that talks about beads).

**Fix:** treat warnings as failures during initial migration. Re-edit until PASS with **zero** warnings.

---

## Quick Diagnostics — single file

```bash
file="$1"

echo "=== $file ==="
echo "bd `bd ` refs:        $(grep -c '`bd ' "$file")           (must be 0)"
echo "bd sync:              $(grep -c 'bd sync' "$file")        (must be 0)"
echo "bd-NNNN ids:          $(grep -cE 'bd-[0-9a-z]{3,}' "$file") (must be 0)"
echo "br prime:             $(grep -c 'br prime' "$file")       (must be 0)"
echo "br compact:           $(grep -c 'br compact' "$file")     (must be 0)"
echo "br doctor --fix:      $(grep -c 'br doctor --fix' "$file") (must be 0)"
echo "--add-note:           $(grep -c '--add-note' "$file")     (must be 0)"
echo "--description-file:   $(grep -c -- '--description-file' "$file") (must be 0)"
echo "br sync --flush-only: $(grep -c 'br sync --flush-only' "$file") (>0 if file has sync)"
echo "git add .beads/:      $(grep -c 'git add .beads/' "$file") (== sync count)"
echo "non-invasive note:    $(grep -c 'non-invasive' "$file")   (>=1 if file has beads)"
```
