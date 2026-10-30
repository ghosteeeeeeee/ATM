#!/usr/bin/env python3
"""log_rotate_pipeline.py — D4a durable pipeline.log retention (CEO 2026-10-30).

pipeline.log grew to 455MB with NO rotator anywhere (no logrotate.d, no cron,
no systemd timer). Archives were deleted once already, permanently losing the
Oct 4-10 window and blocking external audit. This renames the live file into
logs/archive/pipeline.log.YYYYMMDDHHMMSS.gz when it exceeds MAX_SIZE_BYTES and
prunes archives older than RETENTION_DAYS.

Safe while the pipeline appends (standard pattern here): appenders re-open the
path each run (run_pipeline.py opens per step; liquidation-map is oneshot), so
rename-based rotation is correct. Before renaming, gate_shadow --record is
flushed (best-effort, timeout) so no gate-block line is lost from
brain/gate_shadow.db at the rotation boundary — gate_shadow.py's own
offset>size guard then resets on the fresh file.

Timer: pipeline-log-rotate.timer (daily, RandomizedDelaySec) — systemd, never
cron (repo rule).

Usage:
  python3 scripts/log_rotate_pipeline.py            # rotate if oversized + prune
  python3 scripts/log_rotate_pipeline.py --selftest # synthetic-dir self-test
"""
import sys
import os
import time
import gzip
import shutil
import argparse
import subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_LOG_DIR

MAX_SIZE_BYTES = 200 * 1024 * 1024   # rotate when pipeline.log exceeds this
RETENTION_DAYS = 30                  # delete archives older than this
FLUSH_TIMEOUT_SEC = 120              # gate_shadow --record flush budget

PIPELINE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
ARCHIVE_DIR = os.path.join(HERMES_LOG_DIR, 'archive')
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [log_rotate] {msg}', flush=True)


def _flush_gate_shadow():
    """Best-effort: record trailing gate blocks into gate_shadow.db BEFORE the
    rename, so the offset lands at old-file-end and nothing is lost from the
    shadow DB at the rotation boundary. Failure never blocks rotation."""
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, 'gate_shadow.py'),
             '--record', '--since-hours', '6'],
            timeout=FLUSH_TIMEOUT_SEC, capture_output=True, text=True)
        if r.returncode == 0:
            log('flushed gate_shadow --record before rotate')
        else:
            log(f'gate_shadow flush rc={r.returncode} (continuing): {r.stderr[-200:]}')
    except Exception as e:
        log(f'gate_shadow flush failed (continuing): {e}')


def rotate(log_path=PIPELINE_LOG, archive_dir=ARCHIVE_DIR,
           max_size=MAX_SIZE_BYTES, flush_recorder=True):
    """Rename-rotate log_path into archive_dir and gzip. Recreates an empty
    log_path so appenders always find the file. Returns True if rotated."""
    if not os.path.exists(log_path):
        log(f'{log_path} missing — nothing to rotate')
        return False
    size = os.path.getsize(log_path)
    if size < max_size:
        log(f'{os.path.basename(log_path)} {size/1e6:.1f}MB < '
            f'{max_size/1e6:.0f}MB threshold — no rotation')
        return False
    if flush_recorder:
        _flush_gate_shadow()
    os.makedirs(archive_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    dest = os.path.join(archive_dir, f'{os.path.basename(log_path)}.{ts}')
    os.rename(log_path, dest)          # atomic; open writers keep the old fd
    open(log_path, 'a').close()        # recreate so appenders/recorder find it
    with open(dest, 'rb') as f_in, gzip.open(dest + '.gz', 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    gz_size = os.path.getsize(dest + '.gz')
    os.unlink(dest)
    log(f'rotated {size/1e6:.1f}MB -> {os.path.basename(dest)}.gz '
        f'({gz_size/1e6:.1f}MB gzip)')
    return True


def prune(archive_dir=ARCHIVE_DIR, retention_days=RETENTION_DAYS):
    """Delete archives (pipeline.log.* and *.gz) older than retention_days."""
    if not os.path.isdir(archive_dir):
        return 0
    cutoff = time.time() - retention_days * 86400
    removed = 0
    for name in os.listdir(archive_dir):
        if not name.startswith('pipeline.log.'):
            continue
        path = os.path.join(archive_dir, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.unlink(path)
                removed += 1
        except OSError:
            continue
    if removed:
        log(f'pruned {removed} archives older than {retention_days}d')
    return removed


def selftest():
    """Synthetic-dir self-test under logs/_selftest/ — never touches the real
    pipeline.log. Checks: rotate fires over threshold, archive is valid gzip
    with original content, original recreated empty, prune removes old files."""
    base = os.path.join(HERMES_LOG_DIR, '_selftest')
    arch = os.path.join(base, 'archive')
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(arch)
    logp = os.path.join(base, 'pipeline.log')
    payload = ('2026-10-30 20:00:00 selftest line\n' * 100).encode()
    with open(logp, 'wb') as f:
        f.write(payload)
    try:
        # under threshold: no rotation
        assert rotate(logp, arch, max_size=len(payload) + 1,
                      flush_recorder=False) is False, 'rotate fired under threshold'
        # over threshold: rotates
        assert rotate(logp, arch, max_size=len(payload) - 1,
                      flush_recorder=False) is True, 'rotate did not fire'
        archives = os.listdir(arch)
        assert len(archives) == 1 and archives[0].endswith('.gz'), \
            f'expected 1 .gz archive, got {archives}'
        with gzip.open(os.path.join(arch, archives[0]), 'rb') as f:
            assert f.read() == payload, 'archive gzip content mismatch'
        assert os.path.exists(logp) and os.path.getsize(logp) == 0, \
            'original not recreated empty'
        # prune: 40d-old archive removed, fresh kept
        old = os.path.join(arch, 'pipeline.log.20260901000000.gz')
        with gzip.open(old, 'wb') as f:
            f.write(b'old')
        os.utime(old, (time.time() - 40 * 86400,) * 2)
        assert prune(arch, retention_days=30) == 1, 'prune did not remove old archive'
        assert os.listdir(arch) == [archives[0]], 'prune removed wrong file'
        print('PASS: under-threshold skip')
        print('PASS: rotation + gzip archive content valid')
        print('PASS: original recreated empty')
        print('PASS: prune removed >30d archive, kept fresh')
        print('SELFTEST PASS')
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true',
                    help='run synthetic self-test under logs/_selftest/ and exit')
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    prune()
    rotate()
    return 0


if __name__ == '__main__':
    sys.exit(main())
