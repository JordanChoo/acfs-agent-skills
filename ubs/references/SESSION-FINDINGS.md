# UBS skill audit — CASS evidence and replay, 2026-11-16

## Search coverage and limits

The initial lexical search returned **5,450 matching messages in 341 sessions**.
`ubs/SKILL.md` search returned 387 hits in 136 sessions; most were catalogs,
instruction blocks, or mentions, not evidence of loading the skill. Reviewing the
UBS-matching content identified **17 sessions with explicit tool calls reading the
skill**, including **14 with identifiable scan invocations** and three with only
loading/discovery in the retrieved evidence. All are listed below.

CASS health reported lexical search ready with semantic assets still catching up,
so this audit used lexical mode. Full-content search omitted 54 initial metadata
hits; each was fetched through `cass expand --conversation-id ...
--message-index ... -C 0 --json` (54 fetched, no command failures). They did not
add a confirmed skill load. A later search grew to 5,468 matches as indexing
continued. Counts are a snapshot, not a claim about every unindexed/deleted/remote
session or about identical content across dates. This audit did not query SQLite
or read entire source JSONL files.

Reproduce discovery (save large outputs instead of printing them):

```bash
cass health --json
cass search ubs --mode lexical --robot --limit 10000 --fields summary
cass search 'ubs/SKILL.md' --mode lexical --robot --limit 500 --fields summary
```

Search `line_number` is a canonical **message ordinal** on the current CLI. Reopen
hits with `--message-index`, not physical-file `-n`. Example:

```bash
cass expand /home/ubuntu/.codex/sessions/2026/05/21/rollout-2026-05-21T00-56-54-019e479b-33d5-71c3-9cb6-caa55d79e01a.jsonl \
  --message-index 215 -C 1 --json
```

## Confirmed skill-read inventory

Sources are under `/home/ubuntu/.codex/sessions/YYYY/MM/DD/`; append the exact
filename below. Ordinals identify explicit `exec_command` reads of `ubs/SKILL.md`.
A scan can occur before or after the read; a read is not proof the instructions
were followed. Duplicate assistant commentary is not counted as independent use.

| Source filename | Skill-read message(s) |
|---|---|
| `rollout-2026-05-15T04-12-11-019e2967-d6c2-7a62-8702-6b8fc8a74a3d.jsonl` | 75; discovery only |
| `rollout-2026-05-15T12-59-23-019e2b4a-8240-75b3-aefc-555b8483d831.jsonl` | 590 |
| `rollout-2026-05-15T15-59-10-019e2bef-1993-7ae3-b817-c02a38ca53af.jsonl` | 252 |
| `rollout-2026-05-19T23-41-20-019e422f-a983-7070-a974-9d2ea0d83c7d.jsonl` | 847 |
| `rollout-2026-05-21T00-55-21-019e4799-c857-7751-a8b3-e4f70ea54fa0.jsonl` | 112; no scan command identified |
| `rollout-2026-05-21T00-56-04-019e479a-715d-76f0-a9b9-e4066161cdfa.jsonl` | 93, 198 |
| `rollout-2026-05-21T00-56-04-019e479a-7228-76e3-857f-b5409e71f1a5.jsonl` | 173, 253 |
| `rollout-2026-05-21T00-56-54-019e479b-32ff-7753-b9eb-0c824299ad1a.jsonl` | 109 |
| `rollout-2026-05-21T00-56-54-019e479b-33d5-71c3-9cb6-caa55d79e01a.jsonl` | 105 |
| `rollout-2026-05-21T01-24-23-019e47b4-5dd4-7201-8dbc-9c3ec3e11c8e.jsonl` | 62; no scan command identified |
| `rollout-2026-05-22T04-08-07-019e4d70-a260-7780-a2a4-e6ddf7c108f4.jsonl` | 264, 287, 289, 440 |
| `rollout-2026-05-22T04-08-18-019e4d70-cbad-76b0-8fcd-448ad79c8ceb.jsonl` | 269, 500 |
| `rollout-2026-05-22T04-56-31-019e4d9c-f1de-77c0-9ca5-a8908ce7fe0c.jsonl` | 273, 796, 939, 1455, 2435, 2840, 3119 |
| `rollout-2026-05-22T04-56-55-019e4d9d-4f1b-77d0-9720-0f1463a2fd85.jsonl` | 1081, 1350, 1657, 2044, 2695, 2786 |
| `rollout-2026-05-22T17-54-56-019e5065-9b02-7c70-8882-ed7535f081ec.jsonl` | 345, 750 |
| `rollout-2026-05-22T17-55-01-019e5065-ad04-7193-a56d-b81286cc6c77.jsonl` | 932, 1100, 1608 |
| `rollout-2026-05-23T03-34-19-019e5278-0b96-7cf2-aaf0-7bd3e0c84b1d.jsonl` | 313, 796, 1154, 1288, 1517 |

## Observed failure cases → official workflow

UUID prefixes below refer to the inventory above, unless a full alternative
source is specified. These are observed actions/statements, not inferred bugs.

| Case | Session / message evidence | Revision and replay result |
|---|---|---|
| Unsupported files called clean | `019e2b4a` 598 scans only `prd/PRD.md`; 608 calls its output clean. `019e479a-715d` 133/140, 252/257 similarly scan/approve bead JSONL. | Explicit `not scanned` category and manual review. Live Markdown probe returns 3; mixed scopes remain review-required. |
| Missing output interpreted as zero results | `019e479b-33d5` 215 runs `ubs ... || true`, then prints zero results when the SARIF file is absent/empty. | Runner rejects empty/malformed output; fixtures replay exit-zero empty and missing coverage. |
| Real exit replaced by parser result | Same 215, and piped commands in `019e4d9c` 347/349. | Capture process status before parsing, preserve stderr and reports; nonzero/hidden-critical replay tests fail closed. |
| Filenames/argv rebuilt incorrectly | `019e4d70-a260` 279/281 rebuilds a filename string/array; `019e4d70-cbad` 275/277 invents zsh array and xargs handling for untracked Rust files. | One subprocess argv, NUL Git enumeration, untracked inclusion, no shell word splitting. Tests include spaces, newline, and leading dash. |
| Long scan considered optional because quiet | `019e5065-9b02` 695 says it may not block bead closeout if UBS stays quiet. | Prose requires real completion; signal/partial/no-output replay cases cannot pass. |
| Broken pipe obscures scanner outcome | `019e5065-ad04` 1703 records UBS's `echo ... Broken pipe` with a failed process. `019e4d70-a260` 546 notes its quick pipeline assumed SARIF unconditionally. | Save both streams once, parse files afterwards; no scanner-to-parser/head pipeline. |
| Rust noise prompts unnecessary test changes | `019e4d9c` 1001 removes a test `expect()` warning; `019e5278` 327 replaces a test panic with an expect to appease a heuristic. `019e4d70-cbad` 602 distinguishes intentional test assertions. | Preserve meaningful assertions and semantics. Optional verified production-only view retains a real unwrap canary while filtering test assertions. |
| Good existing workaround: explicit status + saved SARIF | `019e5278` 1156/1206 records `status=$?`/`rc=$?`, reads counts from the saved report, then returns the original status. | Promoted to the raw happy-path fallback and bundled runner. |
| Good existing behavior: acknowledge no coverage | `019e422f` 853 says UBS had nothing meaningful to scan on bead JSONL. | Promote this wording, instead of calling the same outcome “clean.” |
| Real findings must survive noise triage | `019e4d9d` 1032 reports generator JSON parsing without a typed failure, unlike its test/comment noise. | Prioritize actual data flow and unguarded parsing; real JS eval canary remains detected under narrow ignores. |

## Broader UBS-use evidence and old-skill problems

These are additional context, not newly proven skill loads:

- The earlier audit in Claude session
  `/home/ubuntu/.claude/projects/-home-ubuntu/3c2f0583-f5f2-45dd-a5b1-600a66b8370b.jsonl`
  message 199 summarized context blowups, staged-empty scans, format confusion and
  changing intentional `!= null` to strict equality. Its subagent
  `agent-a1bb76bf574eec54d.jsonl` message 58 reports the semantic regression in
  historical `7f29e7ed/agent-acompact-c10da2bf50ec200a`. This is **secondary audit
  evidence**, not an independently rerun historical patch. The rewrite preserves
  the semantic guardrail and removes automatic false-positive exemptions.
- Direct older UBS-use session
  `/home/ubuntu/.codex/sessions/2026/03/07/rollout-2026-03-07T03-13-48-019cc612-8336-75c3-966f-fa96fdfb1aa9.jsonl`
  message 2219 discusses format/count disagreement; 2185 distinguishes synchronous
  k6 API warnings. Keep saved coverage and per-finding evidence rather than
  rescan repeatedly or equate an API name with a vulnerability.
- Rusty Jev Claude session
  `/home/ubuntu/.claude/projects/-data-projects-rusty-jev/5f3d3411-8898-40e8-949a-31cf4b13f4e1.jsonl`
  messages 917/930 show the cargo-deny compatibility/workspace caveat. Preserve
  project toolchain pins; a broken advisory parser is not a dependency finding.
- The old skill itself incorrectly equated exit 0 with zero warnings, hid stderr
  in nearly every recipe, supplied unsafe shell splitting, recommended blanket
  TSX/backend/test exclusions, claimed JSON could never have locations, and marked
  flags permanently broken. These were verified against the text and installed
  UBS 5.5.26 help/robot docs, then corrected.
- Its self-test inferred the dirty exit from JSON counts instead of measuring it,
  used `|| true`, had cleanup deletion, and used `((PASS++))` under `set -e`, which
  can fail on a successful first increment. The replacement records actual
  statuses, retains fixtures, asserts ignore canaries, and reports test failures.

## Testing the revision

`bash ubs/scripts/self-test.sh` passed **17 tests**, including 15 envelope subcases
and live installed-UBS clean/dirty JS, unsupported Markdown, narrow ignore with a
source canary, and Rust test-filter probes. All tests use fake/local input; no paid
endpoints, model benchmark, tool update, or source-session mutation is involved.

Manual replay of every row above checked that the new instructions select the
right scope, distinguish unsupported from clean, retain failure evidence, preserve
semantics/tests, and do not quietly bypass a mandatory gate. The scripted tests
exercise the helper and CLI contracts; they do **not** establish a model-adherence
rate or prove the scanner finds every bug. New partial/failure and concurrent-input
fixtures are preventive tests motivated by observed lost-evidence patterns, not
claims that every synthetic envelope occurred verbatim in CASS.

The rewritten helper/tests were themselves scanned with UBS. The Python analyzer
flagged `subprocess.run(command + ["lib.rs"], ...)` in the live Rust probe as command
injection. Inspection shows `command` is a local list of fixed UBS flags, with only
a boolean adding the fixed `--exclude-tests` flag; no caller-controlled executable
or shell is involved. This is documented triage, not an automatic test exemption.
Remaining warnings cover intentional test JSON assertions and subprocess timeout
heuristics (UBS owns its module timeouts; the wrapper waits for actual completion).
No broad exclusion or semantic workaround was added to make those counts vanish.

## Direct UBS use (second pass, 2026-11-16)

The audit above covers the 17 sessions that opened the skill. Most UBS runs come from project
AGENTS.md files ("ubs <changed-files> before every commit") and never load the skill. A second
pass read about 35 runs in Claude Code sessions (rusty-jev, philomena-agent, hugh, scry,
rusty-manus, rusty-seo) and about 89 runs in 13 Codex sessions not in the inventory
(philomena, philomena-agent, scry, jordanchoo-static, rusty-seo). There are no Codex sessions
after 2026-05-23. Claude Code transcripts often store only the tool's description, not the
command, so some conclusions rest on the output and the agent's words. Paths: `C:` is
`~/.claude/projects/`, `X:` is `~/.codex/sessions/2026/`; numbers are message indices.

| Pattern | Evidence | Rule in SKILL.md |
| --- | --- | --- |
| Default text output flooding the context; reruns to clear warnings | About 40 runs in 4 Codex sessions; X:04/10 019d7540 made 26 runs (about 160k tokens); one Rust file can list 500+ warnings (C:rusty-manus #578) | Runner summary only; rule 3 |
| Code changed only to quiet UBS: test `panic!` to `assert!`, re-raising try/except, `!= null` rewrites, `ubs:ignore` comments, test-wide `.ubsignore` | 5 Claude sessions (C:rusty-seo 38ca56db #915, #1015; C:rusty-jev 06c74ad3 #3786-3806, where warnings rose 148 to 152) and 9 Codex cases (X:04/10 019d7540 2717, 2899; X:04/28 019dd529 2026; X:03/13 019ce871 309, 119, 526; the comments then spread into new files, 019ce891 1432) | Rule 1 |
| Exit 0 with hundreds of warnings, then commit | C:rusty-jev 06c74ad3 #3573 (409 warnings); C:hugh 5af828ad #1592; C:philomena 9d9f4ee7 #11892 | `--baseline`, report requirements |
| Hand-made before/after comparisons, some by counts only | C:philomena 9d9f4ee7 #6563-6579 (7+ calls, 2 dcg blocks), #8130 ("same 20 criticals" from equal counts); C:rusty-manus bbafa3dc #361, #579 | Runner `--baseline` |
| Scope narrowed until exit 0, findings misattributed | C:philomena 9d9f4ee7 #3921-3930 (5 of 13 "test dummy" criticals were in `src/`) | Rule 2 |
| Exit 1 waved through at bead close | X:05/23 019e5277 560, 577 | Rule 4 |
| Unsupported-only scans reported as passing | X:05/16 019e2f19 1246, X:05/19 019e41e3 220, X:05/20 019e4279 734 ("no recognizable languages", exit 0); X:03/06 019cc342 2776; X:04/06 019d62b7 617 ("Files scanned: 1" of 9); C:scry 6407ffd3 #691 (exit 3 not reported) | Rule 5 |
| Skipped check reported clean | C:rusty-jev 06c74ad3 #604 (cargo-deny licenses skipped, called clean) | Rule 6, `not_evaluated` |
| Grepping text output | C:rusty-manus #357 (per-language "Critical issues: 0" before combined "Critical: 9"); C:philomena #3929, #6236 | Rule 7 |
| `Cargo.toml` or fixtures in the scan list | X:05/23 019e5277 560; X:04/06 019d62b7 617 | Rule 8 |
| Whole-repo scans, size-limit bypass, a moving `--diff` scope | X:03/07 019cc889 (101 critical, 1337 warnings from compiled `functions/lib`); X:03/12 019ce208 794 and X:03/13 019ce871 81 (`UBS_MAX_DIR_SIZE_MB=0` on a 1.5 GB tree); X:03/07 019cc612 5663 (49, 51, 53 files) | Rule 9 |
| Version-specific output gaps (5.0.7: empty SARIF, broken `--suggest-ignore`) | X:03/07 019cc881 2951, 019ce871 220 | Rule 10 |
| Exit codes of chained checks mislabeled | C:philomena #10830 | Raw fallback note |

Good practices promoted: printing `ubs rc=$?` beside the counts (C:rusty-jev, many runs);
scanning a fresh worktree of the commit (C:philomena wt-jzgj, X:philomena-agent 4286, which
linked `node_modules`); saving reports to files before reading them. Real bugs UBS found were
JS/TS/Python data-flow and parsing issues (X:03/12 019ce208 1053: global `isNaN`, unguarded
`JSON.parse` of a downloaded payload, user-supplied regex ReDoS, an XHR listener leak, a
divide-by-zero; X:04/28 019dd529 2010).

### Live checks behind the changes (UBS 5.5.26, rusty-jev)

- A file-only Rust scan of `src/tools/verify.rs` reported four "Not evaluated" notes: `cargo
  check` and test build, fmt and clippy, dependency hygiene (`cargo audit/deny`), and "No
  Cargo.toml at project root". The runner now surfaces them as `not_evaluated`.
- The same scan had 150 warnings: 2 in production code and 148 in `#[cfg(test)]` code
  (`rust_split`).
- `--baseline cdd435e~1` against that file reported 17 new warnings, all in test code added by
  that change, and 3 fixed, despite about 50 lines of shift. UBS's native
  `--save-baseline` / `--new-only` on the same pair reported 16: it treats an identical
  snippet already present as old, where the runner counts the extra copy as new.
- The previous raw fallback (redirects into a `$(mktemp)` path) is denied by the dcg hook
  (`core.filesystem:redirect-truncate-dynamic-path`); the replacement with `--also` and a
  literal directory is allowed, checked with `dcg hook --batch`.
