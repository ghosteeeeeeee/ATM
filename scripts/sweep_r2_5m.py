#!/usr/bin/env python3
"""
Sweep R² backtest across multiple lookbacks and R² thresholds on 5m.
"""
import sys, os, sqlite3, argparse
from collections import defaultdict
from statistics import mean

CANDLES_DB = '/root/.hermes/data/candles.db'

parser = argparse.ArgumentParser()
parser.add_argument('--min-candles', type=int, default=500)
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

def backtest(closes, direction, lookback, r2_thresh):
    n = len(closes)
    if n < lookback + 5:
        return []

    trades = []
    in_pos = False
    entry_price = 0.0
    entry_bar = 0

    for i in range(lookback, n - 1):
        window = closes[i - lookback + 1: i + 1]
        slope, r2 = ols_slope_r2(window)
        x_vals = list(range(lookback))
        x_mean = (lookback - 1) / 2.0
        y_mean = sum(window) / lookback
        reg_line = y_mean + slope * (lookback - 1 - x_mean)
        price = closes[i]

        if not in_pos:
            if direction == 'long' and slope > 0 and r2 >= r2_thresh and price > reg_line:
                in_pos = True
                entry_price = price
                entry_bar = i
            elif direction == 'short' and slope < 0 and r2 >= r2_thresh and price < reg_line:
                in_pos = True
                entry_price = price
                entry_bar = i
        else:
            # Recompute regression at current bar
            cur_window = closes[i - lookback + 1: i + 1]
            cur_slope, _ = ols_slope_r2(cur_window)
            cur_x_vals = list(range(lookback))
            cur_x_mean = (lookback - 1) / 2.0
            cur_y_mean = sum(cur_window) / lookback
            cur_reg_line = cur_y_mean + cur_slope * (lookback - 1 - cur_x_mean)
            cur_price = closes[i]

            exited = False
            if direction == 'long' and cur_price < cur_reg_line:
                exited = True
            elif direction == 'short' and cur_price > cur_reg_line:
                exited = True

            if exited:
                pct = (cur_price - entry_price) / entry_price * 100
                if direction == 'short':
                    pct = -pct
                trades.append(pct)
                in_pos = False

    return trades

# Fetch data
conn = sqlite3.connect(CANDLES_DB)
cur = conn.cursor()
cur.execute("SELECT token, COUNT(*) FROM candles_5m GROUP BY token HAVING COUNT(*) >= ? ORDER BY COUNT(*) DESC", (args.min_candles,))
token_rows = cur.fetchall()

token_closes = {}
for token, count in token_rows:
    cur.execute("SELECT close FROM candles_5m WHERE token=? ORDER BY ts ASC", (token,))
    rows = [r[0] for r in cur.fetchall()]
    if rows:
        token_closes[token] = rows
conn.close()

print(f"Tokens: {len(token_closes)} | min_candles: {args.min_candles}")
print()

LOOKBACKS = [8, 12, 16, 24, 32, 48, 64, 96]
R2_THRESHES = [0.40, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
DIRECTIONS = (['long', 'short'] if args.direction == 'both' else [args.direction])

best = {}
for direction in DIRECTIONS:
    print(f"\n{'═'*70}")
    print(f"  {direction.upper()} RESULTS")
    print(f"{'═'*70}")
    print(f"{'LB':>4} {'R2':>5} {'N':>5} {'WR%':>6} {'Net%':>8} {'Avg%':>7} {'Wins':>5} {'Loss':>5}")
    print(f"{'─'*70}")

    for lb in LOOKBACKS:
        for r2 in R2_THRESHES:
            all_pnls = []
            for closes in token_closes.values():
                trades = backtest(closes, direction, lb, r2)
                all_pnls.extend(trades)

            if not all_pnls:
                continue

            n = len(all_pnls)
            wr = sum(1 for p in all_pnls if p > 0) / n * 100
            net = sum(all_pnls)
            avg = mean(all_pnls)
            wins = sum(1 for p in all_pnls if p > 0)
            loss = n - wins
            print(f"{lb:>4} {r2:>5.2f} {n:>5} {wr:>6.1f} {net:>8.2f} {avg:>7.3f} {wins:>5} {loss:>5}")

            key = (direction, lb, r2)
            best[key] = (n, wr, net, avg)

    # Top 5 by net
    print(f"\n  Top 5 by Net P&L:")
    sorted_keys = sorted(best.keys(), key=lambda k: best[k][2], reverse=True)[:5]
    for k in sorted_keys:
        n, wr, net, avg = best[k]
        print(f"    LB={k[1]:>3} R2={k[2]:.2f}  N={n:>4}  WR={wr:>5.1f}%  Net={net:>+8.2f}%  Avg={avg:>+.4f}%")
