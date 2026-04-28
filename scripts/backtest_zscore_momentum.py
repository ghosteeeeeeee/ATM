#!/usr/bin/env python3
"""
Backtest: z-score momentum continuation (catch the pump).
Theory: if z crosses 1, it will continue to 2 and 3 — play the momentum.

Strategy:
  - LONG: z crosses above +1 (z was below, now above) AND z is still rising
  - SHORT: z crosses below -1 (z was above, now below) AND z is still falling
  - Target: how far does z/price continue in the same direction?

Measures:
  - After crossing threshold, how often does it reach +2, +3?
  - Avg price return when entering at cross and exiting at various z peaks
  - Compare: entering at z=1 vs z=2 vs z=3
"""
import sqlite3, statistics, sys, os
from typing import List, Tuple, Optional

DB = '/root/.hermes/data/candles.db'

TOKENS = ['BTC', 'ETH', 'AXS', 'IMX', 'SKY', 'TRB',
          'SOL', 'AVAX', 'MATIC', 'LINK', 'UNI', 'AAVE', 'MKR', 'SNX']

WINDOWS = [1, 2, 4, 6]  # 4h bars forward

def get_candles(token: str) -> List[Tuple[int, float]]:
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

def rolling_zscore(prices: List[float], window: int = 60) -> List[Tuple[float, float]]:
    """
    Returns list of (z, prev_z) tuples for each price point.
    prev_z = z from previous bar.
    """
    zscores = []
    prev_z = None
    for i in range(len(prices)):
        if i < window:
            zscores.append((None, None))
            continue
        subset = prices[i-window:i]
        mu = statistics.mean(subset)
        std = statistics.stdev(subset) if len(subset) > 1 else 1
        if std == 0:
            z = 0.0
        else:
            z = (prices[i] - mu) / std
        zscores.append((z, prev_z))
        prev_z = z
    return zscores

def backtest_momentum_cross(token: str, threshold: float, direction: str, forward_windows: List[int]) -> dict:
    """
    LONG: z crosses above +threshold (prev_z < threshold, z >= threshold)
    SHORT: z crosses below -threshold (prev_z > -threshold, z <= -threshold)

    Measures:
      - How often does z continue to threshold*2, threshold*3?
      - Avg price return from cross point forward
    """
    candles = get_candles(token)
    if len(candles) < 100:
        return None

    closes = [c[1] for c in candles]
    zscores = rolling_zscore(closes, window=60)

    results_by_window = {w: {'returns': [], 'hit': [], 'reached_2x': [], 'reached_3x': []} for w in forward_windows}

    for i in range(len(candles) - max(forward_windows)):
        z, prev_z = zscores[i]
        if z is None or prev_z is None:
            continue

        if direction == 'long':
            # z crossed above +threshold
            if prev_z < threshold and z >= threshold:
                entry_price = closes[i]
                entry_z = z
                max_z_seen = z
                for w in forward_windows:
                    if i + w >= len(closes):
                        break
                    future_price = closes[i + w]
                    future_z, _ = zscores[i + w] if i + w < len(zscores) else (None, None)
                    if future_z is not None:
                        max_z_seen = max(max_z_seen, future_z)
                    ret = (future_price - entry_price) / entry_price
                    results_by_window[w]['returns'].append(ret)
                    hit = ret > 0
                    results_by_window[w]['hit'].append(hit)

                # Did z reach 2x threshold? 3x?
                if max_z_seen >= threshold * 2:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_2x'].append(True)
                else:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_2x'].append(False)

                if max_z_seen >= threshold * 3:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_3x'].append(True)
                else:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_3x'].append(False)

        elif direction == 'short':
            # z crossed below -threshold
            if prev_z > -threshold and z <= -threshold:
                entry_price = closes[i]
                entry_z = z
                min_z_seen = z
                for w in forward_windows:
                    if i + w >= len(closes):
                        break
                    future_price = closes[i + w]
                    future_z, _ = zscores[i + w] if i + w < len(zscores) else (None, None)
                    if future_z is not None:
                        min_z_seen = min(min_z_seen, future_z)
                    # SHORT return = price went down
                    ret = -(future_price - entry_price) / entry_price
                    results_by_window[w]['returns'].append(ret)
                    hit = ret > 0
                    results_by_window[w]['hit'].append(hit)

                if min_z_seen <= -threshold * 2:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_2x'].append(True)
                else:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_2x'].append(False)

                if min_z_seen <= -threshold * 3:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_3x'].append(True)
                else:
                    for w in forward_windows:
                        if results_by_window[w]['returns']:
                            results_by_window[w]['reached_3x'].append(False)

    return results_by_window

def main():
    thresholds = [1.0, 1.5, 2.0]
    # How often does z continue from threshold to 2x and 3x?
    print("=" * 140)
    print("PART 1: How often does z continue from threshold to 2x, 3x?")
    print("=" * 140)
    print(f"{'Token':<8} {'Dir':<4} {'Thresh':<7} {'N':>5} "
          "| {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} "
          "| {'Reach 2x 4h':>12} {'Reach 2x 8h':>12} {'Reach 2x 16h':>13} "
          "| {'Reach 3x 4h':>12} {'Reach 3x 8h':>12} {'Reach 3x 16h':>13}")
    print("-" * 140)

    agg = {d: {t: {w: {'rets': [], 'hits': [], 'r2': [], 'r3': []} for w in WINDOWS}
              for t in thresholds} for d in ['long', 'short']}

    for token in TOKENS:
        candles = get_candles(token)
        if len(candles) < 100:
            continue

        for direction in ['long', 'short']:
            for thresh in thresholds:
                results = backtest_momentum_cross(token, thresh, direction, WINDOWS)
                if not results:
                    continue
                n = len(results[1]['returns'])
                if n < 3:
                    continue

                def fmt_window(w):
                    rets = results[w]['returns']
                    hits = results[w]['hit']
                    r2 = results[w]['reached_2x']
                    r3 = results[w]['reached_3x']
                    if not rets:
                        return f"{'N/A':>10} {'N/A':>10} {'N/A':>12} {'N/A':>12} {'N/A':>13}"
                    avg_ret = statistics.mean(rets) * 100
                    hit_rate = statistics.mean(hits) * 100
                    r2_rate = statistics.mean(r2) * 100 if r2 else 0
                    r3_rate = statistics.mean(r3) * 100 if r3 else 0
                    return f"{avg_ret:>+10.2f} {hit_rate:>10.1f} {r2_rate:>12.1f} {r3_rate:>12.1f}"

                print(f"{token:<8} {direction:<4} {thresh:<7} {n:>5} | " + fmt_window(1) + " | " + fmt_window(2) + " | " + fmt_window(4) + " | " + fmt_window(6))

                # aggregate
                for w in WINDOWS:
                    agg[direction][thresh][w]['rets'].extend(results[w]['returns'])
                    agg[direction][thresh][w]['hits'].extend(results[w]['hit'])
                    agg[direction][thresh][w]['r2'].extend(results[w]['reached_2x'])
                    agg[direction][thresh][w]['r3'].extend(results[w]['reached_3x'])

    print("\n" + "=" * 140)
    print("AGGREGATE:")
    print(f"{'Dir':<4} {'Thresh':<7} {'N':>6} "
          "| {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} "
          "| {'Reach 2x 4h':>12} {'Reach 2x 8h':>12} {'Reach 2x 16h':>13} "
          "| {'Reach 3x 4h':>12} {'Reach 3x 8h':>12} {'Reach 3x 16h':>13}")
    print("-" * 140)

    for direction in ['long', 'short']:
        for thresh in thresholds:
            def fmt_agg(w):
                rets = agg[direction][thresh][w]['rets']
                hits = agg[direction][thresh][w]['hits']
                r2 = agg[direction][thresh][w]['r2']
                r3 = agg[direction][thresh][w]['r3']
                if not rets:
                    return f"{'N/A':>10} {'N/A':>10} {'N/A':>12} {'N/A':>12} {'N/A':>13}"
                avg_ret = statistics.mean(rets) * 100
                hit_rate = statistics.mean(hits) * 100
                r2_rate = statistics.mean(r2) * 100 if r2 else 0
                r3_rate = statistics.mean(r3) * 100 if r3 else 0
                return f"{avg_ret:>+10.2f} {hit_rate:>10.1f} {r2_rate:>12.1f} {r3_rate:>12.1f}"

            n = len(agg[direction][thresh][1]['rets'])
            if n < 10:
                continue
            print(f"{direction:<4} {thresh:<7} {n:>6} | " + fmt_agg(1) + " | " + fmt_agg(2) + " | " + fmt_agg(4) + " | " + fmt_agg(6))

    # Part 2: Simple entry at z>=threshold (no cross required)
    print("\n\n" + "=" * 120)
    print("PART 2: Entry at z >= threshold (no cross) — simpler signal, mean-reversion vs momentum")
    print("=" * 120)
    print(f"{'Token':<8} {'Dir':<4} {'Thresh':<7} {'N':>5} "
          "| {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} "
          "| {'4h Hit%':>10} {'8h Hit%':>10} {'16h Hit%':>10} {'24h Hit%':>10}")
    print("-" * 120)

    agg2 = {d: {t: {w: {'rets': [], 'hits': []} for w in WINDOWS}
               for t in thresholds} for d in ['long', 'short']}

    for token in TOKENS:
        candles = get_candles(token)
        if len(candles) < 100:
            continue

        closes = [c[1] for c in candles]
        zscores_roll = []
        for i in range(len(closes)):
            if i < 60:
                zscores_roll.append(None)
                continue
            subset = closes[i-60:i]
            mu = statistics.mean(subset)
            std = statistics.stdev(subset) if len(subset) > 1 else 1
            zscores_roll.append((closes[i] - mu) / std if std != 0 else 0.0)

        for direction in ['long', 'short']:
            for thresh in thresholds:
                rets_by_w = {w: [] for w in WINDOWS}
                hits_by_w = {w: [] for w in WINDOWS}

                for i in range(len(closes) - max(WINDOWS)):
                    z = zscores_roll[i]
                    if z is None:
                        continue

                    if direction == 'long' and z >= thresh:
                        entry = closes[i]
                        for w in WINDOWS:
                            ret = (closes[i+w] - entry) / entry
                            rets_by_w[w].append(ret)
                            hits_by_w[w].append(ret > 0)
                    elif direction == 'short' and z <= -thresh:
                        entry = closes[i]
                        for w in WINDOWS:
                            ret = -(closes[i+w] - entry) / entry
                            rets_by_w[w].append(ret)
                            hits_by_w[w].append(ret > 0)

                n = len(rets_by_w[1])
                if n < 3:
                    continue

                def fmt(w):
                    if not rets_by_w[w]:
                        return f"{'N/A':>10} {'N/A':>10}"
                    return f"{statistics.mean(rets_by_w[w])*100:>+10.2f} {statistics.mean(hits_by_w[w])*100:>10.1f}"

                print(f"{token:<8} {direction:<4} {thresh:<7} {n:>5} | " + " ".join(fmt(w) for w in WINDOWS))

                for w in WINDOWS:
                    agg2[direction][thresh][w]['rets'].extend(rets_by_w[w])
                    agg2[direction][thresh][w]['hits'].extend(hits_by_w[w])

    print("\n" + "=" * 120)
    print("AGGREGATE (z >= threshold, no cross):")
    print(f"{'Dir':<4} {'Thresh':<7} {'N':>6} "
          "| {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} "
          "| {'4h Hit%':>10} {'8h Hit%':>10} {'16h Hit%':>10} {'24h Hit%':>10}")
    print("-" * 120)

    for direction in ['long', 'short']:
        for thresh in thresholds:
            n = len(agg2[direction][thresh][1]['rets'])
            if n < 10:
                continue
            def fmt_agg2(w):
                rets = agg2[direction][thresh][w]['rets']
                hits = agg2[direction][thresh][w]['hits']
                if not rets:
                    return f"{'N/A':>10} {'N/A':>10}"
                return f"{statistics.mean(rets)*100:>+10.2f} {statistics.mean(hits)*100:>10.1f}"
            print(f"{direction:<4} {thresh:<7} {n:>6} | " + " ".join(fmt_agg2(w) for w in WINDOWS))

if __name__ == '__main__':
    main()
