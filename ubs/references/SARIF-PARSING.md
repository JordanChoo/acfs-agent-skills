# SARIF Parsing Recipes for UBS

SARIF (Static Analysis Results Interchange Format) is the **only** UBS output format that includes file:line:col locations. Always use `--format=sarif` for agent work.

---

## Full SARIF structure

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": { "driver": { "name": "ubs-js", "version": "..." } },
    "results": [
      {
        "ruleId": "js.eval-call",
        "level": "error",
        "message": { "text": "eval() allows arbitrary code execution" },
        "locations": [{
          "physicalLocation": {
            "artifactLocation": { "uri": "/absolute/path/to/file.js" },
            "region": {
              "startLine": 42,
              "startColumn": 11,
              "endLine": 42,
              "endColumn": 23
            }
          }
        }]
      }
    ]
  }]
}
```

## Severity mapping

| SARIF `level` | UBS severity | Action |
|---|---|---|
| `error` | Critical | Always investigate. Fix unless false positive. |
| `warning` | Warning | Usually fix for production code. |
| `note` | Info | Judgment call. Often noise. |

---

## One-liners

### List all critical and warning findings with locations

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

### Count findings by severity

```bash
ubs --format=sarif --quiet <files> 2>/dev/null | python3 -c "
import sys,json
from collections import Counter
d=json.load(sys.stdin)
c=Counter()
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    c[r.get('level','unknown')]+=1
for level in ('error','warning','note'):
  if c[level]: print(f'{level}: {c[level]}')
"
```

### Count findings by ruleId (find noisy rules)

```bash
ubs --format=sarif --quiet <files> 2>/dev/null | python3 -c "
import sys,json
from collections import Counter
d=json.load(sys.stdin)
c=Counter()
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    c[r.get('ruleId','?')]+=1
for rule,count in c.most_common(20):
  print(f'{count:4d}  {rule}')
"
```

### Filter to specific ruleId

```bash
ubs --format=sarif --quiet <files> 2>/dev/null | python3 -c "
import sys,json
TARGET='js.eval-call'
d=json.load(sys.stdin)
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    if r.get('ruleId')==TARGET:
      loc=r.get('locations',[{}])[0].get('physicalLocation',{})
      f=loc.get('artifactLocation',{}).get('uri','')
      ln=loc.get('region',{}).get('startLine','?')
      print(f'{f}:{ln}  {r.get(\"message\",{}).get(\"text\",\"\")[:100]}')
"
```

### Exclude findings in specific directories

```bash
ubs --format=sarif --quiet . 2>/dev/null | python3 -c "
import sys,json
EXCLUDE=['functions/lib/','dist/','node_modules/','build/']
d=json.load(sys.stdin)
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    loc=r.get('locations',[{}])[0].get('physicalLocation',{})
    f=loc.get('artifactLocation',{}).get('uri','')
    if any(ex in f for ex in EXCLUDE): continue
    if r.get('level') in ('error','warning'):
      ln=loc.get('region',{}).get('startLine','?')
      print(f\"{r['level']:8s} {r.get('ruleId','?'):30s} {f}:{ln}\")
"
```

### Pass/fail gate (exit 1 if any criticals after filtering)

```bash
ubs --format=sarif --quiet <files> 2>/dev/null | python3 -c "
import sys,json
EXCLUDE=['functions/lib/','dist/','node_modules/']
d=json.load(sys.stdin)
real=[]
for run in d.get('runs',[]):
  for r in run.get('results',[]):
    if r.get('level')!='error': continue
    loc=r.get('locations',[{}])[0].get('physicalLocation',{})
    f=loc.get('artifactLocation',{}).get('uri','')
    if any(ex in f for ex in EXCLUDE): continue
    real.append(f\"{r.get('ruleId','?')} {f}:{loc.get('region',{}).get('startLine','?')}\")
if real:
  print(f'{len(real)} real critical(s):')
  for r in real: print(f'  {r}')
  sys.exit(1)
else:
  print('Clean')
"
```
