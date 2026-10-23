#!/usr/bin/env python3
"""TAT (trail_arm_timeout) forward-return audit — brain_auditor #91, 2026-10-23.

Question the live TAT exit never had answered: after the timeout closes a
stalled trade, does price recover to entry (cut was premature) or keep going
against (cut was right)? Informs the pending TAT flip / Oct 25 stall-exit
eval — NOT a ship by itself (n<20 = monitor bar).

Method (close-anchored, stated explicitly):
  - anchor = close_time of each trail_arm_timeout exit (14d)
  - recovery: a 1m bar at-or-after the exit bar trades back within 0.2% of
    ENTRY within 30m (bar0 close is strictly after the exit print, so this
    is not the known-vacuous open-anchored class)
  - exit_depth = (exit_price - entry)/entry: TAT only cuts trades still
    below the 0.40% arm line, so recovery rate is heavily conditioned on
    cut depth — ALWAYS report recovery bucketed by exit_depth (bug-hunter
    #91 finding: unbucketed "70.6% recovered" restates cut depth, not
    post-cut reversal)
  - fwd30m = exit_price -> last closed bar close in the 30m window,
    sign-flipped so positive = favorable to the trade

Usage: python3 tat_forward_2026-10-23.py [--selfcheck]
"""
import os
import sys
from datetime import timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import *
import psycopg2
import sqlite3

WIN_MIN = 30


def recovered(entry, long_, closes):
    """True if any close trades back within 0.2% of entry."""
    if long_:
        return any(c >= entry * 0.998 for c in closes)
    return any(c <= entry * 1.002 for c in closes)


def fwd_pct(exit_price, last_close, long_):
    """Signed 30m forward from exit_price; positive = favorable to trade."""
    f = (last_close - exit_price) / exit_price * 100.0
    return f if long_ else -f


def rows_14d():
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, exit_price, close_time, pnl_usdt, signal
        FROM trades
        WHERE status='closed' AND exit_reason='trail_arm_timeout'
          AND close_time > NOW() - INTERVAL '14 days'
        ORDER BY close_time""")
    out = cur.fetchall()
    conn.close()
    return out


def replay(rows):
    db = sqlite3.connect(CANDLES_DB)
    cur = db.cursor()
    res = {'n': len(rows), 'recovered': [], 'never': [], 'nodata': [], 'partial': []}
    for tid, tok, direction, entry, xp, ct, pnl, sig in rows:
        entry, xp = float(entry), float(xp)
        t0 = int(ct.replace(tzinfo=timezone.utc).timestamp())
        cur.execute(
            'SELECT ts, close FROM candles_1m '
            'WHERE token=? AND ts>=? AND ts<=? AND is_closed=1 ORDER BY ts',
            (tok, t0, t0 + WIN_MIN * 60))
        bars = cur.fetchall()
        if not bars:
            res['nodata'].append(tid)
            continue
        if bars[-1][0] < t0 + (WIN_MIN - 2) * 60:
            res['partial'].append(tid)
        long_ = direction.upper() == 'LONG'
        rec = recovered(entry, long_, [float(b[1]) for b in bars])
        fwd = fwd_pct(xp, float(bars[-1][1]), long_)
        depth = (xp - entry) / entry * 100.0  # signed vs entry (LONG convention)
        if not long_:
            depth = -depth
        (res['recovered'] if rec else res['never']).append(
            (tid, tok, sig, float(pnl), fwd, depth))
    db.close()
    return res


def bucket(rows):
    """Recovery rate by exit depth — the non-vacuous framing."""
    shallow = [r for r in rows if r[5] >= -0.40]
    deep = [r for r in rows if r[5] < -0.40]
    return shallow, deep


def main():
    rows = rows_14d()
    assert all(r[1] for r in rows), 'bad rows'
    res = replay(rows)
    print(f"TAT closes 14d: n={res['n']} (nodata {len(res['nodata'])}, "
          f"partial-window {len(res['partial'])})")
    rec, nev = res['recovered'], res['never']
    print(f"  recovered to entry within {WIN_MIN}m post-close: {len(rec)}")
    for r in rec:
        print(f"    #{r[0]} {r[1]} {r[2][:26]:28s} pnl={r[3]:+.3f} "
              f"depth={r[5]:+.2f}% fwd30m={r[4]:+.2f}%")
    print(f"  never traded back within {WIN_MIN}m: {len(nev)}")
    for r in nev:
        print(f"    #{r[0]} {r[1]} {r[2][:26]:28s} pnl={r[3]:+.3f} "
              f"depth={r[5]:+.2f}% fwd30m={r[4]:+.2f}%")
    allr = rec + nev
    n = len(allr)
    if n:
        for label, grp in (('recovered', rec), ('never', nev)):
            if grp:
                mean = sum(r[4] for r in grp) / len(grp)
                print(f"  mean fwd30m {label}: {mean:+.2f}% (n={len(grp)})")
        shallow, deep = bucket(allr)
        sr = sum(1 for r in shallow if r in rec)
        dr = sum(1 for r in deep if r in rec)
        print(f"  recovery BY EXIT DEPTH (conditioning check): "
              f"depth>=-0.40%: {sr}/{len(shallow)} | depth<-0.40%: {dr}/{len(deep)}")
        print(f"  recovered rate {100.0*len(rec)/n:.1f}%  (n={n}, monitor bar n>=20)")
        print("  NOTE: if the depth split is near-perfect, the raw recovery "
              "rate restates cut depth — cite the bucketed numbers, not 70.6%.")


def selfcheck():
    # predicate unit checks (no candles needed)
    assert recovered(100.0, True, [99.79, 99.9]) is True
    assert recovered(100.0, True, [99.0]) is False
    assert recovered(100.0, True, [99.7]) is False       # -0.30% not recovered
    assert recovered(100.0, False, [100.19]) is True
    assert recovered(100.0, False, [101.0]) is False
    assert fwd_pct(100.0, 101.0, True) > 0
    assert fwd_pct(100.0, 99.0, True) < 0
    assert fwd_pct(100.0, 99.0, False) > 0               # short favors down
    r = rows_14d()
    assert len(r) >= 10, f'expected >=10 TAT closes in 14d, got {len(r)}'
    assert all(x[4] is not None for x in r), 'exit_price null'
    print(f'selfcheck OK: predicate 8/8, {len(r)} TAT closes, exit_price non-null')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        main()
