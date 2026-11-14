#!/usr/bin/env python3
"""11-14 EXIT-STACK walk — brain_auditor #258.

Two PRE-REGISTERED counterfactuals due 2026-11-14, adjudicated jointly,
ship at most ONE (registry collision_check on amplify-tat-neverarmed-age-widen):

A) amplify-prearm-breakeven-lock (type a, tighten):
   UNARMED trades (trailing_activated=false): once peak fav >= thr and price
   later returns to entry BEFORE the walk ever sees +0.40 arm -> lock exits
   at entry -> pnl 0. Armed trades (walk fav>=0.40 first) untouched.
   Bars: net delta >= +$2.00/30d (pnl_usdt) AND fk<20% AND 14d same-sign.
   Default NO SHIP; pick ONE arm.

B) amplify-tat-neverarmed-age-widen (type a, loosen):
   trail_arm_timeout exits: extend age +38m (52->90m cap). New exit = 1m
   close at close_time+38m. delta = price_move% x amount_usdt (UNITS GUARD:
   never mix with pnl_pct). Trades that ARM during the extension are reported
   separately, excluded from net (trail takes over, exit unknown).
   Bars: pooled n>=40 walked AND net delta >= +$1.00/30d AND fk<20% AND
   30d same-sign (halves). Default NO CHANGE.

Usage: python3 exit_stack_walk_2026_11_14.py [--selfcheck]
"""
import os
import sys
from datetime import timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'scripts'))
from paths import *
import psycopg2
import sqlite3

ARM = 0.40
THR_SWEEP = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40)
TAT_EXT_S = 38 * 60


def load_trades(days=30):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, exit_price, pnl_usdt, amount_usdt,
               open_time, close_time, COALESCE(signal,'(none)'),
               COALESCE(exit_reason,'(none)'), trailing_activated, mfe_pct
        FROM trades
        WHERE status='closed' AND entry_price IS NOT NULL
          AND close_time > NOW() - INTERVAL %s
        ORDER BY open_time""", (f'{days} days',))
    rows = cur.fetchall()
    conn.close()
    return rows


def walk_lock(bars, entry, long_, thr):
    """Sequential walk. Returns (locked:bool, armed:bool).

    Lock fires only if: prior maxfav >= thr, this bar crosses entry back,
    and the walk has NOT yet seen fav >= ARM. Arm is checked first within a
    bar (conservative: armed trades untouched).
    """
    maxfav = 0.0
    armed = False
    for hi, lo in bars:
        fav = ((hi / entry - 1) * 100) if long_ else ((1 - lo / entry) * 100)
        prior = maxfav
        if fav > maxfav:
            maxfav = fav
        if maxfav >= ARM:
            armed = True
            return False, True
        if prior >= thr:
            cross = (lo <= entry) if long_ else (hi >= entry)
            if cross:
                return True, False
    return False, armed


def prearm_walk(rows, db, thr):
    """A) per-thr lock walk over unarmed trades."""
    out = {'n': 0, 'locked': 0, 'winners': 0, 'fk_winners': 0,
           'net30': 0.0, 'net14': 0.0, 'net_h1': 0.0, 'net_h2': 0.0,
           'nodata': 0, 'excluded_armed_live': 0}
    now_ts = rows[-1][8].timestamp() if rows else 0  # not used; split by 14d below
    for (tid, tok, direc, entry, xprice, pnl_usd, amt, ot, ct, sig, exr,
         trail, mfe) in rows:
        if trail:  # armed live — untouched
            out['excluded_armed_live'] += 1
            continue
        entry = float(entry)
        long_ = direc.upper() == 'LONG'
        ts0 = int(ot.replace(tzinfo=timezone.utc).timestamp())
        ts1 = int(ct.replace(tzinfo=timezone.utc).timestamp())
        bars = db.execute(
            "SELECT high, low FROM candles_1m WHERE token=? AND ts>=? AND ts<=? "
            "ORDER BY ts", (tok, ts0, ts1 + 60)).fetchall()
        if not bars:
            out['nodata'] += 1
            continue
        out['n'] += 1
        pnl = float(pnl_usd or 0)
        if pnl > 0:
            out['winners'] += 1
        locked, _armed = walk_lock(bars, entry, long_, thr)
        if locked:
            out['locked'] += 1
            delta = 0.0 - pnl  # exit at entry -> 0
            out['net30'] += delta
            if pnl > 0:
                out['fk_winners'] += 1
            # window splits by close_time
            if ct.replace(tzinfo=timezone.utc).timestamp() >= _now_minus(14):
                out['net14'] += delta
            if ct.replace(tzinfo=timezone.utc).timestamp() >= _now_minus(15):
                out['net_h2'] += delta
            else:
                out['net_h1'] += delta
    out['fk_pct'] = round(100.0 * out['fk_winners'] / out['winners'], 1) if out['winners'] else None
    for k in ('net30', 'net14', 'net_h1', 'net_h2'):
        out[k] = round(out[k], 2)
    return out


_NOW = None


def _now_minus(days):
    global _NOW
    if _NOW is None:
        import time
        _NOW = time.time()
    return _NOW - days * 86400


def tat_walk(rows, db):
    """B) TAT +38m extension walk."""
    out = {'n': 0, 'armed_during_ext': 0, 'nodata': 0, 'winners': 0,
           'fk_flip': 0, 'fk_any': 0, 'net30': 0.0, 'net14': 0.0,
           'net_h1': 0.0, 'net_h2': 0.0}
    for (tid, tok, direc, entry, xprice, pnl_usd, amt, ot, ct, sig, exr,
         trail, mfe) in rows:
        if exr != 'trail_arm_timeout':
            continue
        if entry is None or xprice is None or not amt:
            out['nodata'] += 1
            continue
        entry = float(entry)
        xprice = float(xprice)
        amt = float(amt)
        long_ = direc.upper() == 'LONG'
        ct_ts = int(ct.replace(tzinfo=timezone.utc).timestamp())
        # candles strictly after exit, completing within +38m
        bars = db.execute(
            "SELECT ts, close FROM candles_1m WHERE token=? AND ts>? AND ts+60<=? "
            "AND is_closed=1 ORDER BY ts", (tok, ct_ts, ct_ts + TAT_EXT_S)).fetchall()
        if not bars:
            out['nodata'] += 1
            continue
        out['n'] += 1
        pnl = float(pnl_usd or 0)
        if pnl > 0:
            out['winners'] += 1
        # did the walk ARM during the extension?
        armed = False
        for _ts, cl in bars:
            fav = ((cl / entry - 1) * 100) if long_ else ((1 - cl / entry) * 100)
            if fav >= ARM:
                armed = True
                break
        if armed:
            out['armed_during_ext'] += 1
            continue
        new_close = bars[-1][1]
        move_pct = ((new_close - xprice) / entry * 100.0) if long_ else \
                   ((xprice - new_close) / entry * 100.0)
        delta = move_pct / 100.0 * amt  # pnl_usdt units: price_move% x notional
        new_pnl = pnl + delta
        out['net30'] += delta
        if pnl > 0:
            if new_pnl <= 0:
                out['fk_flip'] += 1
            if new_pnl < pnl:
                out['fk_any'] += 1
        if ct_ts >= _now_minus(14):
            out['net14'] += delta
        if ct_ts >= _now_minus(15):
            out['net_h2'] += delta
        else:
            out['net_h1'] += delta
    out['fk_pct'] = round(100.0 * out['fk_flip'] / out['winners'], 1) if out['winners'] else None
    out['fk_any_pct'] = round(100.0 * out['fk_any'] / out['winners'], 1) if out['winners'] else None
    for k in ('net30', 'net14', 'net_h1', 'net_h2'):
        out[k] = round(out[k], 2)
    return out


def selfcheck():
    # synthetic: peak 0.15->0.30 (below arm 0.40) then back to entry -> lock
    entry = 100.0
    locked, armed = walk_lock([(100.15, 100.05), (100.30, 100.10), (100.20, 99.95)],
                              entry, True, 0.10)
    assert locked and not armed, (locked, armed)
    # arm first then cross entry -> no lock
    locked, armed = walk_lock([(100.15, 100.05), (104.5, 103.0), (100.0, 99.5)],
                              entry, True, 0.10)
    assert not locked and armed, (locked, armed)
    # peak below thr, never returns -> no lock
    locked, armed = walk_lock([(100.03, 100.01), (100.02, 100.005)], entry, True, 0.10)
    assert not locked, (locked, armed)
    # peak >= thr but never crosses back -> no lock
    locked, armed = walk_lock([(100.20, 100.10), (100.30, 100.15)], entry, True, 0.10)
    assert not locked, (locked, armed)
    rows = load_trades(30)
    assert len(rows) > 100, len(rows)
    db = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True)
    tat = tat_walk(rows, db)
    assert tat['n'] + tat['nodata'] > 0, tat
    db.close()
    print('SELF-CHECK PASS', {'rows30d': len(rows), 'tat_n': tat['n'],
                              'tat_nodata': tat['nodata']})


def main():
    if '--selfcheck' in sys.argv:
        selfcheck()
        return
    rows = load_trades(30)
    db = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True)
    print(f'30d closed trades loaded: {len(rows)}')
    print('\n=== A) PRE-ARM BREAKEVEN LOCK (thr sweep) ===')
    print(f'{"thr":>5} {"n":>5} {"lock":>5} {"win":>5} {"fk%":>6} {"net30":>8} {"net14":>8} {"h1":>7} {"h2":>7} {"nodata":>6}')
    best = None
    excluded = 0
    for thr in THR_SWEEP:
        r = prearm_walk(rows, db, thr)
        excluded = r['excluded_armed_live']
        print(f'{thr:>5} {r["n"]:>5} {r["locked"]:>5} {r["winners"]:>5} '
              f'{str(r["fk_pct"]):>6} {r["net30"]:>8} {r["net14"]:>8} '
              f'{r["net_h1"]:>7} {r["net_h2"]:>7} {r["nodata"]:>6}')
        # bar check (only for candidate selection; ship needs CEO)
        if (r['net30'] >= 2.00 and r['fk_pct'] is not None and r['fk_pct'] < 20
                and r['net14'] > 0 and r['winners'] >= 5):
            if best is None or r['net30'] > best[1]['net30']:
                best = (thr, r)
    print(f'  excluded trailing_activated=true (armed live, untouched): {excluded}')
    print(f'  BAR CANDIDATE: {best}' if best else '  NO ARM CLEARS ALL BARS (default NO SHIP stands)')
    tat = tat_walk(rows, db)
    print('\n=== B) TAT AGE WIDEN 52->90m (+38m) ===')
    print(f'  walked n={tat["n"]} nodata={tat["nodata"]} armed_during_ext={tat["armed_during_ext"]} '
          f'(excluded from net)')
    print(f'  winners={tat["winners"]} fk_flip={tat["fk_flip"]} ({tat["fk_pct"]}%) '
          f'fk_any={tat["fk_any"]} ({tat["fk_any_pct"]}%)')
    print(f'  net30={tat["net30"]} net14={tat["net14"]} h1={tat["net_h1"]} h2={tat["net_h2"]}')
    tat_bar = (tat['n'] >= 40 and tat['net30'] >= 1.00 and tat['fk_pct'] is not None
               and tat['fk_pct'] < 20 and tat['net_h1'] * tat['net_h2'] > 0)
    print(f'  ALL BARS: {"PASS -> SHIP CANDIDATE" if tat_bar else "FAIL -> NO CHANGE stands"}')
    db.close()


if __name__ == '__main__':
    main()
