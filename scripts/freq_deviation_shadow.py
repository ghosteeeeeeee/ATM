#!/usr/bin/env python3
"""
freq_deviation_shadow.py — trade-frequency deviation monitor (SHADOW, log-only).

Counts trades/hour per signal source in PostgreSQL brain `trades`, compares the
current window against a rolling baseline, and ALERTS when the current rate is
<0.5x or >2x the baseline. SHADOW = compute + log only: this script does NOT
import decider/signals/position_manager, does NOT write to any DB, and has
ZERO effect on the trading path (automatic-implementation Phase 1).

Output:
  - stdout lines prefixed [FREQ-SHADOW] (grep-able, journal via systemd timer)
  - appended rows to HERMES_DATA/freq_deviation_shadow.jsonl (alert events only)
  - alert line appended to automation/error_alerts.md (24h dedup per source)

FLIP BAR (pre-registered — never auto-flip):
  ENFORCE (as a size-cut/block gate) only when ALL of:
    (a) 14 days of shadow data collected, AND
    (b) >=30 alert events recorded, AND
    (c) alert-conditioned next-24h PnL of the alerted source is mean <0 over
        those >=30 events, AND
    (d) explicit CEO approval.
  Otherwise this stays log-only forever. No code path here can flip itself.

Usage:
    python3 scripts/freq_deviation_shadow.py
    python3 scripts/freq_deviation_shadow.py --baseline-days 14 --window-hours 24
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, 'scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT
from paths import HERMES_DATA

PREFIX = '[FREQ-SHADOW]'

# Floor + thresholds live HERE, not in hermes_constants.py (shadow-only monitor).
MIN_BASELINE_N = 10        # skip sources with fewer than N trades in lookback
UNDER_RATIO = 0.5          # alert if current < 0.5x baseline
OVER_RATIO = 2.0           # alert if current > 2x baseline
ALERT_DEDUP_HOURS = 24     # one error_alerts.md entry per source+direction / 24h

STATE_FILE = os.path.join(HERMES_DATA, 'freq_deviation_shadow.jsonl')
ERROR_ALERTS = '/root/.hermes/automation/error_alerts.md'


def log(msg):
    print(f'{PREFIX} {msg}', flush=True)


def fetch_trades(baseline_cut, window_cut):
    """Read-only fetch of open_time+signal for trades opened since baseline_cut.

    Returns (baseline_counts, current_counts) keyed by signal source string.
    """
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    try:
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT signal, open_time
                FROM trades
                WHERE server = 'Hermes'
                  AND open_time > %s
            """, (baseline_cut,))
            rows = cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()

    baseline = defaultdict(int)
    current = defaultdict(int)
    for signal, open_time in rows:
        if open_time is None:
            continue
        source = (signal or '').strip() or '(none)'
        # open_time may come back naive (DB tz) — normalize before comparing
        ot = open_time if open_time.tzinfo else open_time.replace(tzinfo=timezone.utc)
        baseline[source] += 1
        if ot > window_cut:
            current[source] += 1
    return baseline, current


def load_recent_alerts(hours):
    """Recent alert events from the JSONL state file (for 24h dedup). Returns list of dicts."""
    if not os.path.exists(STATE_FILE):
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    try:
        with open(STATE_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    ts = datetime.fromisoformat(ev['ts'])
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        recent.append(ev)
                except (ValueError, KeyError):
                    continue
    except OSError:
        return []
    return recent


def append_state(ev):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'a') as f:
        f.write(json.dumps(ev) + '\n')


def append_error_alert(source, direction, msg):
    """Follow auditor_verify.py convention: '## Error Alerts — <ts>' + bullet."""
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    try:
        with open(ERROR_ALERTS, 'a') as f:
            f.write(f'\n## Error Alerts — {ts}\n')
            f.write(f'- **[WARN]** (freq_deviation_shadow): `{source}`: {msg}\n')
        return True
    except OSError:
        return False


def evaluate(baseline, current, baseline_hours, window_hours, recent_alerts):
    """Compare rates per source; returns list of alert event dicts."""
    alerts = []
    checked = 0
    for source, n_base in sorted(baseline.items()):
        if n_base < MIN_BASELINE_N:
            continue  # too few baseline trades — tiny-count false-alert guard
        checked += 1
        n_cur = current.get(source, 0)
        base_rate = n_base / baseline_hours
        cur_rate = n_cur / window_hours
        # base_rate > 0 guaranteed by MIN_BASELINE_N >= 1 and hours > 0
        ratio = cur_rate / base_rate
        if ratio < UNDER_RATIO:
            direction = 'under'
        elif ratio > OVER_RATIO:
            direction = 'over'
        else:
            log(f'OK source={source} baseline={base_rate:.3f}/h current={cur_rate:.3f}/h '
                f'ratio={ratio:.2f} n_base={n_base} n_cur={n_cur}')
            continue

        msg = (f'FREQ DEVIATION {direction.upper()} source={source} '
               f'baseline={base_rate:.3f}/h current={cur_rate:.3f}/h '
               f'ratio={ratio:.2f} n_base={n_base} n_cur={n_cur}')
        log(f'ALERT {msg}')

        ev = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'source': source,
            'baseline_rate': round(base_rate, 4),
            'current_rate': round(cur_rate, 4),
            'ratio': round(ratio, 4),
            'direction': direction,
            'n_baseline': n_base,
            'n_current': n_cur,
        }
        append_state(ev)

        # error_alerts.md: only if no same-source+direction alert in last 24h
        dedup = any(a.get('source') == source and a.get('direction') == direction
                    for a in recent_alerts)
        if not dedup:
            wrote = append_error_alert(source, direction, msg)
            log(f'error_alerts.md {"appended" if wrote else "write FAILED"} '
                f'(source={source} dir={direction})')
        alerts.append(ev)

    log(f'checked {checked} source(s) (baseline n>={MIN_BASELINE_N}), '
        f'{len(alerts)} alert(s)')
    return alerts


def main():
    p = argparse.ArgumentParser(description='Trade-frequency deviation shadow monitor')
    p.add_argument('--baseline-days', type=int, default=14,
                   help='rolling baseline lookback in days (default 14)')
    p.add_argument('--window-hours', type=int, default=24,
                   help='current window in hours (default 24)')
    args = p.parse_args()

    now = datetime.now(timezone.utc)
    baseline_cut = now - timedelta(days=args.baseline_days)
    window_cut = now - timedelta(hours=args.window_hours)
    baseline_hours = args.baseline_days * 24
    window_hours = args.window_hours

    baseline, current = fetch_trades(baseline_cut, window_cut)
    log(f'baseline={args.baseline_days}d window={args.window_hours}h '
        f'trades_in_lookback={sum(baseline.values())} '
        f'trades_in_window={sum(current.values())}')

    recent_alerts = load_recent_alerts(ALERT_DEDUP_HOURS)
    evaluate(baseline, current, baseline_hours, window_hours, recent_alerts)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # fail-open: never crash the timer run
        print(f'{PREFIX} ERROR {type(e).__name__}: {e}', flush=True)
        sys.exit(0)
