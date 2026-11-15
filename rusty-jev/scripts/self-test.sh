#!/usr/bin/env bash
# Self-test for the rusty-jev skill. Read-only; makes no network calls.
#
# 1. Structure: SKILL.md frontmatter and the two reference files.
# 2. Drift: when the Rusty Jev repo is present (RUSTY_JEV_REPO, default
#    /data/projects/rusty-jev), compares the limits, tool names and fixed error
#    messages this skill states with the server's published contract:
#    tests/snapshots/tools_list.json and tests/snapshots/error_messages.txt.
#    Without the repo, the drift checks are skipped, not passed.
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${RUSTY_JEV_REPO:-/data/projects/rusty-jev}"

python3 -I - "$SKILL_DIR" "$REPO" <<'PY'
import json, os, re, sys

skill_dir, repo = sys.argv[1], sys.argv[2]
passed, failed, skipped = 0, 0, 0

def check(ok, label):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}")

def read(rel):
    with open(os.path.join(skill_dir, rel), encoding="utf-8") as f:
        return f.read()

print("=== rusty-jev skill self-test ===")
print("--- Structure ---")
for rel in ["SKILL.md", "references/tools.md", "references/errors.md", "references/recipes.md"]:
    check(os.path.isfile(os.path.join(skill_dir, rel)), f"{rel} exists")
skill = read("SKILL.md")
tools_md = read("references/tools.md")
errors_md = read("references/errors.md")
recipes_md = read("references/recipes.md")
for link in sorted(set(re.findall(r"\]\((references/[^)]+)\)", skill))):
    check(os.path.isfile(os.path.join(skill_dir, link)), f"SKILL.md link {link} resolves")
check("—" not in recipes_md, "recipes.md has no em dashes")
front = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
check(front is not None, "SKILL.md has YAML frontmatter")
check(bool(front) and re.search(r"^name: rusty-jev$", front.group(1), re.M) is not None,
      "frontmatter name is rusty-jev")
check(bool(front) and "description:" in front.group(1), "frontmatter has a description")
for name in ["decide", "classify", "verify", "rerank", "screen", "list_models"]:
    check(f"rusty-jev_{name}" in skill and f"## {name}" in tools_md,
          f"{name} is covered in SKILL.md and references/tools.md")
check("—" not in skill + tools_md + errors_md, "no em dashes")
check("required" in skill and "instructions" in skill, "SKILL.md says classify instructions are required")
check("snapshot ID" in skill, "SKILL.md warns that snapshot model IDs are rejected")

print("--- Drift against the Rusty Jev contract ---")
snapshot = os.path.join(repo, "tests/snapshots/tools_list.json")
messages = os.path.join(repo, "tests/snapshots/error_messages.txt")
if not (os.path.isfile(snapshot) and os.path.isfile(messages)):
    skipped += 1
    print(f"  SKIP  Rusty Jev repo not found at {repo} (set RUSTY_JEV_REPO)")
else:
    with open(snapshot, encoding="utf-8") as f:
        data = json.load(f)
    tools = data.get("tools") or data.get("result", {}).get("tools") or data
    by_name = {t["name"]: t for t in tools}
    check(sorted(by_name) == sorted(["decide", "classify", "verify", "rerank", "screen", "list_models"]),
          "the server publishes exactly the six tools the skill covers")

    def props(tool):
        return by_name[tool]["inputSchema"].get("properties", {})

    def question(kind):
        for variant in by_name["decide"]["inputSchema"]["$defs"]["Question"]["oneOf"]:
            if variant["properties"]["type"].get("const") == kind:
                return variant
        return {}

    limits = [
        ("decide questions 1 to 32", props("decide")["questions"].get("maxProperties"), 32),
        ("decide question IDs up to 128 characters",
         props("decide")["questions"].get("propertyNames", {}).get("maxLength"), 128),
        ("decide choice options up to 255", question("choice")["properties"]["criteria"].get("maxProperties"), 255),
        ("decide score levels up to 10", question("score")["properties"]["criteria"].get("maxItems"), 10),
        ("classify items up to 64", props("classify")["items"].get("maxItems"), 64),
        ("classify categories up to 250", props("classify")["categories"].get("maxProperties"), 250),
        ("verify claims up to 25", props("verify")["claims"].get("maxItems"), 25),
        ("rerank candidates up to 50", props("rerank")["candidates"].get("maxItems"), 50),
        ("rerank top_k up to 50", props("rerank")["top_k"].get("maximum"), 50),
    ]
    for label, actual, expected in limits:
        check(actual == expected, f"{label} (server says {actual})")
    for tool in by_name:
        check(props(tool).get("caller", {}).get("maxLength") == 64, f"{tool}: caller up to 64 characters")
    check("default 10" in props("rerank")["top_k"].get("description", ""), "rerank top_k defaults to 10")
    check("min_margin" not in props("screen"), "screen takes no min_margin")
    check(set(props("list_models")) == {"caller"}, "list_models takes only caller")
    for tool in ["classify", "verify", "rerank", "screen"]:
        desc = props(tool)["auto_accept"].get("description", "")
        check("default 0.85" in desc, f"{tool}: auto_accept defaults to 0.85")
    check("8,000" in by_name["classify"]["description"], "classify caps items x categories at 8,000")

    published = {}
    with open(messages, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split(None, 1)  # "code<TAB>message"
            if len(parts) == 2:
                published[parts[0]] = parts[1].strip()
    interactive = ["invalid_input", "unknown_model", "provider_not_configured", "rate_limited",
                   "daily_cap_reached", "service_unavailable", "upstream_rate_limited",
                   "upstream_rejected", "upstream_unavailable", "upstream_timeout",
                   "invalid_provider_answer"]
    for code in interactive:
        message = published.get(code)
        check(message is not None and f"| `{code}` | {message} |" in errors_md,
              f"errors.md quotes the fixed message for {code}")
    check(len(published) == 18, f"the server has 18 error codes (found {len(published)})")

    mcp_rs = os.path.join(repo, "src/mcp.rs")
    if os.path.isfile(mcp_rs):
        with open(mcp_rs, encoding="utf-8") as f:
            mcp_src = f.read()
        for code, message in [("-32602", "Unknown tool"), ("-32602", "Invalid params"),
                              ("-32601", "Method not found"),
                              ("-32600", "Unsupported protocol version"),
                              ("-32600", "Invalid Request"), ("-32700", "Parse error")]:
            check(f'"{message}"' in mcp_src and f"| `{code}` | {message} |" in errors_md,
                  f"errors.md quotes protocol error {code} {message!r} as src/mcp.rs has it")
        check('"2025-11-25"' in mcp_src, "the server's protocol version is 2025-11-25")

print(f"PASS: {passed} pass, {failed} fail, {skipped} skip")
sys.exit(1 if failed else 0)
PY
