#!/usr/bin/env python3
"""tape_state_arm_census_2026-10-28.py — run #191's named next lever, UNLOCKED.

WHY THIS IS NOT A DUPLICATE OF #191's METADATA CENSUS
  #191 tested 14 DETECT-stamped fields (momentum_state, volume_spike, ...). It
  rejected them. btc_ema300_* did not exist then — it shipped 2026-10-28 00:50Z
  and was the named follow-up: "tape-state arm census once n>=100 stamped trades".

WHY WE DO NOT WAIT FOR n>=100 STAMPED
  The first stamped open was PURR #16452 at 2026-10-28 02:06Z. At ~7 trades/day
  the stamped sample would take ~2 weeks to reach 100. But the live stamp IS the
  "latest BTC 1m continuum row with age<=600s" (decider_run.py:5456-5474), and
  data/continuum.db holds BTC 1m rows for 78 consecutive days (2026-08-12..now;
  verified this run: 0 COMPLETE days below 1000 rows — only the current partial
  day 2026-10-28 is below, and the row count grows every minute). So the exact same
  fields can be reconstructed at every historical open_time: same source table,
  same staleness guard, n~700 instead of n=5.

  This is a HISTORICAL RECONSTRUCTION, not the stamped sample. The stamped subset
  is a subset of this one. Disposition rule: if a test passes here it still has
  to clear the same bar on the stamped subset at n>=100 before any enforcement.

NOT-ALREADY-IN-CONSTANTS (checked this run)
  hermes_constants has SHORT_CONTINUUM_FILTER (state_score based), SHORT-MIDBAND
  (RSI), BTC-CRASH / BTC-ACCEL (move based). No gate reads BTC ema300_position,
  trend_quality, ema300_duration or dist_pct. brain/analysis/midband_ema300_cond_
  2026-10-25.py already measured ema300_position vs PnL midband-scoped and
  REFUTED it (bleed sits AT/ABOVE, blocked set was profitable) — this script
  measures a different endpoint (ARM rate) on the whole book.

PRE-DECLARED TESTS (10 — written into this docstring BEFORE the first run;
Bonferroni bar = 0.05/10 = 0.005)
  T1  ALL       pos == BELOW  vs {AT, ABOVE}
  T2  ALL       pos == ABOVE  vs {AT, BELOW}
  T3  LONG      pos == BELOW  vs {AT, ABOVE}
  T4  LONG      pos == ABOVE  vs {AT, BELOW}
  T5  SHORT     pos == ABOVE  vs {AT, BELOW}
  T6  SHORT     pos == BELOW  vs {AT, ABOVE}
  T7  ALL       trend bear (STRONG_DOWN/DOWN) vs bull (STRONG_UP/UP)
  T8  ALL       ema300_duration >= 60min (established side) vs < 60min
  T9  ALL       tape ALIGNED with trade (LONG&dist>0 | SHORT&dist<0) vs counter
  T10 ALL       |dist| >= 0.15% (extended from line) vs < 0.15% (at/near line)

PRIMARY endpoint = ARM (mfe_pct >= 0.40). SECONDARY = pnl / WR (reported, and
used for winner-kill, but never sufficient on its own to ship).

SHIP BAR (locked #191, unchanged)
  30d same-sign (test direction identical at 30d AND 14d AND 7d)
  AND raw p < 0.05 AND min-p clears Bonferroni 0.005
  AND winner-kill < 20% for the implied block
  AND n >= 20 in BOTH cells at 30d
  AND not-already-in-constants (checked above)
  FAIL ANY => monitor, no gate.

Usage:
  python3 brain/analysis/tape_state_arm_census_2026-10-28.py [--selfcheck]
"""
import math
import os
import sqlite3
import sys
from datetime import timezone
from math import comb

import psycopg2

HERE = __file__.rsplit('/', 1)[0]
CDB = HERE + '/../../data/continuum.db'

# no hardcoded tunables (AGENTS): duration/streak are stored in state TICKs
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
from continuum_constants import TICK_INTERVAL  # noqa: E402

ARM_PCT = 0.40          # PM_TRAIL_ACTIVATE_PCT
JOIN_SLACK_S = 600      # matches decider_run.py:5461 live stamp guard (< 600, not <=)
BONFERRONI = 0.05 / 10

TESTS = [
    ('T1',  'ALL',   'pos==BELOW vs {AT,ABOVE}'),
    ('T2',  'ALL',   'pos==ABOVE vs {AT,BELOW}'),
    ('T3',  'LONG',  'pos==BELOW vs {AT,ABOVE}'),
    ('T4',  'LONG',  'pos==ABOVE vs {AT,BELOW}'),
    ('T5',  'SHORT', 'pos==ABOVE vs {AT,BELOW}'),
    ('T6',  'SHORT', 'pos==BELOW vs {AT,ABOVE}'),
    ('T7',  'ALL',   'trend bear vs bull'),
    ('T8',  'ALL',   'duration >=60m vs <60m'),
    ('T9',  'ALL',   'tape aligned vs counter'),
    ('T10', 'ALL',   '|dist| >=0.15% vs <0.15%'),
]


def fisher_two_sided(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return 1.0

    def prob(x):
        r1, c1 = a + b, a + c
        lo, hi = max(0, r1 + c1 - n), min(r1, c1)
        if x < lo or x > hi:
            return 0.0
        return comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)

    p0 = prob(a)
    lo, hi = max(0, (a + b) + (a + c) - n), min(a + b, a + c)
    total = sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p0 + 1e-12)
    return min(1.0, total)


def load(days):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, open_time, pnl_usdt, mfe_pct, signal
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '%s days'
          AND open_time IS NOT NULL AND mfe_pct IS NOT NULL
        ORDER BY open_time
    """ % (days,))
    out = []
    for tid, tok, d, ot, pnl, mfe, sig in cur.fetchall():
        out.append(dict(id=tid, tok=tok, d=(d or '').upper(), ot=ot,
                        pnl=float(pnl or 0), mfe=float(mfe), sig=sig))
    conn.close()
    return out


def tape_at(open_time):
    """Same fields the live stamp writes, reconstructed at open_time."""
    ts = int(open_time.replace(tzinfo=timezone.utc).timestamp())
    con = sqlite3.connect(CDB)
    try:
        row = con.execute(
            "SELECT price, ema300, ema300_position, ema300_duration, trend_quality, "
            "consecutive_above, consecutive_below, ts FROM continuum_states "
            "WHERE token='BTC' AND timeframe='1m' AND ts<=? ORDER BY ts DESC LIMIT 1",
            (ts,)).fetchone()
    finally:
        con.close()
    if not row or ts - row[7] >= JOIN_SLACK_S:
        return None
    price, ema, pos, dur, trend, ca, cb, _ = row
    dist = None
    if price is not None and ema:
        dist = (float(price) - float(ema)) / float(ema) * 100.0
    streak = 0
    if pos == 'ABOVE':
        streak = ca or 0
    elif pos == 'BELOW':
        streak = cb or 0
    return dict(pos=pos, dur_min=(dur or 0) * TICK_INTERVAL / 60.0,
                trend=trend, dist=dist, streak=streak, age_s=ts - row[7])


def attach(rows):
    joined, miss = [], 0
    for r in rows:
        t = tape_at(r['ot'])
        if t is None:
            miss += 1
            continue
        r2 = dict(r)
        r2.update(t)
        joined.append(r2)
    return joined, miss


def cell(rows):
    n = len(rows)
    arm = sum(1 for r in rows if r['mfe'] >= ARM_PCT)
    win = sum(1 for r in rows if r['pnl'] > 0)
    pnl = sum(r['pnl'] for r in rows)
    return dict(n=n, arm=arm, arm_pct=100.0 * arm / n if n else 0.0,
                w=win, wr=100.0 * win / n if n else 0.0, pnl=round(pnl, 2))


def split(rows, tid, scope):
    """Return (cellA_rows, complement_rows). cellA = the named condition."""
    base = [r for r in rows if scope == 'ALL' or r['d'] == scope]
    if tid in ('T1', 'T3', 'T6'):
        a = [r for r in base if r['pos'] == 'BELOW']
    elif tid in ('T2', 'T4', 'T5'):
        a = [r for r in base if r['pos'] == 'ABOVE']
    elif tid == 'T7':
        a = [r for r in base if r['trend'] in ('STRONG_DOWN', 'DOWN')]
        base = [r for r in base if r['trend'] in ('STRONG_DOWN', 'DOWN',
                                                  'STRONG_UP', 'UP')]
    elif tid == 'T8':
        a = [r for r in base if r['dur_min'] >= 60]
    elif tid == 'T9':
        a = [r for r in base
             if (r['d'] == 'LONG' and r['dist'] is not None and r['dist'] > 0)
             or (r['d'] == 'SHORT' and r['dist'] is not None and r['dist'] < 0)]
    elif tid == 'T10':
        a = [r for r in base if r['dist'] is not None and abs(r['dist']) >= 0.15]
    else:
        raise ValueError(tid)
    aset = {r['id'] for r in a}
    if tid in ('T9', 'T10'):
        base = [r for r in base if r['dist'] is not None]
    b = [r for r in base if r['id'] not in aset]
    return a, b


def evaluate(days):
    rows, miss = attach(load(days))
    total_win = sum(1 for r in rows if r['pnl'] > 0)
    out = []
    for tid, scope, desc in TESTS:
        a, b = split(rows, tid, scope)
        ca, cb = cell(a), cell(b)
        if ca['n'] < 5 or cb['n'] < 5:
            p = 1.0
        else:
            p = fisher_two_sided(ca['arm'], ca['n'] - ca['arm'],
                                 cb['arm'], cb['n'] - cb['arm'])
        # candidate gate = block the LOWER-ARM cell (the chop cell we would gate).
        # fk = that cell's winners / all winners in window (def-A, run #86 pin).
        block = a if ca['arm_pct'] <= cb['arm_pct'] else b
        fk = round(100.0 * sum(1 for r in block if r['pnl'] > 0) / total_win,
                   1) if total_win else 0.0
        blocked_side = 'A' if ca['arm_pct'] <= cb['arm_pct'] else 'B'
        out.append(dict(tid=tid, scope=scope, desc=desc, days=days,
                        a=ca, b=cb, p=round(p, 5), fk=fk, block=blocked_side,
                        miss=miss, n_rows=len(rows)))
    return out


def sign_of(res):
    """Which side arms more: +1 => cellA arms MORE than complement."""
    return 1 if res['a']['arm_pct'] > res['b']['arm_pct'] else -1


def run(verbose=True):
    per = {d: evaluate(d) for d in (7, 14, 30)}
    header = (f"{'ID':4s} {'scope':6s} {'cellA n/arm%/pnl':>26s} "
              f"{'complement n/arm%/pnl':>26s} {'p':>8s} {'fk%':>6s}{'':2s} "
              f"{'7d':>6s} {'14d':>6s} {'30d':>6s}")
    print('=== TAPE-STATE ARM CENSUS (BTC 1m continuum at open_time) ===')
    print('join slack <=600s (live stamp rule) · ARM = mfe_pct >= 0.40')
    print(header)
    results = []
    for i, (tid, scope, desc) in enumerate(TESTS):
        r7, r14, r30 = per[7][i], per[14][i], per[30][i]
        same = sign_of(r7) == sign_of(r14) == sign_of(r30)
        a30, b30 = r30['a'], r30['b']
        bars = dict(
            same_sign=same,
            p_lt05=r30['p'] < 0.05,
            bonf=r30['p'] < BONFERRONI,
            n20=a30['n'] >= 20 and b30['n'] >= 20,
            fk_lt20=r30['fk'] < 20.0,
        )
        verdict = 'PASS' if all(bars.values()) else \
            'FAIL:' + ','.join(k for k, v in bars.items() if not v)
        if verbose:
            print(f"{tid:4s} {scope:6s} "
                  f"{a30['n']:>4d} {a30['arm_pct']:>6.1f}% {a30['pnl']:+7.2f}   "
                  f"{b30['n']:>4d} {b30['arm_pct']:>6.1f}% {b30['pnl']:+7.2f}   "
                  f"{r30['p']:>8.5f} {r30['fk']:>6.1f}{'A' if r30['block'] == 'A' else 'B':>2s}  "
                  f"{'+' if sign_of(r7) > 0 else '-':>6s} "
                  f"{'+' if sign_of(r14) > 0 else '-':>6s} "
                  f"{'+' if sign_of(r30) > 0 else '-':>6s}  {verdict}")
        results.append(dict(tid=tid, scope=scope, desc=desc, bars=bars,
                            verdict=verdict, r7=r7, r14=r14, r30=r30))
    npass = sum(1 for r in results if r['verdict'] == 'PASS')
    print(f"\nBonferroni bar = {BONFERRONI:.4f} over {len(TESTS)} pre-declared tests")
    print(f"tests passing ALL bars: {npass}/{len(TESTS)}")
    cov7 = per[7][0]['n_rows']
    print(f"coverage: 7d joined={cov7} (missed={per[7][0]['miss']})")
    return results


def selfcheck():
    # fisher sanity: symmetric, extremes
    assert abs(fisher_two_sided(8, 2, 2, 8) - fisher_two_sided(2, 8, 8, 2)) < 1e-12
    assert fisher_two_sided(20, 0, 0, 20) < 0.0001
    assert fisher_two_sided(5, 5, 5, 5) > 0.9
    p = fisher_two_sided(8, 2, 2, 8)
    assert 0.01 < p < 0.05, p
    print(f'  fisher two-sided [[8,2],[2,8]] = {p:.5f} in (0.01,0.05) OK')

    rows, miss = attach(load(7))
    assert rows, 'no rows joined'
    cov = 100.0 * len(rows) / max(1, len(rows) + miss)
    assert cov >= 90.0, f'join coverage {cov:.1f}% < 90%'
    print(f'  7d join coverage {cov:.1f}% ({len(rows)} joined, {miss} miss) OK')

    # every joined row carries a usable pos + finite dist
    assert all(r['pos'] in ('ABOVE', 'AT', 'BELOW') for r in rows)
    assert all(r['dist'] is not None for r in rows)
    assert all(r['dur_min'] >= 0 for r in rows)

    # hand-recount T1 on the joined rows must equal evaluate(7)[0]
    a = [r for r in rows if r['pos'] == 'BELOW']
    b = [r for r in rows if r['pos'] != 'BELOW']
    ca, cb = cell(a), cell(b)
    ev = evaluate(7)[0]
    assert ev['tid'] == 'T1'
    assert (ca['n'], ca['arm'], ca['w']) == (ev['a']['n'], ev['a']['arm'], ev['a']['w'])
    assert (cb['n'], cb['arm'], cb['w']) == (ev['b']['n'], ev['b']['arm'], ev['b']['w'])
    print(f'  T1 hand-recount matches evaluate(): A n={ca["n"]} arm={ca["arm"]} '
          f'W={ca["w"]} | B n={cb["n"]} arm={cb["arm"]} W={cb["w"]} OK')

    # winner-kill must be for the cell we would actually block (lower arm side),
    # not blindly cellA — a fk on the GOOD side is meaningless.
    tot_w = sum(1 for r in rows if r['pnl'] > 0)
    blk = a if ca['arm_pct'] <= cb['arm_pct'] else b
    fk_hand = round(100.0 * sum(1 for r in blk if r['pnl'] > 0) / tot_w, 1)
    assert ev['block'] == ('A' if ca['arm_pct'] <= cb['arm_pct'] else 'B')
    assert ev['fk'] == fk_hand, (ev['fk'], fk_hand)
    print(f'  fk targets the blocked (lower-arm) side: {ev["block"]} '
          f'{ev["fk"]}% == hand {fk_hand}% OK')

    # determinism
    ev2 = evaluate(7)[0]
    assert (ev2['a']['n'], ev2['p']) == (ev['a']['n'], ev['p'])

    # duration unit guard (TICK_INTERVAL=30s, #139 unit fix): a 60m pin = 120 ticks
    assert 120 * TICK_INTERVAL / 60.0 == 60.0  # T8 60-min pin == 120 state ticks
    # ARM threshold guard
    assert ARM_PCT == 0.40

    # pre-declared test table is exactly what the docstring promises
    assert [t[0] for t in TESTS] == [f'T{i}' for i in range(1, 11)]

    print('ASSERT PASS: tape_state_arm_census selfcheck '
          '(fisher, coverage, hand-recount, determinism, units, test table)')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
        sys.exit(0)
    run()
