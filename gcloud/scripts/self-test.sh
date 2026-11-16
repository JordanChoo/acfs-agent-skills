#!/usr/bin/env bash
# gcloud skill self-test. Never reaches Google and never touches the shared gcloud config:
# gcloud runs only with an empty throwaway CLOUDSDK_CONFIG, the deploy watcher runs against a stub.
#
# 1. Structure: frontmatter, references, links, no em dashes, nothing private in a public repo.
# 2. Corpus: scripts/test_gcloud.py (wrong forms fail, every command in SKILL.md parses, identity,
#    watcher outcomes, emulator recipe, shared config untouched).
set -uo pipefail

SKILL_DIR="$(cd -P "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"

python3 -I - "$SKILL_DIR" <<'PY'
import os, re, sys
skill_dir = sys.argv[1]
passed = failed = 0
def check(ok, label):
    global passed, failed
    passed += bool(ok); failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
print("=== gcloud skill structure ===")
skill = open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8").read()
front = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
check(bool(front) and re.search(r"^name: gcloud$", front.group(1), re.M) is not None, "frontmatter name is gcloud")
for rel in ["references/evidence.md", "scripts/test_gcloud.py", "scripts/watch_deploy.py"]:
    check(os.path.isfile(os.path.join(skill_dir, rel)), f"{rel} exists")
for link in sorted(set(re.findall(r"\]\((references/[^)]+)\)", skill))):
    check(os.path.isfile(os.path.join(skill_dir, link)), f"link {link} resolves")
texts = {}
for root, _, files in os.walk(skill_dir):
    for f in files:
        if f.endswith((".md", ".py", ".sh")):
            texts[os.path.relpath(os.path.join(root, f), skill_dir)] = open(os.path.join(root, f), encoding="utf-8").read()
check(all(chr(0x2014) not in t for t in texts.values()), "no em dashes")
# Public repo: no real project IDs, no real account emails.
private = re.compile(r"[\w.-]+@(?!example\.com|b\.c\b|p1?\.iam\.gserviceaccount\.com)[\w-]+\.(?:ventures|com|iam\.gserviceaccount\.com)|\b[a-z]+-\d{6}\b|\b[a-z]+-\d\d[a-z]\d\d\b")
leaks = [(n, m.group(0)) for n, t in texts.items() for m in private.finditer(t)]
check(not leaks, "no real project IDs or account emails" + (f": {leaks[:3]}" if leaks else ""))
print(f"{'PASS' if not failed else 'FAIL'}: {passed} pass, {failed} fail, 0 skip")
sys.exit(1 if failed else 0)
PY
structure_rc=$?
python3 "$SKILL_DIR/scripts/test_gcloud.py" </dev/null
corpus_rc=$?
if [ "$structure_rc" -ne 0 ] || [ "$corpus_rc" -ne 0 ]; then
  echo "FAIL: structure=$structure_rc corpus=$corpus_rc"
  exit 1
fi
echo "PASS: gcloud skill structure and corpus"
