#!/usr/bin/env python3
"""
backtest_zscore_pump_full.py — pre-computed z-score full universe sweep.
1. Pre-compute ALL z-scores for each (token, lookback) pair (once).
2. Sweep thresholds × directions on cached z-arrays.
Total: 6 lookbacks × 110 tokens = 660 z-computes (one pass each) vs 72×60k naive.
"""

import sys, os, time, json, sqlite3, statistics
import numpy as np
from multiprocessing import Pool, cpu_count

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Constants ──────────────────────────────────────────────────────────────────
CANDLES_DB    = '/root/.hermes/data/candles.db'
OUTPUT_JSON   = '/root/.hermes/data/zscore_pump_backtest_raw.json'
N_WORKERS     = max(1, cpu_count() - 1)
COOLDOWN_BARS = 20
HORIZON_BARS  = 240
LOOKBACKS     = [30, 50, 75, 100, 150, 200]
THRESHOLDS    = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

# ── Blacklists ─────────────────────────────────────────────────────────────────
def load_blacklists():
    try:
        from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
        return SHORT_BLACKLIST | LONG_BLACKLIST
    except Exception:
        return set()

# ── Universe ───────────────────────────────────────────────────────────────────
def get_universe():
    blocked = load_blacklists()
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT token FROM candles_1m ORDER BY token")
    all_tokens = [r[0] for r in c.fetchall()]
    conn.close()
    eligible = [t for t in all_tokens if t not in blocked]
    print(f"[universe] {len(all_tokens)} total, {len(blocked)} blocked, {len(eligible)} eligible", flush=True)
    return eligible

# ── Per-worker token cache (closes + pre-computed z-scores) ─────────────────────
_token_cache = {}  # token → {'closes': np.ndarray, 'zs': {lb: np.ndarray}}

def _get_token_data(token):
    """Load closes + pre-compute z-scores for all lookbacks (one-time per token)."""
    if token in _token_cache:
        return _token_cache[token]

    conn = sqlite3.connect(CANDLES_DB, timeout=15)
    c = conn.cursor()
    c.execute("SELECT close FROM candles_1m WHERE token = ? ORDER BY ts ASC", (token,))
    closes = np.array([r[0] for r in c.fetchall()], dtype=np.float64)
    conn.close()

    n = len(closes)
    zscores = {}

    for lb in LOOKBACKS:
        if n < lb + HORIZON_BARS + COOLDOWN_BARS + 2:
            zscores[lb] = np.array([])
            continue

        # Simple z-score: last value vs lookback window (same as production)
        zs = np.full(n, np.nan, dtype=np.float64)
        for i in range(lb - 1, n):
            chunk = closes[i - lb + 1:i + 1]
            mean = chunk.mean()
            std  = chunk.std(ddof=1)
            zs[i] = (closes[i] - mean) / std if std > 0 else np.nan
        zscores[lb] = zs

    _token_cache[token] = {'closes': closes, 'zscores': zscores, 'n': n}
    return _token_cache[token]

# ── Sweep thresholds × directions on cached z-scores ───────────────────────────
def sweep_combo(token, lookback):
    """
    Sweep ALL thresholds × directions for one token, one lookback.
    Returns list of result dicts (one per threshold × direction × horizon).
    """
    data = _get_token_data(token)
    closes = data['closes']
    zs     = data['zscores'].get(lookback, np.array([]))
    n      = data['n']

    if zs.size == 0 or n < lookback + HORIZON_BARS + COOLDOWN_BARS + 2:
        return []

    results = []
    max_start = n - HORIZON_BARS - 1

    for threshold in THRESHOLDS:
        for direction in ['LONG', 'SHORT']:
            if direction == 'LONG':
                fires_mask = zs > threshold
            else:
                fires_mask = zs < -threshold

            # Apply cooldown: only keep first fire after each gap of COOLDOWN_BARS
            last_sig = -COOLDOWN_BARS
            signal_bars = []
            for i in range(lookback, max_start + 1):
                if not fires_mask[i]:
                    continue
                if i - last_sig < COOLDOWN_BARS:
                    continue
                signal_bars.append(i)
                last_sig = i

            if not signal_bars:
                continue

            signal_idx = np.array(signal_bars, dtype=np.int64)
            entry_px   = closes[signal_idx]
            exit_px    = closes[signal_idx + HORIZON_BARS]

            # Filter valid
            valid = (entry_px > 0) & (exit_px > 0)
            entry_px  = entry_px[valid]
            exit_px   = exit_px[valid]
            signal_idx = signal_idx[valid]

            if entry_px.size == 0:
                continue

            returns = (exit_px - entry_px) / entry_px
            if direction == 'SHORT':
                returns = -returns

            wins   = int(np.sum(returns > 0))
            losses = int(np.sum(returns <= 0))
            fires  = wins + losses

            if fires < 3:
                continue

            avg_ret = float(np.mean(returns)) * 100
            sharpe  = 0.0
            if fires > 1 and np.std(returns) > 1e-12:
                sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(240))

            results.append({
                'token': token, 'lookback': lookback, 'threshold': threshold,
                'direction': direction, 'horizon': '4h',
                'fires': fires, 'wins': wins, 'losses': losses,
                'wr': round(wins / fires * 100, 2),
                'wl': round(wins / losses, 2) if losses else 999,
                'avg_ret': round(avg_ret, 4),
                'sharpe': round(sharpe, 3),
            })

    return results

# ── Job runner: one lookback × all tokens (sweeps all thresholds/directions) ────
def run_lookback(args):
    lookback, universe = args
    t0 = time.time()
    all_rows = []
    for tok in universe:
        all_rows.extend(sweep_combo(tok, lookback))
    return lookback, round(time.time() - t0, 1), all_rows

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] ZSCORE PUMP — FULL UNIVERSE BACKTEST", flush=True)

    universe = get_universe()

    # 6 lookbacks × all tokens (thresholds swept inside)
    jobs = [(lb, list(universe)) for lb in LOOKBACKS]
    total = len(jobs)

    print(f"[{time.strftime('%H:%M:%S')}] {total} lookbacks × 110 tokens | {N_WORKERS} workers", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}] LB={LOOKBACKS} TH={THRESHOLDS} CD={COOLDOWN_BARS} bars | 4h hold", flush=True)
    print("=" * 80, flush=True)

    all_rows = []
    with Pool(N_WORKERS) as pool:
        for lb, elapsed, rows in pool.imap_unordered(run_lookback, jobs):
            done = len([j for j in jobs if j[0] <= lb])
            total_fires = sum(r['fires'] for r in rows)
            eta = (time.time() - t0) / done * (total - done)
            print(f"[{done:02d}/{total}] LB={lb:3d} | tokens={len(rows)//(len(THRESHOLDS)*2)} | F={total_fires:7d} | {elapsed}s | ETA={eta:.0f}s", flush=True)
            all_rows.extend(rows)

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(all_rows, f)

    total_s = time.time() - t0
    print(f"\nDONE — {len(all_rows)} rows | {total_s:.0f}s", flush=True)

    print("\n" + "=" * 80, flush=True)
    print("BEST COMBOS BY HORIZON+DIR (min 50 fires)", flush=True)
    print("=" * 80, flush=True)
    for d in ['LONG', 'SHORT']:
        rows = [r for r in all_rows if r['direction'] == d and r['fires'] >= 50]
        if not rows:
            continue
        best = max(rows, key=lambda x: x['wr'])
        print(f"  {d:<5} WR={best['wr']:.1f}% F={best['fires']:6d} LB={best['lookback']:3d} TH={best['threshold']:.1f} Ret={best['avg_ret']:+.3f}% Sharpe={best['sharpe']:+.2f}", flush=True)

if __name__ == '__main__':
    main()