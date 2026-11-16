# br audit: evidence and regression scope

## Follow-up audit (2026-11-16)

### Search coverage and skill-use limits

CASS health was healthy with lexical ready and semantic assets catching up. Used
lexical search only; no index repair or raw database access. Search snapshots:

- `br/SKILL.md`: content search returned 1,486 of 1,646 hits across 429 paths.
  A later summary search returned 1,735 hits across 518 paths as indexing changed.
- Quoted `"br/SKILL.md"`: 349 metadata hits across 304 paths, mostly instruction
  catalogs rather than reads. `"Launching skill: br"` returned zero hits.
- The union of the metadata snapshots contained 249 hits absent from the earlier
  full-content response; all 249 were expanded individually without failures.
  A follow-up scan for explicit reads and shell-read patterns added no operational
  skill loads beyond the cold test below.

The one confirmed explicit load is the prior author's cold test:
`/home/ubuntu/.claude/projects/-data-projects-rusty-jev/5f3d3411-8898-40e8-949a-31cf4b13f4e1/subagents/agent-ac8eb1fabaa4210d3.jsonl`,
message 2; its response is message 4. It followed the old force-conflict recipe
and noted missing guidance in some situations. This is an authoring evaluation,
**not independently confirmed operational skill use**. No claim that hundreds
of sessions loaded this newly added skill is justified. Omitted markers, unindexed
new sessions and live index changes limit any assertion about all possible use.

To evaluate the existing skill against real work, also searched exact symptoms:
28 stale-export hits, 58 blocked-claim hits, 157 UNIQUE/import hits, 57 busy hits,
and the first 200 of 802 conflict hits. Those counts are search hits, not distinct
incidents or skill-use counts. Conflict coverage is explicitly capped. Prior
research below supplies broader secondary evidence, not fresh measurements.

Local artifacts: `/tmp/br-skill-content.json`, `/tmp/br-broad-summary.json`,
`/tmp/br-skill-summary.json`, `/tmp/br-recovered-hits.json`,
`/tmp/br-exact-loads.json`, `/tmp/br-primary-expansions.json` and the symptom-specific
`/tmp/br-*-hits.json` reports. Use CASS `source_path`, `conversation_id` and
`--message-index` for expansion; coordinates are messages, not physical JSONL lines.

### Direct incident context

All six selected expansions completed successfully (the cold test above plus
these five operational incidents). The operational incidents predate the skill.

| Source path | Messages | Finding |
|---|---|---|
| `/home/ubuntu/.codex/sessions/2026/03/22/rollout-2026-03-22T00-46-56-019d12cb-744e-77a0-9f08-aa2ded2e0f19.jsonl` | 5082-5087 | Stale export refused; agent moved directly to `doctor --repair`. Refusal and the tool's force hint are not evidence a rebuild preserves unpublished records. |
| `/home/ubuntu/.codex/sessions/2026/03/09/rollout-2026-03-09T01-22-39-019ccff9-7aa5-7f43-b041-9477d81912e2.jsonl` | 184-192 | Blocked claim error followed by intent to rewire a blocking edge into a non-blocking relation to proceed. Don't change the graph merely to bypass a claim refusal, even when error metadata says retryable. |
| `/home/ubuntu/.codex/sessions/2026/03/25/rollout-2026-03-25T01-35-57-019d226b-67cf-77a1-a468-e651d85a111a.jsonl` | 7751-7760 | UNIQUE error followed by proposal to rebuild a temporary DB from JSONL. Distinguish isolated diagnosis from declaring that JSONL contains all DB-only data; verify routing and preservation first. |
| `/home/ubuntu/.codex/sessions/2026/03/15/rollout-2026-03-15T17-47-22-019cf265-29b0-7551-b335-2f64fea0d293.jsonl` | 1378-1393 | Repeated awk one-side conflict filtering and overwrite attempts. No hand-spliced JSONL or one-side selection as a semantic recovery. |
| `/home/ubuntu/.codex/sessions/2026/03/25/rollout-2026-03-25T01-35-57-019d226b-67cf-77a1-a468-e651d85a111a.jsonl` | 3348-3356 | Busy close was later treated as landed, with tracker state checks before publication. Keep outcome reconciliation; do not infer failure/success solely from a busy error. Adjacent duplicate commentary is not independent retry evidence. |

### Old-skill gaps and changes

- Replaced the overbroad “br wins” heading: CLI syntax never overrides project
  authorization, no-force rules or evidence-bound closure.
- Removed automatic force-flush conflict recovery. Distinct-ID title preservation
  does not establish preservation of competing edits, comments, relations,
  tombstones or unpublished audit state. A moving `origin/main` is not necessarily
  the rebase incoming commit; identify actual stages/refs and preserve evidence.
- Limited routine import-after-pull to a known coordinated state. Unpublished DB
  work or markers trigger preservation/reconciliation first. Hashes/counts do
  not prove DB-only data is absent, so they cannot authorize a rebuild.
- Made same-record concurrency explicit with current `--if-unchanged` capability,
  append-only text and short-rewrite refusal handling. File input fixes quoting,
  not overwrite/merge semantics.
- Added unknown-write outcome checks, partial/postcommit failure handling,
  routing validation, isolated test environments and cross-worktree claim limits.
- Kept useful established practices: sequential writes, narrow coordination,
  exact IDs, fresh claims, actual remote/test closure evidence, explicit JSONL
  staging and publication, and graph-cycle checks.
- Missing br now fails live test setup instead of printing a successful skip.

### Tests and limits

The original corpus passed before substantive changes (after hardening fixture
routing). Expanded corpus: **77 passing checks**, zero failures/skips under the
installed `br 0.7.6`. The version string alone is not a permanent capability
contract; local help now advertises reviewed additive reconciliation and
optimistic updates beyond the older skill's scope.

New real-CLI regressions exercise: environment routing removal; rejecting fixture
paths outside the retained root; exact append preservation; stale timestamp
rejection without destroying peer text; successful reviewed update; short rewrite
refusal; exact comment text/dependency direction/notes in exported JSONL;
read-only additive plan leaving the database family, JSONL and base byte-identical;
stale plan-token rejection; and same-ID equal-timestamp semantic conflict refusal
while preserving incoming evidence. Missing-binary behavior is tested separately
by running the corpus with an empty temporary PATH. CLI help probes are bounded.

Legacy force/overwrite tests are retained and labeled as **hazard demonstrations
on fresh fixtures**, not approved real-project operations or a losslessness proof.
All fixtures are retained; no files are deleted. Inherited `BEADS_*`, `BR_*`,
`BD_*` and Git routing variables are cleared, fixture DB paths are explicit, and
user Git hooks/config are excluded. No real tracker, claim, graph, mail recipient
or live repair is changed by these tests.

One independent dry run of the old text and one of the revised text each covered
12 hypothetical scenarios: policy-vs-syntax, stale claims, unpublished mixed DB
state, moved rebase refs, rebuild evidence, competing description edits, uncertain
close outcomes, busy writers, poisoned test routing, semantic preservation,
unrun closure gates, and missing binaries. The old-text reviewer identified
unsafe or underspecified recovery/routing/concurrency instructions; the revised
reviewer selected the intended safe action and stop condition in all 12. This is
qualitative evidence, not a statistical benchmark or proof of all future merges.
Static prose checks test reminder presence only; they don't measure adherence.

Old/revised dry-run outputs and the generated review page are retained at
`/data/tmp/br-skill-eval-20261116/`. The viewer's `without_skill` folder is labeled
as the **old skill baseline**, not a no-skill control.

### Scanner review

UBS 5.5.26 scanned `scripts/test_br.py` and `scripts/self-test.sh` against HEAD.
Final scanner exit: **1**, with two criticals, three warnings and one note, all
reviewed below. Raw artifacts: `/data/tmp/ubs-skill-yhv7n81p/`; summary:
`/tmp/br-skill-ubs-final.json`. Coverage reported both requested source files and
no skipped analysis phases. These files are test helpers, not Rust workspace code.
It reported two critical heuristics at the fixture runner's subprocess call:
`py.security.command-injection` and `python.taint.command`. Both were reviewed:
the executable is the fixed literal `br`; arguments and actor values originate
in this test corpus and br-generated fixture IDs, are passed as separate argv
elements, and never use a shell. DB paths are pinned below a fresh retained test
root; inherited routing overrides are stripped. No user command string is
executed. These are false positives, not a zero-critical scanner result.

The three new `py.parsing.json-loads-no-try` warnings concern parsing the fixture
create/show/plan output: malformed output intentionally raises and fails setup or
the test, rather than becoming a pass. The `py.functions.missing-returns` note
concerns `check`, which updates counters and intentionally returns None. A
subprocess-no-check note on the old sidecar import was addressed by explicitly
retaining/checking its result and diagnostics. No suppressions or smaller scan
scope were used. Prose was reviewed separately; scanning it is not behavioral
validation.

## Prior audit (historical approximate counts)

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

## Original tests against br 0.7.6 (legacy scope, not general recovery proof)

- The `br prime`, `br import`, `--add-note`, `--blocks` and `list --parent` forms fail; their
  replacements work. `br doctor --fix` works (it is `--repair`, a rebuild).
- A second agent's `--claim` on a held bead is refused, and the first claim survives. `--force`
  with `--assignee` silently replaces the live claim.
- Claiming a blocked bead is refused; a cycle is refused.
- After a simulated pull, a flush is refused until `--import-only`.
- With conflict markers, flush and merge refused. A legacy sidecar import plus
  forced export produced both distinct fixture titles. It did not establish
  completeness or semantic preservation and is no longer a recommended recovery.
  A plain import then plain flush left DB-only fixture records absent from the
  output file; “Nothing to export” was insufficient evidence. `BEADS_JSONL` needed
  a `.jsonl` filename in this test.
- `--import-only --rebuild` deletes DB entries absent from the JSONL (from `br sync --help`).
- In a fresh git worktree, `br show` works before importing (0.7.6 auto-imports).
