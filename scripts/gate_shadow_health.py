#!/usr/bin/env python3
"""gate_shadow_health.py — D4b capture-rate observability (CEO 2026-10-30).

gate_shadow.py has failed silently twice: the Oct-10 rotation bug (consumer
guard since fixed) and a pre-2026-10-22 regex blind spot that cut capture to
33-43% for the highest-volume gates for DAYS with zero alarm. This check
compares brain/gate_shadow.db rows against pipeline.log gate-block lines over
the trailing 24h and WARNs when the recorder is missing events.

Ground truth applies gate_shadow's own dedup (10-min gate|token|direction
bucket), so the ratio is apples-to-apples with what --record stores.
Patterns are imported from gate_shadow.py (single source — do not duplicate).

WARN conditions:
  1. capture ratio (db rows / log dedup keys) < CAPTURE_RATIO_MIN (0.90)
  2. recorder wrote 0 rows in STALE_HOURS while pipeline.log has gate lines

Read-only w.r.t. both DBs (SELECT only). Standalone:
  python3 scripts/gate_shadow_health.py [--dry]
  python3 scripts/gate_shadow_health.py --per-gate   # per-gate bar read
  python3 scripts/gate_shadow_health.py --selfcheck  # dedup-frame invariants
Prints ratio + OK/WARN; exits 1 on WARN. Also invoked from
pipeline_watchdog.py (2-min timer) via check(), which appends to
automation/error_alerts.md (6h-deduped) on WARN.
"""
import sys
import os
import re
import time
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, HERMES_LOG_DIR
# Reuse gate_shadow's exact block-line patterns (BLOCK_RE + CONF_RE + RR_BLOCK_RE)
# and its rotated-log discovery (archive_paths + open_log_text) so this check can
# never drift from what the recorder actually captures, nor from the rotation
# that moves history into logs/archive/*.gz.
from gate_shadow import (BLOCK_RE, CONF_RE, RR_BLOCK_RE,
                         archive_paths, open_log_text)

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'gate_shadow.db')
PIPELINE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
ALERT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'automation', 'error_alerts.md')
ALERT_TS_FILE = os.path.join(HERMES_DATA, 'gate_shadow_health_alert_ts.txt')

CAPTURE_RATIO_MIN = 0.90   # db/log capture ratio floor over trailing 24h
STALE_HOURS = 6            # 0 db rows in this window + log lines => recorder dead
ALERT_DEDUP_HOURS = 6      # don't re-append the same WARN to error_alerts.md
TAIL_BYTES = 50_000_000    # ~2x daily pipeline.log growth (~23MB/day measured
                           # 2026-10-10..30) — covers a full trailing 24h

TS_RE = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [gate_shadow_health] {msg}', flush=True)


def _parse_gate_line(line):
    """Same match order + 10-min dedup bucket as gate_shadow.record()."""
    m = BLOCK_RE.search(line)
    if m:
        gate, token, direction = m.group(1), m.group(2).upper(), m.group(3).upper()
    else:
        # must mirror gate_shadow.record()'s order exactly, or the db<=dedup
        # selfcheck below would frame RR-ENGINE rows as unexplained extras.
        mr = RR_BLOCK_RE.search(line)
        if mr:
            gate, token, direction = 'RR-ENGINE', mr.group(1).upper(), mr.group(2).upper()
        else:
            mc = CONF_RE.search(line)
            if not mc:
                return None
            gate, token, direction = 'CONFLUENCE-GATE-BLOCK', mc.group(1).upper(), mc.group(2).upper()
    ts_m = TS_RE.match(line)
    if not ts_m:
        return None
    try:
        b_dt = datetime.fromisoformat(ts_m.group(1) + '+00:00')
    except ValueError:
        return None
    bucket = b_dt.strftime('%Y%m%d%H%M')[:-1]  # 10-min bucket (gate_shadow style)
    return b_dt, f'{gate}|{token}|{direction}|{bucket}'


def count_log_gate_lines(window_hours):
    """Scan pipeline.log (and its rotated archives) for gate-block lines in the window.

    Returns (raw_line_count, dedup_key_set, window_covers) — window_covers is
    False when no source reaches back to the cutoff (then log counts are
    underestimates; ratio would be inflated, so the caller must not WARN on
    ratio alone).

    ROTATION-AWARE (code-review M2 + H1): log_rotate_pipeline renames the live
    log daily (~00:10) into logs/archive/pipeline.log.<ts>.gz, so right after
    the rename the live file holds only a couple of hours. Reading it alone
    collapsed log-dedup while gate_shadow.db still held 24h of rows ->
    `db > log-dedup` and --selfcheck ASSERTED (observed 2026-11-07 02:17).
    The live tail is still read first and still TAIL_BYTES-limited so the
    2-minute watchdog stays cheap; archives are only opened when the live tail
    does NOT reach back to the cutoff — i.e. only in the post-rotation window,
    when they are the sole source of the older lines.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    raw = 0
    keys = set()
    # True once ANY scanned line is at/before the cutoff — under the log's
    # chronological ordering that proves the scanned region reaches the window
    # start, which is exactly what the old `first_ts <= cutoff` test asserted.
    reached = False

    def _consume(lines):
        nonlocal raw, reached
        for line in lines:
            if not reached:
                tm = TS_RE.match(line)
                if tm:
                    try:
                        ts = datetime.fromisoformat(tm.group(1) + '+00:00')
                    except ValueError:
                        ts = None
                    if ts is not None and ts <= cutoff:
                        reached = True
            parsed = _parse_gate_line(line)
            if not parsed:
                continue
            b_dt, key = parsed
            if b_dt < cutoff:
                continue
            raw += 1
            keys.add(key)

    # 1) live log, tail-limited (unchanged cost profile)
    if os.path.exists(PIPELINE_LOG):
        with open(PIPELINE_LOG, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            _consume(b.decode('utf-8', errors='replace') for b in f)

    # 2) rotated archives only when the live tail cannot prove coverage
    if not reached:
        for path in archive_paths(PIPELINE_LOG, since=cutoff):
            try:
                with open_log_text(path) as f:
                    _consume(f)
            except (OSError, EOFError) as e:
                log(f'skipping unreadable {path}: {e}')
                continue

    if not os.path.exists(PIPELINE_LOG) and not archive_paths(PIPELINE_LOG):
        return 0, keys, True
    return raw, keys, reached


def count_db_events(window_hours):
    """gate_shadow events with blocked_at in window (blocked_at is the log-line
    timestamp; the events table has no created_at — blocked_at is the correct
    window key). String compare works: stored as 'YYYY-MM-DD HH:MM:SS+00:00'."""
    if not os.path.exists(SHADOW_DB):
        return None
    cutoff_s = (datetime.now(timezone.utc) - timedelta(hours=window_hours)
                ).strftime('%Y-%m-%d %H:%M:%S') + '+00:00'
    conn = sqlite3.connect(SHADOW_DB, timeout=10)
    try:
        return conn.execute(
            'SELECT COUNT(*) FROM events WHERE blocked_at >= ?',
            (cutoff_s,)).fetchone()[0]
    finally:
        conn.close()


def check():
    """Core check — returns {'status': 'ok'|'warning', 'message': ...}.
    Called standalone (main) and from pipeline_watchdog.check_gate_shadow_capture.
    Appends to error_alerts.md on WARN (6h-deduped) — that side effect is
    idempotent enough for the 2-min watchdog cadence."""
    raw24, keys24, covers = count_log_gate_lines(24)
    db24 = count_db_events(24)
    if db24 is None:
        return {'status': 'warning', 'message': f'gate_shadow.db missing: {SHADOW_DB}'}

    msgs = []
    ratio = None
    if keys24:
        ratio = min(1.0, db24 / len(keys24))
        if covers and ratio < CAPTURE_RATIO_MIN:
            msgs.append(
                f'capture ratio {ratio:.2f} < {CAPTURE_RATIO_MIN} '
                f'(db={db24} vs log-dedup={len(keys24)} over 24h)')
        elif not covers:
            msgs.append(f'note: log tail <24h coverage, ratio not conclusive '
                        f'(db={db24}, log-dedup={len(keys24)}, raw={raw24})')

    # recorder-stalled check: 0 db rows in STALE_HOURS while log has gate lines
    raw6, keys6, _ = count_log_gate_lines(STALE_HOURS)
    db6 = count_db_events(STALE_HOURS)
    if keys6 and db6 == 0:
        msgs.append(f'recorder wrote 0 rows in {STALE_HOURS}h while '
                    f'pipeline.log has {raw6} gate lines')

    ratio_s = f'{ratio:.2f}' if ratio is not None else 'n/a'
    if msgs:
        msg = f'24h capture ratio={ratio_s} (db={db24}, log-dedup={len(keys24)}); ' \
              + '; '.join(msgs)
        _append_alert(msg)
        return {'status': 'warning', 'message': msg}
    return {'status': 'ok',
            'message': f'24h capture ratio={ratio_s} (db={db24}, '
                       f'log-dedup={len(keys24)}, raw={raw24})'}


def per_gate(window_hours=24, min_n=10):
    """Per-gate capture ratio in the recorder's OWN dedup frame.

    ponytail: the disposition bar is "per-gate >=90%", but only the overall
    ratio was ever printed — so auditors hand-rolled db/raw-line ratios and
    reported the designed 10-min dedup (raw 13k -> dedup 2.4k) as a 15-30%
    "capture gap" for 3 runs (#225/#227). Raw lines are NOT the denominator:
    the recorder INSERTs with a UNIQUE gate|token|direction|bucket key, so
    db/raw can never exceed ~0.3 by construction. This prints the number the
    bar actually asks for. Rows with dedup < min_n are marked (small-n) and
    do not fail the bar.
    Returns (rows, covers); each row is (gate, log_dedup, db, ratio, flagged).
    """
    _raw, keys, covers = count_log_gate_lines(window_hours)
    from collections import Counter
    log_by_gate = Counter(k.split('|')[0] for k in keys)
    cutoff_s = (datetime.now(timezone.utc) - timedelta(hours=window_hours)
                ).strftime('%Y-%m-%d %H:%M:%S') + '+00:00'
    conn = sqlite3.connect(SHADOW_DB, timeout=10)
    try:
        db_by_gate = dict(conn.execute(
            'SELECT gate, COUNT(*) FROM events WHERE blocked_at >= ? GROUP BY gate',
            (cutoff_s,)).fetchall())
    finally:
        conn.close()
    out = []
    for g in sorted(set(log_by_gate) | set(db_by_gate),
                    key=lambda x: -log_by_gate.get(x, 0)):
        lg, db = log_by_gate.get(g, 0), db_by_gate.get(g, 0)
        ratio = min(1.0, db / lg) if lg else (1.0 if db else 0.0)
        out.append((g, lg, db, ratio, lg < min_n or ratio < CAPTURE_RATIO_MIN))
    return out, covers


def _append_alert(msg):
    """Anomaly-only append to automation/error_alerts.md (same pattern as
    health_monitor.append_alerts), 6h-deduped via ALERT_TS_FILE so the 2-min
    watchdog cadence cannot flood the file."""
    try:
        if os.path.exists(ALERT_TS_FILE):
            with open(ALERT_TS_FILE) as f:
                last = float(f.read().strip() or 0)
            if time.time() - last < ALERT_DEDUP_HOURS * 3600:
                return False
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
        with open(ALERT_LOG, 'a') as f:
            f.write(f'\n## Error Alerts — {ts}\n'
                    f'- **[WARN]** (gate_shadow_health): {msg}\n')
        tmp = ALERT_TS_FILE + '.tmp'
        with open(tmp, 'w') as f:
            f.write(str(time.time()))
        os.replace(tmp, ALERT_TS_FILE)
        return True
    except Exception as e:
        log(f'alert append failed: {e}')
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true',
                    help='report only — do not write error_alerts.md')
    ap.add_argument('--per-gate', action='store_true',
                    help='print per-gate capture in the recorder dedup frame '
                         '(the denominator the per-gate >=90% bar asks for)')
    ap.add_argument('--selfcheck', action='store_true',
                    help='assert dedup-frame invariants; exit 1 on violation')
    args = ap.parse_args()
    if args.selfcheck:
        rows, covers = per_gate(24)
        assert covers, 'log tail does not cover 24h — ratios not conclusive'
        # recorder dedup contract: db can never exceed distinct log keys
        over = [(g, lg, db) for g, lg, db, _r, _f in rows if db > lg]
        assert not over, f'db > log-dedup (frame broken): {over[:5]}'
        log(f'selfcheck PASS — {len(rows)} gates, '
            f'{len([1 for *_x, f in rows if f])} flagged, covers={covers}')
        return 0
    if args.per_gate:
        rows, covers = per_gate(24)
        log(f'per-gate capture (dedup frame, covers={covers}) — '
            f'bar >= {CAPTURE_RATIO_MIN:.2f} for every gate with n>=10')
        for g, lg, db, r, f in rows:
            mark = '  <-- FLAG' if (f and lg >= 10) else ('  (small-n)' if lg < 10 else '')
            log(f'  {g:34} dedup={lg:5} db={db:5} ratio={r:.2f}{mark}')
        return 1 if any(f and lg >= 10 for _g, lg, _db, _r, f in rows) else 0
    # --dry: neuter the alert writer by pretending an alert just fired
    if args.dry:
        globals()['_append_alert'] = lambda msg: (log(f'[DRY] would alert: {msg}'), False)[1]
    r = check()
    log(f'{r["status"].upper()} — {r["message"]}')
    return 1 if r['status'] == 'warning' else 0


if __name__ == '__main__':
    sys.exit(main())
