#!/usr/bin/env bash
# dcg skill self-test. Read-only: dcg only evaluates the commands, nothing runs.
#
# 1. Structure: SKILL.md frontmatter, references, test corpus.
# 2. Corpus: every case in tests/cases.json goes through `dcg hook --batch`, exactly the payload
#    the Claude Code hook sees. Recorded failures must be denied and every fix the skill
#    recommends must be allowed. A mismatch means dcg changed or the skill is wrong.
# 3. Coverage: every fix command quoted in SKILL.md's code blocks has a case.
set -uo pipefail

SKILL_DIR="$(cd -P "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"

command -v dcg >/dev/null || { echo "  SKIP  dcg not on PATH"; echo "PASS: 0 pass, 0 fail, 1 skip"; exit 0; }

python3 -I - "$SKILL_DIR" <<'PY'
import json, os, re, subprocess, sys

skill_dir = sys.argv[1]
passed = failed = 0

def check(ok, label):
    global passed, failed
    passed += ok
    failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")

def read(rel):
    with open(os.path.join(skill_dir, rel), encoding="utf-8") as f:
        return f.read()

print("=== dcg skill self-test ===")
print("--- Structure ---")
for rel in ["SKILL.md", "references/rules.md", "tests/cases.json"]:
    check(os.path.isfile(os.path.join(skill_dir, rel)), f"{rel} exists")
skill = read("SKILL.md")
front = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
check(bool(front) and re.search(r"^name: dcg$", front.group(1), re.M) is not None, "frontmatter name is dcg")
check(bool(front) and "description:" in front.group(1), "frontmatter has a description")
for link in sorted(set(re.findall(r"\]\(((?:references|tests)/[^)]+)\)", skill))):
    check(os.path.isfile(os.path.join(skill_dir, link)), f"link {link} resolves")
check("—" not in skill + read("references/rules.md"), "no em dashes")

print("--- Corpus (dcg hook --batch) ---")
cases = json.loads(read("tests/cases.json"))
ids = [c["id"] for c in cases]
check(len(ids) == len(set(ids)), f"{len(ids)} case ids are unique")
check(all(c["expect"] in ("allow", "deny") for c in cases), "every case expects allow or deny")
payload = "".join(json.dumps({"tool_name": "Bash", "tool_input": {"command": c["cmd"]}}) + "\n"
                  for c in cases)
proc = subprocess.run(["dcg", "hook", "--batch", "--continue-on-error"], input=payload,
                      capture_output=True, text=True)
results = {}
for line in proc.stdout.splitlines():
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if isinstance(r, dict) and "index" in r:
        results[r["index"]] = r
version = subprocess.run(["dcg", "--version"], capture_output=True, text=True).stdout.strip()
print(f"  ({version})")
for i, c in enumerate(cases):
    r = results.get(i, {})
    got = r.get("decision", "missing")
    note = f" [{r.get('rule_id')}]" if r.get("rule_id") else ""
    policy = " (policy: forbidden by the skill)" if c.get("policy") == "forbidden" else ""
    check(got == c["expect"], f"{c['id']}: expect {c['expect']}, got {got}{note}{policy}")

print("--- Coverage ---")
corpus = {c["cmd"] for c in cases}
blocks = re.findall(r"```bash\n(.*?)```", skill, re.S)
for block in blocks:
    for line in block.splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith(("dcg test", "dcg explain", "bash scripts/")):
            continue
        check(line in corpus, f"SKILL.md command has a case: {line}")

print(f"PASS: {passed} pass, {failed} fail, 0 skip")
sys.exit(1 if failed else 0)
PY
