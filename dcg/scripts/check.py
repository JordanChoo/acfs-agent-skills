#!/usr/bin/env python3
"""Evaluate a shell payload with DCG. Never execute the command being evaluated."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def classify(exit_code, stdout):
    try:
        rows = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    except ValueError:
        return "unverified", 2, None
    if len(rows) != 1 or not isinstance(rows[0], dict) or type(rows[0].get("index")) is not int or rows[0]["index"] != 0:
        return "unverified", 2, None
    row = rows[0]
    decision = row.get("decision")
    if row.get("error") or row.get("rule_id") == "general.unverified_decision":
        return "unverified", 2, row
    if decision == "allow" and exit_code == 0 and row.get("mode") in (None, "allow"):
        return "guard_allows", 0, row
    if decision == "deny" and exit_code == 1:
        return "blocked", 1, row
    return "unverified", 2, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--command-file", type=Path)
    source.add_argument("--payload", type=Path, help="exact JSON tool payload, including cwd/context when available")
    parser.add_argument("--tool", choices=("Bash", "PowerShell", "exec_command"), default="Bash")
    args = parser.parse_args()
    artifacts = Path(tempfile.mkdtemp(prefix="dcg-skill-check-"))
    report = {"artifact_dir": str(artifacts), "authorization": "not_checked",
              "will_execute_command": False, "status": "unverified", "dcg_exit": None}
    result = 2
    try:
        if args.payload:
            payload = json.loads(args.payload.read_text(encoding="utf-8"))
        else:
            field = "cmd" if args.tool == "exec_command" else "command"
            payload = {"tool_name": args.tool,
                       "tool_input": {field: args.command_file.read_text(encoding="utf-8")}}
        if not isinstance(payload, dict) or not isinstance(payload.get("tool_name"), str):
            raise ValueError("expected a JSON tool payload with tool_name")
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict) or not any(isinstance(tool_input.get(k), str) and tool_input[k].strip()
                                                      for k in ("command", "cmd")):
            raise ValueError("missing shell command; do not mistake a skipped invocation for allow")
        wire = json.dumps(payload, ensure_ascii=False)
        report["payload_sha256"] = hashlib.sha256(wire.encode()).hexdigest()
        report["tool_name"] = payload["tool_name"]
        report["cwd"] = str(Path.cwd())
        completed = subprocess.run(["dcg", "hook", "--batch", "--robot"], input=wire + "\n",
                                   text=True, capture_output=True, timeout=30, check=False)
        (artifacts / "stdout.jsonl").write_text(completed.stdout, encoding="utf-8")
        (artifacts / "stderr.log").write_text(completed.stderr, encoding="utf-8")
        report["dcg_exit"] = completed.returncode
        report["status"], result, row = classify(completed.returncode, completed.stdout)
        if row:
            report["guard_decision"] = row.get("decision")
            report["rule_id"] = row.get("rule_id")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        # Do not echo a command, credential, or raw JSON parse error into shared output.
        report["error"] = "Input or evaluator failed; inspect the input and local diagnostics. No command was executed."
    report["helper_exit"] = result
    (artifacts / "record.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
