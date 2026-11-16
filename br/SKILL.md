---
name: br
description: >-
  How to use br (beads_rust), the dependency-aware issue tracker in `.beads/` (SQLite
  beads.db plus git-tracked issues.jsonl), without the mistakes agents repeat. Use when
  picking, claiming, creating, updating or closing beads; syncing `.beads/` with git;
  after a git pull or rebase; resolving an issues.jsonl conflict; on errors such as
  "cannot claim blocked issue", "database is busy", "Refusing to export stale database",
  "UNIQUE constraint failed", "unrecognized subcommand 'prime'" or "unexpected argument
  '--add-note'"; and when AGENTS.md br instructions disagree with `br --help`.
---

# br

br stores beads in `.beads/beads.db` and exports them to `.beads/issues.jsonl`, the file git
tracks. br never runs git; committing is your job. This skill was built from about 100 past
sessions on this VPS and checked against br 0.7.6 (`scripts/test_br.py` replays every failure
case below). Evidence: [references/evidence.md](references/evidence.md).

## The happy path

```bash
br ready --json                                   # 1. find unblocked work
br show <id> --json                               #    read it, check nobody holds it
br update <id> --claim --actor <your-name>        # 2. claim (atomic: assignee + in_progress)
# ... do the work, commit the code, rebase, push ...
br close <id> --reason "Completed. commit=<final sha>; tests: <names> passed"   # 3. close
br sync --flush-only                              # 4. export; always run it ("Nothing to export" is fine)
git add .beads/issues.jsonl                       # 5. stage the tracker explicitly
git commit -m "beads: close <id>" && git push     # 6. the close is a change too: commit and push it
```

After a `git pull`, or once a rebase has finished, run `br sync --import-only` before any other
br command. (During a conflicted rebase, follow the conflict recipe below instead.)

Names used below: `--actor` is your Agent Mail name (or your agent's name if the project has no
Agent Mail). "The owner" is the human you work for. "Message the holder" means Agent Mail (see
the agent-mail-ops skill), or a `br comments add` on the bead when Agent Mail is down.

## When AGENTS.md and br disagree, br wins

Several AGENTS.md files on this VPS teach commands br 0.7.6 does not have. Check with
`br <command> --help` and use the real one:

| Written in some AGENTS.md | Use instead |
| --- | --- |
| `br prime` | `br ready --json` (and `br robot-docs guide` for the agent guide) |
| `br import -i .beads/issues.jsonl` | `br sync --import-only` |
| `br update <id> --add-note "..."` | `br update <id> --append-notes "..."` or `br comments add <id> "..."` |
| `br update <a> --blocks <b>` | `br dep add <b> <a>` (b depends on a) |
| `br list --parent <id>` | `br ready --parent <id> --json`, or `br show <id> --json` |
| `br update <id> --status closed` | `br close <id> --reason "..."` |
| `br doctor --fix` | `br doctor` first (read-only); `--fix` is an alias of `--repair`, which **rebuilds the DB from JSONL**: dry-run it first |

If you fix a project's AGENTS.md, say so in a bead comment so other agents know.

## Rules

### Claiming
- **Never use `--force` to claim.** br refuses to claim a blocked issue and refuses a second
  `--claim` on a held one; `--force` silently replaces a live claim (confirmed in tests; it
  overwrote two agents' claims in rusty-jev). Blocked: pick other work or work the blocker.
  Held: message the holder. Owner says take it: then `--force`, with a comment saying why.
- **Recommendations go stale.** `bv --robot-next` and old triage output can name beads
  already in progress. Re-check `br show <id> --json` (status, assignee) right before claiming.
- **Cannot finish?** Return the claim with evidence instead of leaving it stale:
  `br update <id> --status open --assignee ""` and a `br comments add` saying what is done
  and what blocks it.

### Closing
- **Close only after the work is on the remote.** Commit, rebase, push, then close. A commit
  hash cited before the final rebase may never reach main.
- **The reason is evidence**, not "Completed": the final sha and the tests that actually ran.
  Follow the project's closure rules (for example an `acceptance-tests` block). A test that
  did not run is not a pass; leave the bead open.
- To close epics, run `br epic close-eligible --dry-run` first; without `--dry-run` it closes.
  Closed something by mistake: `br reopen <id>` with a comment saying why.

### Writing and quoting
- **Run br writes one at a time.** Parallel `br` writes (a close and a sync fired together,
  several dependency edits at once) fail with "database is busy". After that error, check with
  `br show <id> --json` whether the write landed before repeating it. If another agent may be
  writing, add `--lock-timeout 30000` (milliseconds; two separate words).
- **Long text goes in files:** `--description-file f.md`, `br comments add <id> -f f.md`.
  Never keep a flag in a zsh variable: zsh passes `"$FLAGS"` as one word.
- **Add, do not rewrite:** `--append-notes`, `--add-acceptance`, `br comments add`. Rewriting
  `--notes` or `--description` loses what was there.
- Priority is `0`-`4` or `P0`-`P4`, never `high`. Types: task, bug, feature, epic, chore,
  docs, question.
- **Check a change with `br show <id> --json`**, not by grepping issues.jsonl (`.13` also
  matches `.130`) and never with `sqlite3`.

### The database and the JSONL
- **Never write to `beads.db` with SQL, never delete it, never commit it.** It is local and
  disposable; issues.jsonl is the truth that git carries.
- **"Refusing to export stale database that would lose issues"** means the JSONL has issues
  the DB lacks (usually after a pull). Run `br sync --import-only`, then
  `br sync --flush-only`. Do not use `--force` or `--allow-stale`.
- **"UNIQUE constraint failed"** on import: run `br doctor --robot-triage` and follow its
  recommendation. `br sync --import-only --rebuild` is the usual fix, but it **deletes DB
  entries that are not in the JSONL**: use it only after `br sync --status` shows the DB holds
  nothing the JSONL lacks, or after a successful `br sync --flush-only`.
- **Health:** `br doctor` (read-only) or `br doctor --robot-triage` (one JSON read). Repair
  only after `br doctor --repair --dry-run` shows the plan.
- **Worktrees:** if IDs are missing, run `br sync --import-only` there. Never copy
  issues.jsonl in or delete a DB to make it work.

### Git and issues.jsonl
- **Stage `.beads/issues.jsonl` explicitly**, never `git add -A` (it sweeps up other agents'
  code). The file is one export of everyone's beads, so it may hold other agents' changes too;
  committing them with yours is normal. Look at the diff first
  (`git diff .beads/issues.jsonl`, by bead ID) so you notice anything unexpected, such as a
  bead you did not mean to change. A separate tracker-only commit is fine.
- **Flushed but not staged** is the most common miss (66 sessions in one study). Check
  `git status --short .beads/` before you finish.
- **Merge or rebase conflict in issues.jsonl: never hand-pick lines, splice, or patch it with
  a script, and never commit one side as the answer.** Your own beads are in your local DB;
  let br merge in the other side and rewrite the file itself (tested; every step is allowed by
  the dcg hook, which blocks `git checkout --theirs/--ours -- <file>` and `git restore`):
  1. resolve the code conflicts first;
  2. write the other side's version beside the file, naming the ref you are rebasing onto or
     merging in: `git show origin/main:.beads/issues.jsonl > .beads/issues.incoming.jsonl`;
  3. `BEADS_JSONL=.beads/issues.incoming.jsonl br sync --import-only` (your DB now holds both);
  4. `br sync --flush-only --force`: br regenerates issues.jsonl from the DB, replacing the
     conflict markers. This is the one place `--force` belongs, because br, not you, writes
     the file from a DB that holds everything;
  5. check your beads and theirs with `br show <id> --json`, then `git add .beads/issues.jsonl`
     (never the `issues.incoming.jsonl` sidecar; leave it untracked, or ask the owner before
     removing it) and continue the rebase. When it finishes, `br sync --import-only`.

  Two traps found while testing: with markers in the file, `br sync --flush-only` and
  `br sync --merge` both refuse; and a plain `--import-only` then `--flush-only` exports
  nothing ("no dirty issues"), so the file silently loses your beads. If issues.jsonl has no
  conflict markers but you suspect it lacks the other side's beads (for example after a merge
  git resolved on its own), `br sync --merge` alone is enough. If br reports a semantic
  conflict (one bead edited on both sides), inspect both versions and ask; do not pick with
  `--force-db` or `--force-jsonl`.

### The work graph
- Search before creating: `br search "<words>"` and `br list --json`. Close a duplicate
  with a reason pointing to the original.
- **Announce graph changes first** (new epics, dependency edges, re-parenting) in the
  project's coordination channel. `br dep add <issue> <depends-on>`; br refuses cycles, and
  `br dep cycles` must stay empty.
- Commit new beads promptly; one audit found 400 bead creations left uncommitted.
- Never run bare `bv` (it opens a TUI); use `bv --robot-triage` or `bv --robot-next`.

## Quick reference (br 0.7.6)

```bash
br create --title "T" -t task -p 2 --description-file d.md --labels a,b --parent <epic> --json
br update <id> --claim --actor <name>
br update <id> --append-notes "..." --add-acceptance "..."
br comments add <id> "text"
br dep add <issue> <depends-on>
br close <id> --reason "..." --suggest-next
br sync --flush-only
br sync --import-only
br sync --status
br doctor --robot-triage
br robot-docs guide
```

## Self-test

`bash scripts/self-test.sh` replays every case in `scripts/test_br.py` (recorded failures
must fail, recommended commands must work) in throwaway projects, and checks that every
command in this file exists in the installed br.
