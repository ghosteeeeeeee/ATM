#!/usr/bin/env python3
"""
MACD 1M Tuner — Per-token MACD SHORT params tuned on local 1m candles.

Reads 1m candles from local candles.db, sweeps (fast, slow, signal, hold)
combos, stores best per token in token_best_config_1m table.

Fast (5min): runs on-demand / as cron
Params are loaded by _load_token_macd_1m_params() in signal_gen.py

Why separate from mtf_macd_tuner.py:
  - mtf_macd_tuner reads Binance (1h/4h candles) for slow MACD params
  - macd_1m_tuner reads local candles.db (1m candles) for fast MACD params
  - Different data sources, different param ranges, different hold periods
"""
import sqlite3, statistics, time, os, sys
from datetime import datetime

DB_CANDLES = '/root/.hermes/data/candles.db'
DB_TUNER   = '/root/.hermes/data/mtf_macd_tuner.db'
WINDOW_BARS = 450   # ~7.5h of 1m — enough for MACD slow=30 + sig=6 + hold=60 + buffer
MIN_SIGNALS = 3     # minimum crossover signals to trust the result

# Param grid — pre-selected from 315-combo sweep (2026-04-19)
# Fast: 3-8, Slow: 10-30, Signal: 4-6, Hold: 40-60
PARAM_GRID = [
    (f, sl, sg, h)
    for f in [3, 5, 6, 8]
    for sl in [10, 15, 20, 30]
    for sg in [4, 5, 6]
    for h in [40, 60]
    if sl > f
]
# 96 combos per token

def ema(data, n):
    if data is None or len(data) < n:
        return None
    k = 2 / (n + 1)
    e = sum(data[:n]) / n
    r = [e]
    for v in data[n:]:
        e = v * k + e * (1 - k)
        r.append(e)
    return r

def backtest(closes, fast, slow, sig, hold):
    """Return (win_rate, avg_pnl, n_signals) for SHORT signals only."""
    ef = ema(closes, fast)
    es = ema(closes, slow)
    if ef is None or es is None:
        return 0, 0, 0
    ml = [ef[i] - es[i] for i in range(min(len(ef), len(es)))]
    if len(ml) < slow:
        return 0, 0, 0
    esig = ema(ml, sig)
    if esig is None or len(esig) < sig:
        return 0, 0, 0
    n = min(len(ml), len(esig))
    h = [ml[i] - esig[i] for i in range(n)]

    shorts = []
    for i in range(slow + sig, n):
        fi = i + hold
        if fi >= len(closes):
            break
        # SHORT: histogram crosses below zero
        if h[i - 1] >= 0 > h[i]:
            shorts.append((closes[i] - closes[fi]) / closes[i])

    if len(shorts) < MIN_SIGNALS:
        return 0, 0, 0
    wr = sum(1 for r in shorts if r > 0) / len(shorts) * 100
    avg = statistics.mean(shorts) * 100
    return wr, avg, len(shorts)

def run_sweep():
    """Load candles from DB, sweep params, store best config per token."""
    t0 = time.time()

    # Connect to candles DB
    conn_c = sqlite3.connect(DB_CANDLES, timeout=10)
    cc = conn_c.cursor()

    # Get tokens with enough 1m data
    cc.execute("""
        SELECT token, COUNT(*) as cnt
        FROM candles_1m
        GROUP BY token
        HAVING cnt >= ?
        ORDER BY cnt DESC
    """, (WINDOW_BARS,))
    tokens = {r[0]: r[1] for r in cc.fetchall()}
    print(f"[1m-tuner] {len(tokens)} tokens with >={WINDOW_BARS} 1m candles")

    # Pre-load all candle data into memory
    print(f"[1m-tuner] Loading candle data...", flush=True)
    cc.execute(f"""
        SELECT token, close FROM candles_1m
        WHERE token IN (SELECT token FROM candles_1m GROUP BY token HAVING COUNT(*) >= ?)
        ORDER BY token, ts
    """, (WINDOW_BARS,))
    token_closes = {}
    for token, close in cc.fetchall():
        if token not in token_closes:
            token_closes[token] = []
        token_closes[token].append(close)
    conn_c.close()
    print(f"[1m-tuner] Loaded {len(token_closes)} tokens, {sum(len(v) for v in token_closes.values())} total candles")

    # Sweep params per token
    results = []
    for idx, (token, closes) in enumerate(token_closes.items()):
        best = {'wr': 0, 'pnl': 0, 'n': 0, 'params': None}
        for fast, slow, sig, hold in PARAM_GRID:
            wr, avg, n = backtest(closes, fast, slow, sig, hold)
            if n < MIN_SIGNALS:
                continue
            # Score: WR weighted heavily, pnl breaks ties, n signals as tiebreaker
            score = wr + (25 if avg > 0 else 0)
            best_score = best['wr'] + (25 if best['pnl'] > 0 else 0)
            if score > best_score or (score == best_score and n > best['n']):
                best = {'wr': wr, 'pnl': avg, 'n': n, 'params': (fast, slow, sig, hold)}

        if best['params']:
            results.append((token, best['wr'], best['pnl'], best['n'], best['params']))

        if (idx + 1) % 50 == 0:
            elapsed = time.time() - t0
            print(f"  {idx+1}/{len(token_closes)} done, {len(results)} populated ({elapsed:.1f}s)", flush=True)

    # Store in tuner DB
    conn_t = sqlite3.connect(DB_TUNER, timeout=10)
    ct = conn_t.cursor()

    # Ensure table exists
    ct.execute("""
        CREATE TABLE IF NOT EXISTS token_best_config_1m (
            token TEXT PRIMARY KEY,
            fast INTEGER NOT NULL,
            slow INTEGER NOT NULL,
            signal INTEGER NOT NULL,
            hold_bars INTEGER NOT NULL,
            win_rate REAL NOT NULL,
            avg_pnl_pct REAL NOT NULL,
            signal_count INTEGER NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    ct.execute("DELETE FROM token_best_config_1m")
    for token, wr, pnl, n, params in results:
        f, s, sg, h = params
        ct.execute("""
            INSERT INTO token_best_config_1m
            (token, fast, slow, signal, hold_bars, win_rate, avg_pnl_pct, signal_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (token, f, s, sg, h, wr, pnl, n))
    conn_t.commit()

    elapsed = time.time() - t0
    conn_t.close()

    # Summary
    results.sort(key=lambda x: x[1], reverse=True)
    print(f"\n[1m-tuner] Done in {elapsed:.1f}s — {len(results)}/{len(token_closes)} tokens tuned")
    print(f"Avg WR: {statistics.mean(r[1] for r in results):.1f}%")
    print(f"Top 5: {[(r[0], f'{r[1]:.1f}%') for r in results[:5]]}")
    print(f"Bottom 5: {[(r[0], f'{r[1]:.1f}%') for r in results[-5:]]}")

    return len(results)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'sweep'
    if mode == 'sweep':
        run_sweep()
    else:
        print(f"Unknown mode: {mode}")
