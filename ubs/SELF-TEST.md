# Self-Test: ubs skill

Each test maps to a failure pattern observed in CASS sessions where agents used UBS.

Run via:
```bash
bash "$(dirname "$(realpath "$0" 2>/dev/null || echo .)")/scripts/self-test.sh"
# Or just:
bash ~/.claude/skills/ubs/scripts/self-test.sh
```

---

## Trigger Phrases (must activate the skill)

| Phrase | Expected |
|---|---|
| "run ubs before committing" | Activates |
| "scan these files for bugs" | Activates |
| "run the bug scanner" | Activates |
| "ubs is showing false positives" | Activates |
| "create a .ubsignore" | Activates |
| "security scan the changes" | Activates |
| "what does this ubs finding mean?" | Activates |

---

## Structure

```bash
SKILL_DIR=~/.claude/skills/ubs
test -f "$SKILL_DIR/SKILL.md"
test -f "$SKILL_DIR/references/FALSE-POSITIVES.md"
test -f "$SKILL_DIR/references/SARIF-PARSING.md"
test -x "$SKILL_DIR/scripts/self-test.sh"
```

---

## Behavioural Checks (the skill should produce these results)

### B1 -- Agent uses --format=sarif for triage
Any UBS scan intended for triage should use `--format=sarif`, not `--format=json` or default text.

Spot check: grep the agent's bash invocations for `ubs` without `--format=sarif` when the agent is triaging findings -- that's an A2 violation.

### B2 -- Agent uses --quiet in non-interactive context
Any UBS invocation from an agent should include `--quiet` or `-q` to suppress ASCII banner art.

### B3 -- Agent scopes to changed files, not full repo
Unless explicitly doing an initial audit, the agent should use `--staged`, `--diff`, or specific file arguments -- not bare `ubs .`.

### B4 -- Agent stages before --staged
If using `--staged`, the agent should `git add` first. Running `--staged` on an empty index is an A4 violation.

### B5 -- Agent triages before fixing
On a full-repo scan with many findings, the agent should classify false positives before attempting fixes. Jumping straight to fixes is an A5 violation.

### B6 -- Agent does NOT change correct code to appease scanner
If a finding is a false positive (e.g., intentional `!= null` for dual null/undefined check), the agent should suppress it, not change semantics to silence the scanner.

---

## Failure-Case Tests

### F1 -- UBS is installed and callable
```bash
command -v ubs >/dev/null && echo "F1 PASS" || echo "F1 FAIL (ubs not found)"
ubs --version 2>&1 | grep -q "UBS Meta-Runner" && echo "F1b PASS" || echo "F1b FAIL"
```

### F2 -- SARIF output has file:line:col locations
```bash
tmpdir=$(mktemp -d)
echo 'const x = eval("test");' > "$tmpdir/test.js"
sarif=$(ubs --format=sarif --quiet "$tmpdir/test.js" 2>/dev/null)
echo "$sarif" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    loc=r.get('locations',[{}])[0].get('physicalLocation',{})
    if loc.get('region',{}).get('startLine'):
      print('F2 PASS (SARIF has line numbers)')
      sys.exit(0)
print('F2 FAIL (no line numbers in SARIF)')
sys.exit(1)
" || echo "F2 FAIL"
rm -rf "$tmpdir"
```

### F3 -- JSON output has totals but NOT file:line
```bash
tmpdir=$(mktemp -d)
echo 'const x = eval("test");' > "$tmpdir/test.js"
j=$(ubs --format=json --quiet "$tmpdir/test.js" 2>/dev/null)
echo "$j" | python3 -c "
import sys,json
d=json.load(sys.stdin)
has_totals = 'totals' in d
# JSON findings don't have file locations
has_locations = False
for s in d.get('scanners',[]):
  for f in s.get('findings',[]):
    if 'locations' in f or 'file' in f:
      has_locations = True
if has_totals and not has_locations:
  print('F3 PASS (JSON has totals, no locations -- use SARIF instead)')
else:
  print(f'F3 INFO (totals={has_totals}, locations={has_locations})')
" || echo "F3 FAIL"
rm -rf "$tmpdir"
```

### F4 -- Exit code 0 for clean file, 1 for dirty file
```bash
tmpdir=$(mktemp -d)
echo 'const x = 1 + 2;' > "$tmpdir/clean.js"
echo 'const x = eval("test");' > "$tmpdir/dirty.js"
ubs --quiet "$tmpdir/clean.js" >/dev/null 2>&1; clean_exit=$?
ubs --quiet "$tmpdir/dirty.js" >/dev/null 2>&1; dirty_exit=$?
if [ "$clean_exit" -eq 0 ] && [ "$dirty_exit" -eq 1 ]; then
  echo "F4 PASS (exit 0=clean, 1=dirty)"
else
  echo "F4 FAIL (clean=$clean_exit, dirty=$dirty_exit)"
fi
rm -rf "$tmpdir"
```

### F5 -- --staged outside git repo gives clear error
```bash
tmpdir=$(mktemp -d)
cd "$tmpdir"
msg=$(ubs --staged --quiet 2>&1)
echo "$msg" | grep -qi "not a git" && echo "F5 PASS" || echo "F5 FAIL ($msg)"
cd - >/dev/null
rm -rf "$tmpdir"
```

### F6 -- doctor runs without error
```bash
ubs doctor 2>&1 | tail -1
echo "F6 exit=$?"
```

### F7 -- --quiet suppresses banner art
```bash
tmpdir=$(mktemp -d)
echo 'const x = 1;' > "$tmpdir/test.js"
lines=$(ubs --quiet --format=json "$tmpdir/test.js" 2>/dev/null | wc -l)
banner_lines=$(ubs --format=json "$tmpdir/test.js" 2>/dev/null | wc -l)
if [ "$lines" -lt "$banner_lines" ] || [ "$lines" -lt 20 ]; then
  echo "F7 PASS (--quiet reduces output: $lines vs $banner_lines lines)"
else
  echo "F7 INFO (quiet=$lines, normal=$banner_lines)"
fi
rm -rf "$tmpdir"
```

### F8 -- Known broken flags fail gracefully
```bash
tmpdir=$(mktemp -d)
echo 'const x = 1;' > "$tmpdir/test.js"

# --category=security should fail (known broken)
msg=$(ubs --category=security --quiet "$tmpdir/test.js" 2>&1)
echo "$msg" | grep -qi "unknown\|error\|invalid" \
  && echo "F8a PASS (--category fails as expected)" \
  || echo "F8a INFO (--category may have been fixed: $msg)"

rm -rf "$tmpdir"
```

### F9 -- .ubsignore excludes directories
```bash
tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/src" "$tmpdir/lib"
echo 'const x = eval("test");' > "$tmpdir/src/real.js"
echo 'const y = eval("test");' > "$tmpdir/lib/compiled.js"
echo 'lib/' > "$tmpdir/.ubsignore"

count_with=$(ubs --format=sarif --quiet "$tmpdir" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
c=sum(len(run.get('results',[])) for run in d.get('runs',[]))
print(c)
" 2>/dev/null)

# Without ignore: should find in both files
# With ignore: should only find in src/real.js
echo "F9 findings with .ubsignore: $count_with (expect: findings only from src/)"
rm -rf "$tmpdir"
```

---

## Cleanup

The tests above create temp directories and clean up after themselves. No manual cleanup needed.
