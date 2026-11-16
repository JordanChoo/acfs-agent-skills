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
