#!/usr/bin/env python3
"""locked_test_split.py — define train/OOS split, mark OOS window consumed.

Usage:
  python3 scripts/locked_test_split.py                  # OOS = last 14 days
  python3 scripts/locked_test_split.py --oos-days 30
  python3 scripts/locked_test_split.py --train-end 2026-10-01
  python3 scripts/locked_test_split.py --reset          # clear consumed state

Marks HERMES_DATA/locked_test_state.json so a second look at the same
OOS window is detectable (exactly-once rule, brain/SOPs.md).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from paths import *
import psycopg2
from _secrets import BRAIN_DB_DICT

STATE_FILE = os.path.join(HERMES_DATA, 'locked_test_state.json')


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_state(state):
    os.makedirs(HERMES_DATA, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def query_counts(train_end_str, oos_end_str):
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    try:
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT COUNT(*), MIN(open_time), MAX(open_time)
                FROM trades WHERE open_time < %s
            """, (train_end_str,))
            n_train, train_min, train_max = cur.fetchone()
            cur.execute("""
                SELECT COUNT(*), MIN(open_time), MAX(open_time)
                FROM trades WHERE open_time >= %s AND open_time <= %s
            """, (train_end_str, oos_end_str,))
            n_oos, oos_min, oos_max = cur.fetchone()
        finally:
            cur.close()
    finally:
        conn.close()
    return n_train, train_min, train_max, n_oos, oos_min, oos_max


def main():
    p = argparse.ArgumentParser(description='Locked train/OOS split (SOPs.md Locked Test Protocol)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--train-end', metavar='YYYY-MM-DD', help='OOS starts the day after this date')
    g.add_argument('--oos-days', type=int, default=14, help='OOS = last N days (default 14)')
    p.add_argument('--reset', action='store_true', help='clear consumed OOS state (explicit required)')
    args = p.parse_args()

    if args.reset:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print(f'RESET: cleared consumed state {STATE_FILE}')
        else:
            print(f'RESET: no state file at {STATE_FILE} (nothing to clear)')
        return 0

    state = load_state()
    if state:
        print('OOS WINDOW ALREADY CONSUMED — second look detectable, refusing to re-print split.')
        print(json.dumps(state, indent=2))
        print('A new tune requires a NEW OOS window (new date boundary). '
              'Use --reset only to acknowledge/revert, per SOPs.md Locked Test Protocol.')
        return 1

    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, matches trades.open_time
    if args.train_end:
        # train = open_time < train_end 00:00 (ends end of previous day); OOS = [train_end, now]
        train_end = datetime.strptime(args.train_end, '%Y-%m-%d')
        oos_start_str = args.train_end
    else:
        train_end = now - timedelta(days=args.oos_days)
        oos_start_str = train_end.strftime('%Y-%m-%d')
    oos_end_str = now.strftime('%Y-%m-%d') + ' 23:59:59'
    train_end_str = train_end.strftime('%Y-%m-%d %H:%M:%S')

    n_train, train_min, train_max, n_oos, oos_min, oos_max = query_counts(train_end_str, oos_end_str)

    print('=== Locked Test Split (brain/SOPs.md Locked Test Protocol) ===')
    print(f'TRAIN window: {train_min or "(no trades)"}  ->  {train_end_str} (exclusive)')
    print(f'  train trades: {n_train}')
    print(f'OOS   window: {oos_start_str}  ->  {oos_end_str}   ** LOOK EXACTLY ONCE **')
    print(f'  oos trades:   {n_oos}')
    if n_oos == 0:
        print('WARNING: OOS window has 0 trades — pick a longer --oos-days before tuning.')

    state = {
        'oos_start': oos_start_str,
        'oos_end': oos_end_str,
        'train_end': train_end_str,
        'train_trades': n_train,
        'oos_trades': n_oos,
        'consumed_at': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'method': f'--train-end {args.train_end}' if args.train_end else f'--oos-days {args.oos_days}',
    }
    save_state(state)
    print(f'CONSUMED: OOS window marked in {STATE_FILE}')
    print('Record tune + OOS verdict in commit message and automation/recent_changes.log.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
