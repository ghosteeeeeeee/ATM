#!/usr/bin/env python3
"""chop_bleed_kpi.py — OFFICIAL chop-bleed KPI (canonical definition pin).

Pinned by brain_auditor #302 (2026-11-26) from creative #1 of run #301,
after the trailing_activated column was shown to overstate the KPI by 21pt
(7d 94.7% vs official 73.7% — gap cohort = manual path never writes the column).

Canonical definition — do not vary:
  cohort  = closed losers (pnl_usdt < 0) in window
  bleed   = losers with mfe_pct < 0.40 (never reached trail activation)
  dollar  = sum(-pnl of bleed) / sum(-pnl of all losers)
  count   = count(bleed) / count(losers)
  NULL mfe_pct = NOT bleed (NULL count printed beside the KPI, never silent)

Run:  python3 brain/analysis/chop_bleed_kpi.py [days] [--selfcheck]
"""
import sys

import psycopg2

DAYS_DEFAULT = 7


def pg():
    return psycopg2.connect(host='/var/run/postgresql', database='brain',
                            user='postgres')


def kpi(days):
    conn = pg()
    try:
        cur = conn.cursor()
        # psycopg2 param binding for the window (int cast = no injection path)
        cur.execute(
            """
            SELECT COUNT(*)                                        AS n_losers,
                   COUNT(*) FILTER (WHERE mfe_pct IS NULL)         AS n_null,
                   COUNT(*) FILTER (WHERE mfe_pct IS NOT NULL
                                      AND mfe_pct < 0.40)          AS n_bleed,
                   COALESCE(SUM(-pnl_usdt), 0)                     AS total_loss,
                   COALESCE(SUM(-pnl_usdt) FILTER (WHERE mfe_pct
                             IS NOT NULL AND mfe_pct < 0.40), 0)    AS bleed_loss
            FROM trades
            WHERE status = 'closed'
              AND pnl_usdt < 0
              AND close_time > NOW() - make_interval(days => %s)
            """,
            (int(days),),
        )
        n_losers, n_null, n_bleed, total_loss, bleed_loss = cur.fetchone()
    finally:
        conn.close()

    if n_losers == 0:
        return {'days': days, 'n_losers': 0, 'n_bleed': 0, 'n_null_mfe': 0,
                'total_loss': 0.0, 'bleed_loss': 0.0,
                'dollar_share': None, 'count_share': None}
    dollar = float(bleed_loss) / float(total_loss) if total_loss else None
    count = n_bleed / n_losers
    return {
        'days': days,
        'n_losers': n_losers,
        'n_bleed': n_bleed,
        'n_null_mfe': n_null,
        'total_loss': round(float(total_loss), 2),
        'bleed_loss': round(float(bleed_loss), 2),
        'dollar_share': round(dollar, 4) if dollar is not None else None,
        'count_share': round(count, 4),
    }


def selfcheck():
    """Fail loudly if the KPI is out of range. Uses explicit raises (not
    assert) so `python -O` cannot strip the checks."""
    r = kpi(7)
    if r['n_losers'] <= 0:
        raise SystemExit('selfcheck FAIL: no 7d losers — window dead?')
    for key in ('dollar_share', 'count_share'):
        v = r[key]
        if v is None or not (0.0 <= v <= 1.0):
            raise SystemExit(f'selfcheck FAIL: {key}={v} outside [0,1]')
    # Informational only: trailing_activated vs mfe<0.40 counts on the same
    # cohort. They MAY diverge (column historically overstates — do not use
    # the column for KPI math). Equality is fine; this print exists so the
    # divergence is visible, not to assert either way.
    conn = pg()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FILTER (WHERE trailing_activated) AS by_col,
                   COUNT(*) FILTER (WHERE mfe_pct < 0.40)     AS by_kpi
            FROM trades
            WHERE status = 'closed' AND pnl_usdt < 0
              AND close_time > NOW() - INTERVAL '7 days'
            """
        )
        by_col, by_kpi = cur.fetchone()
    finally:
        conn.close()
    print(f'selfcheck PASS  dollar={r["dollar_share"]} '
          f'count={r["count_share"]} null_mfe={r["n_null_mfe"]} '
          f'| column-vs-KPI (informational): trailing_activated={by_col} '
          f'mfe<0.40={by_kpi} — KPI uses mfe only, never the column')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(0 if selfcheck() else 1)
    days = DAYS_DEFAULT
    for a in sys.argv[1:]:
        if a.lstrip('-').isdigit():
            days = abs(int(a))
        else:
            raise SystemExit(f'unknown arg: {a!r} (usage: [days] [--selfcheck])')
    r = kpi(days)
    if r['n_losers'] == 0:
        print(f'chop-bleed KPI {days}d: 0 losers — nothing to measure')
    elif r['dollar_share'] is None:
        print(f'chop-bleed KPI {days}d: losers present but total_loss=0 — '
              f'cannot compute dollar share (count={r["count_share"]:.1%})')
    else:
        print(f'chop-bleed KPI (canonical mfe<0.40) {days}d: '
              f'dollar={r["dollar_share"]:.1%} '
              f'({r["bleed_loss"]}/{r["total_loss"]})  '
              f'count={r["count_share"]:.1%} '
              f'({r["n_bleed"]}/{r["n_losers"]})  '
              f'NULL mfe={r["n_null_mfe"]}')
        print('gate: escalate >=92%; exit-ownership trigger <=70% (x2 windows)')
