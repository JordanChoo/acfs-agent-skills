#!/usr/bin/env python3
"""Static regressions; --live adds bounded read-only schema/help probes."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = json.loads((ROOT / 'tests/scenarios.json').read_text())


def decode_tools(body):
    """Accept JSON-RPC JSON or SSE; errors/incomplete discovery are not passes."""
    payloads = []
    try:
        payloads.append(json.loads(body))
    except ValueError:
        for event in body.replace('\r\n', '\n').split('\n\n'):
            data = '\n'.join(line[5:].lstrip(' ') for line in event.splitlines()
                             if line.startswith('data:'))
            if data:
                payloads.append(json.loads(data))
    for payload in payloads:
        if not isinstance(payload, dict) or payload.get('id') != 'skill-schema-audit':
            continue
        if 'error' in payload:
            raise ValueError('tools/list returned error')
        result = payload.get('result')
        if not isinstance(result, dict) or not isinstance(result.get('tools'), list):
            raise ValueError('missing tools list')
        tools = result['tools']
        if not tools or any(not isinstance(t, dict) or not isinstance(t.get('name'), str)
                            for t in tools):
            raise ValueError('invalid tool entries')
        names = [t['name'] for t in tools]
        if len(names) != len(set(names)):
            raise ValueError('duplicate tools')
        if result.get('nextCursor'):
            raise ValueError('schema coverage incomplete: pagination required')
        return {t['name']: t for t in tools}
    raise ValueError('missing matching JSON-RPC response')


class Regression(unittest.TestCase):
    def test_frontmatter_and_links(self):
        skill = (ROOT / 'SKILL.md').read_text()
        self.assertRegex(skill, r'\A---\nname: agent-mail-ops\n')
        self.assertIn('description:', skill.split('---', 2)[1])
        for target in re.findall(r'\]\(([^)]+)\)', skill):
            self.assertTrue((ROOT / target).is_file(), target)

    def test_failure_case_guidance(self):
        self.assertEqual(len(SCENARIOS), 18)
        self.assertEqual(len({s['id'] for s in SCENARIOS}), len(SCENARIOS))
        for scenario in SCENARIOS:
            with self.subTest(case=scenario['id']):
                text = (ROOT / scenario.get('file', 'SKILL.md')).read_text()
                self.assertTrue(scenario['expected'])
                for needle in scenario['needles']:
                    self.assertIn(needle, text)

    def test_json_and_sse_schema_decoding(self):
        response = {'jsonrpc': '2.0', 'id': 'skill-schema-audit',
                    'result': {'tools': [{'name': 'health_check'}]}}
        wire = json.dumps(response)
        self.assertIn('health_check', decode_tools(wire))
        self.assertIn('health_check', decode_tools('event: message\r\ndata: ' + wire + '\r\n\r\n'))

    def test_bad_and_incomplete_schema_is_not_pass(self):
        for payload in ('', '{', 'null', '{}',
                        '{"id":"other","result":{"tools":[{"name":"x"}]}}',
                        '{"id":"skill-schema-audit","error":{"code":-1}}',
                        '{"id":"skill-schema-audit","result":{"tools":[]}}',
                        '{"id":"skill-schema-audit","result":{"tools":[{"name":"x"}],"nextCursor":"more"}}',
                        '{"id":"skill-schema-audit","result":{"tools":[{"name":"x"},{"name":"x"}]}}'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    decode_tools(payload)


def live_checks():
    am = shutil.which('am')
    if not am:
        raise RuntimeError('am missing: live help checks NOT RUN')
    for argv in ([am, '--version'], [am, 'doctor', 'health', '--help'],
                 [am, 'doctor', 'drain', '--help'], [am, 'doctor', 'reclaim', '--help'],
                 [am, 'doctor', 'reconstruct', '--help'],
                 [am, 'file_reservations', 'active', '--help']):
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise RuntimeError('read-only CLI help check failed')
    # Schema discovery only. Never tools/call or a replacement transport for writes.
    request = urllib.request.Request('http://127.0.0.1:8765/mcp/',
        data=json.dumps({'jsonrpc': '2.0', 'id': 'skill-schema-audit', 'method': 'tools/list'}).encode(),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                 'User-Agent': 'agent-mail-ops-skill-tests'})
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError('schema response too large; coverage NOT RUN')
    tools = decode_tools(body.decode())
    required = {
        'macro_start_session': ['human_key', 'program', 'model'],
        'register_agent': ['project_key', 'program', 'model', 'name'],
        'file_reservation_paths': ['project_key', 'agent_name', 'paths', 'idempotency_key'],
        'check_file_reservation_conflicts': ['project_key', 'agent_name', 'paths'],
        'send_message': ['sender_name', 'sender_token', 'idempotency_key', 'to'],
        'reply_message': ['message_id', 'sender_name', 'idempotency_key'],
        'fetch_inbox': ['since_ts', 'mark_read', 'ack_overdue_only', 'include_bodies'],
        'fetch_inbox_events': ['after', 'position_now', 'limit'],
        'renew_file_reservations': ['file_reservation_ids', 'extend_seconds'],
        'release_file_reservations': ['file_reservation_ids'],
        'resolve_pane_identity': ['pane_id'],
        'acknowledge_message': ['message_id'], 'whois': ['agent_name'], 'health_check': [],
    }
    for name, fields in required.items():
        if name not in tools:
            raise ValueError(f'live schema lacks {name}')
        properties = tools[name].get('inputSchema', {}).get('properties', {})
        if any(field not in properties for field in fields):
            raise ValueError(f'live argument drift for {name}')
    print(f'PASS: live read-only schema checks for {len(required)} tools and 6 CLI probes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Regression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    if args.live:
        try:
            live_checks()
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, urllib.error.URLError) as exc:
            print(f'FAIL: live schema/help coverage failed ({type(exc).__name__}); not a pass')
            return 1
    else:
        print('NOT RUN: optional live schema/help checks (use --live)')
    print('PASS: 18 static scenario regressions; no live workflow mutations executed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
