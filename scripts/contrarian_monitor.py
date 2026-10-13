#!/usr/bin/env python3
"""
contrarian_monitor.py — Hourly monitor for contrarian shadow data.

Reads data/contrarian_shadow.jsonl, joins with actual trade outcomes,
and writes summary to data/contrarian_shadow_summary.json.

Runs via systemd timer (hermes-contrarian-monitor.timer).

Evaluation:
  - For each contrarian shadow event, check what the OPPOSITE direction
    would have done at the same entry price over the next 30 minutes.
  - Track contrarian WR per signal type.
  - Kill switch: n≥10 AND WR<45% → recommend disabling.
"""

import os
import sys
import json
import time
import sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, CANDLES_DB

SHADOW_FILE = os.path.join(HERMES_DATA, 'contrarian_shadow.jsonl')
SUMMARY_FILE = os.path.join(HERMES_DATA, 'contrarian_shadow_summary.json')


def evaluate_contrarian_outcome(token, contrarian_direction, entry_price, entry_ts):
    """Check what the contrarian trade would have done in next 30 minutes.
    Returns (pnl_pct, outcome) or (None, 'no_data')."""
    conn = None
    try:
        conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=5)
        cur = conn.cursor()
        # Get price 30min after entry
        cur.execute(
            "SELECT close FROM candles_1m WHERE token=? AND ts >= ? AND is_closed=1 ORDER BY ts LIMIT 1",
            (token.upper(), entry_ts + 1800)
        )
        row = cur.fetchone()
        if not row:
            return None, 'no_data'
        exit_price = row[0]
        if contrarian_direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100
        outcome = 'win' if pnl_pct > 0 else 'loss'
        return pnl_pct, outcome
    except Exception:
        return None, 'error'
    finally:
        if conn:
            conn.close()


def parse_ts(ts_str):
    """Parse ISO timestamp to epoch."""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.timestamp()
    except Exception:
        return None


def run_monitor():
    """Main monitor: evaluate all shadow events, write summary."""
    events = []
    try:
        with open(SHADOW_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
    except FileNotFoundError:
        print('[contrarian-monitor] No shadow file yet')
        return

    if not events:
        print('[contrarian-monitor] No events to evaluate')
        return

    # Evaluate each event
    by_signal = defaultdict(lambda: {'n': 0, 'wins': 0, 'total_pnl': 0.0, 'evaluated': 0, 'outcomes': []})
    now = time.time()

    for ev in events:
        sig = ev.get('signal', '?')
        token = ev.get('token', '?')
        contra_dir = ev.get('contrarian_direction')
        entry_price = ev.get('entry_price', 0)
        entry_ts = parse_ts(ev.get('ts', ''))

        if not contra_dir or not entry_price or not entry_ts:
            continue

        by_signal[sig]['n'] += 1

        # Only evaluate if 30min have passed
        if now - entry_ts < 1800:
            continue

        pnl_pct, outcome = evaluate_contrarian_outcome(token, contra_dir, entry_price, entry_ts)
        if pnl_pct is not None:
            by_signal[sig]['evaluated'] += 1
            by_signal[sig]['total_pnl'] += pnl_pct
            by_signal[sig]['outcomes'].append({'token': token, 'pnl_pct': round(pnl_pct, 2), 'outcome': outcome})
            if outcome == 'win':
                by_signal[sig]['wins'] += 1

    # Build summary
    summary = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'total_events': len(events),
        'by_signal': {},
        'recommendations': [],
    }

    for sig, data in by_signal.items():
        evaluated = data['evaluated']
        wins = data['wins']
        wr = (100 * wins / evaluated) if evaluated > 0 else 0
        total_pnl = data['total_pnl']

        rec = 'SOAK'
        if evaluated >= 10:
            if wr >= 55:
                rec = 'PROMOTE'
            elif wr < 45:
                rec = 'KILL'
            else:
                rec = 'HOLD'

        summary['by_signal'][sig] = {
            'total_events': data['n'],
            'evaluated': evaluated,
            'wins': wins,
            'wr': round(wr, 1),
            'total_pnl_pct': round(total_pnl, 2),
            'avg_pnl_pct': round(total_pnl / evaluated, 2) if evaluated > 0 else 0,
            'recommendation': rec,
            'recent_outcomes': data['outcomes'][-5:],  # last 5
        }

        if rec == 'KILL':
            summary['recommendations'].append(
                f"KILL: {sig} — contrarian WR {wr:.0f}% over {evaluated} trades. "
                f"Disable both signal and contrarian."
            )
        elif rec == 'PROMOTE':
            summary['recommendations'].append(
                f"PROMOTE: {sig} — contrarian WR {wr:.0f}% over {evaluated} trades. "
                f"Consider enabling live contrarian."
            )

    # Write summary
    try:
        with open(SUMMARY_FILE, 'w') as f:
            json.dump(summary, f, indent=2)
    except Exception as e:
        print(f'[contrarian-monitor] Write failed: {e}')

    # Print summary
    print(f'[contrarian-monitor] {len(events)} events, {sum(d["evaluated"] for d in by_signal.values())} evaluated')
    for sig, data in sorted(summary['by_signal'].items(), key=lambda x: x[1].get('wr', 0)):
        if data['evaluated'] > 0:
            print(f'  {sig:30s} {data["evaluated"]:3d}T  WR={data["wr"]:5.1f}%  '
                  f'PnL={data["total_pnl_pct"]:+.2f}%  {data["recommendation"]}')
    for rec in summary['recommendations']:
        print(f'  ⚠️  {rec}')


if __name__ == '__main__':
    run_monitor()
