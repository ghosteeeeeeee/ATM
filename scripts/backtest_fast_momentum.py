#!/usr/bin/env python3
"""
backtest_fast_momentum.py — Backtest fast_momentum signal with parameter sweeps.

Tests different combinations of:
  - ACCEL_THRESHOLD (z-score acceleration threshold)
  - SPEED_PCTL_MIN (minimum speed percentile)
  - RSI_MAX_LONG / RSI_MIN_SHORT (RSI filters)
  - Forward window (how long to hold)

Usage:
  python3 backtest_fast_momentum.py
  python3 backtest_fast_momentum.py --tokens DYDX ETH BTC
"""

import sys
import os
import sqlite3
import statistics
import time
from datetime import datetime, timezone
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Constants ───────────────────────────────────────────────────────────────────
_PRICE_DB = os.path.join('/root/.hermes/data', 'signals_hermes.db')
_MIN_PRICE_ROWS = 60
_FORWARD_WINDOW = 15  # candles to check for success (1m candles = 15 minutes)

# Parameter grid to test
PARAM_GRID = {
    'accel_threshold': [0.05, 0.10, 0.15, 0.20, 0.25],
    'speed_pctl_min': [30, 40, 50, 60],
    'rsi_max_long': [65, 70, 75, 80],
    'rsi_min_short': [20, 25, 30, 35],
}


def _log(msg):
    print(msg, flush=True)


def _fast_zscore(prices_subset):
    """Compute z-score for a subset of prices."""
    if len(prices_subset) < 5:
        return None
    mu = statistics.mean(prices_subset)
    std = statistics.stdev(prices_subset) if len(prices_subset) > 1 else 1
    if std == 0:
        return None
    return (prices_subset[-1] - mu) / std


def _compute_rsi(closes, period=14):
    """RSI calculation."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _ema(values, period):
    """Compute EMA."""
    if len(values) < period:
        return values[-1] if values else 0
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _compute_macd(closes):
    """Compute MACD histogram."""
    if len(closes) < 26:
        return None
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = _ema([macd_line] * 9, 9)
    return macd_line - signal_line


def _compute_zscore_velocity(prices, window=30):
    """Compute z-score velocity (change in z-score over window)."""
    if len(prices) < window * 2:
        return 0.0
    recent = prices[-window:]
    earlier = prices[-window*2:-window]
    if len(recent) < 5 or len(earlier) < 5:
        return 0.0
    z_now = _fast_zscore(recent)
    z_prior = _fast_zscore(earlier)
    if z_now is None or z_prior is None:
        return 0.0
    return z_now - z_prior


def load_price_data(token, limit=5000):
    """Load price history for a token."""
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [(r[0], r[1]) for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def detect_fast_momentum(prices, timestamps, params, idx):
    """
    Detect fast_momentum signal at a given index in the price array.
    
    Returns: (direction, confidence) or (None, None) if no signal
    """
    accel_threshold = params['accel_threshold']
    speed_pctl_min = params['speed_pctl_min']
    rsi_max_long = params['rsi_max_long']
    rsi_min_short = params['rsi_min_short']
    
    # Need enough data
    if idx < _MIN_PRICE_ROWS:
        return None, None
    
    # Get price windows
    window_5m = prices[idx-4:idx+1]  # last 5 prices
    window_30m = prices[idx-29:idx+1]  # last 30 prices
    window_60m = prices[idx-59:idx+1]  # last 60 prices
    
    if len(window_5m) < 5 or len(window_30m) < 30 or len(window_60m) < 60:
        return None, None
    
    # Compute z-scores
    z_5m = _fast_zscore(window_5m)
    z_30m = _fast_zscore(window_30m)
    z_60m = _fast_zscore(window_60m)
    
    if z_5m is None or z_30m is None or z_60m is None:
        return None, None
    
    # Acceleration: short-term z change vs medium-term
    z_accel = z_5m - z_30m
    
    # Velocity
    velocity = _compute_zscore_velocity(prices[:idx+1], window=30)
    
    # Direction logic
    is_bullish = z_accel > accel_threshold and velocity > 0
    is_bearish = z_accel < -accel_threshold and velocity < 0
    
    if not (is_bullish or is_bearish):
        return None, None
    
    # RSI filter
    rsi = _compute_rsi(window_60m)
    if is_bullish and rsi is not None and rsi > rsi_max_long:
        return None, None
    if is_bearish and rsi is not None and rsi < rsi_min_short:
        return None, None
    
    # MACD filter
    macd_hist = _compute_macd(window_60m)
    if is_bullish and macd_hist is not None and macd_hist < 0:
        return None, None
    if is_bearish and macd_hist is not None and macd_hist > 0:
        return None, None
    
    # z_5m vs z_60m filter
    if is_bullish and z_5m < z_60m - 0.5:
        return None, None
    if is_bearish and z_5m > z_60m + 0.5:
        return None, None
    
    # Confidence scoring
    accel_magnitude = abs(z_accel)
    confidence = min(95.0, 60.0 + accel_magnitude * 100)
    
    direction = 'LONG' if is_bullish else 'SHORT'
    return direction, confidence


def backtest_token(token, params, prices, timestamps):
    """
    Backtest fast_momentum on a single token.
    
    Returns list of trade results: (direction, entry_price, exit_price, pnl_pct)
    """
    trades = []
    forward_window = _FORWARD_WINDOW
    cooldown = 15  # minutes between trades on same token (dedup)
    last_trade_idx = -cooldown - 1
    
    for i in range(_MIN_PRICE_ROWS, len(prices) - forward_window):
        # Dedup: skip if too soon after last trade
        if i - last_trade_idx < cooldown:
            continue
        
        direction, confidence = detect_fast_momentum(prices, timestamps, params, i)
        
        if direction is None:
            continue
        
        entry_price = prices[i]
        
        # Check forward window for exit
        if direction == 'LONG':
            # Exit at highest point in forward window (take profit)
            future_prices = prices[i+1:i+1+forward_window]
            max_price = max(future_prices)
            exit_price = max_price
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:  # SHORT
            future_prices = prices[i+1:i+1+forward_window]
            min_price = min(future_prices)
            exit_price = min_price
            pnl_pct = (entry_price - exit_price) / entry_price * 100
        
        trades.append({
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'confidence': confidence,
            'timestamp': timestamps[i],
        })
        
        last_trade_idx = i
    
    return trades


def run_backtest(tokens=None, params=None):
    """Run backtest across multiple tokens with given parameters."""
    if tokens is None:
        tokens = ['DYDX', 'ETH', 'BTC', 'ASTER', 'AVNT', 'LINK', 'JUP', 'MNT', 'MORPHO', 'ENS']
    
    if params is None:
        params = {
            'accel_threshold': 0.15,
            'speed_pctl_min': 40,
            'rsi_max_long': 70,
            'rsi_min_short': 30,
        }
    
    all_trades = []
    
    for token in tokens:
        data = load_price_data(token, limit=5000)
        if not data or len(data) < 100:
            continue
        
        timestamps = [d[0] for d in data]
        prices = [d[1] for d in data]
        
        trades = backtest_token(token, params, prices, timestamps)
        for t in trades:
            t['token'] = token
        all_trades.extend(trades)
    
    return all_trades


def analyze_results(trades, params=None):
    """Analyze backtest results."""
    if not trades:
        return {'total': 0, 'wr': 0, 'avg_pnl': 0, 'total_pnl': 0}
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    
    total_pnl = sum(t['pnl_pct'] for t in trades)
    avg_pnl = total_pnl / len(trades) if trades else 0
    wr = len(wins) / len(trades) * 100 if trades else 0
    
    # By direction
    long_trades = [t for t in trades if t['direction'] == 'LONG']
    short_trades = [t for t in trades if t['direction'] == 'SHORT']
    
    long_wr = len([t for t in long_trades if t['pnl_pct'] > 0]) / len(long_trades) * 100 if long_trades else 0
    short_wr = len([t for t in short_trades if t['pnl_pct'] > 0]) / len(short_trades) * 100 if short_trades else 0
    
    result = {
        'total': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'wr': wr,
        'avg_pnl': avg_pnl,
        'total_pnl': total_pnl,
        'long_trades': len(long_trades),
        'long_wr': long_wr,
        'short_trades': len(short_trades),
        'short_wr': short_wr,
    }
    
    if params:
        result['params'] = params
    
    return result


def run_parameter_sweep(tokens=None):
    """Run parameter sweep to find optimal parameters."""
    if tokens is None:
        tokens = ['DYDX', 'ETH', 'BTC', 'ASTER', 'AVNT', 'LINK', 'JUP', 'MNT', 'MORPHO', 'ENS']
    
    results = []
    
    # Generate all parameter combinations
    param_keys = list(PARAM_GRID.keys())
    param_values = list(PARAM_GRID.values())
    
    total_combos = 1
    for v in param_values:
        total_combos *= len(v)
    
    _log(f'Running parameter sweep: {total_combos} combinations across {len(tokens)} tokens')
    _log(f'Tokens: {tokens}')
    _log(f'Parameter grid: {PARAM_GRID}')
    _log('')
    
    start_time = time.time()
    
    for i, combo in enumerate(product(*param_values)):
        params = dict(zip(param_keys, combo))
        
        trades = run_backtest(tokens=tokens, params=params)
        result = analyze_results(trades, params)
        results.append(result)
        
        # Progress update
        if (i + 1) % 10 == 0 or (i + 1) == total_combos:
            elapsed = time.time() - start_time
            eta = elapsed / (i + 1) * (total_combos - i - 1)
            _log(f'  [{i+1}/{total_combos}] {result["total"]}T {result["wr"]:.0f}% WR {result["total_pnl"]:+.1f}% PnL | ETA: {eta:.0f}s')
    
    # Sort by total PnL
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    return results


def print_results(results, top_n=20):
    """Print top results."""
    _log(f'\n=== TOP {top_n} RESULTS ===')
    _log(f'{"#":<4} {"T":<5} {"WR%":<6} {"AvgPnL%":<9} {"TotalPnL%":<11} {"Long":<6} {"Short":<7} {"Params"}')
    
    for i, r in enumerate(results[:top_n]):
        params = r.get('params', {})
        param_str = f'accel={params.get("accel_threshold", "?"):.2f} spd={params.get("speed_pctl_min", "?")} rsiL={params.get("rsi_max_long", "?")} rsiS={params.get("rsi_min_short", "?")}'
        _log(f'{i+1:<4} {r["total"]:<5} {r["wr"]:<6.0f} {r["avg_pnl"]:<9.3f} {r["total_pnl"]:<11.2f} {r["long_trades"]:<5}L {r["short_trades"]:<6}S {param_str}')
    
    # Also show worst results for comparison
    _log(f'\n=== WORST 5 (for comparison) ===')
    for i, r in enumerate(results[-5:]):
        params = r.get('params', {})
        param_str = f'accel={params.get("accel_threshold", "?"):.2f} spd={params.get("speed_pctl_min", "?")} rsiL={params.get("rsi_max_long", "?")} rsiS={params.get("rsi_min_short", "?")}'
        _log(f'  {r["total"]}T {r["wr"]:.0f}% WR {r["total_pnl"]:+.1f}% PnL | {param_str}')


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest fast_momentum signal')
    parser.add_argument('--tokens', nargs='+', default=None, help='Tokens to test')
    parser.add_argument('--sweep', action='store_true', help='Run parameter sweep')
    parser.add_argument('--accel', type=float, default=0.15, help='Acceleration threshold')
    parser.add_argument('--speed', type=int, default=40, help='Speed percentile minimum')
    parser.add_argument('--rsi-long', type=int, default=70, help='RSI max for LONG')
    parser.add_argument('--rsi-short', type=int, default=30, help='RSI min for SHORT')
    
    args = parser.parse_args()
    
    if args.sweep:
        results = run_parameter_sweep(tokens=args.tokens)
        print_results(results)
    else:
        params = {
            'accel_threshold': args.accel,
            'speed_pctl_min': args.speed,
            'rsi_max_long': args.rsi_long,
            'rsi_min_short': args.rsi_short,
        }
        _log(f'Testing with params: {params}')
        trades = run_backtest(tokens=args.tokens, params=params)
        result = analyze_results(trades, params)
        _log(f'\nResults: {result["total"]}T {result["wr"]:.0f}% WR {result["total_pnl"]:+.2f}% PnL')
        _log(f'  LONG: {result["long_trades"]}T {result["long_wr"]:.0f}% WR')
        _log(f'  SHORT: {result["short_trades"]}T {result["short_wr"]:.0f}% WR')
        
        if trades:
            _log(f'\nSample trades:')
            for t in trades[:10]:
                _log(f'  {t["token"]:<8} {t["direction"]:<6} entry={t["entry_price"]:.5f} exit={t["exit_price"]:.5f} pnl={t["pnl_pct"]:+.3f}%')
