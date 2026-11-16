#!/usr/bin/env bash
# agent-mail-ops skill self-test. Read-only: `am <cmd> --help` and one MCP tools/list call.
#
# 1. Structure: frontmatter, references, links, no em dashes.
# 2. Guardrails: each failure mode found in past sessions (references/evidence.md) has its rule.
# 3. Drift: every `am` subcommand the skill names answers --help, and every Agent Mail tool it
#    names is in the live server's tools/list. Without am or the server, those are skipped.
set -uo pipefail

SKILL_DIR="$(cd -P "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"

python3 -I - "$SKILL_DIR" <<'PY'
import json, os, re, shutil, subprocess, sys, urllib.request

skill_dir = sys.argv[1]
passed = failed = skipped = 0

def check(ok, label):
    global passed, failed
    passed += ok
    failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")

def skip(label):
    global skipped
    skipped += 1
    print(f"  SKIP  {label}")

def read(rel):
    with open(os.path.join(skill_dir, rel), encoding="utf-8") as f:
        return f.read()

print("=== agent-mail-ops skill self-test ===")
print("--- Structure ---")
for rel in ["SKILL.md", "references/evidence.md", "references/recovery.md"]:
    check(os.path.isfile(os.path.join(skill_dir, rel)), f"{rel} exists")
skill = read("SKILL.md")
front = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
check(bool(front) and re.search(r"^name: agent-mail-ops$", front.group(1), re.M) is not None,
      "frontmatter name is agent-mail-ops")
for link in sorted(set(re.findall(r"\]\((references/[^)]+)\)", skill))):
    check(os.path.isfile(os.path.join(skill_dir, link)), f"link {link} resolves")
alltext = skill + read("references/evidence.md") + read("references/recovery.md")
check("—" not in alltext, "no em dashes")

print("--- Guardrails from past failures ---")
rules = {
    "one identity per session": "One identity per session",
    "no retry after a registration timeout": "may have succeeded",
    "resume with your own name": "server-issued `name`",
    "never choose a name": "INVALID_AGENT_NAME",
    "keep and pass sender_token": "sender_token",
    "confirm recipients with whois (ghost agents)": "silently creates a placeholder agent",
    "contact approval handling": "Contact approval required",
    "no inbox polling": "never poll",
    "acknowledge ack_required": "ack_required",
    "main repo path as project_key, slug in URIs": "even inside a worktree",
    "read-only conflict check before reserving": "check_file_reservation_conflicts",
    "never edit despite a conflict": "never edit the file anyway",
    "refused force-release is final": "refusing\n  forced release",
    "last_active heuristic is not proof": "does **not** prove an agent is dead",
    "reservation ids without grepping the archive": "am file_reservations active",
    "narrow globs": "Narrow paths",
    "short lease on .beads/issues.jsonl": ".beads/issues.jsonl",
    "renew with an id list": "ids are a list",
    "build slots disabled": "FEATURE_DISABLED",
    "shared tree: stage own paths": "git diff --cached",
    "down: retry once then proceed": "Retry the call **once**",
    "down: no curl or sqlite workarounds": "no `curl` JSON-RPC",
    "no manual server": "Never** launch `am serve-http`",
    "wedged server branch": "pool_acquire",
    "timeouts on triage curls": "curl -m 10",
    "NRestarts in triage": "NRestarts",
    "stale am CLI processes": "activity lock",
    "am setup skips tokenless entries": "skips entries that have no bearer",
    "never touch the live database": "not even a `pragma`",
    "copy db with wal and shm": "`-wal` and `-shm`",
    "GH#151 false positive": "GH#151",
    "self-heal takes about 2 minutes": "about 2 minutes",
    "never build am from source": "never build `am` from source",
}
for label, needle in rules.items():
    check(needle in alltext, label)

print("--- Drift: am subcommands ---")
am = shutil.which("am")
if not am:
    skip("am not on PATH")
else:
    cmds = set()
    for m in re.finditer(r"`am ([a-z_-]+)(?: ([a-z_-]+))?", skill):
        cmds.add((m.group(1), m.group(2)))
    for sub, sub2 in sorted(cmds, key=lambda t: (t[0], t[1] or "")):
        argv = [am, sub] + ([sub2] if sub2 else []) + ["--help"]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        if r.returncode != 0 and sub2:
            r = subprocess.run([am, sub, "--help"], capture_output=True, text=True, timeout=20)
            label = f"am {sub} (with argument {sub2})"
        else:
            label = f"am {sub}{' ' + sub2 if sub2 else ''}"
        check(r.returncode == 0, f"{label} --help exits 0")

print("--- Drift: MCP tool names ---")
try:
    req = urllib.request.Request(
        "http://127.0.0.1:8765/mcp/",
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
    payload = body[body.index("{"):] if not body.lstrip().startswith("{") else body
    for line in body.splitlines():
        if line.startswith("data:"):
            payload = line[5:]
    tools = {t["name"] for t in json.loads(payload)["result"]["tools"]}
except Exception as exc:
    tools = None
    skip(f"server tools/list unavailable ({type(exc).__name__})")
if tools is not None:
    named = set(re.findall(r"`([a-z_]+)\(", skill)) | set(re.findall(r"`([a-z]+_[a-z_]+)`", skill))
    named = {n for n in named if n not in {"project_key", "human_key", "agent_name", "sender_token",
             "registration_token", "thread_id", "since_ts", "include_bodies", "ack_required",
             "last_active_ts", "inception_ts", "file_reservation_ids", "extend_seconds",
             "ttl_seconds", "pane_id", "health_level", "health_level_contributors",
             "functionally_degraded", "reclaimable_attention", "safe_to_mutate",
             "integrity_check", "failing_verdicts", "verdicts", "mcp_agent_mail",
             "file_reservations", "storage.sqlite3", "pool_acquire"}}
    for name in sorted(named):
        check(name in tools, f"tool {name} exists on the server")

print(f"PASS: {passed} pass, {failed} fail, {skipped} skip")
sys.exit(1 if failed else 0)
PY
