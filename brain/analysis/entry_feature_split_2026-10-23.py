#!/usr/bin/env python3
"""entry_feature_split_2026-10-23.py — can stamped entry-time metadata separate
hard_max_loss (chop, never-armed) trades from trail-armed trades?

brain_auditor run #96 creative #1.  Mandate: keep us out of chop at ADMISSION.
If the metadata we already stamp at entry separates the two families, an entry
gate exists.  This measures it instead of assuming it.

Families (14d closed trades with _signal_metadata):
  HML     exit_reason == 'hard_max_loss'
  ARMED   trailing_activated = TRUE  (and not HML)
  UNARMED trailing_activated = FALSE (and not HML)  — context column only

Reported: per-field medians, a threshold sweep on the widest-gap field with
Fisher exact p-values, and a 7d/7d split-half check for temporal stability.

Usage:
    python3 entry_feature_split_2026-10-23.py            # full report
    python3 entry_feature_split_2026-10-23.py --selfcheck # asserts the negative
"""
import sys
import os
import json
import statistics
from math import comb

sys.path.insert(0, '/root/.hermes/scripts')
from paths import *  # noqa: F401,F403
import psycopg2

FIELDS = ['momentum_score', 'volume_spike', 'speed_percentile', 'bb_position',
          'z_score', 'price_acceleration', 'gap_at_entry', 'staleness_minutes',
          'macd_hist', 'rsi_14', 'rsi_exec', 'btc_score', 'coin_regime_conf']
DAYS = 14


def _is_num(v):
    """Numeric metadata only — bool is an int subclass and must stay out."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact for [[a,b],[c,d]]."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    if r1 == 0 or c1 == 0:
        return 1.0

    def prob(x):
        y, z, w = r1 - x, c1 - x, n - r1 - c1 + x
        if min(x, y, z, w) < 0:
            return 0.0
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)

    p0 = prob(a)
    return sum(prob(x) for x in range(0, min(r1, c1) + 1) if prob(x) <= p0 + 1e-12)


def load():
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT exit_reason, trailing_activated, close_time, _signal_metadata
               FROM trades
               WHERE status='closed' AND close_time > NOW() - INTERVAL %s
                 AND _signal_metadata IS NOT NULL""",
            (f'{DAYS} days',))
        rows = cur.fetchall()
    finally:
        conn.close()

    groups = {'HML': {}, 'ARMED': {}, 'UNARMED': {}}
    meta = {'HML': [], 'ARMED': [], 'UNARMED': []}
    for er, ta, ct, md in rows:
        try:
            m = md if isinstance(md, dict) else json.loads(md)
        except Exception:
            continue
        fam = 'HML' if er == 'hard_max_loss' else ('ARMED' if ta else 'UNARMED')
        meta[fam].append((ct, m))
        for f in FIELDS:
            v = m.get(f)
            if _is_num(v):
                groups[fam].setdefault(f, []).append(float(v))
    return groups, meta


def report():
    groups, meta = load()
    n_hml, n_arm, n_una = len(meta['HML']), len(meta['ARMED']), len(meta['UNARMED'])
    print(f'14d stamped trades: HML={n_hml} ARMED={n_arm} UNARMED={n_una}')

    print(f"\n{'field':22} {'HML_med':>9} {'ARMED_med':>9} {'UNARMED_med':>11} {'nHML':>5} {'nARM':>5} {'delta':>7}")
    best_field, best_ratio, best_gap = None, -1.0, 0.0
    for f in FIELDS:
        h = groups['HML'].get(f, [])
        a = groups['ARMED'].get(f, [])
        u = groups['UNARMED'].get(f, [])
        if len(h) < 10 or len(a) < 10:
            continue
        hm, am, um = statistics.median(h), statistics.median(a), statistics.median(u)
        spread = statistics.pstdev(h + a) or 1.0
        ratio = abs(hm - am) / spread
        print(f'{f:22} {hm:9.3f} {am:9.3f} {um:11.3f} {len(h):5} {len(a):5} {hm - am:7.3f}')
        if ratio > best_ratio:
            best_field, best_ratio, best_gap = f, ratio, abs(hm - am)

    print(f'\nwidest HML-vs-ARMED gap: {best_field} (|delta|={best_gap:.3f}, '
          f'{best_ratio:.2f} pooled sd) -> threshold sweep + Fisher exact')

    print(f'\nthreshold sweep + Fisher exact (5 cut points per field, block if field >= t):')
    sweep = []
    global_min_p, arg, n_tests = 1.0, None, 0
    for f in FIELDS:
        h = [(m[f], ct) for ct, m in meta['HML'] if _is_num(m.get(f))]
        a = [(m[f], ct) for ct, m in meta['ARMED'] if _is_num(m.get(f))]
        if len(h) < 10 or len(a) < 10:
            continue
        lo = min(x for x, _ in h + a)
        hi = max(x for x, _ in h + a)
        n_tests += 5
        for k in range(1, 6):
            t = lo + (hi - lo) * k / 6
            hb = sum(1 for x, _ in h if x >= t)
            ab = sum(1 for x, _ in a if x >= t)
            p = fisher_2x2(hb, len(h) - hb, ab, len(a) - ab)
            if p < global_min_p:
                global_min_p, arg = p, (f, t, hb, len(h), ab, len(a))
            if f == best_field:
                sweep.append((t, p))
    for t, p in sweep:
        print(f'  {best_field} >= {t:6.2f}: p={p:.3f}')
    print(f'  global min p over all fields x thresholds = {global_min_p:.3f} at {arg}')
    min_p = global_min_p

    from datetime import timedelta
    allct = [ct for ct, m in meta['HML']] + [ct for ct, m in meta['ARMED']]
    if not allct:
        raise SystemExit('FAIL: no stamped HML/ARMED trades in window (nothing to split)')
    cut = max(allct) - timedelta(days=7)
    bonf = 0.05 / n_tests if n_tests else 0.05
    cand_field = arg[0] if arg else best_field
    print(f'\nsplit-half mean gap on candidate field {cand_field!r} '
          f'(recent half should match prior half if the feature is real):')
    half_delta = []
    for name, sel in (('prior7', lambda ct: ct < cut), ('recent7', lambda ct: ct >= cut)):
        h = [m[cand_field] for ct, m in meta['HML'] if _is_num(m.get(cand_field)) and sel(ct)]
        a = [m[cand_field] for ct, m in meta['ARMED'] if _is_num(m.get(cand_field)) and sel(ct)]
        if not h or not a:
            print(f'  {name}: empty')
            continue
        d = statistics.mean(h) - statistics.mean(a)
        half_delta.append(d)
        print(f'  {name}: HML n={len(h)} mean={statistics.mean(h):.2f} | '
              f'ARMED n={len(a)} mean={statistics.mean(a):.2f} | delta {d:+.2f}')

    survives_bonf = min_p < bonf
    durable = (len(half_delta) == 2 and half_delta[0] * half_delta[1] > 0
               and half_delta[0] != 0
               and abs(half_delta[1]) / abs(half_delta[0]) >= 0.5)
    verdict = 'CANDIDATE' if survives_bonf else 'NO SEPARATOR'
    print(f'\nVERDICT: {verdict} (min Fisher p={min_p:.3f} over {n_tests} unadjusted tests, '
          f'Bonferroni bar {bonf:.4f}; split-half deltas '
          f'{[round(d, 2) for d in half_delta]})')
    if not survives_bonf:
        print(f'  no test survives multiplicity — raw min-p {min_p:.3f} against '
              f'{n_tests} tests is within noise; not a separator.')
    if survives_bonf and not durable:
        print('  survives multiplicity but split-half is reversed/decayed — not durable, '
              're-check before citing.')
    if len(half_delta) == 2:
        same = half_delta[0] * half_delta[1] > 0
        decay = abs(half_delta[1]) / abs(half_delta[0]) if half_delta[0] else 0.0
        label = ('SAME-SIGN' if same else 'REVERSED') + (f', recent/prior magnitude {decay:.0%}')
        if not same or decay < 0.5:
            label += ' -> DECAYED, not a durable edge'
        print(f'temporal stability: {label}')
    return min_p, half_delta, (n_hml, n_arm, n_una), n_tests


def selfcheck():
    min_p, half_delta, counts, n_tests = report()
    n_hml, n_arm, _ = counts
    bonf = 0.05 / n_tests if n_tests else 0.05
    # explicit raises, not assert — asserts vanish under `python -O`
    if not (n_hml >= 50 and n_arm >= 100):
        raise SystemExit(f'SELFCHECK FAIL: sample too small {counts} (need HML>=50, ARMED>=100)')
    if not (0.0 <= min_p <= 1.0):
        raise SystemExit(f'SELFCHECK FAIL: bad p {min_p}')
    survives_bonf = min_p < bonf
    durable = (len(half_delta) == 2 and half_delta[0] * half_delta[1] > 0
               and half_delta[0] != 0
               and abs(half_delta[1]) / abs(half_delta[0]) >= 0.5)
    if survives_bonf and durable:
        raise SystemExit(
            f'SELFCHECK FAIL: a stamped entry feature separates at p={min_p:.3f} which SURVIVES '
            f'Bonferroni ({n_tests} tests, bar {bonf:.4f}) with a same-sign split-half '
            f'{[round(d, 2) for d in half_delta]} — the negative verdict is stale, re-run '
            'the analysis and re-check before citing')
    if min_p < 0.05:
        if survives_bonf:
            print(f'\nSELFCHECK PASS (raw min-p {min_p:.3f} SURVIVES Bonferroni '
                  f'({n_tests} tests, bar {bonf:.4f}) but the split-half on '
                  f'{[round(d, 2) for d in half_delta]} is not durable) — negative result '
                  'holds on durability; re-run the analysis before citing.')
        else:
            print(f'\nSELFCHECK PASS (raw min-p {min_p:.3f} < 0.05 does NOT survive '
                  f'multiplicity: {n_tests} tests, Bonferroni bar {bonf:.4f}, split-half '
                  f'{[round(d, 2) for d in half_delta]}) — negative result holds.')
    else:
        print('\nSELFCHECK PASS — negative result holds: no stamped entry feature separates '
              'HML from trail-armed, no admission gate from these fields.')
    return 0


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(selfcheck())
    report()
