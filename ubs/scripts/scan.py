#!/usr/bin/env python3
"""Capture one UBS scan without losing scope, diagnostics, or its real exit code."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def select(root, scope, paths):
    if scope == "project":
        if paths:
            raise ValueError("project scope takes no file paths; cd to the project root")
        return ["."], {}
    if paths:
        if scope == "staged":
            raise ValueError("choose staged scope OR explicit working-tree paths")
        names = paths
    else:
        args = ["diff", "--name-only", "-z", "--diff-filter=ACMRT"]
        args += ["--cached"] if scope == "staged" else ["HEAD"]
        names = git(root, *args).decode().split("\0")
        if scope == "changed":
            names += git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    names = sorted(set(n for n in names if n))
    selected = []
    for name in names:
        path = root / name
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"not an existing in-project file: {name!r}")
        selected.append(path.relative_to(root).as_posix())
    if scope == "staged" and selected:
        unstaged = set(git(root, "diff", "--name-only", "-z", "--", *selected).decode().split("\0"))
        if unstaged.intersection(selected):
            raise ValueError("partially staged files: verify an exact index snapshot, or scan explicit working-tree paths")
    return ["./" + n for n in selected], fingerprints(root, selected)


def fingerprints(root, names):
    return {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in names}


def results(sarif):
    if not isinstance(sarif, dict) or sarif.get("version") != "2.1.0" or not isinstance(sarif.get("runs"), list) or not sarif["runs"]:
        return None
    found = []
    for run in sarif["runs"]:
        if not isinstance(run, dict) or not isinstance(run.get("results", []), list):
            return None
        for finding in run.get("results", []):
            if not isinstance(finding, dict):
                return None
            found.append(finding)
    return found


def evaluate(rc, sarif, summary):
    """Never promote an empty, partial, legacy-unknown, or refused scan to clean."""
    findings = results(sarif)
    if rc == 3:
        return "not_scanned", 3
    if findings is None:
        return "incomplete", 2
    if not isinstance(summary, dict):
        return "coverage_unverified", 2
    if not isinstance(summary.get("failed_modules"), list):
        return "coverage_unverified", 2
    if summary.get("status") != "ok" or summary.get("failed_modules"):
        return "incomplete", 2
    scanners = summary.get("scanners")
    totals = summary.get("totals")
    if not isinstance(scanners, list) or not isinstance(totals, dict):
        return "coverage_unverified", 2
    if any(type(totals.get(k)) is not int or totals[k] < 0 for k in ("files", "critical", "warning", "info")):
        return "coverage_unverified", 2
    if not scanners or not totals["files"]:
        return "not_scanned", 3
    if rc not in (0, 1) or any(not isinstance(s, dict) or s.get("status") != "ok" for s in scanners):
        return "incomplete", 2
    critical = totals.get("critical", 0) or any(r.get("level") == "error" for r in findings)
    warnings = totals.get("warning", 0) or any(r.get("level") == "warning" for r in findings)
    if rc == 1 or critical:
        return "findings", 1
    return ("review_required" if warnings else "no_findings_reported"), 0


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError, UnicodeError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("changed", "staged", "project"), default="changed")
    parser.add_argument("--ubs-arg", action="append", default=[], help="e.g. --ubs-arg=--only=rust")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    cwd = Path.cwd()
    # Explicit paths are relative to the invocation directory. Git selectors are root based.
    try:
        root = Path(git(cwd, "rev-parse", "--show-toplevel").decode().strip())
    except subprocess.CalledProcessError:
        root = cwd
    artifact = Path(tempfile.mkdtemp(prefix="ubs-skill-"))
    record = {"artifact_dir": str(artifact), "root": str(root), "scope": args.scope,
              "scanner_exit": None, "status": "incomplete"}
    result = 2
    try:
        allowed = ("--only=", "--exclude=", "--exclude-langs=", "--ignore-file=", "--jobs=", "--config=")
        switches = {"--no-cargo", "--exclude-tests", "--skip-type-narrowing", "--no-cache", "--fail-on-warning"}
        if any(a not in switches and not a.startswith(allowed) for a in args.ubs_arg):
            raise ValueError("unsupported helper argument; use a documented raw scan for other modes")
        paths = [str((cwd / p).absolute().relative_to(root)) for p in args.paths]
        targets, before = select(root, args.scope, paths)
        record.update(targets=targets, input_sha256=before, analysis_options=args.ubs_arg)
        # Candidates for manual review, NOT an authoritative extension/coverage allowlist.
        manual = [p for p in targets if Path(p).suffix.lower() in
                  {".md", ".json", ".jsonl", ".jsonc", ".toml", ".lock", ".tf", ".yaml", ".yml"}
                  or Path(p).name.startswith(".env")]
        record["manual_review_candidates"] = manual
        if not targets:
            record["status"], result = "not_run_empty_scope", 3
        else:
            command = ["ubs", "--format=sarif", "--quiet", "--no-auto-update",
                       "--report-json=" + str(artifact / "summary.json"), *args.ubs_arg, *targets]
            record["command"] = command
            env = dict(os.environ, UBS_ALLOW_PARTIAL="0", UBS_ALLOW_NO_SCAN="0")
            with (artifact / "findings.sarif").open("w") as out, (artifact / "stderr.log").open("w") as err:
                completed = subprocess.run(command, cwd=root, env=env, stdout=out, stderr=err)
            record["scanner_exit"] = completed.returncode
            sarif, summary = load(artifact / "findings.sarif"), load(artifact / "summary.json")
            record["status"], result = evaluate(completed.returncode, sarif, summary)
            if before != fingerprints(root, list(before)):
                record["status"], result = "inputs_changed_during_scan", 2
            if manual and result == 0:
                record["status"] = "review_required"
            findings = results(sarif) or []
            record["sarif_counts"] = dict(collections.Counter(r.get("level", "unknown") for r in findings))
            record["totals"] = summary.get("totals") if isinstance(summary, dict) else None
            record["by_rule"] = dict(collections.Counter(r.get("ruleId", "unknown") for r in findings))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        record["error"] = str(error)
        record["status"], result = "incomplete", 2
    record["helper_exit"] = result
    (artifact / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    display = {k: record.get(k) for k in ("artifact_dir", "root", "scope", "status", "scanner_exit", "helper_exit", "sarif_counts", "totals", "error")}
    display["files_requested"] = len(record.get("targets", []))
    display["manual_review_candidates"] = record.get("manual_review_candidates", [])[:20]
    display["top_rules"] = sorted(record.get("by_rule", {}).items(), key=lambda x: x[1], reverse=True)[:20]
    print(json.dumps(display, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
