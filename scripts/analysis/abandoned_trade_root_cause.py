#!/usr/bin/env python3
"""Characterize abandoned trades and root-cause their SL placement.

Outputs three sections:
  1. Population summary (sub-60s, sub-2min closed trades)
  2. Wrong-side SL trades (LONG with SL>entry or SHORT with SL<entry)
  3. Per-trade dump for the worst offenders

Used to triage the 2026-07-14 abandoned-trade class: 26 sub-60s trades
in 14d, 11 with wrong-side SL, 10 with SL < 0.10% from entry.
"""
from __future__ import annotations

import argparse
import os
import sys
import psycopg2
import psycopg2.extras
from collections import Counter, defaultdict


def fetch(window_days: int) -> list[dict]:
    pg = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id, token, direction, entry_price, exit_price, stop_loss, target,
               EXTRACT(EPOCH FROM (close_time - open_time)) AS dur_s,
               open_time, close_time, exit_reason, signal, atr_managed, pnl_usdt, pnl_pct
        FROM trades
        WHERE status = 'closed'
          AND close_time > NOW() - INTERVAL '%s days'
          AND EXTRACT(EPOCH FROM (close_time - open_time)) < 120
        ORDER BY open_time DESC
        """,
        (window_days,),
    )
    rows = cur.fetchall()
    pg.close()
    return rows


def sl_pct_and_side(direction: str, entry: float, sl: float) -> tuple[float | None, bool]:
    """Returns (sl_pct_with_sign_convention, is_wrong_side)."""
    if not sl or sl <= 0 or not entry or entry <= 0:
        return None, False
    if direction == 'LONG':
        return (entry - sl) / entry * 100, sl > entry
    return (sl - entry) / entry * 100, sl < entry


def characterize(rows: list[dict], window_days: int) -> None:
    sub60 = [r for r in rows if (r['dur_s'] or 0) < 60]
    sub60_atr = sum(1 for r in sub60 if r['atr_managed'])
    wrong = []
    tight = []
    for r in sub60:
        sl_pct, wrong_side = sl_pct_and_side(r['direction'], float(r['entry_price']), float(r['stop_loss'] or 0))
        if wrong_side:
            wrong.append(r)
        if sl_pct is not None and abs(sl_pct) < 0.10:
            tight.append(r)

    total_pnl = sum(float(r['pnl_usdt'] or 0) for r in sub60)
    print(f'== window: last {window_days} days ==')
    print(f'sub-60s closed trades: {len(sub60)}  (atr_managed: {sub60_atr}/{len(sub60)})')
    print(f'wrong-side SL: {len(wrong)}/{len(sub60)}')
    print(f'tight SL (<0.10%): {len(tight)}/{len(sub60)}')
    print(f'total PnL of sub-60s: ${total_pnl:+.2f}')
    print()

    by_exit = Counter(r['exit_reason'] for r in sub60)
    print('exit reasons:')
    for reason, n in by_exit.most_common():
        print(f'  {reason or "NULL":25s} n={n}')

    by_signal = Counter(r['signal'] for r in sub60)
    print('\ntop signals:')
    for s, n in by_signal.most_common(8):
        print(f'  {s or "NULL":25s} n={n}')

    print('\nWRONG-SIDE SL ROWS:')
    for r in wrong:
        sl_pct, _ = sl_pct_and_side(r['direction'], float(r['entry_price']), float(r['stop_loss'] or 0))
        print(f"  #{r['id']:5d} {r['open_time'].strftime('%m-%d %H:%M:%S')} "
              f"{r['token']:8s} {r['direction']:5s} entry={r['entry_price']:.4g} sl={r['stop_loss']:.4g} "
              f"sl_pct={sl_pct:+.3f}% dur={r['dur_s']:.0f}s pnl=${(r['pnl_usdt'] or 0):+.2f} "
              f"exit={r['exit_reason']} atr={r['atr_managed']} sig={r['signal']}")

    print('\nVERY TIGHT SL ROWS (|sl_pct| < 0.10%):')
    for r in tight:
        sl_pct, _ = sl_pct_and_side(r['direction'], float(r['entry_price']), float(r['stop_loss'] or 0))
        print(f"  #{r['id']:5d} {r['open_time'].strftime('%m-%d %H:%M:%S')} "
              f"{r['token']:8s} {r['direction']:5s} entry={r['entry_price']:.4g} sl={r['stop_loss']:.4g} "
              f"sl_pct={sl_pct:+.3f}% dur={r['dur_s']:.0f}s pnl=${(r['pnl_usdt'] or 0):+.2f} "
              f"exit={r['exit_reason']} atr={r['atr_managed']} sig={r['signal']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=14)
    args = parser.parse_args()
    rows = fetch(args.days)
    characterize(rows, args.days)


if __name__ == '__main__':
    main()
