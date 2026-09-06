# acfs-agent-skills

Cross-harness skill library for Claude Code and Codex. One source of truth, two `~/.<harness>/skills/` directories that symlink into it.

## Layout

```
~/src/acfs-agent-skills/                ← this repo (canonical source)
├── <skill-name>/
│   ├── SKILL.md                        ← required
│   ├── SELF-TEST.md                    ← optional
│   ├── references/                     ← optional, loaded as needed
│   ├── scripts/                        ← optional, executable
│   └── …
├── scripts/
│   ├── install.sh                      ← link skills into ~/.claude + ~/.codex
│   ├── audit-drift.sh                  ← report harness drift from this repo
│   ├── test-all.sh                     ← run every skill's self-test
│   └── tool-managed.txt                ← skills owned by their own installers
└── README.md
```

After `install.sh`:

```
~/.claude/skills/<name> ─┐
                         ├──► ~/src/acfs-agent-skills/<name>
~/.codex/skills/<name>  ─┘
```

Edit a skill once in the repo; both harnesses see it instantly.

## New machine bootstrap

```bash
gh repo clone <owner>/acfs-agent-skills ~/src/acfs-agent-skills
cd ~/src/acfs-agent-skills
bash scripts/install.sh
```

That's it. Both Claude Code and Codex now see every skill.

If you have pre-existing skills at the same names, `install.sh` refuses to overwrite real (non-symlink) directories — pass `--force` to back them up to `~/.<harness>-skills-backup-<timestamp>/` and replace. One blocked skill does not abort the run: the rest still link, and the script exits non-zero so you notice.

## Tool-managed skills

Some skills are written into `~/.claude/skills` and `~/.codex/skills` by their own tool's installer — currently `rch`, `pfr`, and `pi-agent-rust`, all refreshed nightly by the ACFS update job. They must stay real directories there: a symlink would be replaced, or written through into this repo, on the installer's next run.

`scripts/tool-managed.txt` lists them. `install.sh` never links or unlinks a listed skill (even with `--force`), and `audit-drift.sh` reports it as `◦ tool-managed` (counted as pass) instead of drift. The `rch/` directory in this repo is a reference snapshot of the installed skill, not the live copy; when the audit says the snapshot is behind, refresh it:

```bash
cp -R ~/.codex/skills/rch/. rch/ && git add rch && git commit -m "rch: refresh snapshot"
```

## Daily workflow

```bash
cd ~/src/acfs-agent-skills

# Check for cross-harness drift first.
bash scripts/audit-drift.sh

# Edit a skill in place — both harnesses see changes immediately.
$EDITOR cass/SKILL.md

# Run its self-test (if any).
bash scripts/test-all.sh --skill cass

# Or run the whole suite.
bash scripts/test-all.sh

# Reconcile symlinks into both harnesses.
bash scripts/install.sh

# Commit & push.
git add cass
git commit -m "cass: tighten happy path"
git push
```

## On another machine

```bash
cd ~/src/acfs-agent-skills
git pull
# No re-install needed — symlinks already point into this directory.
```

## Authoring conventions

Each skill should:

1. **Have a `SKILL.md` with YAML frontmatter** — required `name` and `description`. Both Claude Code and Codex read these to decide when to surface the skill.
2. **Be self-locating in scripts** — never hardcode `~/.claude/skills/<name>` or `~/.codex/skills/<name>`. Use:
   ```bash
   SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
   ```
3. **Avoid Claude-only or Codex-only assumptions** — both harnesses run on bash; both honour `references/` and `scripts/` directories. Don't depend on harness-specific tools (`Skill` tool, `subagents/`) unless you fall back gracefully.
4. **Ship a `scripts/self-test.sh`** when feasible. `test-all.sh` invokes it. The tests should be read-only and fast.

## Subcommands

```
scripts/install.sh                  # link both harnesses
scripts/install.sh --claude-only
scripts/install.sh --codex-only
scripts/install.sh --force          # back up + replace real dirs at target
scripts/install.sh --dry-run
scripts/install.sh --uninstall      # remove only the symlinks we own

scripts/audit-drift.sh              # report non-symlinks, missing links, target mismatches (◦ = tool-managed, ok)
scripts/audit-drift.sh --json

scripts/test-all.sh                 # run every self-test
scripts/test-all.sh --skill cass    # one skill
scripts/test-all.sh --quiet
scripts/test-all.sh --json          # CI-friendly
```

## Adding a new skill

```bash
cd ~/src/acfs-agent-skills
mkdir -p new-skill/{references,scripts}
$EDITOR new-skill/SKILL.md          # write frontmatter + body
bash scripts/audit-drift.sh         # drift should be clean before install
bash scripts/install.sh             # idempotent — links the new skill
git add new-skill
git commit -m "add new-skill"
git push
```

## Removing a skill

```bash
cd ~/src/acfs-agent-skills
bash scripts/install.sh --uninstall    # removes ALL symlinks we own (safe; real dirs untouched)
git rm -r <skill-name>
bash scripts/install.sh                # relink the remaining skills
git commit -m "remove <skill-name>"
git push
```

## Rollback

If you need to undo `install.sh` and restore previously-installed real directories:

```bash
ls ~/.claude-skills-backup-*  ~/.codex-skills-backup-*    # find the backup
mv ~/.claude-skills-backup-<ts>/<name> ~/.claude/skills/<name>
mv ~/.codex-skills-backup-<ts>/<name>  ~/.codex/skills/<name>
```
