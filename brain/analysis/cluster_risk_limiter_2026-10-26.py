#!/usr/bin/env python3
"""cluster_risk_limiter_2026-10-26 — brain_auditor run #163 creative candidate.

WHY THIS EXISTS
  brain/creative_improvements.json has carried a cluster risk limiter 5 times
  (2026-10-03 #207/#214, 2026-10-04 #246/#252/#256) with status
  "suggested / needs backtest" and NO measurement. The only related verdict is
  #132 (2026-10-01) which rejected a DIFFERENT rule: "3+ same-dir within 90s".
  The trade watchdog fired steer-001 this very cycle: "Trade cluster: DYDX + LTC
  — both opened within 20 minutes, correlation risk" (both volume-buildup- SHORT).

RULE UNDER TEST (two arms, measured separately, one variable each)
  A. FAMILY: a signal-family open that is NOT the first open of that family
     within a 15-minute window is a cluster member -> would be blocked.
  B. BOOK: any open that is NOT the first open in the book within a 15-minute
     window (regardless of signal) -> would be blocked.
  Trades opening before the window starts are anchors (never blocked).

PRE-REGISTERED BARS (written before the groups are read)
  B1 blocked n >= 20 at 30d
  B2 blocked cohort net pnl_usdt < 0 at 30d AND 14d AND 7d (same sign, 3/3)
  B3 winner-impact: < 20% of 30d winning trades fall in the blocked cohort
  B4 left-tail Fisher p < 0.05 (blocked WR <= solo/anchor WR), 30d
  B5 delta = (sum of blocked-cohort pnl) still > 0 after adding back a 0.05%
     round-trip fee on each blocked trade's notional (units: pnl_usdt basis,
     never pnl_pct — pnl_pct is LEVERAGED)
  Any arm passing B1-B5 is a CANDIDATE FOR CEO. Nothing ships from here.

SELF-CHECK: python3 brain/analysis/cluster_risk_limiter_2026-10-26.py --selfcheck
"""
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import *  # noqa: F401,F403

import psycopg2

WINDOW_MIN = 15
FEE_PCT = 0.05


def load(days):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, signal, direction, open_time, close_time, pnl_usdt, amount_usdt, status
        FROM trades
        WHERE status='closed' AND open_time > NOW() - INTERVAL %s
          AND pnl_usdt IS NOT NULL AND amount_usdt IS NOT NULL
        ORDER BY open_time
    """, (f'{days} days',))
    rows = cur.fetchall()
    conn.close()
    return rows


def mark(rows, family):
    """Trade ids that are cluster members (an earlier open of the same key
    within WINDOW_MIN). The anchor of a burst stays the first open, so a
    5-trade burst in 15m yields 4 members, not 4 anchors drifting the window."""
    anchor = {}   # key -> open_time of the current window's first open
    out = set()
    for tid, sig, d, ot, ct, pnl, amt, st in rows:
        k = sig if family else '__book__'
        a = anchor.get(k)
        if a is not None and ot - a <= timedelta(minutes=WINDOW_MIN):
            out.add(tid)
        else:
            anchor[k] = ot
    return out


def evaluate(days, family):
    rows = load(days)
    blocked = mark(rows, family)
    tot_n = len(rows)
    tot_w = sum(1 for r in rows if r[5] > 0)
    tot_pnl = sum(float(r[5]) for r in rows)
    b_rows = [r for r in rows if r[0] in blocked]
    a_rows = [r for r in rows if r[0] not in blocked]
    bn, bp = len(b_rows), sum(float(r[5]) for r in b_rows)
    bw = sum(1 for r in b_rows if r[5] > 0)
    aw = sum(1 for r in a_rows if r[5] > 0)
    fee = sum(float(r[6]) * FEE_PCT / 100.0 for r in b_rows)
    return dict(days=days, family=family, tot_n=tot_n, tot_w=tot_w, tot_pnl=round(tot_pnl, 2),
                bn=bn, bw=bw, b_pnl=round(bp, 2), an=len(a_rows), aw=aw,
                a_pnl=round(sum(float(r[5]) for r in a_rows), 2),
                b_wr=round(100.0 * bw / bn, 1) if bn else None,
                a_wr=round(100.0 * aw / len(a_rows), 1) if a_rows else None,
                win_impact=round(100.0 * bw / tot_w, 1) if tot_w else None,
                fee=round(fee, 2), delta_after_fee=round(bp + fee, 2))


def fisher_left(p1, n1, p2, n2):
    """Left-tail Fisher exact: P(blocked WR <= anchor WR) via hypergeometric."""
    from math import comb
    if not n1 or not n2:
        return 1.0
    k1 = round(p1 * n1)
    k2 = round(p2 * n2)
    N, K, n = n1 + n2, k1 + k2, n1
    lo = max(0, n - (N - K))
    hi = min(n, K)
    tot = comb(N, n)
    p = 0.0
    for x in range(lo, min(k1, hi) + 1):
        p += comb(K, x) * comb(N - K, n - x)
    return p / tot


def report(family):
    label = 'A.FAMILY' if family else 'B.BOOK'
    res = {d: evaluate(d, family) for d in (7, 14, 30)}
    r30 = res[30]
    print(f'\n=== ARM {label}  (window {WINDOW_MIN}m) ===')
    for d in (7, 14, 30):
        r = res[d]
        print(f"  {d:>2}d  blocked n={r['bn']:>3} WR={r['b_wr']}% pnl={r['b_pnl']:>7} | "
              f"anchor n={r['an']:>3} WR={r['a_wr']}% pnl={r['a_pnl']:>7} | "
              f"win_impact={r['win_impact']}% fee={r['fee']} delta_after_fee={r['delta_after_fee']}")
    p = fisher_left(r30['b_wr'] / 100.0 if r30['b_wr'] else 0, r30['bn'],
                    r30['a_wr'] / 100.0 if r30['a_wr'] else 0, r30['an'])
    bars = {
        'B1 n>=20 (30d)': r30['bn'] >= 20,
        'B2 same-sign 3/3 (blocked pnl<0)': all(res[d]['b_pnl'] < 0 for d in (7, 14, 30)),
        'B3 winner-impact <20%': (r30['win_impact'] if r30['win_impact'] is not None else 100) < 20,
        'B4 fisher p<0.05': p < 0.05,
        'B5 delta_after_fee>0 (30d)': r30['delta_after_fee'] > 0,
    }
    print(f'  fisher_left p = {p:.4f}')
    for k, v in bars.items():
        print(f'    [{"PASS" if v else "FAIL"}] {k}')
    verdict = 'CANDIDATE FOR CEO' if all(bars.values()) else 'REJECT-WITH-DATA'
    print(f'  -> {verdict}')
    return verdict


def selfcheck():
    from datetime import datetime
    base = datetime(2026, 1, 1, 0, 0)
    rows = [
        (1, 'sigA', 'LONG', base, None, 1.0, 10.0, 'closed'),                      # anchor
        (2, 'sigA', 'LONG', base + timedelta(minutes=5), None, -1.0, 10.0, 'closed'),  # member
        (3, 'sigB', 'LONG', base + timedelta(minutes=6), None, -1.0, 10.0, 'closed'),  # anchor (other family)
        (4, 'sigA', 'LONG', base + timedelta(minutes=40), None, -1.0, 10.0, 'closed'),  # outside 15m -> anchor
    ]
    fam = mark(rows, family=True)
    book = mark(rows, family=False)
    assert fam == {2}, f'family arm wrong: {fam}'          # t+40 > 15m from sigA anchor
    assert book == {2, 3}, f'book arm wrong: {book}'        # t+40 > 15m from book anchor
    # anchor-drift regression guard: t=0,10,20,30 same family. Fixed anchor
    # gives members {t10, t30} (t20 starts a new window); a drifting-anchor
    # implementation would give {t10, t20, t30}.
    rows_drift = [
        (i, 'sigA', 'LONG', base + timedelta(minutes=10 * i), None, 0.0, 10.0, 'closed')
        for i in range(4)
    ]
    assert mark(rows_drift, family=True) == {1, 3}, f'anchor drift: {mark(rows_drift, family=True)}'
    assert fisher_left(0.0, 10, 0.9, 10) < 0.001, 'fisher left-tail broken'
    assert fisher_left(0.9, 10, 0.1, 10) > 0.99, 'fisher left-tail symmetric broken'
    # mid-range pin: P(X<=2) for Hypergeom(N=10,K=5,n=5) = 53/70 exactly.
    # Catches off-by-one in the summation bound that the extreme cases miss.
    assert abs(fisher_left(0.5, 4, 0.5, 4) - 53.0 / 70.0) < 1e-12, 'fisher mid-range sum wrong'
    print('ASSERT PASS: mark() family/book split + anchor-drift guard + fisher_left extremes/mid')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        report(family=True)
        report(family=False)
