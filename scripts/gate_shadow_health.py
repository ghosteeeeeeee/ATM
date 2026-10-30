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
# Reuse gate_shadow's exact block-line patterns (BLOCK_RE + CONF_RE) so this
# check can never drift from what the recorder actually captures.
from gate_shadow import BLOCK_RE, CONF_RE

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
    """Scan pipeline.log tail for gate-block lines in the window.

    Returns (raw_line_count, dedup_key_set, tail_covers_window) —
    tail_covers_window is False when TAIL_BYTES didn't reach back to the
    cutoff (then log counts are underestimates; ratio would be inflated, so
    the caller must not WARN on ratio alone).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    raw = 0
    keys = set()
    covers = False
    if not os.path.exists(PIPELINE_LOG):
        return 0, keys, True
    with open(PIPELINE_LOG, 'rb') as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - TAIL_BYTES))
        first_ts = None
        for bline in f:
            line = bline.decode('utf-8', errors='replace')
            if first_ts is None:
                tm = TS_RE.match(line)
                if tm:
                    try:
                        first_ts = datetime.fromisoformat(tm.group(1) + '+00:00')
                    except ValueError:
                        first_ts = False
            parsed = _parse_gate_line(line)
            if not parsed:
                continue
            b_dt, key = parsed
            if b_dt < cutoff:
                continue
            raw += 1
            keys.add(key)
        covers = (first_ts is not False and first_ts is not None
                  and first_ts <= cutoff) or size < TAIL_BYTES
    return raw, keys, covers


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
    args = ap.parse_args()
    # --dry: neuter the alert writer by pretending an alert just fired
    if args.dry:
        globals()['_append_alert'] = lambda msg: (log(f'[DRY] would alert: {msg}'), False)[1]
    r = check()
    log(f'{r["status"].upper()} — {r["message"]}')
    return 1 if r['status'] == 'warning' else 0


if __name__ == '__main__':
    sys.exit(main())
