---
name: ubs
description: >-
  Run and interpret Ultimate Bug Scanner (UBS) for a bug/security scan or a
  repository-required pre-commit gate. Use when the user names UBS, when AGENTS.md
  says to run `ubs <changed-files>` before committing, or when asked to triage
  scanner findings, scan changed files, or configure .ubsignore. Handles exact
  scope, real exit codes, findings new since a baseline, incomplete coverage
  (unsupported files, skipped Cargo phases), Rust test-vs-production noise, and
  false positives without weakening correct code or tests.
---

# UBS: capture once, verify coverage, then triage

UBS is a heuristic scanner, not a proof that code is safe and not a substitute for
compiler, test, dependency, or repository-specific gates. Read the project's
AGENTS.md/CLAUDE.md first; its toolchain pins and build-location rules take precedence.

## Happy path

1. Work from the project root. Inspect `git status --short`; identify the files you
   own. Check `command -v ubs` and `ubs --version` once; if missing, use the approved
   tool-install workflow rather than improvising an installer. Do not stage
   another agent's work merely to make `--staged` work.
2. Use the bundled runner. Set `UBS_SKILL` to the directory containing this file
   (the shared installation is `~/.codex/skills/ubs` or `~/.claude/skills/ubs`).

```bash
# The usual gate: your changed source files, plus what is NEW compared with HEAD.
# Run it with the project's PATH (pinned tools such as cargo-deny first, per AGENTS.md).
python3 "$UBS_SKILL/scripts/scan.py" --baseline HEAD src/worker.rs src/lib.rs

# Specific files: safest scope in a shared working tree; filenames are separate arguments.
python3 "$UBS_SKILL/scripts/scan.py" src/worker.rs 'tests/file with spaces.rs'

# All working-tree changes PLUS untracked files; deleted files are omitted.
python3 "$UBS_SKILL/scripts/scan.py" --scope changed

# Already staged files only. Refuses partially staged files rather than silently
# claiming working-tree results cover different index contents.
python3 "$UBS_SKILL/scripts/scan.py" --scope staged
```

3. Wait for the actual process completion. The runner prints a bounded JSON summary
   and the unique artifact directory. Read `record.json`, `stderr.log`,
   `summary.json`, and `findings.sarif` there as needed. It preserves the scanner's
   real exit code, selected filenames, hashes for file scopes, and analysis options.
   It never stages, commits, invokes install/update/repair commands, or deletes files.
   Never let raw text output into your context: one Rust file can produce 500 warnings
   and a session lost 160k tokens that way.
4. Check **coverage and findings separately** using the table below. Review warnings
   even when UBS exits zero. Inspect changed unsupported files manually. The summary
   gives you three triage aids:
   - `baseline.new`: findings that are new since the baseline ref, matched by rule, file
     and quoted code (not by line or count), each tagged `production` or `test` for Rust.
     Triage these first; `fixed_count` says how many disappeared.
   - `not_evaluated`: phases UBS skipped. File-only Rust scans skip `cargo check`,
     clippy and `cargo audit/deny`; those checks have **not run**, whatever a project's
     AGENTS.md says UBS does. Run them separately when they are required.
   - `rust_split`: warnings in production code versus `tests/` and `#[cfg(test)]`
     modules (an approximate triage aid; it never makes a test finding ignorable).
   UBS also has native `--save-baseline=FILE` / `--baseline=FILE --new-only`, which
   needs a scan of the old file versions; the runner's `--baseline` does that for you.
5. Fix confirmed bugs; rerun the same scope after changes. Keep the raw artifacts
   and record the final revision/scope, exit code, coverage limits, and triage.
   If source changed during the scan, the runner refuses that result.

The runner requires Python 3.9+ and the current UBS `--report-json` coverage
summary. An older or missing report yields `coverage_unverified`, not a fabricated
pass. Use the raw recipe below if necessary; document the coverage limitation.
Do not install/upgrade tools or change project policy just to make a gate green.

## Outcome is not just an exit code

Verified with UBS 5.5.26; inspect `ubs --version`, `ubs --help` and
`ubs robot-docs exit-codes` when local behavior differs.

| Evidence | Interpretation and action |
|---|---|
| Exit 0, status `ok`, scanners ran | No criticals; **warnings may remain** unless warning failures were enabled. Triage SARIF and totals. |
| Exit 1 | Criticals, or warnings under `--fail-on-warning`. Investigate; do not discard the exit status. |
| Exit 2 / signal / status `partial`, `error`, or `refused` / failed modules | Incomplete or failed analysis. Read stderr and coverage metadata. Not a pass, even if available findings are empty. |
| Exit 3 / zero scanned files / no supported languages | Nothing checked. Report `not scanned`; manually review unsupported changes. |
| Empty/malformed SARIF, missing summary, unknown schema | Missing evidence. Report incomplete/unverified; never substitute zero findings. |
| Empty selected scope | `not run`; do not invoke bare `ubs` and accidentally scan the repository. |

Older UBS versions returned 0 for unsupported-only scopes; `UBS_ALLOW_NO_SCAN`
and `UBS_ALLOW_PARTIAL` can also weaken exits. The runner disables those two
permissive settings and still checks coverage metadata. A completed scan with
warnings or unsupported-file candidates is `review_required`, not “clean.”
A file count is not proof that every requested file or analysis ran: inspect
ignore rules, selected languages, and per-scanner limitations.

## Choose the analysis deliberately

| Situation | Scope / next step |
|---|---|
| One to five edited source files | Explicit relative paths; do not dump a full-repo report into chat. |
| New untracked source | Explicit paths or the runner's `changed` scope; plain `git diff HEAD` misses it. |
| Markdown, bead JSONL, TOML/JSONC, Terraform, `.env.example`, etc. | UBS may not analyze them. Report actual coverage; use manual review and appropriate format validators. A mixed scan does not validate its unsupported files. |
| Rust source-only scan | `--ubs-arg=--only=rust`; targeted shadow workspaces may omit Cargo phases. Native/Wasm checks and tests remain separate gates. |
| Cargo manifest/lock/dependency change | Run the required checks/audit from the real workspace (with pinned `cargo-deny` first on PATH where required). If UBS needs workspace context, use an explicit project scan below; never copy a lone manifest into an incomplete shadow crate and call that a graph audit. |
| Large initial audit / workspace-dependent Rust audit | Explicit `--scope project --ubs-arg=--only=rust` (choose actual languages). Verify ignores and size first. Project scope is not an immutable snapshot; use an isolated checkout for concurrent work. |
| Hundreds of Rust assertion/expect warnings | Group by rule/path; distinguish test code from production, including inline `#[cfg(test)]` modules in `src/`. See the triage reference. |

Optional, **only when locally supported and consistent with project rules**:

```bash
# Static Rust analysis only; explicitly NOT cargo/test/dependency verification.
python3 "$UBS_SKILL/scripts/scan.py" --ubs-arg=--only=rust --ubs-arg=--no-cargo src/lib.rs

# Supplemental production-focused view; does not replace required scanning of tests.
python3 "$UBS_SKILL/scripts/scan.py" --ubs-arg=--only=rust --ubs-arg=--exclude-tests src/lib.rs
```

Skipped categories are “not evaluated,” never clean. Do not add these switches
just to silence a required gate. The language selector is `--only=rust` or
`--exclude-langs=...`; current `--exclude=...` excludes **paths**, not languages.
Historical `--category`/`--suggest-ignore` failures are version-specific: consult
local help rather than memorizing that a flag is permanently broken.

## Triage without changing correct behavior

Read the actual code and the finding's file, line, and rule. Start with changed
production paths, real secret/data exposure, unguarded parsing, unsafe indexing,
and lifecycle mistakes. Then inspect tests and helpers. Findings on unchanged
lines in a scanned file are not automatically regressions from this patch.

- A critical label is a priority to investigate, not proof of a bug.
- `assert!`/`expect()` in a Rust test may be intentional; a production request-path
  panic is different. Do not remove assertions, weaken tests, or replace a valid
  assertion solely to reduce the warning count.
- Compiled directories, `lib/`, `.tsx`, tests, backend code, and fake-looking
  credentials are **not automatically safe**. Verify the artifact boundary,
  fixture provenance, trust boundary, and actual data flow before dismissing.
- Preserve intentional `x != null` (checks both null and undefined). Do not change
  semantics to satisfy a heuristic. Similarly, prove synchronous-vs-async APIs
  before dismissing promise warnings.
- Prefer documented triage over blanket exclusion. Exclude verified generated or
  vendored artifacts narrowly; do not exclude all tests, backend source, or TSX.
- Treat inline `ubs:ignore` and ignore globs as analyzer/version-specific. Verify
  the exact finding disappears **and a nearby real finding still appears**.
  If suppression does not work, document the false positive rather than broadening
  exclusions or repeatedly editing correct code.

See [FALSE-POSITIVES.md](references/FALSE-POSITIVES.md) for examples and boundaries.

## Rules from past runs (each was broken repeatedly)

Evidence: [SESSION-FINDINGS.md](references/SESSION-FINDINGS.md), sections "Direct UBS
use".

1. **Never change correct code only to quiet the scanner.** That includes rewriting a
   test `panic!`/`expect` into `assert!` "because UBS doesn't flag that", wrapping code in
   a try/catch that only re-raises, expanding `!= null`, and adding `ubs:ignore` comments
   or test-wide `.ubsignore` entries. "Same false positive as prior beads" is not
   triage: list each finding. One agent's rewrites raised the warning count.
2. **Never shrink the scope until UBS exits 0.** Explain every critical from the first
   run, file by file. In one case five "test dummy credential" criticals were in `src/`.
3. **Never loop scans to reach zero warnings.** Fix real issues, rerun once, and report
   what remains with its triage.
4. **Exit 1 or criticals at bead close need a written triage per finding**, not a
   summary line such as "generic test notes, no blocker".
5. **"Not scanned" has several spellings:** exit 3, "no recognizable languages",
   "nothing was checked", or "Files scanned" lower than the files you selected. Report
   it as not scanned. "Ran ubs successfully" for a docs- or JSONL-only change is wrong.
6. **Any skipped or "Not evaluated" check did not run** (for example "cargo-deny ...
   skipped", or the Cargo phases of a file-only Rust scan). Never report it as clean.
7. **Never grep the text output.** Multi-language runs print a per-language summary
   (`Critical issues: 0`) before the combined one (`Critical: 9`), and counts appear
   twice. Use the runner or saved SARIF/JSON.
8. **Keep the scan list to source files.** Leave out `Cargo.toml`, lock files and JSON
   fixtures; review those by other means.
9. **No whole-repo scans in a shared tree** unless the project requires one. Never
   bypass "Directory too large" with `UBS_MAX_DIR_SIZE_MB=0` (UBS copies the tree to
   temp storage); exclude generated directories narrowly instead. For an exact,
   stable snapshot, scan from a fresh worktree of your commit (link `node_modules` in
   if the JS scanner needs it, never commit it) and map paths back to the repo.
10. **Record `ubs --version`** with the result. Behaviour changed between 5.0.7, 5.2.76
    and 5.5.26 (for example 5.0.7 wrote empty SARIF and had a broken
    `--suggest-ignore`). If SARIF is empty or does not match the summary totals, the
    result is unverified; do not substitute hand-made `rg` sweeps.

**How far to triage.**
- Every **critical** in files you changed gets its own verdict, new or not.
- Every finding in `baseline.new` gets a verdict. Warnings of one rule in one area
  (for example 40 `assert!` in `#[cfg(test)]` code) may share one verdict that names the
  rule, the area and the count; list any exception separately.
- Pre-existing warnings outside `baseline.new` need no verdict: report their total.
- Criticals in files you did not change (another agent's work swept into a wider scan)
  are not yours to fix: report them to that file's owner or reservation holder.
- **Baseline ref:** `HEAD` while your change is uncommitted; once committed, the commit
  before it (`HEAD~1` for one commit, or `git merge-base HEAD origin/main` for a branch).

**What a report must say:** the scope and files, `ubs --version`, the scanner exit
code, coverage gaps (`not_evaluated`, unsupported files), the new findings against the
baseline with their verdicts, and anything left untriaged, named as such. An unverified
or incomplete result goes to the owner as exactly that; do not upgrade UBS or change
project policy to turn it green without their approval.

## Raw fallback: keep both streams and the real status

Use a shell with normal command-status semantics. Let UBS write its own report files
(`--also`, `--report-json`) to a **literal** fresh directory: redirects into a
`$(mktemp)` or variable path are denied by the dcg hook on this VPS (the previous
version of this recipe was). This form survives `set -e`:

```bash
mkdir -p /data/tmp/ubs-run-20261116a   # new literal dir per run (or under your session scratchpad)
if ubs --format=json --quiet --no-auto-update \
  --also=sarif:/data/tmp/ubs-run-20261116a/findings.sarif \
  --report-json=/data/tmp/ubs-run-20261116a/summary.json \
  src/file.rs >/dev/null 2>/data/tmp/ubs-run-20261116a/stderr.log; then
  ubs_rc=0
else
  ubs_rc=$?
fi
echo "ubs exit=$ubs_rc"
# Parse the saved reports afterwards; do not let parser success replace ubs_rc.
```

When one command runs several checks, label each status where it is captured
(`ubs_rc=$?` right after `ubs`); a later `echo "exit: $?"` reports the wrong command.

Do not pipe the scanner to `head`, a fallible inline Python program, or a heredoc
that also consumes stdin: this caused broken pipes and hidden failures in CASS.
Do not use `|| true`, `2>/dev/null`, or “empty file means no results” for a gate.
Paths with spaces/newlines need separate argv entries or NUL-safe Git handling;
avoid `ubs $(git diff ...)`, shell-specific word splitting, and non-NUL `xargs`.
Reuse saved SARIF for counts and details instead of rescanning to change format.

Long-running tools need a completion result. Quiet output is not success; a
cancelled or timed-out mandatory scan stays incomplete. UBS can compile/analyze
code; follow project build isolation/offloading rules and coordinate heavy runs.
Check version/pins and diagnostics before assuming a scanner finding is a product
bug (for example an old cargo-deny unable to parse a newer advisory format).

## References and tests

- [SARIF-PARSING.md](references/SARIF-PARSING.md): bounded inspection of saved reports.
- [SESSION-FINDINGS.md](references/SESSION-FINDINGS.md): CASS scope, concrete evidence,
  old-skill mistakes, and regression cases. Tool use and skill loading are distinguished.
- [SELF-TEST.md](SELF-TEST.md): run `bash scripts/test-all.sh --skill ubs` from the shared
  skill repo; tests retain small artifacts and perform no deletion or tool updates.
