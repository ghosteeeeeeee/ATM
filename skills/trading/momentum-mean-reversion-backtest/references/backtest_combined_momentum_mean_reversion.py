#!/usr/bin/env python3
"""
Backtest: Combined pct-hermes (mean reversion) + momentum-accel (acceleration crossing)
Hypothesis: pct_hermes oversold (pct_long<=30) + acceleration crossing up → high-confluence LONG
            pct_hermes overbought (pct_short>=70) + acceleration crossing down → high-confluence SHORT
"""
import sqlite3, statistics, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB = '/root/.hermes/data/candles.db'

TOKENS = ['BTC','ETH','SOL','AXS','IMX','SKY','TRB','AVAX','MATIC','LINK','UNI','AAVE','MKR','SNX','FIL','DOT']

PCT_LONG_OVERSOLD  = 30
PCT_SHORT_OVERBOUGHT = 70
ACCEL_CROSS_UP   = 0.001
ACCEL_CROSS_DOWN = -0.001

Z_WINDOW   = 240
ACCEL_WIN  = 60
PCT_WINDOW = 500
MIN_BARS   = 200

HORIZONS = [4, 8, 16, 24]

def get_candles(token, tf='1h', limit=2000):
    conn = sqlite3.connect(DB)
    rows = conn.execute(f"""
        SELECT ts, close FROM candles_{tf}
        WHERE token=? ORDER BY ts ASC LIMIT ?
    """, (token, limit)).fetchall()
    conn.close()
    return rows

def compute_z(prices, window):
    if len(prices) < window: return None
    chunk = prices[-window:]
    mu = statistics.mean(chunk); std = statistics.stdev(chunk) if len(chunk) > 1 else 1
    return (prices[-1] - mu) / std if std > 0 else None

def compute_accel(prices, window=60):
    if len(prices) < window + 20: return None, None, None
    def z_at(chunk):
        if len(chunk) < 15: return None
        mu = statistics.mean(chunk); s = statistics.stdev(chunk) if len(chunk)>1 else 1
        return (chunk[-1]-mu)/s if s>0 else None
    z_now  = z_at(prices[-15:])
    z_then = z_at(prices[-15-window:-window]) if len(prices) >= window+15 else None
    if z_now is None or z_then is None: return None, None, None
    return (z_now - z_then) / window, z_now, z_then

def compute_pct_rank(prices, window=500):
    if len(prices) < 30: return 50.0, 50.0
    look = prices[-window:] if len(prices) >= window else prices
    cur = prices[-1]
    below = sum(1 for p in look if p <= cur)
    above = sum(1 for p in look if p >= cur)
    return (below/len(look))*100, (above/len(look))*100

SIGNALS = {
    'pct_hermes_only': {
        'long':  lambda pl,ps,ac,zn,zt: pl <= PCT_LONG_OVERSOLD,
        'short': lambda pl,ps,ac,zn,zt: ps >= PCT_SHORT_OVERBOUGHT,
    },
    'accel_only': {
        'long':  lambda pl,ps,ac,zn,zt: ac is not None and zt is not None and zt < 0 and ac > ACCEL_CROSS_UP,
        'short': lambda pl,ps,ac,zn,zt: ac is not None and zt is not None and zt > 0 and ac < -ACCEL_CROSS_DOWN,
    },
    'combined_strict': {
        'long':  lambda pl,ps,ac,zn,zt: pl <= PCT_LONG_OVERSOLD and (ac is not None and zt is not None and zt < 0 and ac > ACCEL_CROSS_UP),
        'short': lambda pl,ps,ac,zn,zt: ps >= PCT_SHORT_OVERBOUGHT and (ac is not None and zt is not None and zt > 0 and ac < -ACCEL_CROSS_DOWN),
    },
    'combined_lenient': {
        'long':  lambda pl,ps,ac,zn,zt: pl <= PCT_LONG_OVERSOLD or (ac is not None and zt is not None and zt < 0 and ac > ACCEL_CROSS_UP),
        'short': lambda pl,ps,ac,zn,zt: ps >= PCT_SHORT_OVERBOUGHT or (ac is not None and zt is not None and zt > 0 and ac < -ACCEL_CROSS_DOWN),
    },
    'pct_extreme_only': {
        'long':  lambda pl,ps,ac,zn,zt: pl <= 20,
        'short': lambda pl,ps,ac,zn,zt: ps >= 80,
    },
    'combined_pct_extreme': {
        'long':  lambda pl,ps,ac,zn,zt: pl <= 20 and (ac is not None and zt is not None and zt < 0 and ac > ACCEL_CROSS_UP),
        'short': lambda pl,ps,ac,zn,zt: ps >= 80 and (ac is not None and zt is not None and zt > 0 and ac < -ACCEL_CROSS_DOWN),
    },
}

def backtest_signal(token, tf, signal_name, direction, signal_fn, horizons):
    candles = get_candles(token, tf)
    if not candles: return None
    closes = [c[1] for c in candles]
    if len(closes) < MIN_BARS + max(horizons)*4: return None
    n = len(closes)
    pct_long_s, pct_short_s, accel_s, zn_s = [], [], [], []
    for i in range(n):
        pl, ps = compute_pct_rank(closes[:i+1])
        ac, zn, _ = compute_accel(closes[:i+1])
        pct_long_s.append(pl); pct_short_s.append(ps); accel_s.append(ac); zn_s.append(zn)
    signals = []
    for i in range(MIN_BARS, n - max(horizons)*4):
        pl = pct_long_s[i]; ps = pct_short_s[i]; ac = accel_s[i]; zn = zn_s[i]
        zt = zn_s[i-ACCEL_WIN] if i >= ACCEL_WIN else None
        if signal_fn(pl, ps, ac, zn, zt):
            h_ret = {}
            for h in horizons:
                idx = i + h*4
                if idx < n: h_ret[h] = (closes[idx] - closes[i]) / closes[i] * 100
            if h_ret: signals.append(h_ret)
    return signals

def analyze(signals, horizons):
    if not signals: return None
    n = len(signals)
    results = {}
    for h in horizons:
        rets = [s[h] for s in signals if h in s]
        if not rets: continue
        avg = statistics.mean(rets)
        hits = sum(1 for r in rets if r > 0)
        hr = hits/len(rets)*100
        losses = sum(1 for r in rets if r < 0)
        results[h] = (round(avg,3), round(hr,1), hits, losses)
    return n, results

if __name__ == '__main__':
    tf = '1h'
    print(f"T={tf} | horizons={HORIZONS}h | tokens={len(TOKENS)}")
    all_results = {}
    for sig_name in sorted(SIGNALS.keys()):
        sig = SIGNALS[sig_name]
        print(f"\n{'='*90}\nSIGNAL: {sig_name}\n{'='*90}")
        for direction in ['long','short']:
            fn = sig[direction]
            all_sigs = []; token_counts = {}
            for token in TOKENS:
                res = backtest_signal(token, tf, sig_name, direction, fn, HORIZONS)
                if res:
                    all_sigs.extend(res)
                    token_counts[token] = len(res)
            if not all_sigs:
                print(f"  {direction.upper()}: NO SIGNALS"); continue
            n_total = len(all_sigs)
            print(f"  {direction.upper()}: N={n_total} | Top: {sorted(token_counts.items(),key=lambda x:-x[1])[:4]}")
            print(f"  {'Horizon':>8} | {'Avg Ret%':>10} | {'Hit Rate%':>10} | {'Win/Loss':>10}")
            print(f"  {'-'*50}")
            for h in HORIZONS:
                rets = [s[h] for s in all_sigs if h in s]
                if not rets: continue
                avg,hr,hits,losses = analyze(all_sigs, HORIZONS)[1][h]
                print(f"  {h:>8}h | {avg:>+10.3f}% | {hr:>10.1f}% | {hits}/{losses}")
            all_results[(sig_name, direction)] = all_sigs
