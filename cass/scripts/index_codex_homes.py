#!/usr/bin/env python3
"""Incrementally index default and isolated Codex homes. Preview unless --apply."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def homes(base):
    candidates = [base / '.codex', *sorted((base / '.codex-instances').glob('*'))]
    return [p for p in candidates if p.is_dir() and (p / 'sessions').is_dir()]


def fingerprint(path):
    stat = path.stat()
    return [stat.st_size, stat.st_mtime_ns]


def pending(home, cached):
    return [p for p in sorted((home / 'sessions').rglob('rollout-*.jsonl'))
            if cached.get(str(p)) != fingerprint(p)]


def command(binary, data, paths):
    return [binary, '--db', str(data / 'agent_search.db'), 'index', '--data-dir', str(data),
            '--json', '--no-progress-events', '--watch-once', *map(str, paths)]


def verified_batch(result, count):
    stats = result.get('indexing_stats', {})
    codex = stats.get('connector_summary', {}).get('codex', {})
    return (result.get('success') is True and result.get('full') is False
            and stats.get('scan_had_errors') is False
            and result.get('lexical_update_deferred') is False
            and result.get('quarantined_conversations') == 0
            and stats.get('deferred_active_sources') == 0
            and codex.get('partially_indexed', 0) == 0
            and codex.get('indexed', 0) >= count)


def active_deferral_only(result):
    if not isinstance(result, dict):
        return False
    stats = result.get('indexing_stats', {})
    return (result.get('success') is True and stats.get('deferred_active_sources', 0) > 0
            and stats.get('scan_had_errors') is False
            and result.get('quarantined_conversations') == 0
            and result.get('lexical_update_deferred') is False)


def archive_paths(binary, data):
    # Timeline is provider-scoped and avoids sessions' expensive per-row archive counts.
    proc = subprocess.run([binary, '--db', str(data / 'agent_search.db'), 'timeline',
                           '--data-dir', str(data), '--agent', 'codex', '--since', '2000-01-01',
                           '--group-by', 'none', '--json'],
                          capture_output=True, text=True, timeout=60, check=False)
    if proc.returncode != 0:
        raise RuntimeError('cannot verify session coverage')
    result = json.loads(proc.stdout)
    rows = result['sessions']
    if result.get('total_sessions') != len(rows):
        raise ValueError('session enumeration incomplete')
    return {row['source_path'] for row in rows if row.get('agent') == 'codex'}


def index_batch(binary, data, batch, env):
    for attempt in range(7):
        proc = subprocess.run(command(binary, data, batch), env=env,
                              capture_output=True, text=True, timeout=900, check=False)
        try:
            result = json.loads(proc.stdout)
        except ValueError:
            # Preserve the raw response in the caller's artifact files, never cache it.
            return proc, {'success': False, 'kind': 'invalid-json'}
        if not isinstance(result, dict) or result.get('kind') != 'index-busy' or attempt == 6:
            return proc, result
        # Explicit index-busy is a refused run, so retrying cannot duplicate a write.
        time.sleep(5)


def save_checkpoint(path, archive, files):
    # Only our derived progress cache is replaced, never source logs or archive files.
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='checkpoint-',
                                     suffix='.json', delete=False) as output:
        json.dump({'archive': str(archive), 'files': files}, output)
        output.flush()
        os.fsync(output.fileno())
        temporary = output.name
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--base-home', type=Path, default=Path.home())
    parser.add_argument('--data-dir', type=Path,
                        default=Path.home() / '.local/share/coding-agent-search')
    parser.add_argument('--state-dir', type=Path,
                        default=Path.home() / '.local/state/cass-codex-homes')
    args = parser.parse_args()
    data = args.data_dir.resolve()
    checkpoint = args.state_dir / 'checkpoint.json'
    cached = {}
    if checkpoint.exists():
        saved = json.loads(checkpoint.read_text())
        if saved.get('archive') != str(data) or not isinstance(saved.get('files'), dict):
            raise ValueError('checkpoint belongs to another archive or has invalid format')
        cached = saved['files']
    roots = homes(args.base_home)
    summary = {'homes': len(roots), 'pending_files': sum(len(pending(p, cached)) for p in roots),
               'completed_files': 0, 'deferred_or_failed_files': 0, 'apply': args.apply}
    if not args.apply:
        print(json.dumps(summary))
        return 0
    binary = shutil.which('cass')
    if not binary:
        raise RuntimeError('cass not installed; no indexing performed')
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (args.state_dir / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Read the cache again under the lock so simultaneous starts cannot lose progress.
        if checkpoint.exists():
            saved = json.loads(checkpoint.read_text())
            if saved.get('archive') != str(data) or not isinstance(saved.get('files'), dict):
                raise ValueError('invalid checkpoint archive/format')
            cached = saved['files']
        run = Path(tempfile.mkdtemp(prefix='run-', dir=args.state_dir))
        summary['artifact_dir'] = str(run)
        known = archive_paths(binary, data)
        # A restored/repaired archive may no longer contain previously cached paths.
        cached = {path: value for path, value in cached.items() if path in known}
        failures = 0
        sequence = 0
        for home in roots:
            paths = pending(home, cached)
            batch_size = 32 if all(str(p) in known for p in paths) else 8
            for offset in range(0, len(paths), batch_size):
                batch = paths[offset:offset + batch_size]
                before = {str(p): fingerprint(p) for p in batch}
                env = dict(os.environ, CODEX_HOME=str(home))
                env.pop('CASS_DB_PATH', None)
                env.pop('CASS_DATA_DIR', None)
                sequence += 1
                try:
                    proc, result = index_batch(binary, data, batch, env)
                    (run / f'{sequence}.json').write_text(proc.stdout)
                    (run / f'{sequence}.stderr').write_text(proc.stderr)
                    clean = proc.returncode == 0 and isinstance(result, dict) and verified_batch(result, 0)
                    # Zero additions can mean an unchanged archived source, not a failure.
                    # Unknown paths must actually appear in the archive before checkpointing.
                    if clean and any(str(p) not in known for p in batch):
                        known = archive_paths(binary, data)
                    ok = clean and all(str(p) in known for p in batch)
                    if ok:
                        for p in batch:
                            if fingerprint(p) == before[str(p)]:
                                cached[str(p)] = before[str(p)]
                                summary['completed_files'] += 1
                            else:
                                summary['deferred_or_failed_files'] += 1
                        save_checkpoint(checkpoint, data, cached)
                    else:
                        summary['deferred_or_failed_files'] += len(batch)
                        # Active-writer deferral is expected; actual errors make the job fail.
                        if proc.returncode != 0 or not active_deferral_only(result):
                            failures += 1
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    summary['deferred_or_failed_files'] += len(batch)
                    failures += 1
                print(json.dumps({'home': str(home), 'batch': len(batch),
                                  'completed_files': summary['completed_files'],
                                  'deferred_or_failed_files': summary['deferred_or_failed_files']}), flush=True)
        summary['failures'] = failures
        (run / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary), flush=True)
        return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
