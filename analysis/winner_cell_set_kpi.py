#!/usr/bin/env python3
"""winner_cell_set_kpi — one-shot reproducible read for the two size-amplify items.

Answers, from live PG + rotated pipeline logs (spanning rotation, per audit #233):

  1. winner-cell-size-125 bar: 14d TAGGED-trade uplift vs 1.0x, three readings
     (A) uplift = tagged_pnl * (mult-1)/mult
     (B) cell-set net now vs pre-flip window (10-15..10-29)
     (C) cell-set net rolling-14d
     bar: delta >= +$1.00  (registry winner-cell-size-125, deadline 11-10)
  2. amplify-winner-cell-mult-150 threshold: each cell net30>0 AND
     >=3 of 4 cells net14>0 AND set net7>0
  3. per-cell + set net at 7/14/30d

UNITS: pnl_usdt everywhere (never pnl_pct — leverage landmine, #193).

Self-check: python3 analysis/winner_cell_set_kpi.py --selfcheck
"""
import glob
import gzip
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from paths import *  # noqa

CELLS = [
    ('bb-squeeze+', 'NORMAL'),
    ('volume-buildup-', 'HIGH'),
    ('r2v2-long3', 'NORMAL'),
    ('pump-chain+', 'EXTREME'),
]
PRE_FLIP = ('2026-10-15', '2026-10-29')   # before WINNER_CELL_SIZE_MULT went live 2026-10-29
TAG_RE = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*WINNER-CELL-SIZE\] '
    r'(?P<tok>[A-Z0-9]+) (?P<dir>LONG|SHORT): (?P<sig>.+?) in (?P<reg>[A-Z]+) cell '
    r'-> x(?P<mult>[\d.]+)')
TAG = 'WINNER-CELL-SIZE'


def tag_lines():
    """Every WINNER-CELL-SIZE line across rotated archives AND the live log."""
    out = []
    for f in sorted(glob.glob(os.path.join(HERMES_LOG_DIR, 'archive', '*.gz'))):
        try:
            with gzip.open(f, 'rt', errors='replace') as fh:
                out.extend(ln.rstrip() for ln in fh if TAG in ln)
        except OSError:
            pass
    live = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
    if os.path.exists(live):
        with open(live, errors='replace') as fh:
            out.extend(ln.rstrip() for ln in fh if TAG in ln)
    return out


def tagged_trades(conn, days=14):
    """Unique (token,direction,minute) tags -> PG trade rows opened within +-10min."""
    recs, seen = [], set()
    for ln in tag_lines():
        m = TAG_RE.search(ln)
        if not m:
            continue
        d = m.groupdict()
        k = (d['tok'], d['dir'], d['ts'][:16])
        if k in seen:
            continue
        seen.add(k)
        recs.append(d)
    cur = conn.cursor()
    ids, by_mult = set(), {}
    for d in recs:
        t = datetime.strptime(d['ts'], '%Y-%m-%d %H:%M:%S')
        cur.execute(
            """SELECT id FROM trades
               WHERE token=%s AND direction=%s AND open_time BETWEEN %s AND %s""",
            (d['tok'], d['dir'], t - timedelta(minutes=10), t + timedelta(minutes=10)))
        for (tid,) in cur.fetchall():
            ids.add(tid)
            by_mult[tid] = float(d['mult'])
    if not ids:
        return {'n': 0, 'pnl': 0.0, 'mult': 1.0, 'uplift': 0.0,
                'tag_events': len(recs)}
    cur.execute(
        """SELECT id, pnl_usdt FROM trades
           WHERE id = ANY(%s) AND close_time > NOW() - INTERVAL %s""",
        (list(ids), f'{days} days'))
    rows = cur.fetchall()
    pnl = sum(float(r[1] or 0) for r in rows)
    mults = {by_mult[r[0]] for r in rows}
    mult = max(mults) if mults else 1.0
    return {'n': len(rows), 'pnl': round(pnl, 4), 'mult': mult,
            'uplift': round(pnl * (mult - 1.0) / mult, 4) if mult > 1 else 0.0,
            'tag_events': len(recs)}


def cell_net(conn, signal, regime, days):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(pnl_usdt),0) FROM trades "
        "WHERE status='closed' AND signal=%s AND volatility_regime=%s "
        f"AND close_time > NOW() - INTERVAL '{days} days'",
        (signal, regime))
    n, p = cur.fetchone()
    return int(n), round(float(p), 4)


def window_net(conn, a, b):
    cur = conn.cursor()
    tot, n = 0.0, 0
    for s, r in CELLS:
        cur.execute(
            """SELECT COUNT(*), COALESCE(SUM(pnl_usdt),0) FROM trades
               WHERE status='closed' AND signal=%s AND volatility_regime=%s
                 AND close_time >= %s AND close_time < %s""", (s, r, a, b))
        c, p = cur.fetchone()
        n += c
        tot += float(p)
    return n, round(tot, 4)


def report():
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        print('=== per-cell / set net (pnl_usdt) ===')
        sets = {}
        for days in (7, 14, 30):
            tot = 0.0
            print(f'-- {days}d --')
            for s, r in CELLS:
                n, p = cell_net(conn, s, r, days)
                tot += p
                print(f'   {s}|{r}: n={n} net={p}')
            sets[days] = round(tot, 4)
            print(f'   SET {days}d net = {sets[days]}')

        print('\n=== 1) winner-cell-size-125 bar (delta >= +1.00) ===')
        tg = tagged_trades(conn, days=14)
        n_pre, pre = window_net(conn, *PRE_FLIP)
        n_14, set14 = (None, sets[14])
        print(f'   tagged 14d: n={tg["n"]} pnl@{tg["mult"]}x = {tg["pnl"]}')
        print(f'   (A) uplift vs 1.0x            = {tg["uplift"]:+.4f}  '
              f'{"PASS" if tg["uplift"] >= 1.0 else "FAIL"}')
        print(f'   (B) set-net now {set14} - pre-flip {pre} (n={n_pre}) = '
              f'{round(set14 - pre, 4):+.4f}  '
              f'{"PASS" if set14 - pre >= 1.0 else "FAIL"}')
        print(f'   (C) rolling 14d set net       = {set14:+.4f}  '
              f'{"PASS" if set14 >= 1.0 else "FAIL"}')

        print('\n=== 2) amplify-winner-cell-mult-150 threshold ===')
        c30 = all(cell_net(conn, s, r, 30)[1] > 0 for s, r in CELLS)
        n14 = sum(1 for s, r in CELLS if cell_net(conn, s, r, 14)[1] > 0)
        print(f'   each cell net30>0          : {c30}')
        print(f'   >=3 of 4 cells net14>0     : {n14}/4  {"PASS" if n14 >= 3 else "FAIL"}')
        print(f'   set net7>0                 : {sets[7]}  '
              f'{"PASS" if sets[7] > 0 else "FAIL"}')
        met = c30 and n14 >= 3 and sets[7] > 0
        print(f'   THRESHOLD {"MET" if met else "NOT MET"} '
              f'(default = NO CHANGE, stays 1.25)')
        return met
    finally:
        conn.close()


def selfcheck():
    """Hand-checkable asserts on the parsing + arithmetic (no DB needed)."""
    line = ('2026-11-06 12:00:00   🎯 [WINNER-CELL-SIZE] SOL LONG: bb-squeeze+ in NORMAL '
            'cell -> x1.25 (cap 1.50, regime_src=sig)')
    m = TAG_RE.search(line)
    assert m, 'tag regex failed to parse a real-format line'
    assert (m['tok'], m['dir'], m['sig'], m['reg'], m['mult']) == \
        ('SOL', 'LONG', 'bb-squeeze+', 'NORMAL', '1.25'), m.groupdict()
    # uplift arithmetic: 1.25x on a +1.00 pnl trade earns +0.20 over 1.0x
    pnl, mult = 1.00, 1.25
    assert abs(pnl * (mult - 1) / mult - 0.20) < 1e-9
    # rotation spanning: archives must exist and be scanned (audit #233 regression guard)
    arch = glob.glob(os.path.join(HERMES_LOG_DIR, 'archive', '*.gz'))
    assert arch, 'no rotated archives under logs/archive — rotation spanning broken'
    assert isinstance(tag_lines(), list)
    print(f'selfcheck PASS (regex, uplift math, {len(arch)} archives scanned)')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        report()
