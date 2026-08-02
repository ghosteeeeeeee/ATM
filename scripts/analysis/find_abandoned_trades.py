#!/usr/bin/env python3
"""Identify the abandoned/10-second trade class.

Heuristics (any one of):
  - duration < 10s
  - duration < 30s and abs(pnl_usdt) < 0.05 (truncated stop, no real PnL movement)

Pull all candidates from the last N days and characterize.
"""
from __future__ import annotations

import argparse
import os
import sys
import psycopg2
import psycopg2.extras
from collections import Counter, defaultdict


def fetch(window_days: int) -> list[dict]:
    """Fetch closed trades from PostgreSQL with duration computed."""
    pg = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id, token, direction, entry_price, exit_price, leverage,
               amount_usdt, pnl_usdt, pnl_pct, signal_reason,
               EXTRACT(EPOCH FROM (close_time - open_time)) AS duration_sec,
               open_time, close_time, exit_reason, signal, status
        FROM trades
        WHERE status = 'closed'
          AND close_time > NOW() - INTERVAL '%s days'
          AND open_time IS NOT NULL
          AND close_time IS NOT NULL
        ORDER BY open_time DESC
        """,
        (window_days,),
    )
    rows = cur.fetchall()
    pg.close()
    return rows


def characterize(rows: list[dict], window_days: int) -> None:
    print(f'== window: last {window_days} days ==')
    print(f'total 7d closed trades: {len(rows)}')

    abandoned = [r for r in rows if r['duration_sec'] is not None and r['duration_sec'] < 60]
    micro = [r for r in rows if r['duration_sec'] is not None and r['duration_sec'] < 10]
    truncated = [
        r for r in rows
        if r['duration_sec'] is not None and 0 <= r['duration_sec'] < 30
        and abs(r['pnl_usdt'] or 0) < 0.05
    ]
    print(f'duration<60s: {len(abandoned)} | duration<10s: {len(micro)} '
          f'| short+trunc pnl: {len(truncated)}')

    by_signal = Counter((r['signal'] or 'NULL', r['direction'] or 'NULL') for r in abandoned)
    print('\nTop signal/direction in abandoned (<60s):')
    for (sig, d), n in by_signal.most_common(15):
        print(f'  {str(sig):20s} {d:5s} n={n}')

    by_token = Counter((r['token'], r['direction']) for r in abandoned)
    print('\nTop token/dir in abandoned (<60s):')
    for (tok, d), n in by_token.most_common(15):
        print(f'  {str(tok):8s} {d:5s} n={n}')

    by_reason = Counter(r['exit_reason'] for r in abandoned)
    print('\nExit reasons in abandoned:')
    for reason, n in by_reason.most_common(10):
        print(f'  {str(reason):25s} n={n}')

    by_dur_bucket = Counter(int((r['duration_sec'] or 0) // 5) * 5 for r in abandoned)
    print('\nDuration histogram (5s buckets):')
    for bucket in sorted(by_dur_bucket):
        print(f'  {bucket:4d}-{bucket+4:4d}s  n={by_dur_bucket[bucket]}')


def cluster(rows: list[dict]) -> None:
    """Find clusters: same token+direction within 5min of each other."""
    by_token = defaultdict(list)
    for r in rows:
        if r['duration_sec'] is None or r['duration_sec'] >= 60:
            continue
        by_token[(r['token'], r['direction'])].append(r)

    print('\n== Token clusters (>=3 abandoned within 30min) ==')
    for (tok, d), trades in sorted(by_token.items(), key=lambda kv: -len(kv[1])):
        trades.sort(key=lambda r: r['open_time'])
        for i in range(len(trades)):
            window = [
                t for t in trades
                if abs((t['open_time'] - trades[i]['open_time']).total_seconds()) < 1800
            ]
            if len(window) >= 3 and window[0]['id'] == trades[i]['id']:
                print(f'\n  {tok} {d}: {len(window)} abandoned within 30min')
                for t in window:
                    print(f"    #{t['id']:5d} {t['open_time'].strftime('%Y-%m-%d %H:%M:%S')} "
                          f"dur={t['duration_sec']:.0f}s pnl=${(t['pnl_usdt'] or 0):+.2f} "
                          f"exit={t['exit_reason']} signal={t['signal']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()

    rows = fetch(args.days)
    characterize(rows, args.days)
    cluster(rows)


if __name__ == '__main__':
    main()
