#!/usr/bin/env python3
"""
linreg_combined_backtest.py — event-level validation of the ROUND-2 trigger:

    own-history P10/P90 extreme (round 1)  AND  cross-sectional decile
    (round 2: rank among ALL tokens at the same bar)

Why: cross-sectional IC research showed the fade is regime-free (IC sign
stable all 4 months, t=14-100) and the followup showed combined-trigger legs
net-positive on BOTH sides over 3 months (slope H32: LONG +0.25%/SHORT
+0.66% net, n=7.5k/6.1k). This script re-runs the round-1 event machinery
(next-bar-open entry, no lookahead, V8 exits, 0.09% fees, one position per
token) and filters events through the cross-sectional decile requirement —
the number that decides whether both flags can go ON.

Cohorts: A = round-1 trigger (own-history only, both sides)
         B = combined trigger (own-history AND cross-sectional decile)

Usage: python3 scripts/analysis/linreg_combined_backtest.py [--tf 15m|1m]
"""
import os
import sys
import datetime
from collections import defaultdict

import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linreg_fade_backtest as B  # noqa: E402

PEG_TOKENS = {'PAXG', 'STABLE'}


def build_xsec_thresholds(data):
    """For each bar timestamp: P10/P90 of slope_pct across ALL tokens
    (pegs excluded) at that bar. Returns dict ts -> (p10, p90)."""
    by_ts = defaultdict(list)
    for tok, d in data.items():
        if tok.upper() in PEG_TOKENS:
            continue
        sl, _ = B.compute_slope_atr(d)
        for ts, v in zip(d['ts'], sl):
            if np.isfinite(v):
                by_ts[int(ts)].append(v)
    out = {}
    for ts, vals in by_ts.items():
        if len(vals) >= 40:
            p10, p90 = np.percentile(vals, [10, 90])
            out[ts] = (float(p10), float(p90))
    return out


def main():
    tf = '15m'
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == '--tf' and i + 1 < len(argv):
            tf = argv[i + 1]
    B.configure(tf)
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    import linreg_forecast_research as R
    data = B.load_token(0, now, min_bars=R.MIN_BARS)
    all_ts = np.concatenate([d['ts'] for d in data.values()])
    split_ts = all_ts.min() + (all_ts.max() - all_ts.min()) * 0.70
    bar_sec = 900 if tf == '15m' else 60
    print(f'tf={tf} tokens={len(data)} split='
          f'{datetime.datetime.utcfromtimestamp(split_ts)}')

    variants = [('V1', 'fixed', 0.0, 0.0, 'none')]
    events, baselines, _ = B.run_events(data, split_ts, variants,
                                        gate_type='none', regime=None,
                                        regime4h=None)
    ev = events['V1']
    print(f'round-1 events (own-history trigger): {len(ev)}')

    thr = build_xsec_thresholds(data)
    print(f'cross-sections with >=40 tokens: {len(thr)}')

    # filter: signal bar = entry bar - 1 bar
    combined, no_xsec = [], 0
    for e in ev:
        sig_ts = e['ts'] - bar_sec
        t = thr.get(int(sig_ts))
        if t is None:
            no_xsec += 1
            continue
        p10, p90 = t
        if e['side'] == 'LONG' and e['slope'] <= p10:
            combined.append(e)
        elif e['side'] == 'SHORT' and e['slope'] >= p90:
            combined.append(e)
    print(f'events without cross-section data: {no_xsec} '
          f'(excluded from combined cohort)')

    def report(name, evs):
        print(f'\n--- {name} ---')
        for period, sel in [('IS ', lambda e: not e['oos']),
                            ('OOS', lambda e: e['oos']),
                            ('ALL', lambda e: True)]:
            sub = [e for e in evs if sel(e)]
            if not sub:
                print(f'  [{period}] n=0')
                continue
            for side in ['LONG', 'SHORT']:
                g = [e for e in sub if e['side'] == side]
                if not g:
                    continue
                nets = [x['net'] for x in g]
                w = sum(1 for x in nets if x > 0)
                print(f"  [{period}] {side:6} n={len(g):<6} "
                      f"WR={100*w/len(g):5.1f}% avg_net={np.mean(nets):+.4f}% "
                      f"sum={sum(nets):+.0f}")
            nets = [x['net'] for x in sub]
            w = sum(1 for x in nets if x > 0)
            print(f"  [{period}] BOOK  n={len(sub):<6} WR={100*w/len(sub):5.1f}% "
                  f"avg_net={np.mean(nets):+.4f}% sum={sum(nets):+.0f}")
        print('  by month:')
        for mo in sorted(set(e['month'] for e in evs)):
            g = [e for e in evs if e['month'] == mo]
            parts = []
            for side in ['LONG', 'SHORT']:
                s = [x['net'] for x in g if x['side'] == side]
                if s:
                    w = sum(1 for x in s if x > 0)
                    parts.append(f"{side}: n={len(s):<5} WR={100*w/len(s):4.1f}% "
                                 f"avg={np.mean(s):+.3f}%")
                else:
                    parts.append(f'{side}: n=0')
            nets = [x['net'] for x in g]
            w = sum(1 for x in nets if x > 0)
            print(f"    {mo} BOOK n={len(g):<5} WR={100*w/len(g):4.1f}% "
                  f"avg={np.mean(nets):+.3f}% | " + ' | '.join(parts))

    report('A. ROUND-1 TRIGGER — own-history extreme only, both sides', ev)
    report('B. COMBINED TRIGGER — own-history AND cross-sectional decile',
           combined)


if __name__ == '__main__':
    main()
