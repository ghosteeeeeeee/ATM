#!/usr/bin/env python3
"""
linreg_crosssection_research.py — RenTech round 2: CROSS-SECTIONAL regression.

WHY THIS ROUND: round 1 predicted each token's ABSOLUTE forward return, which
is contaminated by market beta — that is why the shipped signal ended up
one-sided (LONG only works in up-regimes, SHORT only in down-regimes) and why
a "both sides" deployment failed the regime tests. Hedge funds do not predict
whether the market rises; they predict WHICH ASSET outperforms the others —
market-neutral, both sides simultaneously, every day.

  TARGET    : cross-sectional EXCESS return — token's forward H-bar return
              MINUS the cross-sectional median return of the same bar
              (the nonlinear transform + beta removal Patterson asks about).
              Raw forward return reported alongside for comparison.
  PREDICTOR : ONE at a time (slope%, residual-z, range position, momentum,
              volume-z, ATR compression, ATR-normalized slope).
  UNIT      : one cross-section per bar (>=40 tokens with finite data),
              Spearman IC per bar -> mean IC, t-stat, IS/OOS, monthly.
  ALSO      : fade spread = mean(excess return of bottom-quintile feature)
              vs top-quintile — the tradeable both-sides number.

Data cleaning: PAXG (gold peg) and STABLE (stablecoin) excluded.

Usage: python3 scripts/analysis/linreg_crosssection_research.py [--tf 1m|15m]
"""
import os
import sys
import datetime

import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
from paths import HERMES_DATA  # noqa: E402

CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

EXCLUDE_TOKENS = {'PAXG', 'STABLE'}   # gold peg / stablecoin — no crypto beta
MIN_BARS = {'1m': 10000, '15m': 2000}  # >= ~7 days of 1m, ~14 days of 15m
HORIZONS = {'1m': [60, 120, 240, 480], '15m': [4, 8, 16, 32]}  # 1h..8h / 1h..32h
MIN_TOKENS_PER_BAR = 40
IS_FRAC = 0.70

FEATURES = ['slope_pct', 'resid_z', 'rng_pos', 'mom', 'vol_z', 'atr_comp',
            'slope_atr']


def load_universe(tf, min_bars):
    """{token: dict(ts, open, close, high, low, vol)} excluding pegs."""
    import sqlite3
    table = f'candles_{tf}'
    conn = sqlite3.connect(CANDLES_DB, timeout=60)
    try:
        toks = [r[0] for r in conn.execute(
            f"SELECT token FROM {table} WHERE is_closed=1 GROUP BY token "
            f"HAVING COUNT(*) >= ?", (min_bars,))]
        out = {}
        for tok in toks:
            if tok.upper() in EXCLUDE_TOKENS:
                continue
            rows = conn.execute(
                f"SELECT ts, open, close, high, low, volume FROM {table} "
                f"WHERE token=? AND is_closed=1 AND close > 0 ORDER BY ts",
                (tok,)).fetchall()
            if len(rows) < min_bars:
                continue
            out[tok] = dict(
                ts=np.array([r[0] for r in rows], dtype=np.int64),
                open=np.array([r[1] for r in rows], dtype=np.float64),
                close=np.array([r[2] for r in rows], dtype=np.float64),
                high=np.array([r[3] for r in rows], dtype=np.float64),
                low=np.array([r[4] for r in rows], dtype=np.float64),
                vol=np.array([r[5] if r[5] is not None else 0.0 for r in rows],
                             dtype=np.float64))
        return out
    finally:
        conn.close()


def build_matrix(universe, field_fn, ts_grid):
    """Scatter per-token feature arrays into a (T x N) matrix on ts_grid
    (vectorized searchsorted — dict scatter was O(T*N) python)."""
    T = len(ts_grid)
    M = np.full((T, len(universe)), np.nan)
    for j, (tok, d) in enumerate(universe.items()):
        vals = field_fn(d)
        pos = np.searchsorted(ts_grid, d['ts'])
        pos_c = np.clip(pos, 0, T - 1)
        ok = (pos < T) & (ts_grid[pos_c] == d['ts']) & np.isfinite(vals)
        M[pos[ok], j] = vals[ok]
    return M


def feature_fns():
    """Per-token feature calculators (round-1 variables, unchanged)."""
    def slope_pct(d):
        c = d['close']
        from numpy.lib.stride_tricks import sliding_window_view
        if len(c) < 21:
            return np.full(len(c), np.nan)
        win = sliding_window_view(c, 20)
        x = np.arange(20.0)
        dx = x - x.mean()
        denom = float((dx * dx).sum())
        ym = win.mean(axis=1)
        s = (win @ dx) / denom
        out = np.full(len(c), np.nan)
        with np.errstate(divide='ignore', invalid='ignore'):
            pct = s / ym * 100.0
        pct[~np.isfinite(pct)] = np.nan
        out[19:] = pct
        return out

    def resid_z(d):
        c = d['close']
        from numpy.lib.stride_tricks import sliding_window_view
        if len(c) < 21:
            return np.full(len(c), np.nan)
        win = sliding_window_view(c, 20)
        x = np.arange(20.0)
        dx = x - x.mean()
        denom = float((dx * dx).sum())
        ym = win.mean(axis=1)
        s = (win @ dx) / denom
        a = ym - s * x.mean()
        fitted = a[:, None] + s[:, None] * x[None, :]
        resid = win - fitted
        sd = resid.std(axis=1, ddof=1)
        out = np.full(len(c), np.nan)
        rz = np.full(len(sd), np.nan)
        ok = sd > 0
        rz[ok] = resid[ok, -1] / sd[ok]
        out[19:] = rz
        return out

    def rng_pos(d):
        from numpy.lib.stride_tricks import sliding_window_view
        h, l, c = d['high'], d['low'], d['close']
        if len(h) < 61:
            return np.full(len(h), np.nan)
        hw = sliding_window_view(h, 60).max(axis=1)
        lw = sliding_window_view(l, 60).min(axis=1)
        span = hw - lw
        out = np.full(len(h), np.nan)
        ok = span > 0
        rp = np.full(len(span), 0.5)
        rp[ok] = (c[59:][ok] - lw[ok]) / span[ok]
        out[59:] = rp
        return out

    def mom(d):
        c = d['close']
        out = np.full(len(c), np.nan)
        if len(c) > 60:
            out[60:] = c[60:] / c[:-60] - 1.0
        return out

    def vol_z(d):
        v = d['vol']
        n = len(v)
        out = np.full(n, np.nan)
        if n < 60:
            return out
        csum = np.cumsum(v)
        csum2 = np.cumsum(v ** 2)
        idx = np.arange(n)
        start = idx - 59
        valid = start >= 0
        m = np.full(n, np.nan)
        m2 = np.full(n, np.nan)
        m[valid] = (csum[valid] - np.where(start[valid] > 0, csum[start[valid] - 1], 0.0)) / 60
        m2[valid] = (csum2[valid] - np.where(start[valid] > 0, csum2[start[valid] - 1], 0.0)) / 60
        var = np.maximum(m2 - m ** 2, 0.0)
        sd = np.sqrt(var)
        with np.errstate(divide='ignore', invalid='ignore'):
            z = (v - m) / sd
        z[~np.isfinite(z)] = np.nan
        return z

    def atr_comp(d):
        c, h, l = d['close'], d['high'], d['low']
        n = len(c)
        out = np.full(n, np.nan)
        if n < 75:
            return out
        pc = c[:-1]
        tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
        atr_raw = np.convolve(tr, np.ones(14) / 14, mode='valid')
        atr = np.full(n, np.nan)
        atr[14:] = atr_raw
        with np.errstate(divide='ignore', invalid='ignore'):
            comp = atr / c * 100.0
        comp[~np.isfinite(comp)] = np.nan
        return comp

    def slope_atr(d):
        sl = slope_pct(d)
        # reuse atr from atr_comp math
        c, h, l = d['close'], d['high'], d['low']
        n = len(c)
        atr = np.full(n, np.nan)
        if n >= 75:
            pc = c[:-1]
            tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
            atr[14:] = np.convolve(tr, np.ones(14) / 14, mode='valid')
        with np.errstate(divide='ignore', invalid='ignore'):
            out = sl / (atr / c * 100.0) * 100.0  # slope% per ATR% — same sign as slope
        # simpler: slope_pct normalized by atr% (both in % — dimensionless-ish)
        out = sl / np.where(atr > 0, atr / c * 100.0, np.nan)
        out[~np.isfinite(out)] = np.nan
        return out

    return dict(slope_pct=slope_pct, resid_z=resid_z, rng_pos=rng_pos,
                mom=mom, vol_z=vol_z, atr_comp=atr_comp, slope_atr=slope_atr)


def row_spearman(x_row, y_row):
    m = np.isfinite(x_row) & np.isfinite(y_row)
    n = int(m.sum())
    if n < MIN_TOKENS_PER_BAR:
        return np.nan, 0
    x = x_row[m]
    y = y_row[m]
    rx = np.argsort(np.argsort(x)).astype(np.float64)
    ry = np.argsort(np.argsort(y)).astype(np.float64)
    rx -= rx.mean()
    ry -= ry.mean()
    den = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    if den <= 0:
        return np.nan, 0
    return float((rx * ry).sum() / den), n


def row_rank(q):
    """Cross-sectional rank of each row (NaN stays NaN)."""
    R = np.full_like(q, np.nan)
    for i in range(q.shape[0]):
        row = q[i]
        m = np.isfinite(row)
        if m.sum() < MIN_TOKENS_PER_BAR:
            continue
        r = np.empty(int(m.sum()))
        r[np.argsort(row[m])] = np.arange(int(m.sum()))
        R[i, m] = r
    return R


def stats(ics):
    ics = np.array([v for v in ics if np.isfinite(v)])
    if len(ics) < 30:
        return dict(n=len(ics), mean=np.nan, t=np.nan)
    mean = float(ics.mean())
    se = float(ics.std(ddof=1) / np.sqrt(len(ics)))
    return dict(n=len(ics), mean=mean, t=mean / se if se > 0 else np.nan)


def main():
    tf = '1m'
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == '--tf' and i + 1 < len(argv):
            tf = argv[i + 1]
    min_bars = MIN_BARS[tf]
    horizons = HORIZONS[tf]

    print('=' * 78)
    print(f'CROSS-SECTIONAL REGRESSION RESEARCH (tf={tf}, horizons={horizons} bars)')
    print(f'exclude pegs: {sorted(EXCLUDE_TOKENS)}  min_bars={min_bars}')
    print('=' * 78)

    uni = load_universe(tf, min_bars)
    print(f'universe: {len(uni)} tokens')

    ts_grid = np.unique(np.concatenate([d['ts'] for d in uni.values()]))
    print(f'cross-sections (unique bars): {len(ts_grid)}')

    # targets: raw fwd returns + cross-sectional excess (beta removal)
    fwd = {}
    for H in horizons:
        F = build_matrix(uni, (lambda d, H=H: (
            np.concatenate([d['close'][H:] / d['close'][:-H] - 1.0,
                            np.full(H, np.nan)]))), ts_grid)
        # note: per-token ts order is chronological; shift by H bars within token
        med = np.nanmedian(F, axis=1, keepdims=True)
        Fex = F - med
        fwd[f'raw{H}'] = F
        fwd[f'ex{H}'] = Fex
        print(f'H={H}: fwd matrix {F.shape}, valid/row median='
              f'{np.median(np.isfinite(F).sum(axis=1)):.0f}')

    fns = feature_fns()
    split_idx = int(len(ts_grid) * IS_FRAC)
    print(f'IS/OOS split at index {split_idx} '
          f'({datetime.datetime.utcfromtimestamp(int(ts_grid[split_idx]))})')

    results = []
    for fname in FEATURES:
        print(f'\n--- feature: {fname} ---')
        X = build_matrix(uni, fns[fname], ts_grid)
        for H in horizons:
            for tgt in ['raw', 'ex']:
                Y = fwd[f'{tgt}{H}']
                ics, ics_is, ics_oos, ics_mon = [], [], [], {}
                for i in range(len(ts_grid)):
                    ic, n = row_spearman(X[i], Y[i])
                    if not np.isfinite(ic):
                        continue
                    ics.append(ic)
                    (ics_is if i < split_idx else ics_oos).append(ic)
                    mo = datetime.datetime.utcfromtimestamp(
                        int(ts_grid[i])).strftime('%Y-%m')
                    ics_mon.setdefault(mo, []).append(ic)
                s_all, s_is, s_oos = stats(ics), stats(ics_is), stats(ics_oos)
                verdict = ''
                if np.isfinite(s_is['mean']) and np.isfinite(s_oos['mean']):
                    if np.sign(s_is['mean']) != np.sign(s_oos['mean']):
                        verdict = 'RUBBISH(sign flip)'
                    elif abs(s_oos['t']) >= 2.0:
                        verdict = 'CANDIDATE'
                    else:
                        verdict = 'weak'
                mon = ' '.join(f'{m}:{np.mean(v):+.3f}' for m, v in sorted(ics_mon.items()))
                print(f'  H={H:>3} {tgt:>3} | all IC={s_all["mean"]:+.4f} t={s_all["t"]:6.1f} | '
                      f'IS={s_is["mean"]:+.4f} OOS={s_oos["mean"]:+.4f} t={s_oos["t"]:6.1f} | {verdict}')
                print(f'        monthly: {mon}')
                results.append((fname, H, tgt, s_all, s_is, s_oos, verdict))

    # ── tradeable fade spread (both sides, market-neutral excess) ─────────
    print('\n' + '=' * 78)
    print('FADE SPREAD (bottom-quintile LONG vs top-quintile SHORT, per bar)')
    print('ex = market-neutral excess return; raw = actual directional P&L')
    print('=' * 78)
    for fname in ['slope_pct', 'slope_atr', 'rng_pos', 'mom']:
        X = build_matrix(uni, fns[fname], ts_grid)
        for H in horizons:
            Yex = fwd[f'ex{H}']
            Yraw = fwd[f'raw{H}']
            spreads_ex, spreads_raw, long_leg_raw, short_leg_raw = [], [], [], []
            for i in range(len(ts_grid)):
                x, ye, yr = X[i], Yex[i], Yraw[i]
                m = np.isfinite(x) & np.isfinite(ye) & np.isfinite(yr)
                if m.sum() < MIN_TOKENS_PER_BAR:
                    continue
                xs, yes, yrs = x[m], ye[m], yr[m]
                order = np.argsort(xs)
                k = max(5, len(xs) // 5)
                bot, top = order[:k], order[-k:]
                # fade: LONG low feature, SHORT high feature (round-1 sign)
                spreads_ex.append(yes[bot].mean() - yes[top].mean())
                spreads_raw.append(yrs[bot].mean() - yrs[top].mean())
                long_leg_raw.append(yrs[bot].mean())
                short_leg_raw.append(-yrs[top].mean())
            se = stats(spreads_ex)
            sr = stats(spreads_raw)
            sl = stats(long_leg_raw)
            ss = stats(short_leg_raw)
            print(f'  {fname:10} H={H:>3} | ex-spread={se["mean"]:+.4f}% t={se["t"]:6.1f} '
                  f'| raw LONG leg={sl["mean"]:+.4f}% t={sl["t"]:5.1f} '
                  f'| raw SHORT leg={ss["mean"]:+.4f}% t={ss["t"]:5.1f} (n={se["n"]})')


if __name__ == '__main__':
    main()
