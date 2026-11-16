#!/usr/bin/env python3
"""Replay CASS failure cases and exercise the installed UBS without deleting fixtures."""
import copy
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ubs_scan", HERE / "scan.py")
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)
SARIF = {"version": "2.1.0", "runs": [{"results": []}]}
SUMMARY = {"status": "ok", "failed_modules": [], "scanners": [{"status": "ok"}],
           "totals": {"files": 1, "critical": 0, "warning": 0, "info": 0}}
WORK = Path(tempfile.mkdtemp(prefix="ubs-skill-selftest-"))
print(f"Retained test artifacts: {WORK}", flush=True)


class Classification(unittest.TestCase):
    def test_replay_empty_partial_legacy_and_malformed_outputs(self):
        cases = [
            (0, SARIF, SUMMARY, ("no_findings_reported", 0)),
            (0, None, SUMMARY, ("incomplete", 2)),
            (0, {}, SUMMARY, ("incomplete", 2)),
            (0, {"version": "2.1.0", "runs": []}, SUMMARY, ("incomplete", 2)),
            (0, SARIF, None, ("coverage_unverified", 2)),
            (0, SARIF, {k: v for k, v in SUMMARY.items() if k != "failed_modules"}, ("coverage_unverified", 2)),
            (0, SARIF, {"status": "partial", "failed_modules": ["rust"]}, ("incomplete", 2)),
            (0, SARIF, dict(SUMMARY, failed_modules=["js"]), ("incomplete", 2)),
            (0, SARIF, dict(SUMMARY, scanners=[]), ("not_scanned", 3)),
            (0, SARIF, dict(SUMMARY, scanners=[{"status": "timeout"}]), ("incomplete", 2)),
            (2, SARIF, SUMMARY, ("incomplete", 2)),
            (-15, SARIF, SUMMARY, ("incomplete", 2)),
            (3, None, None, ("not_scanned", 3)),
            (0, SARIF, dict(SUMMARY, totals={}), ("coverage_unverified", 2)),
            (0, {"version": "2.1.0", "runs": [None]}, SUMMARY, ("incomplete", 2)),
        ]
        for rc, sarif, summary, expected in cases:
            with self.subTest(rc=rc, expected=expected):
                self.assertEqual(scan.evaluate(rc, sarif, summary), expected)

    def test_zero_exit_with_warnings_is_review_required(self):
        summary = copy.deepcopy(SUMMARY)
        summary["totals"]["warning"] = 613
        self.assertEqual(scan.evaluate(0, SARIF, summary), ("review_required", 0))

    def test_parser_cannot_erase_nonzero_or_hidden_critical(self):
        self.assertEqual(scan.evaluate(1, SARIF, SUMMARY), ("findings", 1))
        sarif = copy.deepcopy(SARIF)
        sarif["runs"][0]["results"] = [{"level": "error", "ruleId": "canary"}]
        self.assertEqual(scan.evaluate(0, sarif, SUMMARY), ("findings", 1))

    def test_old_shell_counter_does_not_test_successfully_under_errexit(self):
        old = subprocess.run(["bash", "-c", "set -e; PASS=0; ok(){ ((PASS++)); echo PASS; }; ok"], capture_output=True)
        new = subprocess.run(["bash", "-c", "set -e; PASS=0; ok(){ PASS=$((PASS+1)); echo PASS; }; ok"], capture_output=True)
        self.assertNotEqual(old.returncode, 0)
        self.assertEqual(new.returncode, 0)


class Runner(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="case-", dir=WORK))
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        self.bin = Path(tempfile.mkdtemp(prefix="bin-", dir=WORK))
        self.payload = self.bin / "payload.json"
        self.payload.write_text(json.dumps({"rc": 0, "sarif": SARIF, "summary": SUMMARY}))
        fake = self.bin / "ubs"
        fake.write_text('#!' + sys.executable + '\n' + '''import json,os,pathlib,sys
p=json.loads(pathlib.Path(os.environ['UBS_TEST_PAYLOAD']).read_text())
pathlib.Path(os.environ['UBS_TEST_CALLED']).write_text(json.dumps(sys.argv[1:]))
sys.stderr.write('diagnostic retained\\n')
for a in sys.argv[1:]:
 if a.startswith('--report-json=') and p.get('summary') is not None:
  pathlib.Path(a.split('=',1)[1]).write_text(json.dumps(p['summary']))
if p.get('mutate'): pathlib.Path(p['mutate']).write_text('changed during scan')
if p.get('sarif') is not None: print(json.dumps(p['sarif']))
sys.exit(p['rc'])
''')
        fake.chmod(0o755)
        self.called = self.bin / "called.json"
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        UBS_TEST_PAYLOAD=str(self.payload), UBS_TEST_CALLED=str(self.called))

    def run_scan(self, *args, cwd=None):
        run = subprocess.run([sys.executable, str(HERE / "scan.py"), *args], cwd=cwd or self.root,
                             env=self.env, capture_output=True, text=True)
        out = json.loads(run.stdout)
        record = json.loads((Path(out["artifact_dir"]) / "record.json").read_text())
        return run, record

    def commit(self):
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Skill Test", "-c",
                        "user.email=skill-test@example.invalid", "commit", "-qm", "fixture"], check=True)

    def test_exact_filenames_and_untracked_scope(self):
        (self.root / "tracked.js").write_text("const initial = 1;\n")
        self.commit()
        (self.root / "tracked.js").write_text("const changed = 2;\n")
        for name in ["a file.js", "line\nbreak.js", "-leading.js"]:
            (self.root / name).write_text("const fresh = 3;\n")
        run, record = self.run_scan("--scope", "changed")
        self.assertEqual(run.returncode, 0)
        self.assertEqual(set(record["input_sha256"]), {"tracked.js", "a file.js", "line\nbreak.js", "-leading.js"})
        argv = json.loads(self.called.read_text())
        self.assertIn("./a file.js", argv)
        self.assertIn("./line\nbreak.js", argv)
        self.assertIn("./-leading.js", argv)
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.root), "diff", "--cached", "--name-only"]), b"")

    def test_empty_staged_scope_never_runs_bare_ubs(self):
        run, record = self.run_scan("--scope", "staged")
        self.assertEqual(run.returncode, 3)
        self.assertEqual(record["status"], "not_run_empty_scope")
        self.assertFalse(self.called.exists())

    def test_partially_staged_files_are_refused(self):
        source = self.root / "partial.js"
        source.write_text("const staged = 1;\n")
        subprocess.run(["git", "-C", str(self.root), "add", "partial.js"], check=True)
        source.write_text("const unstaged = 2;\n")
        run, record = self.run_scan("--scope", "staged")
        self.assertEqual(run.returncode, 2)
        self.assertIn("partially staged", record["error"])
        self.assertFalse(self.called.exists())

    def test_stderr_and_real_exit_are_retained(self):
        (self.root / "dirty.js").write_text("eval(data);\n")
        self.payload.write_text(json.dumps({"rc": 1, "sarif": SARIF, "summary": SUMMARY}))
        run, record = self.run_scan("dirty.js")
        self.assertEqual(run.returncode, 1)
        self.assertEqual(record["scanner_exit"], 1)
        self.assertIn("diagnostic retained", (Path(record["artifact_dir"]) / "stderr.log").read_text())

    def test_empty_output_is_not_zero_findings(self):
        (self.root / "source.js").write_text("const x = 1;\n")
        self.payload.write_text(json.dumps({"rc": 0, "sarif": None, "summary": None}))
        run, record = self.run_scan("source.js")
        self.assertEqual(run.returncode, 2)
        self.assertEqual(record["status"], "incomplete")

    def test_mixed_scope_keeps_manual_review_requirement(self):
        (self.root / "source.js").write_text("const x = 1;\n")
        (self.root / "notes.md").write_text("manual review required\n")
        run, record = self.run_scan("source.js", "notes.md")
        self.assertEqual(run.returncode, 0)
        self.assertEqual(record["status"], "review_required")
        self.assertEqual(record["manual_review_candidates"], ["./notes.md"])

    def test_changing_source_invalidates_scan(self):
        (self.root / "source.js").write_text("const x = 1;\n")
        self.payload.write_text(json.dumps({"rc": 0, "sarif": SARIF, "summary": SUMMARY, "mutate": "source.js"}))
        run, record = self.run_scan("source.js")
        self.assertEqual(run.returncode, 2)
        self.assertEqual(record["status"], "inputs_changed_during_scan")

    def test_post_scan_io_failure_cannot_keep_a_success_status(self):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["scan.py", "--scope", "project"]), \
             mock.patch.object(scan, "git", return_value=str(self.root).encode()), \
             mock.patch.object(scan, "select", return_value=(["./source.js"], {"source.js": "before"})), \
             mock.patch.object(scan.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
             mock.patch.object(scan, "load", side_effect=[SARIF, SUMMARY]), \
             mock.patch.object(scan, "fingerprints", side_effect=OSError("input unreadable")), \
             contextlib.redirect_stdout(out):
            rc = scan.main()
        record = json.loads(out.getvalue())
        self.assertEqual(rc, 2)
        self.assertEqual(record["status"], "incomplete")
        self.assertEqual(record["scanner_exit"], 0)

    def test_external_paths_and_report_overrides_are_refused(self):
        (self.root / "source.js").write_text("const x = 1;\n")
        for args in [("../outside.js",), ("--ubs-arg=--format=text", "source.js"),
                     ("--ubs-arg=--staged", "source.js")]:
            with self.subTest(args=args):
                run, _ = self.run_scan(*args)
                self.assertEqual(run.returncode, 2)
        self.assertFalse(self.called.exists())


class InstalledBinary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("ubs"):
            raise RuntimeError("live UBS tests NOT RUN: install via the approved tool workflow, then retry")
        cls.root = Path(tempfile.mkdtemp(prefix="live-", dir=WORK))
        (cls.root / "clean.js").write_text("const x = 1;\n")
        (cls.root / "dirty.js").write_text("const x = eval(userInput);\n")
        (cls.root / "notes.md").write_text("manual review\n")

    def call(self, *args):
        result = subprocess.run([sys.executable, str(HERE / "scan.py"),
                                 "--ubs-arg=--only=js", "--ubs-arg=--skip-type-narrowing",
                                 "--ubs-arg=--no-cache", *args], cwd=self.root, capture_output=True, text=True)
        report = json.loads(result.stdout)
        record = json.loads((Path(report["artifact_dir"]) / "record.json").read_text())
        return result, record

    def test_live_clean_dirty_and_locations(self):
        clean, cr = self.call("clean.js")
        self.assertEqual(clean.returncode, 0, cr)
        dirty, dr = self.call("dirty.js")
        self.assertEqual(dirty.returncode, 1, dr)
        sarif = json.loads((Path(dr["artifact_dir"]) / "findings.sarif").read_text())
        self.assertTrue(any(r.get("locations", [{}])[0].get("physicalLocation", {}).get("region", {}).get("startLine")
                            for r in scan.results(sarif)))

    def test_live_unsupported_markdown_is_not_a_pass(self):
        run, record = self.call("notes.md")
        self.assertEqual(run.returncode, 3, record)
        self.assertEqual(record["status"], "not_scanned")

    def test_live_ignore_keeps_a_real_finding(self):
        case = Path(tempfile.mkdtemp(prefix="ignore-", dir=WORK))
        (case / "generated").mkdir()
        (case / "generated" / "bundle.js").write_text("eval(untrusted);\n")
        (case / "source.js").write_text("eval(untrusted);\n")
        (case / ".ubsignore").write_text("# verified generated artifact\ngenerated/\n")
        result = subprocess.run(["ubs", "--format=sarif", "--quiet", "--no-auto-update",
                                 "--no-cache", "--only=js", "--skip-type-narrowing", "."],
                                cwd=case, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        findings = scan.results(json.loads(result.stdout))
        files = [loc["physicalLocation"]["artifactLocation"]["uri"] for r in findings for loc in r.get("locations", [])]
        self.assertTrue(any("source.js" in p for p in files))
        self.assertFalse(any("bundle.js" in p for p in files))

    def test_live_rust_test_filter_retains_production_findings(self):
        case = Path(tempfile.mkdtemp(prefix="rust-", dir=WORK))
        (case / "lib.rs").write_text('''pub fn production(x: Option<i32>) -> i32 { x.unwrap() }
#[cfg(test)]
mod tests {
    #[test]
    fn intentional_assertion() { assert!(true); }
}
''')
        reports = []
        for excluded in (False, True):
            command = ["ubs", "--format=sarif", "--quiet", "--no-auto-update", "--no-cache",
                       "--only=rust", "--no-cargo", "--skip-type-narrowing"]
            if excluded:
                command.append("--exclude-tests")
            # Fixed argv headed by "ubs", not caller input; subprocess uses no shell.
            result = subprocess.run(command + ["lib.rs"], cwd=case, capture_output=True, text=True)
            self.assertIn(result.returncode, (0, 1), result.stderr)
            findings = scan.results(json.loads(result.stdout))
            self.assertIsNotNone(findings)
            reports.append(findings)
        self.assertTrue(any(r.get("ruleId") == "rust.panic.assert-macros" for r in reports[0]))
        self.assertFalse(any(r.get("ruleId") == "rust.panic.assert-macros" for r in reports[1]))
        self.assertTrue(any("unwrap" in r.get("ruleId", "") for r in reports[1]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
