#!/usr/bin/env python3
"""CONFIDENCE FIELD SEMANTICS — run #146 (2026-10-25), zero-behavior.

Finding
-------
`trades.confidence` and the value the MIN_EXEC_CONFIDENCE gate sees are DIFFERENT
quantities.  decider_run.run() evaluates `if confidence < MIN_EXEC_CONFIDENCE` at
:3796, then applies three further reductions before execute_trade():

    :4308  confidence = confidence - WRONG_SIDE_PENALTY          (gate-time WARN path)
    :4811  confidence = max(confidence - ctx_penalty, 0)         (CTX-GATE WARN, -20 typical)
    :4856  confidence = max(confidence + LOSERS_CONF_PENALTY, 0) (-50)

`_signal_metadata.final_confidence` is the pre-reduction (gate-time) value;
`trades.confidence` is the post-reduction value stored by brain.py.

Consequences
------------
1. The "MIN_EXEC_CONFIDENCE handles the final cutoff" comment (decider_run.py:4298,
   hermes_constants.py:1512) is false — the cutoff runs first.
2. 14d: every trade stored below 40 passed a gate-time value >= 40 (LEAK=stored<40
   count).  Any confidence floor implemented AT :3796 sees gate-time confidence and
   would be a structural no-op for thresholds calibrated on `trades.confidence`
   (the field brain/fk_definitions.md's CONF_FLOOR fk table was computed on).
3. The confidence SCALE also changed: cell_stats `_cell_mult` wiring (2026-10-14)
   + CONF-CALIB clamp (2026-10-15 03:41) moved gate-time p50 95.0 -> 51.8.

Usage:  python3 brain/analysis/conf_field_semantics_2026-10-25.py [--selfcheck]
"""
import sys

import psycopg2

CUR = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres').cursor()
CLAMP_TS = '2026-10-15 03:41'


def _q(sql, *a):
    CUR.execute(sql, a)
    return CUR.fetchone()


def leak_stats(win='14 days'):
    """stored vs gate confidence, 14d (or given window)."""
    return _q("""
        SELECT COUNT(*),
               SUM(CASE WHEN confidence < 40 THEN 1 ELSE 0 END),
               SUM(CASE WHEN (_signal_metadata::jsonb->>'final_confidence')::float < 40 THEN 1 ELSE 0 END),
               SUM(CASE WHEN confidence < 40
                         AND (_signal_metadata::jsonb->>'final_confidence')::float >= 40 THEN 1 ELSE 0 END),
               ROUND(AVG(((_signal_metadata::jsonb->>'final_confidence')::float) - confidence)::numeric, 2)
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL %s
          AND _signal_metadata::jsonb ? 'final_confidence'
    """, win)


def scale_drift():
    """gate-time confidence scale before/after the CONF-CALIB clamp."""
    out = {}
    for label, cond in (('PRE', "open_time < %s"), ('POST', "open_time >= %s")):
        out[label] = _q(f"""
            SELECT COUNT(*),
                   ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (
                       ORDER BY (_signal_metadata::jsonb->>'final_confidence')::float)::numeric, 1),
                   SUM(CASE WHEN (_signal_metadata::jsonb->>'final_confidence')::float < 50 THEN 1 ELSE 0 END)
            FROM trades
            WHERE status='closed' AND open_time > NOW() - INTERVAL '45 days'
              AND {cond} AND _signal_metadata::jsonb ? 'final_confidence'
        """, CLAMP_TS)
    return out


def floor_noop_check():
    """How many gate-time confidences sit below the standing floors?"""
    return _q("""
        SELECT COUNT(*),
               SUM(CASE WHEN (_signal_metadata::jsonb->>'final_confidence')::float < 30 THEN 1 ELSE 0 END),
               SUM(CASE WHEN (_signal_metadata::jsonb->>'final_confidence')::float < 40 THEN 1 ELSE 0 END),
               SUM(CASE WHEN confidence < 30 THEN 1 ELSE 0 END),
               SUM(CASE WHEN confidence < 40 THEN 1 ELSE 0 END)
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
          AND _signal_metadata::jsonb ? 'final_confidence'
    """)


def main():
    n, s_lt40, g_lt40, leak, div = leak_stats()
    print(f'[FIELD] n={n} stored<40={s_lt40} gate<40={g_lt40} LEAK={leak} avg(gate-stored)={div}')
    no = floor_noop_check()
    print(f'[NO-OP] 30d n={no[0]} gate<30={no[1]} gate<40={no[2]} '
          f'| stored<30={no[3]} stored<40={no[4]}  '
          f'-> a floor at decider_run.py:3796 blocks {no[1]}/{no[3]} of the '
          f'stored<30 cohort the fk table measured')
    dr = scale_drift()
    for k in ('PRE', 'POST'):
        c = dr[k]
        print(f'[SCALE] {k} (clamped {CLAMP_TS}): n={c[0]} gate_p50={c[1]} gate<50={c[2]} '
              f'({100 * c[2] / c[0]:.1f}%)' if c[0] else f'[SCALE] {k}: no rows')


def selfcheck():
    n, s_lt40, g_lt40, leak, div = leak_stats()
    assert n > 100, f'n too small: {n}'
    assert g_lt40 == 0, f'gate-time confidence should never be <40 on this path: {g_lt40}'
    assert leak == s_lt40, 'every stored<40 must be a post-gate reduction'
    assert leak > 0, 'expected at least one post-gate reduction'
    assert float(div) > 10, f'expected avg divergence >10 pts, got {div}'
    no = floor_noop_check()
    assert no[1] == 0, 'gate-time conf<30 must be 0 for the no-op claim to hold'
    assert no[3] > 20, f'stored<30 cohort should be non-trivial, got {no[3]}'
    assert no[3] > no[1], 'stored cohort must exceed what the gate site would block'
    dr = scale_drift()
    assert dr['PRE'][0] > 100 and dr['POST'][0] > 50, 'both eras need sample'
    assert float(dr['POST'][1]) < float(dr['PRE'][1]), 'expected post-clamp p50 to fall'
    print('SELF-CHECK PASS: field divergence, no-op hazard and scale drift all reproduce.')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    main()
