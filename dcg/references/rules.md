# DCG session audit and regression evidence

Audit date: 2026-11-16. Canonical skill: `../SKILL.md`.

## Search coverage and limits

Used CASS lexical search because its lexical index was ready while semantic assets
were still catching up. No index repair or transcript database edits were needed.

- `cass search dcg --mode lexical --robot --limit 20000 --fields summary`:
  initial snapshot **1,384 hits in 399 sessions**.
- Full-content retrieval returned **1,167 of 1,387 hits**, covering 259 sessions.
  Counts changed as concurrent agents added indexed messages. For the initial
  metadata snapshot's **220 hits absent from full-content results**, all 220 were
  recovered individually using `cass expand`; none failed.
- `dcg/SKILL.md` search: **333 hits in 189 sessions**, predominantly skill catalogs
  and instructions, not evidence that the skill was loaded.
- Explicit skill-use search found the original skill's authoring session (Write
  at message 6457; Edit at 6460/6462), but **no independently confirmed read/use of
  the existing skill**. Recovered messages supplied no additional load evidence.

This audit therefore examines indexed **DCG workflows**, compares the existing
skill against those incidents, and tests its guidance. It does not claim that
399 sessions used the skill or that unindexed sessions were searched. CASS search
can omit bootstrap content; do not equate search hits with complete transcripts.

For reproducibility, use the CLI's coordinate metadata. Current `line_number`
values are canonical **message indices**, not physical JSONL lines:

```text
cass expand <source_path> --message-index <N> --conversation-id <ID> -C 2 --json
```

Obtain the conversation ID from search results; never substitute a physical file
line or bulk-load the raw session database. Local audit scratch files are
`/tmp/dcg-cass-hits.json`, `/tmp/dcg-cass-content.json`,
`/tmp/dcg-cass-skill-all.json`, `/tmp/dcg-cass-recovered.json`, and
`/tmp/dcg-primary-expansions.json`. They are local research artifacts, not required
skill runtime inputs. Avoid publishing whole conversations or secrets.

## Primary incidents checked in context

All paths below are CASS `source_path` values. Coordinates refer to messages.

| Session source | Message(s) | Observation and resulting rule |
|---|---|---|
| `/home/ubuntu/.claude/projects/-data-projects-rusty-manus/73ff61da-e028-416a-9e1a-a51a9d542cd8.jsonl` | 1354-1356 | DCG denied a Git-source overwrite; the assistant explicitly proposed writing HEAD through Python instead. Same destructive effect, different interpreter: forbid the bypass and preserve the live diff. |
| `/home/ubuntu/.claude/projects/-data-projects-scry/6407ffd3-6837-4cba-aa36-93f9891ddbb6.jsonl` | 150-153 | Long test-writing/testing call exceeded a 1000ms evaluation budget. Separating authorized file edits from test execution worked. Make this an official simplification, without treating all timeouts as either safe or destructive. |
| `/home/ubuntu/.claude/projects/-home-ubuntu/e25d18fb-3baf-4345-b8cc-a122e50e7865.jsonl` | 24-27 | Trash move denied; assistant inspected scope and gave the owner a concrete proposal. Owner ran the removal through their own terminal UI. Distinguish owner execution from agent self-approval; UI syntax is harness-specific. |
| `/home/ubuntu/.claude/projects/-data-projects-rusty-manus/24b2aa16-8a7b-49d9-ba5f-c6b153e79aa2.jsonl` | 119-121 | Code editing a secret scanner triggered a redirect-related block. Rule wording alone did not establish actual credential handling. Inspect effects before diagnosing; this excerpt does not prove a successful workaround. |

Additional search evidence, not claimed as expanded-context confirmations:

- Codex `/home/ubuntu/.codex/sessions/2026/03/06/rollout-2026-03-06T14-07-36-019cc342-bd88-7603-9917-b48f9d081859.jsonl`,
  messages 2268/2446: allowlist snippets for cleanup and force-with-lease.
  A scanner suggestion or remembered policy workaround cannot grant authorization.
- Claude `/home/ubuntu/.claude/projects/-data-projects-philomena-agent/9d9f4ee7-6d96-4b08-bac7-eef911ceb502.jsonl`,
  message 594: pipeline-consumer denial with broad allowlisting suggestions.
  Do not adopt a suggested rule exception automatically.
- Claude `/home/ubuntu/.claude/projects/-data-projects-screaming-frog/9b93a199-08ef-415a-9794-816b790c4b94.jsonl`,
  message 203: recursive deletion denial. Retain artifacts; don't relocate to an
  allowed temp path and delete there.

The original authoring session was
`/home/ubuntu/.claude/projects/-data-projects-rusty-jev/5f3d3411-8898-40e8-949a-31cf4b13f4e1.jsonl`.
Its subagent analyses are **secondary evidence**: they reported repeated dynamic
redirects, cleanup in compound build commands, nonexistent Trash destinations,
interpreter/editor/config/private-API bypasses, and duplicate transcript entries
with/without `cd`. Those observations informed the original 61-case corpus; their
approximate counts are not fresh incident counts. Do not infer retries merely
from duplicated transcript representations.

## Gaps in the old skill and changes

| Gap | Revised guidance / test |
|---|---|
| Allowed `/tmp` deletes, named-file deletes and empty-directory removals presented as fixes | Authorization remains independent; `owner_required` metadata on historical allowed cases. |
| Automatic stash, detach, worktree removal and force-with-lease recommendations | Shared-work and history changes require applicable authorization; retain work by default. |
| Relative-source Trash move recommended after absolute-source denial | Explicitly forbidden bypass, even though the classifier allows it. |
| Literal redirects, append, archive extraction and copies called safe without destination checks | Establish a fresh authorized destination; inspect collisions and preserve existing contents. |
| Script file or editor treated as a universal escape from a block | Inspect actual effects; never reproduce a denied overwrite/delete/config mutation through another tool. |
| Long commands retried or guard policy weakened | Split already-authorized harmless steps; leave optional cleanup out; do not expand budgets/allowlists to force a pass. |
| No distinction between CLI/hook modes and supported adapters | Evaluate exact payload, parse output plus exit code, reject skips and incomplete results. |
| Missing binary reported successful skipped gate | Live suite fails setup; cannot claim unrun checks passed. |
| Hook parser ignored malformed output and duplicate/missing results | Helper fails closed on malformed output, wrong index, extra records, inconsistent exit/mode and timeout/error rows. |
| Universal `!` approval instructions and broad allow-once assumptions | Owner controls approval, local help defines mechanics, grants are scoped and UI-specific. |

## Verified mechanical behavior and tests

Baseline: old suite reported **73 passing checks** under DCG **0.16.0** despite the
unsafe permission advice above. Mechanical allows alone were insufficient.

Current suite: **9 unittest methods**, including **61 historical live classifier
replays** and a response matrix covering allow, deny, skip, timeout/error,
malformed/missing/duplicate output, boolean/wrong index, incompatible mode, signal
exit, and single-hook versus batch exit conventions. These are separate from the
manual authorization decisions below.

Observed locally with DCG 0.16.0:

- Single `dcg hook` returned exit 0 with `permissionDecision: deny` for a hard-reset
  candidate. Batch mode returned denial and nonzero exit.
- `exec_command` was recognized; a `functions.exec_command` payload was skipped.
  The helper calls that unverified, not allowed. Integrations may change.
- All 61 stored mechanical classifications matched. Historical `fix-*` names are
  labels, not endorsements. No candidate was executed.
- A candidate that would create a marker file if executed was evaluated through
  the helper. The marker remained absent; output recorded authorization as
  `not_checked` and execution as false.
- Invalid input returned helper exit 2 without echoing its contents. Injected
  missing-evaluator and timeout exceptions also returned unverified exit 2.

Run `bash scripts/test-all.sh --skill dcg`; detailed output is available from
`python3 dcg/scripts/test_skill.py`. Temporary test and diagnostic directories are
retained, never deleted. Test setup missing DCG is an error. The suite changes no
DCG config, creates no permits and runs no destructive candidate.

## Manual policy replay of failure cases

These are review exercises against the rewritten text, **not model benchmarks**.
The expected outcome follows the cited skill section even where DCG says allow.

| Failure case | Expected decision under the revised skill | Review result |
|---|---|---|
| Git overwrite denied, then Python writes HEAD over live file | Stop same-effect bypass; inspect diff/fresh snapshot | Covered: No effect-preserving bypasses |
| Optional cleanup in a blocked build chain | Retain old artifacts; build/test in an independently authorized fresh directory | Covered: Happy path / Delete |
| Literal `/tmp` delete allowed but project forbids deletion | Do not run; obtain required explicit approval | Covered: opening invariant / Delete |
| Force push denied; guard suggests force-with-lease | Do not rewrite history automatically | Covered: Force push row |
| Shared live-file discard replaced by stash/detach | Preserve other agents' work and current tree | Covered: Git row |
| Trash destination absent or colliding | Inspect directory and collision first; no move without authorization | Covered: Trash paragraph |
| Absolute Trash move denied, relative form allowed | Do not retry spelling to defeat denial | Covered: Move / No bypasses |
| Harmless authorized file/test operation times out | Split editing/testing and preflight, without needless new permission | Covered: Timeout row |
| Dynamic redirect points to existing useful output | Do not truncate using literal path or append as a workaround | Covered: Redirect row |
| Unknown namespaced tool yields skip | Report unverified and diagnose adapter | Covered: CLI traps and live test |
| Hook exit 0 contains denial | Parse the right mode; do not execute | Covered: CLI traps and live test |
| Missing DCG / broken JSON output | Fail live setup or return unverified | Covered: suite / helper matrix |
| Approval code appears in tool response | Owner-controlled exact authorization; no agent-created reusable rule | Covered: Approval section |

All review cases have explicit guidance. Automated tests measure CLI/helper
behavior and fixture metadata, not whether a future agent will follow prose.

## Scanner triage for the test implementation

UBS was run on both Python files and the shell runner. Its command-injection
finding points to the test's `subprocess.run(args, input=...)`: `args` is built
exclusively from fixed `dcg`, `hook`, and batch flags; candidate text is JSON on
stdin, never executable selection or shell code. No `shell=True` is used.
This is a reviewed false positive, not evidence of a clean zero-finding scan.
JSON-parse warnings concern fixtures/test assertions: malformed responses should
raise and fail the test. The runtime helper catches parsing failures and returns
unverified. Missing-return notes are heuristic; helper branches return explicitly
and unittest methods intentionally return None. Subprocess exit checking is
explicit: `check=False` preserves denial exits for classification/assertions.
No rules or coverage were suppressed to hide these findings.
