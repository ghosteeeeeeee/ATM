#!/usr/bin/env python3
"""
linreg_xsec_legs_followup.py — follow-up to linreg_crosssection_research:
the per-bar ICs are stable across all 4 months (fade sign, t=14-100), but the
tradeable question is per-LEG, per-month economics:

  1. Are BOTH legs positive in their own months (the "both sides" question)?
  2. Decile vs quintile concentration — does a more extreme cut widen the
     spread enough to clear fees?
  3. Combined trigger: own-history P10/P90 extreme AND cross-sectional
     decile — the round-1 trigger concentrated with round-2 context.

Usage: python3 scripts/analysis/linreg_xsec_legs_followup.py [--tf 15m|1m]
"""
import os
import sys
import datetime

import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linreg_crosssection_research as X  # noqa: E402

FEE_RT = 0.09   # taker round trip per leg


def own_history_extreme(d, w=20, trail=500, pct=10):
    """Round-1 trigger: slope vs the token's OWN trailing P10/P90.
    Returns array: -1 = own-history bottom (LONG candidate),
    +1 = own-history top (SHORT candidate), 0 = neither, np.nan = no data."""
    c = d['close']
    n = len(c)
    out = np.full(n, np.nan)
    if n < trail + w + 5:
        return out
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(c, w)
    x = np.arange(w, dtype=np.float64)
    dx = x - x.mean()
    denom = float((dx * dx).sum())
    ym = win.mean(axis=1)
    s = (win @ dx) / denom
    with np.errstate(divide='ignore', invalid='ignore'):
        slp = s / ym * 100.0
    slp[~np.isfinite(slp)] = np.nan
    # slp[i] -> window ending at bar i+w-1
    for i in range(w - 1 + trail, n):
        hist = slp[i - w - trail + 1:i - w + 1]
        hist = hist[np.isfinite(hist)]
        if len(hist) < trail * 0.9:
            continue
        cur = slp[i - w + 1]
        if not np.isfinite(cur):
            continue
        if cur <= np.percentile(hist, pct):
            out[i] = -1
        elif cur >= np.percentile(hist, 100 - pct):
            out[i] = +1
    return out


def main():
    tf = '15m'
    horizons = None
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == '--tf' and i + 1 < len(argv):
            tf = argv[i + 1]
    min_bars = X.MIN_BARS[tf]
    horizons = X.HORIZONS[tf]

    uni = X.load_universe(tf, min_bars)
    ts_grid = np.unique(np.concatenate([d['ts'] for d in uni.values()]))
    split_idx = int(len(ts_grid) * X.IS_FRAC)
    split_month = datetime.datetime.utcfromtimestamp(
        int(ts_grid[split_idx])).strftime('%Y-%m')
    print(f'tf={tf} tokens={len(uni)} bars={len(ts_grid)} split_month={split_month}')

    fwd = {}
    for H in horizons:
        F = X.build_matrix(uni, (lambda d, H=H: (
            np.concatenate([d['close'][H:] / d['close'][:-H] - 1.0,
                            np.full(H, np.nan)]))), ts_grid)
        fwd[H] = F

    fns = X.feature_fns()

    def month_of(i):
        return datetime.datetime.utcfromtimestamp(
            int(ts_grid[i])).strftime('%Y-%m')

    for fname in ['slope_pct', 'rng_pos', 'resid_z']:
        Xmat = X.build_matrix(uni, fns[fname], ts_grid)
        for H in horizons:
            Y = fwd[H]
            # ── 1) per-month legs, quintile and decile cuts ───────────────
            for cut_frac, cut_name in [(5, 'quintile'), (10, 'decile')]:
                legs = {}   # month -> {'L': [...], 'S': [...], 'ex': [...]}
                for i in range(len(ts_grid)):
                    x, y = Xmat[i], Y[i]
                    m = np.isfinite(x) & np.isfinite(y)
                    if m.sum() < X.MIN_TOKENS_PER_BAR:
                        continue
                    xs, ys = x[m], y[m]
                    order = np.argsort(xs)
                    k = max(3, len(xs) // cut_frac)
                    bot, top = order[:k], order[-k:]
                    mo = month_of(i)
                    rec = legs.setdefault(mo, {'L': [], 'S': [], 'ex': []})
                    rec['L'].append(ys[bot].mean())
                    rec['S'].append(-ys[top].mean())     # profit of shorting
                    rec['ex'].append(ys[bot].mean() - ys[top].mean())
                if cut_name != 'decile' or fname == 'slope_pct':
                    print(f'\n{fname} H={H} {cut_name} legs by month '
                          f'(raw %, per leg; ex = long-short spread):')
                    for mo in sorted(legs):
                        r = legs[mo]
                        L, S, E = (np.mean(r['L']), np.mean(r['S']),
                                   np.mean(r['ex']))
                        nL = len(r['L'])
                        print(f'  {mo} n={nL:<5} LONG={L*100:+.4f}% '
                              f'(net {(L*100-FEE_RT):+.4f}) | '
                              f'SHORT={S*100:+.4f}% (net {(S*100-FEE_RT):+.4f}) | '
                              f'spread={E*100:+.4f}% | '
                              f'{"IS" if mo < split_month else "OOS"}')

    # ── 3) combined trigger: own-history extreme AND cross-sectional decile
    print('\n' + '=' * 78)
    print('COMBINED TRIGGER: own-history P10/P90 AND cross-sectional decile')
    print('=' * 78)
    # own-history matrix
    OH = X.build_matrix(uni, lambda d: own_history_extreme(d), ts_grid)
    for fname in ['slope_pct', 'rng_pos']:
        Xmat = X.build_matrix(uni, fns[fname], ts_grid)
        for H in horizons:
            Y = fwd[H]
            res = {}   # month -> {'L': [], 'S': []}
            for i in range(len(ts_grid)):
                x, y, oh = Xmat[i], Y[i], OH[i]
                m = np.isfinite(x) & np.isfinite(y) & np.isfinite(oh)
                if m.sum() < X.MIN_TOKENS_PER_BAR:
                    continue
                xs, ys, ohs = x[m], y[m], oh[m]
                order = np.argsort(xs)
                k = max(3, len(xs) // 10)
                bot_set = set(order[:k].tolist())
                top_set = set(order[-k:].tolist())
                mo = month_of(i)
                rec = res.setdefault(mo, {'L': [], 'S': []})
                for j in range(len(xs)):
                    if ohs[j] == -1 and j in bot_set:
                        rec['L'].append(ys[j])
                    elif ohs[j] == +1 and j in top_set:
                        rec['S'].append(-ys[j])
            tot = {'L': [], 'S': []}
            print(f'\n{fname} H={H}:')
            for mo in sorted(res):
                r = res[mo]
                for side in ['L', 'S']:
                    tot[side].extend(r[side])
                line = f'  {mo}'
                for side, lab in [('L', 'LONG'), ('S', 'SHORT')]:
                    v = r[side]
                    if len(v) >= 10:
                        w = sum(1 for z in v if z > 0)
                        line += (f' | {lab} n={len(v):<4} '
                                 f'WR={100*w/len(v):4.1f}% '
                                 f'avg={np.mean(v)*100:+.4f}% '
                                 f'net={(np.mean(v)*100-FEE_RT):+.4f}%')
                    else:
                        line += f' | {lab} n={len(v)}'
                print(line)
            for side, lab in [('L', 'LONG'), ('S', 'SHORT')]:
                v = tot[side]
                if len(v) >= 30:
                    w = sum(1 for z in v if z > 0)
                    print(f'  ALL {lab}: n={len(v)} WR={100*w/len(v):.1f}% '
                          f'avg={np.mean(v)*100:+.4f}% '
                          f'net={(np.mean(v)*100-FEE_RT):+.4f}%')


if __name__ == '__main__':
    main()
