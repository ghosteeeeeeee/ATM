#!/usr/bin/env python3
"""Losing-trade recovery replay — CORRECTED method (brain_auditor #85, 2026-10-22).

THE BUG THIS REPLACES: anchoring recovery at open_time is ~96% vacuous.
The 1m candle containing open_time always includes the entry print, so
'high >= entry*0.998' (LONG) is satisfied by candle 1 itself. Measured
2026-10-22: 198/206 (96.1%) of 14d losers pass on candle 1 alone — every
"X/X recovered within -0.2% in 30m" audit claim from ~#70-#84 was
near-guaranteed by construction and carried no directional evidence.

CORRECTED DEFINITION (default = adverse-first, non-vacuous):
  1. Find the first 1m bar after open where price is >0.2% against entry.
  2. Recovery = a LATER bar trades back within 0.2% of entry.
  3. Trades that never go >0.2% adverse are reported as 'never_adverse'
     (shallow losses) — never counted as recovered.

Usage:
  python3 recovery_replay.py [HOURS]     # default 48
  python3 recovery_replay.py --selfcheck # 14d + vacuity assertion
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import *
import psycopg2
import sqlite3


def losers(hours):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, open_time, entry_price, pnl_usdt, signal, exit_reason
        FROM trades
        WHERE status='closed' AND pnl_usdt < 0
          AND close_time > NOW() - INTERVAL '%d hours'
        ORDER BY pnl_usdt""" % int(hours))
    rows = cur.fetchall()
    conn.close()
    return rows


def replay(rows):
    db = sqlite3.connect(CANDLES_DB)
    cur = db.cursor()
    out = {'n': len(rows), 'never_adverse': [], 'recovered': [], 'never': [], 'nodata': []}
    for tid, tok, direction, ot, entry, pnl, sig, exr in rows:
        entry = float(entry)
        t0 = int(ot.timestamp())
        cur.execute(
            'SELECT open, low, high, close FROM candles_1m '
            'WHERE token=? AND ts>=? AND ts<=? AND is_closed=1 ORDER BY ts',
            (tok, t0, t0 + 1800))
        bars = cur.fetchall()
        if not bars:
            out['nodata'].append(tid)
            continue
        long_ = direction.upper() == 'LONG'
        adverse = (lambda lo: lo < entry * 0.998) if long_ else (lambda hi: hi > entry * 1.002)
        back = (lambda hi: hi >= entry * 0.998) if long_ else (lambda lo: lo <= entry * 1.002)
        idx = next((i for i, (o, lo, hi, cl) in enumerate(bars) if adverse(lo if long_ else hi)), None)
        if idx is None:
            out['never_adverse'].append((tid, tok, sig))
            continue
        hit = (any(back(hi if long_ else lo) for o, lo, hi, cl in bars[idx + 1:])
               or back(bars[idx][3]))
        rec = (tid, tok, direction, sig, exr, round(float(pnl), 3))
        (out['recovered'] if hit else out['never']).append(rec)
    db.close()
    return out


def candle1_vacuity(rows):
    """How many losers pass the OLD open-anchored test on candle 1 alone."""
    db = sqlite3.connect(CANDLES_DB)
    cur = db.cursor()
    hit = checked = 0
    for tid, tok, direction, ot, entry, pnl, sig, exr in rows:
        entry = float(entry)
        cur.execute(
            'SELECT open, low, high FROM candles_1m '
            'WHERE token=? AND ts>=? AND is_closed=1 ORDER BY ts LIMIT 1',
            (tok, int(ot.timestamp())))
        bar = cur.fetchone()
        if not bar:
            continue
        checked += 1
        o, lo, hi = bar
        if (direction.upper() == 'LONG' and hi >= entry * 0.998) or \
           (direction.upper() == 'SHORT' and lo <= entry * 1.002):
            hit += 1
    db.close()
    return hit, checked


def report(hours):
    rows = losers(hours)
    r = replay(rows)
    print(f'{hours}h losers n={r["n"]}')
    print(f'  never_adverse (never moved >0.2% against entry): {len(r["never_adverse"])}')
    print(f'  recovered AFTER adverse excursion:               {len(r["recovered"])}')
    print(f'  NEVER traded back within 0.2% of entry:          {len(r["never"])}')
    for x in r['never']:
        print(f'    NEVER: {x}')
    for x in r['nodata']:
        print(f'    NODATA: {x}')
    return r


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        rows = losers(24 * 14)
        hit, checked = candle1_vacuity(rows)
        print(f'VACUITY: old open-anchored test passes on candle 1 alone for '
              f'{hit}/{checked} = {100.0 * hit / max(checked, 1):.1f}% of 14d losers')
        assert checked > 100 and hit / checked > 0.90, (
            'vacuity pattern changed — re-examine any claims built on the old method')
        print('ASSERT PASS: open-anchored recovery is vacuous; use adverse-first anchor')
        report(24 * 14)
    else:
        report(int(sys.argv[1]) if len(sys.argv) > 1 else 48)
