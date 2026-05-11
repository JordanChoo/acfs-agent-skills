---
name: ubs
description: >-
  Run UBS (Ultimate Bug Scanner) on changed files before committing.
  Use when: pre-commit quality gate, the user mentions "ubs", "bug scan",
  "security scan", or when AGENTS.md / CLAUDE.md instructs agents to run
  UBS before committing. Handles scoping, output parsing, false-positive
  triage, .ubsignore management, and the fix-rerun loop.
---

<!-- TOC: TL;DR | Decision Tree | Preflight | Command Reference | Recipes | Output Parsing | False-Positive Triage | .ubsignore | Anti-Patterns | Troubleshooting | Provenance -->

# ubs -- Ultimate Bug Scanner

> **Premise:** `ubs` is a multi-language static analysis meta-runner at `~/.local/bin/ubs`. It orchestrates ast-grep, ripgrep, and per-language modules to flag security issues, null-safety bugs, resource leaks, and code smells. It is **not** a linter replacement -- it catches classes of bugs that linters miss (eval injection, prototype pollution, stale closures, phantom callables). Run it on **changed files only**, read its output with the right format, triage false positives, fix real issues, and move on.

## TL;DR -- fastest correct path

```bash
# 1. Scope to changed files (< 5s, manageable output)
ubs --format=sarif --quiet $(git diff --name-only HEAD) 2>/dev/null

# 2. Parse actionable findings
... | python3 -c "
import sys,json
d=json.load(sys.stdin)
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    if r.get('level') in ('error','warning'):
      loc=r.get('locations',[{}])[0].get('physicalLocation',{})
      f=loc.get('artifactLocation',{}).get('uri','')
      ln=loc.get('region',{}).get('startLine','?')
      print(f\"{r['level']:8s} {r.get('ruleId','?'):30s} {f}:{ln}\")
"

# 3. Fix real issues, then verify
ubs --format=sarif --quiet <fixed-files> 2>/dev/null
# Exit 0 = clean. Exit 1 = findings remain.
```

If you only do those three steps, you'll be right 90% of the time.

---

## Decision Tree

```
What needs scanning?
|
+-- Pre-commit (staged files)
|   -> Recipe #1: ubs --staged
|   IMPORTANT: stage files FIRST, then run --staged
|
+-- Quick check on files I just edited
|   -> ubs --format=sarif --quiet file1.ts file2.py
|
+-- Changed files vs HEAD (not yet staged)
|   -> Recipe #2: ubs --diff
|
+-- Full project scan (rare -- only for initial audit)
|   -> Recipe #3: ubs --format=sarif --quiet --ci .
|   WARNING: output will be huge. Use SARIF + jq to filter.
|
+-- Triage a specific UBS finding
|   -> Read the file:line, check context, classify per $$False-Positive Triage
|
+-- Suppress known false positives
|   -> .ubsignore for directories, inline // ubs:ignore for lines
```

---

## Preflight

```bash
command -v ubs >/dev/null || { echo "UBS not installed"; exit 1; }
ubs --version  # expect: UBS Meta-Runner v5.x.x
```

If `ubs` is not found, it's installed via:
```bash
curl -sSL https://raw.githubusercontent.com/Dicklesworthstone/ultimate_bug_scanner/main/install.sh | bash
```

Check module health:
```bash
ubs doctor        # validates cached modules, checksums
ubs doctor --fix  # redownload corrupted modules
```

---

## Command Reference

### Scanning modes (pick ONE)

| Mode | Command | When to use |
|---|---|---|
| Specific files | `ubs file1.ts file2.py` | Changed 1-5 files (fastest) |
| Staged files | `ubs --staged` | Pre-commit gate |
| Modified files | `ubs --diff` | Quick check vs HEAD |
| Whole project | `ubs .` | Initial audit only |
| File list | `ubs --files=a.js,b.py .` | Explicit file set |

### Output formats

| Format | Flag | Has file:line? | Agent-friendly? | Use for |
|---|---|---|---|---|
| **SARIF** | `--format=sarif` | Yes (full location) | Yes | **Default for agents** -- structured, parseable, has file:line:col |
| JSON | `--format=json` | No (counts only) | Partial | Quick pass/fail check via `.totals` |
| Text | (default) | Partial (embedded JSON lines) | No | Human reading only |
| TOON | `--format=toon` | Yes | Yes | Token-efficient (~50% smaller than JSON) |
| JSONL | `--format=jsonl` | Varies | Partial | Streaming |

**Always use `--format=sarif` for agent work.** JSON lacks file:line locations. Text output is huge and inconsistent (banner art + embedded JSON lines). SARIF gives you ruleId, severity, file, line, column in a standard schema.

### Useful flags

| Flag | Effect |
|---|---|
| `--quiet` / `-q` | Suppress banner art and progress noise |
| `--ci` | CI mode: stable timestamps, no color |
| `--only=js,python` | Restrict to specific languages (3-5x faster) |
| `--exclude=csharp` | Skip specific languages |
| `--fail-on-warning` | Exit non-zero on warnings too (not just criticals) |
| `--ignore-file=PATH` | Use a specific ignore file |
| `--skip-size-check` | Bypass the 1GB directory size limit |
| `--report-json=FILE` | Write summary to file |
| `--jobs=N` | Parallelism hint |

### Environment variables

| Var | Effect |
|---|---|
| `UBS_MAX_DIR_SIZE_MB=0` | Disable directory size guard (needed for repos > 1GB) |
| `UBS_OUTPUT_FORMAT=sarif` | Default output format |
| `UBS_SKIP_SIZE_CHECK=1` | Same as `--skip-size-check` |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Clean -- no critical or warning findings |
| 1 | Findings present (critical or warning) |
| 2 | Usage error (bad arguments) |

### Subcommands

| Command | Use for |
|---|---|
| `ubs doctor` | Validate module checksums |
| `ubs doctor --fix` | Redownload corrupted modules |
| `ubs sessions --entries 1` | View latest install session log |
| `ubs --update` | Update the UBS binary |
| `ubs --update-modules` | Force redownload of all modules |

---

## Recipes

### Recipe #0 -- Quick pre-commit gate

```bash
# Stage your changes first
git add <files>

# Scan staged files
ubs --staged --format=sarif --quiet 2>/dev/null \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
critical=0
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    if r.get('level')=='error':
      critical+=1
      loc=r.get('locations',[{}])[0].get('physicalLocation',{})
      f=loc.get('artifactLocation',{}).get('uri','')
      ln=loc.get('region',{}).get('startLine','?')
      print(f\"CRITICAL {r.get('ruleId','?')} {f}:{ln}\")
print(f'\\n{critical} critical(s)')
"
# Exit 0 = safe to commit
```

### Recipe #1 -- Scan changed files (most common)

```bash
# What files changed?
changed=$(git diff --name-only HEAD)
[ -z "$changed" ] && echo "No changes" && exit 0

# Scan them
ubs --format=sarif --quiet $changed 2>/dev/null
```

### Recipe #2 -- Full project audit with triage

```bash
# Phase 1: counts only (cheap)
ubs --format=json --quiet --ci . 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['totals'])"

# Phase 2: if criticals > 0, get details via SARIF
ubs --format=sarif --quiet --ci . 2>/dev/null \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    if r.get('level')=='error':
      loc=r.get('locations',[{}])[0].get('physicalLocation',{})
      f=loc.get('artifactLocation',{}).get('uri','')
      ln=loc.get('region',{}).get('startLine','?')
      rule=r.get('ruleId','?')
      msg=r.get('message',{}).get('text','')[:80]
      print(f'{f}:{ln} [{rule}] {msg}')
"
```

### Recipe #3 -- Scoped language scan

```bash
# Only JS/TS (skip Python, Rust, etc.)
ubs --only=js --format=sarif --quiet src/ 2>/dev/null
```

### Recipe #4 -- Comparison against baseline

```bash
# Save baseline
ubs --format=json --quiet --ci --report-json=/tmp/ubs-baseline.json . 2>/dev/null

# After changes, diff against baseline
ubs --format=json --quiet --ci --comparison=/tmp/ubs-baseline.json . 2>/dev/null
```

### Recipe #5 -- Fix-and-verify loop

```bash
# 1. Scan
ubs --format=sarif --quiet file.ts 2>/dev/null > /tmp/ubs-findings.json

# 2. Read each finding, fix the code

# 3. Re-scan the same file
ubs --format=sarif --quiet file.ts 2>/dev/null
# Exit 0 = all fixed
```

---

## Output Parsing -- SARIF Reference

SARIF (Static Analysis Results Interchange Format) is the only UBS format with full file:line:col locations. Structure:

```json
{
  "runs": [{
    "results": [{
      "ruleId": "js.eval-call",
      "level": "error",        // error = critical, warning = warning, note = info
      "message": { "text": "eval() allows arbitrary code execution" },
      "locations": [{
        "physicalLocation": {
          "artifactLocation": { "uri": "/path/to/file.js" },
          "region": {
            "startLine": 42,
            "startColumn": 11,
            "endLine": 42,
            "endColumn": 23
          }
        }
      }]
    }]
  }]
}
```

SARIF severity mapping:
- `"error"` = UBS critical (always fix)
- `"warning"` = UBS warning (production risk, usually fix)
- `"note"` = UBS info (judgment call)

### One-liner to extract actionable findings

```bash
ubs --format=sarif --quiet <files> 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    if r.get('level') in ('error','warning'):
      loc=r.get('locations',[{}])[0].get('physicalLocation',{})
      f=loc.get('artifactLocation',{}).get('uri','')
      ln=loc.get('region',{}).get('startLine','?')
      col=loc.get('region',{}).get('startColumn','?')
      print(f\"{r['level']:8s} {r.get('ruleId','?'):30s} {f}:{ln}:{col}  {r.get('message',{}).get('text','')[:80]}\")
"
```

### JSON format (counts only, no locations)

```json
{
  "totals": { "critical": 1, "warning": 0, "info": 0, "files": 1 },
  "scanners": [{ "findings": [{ "severity": "critical", "count": 1, "title": "..." }] }]
}
```

Use JSON only for pass/fail checks. For triage, always use SARIF.

---

## False-Positive Triage

UBS produces many false positives on real codebases. The following categories are **known false positives** -- do NOT fix these:

### Always false positive (skip immediately)

| Finding | Why it's false | Example |
|---|---|---|
| Loose equality `==` in `functions/lib/` or `dist/` | Compiled JS output (TypeScript `__importStar` helper) | `mod != null` in `__createBinding` |
| `__proto__` / prototype pollution in test files | Intentional test payloads testing defense | `attack-helpers.ts` |
| Hardcoded credentials in test fixtures | Fake tokens, test passwords | `test-password-123` in `*.test.ts` |
| `eval()` in Playwright scripts | `$$eval` / `$eval` are Playwright APIs, not security holes | `page.$$eval('selector', ...)` |
| TSX JSX props flagged as global assignments | UBS mis-parses JSX attribute syntax | `<Comp value={x} />` |
| `process.env` in Node.js backend code | `security.env-in-client` rule -- backend code never reaches client | Firebase Functions `process.env.API_KEY` |
| `console.log` in scripts/tools | Intentional debugging output in non-production code | CLI tools, build scripts |

### Usually false positive (verify before skipping)

| Finding | When it's real | When it's false |
|---|---|---|
| Sensitive data logging | Logging actual secrets or PII | Logging token counts, request IDs |
| Stale closure | Mutable var captured before async boundary | Reactive refs read synchronously before `await` |
| Missing null check | Accessing property on nullable without guard | Framework-guaranteed non-null (e.g., route params after guard) |

### Triage workflow

1. Read finding: note ruleId, file, line
2. Check if file is in a known-FP category (compiled output, test fixtures, generated code)
3. If not obvious FP: read the actual code at that line
4. Determine: is this a real bug or a pattern UBS doesn't understand?
5. Real bug -> fix it, re-run UBS
6. False positive -> suppress via `.ubsignore` (directory) or `// ubs:ignore` (line)

---

## .ubsignore

UBS reads `.ubsignore` from the project root (or `--ignore-file=PATH`). Syntax is like `.gitignore`:

```
# Directories to exclude entirely
node_modules/
dist/
build/
.next/
functions/lib/          # compiled JS output -- always FP
coverage/
playwright-report/
test-results/

# File patterns
*.min.js
*.bundle.js

# Specific files with known FP patterns
scripts/research_*.mjs  # Playwright $$eval triggers eval heuristics
```

### Matching semantics

- Bare directory names (e.g., `functions/lib`) match that path component during traversal
- Trailing `/` explicitly marks a directory
- Glob patterns work: `*.tsx`, `scripts/*.mjs`
- Comments start with `#`
- Leading `./` is stripped automatically

### When to use .ubsignore vs inline suppression

| Use `.ubsignore` when | Use `// ubs:ignore` when |
|---|---|
| Entire directory is noise (compiled output, vendored deps) | Specific line is a known FP but file has real findings |
| File type produces systematic FPs (`.tsx` with JSX prop FPs) | You want to preserve scanning for other rules in the file |
| Build artifacts, generated code | Server-only `process.env` in otherwise-scanned backend code |

### Inline suppression

Add `// ubs:ignore` (or `// ubs:ignore <reason>`) on the line with the finding:

```typescript
const apiKey = process.env.API_KEY  // ubs:ignore server-only env access
```

Use a consistent comment style across the project. `// ubs:ignore server-only env access` is the convention.

---

## Anti-Patterns -- DO NOT do these

### A1. Running `ubs .` on a large project without scoping
**Symptom:** 1000+ lines of output, 300k+ tokens, context blown.
**Why:** UBS scans everything. On a real project it finds hundreds of findings, most false positives.
**Correct:** Scope to changed files: `ubs --staged`, `ubs --diff`, or `ubs <specific-files>`. Only use `ubs .` for initial audits, and always with `--format=sarif --quiet`.

### A2. Using `--format=json` for triage
**Symptom:** You see counts but no file:line locations. You re-scan with text format to find them.
**Why:** JSON output has `totals` (counts) and `scanners[].findings[]` (category summaries), but NO per-finding file locations.
**Correct:** Use `--format=sarif` for triage. Use `--format=json` only for pass/fail checks.

### A3. Parsing text output
**Symptom:** Trying to grep/parse the default text output for findings.
**Why:** Text output has ASCII banner art, embedded raw JSON lines from ast-grep, and a summary that can disagree with the actual findings (known counting bug).
**Correct:** `--format=sarif --quiet` for machine parsing.

### A4. Not staging before `--staged`
**Symptom:** `ubs --staged` returns "No changed files to scan" with exit 0.
**Why:** `--staged` scans the git index. If nothing is staged, there's nothing to scan.
**Correct:** `git add <files>` first, then `ubs --staged`.

### A5. Fixing all findings without triage
**Symptom:** Spending 30 minutes "fixing" 96 criticals that are all false positives.
**Why:** UBS flags compiled JS (`functions/lib/`), test fixtures, and framework patterns as critical.
**Correct:** Triage first. Check file paths. If it's in `lib/`, `dist/`, `node_modules/`, or `*.test.*`, it's almost certainly a false positive. See $$False-Positive Triage.

### A6. Using broken flags
**Known broken flags:**
- `--category=<name>` -- returns "Unknown category filter" for most values
- `--suggest-ignore` -- crashes with `suggest_ignore_candidates: command not found`
**Correct:** Don't use these. Filter with `--only=<language>` instead of `--category`. Create `.ubsignore` manually instead of `--suggest-ignore`.

### A7. Treating exit 0 as "no issues exist"
**Symptom:** "UBS passed, ship it."
**Why:** Exit 0 means no critical or warning findings were detected *in the scanned scope*. If scope was wrong (no staged files, wrong directory, `.ubsignore` too broad), exit 0 is meaningless.
**Correct:** After a clean scan, verify the scope was correct: check that the right files were scanned.

### A8. Running `ubs` without `--quiet` in agent context
**Symptom:** 50+ lines of ASCII banner art consuming tokens.
**Why:** Default text mode prints two large ASCII art banners.
**Correct:** Always pass `--quiet` or `-q` in agent context.

### A9. Re-running full scans to find a single finding
**Symptom:** Full `ubs .` scan after fixing one file.
**Correct:** `ubs --format=sarif --quiet <the-file-you-fixed>` to verify just that file.

### A10. Changing correct code to silence a false positive
**Symptom:** Agent changes `!= null` to `!== null` to "satisfy the scanner," breaking dual null/undefined checks.
**Why:** This changes semantics. `!= null` intentionally catches both `null` and `undefined` -- it's a standard JavaScript idiom.
**Correct:** If a finding is a false positive, suppress it (`// ubs:ignore` or `.ubsignore`). Never change correct code to appease a scanner. The fix should address the *bug*, not the *alert*.

### A11. Web-searching for UBS documentation
**Symptom:** Agent runs a web search for "UBS ultimate bug scanner" instead of reading this skill.
**Why:** UBS is on GitHub but the canonical agent docs are this skill file.
**Correct:** Read this skill. Run `ubs --help` for CLI reference. Run `ubs doctor` for health check.

### A12. Spending 5+ tool calls identifying what UBS is
**Symptom:** Agent greps AGENTS.md, CLAUDE.md, and runs `which ubs` / `command -v ubs` multiple times before recognizing UBS.
**Why:** Agents don't know UBS exists until they read docs or this skill activates.
**Correct:** This skill provides full context. `ubs` is at `~/.local/bin/ubs`. Run `ubs --version` to confirm.

---

## Troubleshooting

### "Failed to prepare files workspace"
UBS copies files to a shadow workspace in /tmp. If you pass absolute paths to files outside the current directory tree, this can fail. **Always `cd` to the project root first**, then use relative paths: `ubs src/file.ts` not `ubs /absolute/path/to/file.ts`.

### "not a git repository; cannot run --staged"
You're not in a git repo. Use positional file args instead: `ubs file1.ts file2.py`

### "No changed files to scan" with --staged
Nothing is staged. Run `git add <files>` first.

### "Refusing to scan home directory"
UBS copies the target to /tmp. Set `UBS_REFUSE_HOME_ROOT=0` or specify a subdirectory.

### Directory size limit exceeded (> 1GB)
```bash
UBS_MAX_DIR_SIZE_MB=0 ubs --format=sarif --quiet . 2>/dev/null
```
Or use `--skip-size-check`.

### Module checksum mismatch
```bash
ubs doctor --fix  # redownloads and re-verifies
```

### "suggest_ignore_candidates: command not found"
Known bug in `--suggest-ignore`. Create `.ubsignore` manually instead.

### Output says 0 criticals but you see findings in the text
Known counting inconsistency between ast-grep's inline JSON output and the summary totals. Trust the SARIF output, which correctly counts all findings.

### UBS takes > 60 seconds on a few files
Check if type narrowing is running (`--skip-type-narrowing` to disable). Type narrowing helpers download and run Python/JS scripts per-file, which is slow on large files.

---

## Provenance

- **A1 (full-repo scan blows context):** CASS sessions 019cc612 (Codex Mar 7), 7f29e7ed, 0477d545, 8d8d4269 (Claude Code). Multiple agents independently hit 300k+ token output.
- **A2 (JSON lacks file:line):** 019cc612 Codex session. Agent cycled through 5 output formats trying to get structured triage data.
- **A3 (text output inconsistency):** Verified against live `ubs v5.2.75`. Text embeds ast-grep JSON lines but summary counts disagree.
- **A4 (--staged without staging):** CASS subagent dd0ae33855762512. Agent ran `--staged` before `git add`, got "No changed files."
- **A5 (96 false positive criticals):** Sessions 7f29e7ed, 0477d545. Agent spent 20+ minutes triaging all-FP findings in compiled JS and test fixtures.
- **A6 (broken flags):** 019cc612 Codex session. `--category=security` returned "Unknown category filter." `--suggest-ignore` crashed with exit 127.
- **A8 (banner art tokens):** All sessions. Every agent learned to add `--quiet` after first run.
- **False-positive categories:** Compiled from sessions 7f29e7ed, 0477d545, 8d8d4269, 019ce871 (ubsignore session). TSX FPs from `.ubsignore` in /data/projects/philomena.
- **SARIF as best format:** Codex session 019cc612. Agent independently concluded SARIF was the only format with file+line detail after trying all five.
- **Inline suppression pattern:** CASS session 019ce871. Agent developed `// ubs:ignore server-only env access` convention for 13 files.
- **A10 (changing code to appease scanner):** Session 7f29e7ed, subagent c10da2bf50ec200a. Agent changed intentional `!= null` to `!== null` to silence a false positive, breaking dual null/undefined guard semantics.
- **A12 (5+ tool calls to identify UBS):** Sessions 8d8d4269, 0477d545, 019cc342. Agents ran 3-5 grep/find commands before locating UBS documentation.
- **Phantom callable detection:** Session 8d8d4269 subagents. Agent invented cross-reference grep for `httpsCallable` vs backend exports. Not a UBS feature but a pattern UBS should catch.

---

## References

| File | When to open |
|---|---|
| [FALSE-POSITIVES.md](references/FALSE-POSITIVES.md) | Detailed false-positive catalog with examples |
| [SARIF-PARSING.md](references/SARIF-PARSING.md) | Full SARIF parsing recipes and jq one-liners |
| [SELF-TEST.md](SELF-TEST.md) | Failure-case tests verifying the skill against live UBS |
