#!/usr/bin/env python3
"""Conditional mid-band LONG block: meta_rsi 45-64 AND BTC 1m continuum BELOW EMA300.

Background: blanket mid-band LONG block (rsi 45-64) FAILS the fk<20% bar (fkA 38.6%,
run #138). The standing watchdog steer (age>=6 cycles) is NARROWER: block only while
BTC 1m holds below continuum EMA300. This script measures the compound condition.

Pre-registered bars (stated before running — AGENTS p<0.05 + house bars):
  blocked n>=20 | net save > 0 | fkA < 20% | both halves same sign | binom p<0.05
  | 7d/14d/30d same sign (OOS)
fkA = blocked winners / all LONG winners in the same window (def-A, run #86 pin).

Sources: PostgreSQL brain.trades (_signal_metadata->>'rsi_14' = watchdog meta_rsi,
DRIFT-E safe) x data/continuum_states (BTC 1m ema300_position) joined at open_time.

Self-check: python3 brain/analysis/midband_ema300_cond_2026-10-25.py --selfcheck
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone

import psycopg2

BAND_LO, BAND_HI = 45, 64          # hermes_constants: LONG mid-band (inclusive)
JOIN_SLACK_S = 180                 # continuum state must be <=3min older than open_time
HERE = __file__.rsplit('/', 1)[0]
CDB = HERE + '/../../data/continuum.db'


def btc_pos_at(open_time):
    """BTC 1m ema300_position (ABOVE/AT/BELOW) at trade open; None if no fresh state."""
    ts = int(open_time.replace(tzinfo=timezone.utc).timestamp())
    con = sqlite3.connect(CDB)
    try:
        row = con.execute(
            "SELECT ema300_position, ts FROM continuum_states "
            "WHERE token='BTC' AND timeframe='1m' AND ts<=? ORDER BY ts DESC LIMIT 1",
            (ts,)).fetchone()
    finally:
        con.close()
    if not row or ts - row[1] > JOIN_SLACK_S:
        return None
    return row[0]


def load(days):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT trade_id, token, signal, direction, open_time, pnl_usdt,
               _signal_metadata::text
        FROM trades
        WHERE status='closed' AND direction='LONG'
          AND close_time > NOW() - INTERVAL '%d days'
        ORDER BY open_time""" % days)
    rows = cur.fetchall()
    cur.execute("""
        SELECT COUNT(*), SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END), COALESCE(SUM(pnl_usdt),0)
        FROM trades
        WHERE status='closed' AND direction='LONG'
          AND close_time > NOW() - INTERVAL '%d days'""" % days)
    base_n, base_w, base_pnl = cur.fetchone()
    conn.close()

    out = []
    for tid, tok, sig, direction, ot, pnl, meta_txt in rows:
        rsi = None
        try:
            m = json.loads(meta_txt) if meta_txt else None
            if isinstance(m, dict) and m.get('rsi_14') is not None:
                rsi = float(m['rsi_14'])
        except (ValueError, TypeError):
            rsi = None
        out.append(dict(trade_id=tid, token=tok, signal=sig, open_time=ot,
                        pnl=float(pnl), rsi=rsi, pos=btc_pos_at(ot) if rsi is not None else None))
    return out, base_n, base_w, float(base_pnl)


def stats(rows):
    n = len(rows)
    w = sum(1 for r in rows if r['pnl'] > 0)
    return n, w, (100.0 * w / n if n else 0.0), round(sum(r['pnl'] for r in rows), 2)


def binom_p(w, n, p0):
    """one-sided P(X<=w) under H0: win prob = p0 (blocked set should win LESS than base)."""
    if n == 0:
        return 1.0
    from math import comb
    return sum(comb(n, k) * p0**k * (1 - p0)**(n - k) for k in range(0, w + 1))


def evaluate(days, verbose=True):
    trades, base_n, base_w, base_pnl = load(days)
    band = [t for t in trades if t['rsi'] is not None and BAND_LO <= t['rsi'] <= BAND_HI]
    band_join = [t for t in band if t['pos'] is not None]
    blocked = [t for t in band_join if t['pos'] == 'BELOW']
    above = [t for t in band_join if t['pos'] != 'BELOW']

    base_wr = (base_w / base_n) if base_n else 0.0
    n, w, wr, pnl = stats(blocked)
    # halves by open_time
    mid = len(blocked) // 2
    order = sorted(blocked, key=lambda r: r['open_time'])
    h1, h2 = order[:mid], order[mid:]
    _, _, _, p1 = stats(h1)
    _, _, _, p2 = stats(h2)
    save = round(-pnl, 2)                     # blocking a net-negative cohort saves money
    fk_a = round(100.0 * w / base_w, 1) if base_w else 0.0
    p = binom_p(w, n, base_wr) if n else 1.0

    bars = dict(n_ge_20=n >= 20, save_pos=save > 0, fkA_lt20=fk_a < 20.0,
                halves=(p1 < 0 and p2 < 0), p_lt05=p < 0.05)
    verdict = 'PASS' if all(bars.values()) else 'FAIL: ' + ','.join(k for k, v in bars.items() if not v)

    # inverted counterfactual: block the AT/ABOVE cell instead (the steer backwards test)
    an, aw, awr, apnl = stats(above)
    asave = round(-apnl, 2)
    afk = round(100.0 * aw / base_w, 1) if base_w else 0.0
    ap = binom_p(aw, an, base_wr) if an else 1.0

    if verbose:
        print(f"=== {days}d  meta_rsi {BAND_LO}-{BAND_HI} LONG x BTC-1m-ema300 ===")
        print(f"  LONG base: n={base_n} W={base_w} WR={100.0*base_wr:.1f}% pnl={base_pnl:+.2f}")
        print(f"  band n={len(band)} with ema300 join={len(band_join)} (no-join {len(band)-len(band_join)})")
        print(f"  band+BELOW (steer's blocked set): n={n} W={w} WR={wr:.1f}% pnl={pnl:+.2f} "
              f"| halves {p1:+.2f}/{p2:+.2f}")
        print(f"  band+AT/ABOVE (steer's kept set): n={an} W={aw} WR={awr:.1f}% pnl={apnl:+.2f}")
        print(f"  BLOCK-BELOW:  save={save:+.2f} fkA={fk_a}% p={p:.4f} -> {verdict}")
        print(f"  BLOCK-AT/ABOVE (inverted): save={asave:+.2f} fkA={afk}% p={ap:.4f} "
              f"-> {'PASS' if (an>=20 and asave>0 and afk<20 and ap<0.05) else 'FAIL'}")
    return dict(days=days, blocked_n=n, blocked_w=w, blocked_pnl=pnl, save=save,
                fkA=fk_a, p=round(p, 4), verdict=verdict, kept_n=len(above),
                kept_pnl=stats(above)[3], bars=bars, base_pnl=base_pnl,
                inv_n=an, inv_w=aw, inv_pnl=apnl, inv_save=asave, inv_fkA=afk, inv_p=round(ap, 4))


def selfcheck():
    trades, base_n, base_w, _base_pnl = load(7)
    assert base_n > 20, base_n
    joined = [t for t in trades if t['rsi'] is not None and t['pos'] is not None]
    assert joined, "ema300 join produced 0 rows — continuum table empty or slack too tight"
    pos = {t['pos'] for t in joined}
    assert pos & {'ABOVE', 'BELOW'}, pos
    # determinism: same call twice = same cohort size
    assert len(joined) == len([t for t in load(7)[0] if t['rsi'] is not None and t['pos'] is not None])
    print(f"selfcheck PASS: base_n={base_n} joined={len(joined)} positions={sorted(pos)}")


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
        sys.exit(0)
    results = [evaluate(d) for d in (7, 14, 30)]
    same_sign = len({r['verdict'].split(':')[0] for r in results}) == 1
    print(f"\nOOS across 7/14/30d: {'SAME verdict' if same_sign else 'DIFFERS'}")
