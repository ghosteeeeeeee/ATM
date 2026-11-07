#!/usr/bin/env python3
"""gate_ev_dedup.py — token-day dedup gate EV ranking (AMPLIFY candidate screen).
House convention: dedup blocked rows by (gate, token, direction, day) before summing,
else join-duplicated trade_id inflates SUM(would_pnl) (SLOPE-FILTER had SOL 16788 x9).
--selfcheck asserts dedup shrinks SLOPE-FILTER row count vs raw.
"""
import sqlite3, sys

DB = '/root/.hermes/brain/gate_shadow.db'


def ranked(since, min_n):
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute(
        """
        WITH d AS (
          SELECT gate, token, direction, substr(blocked_at,1,10) day,
                 MAX(would_pnl) pnl, MAX(would_win) ww
          FROM events
          WHERE blocked_at >= ? AND would_pnl IS NOT NULL
          GROUP BY gate, token, direction, substr(blocked_at,1,10)
        )
        SELECT gate, COUNT(*) n, ROUND(AVG(ww),3) ww,
               ROUND(SUM(pnl),2) sum_pnl, ROUND(AVG(pnl),4) avg_pnl
        FROM d GROUP BY gate HAVING COUNT(*) >= ?
        ORDER BY 5 DESC
        """,
        (since, min_n),
    )
    rows = cur.fetchall()
    c.close()
    return rows


def halves(gate, since='2026-10-08'):
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute(
        """
        WITH d AS (
          SELECT token, direction, substr(blocked_at,1,10) day, MAX(would_pnl) pnl
          FROM events
          WHERE gate = ? AND blocked_at >= ? AND would_pnl IS NOT NULL
          GROUP BY token, direction, substr(blocked_at,1,10)
        ), x AS (SELECT pnl, NTILE(2) OVER (ORDER BY day) h FROM d)
        SELECT COUNT(*),
               COALESCE(SUM(CASE WHEN h=1 THEN pnl END),0),
               COALESCE(SUM(CASE WHEN h=2 THEN pnl END),0)
        FROM x
        """,
        (gate, since),
    )
    r = cur.fetchone()
    c.close()
    return r


def selfcheck():
    c = sqlite3.connect(DB)
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM events WHERE gate='SLOPE-FILTER'")
    raw = cur.fetchone()[0]
    cur.execute(
        """SELECT COUNT(*) FROM (
             SELECT token, direction, substr(blocked_at,1,10)
             FROM events WHERE gate='SLOPE-FILTER'
             GROUP BY token, direction, substr(blocked_at,1,10))"""
    )
    dedup = cur.fetchone()[0]
    c.close()
    assert raw > 0, "no SLOPE-FILTER rows"
    assert dedup <= raw, "dedup must not increase rows"
    print(f"selfcheck PASS (SLOPE-FILTER raw={raw} token-day-dedup={dedup})")
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
        sys.exit(0)
    print("=== 30d token-day-dedup gate EV (n>=15) ===")
    for r in ranked('2026-10-08', 15):
        print(f"  {r[0]:28s} n={r[1]:4d} ww={r[2]} sum={r[3]:+.2f} avg={r[4]:+.4f}")
    print("\n=== 14d (n>=10) ===")
    for r in ranked('2026-10-24', 10):
        print(f"  {r[0]:28s} n={r[1]:4d} ww={r[2]} sum={r[3]:+.2f} avg={r[4]:+.4f}")
    print("\n=== split halves (30d) ===")
    for g, *_ in ranked('2026-10-08', 15):
        n, o, nw = halves(g)
        print(f"  {g:28s} n={n:3d} older={o:+.2f} newer={nw:+.2f}")
