#!/usr/bin/env python3
"""
backtest_r2_trend.py — R² Trend Regression Signal Backtester on 5m candles

Tests whether OLS regression R² + slope detects profitable trends on 5m candles.
Both LONG and SHORT directions tested separately (directional asymmetry expected).

Usage:
  python3 backtest_r2_trend.py                          # all tokens, default params
  python3 backtest_r2_trend.py --tokens BTC ETH        # specific tokens
  python3 backtest_r2_trend.py --top 20                # top 20 by candle count
  python3 backtest_r2_trend.py --lookback 16           # custom lookback
  python3 backtest_r2_trend.py --r2-thresh 0.5          # custom R² threshold
  python3 backtest_r2_trend.py --exit reverse          # exit-on-reverse (default)
  python3 backtest_r2_trend.py --exit fixed            # fixed SL/TP exits
  python3 backtest_r2_trend.py --direction both        # test both LONG and SHORT
"""

import sys, os, sqlite3, time, argparse, math
from collections import defaultdict, Counter
from statistics import mean

CANDLES_DB = '/root/.hermes/data/candles.db'

# ── CLI args ────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='R² Trend Backtester on 5m candles')
parser.add_argument('--tokens', nargs='+', default=None)
parser.add_argument('--top', type=int, default=None)
parser.add_argument('--min-candles', type=int, default=2000)
parser.add_argument('--lookback', type=int, default=16,
                    help='OLS lookback window in candles (default: 16)')
parser.add_argument('--r2-thresh', type=float, default=0.60,
                    help='Minimum R² for signal (default: 0.60)')
parser.add_argument('--exit', choices=['reverse', 'fixed'], default='reverse',
                    help='Exit type: reverse-of-signal or fixed SL/TP (default: reverse)')
parser.add_argument('--sl-pct', type=float, default=0.75,
                    help='Stop loss %% for fixed exit (default: 0.75)')
parser.add_argument('--tp-pct', type=float, default=1.0,
                    help='Take profit %% for fixed exit (default: 1.0)')
parser.add_argument('--direction', choices=['both', 'long', 'short'], default='both')
args = parser.parse_args()

# ── OLS helpers ─────────────────────────────────────────────────────────────────

def ols_slope_r2(closes: list) -> tuple:
    """Compute slope and R² of closes (y) vs index (x)."""
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


def backtest_token(closes: list, direction: str, lookback: int,
                   r2_thresh: float, exit_type: str,
                   sl_pct: float, tp_pct: float):
    """
    Backtest R² regression signal on one token's close series.
    direction: 'long' or 'short'
    exit_type: 'reverse' or 'fixed'
    Returns list of (pnl_pct, bars_held, exit_reason, r2, slope).
    """
    n = len(closes)
    if n < lookback + 5:
        return []

    trades = []
    in_pos = False
    entry_price = 0.0
    entry_bar = 0
    entry_r2 = 0.0
    entry_slope = 0.0

    for i in range(lookback, n - 1):
        window = closes[i - lookback + 1: i + 1]
        slope, r2 = ols_slope_r2(window)
        price = closes[i]

        if not in_pos:
            # Compute regression line value at current bar
            # y = y_mean + slope * (i - x_mean)
            # We need x_mean of the window
            x_vals = list(range(lookback))
            x_mean = (lookback - 1) / 2.0
            y_mean = sum(window) / lookback
            reg_line_now = y_mean + slope * (lookback - 1 - x_mean)

            if direction == 'long':
                # LONG: slope > 0 (uptrend), price above regression line
                cond = slope > 0 and r2 >= r2_thresh and price > reg_line_now
            else:  # short
                # SHORT: slope < 0 (downtrend), price below regression line
                cond = slope < 0 and r2 >= r2_thresh and price < reg_line_now

            if cond:
                in_pos = True
                entry_price = price
                entry_bar = i
                entry_r2 = r2
                entry_slope = slope
        else:
            # Exit logic
            window = closes[entry_bar - lookback + 1: entry_bar + 1]
            slope, r2 = ols_slope_r2(window)
            x_vals = list(range(lookback))
            x_mean = (lookback - 1) / 2.0
            y_mean = sum(window) / lookback
            reg_line_then = y_mean + slope * (lookback - 1 - x_mean)

            exited = False
            exit_reason = 'end'

            if exit_type == 'reverse':
                if direction == 'long':
                    # Exit when price crosses below regression line
                    if price < reg_line_then:
                        exited = True
                        exit_reason = 'reverse'
                else:
                    # Exit when price crosses above regression line
                    if price > reg_line_then:
                        exited = True
                        exit_reason = 'reverse'
            else:  # fixed
                pct_move = (price - entry_price) / entry_price * 100
                if direction == 'long':
                    if pct_move <= -sl_pct:
                        exited = True
                        exit_reason = 'sl'
                    elif pct_move >= tp_pct:
                        exited = True
                        exit_reason = 'tp'
                else:
                    if pct_move >= sl_pct:
                        exited = True
                        exit_reason = 'sl'
                    elif pct_move <= -tp_pct:
                        exited = True
                        exit_reason = 'tp'

            if exited:
                pct = (price - entry_price) / entry_price * 100
                if direction == 'short':
                    pct = -pct
                bars = i - entry_bar
                trades.append((pct, bars, exit_reason, entry_r2, entry_slope))
                in_pos = False

    return trades


# ── Get tokens from DB ──────────────────────────────────────────────────────────

conn = sqlite3.connect(CANDLES_DB)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'candles_%'")
tables = [r[0] for r in cur.fetchall()]
table_5m = 'candles_5m' if 'candles_5m' in tables else None
if not table_5m:
    print("ERROR: candles_5m table not found. Run backfill first.")
    sys.exit(1)

# Get token candle counts
cur.execute(f"SELECT token, COUNT(*) FROM {table_5m} GROUP BY token ORDER BY COUNT(*) DESC")
token_counts = {r[0]: r[1] for r in cur.fetchall()}

if args.top:
    tokens = [t for t, c in token_counts.items() if c >= args.min_candles][:args.top]
elif args.tokens:
    tokens = [t.upper() for t in args.tokens]
else:
    tokens = [t for t, c in token_counts.items() if c >= args.min_candles]

print(f"R² Trend Backtest — {len(tokens)} tokens | lookback={args.lookback} | r2_thresh={args.r2_thresh} | exit={args.exit}")
print(f"5m candles from table: {table_5m}")
print()

# ── Fetch candle data ──────────────────────────────────────────────────────────

token_closes = {}
for token in tokens:
    cur.execute(
        f"SELECT close FROM {table_5m} WHERE token=? ORDER BY ts ASC",
        (token,)
    )
    rows = cur.fetchall()
    if rows:
        token_closes[token] = [r[0] for r in rows]

conn.close()

print(f"Fetched data for {len(token_closes)} tokens")
print()

# ── Run backtest ───────────────────────────────────────────────────────────────

results = {'long': [], 'short': []}

for token, closes in token_closes.items():
    for direction in (['long', 'short'] if args.direction == 'both' else [args.direction]):
        trades = backtest_token(
            closes, direction, args.lookback, args.r2_thresh,
            args.exit, args.sl_pct, args.tp_pct
        )
        for pct, bars, reason, r2, slope in trades:
            results[direction].append({
                'token': token,
                'pnl_pct': pct,
                'bars': bars,
                'exit': reason,
                'r2': r2,
                'slope': slope,
            })

# ── Print results ──────────────────────────────────────────────────────────────

for direction in (['long', 'short'] if args.direction == 'both' else [args.direction]):
    trades = results[direction]
    if not trades:
        print(f"{direction.upper()}: No signals")
        continue

    pnls = [t['pnl_pct'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    wr = len(wins) / len(pnls) * 100 if pnls else 0
    avg_pnl = mean(pnls) if pnls else 0
    net = sum(pnls)
    avg_bars = mean(t['bars'] for t in trades)
    avg_win = mean(wins) if wins else 0
    avg_loss = mean(losses) if losses else 0

    print(f"{'─'*60}")
    print(f"{direction.upper()} — {len(trades)} trades | WR: {wr:.1f}% | Net: {net:+.1f}% | Avg: {avg_pnl:+.2f}%")
    print(f"  Wins: {len(wins)} ({avg_win:+.2f}%) | Losses: {len(losses)} ({avg_loss:+.2f}%)")
    print(f"  Avg bars held: {avg_bars:.0f}")
    print(f"  Exit reasons: {dict(Counter(t['exit'] for t in trades))}")

    # Per-token breakdown
    by_token = defaultdict(list)
    for t in trades:
        by_token[t['token']].append(t['pnl_pct'])

    token_summary = []
    for tok, ps in sorted(by_token.items(), key=lambda x: sum(x[1]), reverse=True)[:10]:
        n = len(ps)
        net_tok = sum(ps)
        wr_tok = sum(1 for p in ps if p > 0) / n * 100
        token_summary.append(f"  {tok:<10} n={n:3d}  WR={wr_tok:5.1f}%  net={net_tok:+8.2f}%")

    print(f"  Top tokens:")
    for line in token_summary:
        print(line)

    print()

print(f"{'═'*60}")
all_pnls = results.get('long', []) + results.get('short', [])
if all_pnls:
    print(f"COMBINED NET: {sum(t['pnl_pct'] for t in all_pnls):+.1f}%")
