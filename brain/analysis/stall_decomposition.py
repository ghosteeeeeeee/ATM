#!/usr/bin/env python3
"""
stall_decomposition.py — brain_auditor run #248 (2026-11-11)

Routes every dollar of exit-reason bleed to the RIGHT owner:

  stall   = mfe_pct < 0.40   never reached trail activation -> ENTRY quality
  armgap  = mfe_pct >= 0.40 AND trailing_activated = False   reached activation,
            never armed          -> UGB-PT / trail WIRING (bypass signals)
  armed   = trailing_activated = True                        -> trail PARAMS

Why: chop-bleed share (#139 KPI) aggregates all exits into one number, so it
says "entry problem" but cannot tell WHICH exit to fix or which side of an
existing amplify proposal the money is on. Run #247 registered
amplify-ugb-bypass-armgap against the armgap pool; this script measures how
big that pool actually is next to the stall pool.

Run: python3 brain/analysis/stall_decomposition.py [days] [--selfcheck]
"""
import sys

import psycopg2

BLEED_EXITS = ('atr_sl_hit', 'hard_max_loss')


def pg():
    return psycopg2.connect(host='/var/run/postgresql', database='brain',
                            user='postgres')


def decompose(days):
    conn = pg()
    try:
        cur = conn.cursor()
        win = (BLEED_EXITS, f'{days} days')
        cur.execute(
            """
            SELECT exit_reason,
                   CASE
                     WHEN trailing_activated THEN 'armed'
                     WHEN COALESCE(mfe_pct,0) >= 0.40 THEN 'armgap'
                     ELSE 'stall'
                   END AS cohort,
                   COUNT(*) n,
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)
                         /COUNT(*),1) wr,
                   ROUND(SUM(pnl_usdt)::numeric,2) pnl
            FROM trades
            WHERE status='closed' AND exit_reason IN %s
              AND close_time > NOW() - INTERVAL %s
            GROUP BY 1,2 ORDER BY 1, 5
            """, win)
        rows = cur.fetchall()

        cur.execute(
            """
            SELECT signal, COUNT(*), ROUND(SUM(pnl_usdt)::numeric,2)
            FROM trades
            WHERE status='closed' AND exit_reason IN %s
              AND COALESCE(mfe_pct,0) < 0.40
              AND trailing_activated = False
              AND close_time > NOW() - INTERVAL %s
            GROUP BY 1 ORDER BY 3 ASC LIMIT 10
            """, win)
        stall_by_signal = cur.fetchall()
    finally:
        conn.close()

    totals = {}
    for _er, cohort, n, _wr, pnl in rows:
        t = totals.setdefault(cohort, [0, 0.0])
        t[0] += n
        t[1] += float(pnl)

    print(f"stall_decomposition — last {days}d, exits {', '.join(BLEED_EXITS)}")
    print(f"{'cohort':10} {'n':>5} {'pnl':>9}")
    for cohort in ('stall', 'armgap', 'armed'):
        if cohort in totals:
            n, pnl = totals[cohort]
            print(f"{cohort:10} {n:>5} {pnl:>9.2f}")
    print("\nper exit_reason x cohort:")
    for er, cohort, n, wr, pnl in rows:
        print(f"  {er:16} {cohort:8} n={n:<4} wr={wr:<5} pnl={pnl}")
    print("\ntop stall feeders (mfe<0.40, never armed):")
    for sig, n, pnl in stall_by_signal:
        print(f"  {sig:40} n={n:<4} pnl={pnl}")
    return rows, totals, stall_by_signal


def selfcheck():
    rows, totals, feeders = decompose(14)
    cohorts = {c for _er, c, *_ in rows}
    assert 'stall' in cohorts, 'stall cohort missing'
    assert 'armgap' in cohorts, 'armgap cohort missing'
    # 'armed' is legitimately empty for these two exits: once the trail arms,
    # profit-monster-trail owns the exit (14d observation, run #248).
    n_sum = sum(v[0] for v in totals.values())
    raw = sum(r[2] for r in rows)
    assert n_sum == raw, f'n mismatch {n_sum} vs {raw}'
    for cohort, (n, pnl) in totals.items():
        assert n > 0, f'{cohort} empty'
    # units guard: pnl is pnl_usdt (never pnl_pct)
    assert all(abs(p) < 1000 for _e, _c, _n, _w, p in rows), 'pnl out of range'
    print('\nSELFCHECK PASS '
          f'(stall={totals.get("stall", [0, 0])[0]}T '
          f'armgap={totals.get("armgap", [0, 0])[0]}T '
          f'armed={totals.get("armed", [0, 0])[0]}T)')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        days = 14
        for a in sys.argv[1:]:
            if a.isdigit():
                days = int(a)
        decompose(days)
