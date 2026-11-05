#!/usr/bin/env python3
"""
linreg_forecast_research.py — RenTech-style univariate regression research.

Nick Patterson (Renaissance): "our most important statistical tool was simple
regression with one target and one independent variable ... nobody tells you
what the variables you should be regressing. What's the target? Should you do
a nonlinear transform before you regress? Should you clean your data? Do you
notice when your results are obviously rubbish?"

So this script does exactly that discipline:

  TARGET    : forward return over H bars (1h / 2h / 4h) on 15m candles.
  PREDICTOR : ONE variable at a time (slope, R^2, deviation-from-regression,
              volume z, momentum, ATR compression, range position).
  CLEANING  : only closed candles, positive prices, minimum history per token,
              1/99 winsorization of predictor AND target (kills outliers that
              otherwise dominate OLS/Spearman).
  TRANSFORM : raw vs sign() (nonlinear transform before regressing).
  STATS     : Spearman IC + p-value, IS (first 70% of time) vs OOS (last 30%),
              plus a strict last-60-day holdout, monthly IC stability.
  RUBBISH   : any predictor whose OOS sign flips vs IS, or p > 0.05 OOS,
              is called rubbish explicitly — we do NOT ship it.

Usage:
    python3 scripts/analysis/linreg_forecast_research.py
"""

import os
import sys
import sqlite3
import datetime

import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
from paths import HERMES_DATA  # noqa: E402

CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
TABLE = 'candles_15m'

# ── Data cleaning constants ─────────────────────────────────────────────
MIN_BARS = 500          # token must have >= this many closed bars
WARMUP = 60             # bars needed before a feature can be computed
FEATURES = ['slope_pct', 'r2', 'dev_atr', 'vol_z', 'mom', 'atr_comp',
            'rng_pos', 'resid_z', 'slope_atr']
WINSOR_PCT = 1.0        # 1/99 percentile clipping (cleaning)
HORIZONS = [4, 8, 16, 32, 64]   # forward-return horizons in 15m bars
                                # (1h, 2h, 4h, 8h, 16h)
IS_FRAC = 0.70          # first 70% of time = in-sample
HOLDOUT_DAYS = 60       # strict most-recent holdout

# ── Feature windows ─────────────────────────────────────────────────────
W_SLOPE = 20            # regression window for slope/R^2/deviation
W_VOL = 20              # volume z window
W_MOM = 4               # momentum lookback (1h)
W_ATR = 14              # ATR window
W_RANGE = 20            # range position window


def load_token(ts_close, ts_fwd, min_bars=MIN_BARS):
    """Load closed 15m candles for all tokens with enough history.

    Returns {token: dict of np arrays (ts, close, high, low, volume)}.
    Cleaning: is_closed=1 only, close>0, high>=low.
    """
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    try:
        toks = [r[0] for r in conn.execute(
            f'SELECT token FROM {TABLE} WHERE is_closed=1 GROUP BY token '
            f'HAVING COUNT(*) >= ?', (min_bars,))]
        out = {}
        for tok in toks:
            rows = conn.execute(
                f'SELECT ts, open, close, high, low, volume FROM {TABLE} '
                f'WHERE token=? AND is_closed=1 AND close > 0 '
                f'ORDER BY ts', (tok,)).fetchall()
            if len(rows) < min_bars:
                continue
            ts = np.array([r[0] for r in rows], dtype=np.int64)
            open_ = np.array([r[1] for r in rows], dtype=np.float64)
            close = np.array([r[2] for r in rows], dtype=np.float64)
            high = np.array([r[3] for r in rows], dtype=np.float64)
            low = np.array([r[4] for r in rows], dtype=np.float64)
            vol = np.array([r[5] for r in rows], dtype=np.float64)
            # cleaning: high>=low sanity, finite values
            bad = ~(np.isfinite(close) & np.isfinite(high) & np.isfinite(low)
                    & np.isfinite(vol)) | (high < low)
            if bad.any():
                ts = ts[~bad]; open_ = open_[~bad]; close = close[~bad]
                high = high[~bad]; low = low[~bad]; vol = vol[~bad]
            if len(ts) < min_bars:
                continue
            out[tok] = dict(ts=ts, open=open_, close=close, high=high,
                            low=low, vol=vol)
        return out
    finally:
        conn.close()


def ols_slope_r2(y):
    """OLS of y on x=0..n-1. Returns (slope, intercept, r2) arrays (vectorized
    over trailing windows via stride trick is complex; called per-window in
    compute_features with rolling loop kept in numpy where possible)."""
    n = len(y)
    x = np.arange(n, dtype=np.float64)
    xm = x.mean()
    ym = y.mean()
    dx = x - xm
    denom = (dx * dx).sum()
    if denom <= 0:
        return 0.0, ym, 0.0
    slope = (dx * (y - ym)).sum() / denom
    intercept = ym - slope * xm
    pred = intercept + slope * x
    ss_res = ((y - pred) ** 2).sum()
    ss_tot = ((y - ym) ** 2).sum()
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return slope, intercept, r2


def rolling_ols(closes, w):
    """Rolling OLS over windows of length w (vectorized).

    Returns (slope[], intercept[], r2[]) where index i corresponds to the
    window closes[i .. i+w-1]. Vectorized because 1m data = 7.5M bars; the
    old per-window Python loop would take ~30 min per pass.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(closes, w)          # (n-w+1, w)
    x = np.arange(w, dtype=np.float64)
    xm = x.mean()
    dx = x - xm
    denom = float((dx * dx).sum())
    ym = win.mean(axis=1)
    slope = (win @ dx) / denom                    # sum(dx)=0 -> sum(dx*y)/denom
    inter = ym - slope * xm
    pred = inter[:, None] + slope[:, None] * x[None, :]
    ss_res = ((win - pred) ** 2).sum(axis=1)
    ss_tot = ((win - ym[:, None]) ** 2).sum(axis=1)
    r2 = np.where(ss_tot > 0, 1.0 - ss_res / np.where(ss_tot > 0, ss_tot, 1.0), 0.0)
    return slope, inter, r2


def compute_features(d):
    """Compute per-bar features using ONLY data up to and including that bar.

    Returns dict of arrays aligned to ts[WARMUP:] plus ts and fwd targets.
    """
    close = d['close']
    high = d['high']
    low = d['low']
    vol = d['vol']
    ts = d['ts']
    n = len(close)
    if n < WARMUP + max(HORIZONS):
        return None

    # True range / ATR(14)
    prev_close = close[:-1]
    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - prev_close),
                               np.abs(low[1:] - prev_close)))
    # ATR = simple moving average of TR
    atr = np.full(n, np.nan)
    if len(tr) >= W_ATR:
        atr_raw = np.convolve(tr, np.ones(W_ATR) / W_ATR, mode='valid')  # len n-1-W_ATR+1
        atr[W_ATR:] = atr_raw  # TR[i] corresponds to bar i+1

    # Rolling OLS (slope, intercept, r2) — slope aligned to window end
    slope, inter, r2 = rolling_ols(close, W_SLOPE)  # len n-W_SLOPE+1, idx i -> bar i+W_SLOPE-1
    reg_at_end = inter + slope * (W_SLOPE - 1)       # fitted value at window end
    # deviation from regression line in ATR units
    dev_atr = np.full(n, np.nan)
    sl_pct = np.full(n, np.nan)
    r2_a = np.full(n, np.nan)
    dev_atr[W_SLOPE - 1:] = (close[W_SLOPE - 1:] - reg_at_end) / atr[W_SLOPE - 1:]
    dev_atr[~np.isfinite(dev_atr)] = np.nan  # ATR==0 flat candles -> NaN, not inf
    sl_pct[W_SLOPE - 1:] = slope / close[W_SLOPE - 1:] * 100.0  # % of price per bar
    r2_a[W_SLOPE - 1:] = r2

    # volume z-score (rolling mean/var via cumsum — cleaning: guard zero std)
    vmean = np.full(n, np.nan)
    vstd = np.full(n, np.nan)
    if n >= W_VOL:
        csum = np.cumsum(vol)
        csum2 = np.cumsum(vol ** 2)
        idx = np.arange(n)
        start = idx - (W_VOL - 1)
        valid = start >= 0
        m = np.full(n, np.nan)
        s = np.full(n, np.nan)
        m[valid] = (csum[valid] - np.where(start[valid] > 0, csum[start[valid] - 1], 0.0)) / W_VOL
        mean2 = np.full(n, np.nan)
        mean2[valid] = (csum2[valid] - np.where(start[valid] > 0, csum2[start[valid] - 1], 0.0)) / W_VOL
        var = np.maximum(mean2 - m ** 2, 0.0)
        s = np.sqrt(var)
        vmean, vstd = m, s
    vol_z = (vol - vmean) / vstd
    vol_z[~np.isfinite(vol_z)] = np.nan

    # momentum (1h = 4 bars)
    mom = np.full(n, np.nan)
    mom[W_MOM:] = close[W_MOM:] / close[:-W_MOM] - 1.0

    # ATR compression
    atr_comp = atr / close * 100.0

    # range position over W_RANGE (vectorized sliding windows)
    rng_pos = np.full(n, np.nan)
    if n >= W_RANGE:
        from numpy.lib.stride_tricks import sliding_window_view
        hw = sliding_window_view(high, W_RANGE).max(axis=1)
        lw = sliding_window_view(low, W_RANGE).min(axis=1)
        span = hw - lw
        ok = span > 0
        rp = np.full(n - W_RANGE + 1, 0.5)
        rp[ok] = (close[W_RANGE - 1:][ok] - lw[ok]) / span[ok]
        rng_pos[W_RANGE - 1:] = rp

    feats = {
        'slope_pct': sl_pct,
        'r2': r2_a,
        'dev_atr': dev_atr,
        'vol_z': vol_z,
        'mom': mom,
        'atr_comp': atr_comp,
        'rng_pos': rng_pos,
    }

    # ── extra RenTech-style transforms ──────────────────────────────────
    # resid_z: regression residual normalized by residual stdev (classic
    # z-score of price vs its own fitted line — the purest 'one variable')
    resid_z = np.full(n, np.nan)
    if n >= W_SLOPE:
        from numpy.lib.stride_tricks import sliding_window_view
        win = sliding_window_view(close, W_SLOPE)          # (n-W+1, W)
        xw_ = np.arange(W_SLOPE, dtype=np.float64)
        fitted = inter[:, None] + slope[:, None] * xw_[None, :]
        resid = win - fitted
        sd = resid.std(axis=1, ddof=1)
        last_res = resid[:, -1]
        ok = sd > 0
        rz = np.full(len(sd), np.nan)
        rz[ok] = last_res[ok] / sd[ok]
        resid_z[W_SLOPE - 1:] = rz
    # slope_atr: slope expressed in ATR units per bar (vol-normalized trend)
    slope_atr = np.full(n, np.nan)
    slope_atr[W_SLOPE - 1:] = slope / atr[W_SLOPE - 1:]
    slope_atr[~np.isfinite(slope_atr)] = np.nan
    feats['resid_z'] = resid_z
    feats['slope_atr'] = slope_atr

    # forward returns (targets)
    fwd = {}
    for H in HORIZONS:
        f = np.full(n, np.nan)
        f[:-H] = close[H:] / close[:-H] - 1.0
        fwd[f'H{H}'] = f

    # mask warmup
    start = WARMUP
    return dict(ts=ts[start:], feats={k: v[start:] for k, v in feats.items()},
                fwd={k: v[start:] for k, v in fwd.items()})


def winsorize(x, pct=WINSOR_PCT):
    """1/99 winsorization restricted to FINITE values.

    Cleaning lesson: inf values (e.g. divide-by-zero on flat candles) poison
    nanpercentile via inf-inf=nan and silently nuke the whole array. Non-finite
    entries become NaN and are excluded downstream instead.
    """
    out = np.array(x, dtype=np.float64, copy=True)
    m = np.isfinite(out)
    if m.sum() < 10:
        out[:] = np.nan
        return out
    lo, hi = np.nanpercentile(out[m], [pct, 100 - pct])
    out[m] = np.clip(out[m], lo, hi)
    out[~m] = np.nan
    return out


def spearman(x, y):
    """Spearman rank IC with t-test p-value approximation."""
    m = np.isfinite(x) & np.isfinite(y)
    xr, yr = x[m], y[m]
    n = len(xr)
    if n < 30:
        return np.nan, np.nan, n
    rx = np.argsort(np.argsort(xr)).astype(np.float64)
    ry = np.argsort(np.argsort(yr)).astype(np.float64)
    rx -= rx.mean()
    ry -= ry.mean()
    denom = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    if denom <= 0:
        return np.nan, np.nan, n
    ic = (rx * ry).sum() / denom
    # t-test for correlation
    if abs(ic) >= 1.0:
        return ic, 0.0, n
    t = ic * np.sqrt((n - 2) / (1 - ic ** 2))
    # two-sided p via survival function of t (use normal approx for large n)
    from math import erf, sqrt
    p = 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / sqrt(2.0))))  # normal approx (n large)
    return ic, p, n


def sign_split(x, y):
    """Nonlinear transform: sign(x). Mean target when x>0 vs x<0, Welch t-test."""
    m = np.isfinite(x) & np.isfinite(y)
    xs, ys = x[m], y[m]
    pos = ys[xs > 0]
    neg = ys[xs < 0]
    n1, n2 = len(pos), len(neg)
    if n1 < 30 or n2 < 30:
        return np.nan, np.nan, n1, n2, np.nan, np.nan
    m1, m2 = pos.mean(), neg.mean()
    v1, v2 = pos.var(ddof=1), neg.var(ddof=1)
    se = np.sqrt(v1 / n1 + v2 / n2)
    if se <= 0:
        return np.nan, np.nan, n1, n2, m1, m2
    t = (m1 - m2) / se
    from math import erf, sqrt
    p = 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / sqrt(2.0))))
    return m1 - m2, p, n1, n2, m1, m2


def ttest_mean(y, mu0=0.0):
    """One-sample t-test of mean(y) vs mu0. Returns (mean, diff, p, n)."""
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 30:
        return np.nan, np.nan, np.nan, n
    m = y.mean()
    se = y.std(ddof=1) / np.sqrt(n)
    if se <= 0:
        return m, m - mu0, np.nan, n
    t = (m - mu0) / se
    from math import erf, sqrt
    p = 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / sqrt(2.0))))
    return m, m - mu0, p, n


def shape_analysis(samples, t_split):
    """Decile shape + extreme-threshold tradeability on OOS data ONLY.

    The relationship need not be linear — RenTech's 'should you do a nonlinear
    transform before you regress' means we must LOOK at the shape first.
    A signal only ships if the tradeable extreme (top/bottom decile) clears
    the 0.09% round-trip fee with p <= 0.05 out-of-sample.
    """
    print('\n' + '=' * 78)
    print('SHAPE + TRADEABLE THRESHOLDS (OOS only, winsorized, vs fee bar 0.09%)')
    print('=' * 78)
    for f in FEATURES:
        for H in HORIZONS:
            ts_all = np.concatenate([t for t, _, _ in samples[f][H]])
            x_all = np.concatenate([x for _, x, _ in samples[f][H]])
            y_all = np.concatenate([y for _, _, y in samples[f][H]])
            xw = winsorize(x_all)
            yw = winsorize(y_all)
            oos = (ts_all > t_split) & np.isfinite(xw) & np.isfinite(yw)
            x, y = xw[oos], yw[oos]
            if len(x) < 1000:
                continue
            # decile shape
            qs = np.percentile(x, np.arange(0, 101, 10))
            dec_means = []
            for i in range(10):
                m = (x >= qs[i]) & (x <= qs[i + 1])
                dec_means.append(y[m].mean() * 100 if m.sum() > 30 else np.nan)
            shape = ' '.join(f'{d:+.3f}' if np.isfinite(d) else '  n/a ' for d in dec_means)
            print(f'\n{f} H{H}  OOS decile mean fwd% (D1->D10): {shape}')

            # extreme thresholds: bottom decile and top decile
            for label, m in [('D1', x <= qs[1]), ('D10', x >= qs[9]),
                             ('D1+D2', x <= qs[2]), ('D9+D10', x >= qs[8])]:
                mean, diff, p, n = ttest_mean(y[m] * 100)
                if not np.isfinite(mean):
                    continue
                clears = abs(diff) >= 0.09
                verdict = 'SHIP' if (p <= 0.05 and clears) else \
                          ('sig<fee' if p <= 0.05 else 'weak')
                print(f'   {label:6} n={n:>7} mean={mean:+.4f}%  vs0 p={p:.2e}  '
                      f'|edge|>=0.09%: {clears}  -> {verdict}')


def configure(tf, slope_w=None):
    """Set timeframe-dependent globals. CLI: --tf 1m|5m|15m [--slope W]."""
    global TABLE, MIN_BARS, WARMUP, HORIZONS, W_SLOPE, W_VOL, W_MOM, W_RANGE
    global HOLDOUT_DAYS
    if tf == '1m':
        TABLE = 'candles_1m'
        MIN_BARS = 2000          # ~1.4 days — includes newer listings
        WARMUP = 600
        HORIZONS = [60, 120, 240, 480]   # 1h, 2h, 4h, 8h in 1m bars
        W_SLOPE = slope_w or 20
        W_VOL = 60
        W_MOM = 60
        W_RANGE = 60
        HOLDOUT_DAYS = 7         # 1m data only spans ~30 days
    elif tf == '5m':
        TABLE = 'candles_5m'
        MIN_BARS = 1000
        WARMUP = 200
        HORIZONS = [12, 24, 48, 96]      # 1h, 2h, 4h, 8h in 5m bars
        W_SLOPE = slope_w or 12
        W_VOL = 24
        W_MOM = 12
        W_RANGE = 24
        HOLDOUT_DAYS = 7
    else:  # 15m defaults (already tuned)
        if slope_w:
            W_SLOPE = slope_w


def main():
    # CLI: --tf 1m|5m|15m  [--slope W]
    tf = '15m'
    slope_w = None
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == '--tf' and i + 1 < len(argv):
            tf = argv[i + 1]
        elif a == '--slope' and i + 1 < len(argv):
            slope_w = int(argv[i + 1])
    configure(tf, slope_w)
    print('=' * 78)
    print(f'RENTECH-STYLE UNIVARIATE REGRESSION RESEARCH ({TABLE}, '
          f'slope_w={W_SLOPE}, horizons={HORIZONS})')
    print('=' * 78)
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    ts_cut_is = None  # set after load
    data = load_token(0, now, min_bars=MIN_BARS)
    print(f'tokens loaded: {len(data)}')

    # assemble pooled samples
    all_ts = []
    samples = {f: {h: [] for h in HORIZONS} for f in FEATURES}
    # for monthly stability we keep (ts, feat, fwd) tuples per feature/horizon

    for tok, d in data.items():
        r = compute_features(d)
        if r is None:
            continue
        ts = r['ts'].astype(np.float64)
        all_ts.append(ts)
        for f, fv in r['feats'].items():
            for H in HORIZONS:
                samples[f][H].append((ts, fv, r['fwd'][f'H{H}']))

    all_ts = np.concatenate(all_ts)
    t_max = all_ts.max()
    t_min = all_ts.min()
    # IS/OOS split by TIME (not random) — no lookahead leakage
    t_split = t_min + (t_max - t_min) * IS_FRAC
    t_holdout = t_max - HOLDOUT_DAYS * 86400
    print(f'time span: {datetime.datetime.utcfromtimestamp(t_min)} -> '
          f'{datetime.datetime.utcfromtimestamp(t_max)}')
    print(f'IS/OOS boundary: {datetime.datetime.utcfromtimestamp(t_split)}  '
          f'holdout start: {datetime.datetime.utcfromtimestamp(t_holdout)}')

    print('\n' + '=' * 78)
    print('POOLED SPEARMAN IC  (predictor vs forward return)')
    print(f'IS = before split | OOS = after split | HOLD = last {HOLDOUT_DAYS} days')
    print('=' * 78)
    hdr = f"{'feature':10} {'H':>3} {'n':>8} {'IC_all':>8} {'p':>9} {'IC_IS':>8} {'IC_OOS':>8} {'p_OOS':>9} {'IC_HOLD':>8} {'verdict':>10}"
    print(hdr)

    results = []
    for f in samples:
        for H in HORIZONS:
            ts_all = np.concatenate([t for t, _, _ in samples[f][H]])
            x_all = np.concatenate([x for _, x, _ in samples[f][H]])
            y_all = np.concatenate([y for _, _, y in samples[f][H]])
            # cleaning: winsorize predictor and target on pooled sample
            xw = winsorize(x_all)
            yw = winsorize(y_all)

            ic, p, n = spearman(xw, yw)

            is_m = ts_all <= t_split
            oos_m = ts_all > t_split
            hold_m = ts_all >= t_holdout
            ic_is, p_is, _ = spearman(xw[is_m], yw[is_m])
            ic_oos, p_oos, _ = spearman(xw[oos_m], yw[oos_m])
            ic_hold, p_hold, _ = spearman(xw[hold_m], yw[hold_m])

            # verdict: rubbish if OOS sign flips or OOS p>0.05
            if not np.isfinite(ic_oos) or not np.isfinite(ic_is):
                verdict = 'NO DATA'
            elif np.sign(ic_oos) != np.sign(ic_is):
                verdict = 'RUBBISH'
            elif p_oos > 0.05:
                verdict = 'weak'
            else:
                verdict = 'CANDIDATE'
            results.append((f, H, n, ic, p, ic_is, ic_oos, p_oos, ic_hold, verdict))
            print(f"{f:10} {H:>3} {n:>8} {ic:>8.4f} {p:>9.2e} {ic_is:>8.4f} "
                  f"{ic_oos:>8.4f} {p_oos:>9.2e} {ic_hold:>8.4f} {verdict:>10}")

    print('\n' + '=' * 78)
    print('NONLINEAR TRANSFORM: sign(x) split — mean fwd return when x>0 vs x<0')
    print('=' * 78)
    print(f"{'feature':10} {'H':>3} {'n_pos':>7} {'n_neg':>7} {'mean+':>9} {'mean-':>9} "
          f"{'diff':>9} {'p':>9} {'verdict':>10}")
    sign_results = []
    for f in samples:
        for H in HORIZONS:
            ts_all = np.concatenate([t for t, _, _ in samples[f][H]])
            x_all = np.concatenate([x for _, x, _ in samples[f][H]])
            y_all = np.concatenate([y for _, _, y in samples[f][H]])
            xw = winsorize(x_all)
            yw = winsorize(y_all)
            oos_m = ts_all > t_split
            xo, yo = xw[oos_m], yw[oos_m]
            # nonlinear transform: sign() when x spans zero, else median split
            # (r2/rng_pos/atr_comp are non-negative — sign() has no control group)
            if np.nanmin(xo) < 0 < np.nanmax(xo):
                split_at = 0.0
            else:
                split_at = float(np.nanmedian(xo))
            m = np.isfinite(xo) & np.isfinite(yo)
            diff, p, n1, n2, m1, m2 = sign_split(xo[m] - split_at, yo[m])
            if np.isnan(diff):
                verdict = 'NO DATA'
            elif p > 0.05:
                verdict = 'weak'
            elif np.sign(diff) != 0:
                verdict = 'CANDIDATE' if p <= 0.05 else 'weak'
            else:
                verdict = 'weak'
            sign_results.append((f, H, n1, n2, m1, m2, diff, p, verdict))
            fmt = lambda v: f'{v*100:+.4f}%' if np.isfinite(v) else 'n/a'
            print(f"{f:10} {H:>3} {n1:>7} {n2:>7} {fmt(m1):>9} {fmt(m2):>9} "
                  f"{fmt(diff):>9} {p:>9.2e} {verdict:>10}")

    print('\n' + '=' * 78)
    print('MONTHLY IC STABILITY (Spearman, per month, pooled across tokens)')
    print('=' * 78)
    H_REF = HORIZONS[len(HORIZONS) // 2]   # middle horizon for stability view
    for f in ['slope_pct', 'resid_z', 'slope_atr', 'r2', 'vol_z', 'mom', 'rng_pos']:
        H = H_REF
        ts_all = np.concatenate([t for t, _, _ in samples[f][H]])
        x_all = np.concatenate([x for _, x, _ in samples[f][H]])
        y_all = np.concatenate([y for _, _, y in samples[f][H]])
        xw = winsorize(x_all)
        yw = winsorize(y_all)
        months = np.array([datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m')
                           for t in ts_all])
        ics = []
        for mo in np.unique(months):
            m = months == mo
            ic, p, n = spearman(xw[m], yw[m])
            if np.isfinite(ic) and n > 500:
                ics.append((mo, ic, p))
        signs = [np.sign(ic) for _, ic, _ in ics]
        pos_frac = sum(1 for s in signs if s > 0) / len(signs) if signs else 0
        line = ' '.join(f'{mo[-2:]}:{ic:+.3f}' for mo, ic, _ in ics)
        print(f'{f:10} H{H} months={len(ics):>3} pos_frac={pos_frac:.2f} | {line}')

    shape_analysis(samples, t_split)

    # cost check: is the average |fwd return| even tradeable?
    print('\n' + '=' * 78)
    print('COST BAR: mean forward returns (round-trip taker fee = 0.09%)')
    print('=' * 78)
    for H in HORIZONS:
        y = np.concatenate([y for f in samples for _, _, y in samples[f][H][:1]])
        print(f'H={H}: mean={np.nanmean(y)*100:+.4f}%  '
              f'std={np.nanstd(y)*100:.4f}%  '
              f'|mean|={np.nanmean(np.abs(y))*100:.4f}%')


if __name__ == '__main__':
    main()
