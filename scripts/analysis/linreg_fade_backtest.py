#!/usr/bin/env python3
"""
linreg_fade_backtest.py — Event-based validation of the linreg extreme-slope
mean-reversion finding from linreg_forecast_research.py.

VALIDATION HISTORY (why this file looks the way it does):
  Round 1 (4h hold): pooled ICs p<1e-16, but event expectancy flipped sign
      IS<->OOS after fees -> edge declared rubbish at 4h.
  Round 2 (8h hold): edge strengthens at 8h. LONG fade selection alpha vs
      blind-long was STABLE (+0.26% IS / +0.26% OOS) but absolute PnL flips
      with market beta (Aug-Sep up, Oct-Nov down). ATR 1:1.5 stops KILL the
      edge (WR 38-46% < 46% breakeven). BTC-24h regime gate FAILED OOS
      (OOS LONG got worse, not better) -> gate abandoned, not re-tuned.
  Round 3 (1m candles, user's trading TF): same structure, per-token trailing
      P10/P90 thresholds computed vectorized with stride (exact per-bar
      percentile at 7.6M bars = hours of runtime).

RULES (all no-lookahead):
  - trigger: OLS slope over SLOPE_W bars vs the token's OWN trailing P10/P90
    of the previous TRAIL_PCT_WIN slopes (threshold from bars < t only)
  - entry at next bar open
  - exits: V1 = fixed hold; V2 = ATR SL/TP with hold as time exit
  - fees 0.09% round trip
  - IS/OOS split by time; baseline = unconditional same-universe returns

Usage:
    python3 scripts/analysis/linreg_fade_backtest.py [--tf 15m|1m|5m] [--slope W]
"""

import os
import sys
import sqlite3
import datetime
from collections import Counter

import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA  # noqa: E402
from linreg_forecast_research import load_token, rolling_ols, WARMUP  # noqa: E402

CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
TABLE = 'candles_15m'
SLOPE_W = 20             # OLS slope window (bars)
REGIME_SHIFT = 96        # BTC drift lookback in bars (24h at 15m)
PCT_STRIDE = 15          # recompute trailing percentile every N bars

FEE_RT = 0.09            # round-trip taker fee, % of notional (0.045% x 2)
HOLD_BARS = 32           # 8h at 15m
TRAIL_PCT_WIN = 500      # trailing window for P10/P90 slope percentile
W_ATR = 14
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.25

# (name, mode, sl_mult, tp_mult, gate_type)
# gate_type: 'none' | 'btc24' (BTC 24h drift — FAILED OOS, kept for record)
#            | 'regime4h' (per-token regime as 4h_regime_scanner computes it)
VARIANTS = [
    ('V1 fixed hold', 'fixed', 0.0, 0.0, 'none'),
    ('V2 ATR SL1.5/TP2.25 + time', 'atr', SL_ATR_MULT, TP_ATR_MULT, 'none'),
    # V6 = PRODUCTION exits: ATR_SL_MIN 1.5%..2.5% SL, 1.5%..2% TP,
    # trailing act 0.40% dist 1.20% (TRAILING_* constants), 8h universal hold
    ('V6 PROD exits (SL2/TP2/trail/8h)', 'prod', 0.02, 0.02, 'none'),
    ('V7 WIDE SL6/noTP/trail/8h', 'prod', 0.06, 0.0, 'none'),
    # V8 = V7 without the trailing stop — isolates whether TRAILING (not SL
    # level) is what destroys the edge. deployable if decider passes an
    # explicit never-arming trailing activation for this source.
    ('V8 WIDE SL6/noTP/NOtrail/8h', 'prod_nt', 0.06, 0.0, 'none'),
    # V9 = V8 + the SOFT_TRAIL safety net that position_manager applies to ALL
    # non-CEO trades (2h, pnl<=0 -> SL trails 0.6% behind price). This is the
    # TRUE production number for the new signal.
    ('V9 V8+SOFT_TRAIL(2h/0.6%)', 'prod_st', 0.06, 0.0, 'none'),
    # V10/V11 = V8 + the hard_max_loss account floor (-4% account / leverage),
    # modeled as a hard price-level early close (bug_hunter Issue 4). The floor
    # is NOT exempted — these runs quantify what it costs at each leverage.
    ('V10 V8+HML floor -0.8% (lev5)', 'prod_hml', 0.008, 0.0, 'none'),
    ('V11 V8+HML floor -4.0% (lev1)', 'prod_hml', 0.040, 0.0, 'none'),
]


def variants_for(tf):
    if tf == '15m':
        return VARIANTS + [
            ('V3 fixed 8h + BTC24 GATE', 'fixed', 0.0, 0.0, 'btc24'),
            ('V4 ATR SL3.0/TP4.5 + BTC24 GATE', 'atr', 3.0, 4.5, 'btc24'),
            ('V5 fixed 8h + REGIME4H GATE', 'fixed', 0.0, 0.0, 'regime4h'),
        ]
    return VARIANTS + [
        ('V5 fixed 8h + REGIME4H GATE', 'fixed', 0.0, 0.0, 'regime4h'),
    ]


def configure(tf, slope_w=None):
    """CLI config. Must be called before run_events/main uses the globals."""
    global TABLE, HOLD_BARS, TRAIL_PCT_WIN, SLOPE_W, REGIME_SHIFT
    import linreg_forecast_research as R
    R.configure(tf, slope_w)
    TABLE = R.TABLE
    if tf == '1m':
        HOLD_BARS = 480        # 8h
        TRAIL_PCT_WIN = 4320   # 3 days of 1m slopes
        REGIME_SHIFT = 1440    # BTC 24h drift in 1m bars
    elif tf == '5m':
        HOLD_BARS = 96
        TRAIL_PCT_WIN = 864
        REGIME_SHIFT = 288
    SLOPE_W = slope_w or R.W_SLOPE


def load_btc_regime():
    """BTC drift per bar ts: close[t]/close[t-REGIME_SHIFT] - 1 (24h)."""
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    try:
        rows = conn.execute(
            f"SELECT ts, close FROM {TABLE} WHERE token='BTC' AND is_closed=1 "
            f"ORDER BY ts").fetchall()
    finally:
        conn.close()
    out = {}
    closes = [r[1] for r in rows]
    for i, (ts, _) in enumerate(rows):
        if i >= REGIME_SHIFT and closes[i - REGIME_SHIFT] > 0:
            out[int(ts)] = closes[i] / closes[i - REGIME_SHIFT] - 1.0
    return out


def load_regime4h():
    """Per-token regime series mirroring 4h_regime_scanner exactly:
    6 closed 4h candles -> slope_pct (per y_mean) + R2 -> determine_regime()
    rules (constants from hermes_constants). Returns {token: (close_ts[], regime[])}
    where close_ts = candle_ts + 4h (conservative: only fully-closed candles).
    """
    from hermes_constants import (
        REGIME_SCANNER_TREND_THRESHOLD, REGIME_SCANNER_NEUTRAL_THRESHOLD,
        REGIME_SCANNER_R2_TREND, REGIME_SCANNER_R2_WEAK,
    )
    W4 = 6  # 4h scanner fetches limit=6 candles
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    try:
        toks = [r[0] for r in conn.execute(
            "SELECT DISTINCT token FROM candles_4h WHERE is_closed=1")]
        out = {}
        for tok in toks:
            rows = conn.execute(
                "SELECT ts, close FROM candles_4h WHERE token=? AND is_closed=1 "
                "AND close > 0 ORDER BY ts", (tok,)).fetchall()
            if len(rows) < W4 + 1:
                continue
            ts4 = np.array([r[0] for r in rows], dtype=np.int64)
            closes = np.array([r[1] for r in rows], dtype=np.float64)
            slope, inter, r2 = rolling_ols(closes, W4)
            ymean = inter + slope * ((W4 - 1) / 2.0)
            slope_pct = slope / ymean * 100.0
            regimes = []
            for i in range(len(slope_pct)):
                sp, rr = float(slope_pct[i]), float(r2[i])
                if sp > REGIME_SCANNER_TREND_THRESHOLD and rr > REGIME_SCANNER_R2_TREND:
                    regimes.append('LONG_BIAS')
                elif sp < -REGIME_SCANNER_TREND_THRESHOLD and rr > REGIME_SCANNER_R2_TREND:
                    regimes.append('SHORT_BIAS')
                elif abs(sp) < REGIME_SCANNER_NEUTRAL_THRESHOLD:
                    regimes.append('NEUTRAL')
                elif sp > 0 and rr > REGIME_SCANNER_R2_WEAK:
                    regimes.append('LONG_BIAS')
                elif sp < 0 and rr > REGIME_SCANNER_R2_WEAK:
                    regimes.append('SHORT_BIAS')
                else:
                    regimes.append('NEUTRAL')
            # window i (regimes[i]) uses closes[i..i+5]; the last candle of
            # that window closes at ts4[i+5]+4h -> pair regimes (len n-W4+1)
            # with ts4[W4-1:]+14400 (same length). MISALIGNMENT BUG fixed:
            # slicing regimes[W4-1:] dropped 5 entries and crashed searchsorted.
            close_ts = ts4[W4 - 1:] + 14400
            regime_arr = np.array(regimes, dtype=object)
            assert len(close_ts) == len(regime_arr), \
                f'regime4h misalignment {tok}: {len(close_ts)} vs {len(regime_arr)}'
            out[tok] = (close_ts, regime_arr)
        return out
    finally:
        conn.close()


def compute_slope_atr(d):
    """slope_pct aligned to bar t (uses closes[t-SLOPE_W+1..t]), ATR14 at t."""
    close, high, low = d['close'], d['high'], d['low']
    n = len(close)
    slope, inter, r2 = rolling_ols(close, SLOPE_W)
    sl = np.full(n, np.nan)
    sl[SLOPE_W - 1:] = slope / close[SLOPE_W - 1:] * 100.0
    prev_close = close[:-1]
    tr = np.maximum(high[1:] - low[1:], np.maximum(
        np.abs(high[1:] - prev_close), np.abs(low[1:] - prev_close)))
    atr = np.full(n, np.nan)
    atr_raw = np.convolve(tr, np.ones(W_ATR) / W_ATR, mode='valid')
    atr[W_ATR:] = atr_raw
    atr[~np.isfinite(atr) | (atr <= 0)] = np.nan
    return sl, atr


def trailing_thresholds(sl, win, stride=PCT_STRIDE):
    """Trailing P10/P90 of sl over the previous `win` bars, recomputed every
    `stride` bars (threshold moves slowly; exact per-bar percentile at 7.6M
    bars costs hours). Window at bar t uses sl[t-win .. t-1] ONLY (no lookahead).

    Returns (p10[], p90[]) aligned to bar index, NaN where unavailable.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    n = len(sl)
    out10 = np.full(n, np.nan)
    out90 = np.full(n, np.nan)
    if n < win + 2:
        return out10, out90
    views = sliding_window_view(sl, win)   # views[k] = sl[k : k+win]
    for k0 in range(0, len(views), stride):
        seg = views[k0]
        fin = seg[np.isfinite(seg)]
        if len(fin) < win * 0.9:
            continue
        lo, hi = np.percentile(fin, [10, 90])
        t_start = k0 + win          # window sl[k0:k0+win] is valid for bar t=k0+win
        t_end = min(t_start + stride, n)
        out10[t_start:t_end] = lo
        out90[t_start:t_end] = hi
    return out10, out90


def simulate(side, entry, a, e, n, mode, sl_m, tp_m, close, high, low, hold):
    """Walk forward from bar e (entry bar). Returns (exit_px, kind, exit_i).

    modes: fixed = time exit only | atr = ATR-scaled SL/TP
           prod  = production exits (fixed % SL/TP + trailing + time exit)
    """
    if mode in ('prod', 'prod_nt', 'prod_st', 'prod_hml'):
        from hermes_constants import (TRAILING_ACTIVATION_PCT as ACT,
                                      TRAILING_DISTANCE_PCT as DIST)
        sl_frac, tp_frac = sl_m, tp_m
        has_tp = tp_frac > 0
        use_trail = (mode == 'prod')   # 'prod_nt'/'prod_st' = trailing disabled
        # SOFT_TRAIL: position_manager tightens losing trades after 2h
        # (SOFT_TRIGGER_HOURS=2.0, SOFT_TRAIL_PCT=0.006, raise/lower only)
        use_soft = (mode == 'prod_st')
        soft_bars = max(1, hold // 4)   # 2h in bars (hold = 8h)
        # HML: hard_max_loss floor — adverse price move >= sl_m (0.008/0.040)
        # closes the trade at market (bug_hunter Issue 4; NOT exempted)
        hml_floor = sl_m if mode == 'prod_hml' else None
        if hml_floor:
            sl_frac = 0.06   # wide 6% backstop still present
        if side == 'LONG':
            stop = entry * (1 - sl_frac)
            tp_px = entry * (1 + tp_frac) if has_tp else None
            arm = entry * (1 + ACT)
            peak = entry
            for i in range(e, min(e + hold, n)):
                hi, lo = high[i], low[i]
                if hi > peak:
                    peak = hi
                if use_trail and peak >= arm:
                    stop = max(stop, peak * (1 - DIST))
                if use_soft and i - e + 1 >= soft_bars and close[i] < entry:
                    stop = max(stop, close[i] * (1 - 0.006))  # raise-only
                if hml_floor is not None and close[i] <= entry * (1 - hml_floor):
                    return close[i], 'HML', i
                if lo <= stop:
                    return stop, 'SL', i
                if tp_px is not None and hi >= tp_px:
                    return tp_px, 'TP', i
                if i - e + 1 >= hold:
                    return close[i], 'TIME', i
        else:
            stop = entry * (1 + sl_frac)
            tp_px = entry * (1 - tp_frac) if has_tp else None
            arm = entry * (1 - ACT)
            trough = entry
            for i in range(e, min(e + hold, n)):
                hi, lo = high[i], low[i]
                if lo < trough:
                    trough = lo
                if use_trail and trough <= arm:
                    stop = min(stop, trough * (1 + DIST))
                if use_soft and i - e + 1 >= soft_bars and close[i] > entry:
                    stop = min(stop, close[i] * (1 + 0.006))  # lower-only
                if hml_floor is not None and close[i] >= entry * (1 + hml_floor):
                    return close[i], 'HML', i
                if hi >= stop:
                    return stop, 'SL', i
                if tp_px is not None and lo <= tp_px:
                    return tp_px, 'TP', i
                if i - e + 1 >= hold:
                    return close[i], 'TIME', i
        if e + hold <= n:
            j = min(e + hold - 1, n - 1)
            return close[j], 'TIME', j
        return None, None, None
    if mode == 'fixed':
        i = min(e + hold - 1, n - 1)
        return close[i], 'TIME', i
    sl_px = entry - sl_m * a * (1 if side == 'LONG' else -1)
    tp_px = entry + tp_m * a * (1 if side == 'LONG' else -1)
    for i in range(e, min(e + hold, n)):
        hi, lo = high[i], low[i]
        if side == 'LONG':
            if lo <= sl_px:
                return sl_px, 'SL', i
            if hi >= tp_px:
                return tp_px, 'TP', i
        else:
            if hi >= sl_px:
                return sl_px, 'SL', i
            if lo <= tp_px:
                return tp_px, 'TP', i
        if i - e + 1 >= hold:
            return close[i], 'TIME', i
    if e + hold <= n:
        j = min(e + hold - 1, n - 1)
        return close[j], 'TIME', j
    return None, None, None


def run_events(data, split_ts, variants, gate_type='none',
               regime=None, regime4h=None):
    """One pass per token: thresholds once, then simulate every variant."""
    events = {v[0]: [] for v in variants}
    baselines = []
    gated = {'LONG': 0, 'SHORT': 0}
    for tok, d in data.items():
        close, open_, high, low = d['close'], d['open'], d['high'], d['low']
        ts = d['ts']
        n = len(close)
        sl, atr = compute_slope_atr(d)
        p10, p90 = trailing_thresholds(sl, TRAIL_PCT_WIN)
        start = TRAIL_PCT_WIN + SLOPE_W + 1
        next_allowed = start
        for t in range(start, n - HOLD_BARS - 1):
            if t < next_allowed:
                continue  # one position at a time per token (no overlap)
            x = sl[t]
            if not np.isfinite(x) or not np.isfinite(p10[t]):
                continue
            if x <= p10[t]:
                side = 'LONG'
            elif x >= p90[t]:
                side = 'SHORT'
            else:
                continue

            if gate_type == 'btc24' and regime:
                drift = regime.get(int(ts[t]))
                if drift is not None:
                    if side == 'LONG' and drift <= 0:
                        gated['LONG'] += 1
                        continue
                    if side == 'SHORT' and drift >= 0:
                        gated['SHORT'] += 1
                        continue
            elif gate_type == 'regime4h' and regime4h is not None:
                r4 = regime4h.get(tok)
                if r4 is None:
                    gated[side] += 1
                    continue
                close_ts_arr, regime_arr = r4
                idx = int(np.searchsorted(close_ts_arr, ts[t], side='right')) - 1
                if idx < 0:
                    gated[side] += 1
                    continue
                idx = min(idx, len(close_ts_arr) - 1)  # clamp: last known
                # regime stands until the next 4h candle closes
                cur_regime = regime_arr[idx]
                if side == 'LONG' and cur_regime != 'LONG_BIAS':
                    gated['LONG'] += 1
                    continue
                if side == 'SHORT' and cur_regime != 'SHORT_BIAS':
                    gated['SHORT'] += 1
                    continue

            e = t + 1
            if e >= n or not np.isfinite(open_[e]) or open_[e] <= 0:
                continue
            entry = open_[e]
            a = atr[t]
            if not np.isfinite(a):
                continue

            last_exit = t
            for vname, mode, sl_m, tp_m, vgate in variants:
                if vgate != gate_type:
                    continue
                exit_px, kind, exit_i = simulate(
                    side, entry, a, e, n, mode, sl_m, tp_m,
                    close, high, low, HOLD_BARS)
                if exit_px is None:
                    continue
                gross = ((exit_px - entry) if side == 'LONG' else
                         (entry - exit_px)) / entry * 100.0
                events[vname].append(dict(
                    token=tok, ts=int(ts[e]), side=side, entry=entry,
                    slope=float(x), p10=float(p10[t]), p90=float(p90[t]),
                    exit_kind=kind, bars=exit_i - e + 1,
                    gross=gross, net=gross - FEE_RT,
                    oos=bool(ts[e] > split_ts),
                    month=datetime.datetime.utcfromtimestamp(
                        int(ts[e])).strftime('%Y-%m'),
                ))
                last_exit = max(last_exit, exit_i)
            next_allowed = last_exit + 1

        # baseline: unconditional 8h returns for EVERY token (beta reference)
        for t in range(WARMUP, n - HOLD_BARS - 1, 4):  # stride 4: mean only
            entry = open_[t + 1] if (np.isfinite(open_[t + 1])
                                     and open_[t + 1] > 0) else close[t]
            if not np.isfinite(entry) or entry <= 0:
                continue
            r = (close[t + HOLD_BARS] - entry) / entry * 100.0
            baselines.append((int(ts[t]), r))
    return events, baselines, gated


def summarize(ev, key='net'):
    n = len(ev)
    if n == 0:
        return None
    wins = sum(1 for e in ev if e[key] > 0)
    return (n, 100.0 * wins / n, float(np.mean([e[key] for e in ev])),
            float(sum(e[key] for e in ev)), float(np.median([e[key] for e in ev])))


def report(vname, evs, baselines, gated, gate_type):
    print('\n' + '=' * 78)
    print(f'{vname}  |  events={len(evs)}'
          + (f'  |  gated out: {gated}' if gate_type != 'none' else ''))
    print('=' * 78)
    if baselines:
        b_is = [r for t, r in baselines if t <= split_ts_g]
        b_oos = [r for t, r in baselines if t > split_ts_g]
        print(f'BASELINE unconditional 8h: IS mean={np.mean(b_is):+.4f}% | '
              f'OOS mean={np.mean(b_oos):+.4f}% | '
              f'OOS blind-short={-np.mean(b_oos):+.4f}% gross '
              f'({-np.mean(b_oos) - FEE_RT:+.4f}% net)')
    for period, sel in [('IS ', lambda e: not e['oos']),
                        ('OOS', lambda e: e['oos']),
                        ('ALL', lambda e: True)]:
        sub = [e for e in evs if sel(e)]
        if not sub:
            continue
        for side in ['LONG', 'SHORT']:
            r = summarize([e for e in sub if e['side'] == side])
            if not r:
                print(f'  [{period}] {side:6} n=0')
                continue
            n, w, avg, tot, med = r
            c = Counter(e['exit_kind'] for e in sub if e['side'] == side)
            print(f'  [{period}] {side:6} n={n:<6} WR={w:5.1f}% avg_net={avg:+.4f}% '
                  f'med={med:+.4f}% total={tot:+.1f} exits={dict(c)}')
    print('  --- by month ---')
    for mo in sorted(set(e['month'] for e in evs)):
        sub = [e for e in evs if e['month'] == mo]
        parts = []
        for side in ['LONG', 'SHORT']:
            r = summarize([e for e in sub if e['side'] == side])
            if r:
                parts.append(f'{side}: n={r[0]:<5} WR={r[1]:4.1f}% avg={r[2]:+.3f}% '
                             f'tot={r[3]:+.1f}')
            else:
                parts.append(f'{side}: n=0')
        tag = 'OOS' if any(e['oos'] for e in sub) else 'IS '
        print(f'    {mo} [{tag}] ' + ' | '.join(parts))


split_ts_g = None  # set in main for report()


def main():
    global split_ts_g
    argv = sys.argv[1:]
    tf = '15m'
    slope_w = None
    for i, a in enumerate(argv):
        if a == '--tf' and i + 1 < len(argv):
            tf = argv[i + 1]
        elif a == '--slope' and i + 1 < len(argv):
            slope_w = int(argv[i + 1])
    configure(tf, slope_w)
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    import linreg_forecast_research as _R
    data = load_token(0, now, min_bars=_R.MIN_BARS)
    all_ts = np.concatenate([d['ts'] for d in data.values()])
    t_min, t_max = all_ts.min(), all_ts.max()
    split_ts = t_min + (t_max - t_min) * 0.70
    split_ts_g = split_ts
    print(f'tokens={len(data)} span='
          f'{datetime.datetime.utcfromtimestamp(t_min)} -> '
          f'{datetime.datetime.utcfromtimestamp(t_max)}')
    print(f'IS/OOS split: {datetime.datetime.utcfromtimestamp(split_ts)}  '
          f'tf={TABLE} slope_w={SLOPE_W} hold={HOLD_BARS} bars  '
          f'trail_win={TRAIL_PCT_WIN} stride={PCT_STRIDE}  fees={FEE_RT}% RT')

    variants = variants_for(tf)
    regime = load_btc_regime()
    regime4h = load_regime4h()
    print(f'regime proxies: btc24 points={len(regime)}  '
          f'regime4h tokens={len(regime4h)}')

    events, baselines, gated_by_gt = {}, None, {}
    for gt in sorted({v[4] for v in variants}):
        ev, bl, gd = run_events(data, split_ts, variants,
                                gate_type=gt, regime=regime,
                                regime4h=regime4h)
        for k, v in ev.items():
            if v:               # only merge variants this pass actually ran
                events[k] = v
        if bl:
            baselines = bl
        gated_by_gt[gt] = gd

    for vname, mode, sl_m, tp_m, gt in variants:
        report(vname, events.get(vname, []), baselines,
               gated_by_gt.get(gt, {}), gt)


if __name__ == '__main__':
    main()
