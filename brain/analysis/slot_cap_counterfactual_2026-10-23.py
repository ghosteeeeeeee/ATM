#!/usr/bin/env python3
"""Concurrency slot-cap counterfactual (brain_auditor #98, 2026-10-23).

WHY THIS EXISTS: size_reduce 0.5x is inert on the min-notional book —
measured this run, 283/349 (81%) of 14d closes sit at amount_usdt <= 11.5
(the HL floor), so `base * 0.5` is floored back to 11.0 and cuts nothing.
The only notional-independent risk levers are trade COUNT (slot cap) or
frequency. This measures the slot-cap lever before anyone proposes it.

COUNTERFACTUAL: replay opens chronologically; a trade is 'blocked' when
already >= CAP positions are open at its open_time (blocked = never opened;
its PnL leaves the book).

Reported per CAP: blocked n / WR / PnL, kept PnL, and winner-kill =
share of all winners that would be blocked (bar: <20%).

Usage:
  python3 slot_cap_counterfactual_2026-10-23.py [--selfcheck]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import *  # noqa


def load(hours=336):
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, open_time, COALESCE(close_time, (NOW() AT TIME ZONE 'UTC')), pnl_usdt
        FROM trades
        WHERE status='closed' AND pnl_usdt IS NOT NULL AND open_time > NOW() - INTERVAL '%d hours'
        ORDER BY open_time""" % int(hours))
    rows = cur.fetchall()
    conn.close()
    return rows


def replay(rows, cap):
    iv = [(r[1], r[2]) for r in rows]
    ev = []
    for i, (a, b) in enumerate(iv):
        ev.append((a, 1, i))
        ev.append((b, -1, i))
    ev.sort(key=lambda x: (x[0], x[1]))  # close(-1) before open(1) at equal ts
    active, blocked = set(), set()
    for t, d, i in ev:
        if d == 1:
            if len(active) >= cap:
                blocked.add(i)   # never opened -> occupies no slot
            else:
                active.add(i)
        else:
            active.discard(i)
    return blocked


def report(rows, cap, all_winners):
    blk = replay(rows, cap)
    keep = [i for i in range(len(rows)) if i not in blk]
    bp = sum(float(rows[i][3]) for i in blk)
    kp = sum(float(rows[i][3]) for i in keep)
    bw = sum(1 for i in blk if rows[i][3] > 0)
    kw = sum(1 for i in keep if rows[i][3] > 0)
    fk = 100.0 * bw / max(all_winners, 1)
    verdict = 'PASS(fk)' if fk < 20 else 'FAIL(fk)'
    print(f"  cap{cap}: blocked n={len(blk):3} W={bw:3} pnl={bp:+7.2f} | "
          f"kept n={len(keep):3} W={kw:3} pnl={kp:+7.2f} | "
          f"fk={bw}/{all_winners}={fk:.1f}% {verdict} | save={bp * -1:+.2f}")
    return dict(cap=cap, blocked=len(blk), blocked_w=bw, blocked_pnl=bp,
                kept_pnl=kp, fk=fk, fk_pass=fk < 20)


def concurrency_time(rows):
    ev = []
    for a, b in ((r[1], r[2]) for r in rows):
        ev.append((a, 1))
        ev.append((b, -1))
    ev.sort(key=lambda x: (x[0], x[1]))  # close(-1) before open(1) at equal ts
    prev = None
    cur = 0
    time_at = {}
    for t, d in ev:
        if prev is not None:
            time_at[cur] = time_at.get(cur, 0) + (t - prev).total_seconds()
        cur += 1 if d == 1 else -1
        prev = t
    tot = sum(time_at.values()) or 1
    return {k: 100.0 * v / tot for k, v in sorted(time_at.items())}


def selfcheck():
    import datetime as dt
    # 4 trades: A 10:00-11:00, B 10:30-12:00, C 10:45-11:30, D 13:00-14:00
    rows = [
        (1, dt.datetime(2026, 10, 23, 10, 0), dt.datetime(2026, 10, 23, 11, 0), -1.0),
        (2, dt.datetime(2026, 10, 23, 10, 30), dt.datetime(2026, 10, 23, 12, 0), +2.0),
        (3, dt.datetime(2026, 10, 23, 10, 45), dt.datetime(2026, 10, 23, 11, 30), -0.5),
        (4, dt.datetime(2026, 10, 23, 13, 0), dt.datetime(2026, 10, 23, 14, 0), +1.0),
    ]
    # at 10:45 A+B open (2) -> C blocked under cap2; A open at 10:30 -> B kept under cap2
    assert replay(rows, 2) == {2}, replay(rows, 2)   # C blocked at 10:45 (A,B already open)
    assert replay(rows, 1) == {1, 2}, replay(rows, 1)  # B and C blocked, D later keeps a free slot
    assert replay(rows, 3) == set(), replay(rows, 3)
    # discriminating case: a BLOCKED trade must not hold the slot for later opens
    disc = [
        (1, dt.datetime(2026, 10, 23, 10, 0), dt.datetime(2026, 10, 23, 11, 0), +1.0),
        (2, dt.datetime(2026, 10, 23, 10, 30), dt.datetime(2026, 10, 23, 13, 0), -1.0),
        (3, dt.datetime(2026, 10, 23, 12, 0), dt.datetime(2026, 10, 23, 13, 0), +1.0),
    ]
    assert replay(disc, 1) == {1}, replay(disc, 1)  # B blocked, C must be KEPT
    ct = concurrency_time(rows)
    assert abs(sum(ct.values()) - 100.0) < 0.01, ct
    # cap2 blocks only C (-0.5): save = +0.5, fk = 0 of 2 winners
    r = report(rows, 2, 2)
    assert r['blocked'] == 1 and abs(r['blocked_pnl'] - (-0.5)) < 1e-9, r
    assert r['fk'] == 0.0 and r['fk_pass']
    print('SELFCHECK PASS — chronological replay, concurrency-time, fk arithmetic')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(0 if selfcheck() else 1)
    rows = load()
    print(f'closed trades (14d window): {len(rows)}')
    print('time at concurrency level: ' + ', '.join(
        f"{k}:{v:.1f}%" for k, v in concurrency_time(rows).items()))
    allw = sum(1 for r in rows if r[3] > 0)
    print(f'winners in book: {allw}')
    out = [report(rows, cap, allw) for cap in (2, 3, 4, 5, 6)]
    best = max((o for o in out if o['fk_pass']), key=lambda o: -o['blocked_pnl'], default=None)
    if best:
        print(f"\nbest fk-passing cap: cap{best['cap']} save={-best['blocked_pnl']:+.2f} "
              f"(n={best['blocked']}, fk={best['fk']:.1f}%)")
    else:
        print('\nno fk-passing cap')
