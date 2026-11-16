# br in past sessions: evidence

Source: `cass` over Claude Code and Codex sessions on this VPS (2026-11-16): about 105 events read
in context across 13 projects, in two passes (command errors; workflow discipline). Counts from
search hits are lower bounds. `co:` is `~/.codex/sessions/2026/`, `cl:` / `C` is
`~/.claude/projects/`; numbers are message indices (`cass expand --message-index`).

## Command errors

| Problem | Count | Examples |
| --- | ---: | --- |
| `br prime` (from philomena and big-flare AGENTS.md line 3): "unrecognized subcommand 'prime'" | 120 sessions | co:03/27 T23-23-39:10, co:03/28 T01-18-45:44 |
| `--add-note` (philomena, big-flare AGENTS.md); then whole `--notes` rewrites | 8+ sessions | co:03/05:2235 and :2898; co:04/26:1511-1512 |
| `br import -i` (scry AGENTS.md:213) | about 14 | co:03/22:2117 |
| `br doctor --fix` rejected by older br (scry AGENTS.md:461); 0.7.6 accepts it as an alias of `--repair`, a DB rebuild | 5 sessions | co:03/13 T19-24-49:225 |
| `update --blocks` (philomena AGENTS.md:351) | 1+ | co:03/13 T01-51-14:896 |
| "database is busy" from parallel writes | 44 sessions | co:03/10:207-210; fixed by sequencing (co:03/20:3890) |
| "Refusing to export stale database that would lose issues"; about 6 turns each before `--import-only` | 10 sessions | co:03/22:2113, co:04/26:1325 |
| `UNIQUE constraint failed` on import | 27 sessions | co:03/15:1075 (recovered with `--rebuild`) |
| Guessed flags (`list --parent`, `dep tree --depth`, `list --query`, `epic status <id>`) | about 7 | co:03/13 T22-45-54:459 |
| zsh passing a flag stored in a variable as one word | 2 | cl:hugh 5af828ad:560, :1047 |
| `epic close-eligible` used to list (it closes) | 1 | cl:hugh agent-aad4e4ab:99 |

## Workflow

| Problem | Count | Examples |
| --- | ---: | --- |
| `--force` to claim past "cannot claim blocked issue", overwriting live assignees | about 22 | co:03/11:2136; C rusty-jev 06c74ad3:3660; memory `check-before-force-claim.md` (two overwrites) |
| Closed before the work landed; bare "Completed" reasons; reopen churn | about 20 | C scry 2c493b3e:604 (six beads closed with nothing on origin); C philomena-agent cc399ae1:9 |
| SQL against beads.db, deleting it, committing it | about 20 | co:04/28:711, co:03/19:410 (`DELETE FROM export_hashes`); co:04/10:4691 (`rm beads.db`) |
| issues.jsonl conflicts settled by one side, splicing, regex or awk scripts | about 12 | co:03/15:1512, :2196, :2210; C philomena-agent 9d9f4ee7:9911 (the owner banned splicing: "regenerate the file from the canonical DB under the lock") |
| Flushed but `.beads/issues.jsonl` never staged | 66 sessions in an earlier study | C -home-ubuntu e8e131fe:144 |
| `git add -A` sweeping other agents' bead changes | about 10 | co:03/30:1139; good practice: diff by bead ID (C scry b6ef7405:343) |
| Stale `bv --robot-next` picks already in progress | about 12 | co:04/27:1328, co:03/07:1470 |
| Graph edits unannounced; 400 creations uncommitted; P0 beads detached from their epic | about 10 | C rusty-seo d7de6090:144, 5e2424a4:70 |
| Duplicates | about 6 | C scry 9e442dbe:1434 |

Good practices made official: sequential writes; `--import-only` after pulls; diffing the JSONL
by bead ID before staging; a separate tracker-only commit; returning a claim with an evidence
comment when blocked (C rusty-jev 06c74ad3:2368); checking `--help` and fixing a stale AGENTS.md
with a bead comment (co:05/22 T19-22-08:2330).

## Tested against br 0.7.6 (`scripts/test_br.py`)

- The `br prime`, `br import`, `--add-note`, `--blocks` and `list --parent` forms fail; their
  replacements work. `br doctor --fix` works (it is `--repair`, a rebuild).
- A second agent's `--claim` on a held bead is refused, and the first claim survives. `--force`
  with `--assignee` silently replaces the live claim.
- Claiming a blocked bead is refused; a cycle is refused.
- After a simulated pull, a flush is refused until `--import-only`.
- With conflict markers in issues.jsonl, `--flush-only` and `--merge` refuse. Importing the
  incoming version from a sidecar (`BEADS_JSONL`) then `--flush-only --force` regenerates a clean
  file holding both sides. A plain `--import-only` then `--flush-only` exports nothing and loses
  the local beads. `BEADS_JSONL` must name a `.jsonl` file.
- `--import-only --rebuild` deletes DB entries absent from the JSONL (from `br sync --help`).
- In a fresh git worktree, `br show` works before importing (0.7.6 auto-imports).
