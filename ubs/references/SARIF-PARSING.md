# Inspect a saved scan; do not rescan to change presentation

The runner writes `findings.sarif`, `summary.json`, `stderr.log`, and `record.json`
to a unique artifact directory. `record.json.scanner_exit` is the actual scanner
exit; `helper_exit` also rejects missing/malformed/incomplete coverage and changing
file inputs. Neither parser success nor zero criticals is a commit approval.

SARIF `runs[].results[]` carries rule, level, message and locations. The combined
JSON summary carries scanner coverage/status and, on current versions, can also
contain individual findings with locations. Avoid the old claim that JSON can
never contain file locations; use the documented stable fields of your version.

## Bounded triage (read an existing artifact)

```bash
python3 - "$report_dir/findings.sarif" <<'PY'
import collections, json, sys
with open(sys.argv[1]) as source:
    document = json.load(source)  # failure is missing evidence, not zero findings
if document.get('version') != '2.1.0' or not isinstance(document.get('runs'), list):
    raise SystemExit('Not a SARIF result; inspect stderr and scanner exit')
findings = [r for run in document['runs'] for r in run.get('results', [])]
print('Levels:', dict(collections.Counter(r.get('level', 'unknown') for r in findings)))
print('Top rules:', collections.Counter(r.get('ruleId', 'unknown') for r in findings).most_common(20))
for result in sorted(findings, key=lambda r: r.get('level') != 'error')[:30]:
    for location in result.get('locations', []):
        physical = location.get('physicalLocation', {})
        region = physical.get('region', {})
        print(result.get('level'), result.get('ruleId'),
              physical.get('artifactLocation', {}).get('uri'),
              region.get('startLine'), region.get('startColumn'))
print('Showing at most 30 findings; inspect remaining rules/locations before concluding.')
PY
```

Keep messages/source excerpts out of summaries when they may contain secrets or
caller content. Resolve relative SARIF paths against the recorded scan root and
check whether a shadow-workspace prefix needs mapping to the original file.

## Coverage checks

Inspect `summary.json.status`, `failed_modules`, `totals.files`, and each
`scanners[]` entry. Require the scan process to have completed. A scanner that
skipped compilation/dependencies (targeted Rust or explicit `--no-cargo`) has not
performed those checks; inspect its metadata and `Not evaluated` notes.
SARIF has version-specific refusal/no-language/partial envelopes too: an empty
`results` array by itself says nothing about success.

Do not independently count only `error` and print “Clean.” Warning policy,
unsupported files, ignores, skipped phases, scanner exit, and module failures
remain separate facts. Baseline/new-only views are presentation filters; inspect
current totals and coverage before treating old findings as resolved.
