#!/usr/bin/env python3
"""
Backtest: mean reversion after z-score thresholds.
Tests: does price actually revert after hitting z=1, 1.5, 2, 2.5, 3?
For each threshold, measure:
  - Avg return over next 4h, 8h, 16h, 24h
  - Hit rate (price moved opposite to z direction)
  - Avg magnitude of reversion
"""
import sqlite3, statistics, sys, os
from typing import List, Tuple

DB = '/root/.hermes/data/candles.db'

# Tokens with enough data
TOKENS = ['BTC', 'ETH', 'AXS', 'IMX', 'SKY', 'TRB',
          'SOL', 'AVAX', 'MATIC', 'LINK', 'UNI', 'AAVE', 'MKR', 'SNX']

# Timeframes to test (in 4h bars)
WINDOWS = [1, 2, 4, 6]  # 4h, 8h, 16h, 24h

# Z-score thresholds to test
THRESHOLDS = [1.0, 1.5, 2.0, 2.5, 3.0]

def get_candles(token: str) -> List[Tuple[int, float]]:
    """Get 4h candles sorted oldest→newest. Returns (ts, close)."""
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT ts, close FROM candles_4h
        WHERE token = ?
        ORDER BY ts ASC
    """, (token,))
    rows = c.fetchall()
    conn.close()
    return rows

def rolling_zscore(prices: List[float], window: int = 60) -> List[float]:
    """Compute rolling z-score with given lookback window."""
    zscores = []
    for i in range(len(prices)):
        if i < window:
            zscores.append(None)
            continue
        subset = prices[i-window:i]
        mu = statistics.mean(subset)
        std = statistics.stdev(subset) if len(subset) > 1 else 1
        if std == 0:
            zscores.append(0.0)
        else:
            zscores.append((prices[i] - mu) / std)
    return zscores

def backtest_threshold(token: str, threshold: float, direction: str, forward_windows: List[int]) -> dict:
    """
    direction: 'positive' = z > threshold (expect reversion DOWN = SHORT)
                'negative' = z < -threshold (expect reversion UP = LONG)
    Measures actual price movement in forward windows.
    """
    candles = get_candles(token)
    if len(candles) < 100:
        return None

    closes = [c[1] for c in candles]
    zscores = rolling_zscore(closes, window=60)

    # Collect stats for each forward window
    results_by_window = {w: {'returns': [], 'hit': []} for w in forward_windows}

    for i in range(len(candles) - max(forward_windows)):
        z = zscores[i]
        if z is None:
            continue

        if direction == 'positive' and z >= threshold:
            entry_price = closes[i]
            for w in forward_windows:
                future_price = closes[i + w]
                ret = (future_price - entry_price) / entry_price  # LONG return
                # For SHORT direction (expect price down), negate
                reversion_return = -ret if direction == 'positive' else ret
                results_by_window[w]['returns'].append(reversion_return)
                # Hit = price moved opposite to z direction
                hit = reversion_return > 0
                results_by_window[w]['hit'].append(hit)

        elif direction == 'negative' and z <= -threshold:
            entry_price = closes[i]
            for w in forward_windows:
                future_price = closes[i + w]
                ret = (future_price - entry_price) / entry_price  # LONG return
                # For LONG direction (expect price up), keep as-is
                reversion_return = ret
                results_by_window[w]['returns'].append(reversion_return)
                hit = reversion_return > 0
                results_by_window[w]['hit'].append(hit)

    return results_by_window

def main():
    print(f"{'Token':<8} {'Dir':<3} {'Z±':<5} {'N':>5} {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} {'4h Hit%':>10} {'8h Hit%':>10} {'16h Hit%':>10} {'24h Hit%':>10}")
    print("-" * 120)

    for token in TOKENS:
        candles = get_candles(token)
        if len(candles) < 100:
            continue

        for direction in ['positive', 'negative']:
            for z_thresh in THRESHOLDS:
                results = backtest_threshold(token, z_thresh, direction, WINDOWS)
                if not results:
                    continue

                n = len(results[1]['returns'])
                if n < 5:
                    continue

                def fmt_window(w):
                    rets = results[w]['returns']
                    hits = results[w]['hit']
                    if not rets:
                        return f"{'N/A':>10} {'N/A':>10}"
                    avg_ret = statistics.mean(rets) * 100
                    hit_rate = statistics.mean(hits) * 100 if hits else 0
                    return f"{avg_ret:>+10.2f} {hit_rate:>10.1f}"

                dir_label = 'SH' if direction == 'positive' else 'LO'
                print(f"{token:<8} {dir_label:<3} {z_thresh:<5} {n:>5} "
                      + fmt_window(1) + " " + fmt_window(2) + " " + fmt_window(4) + " " + fmt_window(6))

    # Aggregate across all tokens
    print("\n" + "=" * 120)
    print("AGGREGATE (all tokens, all z thresholds):")
    print(f"{'Dir':<3} {'Z±':<5} {'N':>6} {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} {'4h Hit%':>10} {'8h Hit%':>10} {'16h Hit%':>10} {'24h Hit%':>10}")
    print("-" * 120)

    for direction in ['positive', 'negative']:
        for z_thresh in THRESHOLDS:
            all_returns = {w: [] for w in WINDOWS}
            all_hits = {w: [] for w in WINDOWS}

            for token in TOKENS:
                results = backtest_threshold(token, z_thresh, direction, WINDOWS)
                if not results:
                    continue
                for w in WINDOWS:
                    all_returns[w].extend(results[w]['returns'])
                    all_hits[w].extend(results[w]['hit'])

            n_total = len(all_returns[1])
            if n_total < 20:
                continue

            def fmt_agg(w):
                rets = all_returns[w]
                hits = all_hits[w]
                if not rets:
                    return f"{'N/A':>10} {'N/A':>10}"
                avg_ret = statistics.mean(rets) * 100
                hit_rate = statistics.mean(hits) * 100 if hits else 0
                return f"{avg_ret:>+10.2f} {hit_rate:>10.1f}"

            dir_label = 'SH' if direction == 'positive' else 'LO'
            print(f"{dir_label:<3} {z_thresh:<5} {n_total:>6} "
                  + fmt_agg(1) + " " + fmt_agg(2) + " " + fmt_agg(4) + " " + fmt_agg(6))

if __name__ == '__main__':
    main()
