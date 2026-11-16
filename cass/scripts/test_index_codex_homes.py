#!/usr/bin/env python3
"""Offline regressions; never run cass or touch real session/archive files."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('homes', Path(__file__).with_name('index_codex_homes.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Coverage(unittest.TestCase):
    def test_default_isolated_and_future_discovery(self):
        root = Path(tempfile.mkdtemp(prefix='cass-homes-test-'))
        default = root / '.codex'
        isolated = root / '.codex-instances/tmux-1'
        for p in [default, isolated]:
            (p / 'sessions/2026/11/16').mkdir(parents=True)
        self.assertEqual(module.homes(root), [default, isolated])
        future = root / '.codex-instances/tmux-2'
        (future / 'sessions').mkdir(parents=True)
        self.assertIn(future, module.homes(root))

    def test_only_changed_rollouts_pending(self):
        home = Path(tempfile.mkdtemp(prefix='cass-homes-pending-'))
        (home / 'sessions').mkdir()
        rollout = home / 'sessions/rollout-test.jsonl'
        rollout.write_text('{}\n')
        (home / 'sessions/other.jsonl').write_text('{}\n')
        self.assertEqual(module.pending(home, {}), [rollout])
        cached = {str(rollout): module.fingerprint(rollout)}
        self.assertEqual(module.pending(home, cached), [])
        rollout.write_text('{}\n{}\n')
        self.assertEqual(module.pending(home, cached), [rollout])

    def test_exact_targeted_command_preserves_paths(self):
        argv = module.command('/bin/cass', Path('/tmp/cass data'), [Path('/tmp/home with spaces/session.jsonl')])
        self.assertIn('--watch-once', argv)
        self.assertNotIn('--full', argv)
        self.assertNotIn('--force', argv)
        self.assertEqual(argv[-1], '/tmp/home with spaces/session.jsonl')
        self.assertEqual(argv[2], '/tmp/cass data/agent_search.db')

    def test_only_verified_full_batches_can_checkpoint(self):
        valid = {'success': True, 'full': False, 'quarantined_conversations': 0,
                 'lexical_update_deferred': False, 'indexing_stats': {
                     'scan_had_errors': False, 'deferred_active_sources': 0,
                     'connector_summary': {'codex': {'indexed': 2, 'partially_indexed': 0}}}}
        self.assertTrue(module.verified_batch(valid, 2))
        self.assertFalse(module.verified_batch(valid, 3))
        self.assertFalse(module.verified_batch({}, 1))
        for field, value in [('success', False), ('full', True), ('quarantined_conversations', 1),
                             ('lexical_update_deferred', True)]:
            with self.subTest(field=field):
                altered = dict(valid, **{field: value})
                self.assertFalse(module.verified_batch(altered, 2))
        valid['indexing_stats']['deferred_active_sources'] = 1
        self.assertFalse(module.verified_batch(valid, 2))
        self.assertTrue(module.active_deferral_only(valid))
        valid['indexing_stats']['scan_had_errors'] = True
        self.assertFalse(module.active_deferral_only(valid))
        self.assertFalse(module.active_deferral_only([]))

    def test_checkpoint_archive_binding(self):
        root = Path(tempfile.mkdtemp(prefix='cass-homes-checkpoint-'))
        checkpoint = root / 'checkpoint.json'
        module.save_checkpoint(checkpoint, root / 'archive', {'x': [1, 2]})
        value = json.loads(checkpoint.read_text())
        self.assertEqual(value, {'archive': str(root / 'archive'), 'files': {'x': [1, 2]}})

    def test_timeline_coverage_is_complete_and_scoped(self):
        payload = {'total_sessions': 1, 'sessions': [{'agent': 'codex', 'source_path': '/log'}]}
        with mock.patch.object(module.subprocess, 'run', return_value=SimpleNamespace(
                returncode=0, stdout=json.dumps(payload))) as run:
            self.assertEqual(module.archive_paths('cass', Path('/archive')), {'/log'})
            self.assertIn('timeline', run.call_args.args[0])
        payload['total_sessions'] = 2
        with mock.patch.object(module.subprocess, 'run', return_value=SimpleNamespace(
                returncode=0, stdout=json.dumps(payload))):
            with self.assertRaises(ValueError):
                module.archive_paths('cass', Path('/archive'))

    def test_retry_only_explicit_index_busy(self):
        busy = SimpleNamespace(returncode=7, stdout=json.dumps({'kind': 'index-busy'}))
        success = SimpleNamespace(returncode=0, stdout=json.dumps({'success': True}))
        with mock.patch.object(module.subprocess, 'run', side_effect=[busy, success]) as run, \
             mock.patch.object(module.time, 'sleep') as sleep:
            proc, result = module.index_batch('cass', Path('/archive'), [Path('/log')], {})
            self.assertEqual(run.call_count, 2)
            self.assertEqual(sleep.call_count, 1)
            self.assertTrue(result['success'])
        failure = SimpleNamespace(returncode=9, stdout=json.dumps({'kind': 'index'}))
        with mock.patch.object(module.subprocess, 'run', return_value=failure) as run:
            module.index_batch('cass', Path('/archive'), [Path('/log')], {})
            self.assertEqual(run.call_count, 1)

    def test_malformed_index_output_is_retained_as_failure(self):
        failure = SimpleNamespace(returncode=0, stdout='malformed', stderr='diagnostic')
        with mock.patch.object(module.subprocess, 'run', return_value=failure):
            proc, result = module.index_batch('cass', Path('/archive'), [Path('/log')], {})
            self.assertEqual(proc.stdout, 'malformed')
            self.assertEqual(proc.stderr, 'diagnostic')
            self.assertFalse(result['success'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
