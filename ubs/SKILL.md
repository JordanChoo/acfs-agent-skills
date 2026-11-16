---
name: ubs
description: >-
  Run and interpret Ultimate Bug Scanner (UBS) for a bug/security scan or a
  repository-required pre-commit gate. Use when the user names UBS or asks to
  triage scanner findings, scan changed files, or configure .ubsignore. Handles
  exact scope, real exit codes, incomplete coverage, Rust scan limits, and false
  positives without weakening correct code or tests.
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
4. Check **coverage and findings separately** using the table below. Review warnings
   even when UBS exits zero. Inspect changed unsupported files manually.
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

## Raw fallback: keep both streams and the real status

Use a shell with normal command-status semantics. This form survives `set -e`:

```bash
report_dir=$(mktemp -d "${TMPDIR:-/tmp}/ubs-run.XXXXXX")
if ubs --format=sarif --quiet --no-auto-update \
  --report-json="$report_dir/summary.json" src/file.rs \
  >"$report_dir/findings.sarif" 2>"$report_dir/stderr.log"; then
  scan_rc=0
else
  scan_rc=$?
fi
printf 'UBS exit=%s; artifacts=%s\n' "$scan_rc" "$report_dir"
# Parse the saved reports afterwards; do not let parser success replace scan_rc.
```

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
