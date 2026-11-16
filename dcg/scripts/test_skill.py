#!/usr/bin/env python3
"""DCG classifier regressions. Retain fixtures; never execute candidate text."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dcg_check", SKILL / "scripts/check.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
CASES = json.loads((SKILL / "tests/cases.json").read_text())


class Classification(unittest.TestCase):
    def test_skill_structure(self):
        skill = (SKILL / 'SKILL.md').read_text()
        front = re.match(r'^---\n(.*?)\n---\n', skill, re.S)
        self.assertIsNotNone(front)
        self.assertRegex(front.group(1), r'(?m)^name: dcg$')
        self.assertIn('description:', front.group(1))
        for target in re.findall(r'\]\(([^)]+)\)', skill):
            self.assertTrue((SKILL / target).is_file(), target)
        self.assertTrue((SKILL / 'tests/cases.json').is_file())

    def test_missing_evaluator_and_timeout_fail_closed(self):
        artifacts = Path(tempfile.mkdtemp(prefix='dcg-skill-failure-tests-'))
        candidate = artifacts / 'candidate.txt'
        candidate.write_text('pwd')
        for error in (FileNotFoundError('dcg missing'),
                      subprocess.TimeoutExpired(['dcg', 'hook'], 30)):
            with self.subTest(error=type(error).__name__):
                output = io.StringIO()
                with mock.patch.object(sys, 'argv', ['check.py', '--command-file', str(candidate)]), \
                     mock.patch.object(helper.subprocess, 'run', side_effect=error), \
                     contextlib.redirect_stdout(output):
                    self.assertEqual(helper.main(), 2)
                report = json.loads(output.getvalue())
                self.assertEqual(report['status'], 'unverified')
                self.assertIs(report['will_execute_command'], False)

    def test_response_matrix(self):
        cases = [
            (0, {'index': 0, 'decision': 'allow'}, 'guard_allows'),
            (1, {'index': 0, 'decision': 'deny'}, 'blocked'),
            (0, {'index': 0, 'decision': 'deny'}, 'unverified'),
            (1, {'index': 0, 'decision': 'allow'}, 'unverified'),
            (-9, {'index': 0, 'decision': 'allow'}, 'unverified'),
            (0, {'index': 0, 'decision': 'skip'}, 'unverified'),
            (0, {'index': False, 'decision': 'allow'}, 'unverified'),
            (0, {'index': 1, 'decision': 'allow'}, 'unverified'),
            (0, {'index': 0, 'decision': 'allow', 'mode': 'warn'}, 'unverified'),
            (1, {'index': 0, 'decision': 'deny', 'error': 'timeout'}, 'unverified'),
            (1, {'index': 0, 'decision': 'deny', 'rule_id': 'general.unverified_decision'}, 'unverified'),
            (0, {'hookSpecificOutput': {'permissionDecision': 'deny'}}, 'unverified'),
        ]
        for rc, row, expected in cases:
            with self.subTest(rc=rc, row=row):
                self.assertEqual(helper.classify(rc, json.dumps(row))[0], expected)
        for wire in ('', '{', 'null', '[]', 'true', '{}\n{}',
                     '{"index":0,"decision":"allow"}\n{"index":0,"decision":"allow"}'):
            with self.subTest(wire=wire):
                self.assertEqual(helper.classify(0, wire)[0:2], ('unverified', 2))

    def test_corpus_integrity(self):
        self.assertEqual(len(CASES), 61)
        self.assertEqual(len({c['id'] for c in CASES}), len(CASES))
        by_id = {c['id']: c for c in CASES}
        for name in ('fix-stash-paths', 'fix-switch-detach', 'fix-force-with-lease',
                     'fix-worktree-remove', 'fix-rm-tmp-literal', 'fix-rm-named-files',
                     'fix-rmdir', 'fix-rename-in-place', 'fix-trash-files'):
            self.assertEqual(by_id[name]['expect'], 'allow')
            self.assertEqual(by_id[name]['policy'], 'owner_required')
        for name in ('fix-trash-relative', 'policy-move-then-delete'):
            self.assertEqual(by_id[name]['policy'], 'forbidden')


class LiveHook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('dcg'):
            raise RuntimeError('DCG missing: live coverage NOT RUN; install/setup required')
        cls.artifacts = Path(tempfile.mkdtemp(prefix='dcg-skill-tests-'))
        print('Retained test artifacts:', cls.artifacts, flush=True)

    def hook(self, payload, batch=True):
        args = ['dcg', 'hook'] + (['--batch', '--robot'] if batch else [])
        return subprocess.run(args, input=json.dumps(payload) + '\n',
                              text=True, capture_output=True, timeout=30, check=False)

    def test_full_historical_corpus(self):
        wire = ''.join(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': c['cmd']}})
                       + '\n' for c in CASES)
        proc = subprocess.run(['dcg', 'hook', '--batch', '--robot'], input=wire,
                              text=True, capture_output=True, timeout=60, check=False)
        (self.artifacts / 'corpus.stdout.jsonl').write_text(proc.stdout)
        (self.artifacts / 'corpus.stderr.log').write_text(proc.stderr)
        rows = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(rows), len(CASES))
        self.assertEqual([r['index'] for r in rows], list(range(len(CASES))))
        self.assertEqual(proc.returncode, 1)
        for case, row in zip(CASES, rows):
            with self.subTest(case=case['id']):
                self.assertFalse(row.get('error'))
                self.assertNotEqual(row.get('rule_id'), 'general.unverified_decision')
                self.assertEqual(row.get('decision'), case['expect'])
        print(f'  Replayed {len(CASES)} historical candidates as data', flush=True)

    def test_single_hook_exit_is_not_batch_convention(self):
        command = next(c['cmd'] for c in CASES if c['id'] == 'reset-hard')
        proc = self.hook({'tool_name': 'Bash', 'tool_input': {'command': command}}, batch=False)
        self.assertEqual(proc.returncode, 0)
        row = json.loads(proc.stdout)
        self.assertEqual(row['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(helper.classify(proc.returncode, proc.stdout)[0], 'unverified')

    def test_unsupported_tool_is_unverified(self):
        proc = self.hook({'tool_name': 'functions.exec_command', 'tool_input': {'cmd': 'pwd'}})
        self.assertEqual(helper.classify(proc.returncode, proc.stdout)[0], 'unverified')

    def test_helper_never_executes_candidate(self):
        marker = self.artifacts / 'MUST-NOT-EXIST'
        command_file = self.artifacts / 'candidate.txt'
        command_file.write_text('touch ' + str(marker))
        proc = subprocess.run([sys.executable, str(SKILL / 'scripts/check.py'),
                               '--command-file', str(command_file)], capture_output=True,
                              text=True, timeout=40, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report['status'], 'guard_allows')
        self.assertEqual(report['authorization'], 'not_checked')
        self.assertIs(report['will_execute_command'], False)
        self.assertFalse(marker.exists())

    def test_helper_bad_payload_fails_without_echo(self):
        payload = self.artifacts / 'malformed.json'
        payload.write_text('{PRIVATE_INPUT_DO_NOT_ECHO')
        proc = subprocess.run([sys.executable, str(SKILL / 'scripts/check.py'),
                               '--payload', str(payload)], capture_output=True,
                              text=True, timeout=40, check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)['status'], 'unverified')
        self.assertNotIn('PRIVATE_INPUT_DO_NOT_ECHO', proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
