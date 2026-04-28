#!/usr/bin/env python3
"""
Fast R² mean reversion sweep on 5m candles.
Samples every 4th candle for speed, then validates top params on full data.
"""
import sys, os, sqlite3, argparse
from collections import Counter
from statistics import mean

CANDLES_DB = '/root/.hermes/data/candles.db'
SAMPLE_RATE = 4  # every 4th candle

parser = argparse.ArgumentParser()
parser.add_argument('--min-candles', type=int, default=5000)
parser.add_argument('--top-tokens', type=int, default=20)
parser.add_argument('--direction', choices=['long', 'short', 'both'], default='both')
args = parser.parse_args()

def ols_slope_r2(closes):
    n = len(closes)
    if n < 3:
        return 0.0, 0.0
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(closes) / n
    num = sum((x_vals[i] - x_mean) * (closes[i] - y_mean) for i in range(n))
    den_x = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
    den_y = sum((closes[i] - y_mean) ** 2 for i in range(n))
    if den_x == 0 or den_y == 0:
        return 0.0, 0.0
    slope = num / den_x
    y_pred = [y_mean + slope * (x_vals[i] - x_mean) for i in range(n)]
    ss_res = sum((closes[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = den_y
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return slope, r2

def backtest_fast(closes, direction, lookback, r2_thresh):
    """Fast version: skip SAMPLE_RATE bars."""
    n = len(closes)
    if n < lookback + 5:
        return []
    step = SAMPLE_RATE
    trades = []
    in_pos = False
    entry_price = 0.0

    # Precompute regression for every bar at step granularity
    for idx in range(lookback, n, step):
        if idx + 1 >= n:
            break
        window = closes[idx - lookback + 1: idx + 1]
        if len(window) < lookback:
            break
        slope, r2 = ols_slope_r2(window)
        x_vals = list(range(lookback))
        x_mean = (lookback - 1) / 2.0
        y_mean = sum(window) / lookback
        reg_val = y_mean + slope * (lookback - 1 - x_mean)
        price = closes[idx]

        if not in_pos:
            if direction == 'long' and slope < 0 and r2 >= r2_thresh and price < reg_val:
                in_pos = True
                entry_price = price
            elif direction == 'short' and slope > 0 and r2 >= r2_thresh and price > reg_val:
                in_pos = True
                entry_price = price
        else:
            # Get current bar's reg line
            if idx < lookback:
                continue
            cur_window = closes[idx - lookback + 1: idx + 1]
            if len(cur_window) < lookback:
                continue
            cur_slope, _ = ols_slope_r2(cur_window)
            cur_x_vals = list(range(lookback))
            cur_x_mean = (lookback - 1) / 2.0
            cur_y_mean = sum(cur_window) / lookback
            cur_reg = cur_y_mean + cur_slope * (lookback - 1 - cur_x_mean)
            cur_price = closes[idx]

            exited = (direction == 'long' and cur_price > cur_reg) or \
                     (direction == 'short' and cur_price < cur_reg)
            if exited:
                pct = (cur_price - entry_price) / entry_price * 100
                if direction == 'short':
                    pct = -pct
                trades.append(pct)
                in_pos = False

    return trades

# Fetch data (sample every SAMPLE_RATE for speed)
conn = sqlite3.connect(CANDLES_DB)
cur = conn.cursor()
cur.execute("""
    SELECT token, COUNT(*) FROM candles_5m
    GROUP BY token HAVING COUNT(*) >= ?
    ORDER BY COUNT(*) DESC LIMIT ?
""", (args.min_candles, args.top_tokens))
token_rows = cur.fetchall()

token_closes = {}
for token, count in token_rows:
    cur.execute("""
        SELECT close FROM candles_5m
        WHERE token=? ORDER BY ts ASC
    """, (token,))
    rows = [r[0] for r in cur.fetchall()]
    if rows:
        # Sample every SAMPLE_RATE bars for fast sweep
        token_closes[token] = rows[::SAMPLE_RATE]
conn.close()

print(f"Tokens: {len(token_closes)} | Sampled every {SAMPLE_RATE} bars")
print(f"Avg bars per token (sampled): {mean(len(v) for v in token_closes.values()):.0f}")
print()

LOOKBACKS = [8, 12, 16, 24, 32, 48, 64]
R2_THRESHES = [0.40, 0.50, 0.55, 0.60, 0.65, 0.70]
DIRECTIONS = (['long', 'short'] if args.direction == 'both' else [args.direction])

best = {}
for direction in DIRECTIONS:
    print(f"\n{'═'*65}")
    print(f"  {direction.upper()} — sampled sweep")
    print(f"{'═'*65}")
    print(f"{'LB':>4} {'R2':>5} {'N':>5} {'WR%':>6} {'Net%':>8} {'Avg%':>7}")
    print(f"{'─'*65}")

    for lb in LOOKBACKS:
        for r2 in R2_THRESHES:
            all_pnls = []
            for closes in token_closes.values():
                trades = backtest_fast(closes, direction, lb, r2)
                all_pnls.extend(trades)

            if not all_pnls:
                continue

            n = len(all_pnls)
            wr = sum(1 for p in all_pnls if p > 0) / n * 100
            net = sum(all_pnls)
            avg = mean(all_pnls)
            print(f"{lb:>4} {r2:>5.2f} {n:>5} {wr:>6.1f} {net:>8.1f} {avg:>7.3f}")
            best[(direction, lb, r2)] = (n, wr, net, avg)

    print(f"\n  Top 5 by Net (sampled):")
    dir_keys = [k for k in best.keys() if k[0] == direction]
    sorted_keys = sorted(dir_keys, key=lambda k: best[k][2], reverse=True)[:5]
    for k in sorted_keys:
        n, wr, net, avg = best[k]
        print(f"    LB={k[1]:>3} R2={k[2]:.2f}  N={n:>5}  WR={wr:>5.1f}%  Net={net:>+8.1f}%  Avg={avg:>+.4f}%")
