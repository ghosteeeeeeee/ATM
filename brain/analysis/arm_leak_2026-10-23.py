#!/usr/bin/env python3
"""arm_leak_2026-10-23.py — does the trail catch the moves we are given?

brain_auditor run #97 creative #1.  Mandate: keep us in trends.
The trail family is how we win (7d profit-monster-trail 36T 88.9% +1.84), so the
question this measures is mechanism health, not a new gate:

  A trade whose price printed +0.40% in our favour (mfe_pct >= 0.40, the arm
  threshold) should end in a trail exit.  If it closed at a stop instead, the
  favorable excursion existed and the trail did not convert it — that is an
  ARM LEAK (wick-vs-close arm check, poll timing, or SL-first ordering).

Cells over the last 14d closed trades with mfe_pct stamped:
    MFE>=0.40 + trail-exit    -> trail converted the move (healthy)
    MFE>=0.40 + no trail-exit -> ARM LEAK (the number this script owns)
    MFE<0.40  + no trail-exit -> never had a move (the known unarmed bleed)

Leak detail is broken out by exit_reason and by signal (n>=3 only), because the
answer decides whether anything is owed: a leak concentrated in already-owned
families (CONF_FLOOR / TAT / MFE-CUT) is owned, a leak in a live uncovered
family is an open item.

Usage:
    python3 arm_leak_2026-10-23.py            # full report
    python3 arm_leak_2026-10-23.py --selfcheck
"""
import sys

sys.path.insert(0, '/root/.hermes/scripts')
from paths import *  # noqa: F401,F403
import psycopg2

DAYS = 14
ARM_MFE = 0.40


def _conn():
    return psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')


def cells(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT (mfe_pct >= %s) AS reached_arm,
               (exit_reason ILIKE '%%trail%%') AS trail_exit,
               COUNT(*), SUM(pnl_usdt)
        FROM trades
        WHERE status='closed' AND mfe_pct IS NOT NULL
          AND close_time > NOW() - INTERVAL '%s days'
        GROUP BY 1, 2
    """, (ARM_MFE, DAYS))
    out = {}
    for reached, trail, n, pnl in cur.fetchall():
        out[(bool(reached), bool(trail))] = (n, float(pnl or 0))
    cur.close()
    return out


def leak_detail(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT exit_reason, COUNT(*), SUM(pnl_usdt)
        FROM trades
        WHERE status='closed' AND mfe_pct >= %s AND NOT (exit_reason ILIKE '%%trail%%')
          AND close_time > NOW() - INTERVAL '%s days'
        GROUP BY 1 ORDER BY 2 DESC
    """, (ARM_MFE, DAYS))
    by_exit = [(r, int(n), float(p or 0)) for r, n, p in cur.fetchall()]
    cur.execute("""
        SELECT signal, COUNT(*), SUM(pnl_usdt)
        FROM trades
        WHERE status='closed' AND mfe_pct >= %s AND NOT (exit_reason ILIKE '%%trail%%')
          AND close_time > NOW() - INTERVAL '%s days'
        GROUP BY 1 HAVING COUNT(*) >= 3 ORDER BY 2
    """, (ARM_MFE, DAYS))
    by_sig = [(r, int(n), float(p or 0)) for r, n, p in cur.fetchall()]
    cur.close()
    return by_exit, by_sig


def report():
    conn = _conn()
    try:
        c = cells(conn)
        by_exit, by_sig = leak_detail(conn)
    finally:
        conn.close()

    leak_n, leak_pnl = c.get((True, False), (0, 0.0))
    conv_n, conv_pnl = c.get((True, True), (0, 0.0))
    cold_n, cold_pnl = c.get((False, False), (0, 0.0))

    print(f'{DAYS}d closed trades with mfe_pct stamped:')
    print(f'  MFE>={ARM_MFE} + trail exit      : {conv_n:4} trades {conv_pnl:+8.2f}  '
          f'({100.0 * conv_n / max(conv_n + leak_n, 1):.1f}% of reached-arm convert)')
    print(f'  MFE>={ARM_MFE} + NO trail exit   : {leak_n:4} trades {leak_pnl:+8.2f}  <= ARM LEAK')
    print(f'  MFE< {ARM_MFE} + no trail exit   : {cold_n:4} trades {cold_pnl:+8.2f}  '
          f'(known unarmed bleed)')

    print('\nleak by exit_reason:')
    for r, n, p in by_exit:
        print(f'  {r:28} {n:3} {p:+8.2f}')
    print('\nleak by signal (n>=3):')
    for s, n, p in by_sig:
        print(f'  {s:32} {n:3} {p:+8.2f}')
    return c, by_exit, by_sig


def selfcheck():
    c, by_exit, by_sig = report()
    total = sum(n for n, _ in c.values())
    leak_n, leak_pnl = c.get((True, False), (0, 0.0))
    conv_n = c.get((True, True), (0, 0.0))[0]
    if not (0 < total < 20000):
        raise SystemExit(f'SELFCHECK FAIL: implausible 14d stamped total {total}')
    if sum(n for _, n, _ in by_exit) != leak_n:
        raise SystemExit(f'SELFCHECK FAIL: exit_reason detail {sum(n for _, n, _ in by_exit)} '
                         f'!= leak cell {leak_n}')
    if abs(sum(p for _, _, p in by_exit) - leak_pnl) > 0.05:
        raise SystemExit('SELFCHECK FAIL: exit_reason pnl does not sum to leak cell pnl')
    if not (0 < conv_n):
        raise SystemExit(f'SELFCHECK FAIL: converted cell missing or empty ({conv_n})')
    print(f'\nSELFCHECK PASS — cells {total} total, leak {leak_n} matches exit_reason detail '
          f'(n and pnl within 0.05).')
    return 0


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(selfcheck())
    report()
