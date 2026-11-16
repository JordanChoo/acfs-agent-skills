#!/usr/bin/env bash
# br skill self-test. Writes only to fresh throwaway projects under a new temporary directory;
# never touches a real .beads and deletes nothing.
#
# 1. Structure: frontmatter, references, links, no em dashes.
# 2. Coverage: every `br <subcommand>` named in SKILL.md exists in the installed br.
# 3. Corpus: scripts/test_br.py tests claims, stale state, conflicts and preservation.
#    Legacy forced operations are hazard demonstrations confined to fresh fixtures.
set -uo pipefail

SKILL_DIR="$(cd -P "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"

python3 -I - "$SKILL_DIR" <<'PY'
import os, re, shutil, subprocess, sys, tempfile
skill_dir = sys.argv[1]
passed = failed = 0
def check(ok, label):
    global passed, failed
    passed += bool(ok); failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
skill = open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8").read()
print("=== br skill structure ===")
front = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
check(bool(front) and re.search(r"^name: br$", front.group(1), re.M) is not None, "frontmatter name is br")
for rel in ["references/evidence.md", "scripts/test_br.py"]:
    check(os.path.isfile(os.path.join(skill_dir, rel)), f"{rel} exists")
for link in sorted(set(re.findall(r"\]\((references/[^)]+)\)", skill))):
    check(os.path.isfile(os.path.join(skill_dir, link)), f"link {link} resolves")
evidence = open(os.path.join(skill_dir, "references/evidence.md"), encoding="utf-8").read()
check("—" not in skill + evidence, "no em dashes")
missing_path = tempfile.mkdtemp(prefix="br-skill-empty-path-")
probe = subprocess.run([sys.executable, os.path.join(skill_dir, "scripts/test_br.py")],
                       env=dict(os.environ, PATH=missing_path), capture_output=True,
                       text=True, timeout=15, check=False)
check(probe.returncode != 0 and "NOT RUN" in probe.stdout,
      "missing binary fails live coverage rather than silently skipping")
print("--- Policy regression reminders (static, not behavioral proof) ---")
for needle in ["Repository policy", "not an unconditional lossless union",
               "not necessarily the incoming side", "not proof of equal records",
               "--if-unchanged", "unexported", "is unconfirmed",
               "Worktrees may have separate DBs", "before issue edits",
               "No real project tracker is changed", "missing br fails"]:
    check(needle in skill, f"preserved guidance: {needle}")
if shutil.which("br"):
    stale = {"prime", "import"}   # documented as NOT existing
    subs = set()
    for block in re.findall(r"```bash\n(.*?)```", skill, re.S):
        code = "\n".join(line.split("#")[0] for line in block.splitlines())
        for m in re.finditer(r"(?:^|\s)br ([a-z][a-z-]*)(?: ([a-z][a-z-]*))?", code):
            subs.add((m.group(1), m.group(2)))
    for sub, sub2 in sorted(subs, key=lambda t: (t[0], t[1] or "")):
        if sub in stale:
            continue
        argv = ["br", sub] + ([sub2] if sub2 and sub in {"sync", "dep", "comments", "epic", "doctor", "robot-docs"} else []) + ["--help"]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=15,
                           env=dict(os.environ, RUST_LOG="error"), check=False)
        check(r.returncode == 0, f"br {' '.join(argv[1:-1])} exists")
print(f"PASS: {passed} pass, {failed} fail, 0 skip")
sys.exit(1 if failed else 0)
PY
structure_rc=$?
python3 "$SKILL_DIR/scripts/test_br.py" </dev/null
corpus_rc=$?
if [ "$structure_rc" -ne 0 ] || [ "$corpus_rc" -ne 0 ]; then
  echo "FAIL: structure=$structure_rc corpus=$corpus_rc"
  exit 1
fi
echo "PASS: br skill structure and corpus"
