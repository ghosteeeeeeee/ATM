#!/usr/bin/env python3
"""
Backtest: Combined pct-hermes (mean reversion) + momentum-accel (acceleration crossing)
Hypothesis: pct_hermes oversold (pct_long<=30) + acceleration crossing up → high-confluence LONG
            pct_hermes overbought (pct_short>=70) + acceleration crossing down → high-confluence SHORT
"""
import sqlite3, statistics, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *

DB = '/root/.hermes/data/candles.db'

# ── Token universe ──────────────────────────────────────────
TOKENS = ['BTC','ETH','SOL','AXS','IMX','SKY','TRB','AVAX','MATIC','LINK','UNI','AAVE','MKR','SNX','FIL','DOT']

# ── Config ─────────────────────────────────────────────────
# pct-hermes thresholds
PCT_LONG_OVERSOLD  = 30   # pct_long <= 30 → oversold (good LONG entry)
PCT_SHORT_OVERBOUGHT = 70  # pct_short >= 70 → overbought (good SHORT entry)

# Acceleration thresholds
ACCEL_CROSS_UP   = 0.001  # accel crosses above this → momentum igniting LONG
ACCEL_CROSS_DOWN = -0.001 # accel crosses below this → momentum fading SHORT

# Windows
Z_WINDOW       = 240   # bars for z-score computation
ACCEL_WINDOW    = 60    # bars ago for acceleration comparison
PCT_WINDOW      = 500   # bars for percentile rank
MIN_BARS        = max(Z_WINDOW, ACCEL_WINDOW, PCT_WINDOW) + 20

# Holding periods
HORIZONS = [4, 8, 16, 24]  # hours

def get_candles(token, tf='1h', limit=2000):
    conn = sqlite3.connect(DB)
    rows = conn.execute(f"""
        SELECT ts, close FROM candles_{tf}
        WHERE token=? ORDER BY ts ASC
    """, (token,)).fetchall()
    conn.close()
    return rows  # [(ts, close), ...]

def compute_z(prices, window):
    if len(prices) < window:
        return None
    chunk = prices[-window:]
    mu = statistics.mean(chunk)
    std = statistics.stdev(chunk) if len(chunk) > 1 else 1
    if std == 0:
        return None
    return (prices[-1] - mu) / std

def compute_accel(prices, window=60):
    """Acceleration = change in z-score over ACCEL_WINDOW bars."""
    if len(prices) < window + 20:
        return None, None, None
    def z_at(prices_subset):
        if len(prices_subset) < 20:
            return None
        mu = statistics.mean(prices_subset)
        std = statistics.stdev(prices_subset) if len(prices_subset) > 1 else 1
        if std == 0:
            return None
        return (prices_subset[-1] - mu) / std
    z_now  = z_at(prices[-20:])
    z_then = z_at(prices[-20-window:-window]) if len(prices) > window + 20 else None
    if z_now is None or z_then is None:
        return None, None, None
    accel = (z_now - z_then) / window
    return accel, z_now, z_then

def compute_pct_rank(prices, window=500):
    """pct_long = % of prices below current price (suppressed = good for LONG)."""
    if len(prices) < 60:
        return 50.0, 50.0
    lookback = prices[-window:] if len(prices) >= window else prices
    current = prices[-1]
    below = sum(1 for p in lookback if p <= current)
    above = sum(1 for p in lookback if p >= current)
    pct_long  = (below / len(lookback)) * 100
    pct_short = (above / len(lookback)) * 100
    return round(pct_long, 1), round(pct_short, 1)

# ── Signal definitions ──────────────────────────────────────
# Each signal: list of conditions for LONG and SHORT
SIGNALS = {
    'pct_hermes_only': {
        'long':  lambda pct_long, pct_short, accel, z_now, z_then: pct_long <= PCT_LONG_OVERSOLD,
        'short': lambda pct_long, pct_short, accel, z_now, z_then: pct_short >= PCT_SHORT_OVERBOUGHT,
    },
    'accel_only': {
        'long':  lambda pct_long, pct_short, accel, z_now, z_then: accel is not None and z_then is not None and z_then < 0 and accel > ACCEL_CROSS_UP,
        'short': lambda pct_long, pct_short, accel, z_now, z_then: accel is not None and z_then is not None and z_then > 0 and accel < -ACCEL_CROSS_DOWN,
    },
    'combined_strict': {
        # BOTH conditions must be met — strictest
        'long':  lambda pct_long, pct_short, accel, z_now, z_then: pct_long <= PCT_LONG_OVERSOLD and (accel is not None and z_then is not None and z_then < 0 and accel > ACCEL_CROSS_UP),
        'short': lambda pct_long, pct_short, accel, z_now, z_then: pct_short >= PCT_SHORT_OVERBOUGHT and (accel is not None and z_then is not None and z_then > 0 and accel < -ACCEL_CROSS_DOWN),
    },
    'combined_lenient': {
        # EITHER condition met (weaker)
        'long':  lambda pct_long, pct_short, accel, z_now, z_then: pct_long <= PCT_LONG_OVERSOLD or (accel is not None and z_then is not None and z_then < 0 and accel > ACCEL_CROSS_UP),
        'short': lambda pct_long, pct_short, accel, z_now, z_then: pct_short >= PCT_SHORT_OVERBOUGHT or (accel is not None and z_then is not None and z_then > 0 and accel < -ACCEL_CROSS_DOWN),
    },
    'pct_extreme_only': {
        # More extreme thresholds — pct_long <= 20 or pct_short >= 80
        'long':  lambda pct_long, pct_short, accel, z_now, z_then: pct_long <= 20,
        'short': lambda pct_long, pct_short, accel, z_now, z_then: pct_short >= 80,
    },
    'combined_pct_extreme': {
        # pct extreme + accel crossing
        'long':  lambda pct_long, pct_short, accel, z_now, z_then: pct_long <= 20 and (accel is not None and z_then is not None and z_then < 0 and accel > ACCEL_CROSS_UP),
        'short': lambda pct_long, pct_short, accel, z_now, z_then: pct_short >= 80 and (accel is not None and z_then is not None and z_then > 0 and accel < -ACCEL_CROSS_DOWN),
    },
    'pct_any_oversold': {
        # Any oversold reading (not just extreme) + accel crossing
        'long':  lambda pct_long, pct_short, accel, z_now, z_then: pct_long <= 40 and (accel is not None and z_then is not None and z_then < 0 and accel > ACCEL_CROSS_UP),
        'short': lambda pct_long, pct_short, accel, z_now, z_then: pct_short >= 60 and (accel is not None and z_then is not None and z_then > 0 and accel < -ACCEL_CROSS_DOWN),
    },
}

def backtest_signal(token, tf, signal_name, direction, signal_fn, horizons):
    candles = get_candles(token, tf)
    if not candles:
        return None
    closes = [c[1] for c in candles]
    if len(closes) < MIN_BARS:
        return None

    # Build indicator series (shift by 1 to avoid lookahead)
    n = len(closes)
    pct_long_series  = []
    pct_short_series = []
    accel_series     = []
    z_now_series     = []
    for i in range(n):
        chunk = closes[:i+1]
        pl, ps = compute_pct_rank(chunk)
        ac, zn, _ = compute_accel(chunk)
        pct_long_series.append(pl)
        pct_short_series.append(ps)
        accel_series.append(ac)
        z_now_series.append(zn)

    signals = []
    for i in range(MIN_BARS, n - max(horizons) * 4):  # need future bars for returns
        pl  = pct_long_series[i]
        ps  = pct_short_series[i]
        ac  = accel_series[i]
        zn  = z_now_series[i]
        # Get z_then (accel was computed relative to this)
        if i >= ACCEL_WINDOW + 20:
            _, _, zt = compute_accel(closes[:i+1])
        else:
            zt = None

        if signal_fn(pl, ps, ac, zn, zt):
            # Compute future returns
            h_ret = {}
            for h in horizons:
                idx_future = i + h * 4  # 4 bars/hour for 1h TF
                if idx_future < n:
                    ret = (closes[idx_future] - closes[i]) / closes[i] * 100
                    h_ret[h] = ret
            if h_ret:
                signals.append(h_ret)

    return signals

def analyze(signals):
    if not signals:
        return None
    n = len(signals)
    results = {}
    for h in horizons:
        rets = [s[h] for s in signals if h in s]
        if not rets:
            continue
        avg = statistics.mean(rets)
        hits = sum(1 for r in rets if r > 0)
        hit_rate = hits / len(rets) * 100
        results[h] = (round(avg, 3), round(hit_rate, 1))
    return (n, results)

# ── Run ────────────────────────────────────────────────────
horizons = HORIZONS
tf = '1h'

print("=" * 100)
print("COMBINED PCT-HERMES (mean reversion) + MOMENTUM ACCELERATION backtest")
print("=" * 100)
print(f"pct_hermes oversold <= {PCT_LONG_OVERSOLD} | overbought >= {PCT_SHORT_OVERBOUGHT}")
print(f"accel crossing up > {ACCEL_CROSS_UP} from negative | crossing down < {-ACCEL_CROSS_DOWN} from positive")
print(f"Horizons: {horizons}h | TF: {tf} | Tokens: {len(TOKENS)}")
print()

all_results = {}

for sig_name in sorted(SIGNALS.keys()):
    sig = SIGNALS[sig_name]
    print(f"\n{'='*90}")
    print(f"SIGNAL: {sig_name}")
    print(f"{'='*90}")

    for direction in ['long', 'short']:
        fn = sig[direction]
        all_signals = []
        token_counts = {}
        for token in TOKENS:
            res = backtest_signal(token, tf, sig_name, direction, fn, horizons)
            if res:
                all_signals.extend(res)
                token_counts[token] = len(res)

        if not all_signals:
            print(f"  {direction.upper()}: NO SIGNALS")
            continue

        n_total = len(all_signals)
        print(f"  {direction.upper()}: N={n_total} signals | Top tokens: {sorted(token_counts.items(), key=lambda x:-x[1])[:5]}")
        print(f"  {'Horizon':>8} | {'Avg Ret%':>10} | {'Hit Rate%':>10} | {'Win/Loss':>8}")
        print(f"  {'-'*50}")

        for h in horizons:
            rets = [s[h] for s in all_signals if h in s]
            if not rets:
                continue
            avg = statistics.mean(rets)
            hits = sum(1 for r in rets if r > 0)
            hr = hits / len(rets) * 100
            losses = sum(1 for r in rets if r < 0)
            print(f"  {h:>8}h | {avg:>+10.3f}% | {hr:>10.1f}% | {hits}/{losses}")
        all_results[sig_name] = all_signals

print()
print("=" * 100)
print("SUMMARY TABLE: All signals at 4h horizon (best forward-looking horizon)")
print("=" * 100)
print(f"  {'Signal':<25} | {'N LONG':>6} | {'4h Ret%':>8} | {'4h Hit%':>8} | {'N SHORT':>6} | {'4h Ret%':>8} | {'4h Hit%':>8}")
print(f"  {'-'*90}")
for sig_name in sorted(SIGNALS.keys()):
    sig = SIGNALS[sig_name]
    for direction in ['long', 'short']:
        fn = sig[direction]
        all_sigs = []
        for token in TOKENS:
            res = backtest_signal(token, tf, sig_name, direction, fn, horizons)
            if res:
                all_sigs.extend(res)
        if not all_sigs:
            continue
        n = len(all_sigs)
        rets_4h = [s[4] for s in all_sigs if 4 in s]
        if not rets_4h:
            continue
        avg = statistics.mean(rets_4h)
        hr = sum(1 for r in rets_4h if r > 0) / len(rets_4h) * 100
        ncol = f"N {direction.upper()}"
        print(f"  {sig_name:<25} | {n:>6} | {avg:>+8.3f}% | {hr:>8.1f}%")
