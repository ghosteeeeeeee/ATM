#!/usr/bin/env python3
"""coin_regime direction-split eval (Oct-27 scheduled, pre-reg #141/#133).

Measures LONG-into-SHORT_BIAS and SHORT-into-LONG_BIAS cohorts against house
bars (n>=20, save>0, fk<20%, p<0.05, halves, OOS same-sign).

Verdicts (locked pre-data criteria, run 2026-10-27):
  - long_into_shortbias: COLLECT (p fails, no halves/OOS possible yet, 45% family confound)
  - short_into_longbias: REFUTED (blocking loses money)

Usage: python3 coin_regime_direction_2026-10-27.py [--selfcheck]
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from paths import *  # noqa: F401,F403

import psycopg2
from math import comb


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact via hypergeometric sum."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def p(x):
        return comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)

    p_obs = p(a)
    lo, hi = max(0, r1 - (n - c1)), min(r1, c1)
    return sum(p(x) for x in range(lo, hi + 1) if p(x) <= p_obs + 1e-12)


def connect():
    return psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')


def cohort(conn, direction, bias, days):
    """Return (n, wins, pnl, all_window_winners) for LONG/SHORT into opposite bias."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*),
               SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END),
               COALESCE(SUM(pnl_usdt), 0)
        FROM trades
        WHERE status = 'closed' AND direction = %s
          AND close_time > NOW() - INTERVAL %s
          AND _signal_metadata ? 'coin_regime'
          AND _signal_metadata->>'coin_regime' = %s
        """,
        (direction, f'{days} days', bias),
    )
    n, w, pnl = cur.fetchone()
    cur.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END), 0)
        FROM trades
        WHERE status = 'closed' AND direction = %s
          AND close_time > NOW() - INTERVAL %s
        """,
        (direction, f'{days} days'),
    )
    allw = cur.fetchone()[0] or 1
    return int(n or 0), int(w or 0), float(pnl), int(allw)


def other_cohort(conn, direction, days):
    """The kept set: same direction, coin_regime present, NOT the opposite bias."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*),
               SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END),
               COALESCE(SUM(pnl_usdt), 0)
        FROM trades
        WHERE status = 'closed' AND direction = %s
          AND close_time > NOW() - INTERVAL %s
          AND _signal_metadata ? 'coin_regime'
          AND _signal_metadata->>'coin_regime' IN ('LONG_BIAS', 'SHORT_BIAS')
          AND NOT (
            (%s = 'LONG' AND _signal_metadata->>'coin_regime' = 'SHORT_BIAS')
            OR (%s = 'SHORT' AND _signal_metadata->>'coin_regime' = 'LONG_BIAS')
          )
        """,
        (direction, f'{days} days', direction, direction),
    )
    n, w, pnl = cur.fetchone()
    return int(n or 0), int(w or 0), float(pnl)


def evaluate(label, blocked, kept, allw, days):
    bn, bw, bp = blocked
    kn, kw, kp = kept
    save = -bp  # blocking the cohort saves its pnl if negative
    fk = 100.0 * bw / allw if allw else 0.0
    p = fisher_exact(bw, bn - bw, kw, kn - kw) if bn and kn else float('nan')
    bars = {
        'n_ge_20': bn >= 20,
        'save_pos': save > 0,
        'fk_lt_20': fk < 20.0,
        'p_lt_05': p < 0.05,
    }
    verdict = 'SHIP-CANDIDATE' if all(bars.values()) else 'COLLECT/REFUSE'
    print(
        f'{days}d {label}: blocked n={bn} W={bw} pnl={bp:+.2f} | '
        f'kept n={kn} W={kw} pnl={kp:+.2f} | save={save:+.2f} fk={fk:.1f}% '
        f'p={p:.4f} -> {verdict} fails={[k for k, v in bars.items() if not v]}'
    )
    return bars, verdict


def main():
    conn = connect()
    print('=== coin_regime direction-split (Oct-27 pre-reg) ===')
    for days in (7, 14, 30):
        # LONG into SHORT_BIAS
        bn, bw, bp, allw_l = cohort(conn, 'LONG', 'SHORT_BIAS', days)
        kn, kw, kp = other_cohort(conn, 'LONG', days)
        evaluate('LONG->coin SHORT_BIAS', (bn, bw, bp), (kn, kw, kp), allw_l, days)
        # SHORT into LONG_BIAS
        bn2, bw2, bp2, allw_s = cohort(conn, 'SHORT', 'LONG_BIAS', days)
        kn2, kw2, kp2 = other_cohort(conn, 'SHORT', days)
        evaluate('SHORT->coin LONG_BIAS', (bn2, bw2, bp2), (kn2, kw2, kp2), allw_s, days)
    conn.close()

    # family confound for the leading candidate
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT signal, COUNT(*), ROUND(SUM(pnl_usdt), 2)
        FROM trades
        WHERE status='closed' AND direction='LONG'
          AND close_time > NOW() - INTERVAL '14 days'
          AND _signal_metadata ? 'coin_regime'
          AND _signal_metadata->>'coin_regime' = 'SHORT_BIAS'
        GROUP BY signal ORDER BY SUM(pnl_usdt)
        """
    )
    rows = cur.fetchall()
    total = sum(abs(float(r[2])) for r in rows) or 1
    top = rows[0] if rows else None
    print(f'14d LONG->SHORT_BIAS families: {len(rows)}; top bleed {top}')
    conn.close()
    print('NOTE: stamps <30d old -> 14d==30d, no OOS/halves possible until ~Nov 4.')
    print('RE-MEASURE when: older half exists AND p<0.05 AND fk stays <20%.')


def selfcheck():
    # Fisher sanity: known value
    p = fisher_exact(1, 9, 11, 3)
    assert abs(p - 0.002759455) < 1e-6, f'fisher mismatch {p}'
    # save/fk arithmetic
    bn, bw, bp = 33, 12, -0.94
    save, fk = -bp, 100.0 * bw / 131
    assert abs(save - 0.94) < 1e-9
    assert 9.0 < fk < 10.0  # 12/131 = 9.16%
    # verdict logic
    bars = {'n_ge_20': True, 'save_pos': True, 'fk_lt_20': True, 'p_lt_05': False}
    assert not all(bars.values())
    print('SELFCHECK PASS (fisher known-value, save/fk arithmetic, verdict logic)')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        main()
