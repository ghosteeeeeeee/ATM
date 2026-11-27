#!/usr/bin/env python3
"""
prearm_day7_read_2026-11-27.py — brain_auditor run #310

Day-7 read of PREARM_LOCK_ENFORCE (live 2026-11-20 01:26Z, commit 9cdf09e4)
against the four bars pre-registered in disposition `prearm-enforce-day7-read`.

Bar 1  fk via full walk: share of prearm exits whose NORMAL exit-engine outcome
       would have been a WINNER < 20% (baseline 13.9%), n >= 15 distinct exits
Bar 2  realized net (pnl_usdt) >= 0 across the enforce cohort
Bar 3  peak-source divergence: pos-peak vs trades.highest_price vs 1m candle
       peak for EVERY fire; >= 2 fires with DB-or-candle peak >= PM_TRAIL_ACTIVATE
       (0.40)  ->  GUARD proposal owed to CEO (never unilateral)
Bar 4  14d same-sign vs walk

This script implements bars 1(reach-proxy)/2/3/4 with 1m candles. It reports
the reach-proxy for bar 1 and LABELS it: reach != winner-fk (the disposition
bar wants the live exit-engine outcome). n < 15 blocks a ship either way.

Run: python3 brain/analysis/prearm_day7_read_2026-11-27.py [--selfcheck]
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'scripts'))
from paths import HERMES_DATA  # noqa: E402

CANDLES = os.path.join(HERMES_DATA, 'candles.db')
ENFORCE_TS = '2026-11-20 01:26:00'
ARM_PCT = 0.40          # PM_TRAIL_ACTIVATE
FWD_MIN = 90             # minutes walked past close_time
Q = """
SELECT id, token, signal, direction, pnl_usdt, mfe_pct, mfe_price,
       highest_price, lowest_price,
       entry_price, exit_price, open_time, close_time, amount_usdt
FROM trades
WHERE status='closed' AND exit_reason='prearm_lock' AND open_time > %s
ORDER BY close_time
"""


def fires():
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                            user='postgres')
    cur = conn.cursor()
    cur.execute(Q, (ENFORCE_TS,))
    rows = cur.fetchall()
    conn.close()
    return rows


def candle_peak(db, token, t0, t1):
    """Favorable peak % vs entry between two datetimes (epoch seconds)."""
    hi = db.execute(
        "SELECT MAX(high), MIN(low) FROM candles_1m "
        "WHERE token=? AND ts>=? AND ts<?",
        (token, int(t0.timestamp()), int(t1.timestamp()))).fetchone()
    return hi


def pct(fav, entry, direction):
    """fav = (raw_max_high, raw_min_low) -> favorable peak % vs entry."""
    mx, mn = fav
    if mx is None:
        return None
    if direction == 'LONG':
        return (mx / entry - 1.0) * 100.0
    return (1.0 - mn / entry) * 100.0


def main():
    import datetime as dt
    rows = fires()
    db = sqlite3.connect(CANDLES)
    out = []
    for (tid, tok, sig, direc, pnl, mfe, mfe_price, hp, lp,
         entry, exitp, ot, ct, amt) in rows:
        entry = float(entry)
        hold = pct(candle_peak(db, tok, ot, ct), entry, direc)
        fwd_end = ct + dt.timedelta(minutes=FWD_MIN)
        fwd = pct(candle_peak(db, tok, ct, fwd_end), entry, direc)
        # trades.highest_price is a RAW price: favorable only for LONG.
        raw = float(hp) if direc == 'LONG' and hp else (float(lp) if lp else None)
        raw_fav = ((raw / entry - 1.0) * 100.0) if raw else None
        out.append(dict(id=tid, tok=tok, sig=sig, dir=direc, pnl=float(pnl),
                        db_mfe=float(mfe or 0),
                        hp_pct=raw_fav,
                        candle_hold=hold, candle_fwd=fwd,
                        reach=(fwd is not None and fwd >= ARM_PCT)))
    db.close()

    n = len(out)
    net = sum(o['pnl'] for o in out)
    db_ge = sum(1 for o in out if o['db_mfe'] >= ARM_PCT)
    hp_ge = sum(1 for o in out if o['hp_pct'] is not None and o['hp_pct'] >= ARM_PCT)
    can_ge = sum(1 for o in out
                 if o['candle_hold'] is not None and o['candle_hold'] >= ARM_PCT)
    union = sum(1 for o in out
                if (o['db_mfe'] >= ARM_PCT)
                or (o['hp_pct'] is not None and o['hp_pct'] >= ARM_PCT)
                or (o['candle_hold'] is not None and o['candle_hold'] >= ARM_PCT))
    reach = sum(1 for o in out if o['reach'])

    print(f"prearm_lock enforce fires since {ENFORCE_TS}: n={n}")
    print(f"bar1  n>=15 distinct exits ....... {'MET' if n >= 15 else 'NOT MET'} (n={n})")
    print(f"bar1  fk reach-proxy (+{ARM_PCT}% fwd {FWD_MIN}m) = {reach}/{n}"
          f" = {100.0 * reach / n:.1f}%  {'<20% PASS' if n and reach / n < 0.20 else '>=20% FAIL'}")
    print(f"bar2  realized net ............... {net:+.3f} "
          f"{'PASS' if net >= 0 else 'FAIL'} (avg {net / n:+.4f})")
    print(f"bar3  peak >= {ARM_PCT}%:  DB mfe {db_ge} | trades.highest_price {hp_ge}"
          f" | 1m candle hold {can_ge} | union {union} -> "
          f"{'TRIPS (>=2) => GUARD proposal owed to CEO' if union >= 2 else 'does not trip'}")
    print(f"bar4  14d same-sign: cohort is 7d-old -> rerun at 14d (2026-12-04)")
    print()
    for o in sorted(out, key=lambda x: x['id']):
        print(f"  {o['id']} {o['tok']:<7} {o['dir']:<5} pnl={o['pnl']:+.3f} "
              f"db_mfe={o['db_mfe']:.3f} hp%={(o['hp_pct'] if o['hp_pct'] is not None else float('nan')):+.3f} "
              f"cand_hold%={(o['candle_hold'] if o['candle_hold'] is not None else float('nan')):+.3f} "
              f"cand_fwd%={(o['candle_fwd'] if o['candle_fwd'] is not None else float('nan')):+.3f} "
              f"reach={'Y' if o['reach'] else 'n'}")
    return dict(n=n, net=net, db_ge=db_ge, hp_ge=hp_ge, can_ge=can_ge,
                union=union, reach=reach)


def selfcheck():
    r = main()
    assert r['n'] == 12, f"expected 12 enforce fires, got {r['n']}"
    assert abs(r['net'] - (-0.13)) < 0.011, f"net drift: {r['net']}"
    assert r['union'] >= 2, "bar3 should trip on the documented #17023/#17037 pair"
    print("SELF-CHECK PASS")


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        main()
