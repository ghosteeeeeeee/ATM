#!/usr/bin/env python3
"""
backtest_momentum_pulse_5m.py — Momentum Pulse Signal Backtester on 5m candles

Tests the proposed momentum pulse signal rules on 5m candles (better data quality):
Entry:
  1. Pulse: 3 consecutive green candles
  2. Trend: Close > SMA(10)
  3. Momentum: RSI > 50 and RSI < 75
  4. Expansion: ATR(14) > SMA(ATR,20)
  5. Direction: 5-bar pre-move > +0.5%

Exit:
  - Profit target: 2x ATR from entry
  - Stop loss: 1x ATR from entry (or 1% whichever tighter)
  - Time exit: 60 candles (5 hours on 5m)

Usage:
  python3 backtest_momentum_pulse_5m.py --tokens TURBO DOGE ENA ETH BTC
  python3 backtest_momentum_pulse_5m.py --top 10
"""

import sys, os, sqlite3, argparse
from collections import defaultdict
from datetime import datetime

CANDLES_DB = '/root/.hermes/data/candles.db'

# ── CLI args ────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='Momentum Pulse Signal Backtester (5m)')
parser.add_argument('--tokens', nargs='+', default=None)
parser.add_argument('--top', type=int, default=None)
parser.add_argument('--min-candles', type=int, default=200)
parser.add_argument('--days', type=int, default=14, help='Days of data to use (default: 14)')
parser.add_argument('--min-green', type=int, default=3, help='Min consecutive green candles (default: 3)')
parser.add_argument('--sma-period', type=int, default=10, help='SMA period for trend filter (default: 10)')
parser.add_argument('--rsi-min', type=float, default=50, help='Min RSI (default: 50)')
parser.add_argument('--rsi-max', type=float, default=75, help='Max RSI (default: 75)')
parser.add_argument('--atr-period', type=int, default=14, help='ATR period (default: 14)')
parser.add_argument('--atr-sma-period', type=int, default=20, help='ATR SMA period (default: 20)')
parser.add_argument('--pre-move', type=float, default=0.5, help='Min pre-move %% (default: 0.5)')
parser.add_argument('--cooldown', type=int, default=6, help='Cooldown candles between entries (default: 6 = 30min on 5m)')
args = parser.parse_args()

# ── Indicator helpers (vectorized) ─────────────────────────────────────────────

def sma(values, period):
    """Simple Moving Average - returns list of same length, None for insufficient data."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        if any(v is None for v in window):
            continue
        result[i] = sum(window) / period
    return result

def rsi(closes, period=14):
    """Relative Strength Index - returns list of same length."""
    result = [None] * len(closes)
    if len(closes) < period + 1:
        return result
    
    # Calculate initial gains/losses
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    
    # Initial average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Calculate RSI
    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
        
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - (100 / (1 + rs))
    
    return result

def atr(highs, lows, closes, period=14):
    """Average True Range - returns list of same length."""
    result = [None] * len(closes)
    if len(closes) < period + 1:
        return result
    
    # Calculate true ranges
    trs = [None] * len(closes)
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs[i] = tr
    
    # Initial ATR
    atr_vals = [None] * len(closes)
    for i in range(period, len(closes)):
        if atr_vals[i-1] is None:
            atr_vals[i] = sum(trs[i-period+1:i+1]) / period
        else:
            atr_vals[i] = (atr_vals[i-1] * (period - 1) + trs[i]) / period
    
    return atr_vals

def is_green(open_price, close_price):
    """Check if candle is green (close > open)."""
    return close_price > open_price

# ── Signal detection ───────────────────────────────────────────────────────────

def detect_momentum_pulse(candles, idx, params, indicators):
    """
    Detect momentum pulse signal at candle index idx.
    candles: list of (ts, open, high, low, close, volume)
    indicators: precomputed indicator arrays
    Returns: signal dict or None
    """
    min_green = params['min_green']
    sma_period = params['sma_period']
    rsi_min = params['rsi_min']
    rsi_max = params['rsi_max']
    atr_period = params['atr_period']
    atr_sma_period = params['atr_sma_period']
    pre_move = params['pre_move']
    
    # Need enough data
    if idx < max(sma_period, atr_period, atr_sma_period, 20):
        return None
    
    # Extract OHLC
    opens = [c[1] for c in candles[:idx+1]]
    closes = [c[4] for c in candles[:idx+1]]
    
    # Rule 1: 3 consecutive green candles
    if idx < min_green - 1:
        return None
    for i in range(idx - min_green + 1, idx + 1):
        if not is_green(opens[i], closes[i]):
            return None
    
    # Rule 2: Close > SMA(10)
    sma_val = indicators['sma'][idx]
    if sma_val is None or closes[idx] <= sma_val:
        return None
    
    # Rule 3: RSI > 50 and RSI < 75
    rsi_val = indicators['rsi'][idx]
    if rsi_val is None or rsi_val < rsi_min or rsi_val > rsi_max:
        return None
    
    # Rule 4: ATR(14) > SMA(ATR,20)
    atr_val = indicators['atr'][idx]
    atr_sma_val = indicators['atr_sma'][idx]
    if atr_val is None or atr_sma_val is None or atr_val <= atr_sma_val:
        return None
    
    # Rule 5: 5-bar pre-move > +0.5%
    if idx < 5:
        return None
    pre_move_pct = (closes[idx] - closes[idx-5]) / closes[idx-5] * 100
    if pre_move_pct < pre_move:
        return None
    
    # Calculate ATR for exit levels
    atr_at_entry = atr_val
    
    return {
        'entry_price': closes[idx],
        'entry_bar': idx,
        'rsi': rsi_val,
        'atr': atr_at_entry,
        'pre_move': pre_move_pct,
        'sma': sma_val,
    }

# ── Backtest engine ────────────────────────────────────────────────────────────

def backtest_token(token, candles, params, indicators):
    """
    Run backtest on one token's candles.
    Returns list of trades: (pnl_pct, bars_held, exit_reason, entry_price, exit_price)
    """
    cooldown = params['cooldown']
    trades = []
    in_position = False
    entry_price = 0.0
    entry_bar = 0
    entry_atr = 0.0
    last_entry_bar = -cooldown  # allow first entry
    
    for i in range(len(candles)):
        if not in_position:
            # Check cooldown
            if i - last_entry_bar < cooldown:
                continue
            
            # Check for entry signal
            signal = detect_momentum_pulse(candles, i, params, indicators)
            if signal is None:
                continue
            
            # Enter position
            in_position = True
            entry_price = signal['entry_price']
            entry_bar = i
            entry_atr = signal['atr']
            last_entry_bar = i
            
        else:
            # Check for exit
            current_price = candles[i][4]  # close
            bars_held = i - entry_bar
            
            # Exit levels
            tp_price = entry_price + 2 * entry_atr
            sl_price = max(entry_price - entry_atr, entry_price * 0.99)  # 1% or ATR, whichever tighter
            
            # Check TP/SL
            if current_price >= tp_price:
                pnl_pct = (current_price - entry_price) / entry_price * 100
                trades.append((pnl_pct, bars_held, 'TP', entry_price, current_price))
                in_position = False
                continue
            
            if current_price <= sl_price:
                pnl_pct = (current_price - entry_price) / entry_price * 100
                trades.append((pnl_pct, bars_held, 'SL', entry_price, current_price))
                in_position = False
                continue
            
            # Time exit (60 candles = 5 hours on 5m)
            if bars_held >= 60:
                pnl_pct = (current_price - entry_price) / entry_price * 100
                trades.append((pnl_pct, bars_held, 'TIME', entry_price, current_price))
                in_position = False
                continue
    
    # Close any open position at end
    if in_position:
        current_price = candles[-1][4]
        pnl_pct = (current_price - entry_price) / entry_price * 100
        trades.append((pnl_pct, len(candles) - entry_bar, 'END', entry_price, current_price))
    
    return trades

# ── Main backtest ──────────────────────────────────────────────────────────────

def main():
    # Parameters
    params = {
        'min_green': args.min_green,
        'sma_period': args.sma_period,
        'rsi_min': args.rsi_min,
        'rsi_max': args.rsi_max,
        'atr_period': args.atr_period,
        'atr_sma_period': args.atr_sma_period,
        'pre_move': args.pre_move,
        'cooldown': args.cooldown,
    }
    
    # Connect to database
    conn = sqlite3.connect(CANDLES_DB)
    cursor = conn.cursor()
    
    # Get tokens to test
    if args.tokens:
        tokens = args.tokens
    else:
        # Get tokens with enough data
        cutoff_ts = int((datetime.now().timestamp() - args.days * 86400))
        cursor.execute('''
            SELECT token, COUNT(*) as cnt
            FROM candles_5m
            WHERE ts >= ?
            GROUP BY token
            HAVING cnt >= ?
            ORDER BY cnt DESC
        ''', (cutoff_ts, args.min_candles))
        
        rows = cursor.fetchall()
        if args.top:
            tokens = [r[0] for r in rows[:args.top]]
        else:
            tokens = [r[0] for r in rows[:10]]  # default top 10
    
    print(f'Momentum Pulse Backtest (5m) — {len(tokens)} tokens')
    print(f'Parameters: {params}')
    print('=' * 80)
    
    # Results storage
    all_trades = []
    token_results = {}
    
    for token in tokens:
        # Get candles
        cutoff_ts = int((datetime.now().timestamp() - args.days * 86400))
        cursor.execute('''
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ? AND ts >= ?
            ORDER BY ts ASC
        ''', (token, cutoff_ts))
        
        rows = cursor.fetchall()
        if len(rows) < params['sma_period'] + params['atr_sma_period'] + 50:
            print(f'{token}: Insufficient data ({len(rows)} candles)')
            continue
        
        # Precompute indicators
        opens = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        closes = [r[4] for r in rows]
        
        indicators = {
            'sma': sma(closes, params['sma_period']),
            'rsi': rsi(closes, 14),
            'atr': atr(highs, lows, closes, params['atr_period']),
            'atr_sma': sma(atr(highs, lows, closes, params['atr_period']), params['atr_sma_period']),
        }
        
        # Run backtest
        trades = backtest_token(token, rows, params, indicators)
        
        if not trades:
            print(f'{token}: No trades')
            continue
        
        # Calculate stats
        wins = [t for t in trades if t[0] > 0]
        losses = [t for t in trades if t[0] <= 0]
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(t[0] for t in trades)
        avg_win = sum(t[0] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t[0] for t in losses) / len(losses) if losses else 0
        
        token_results[token] = {
            'trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
        }
        
        all_trades.extend([(token, t) for t in trades])
        
        # Print token results
        print(f'{token:8s}: {len(trades):3d} trades, {win_rate:5.1f}% WR, PnL: {total_pnl:+.2f}% '
              f'(avg win: {avg_win:+.2f}%, avg loss: {avg_loss:+.2f}%)')
    
    # Overall stats
    if all_trades:
        print('=' * 80)
        all_pnl = [t[1][0] for t in all_trades]
        wins = [p for p in all_pnl if p > 0]
        losses = [p for p in all_pnl if p <= 0]
        overall_wr = len(wins) / len(all_pnl) * 100
        overall_pnl = sum(all_pnl)
        
        print(f'OVERALL: {len(all_pnl)} trades, {overall_wr:.1f}% WR, PnL: {overall_pnl:+.2f}%')
        
        # Exit reason breakdown
        exit_reasons = defaultdict(int)
        for token, trade in all_trades:
            exit_reasons[trade[2]] += 1
        
        print(f'Exit reasons: {dict(exit_reasons)}')
        
        # Check claim: "ENA is the standout performer (64.2% WR, +69.76% PnL)"
        if 'ENA' in token_results:
            ena = token_results['ENA']
            print(f'\\nENA claim check: WR={ena["win_rate"]:.1f}% (claimed 64.2%), PnL={ena["total_pnl"]:+.2f}% (claimed +69.76%)')
        
        # Check claim: "TURBO missed because R² > 0.70 blocked 84% of checks"
        if 'TURBO' in token_results:
            turbo = token_results['TURBO']
            print(f'TURBO claim check: {turbo["trades"]} trades (should be low if R² blocked)')
    
    conn.close()

if __name__ == '__main__':
    main()