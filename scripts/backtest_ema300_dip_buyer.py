#!/usr/bin/env python3
"""
Backtest EMA300 Dip Buyer v2 signal on 5 tokens: ARB, CFX, FIL, AVNT, SYRUP
Tests the signal rules and verifies the claimed performance metrics.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

# Signal parameters from the spec
ENTRY_RULES = {
    'ema_period': 300,
    'min_candles_above_ema': 70,  # % of last 100 candles
    'min_ema_slope': 0,  # > 0 means rising
    'ema_slope_period': 20,
    'max_distance_pct': 0.5,  # within 0.5% of EMA300
    'rsi_oversold': 35,  # RSI < 35
    'rsi_min': 15,  # RSI > 15
    'rsi_period': 14,
    'bounce_confirmation': True,  # close > previous close
    'rsi_lookback': 10,  # recent low within 10 bars
}

EXIT_RULES = {
    'tp_pct': 1.5,
    'sl_pct': 0.8,
    'max_hold_candles': 60,
    'trailing_activation_pct': 1.0,
    'trailing_stop_pct': 0.0,  # move SL to breakeven
}

FILTERS = {
    'cooldown_candles': 30,
    'max_entry_rsi': 60,
}

def calculate_ema(closes, period):
    """Calculate EMA for a series of close prices."""
    ema = [closes[0]]
    multiplier = 2 / (period + 1)
    
    for i in range(1, len(closes)):
        ema.append(closes[i] * multiplier + ema[-1] * (1 - multiplier))
    
    return ema

def calculate_rsi(closes, period=14):
    """Calculate RSI for a series of close prices."""
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    # Initial average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    rsi = []
    if avg_loss == 0:
        rsi.append(100.0)
    else:
        rsi.append(100 - (100 / (1 + avg_gain / avg_loss)))
    
    # Subsequent values
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rsi.append(100 - (100 / (1 + avg_gain / avg_loss)))
    
    return rsi

def backtest_token(token, candles_data):
    """Backtest EMA300 dip buyer signal on a single token."""
    if len(candles_data) < 350:  # Need at least 300 + some buffer
        print(f"Insufficient data for {token}: {len(candles_data)} candles")
        return []
    
    closes = [c['close'] for c in candles_data]
    
    # Calculate indicators
    ema300 = calculate_ema(closes, ENTRY_RULES['ema_period'])
    rsi = calculate_rsi(closes, ENTRY_RULES['rsi_period'])
    
    # Pad RSI to align with closes
    rsi_padded = [None] * (ENTRY_RULES['rsi_period']) + rsi
    
    trades = []
    cooldown_counter = 0
    
    for i in range(300, len(closes)):
        current_close = closes[i]
        current_ema = ema300[i]
        current_rsi = rsi_padded[i] if i < len(rsi_padded) else None
        
        if current_rsi is None or current_ema is None:
            continue
            
        # Check cooldown
        if cooldown_counter > 0:
            cooldown_counter -= 1
            continue
        
        # Entry conditions
        # 1. Price > EMA300
        if current_close <= current_ema:
            continue
            
        # 2. Trend strength: >70% of last 100 candles above EMA300
        last_100_closes = closes[max(0, i-99):i+1]
        last_100_ema = ema300[max(0, i-99):i+1]
        if len(last_100_closes) < 100:
            continue
            
        candles_above = sum(1 for c, e in zip(last_100_closes, last_100_ema) if c > e)
        trend_strength = (candles_above / len(last_100_closes)) * 100
        
        if trend_strength < ENTRY_RULES['min_candles_above_ema']:
            continue
            
        # 3. EMA rising (20-bar slope > 0)
        if i >= ENTRY_RULES['ema_slope_period']:
            ema_now = ema300[i]
            ema_prev = ema300[i - ENTRY_RULES['ema_slope_period']]
            ema_slope = ema_now - ema_prev
            
            if ema_slope <= ENTRY_RULES['min_ema_slope']:
                continue
        else:
            continue
            
        # 4. Price within 0.5% of EMA300
        distance_pct = ((current_close - current_ema) / current_ema) * 100
        if distance_pct <= 0 or distance_pct > ENTRY_RULES['max_distance_pct']:
            continue
            
        # 5. Oversold: RSI < 35 (recent low within 10 bars)
        recent_rsi = [rsi_padded[j] for j in range(max(0, i-9), i+1) if j < len(rsi_padded) and rsi_padded[j] is not None]
        if not recent_rsi:
            continue
            
        min_recent_rsi = min(recent_rsi)
        if min_recent_rsi >= ENTRY_RULES['rsi_oversold']:
            continue
            
        # 6. Bounce: Close > previous close (green candle)
        if i > 0 and current_close <= closes[i-1]:
            continue
            
        # 7. Not extreme: RSI > 15
        if current_rsi <= ENTRY_RULES['rsi_min']:
            continue
            
        # 8. Not overbought: RSI < 60
        if current_rsi >= FILTERS['max_entry_rsi']:
            continue
            
        # Entry found!
        entry_price = current_close
        entry_time = candles_data[i]['ts']
        entry_candle = i
        
        # Exit conditions
        tp_price = entry_price * (1 + EXIT_RULES['tp_pct'] / 100)
        sl_price = entry_price * (1 - EXIT_RULES['sl_pct'] / 100)
        
        exit_price = None
        exit_time = None
        exit_reason = None
        max_hold = EXIT_RULES['max_hold_candles']
        
        for j in range(1, max_hold + 1):
            if i + j >= len(closes):
                break
                
            current_high = candles_data[i + j]['high']
            current_low = candles_data[i + j]['low']
            
            # Check stop loss
            if current_low <= sl_price:
                exit_price = sl_price
                exit_time = candles_data[i + j]['ts']
                exit_reason = 'stop_loss'
                break
                
            # Check take profit
            if current_high >= tp_price:
                exit_price = tp_price
                exit_time = candles_data[i + j]['ts']
                exit_reason = 'take_profit'
                break
                
            # Time exit
            if j == max_hold:
                exit_price = candles_data[i + j]['close']
                exit_time = candles_data[i + j]['ts']
                exit_reason = 'time_exit'
                break
        
        if exit_price is None:
            # No exit found within max hold
            continue
            
        # Calculate PnL
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        
        trades.append({
            'token': token,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
            'trend_strength': trend_strength,
            'distance_pct': distance_pct,
            'rsi_at_entry': current_rsi,
            'candle_index': entry_candle,
        })
        
        # Set cooldown
        cooldown_counter = FILTERS['cooldown_candles']
    
    return trades

def main():
    """Run backtest on all 5 tokens."""
    tokens = ['ARB', 'CFX', 'FIL', 'AVNT', 'SYRUP']
    
    print("=== EMA300 Dip Buyer v2 Backtest ===")
    print(f"Testing {len(tokens)} tokens from candles_1m database")
    print(f"Time range: Last 3 days (from current data)")
    print()
    
    all_trades = []
    token_stats = {}
    
    for token in tokens:
        print(f"Backtesting {token}...")
        
        # Get candles from database
        conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=10)
        try:
            # Get last 3 days of data (4320 minutes)
            cutoff_time = int((datetime.now() - timedelta(days=3)).timestamp())
            
            query = """
                SELECT ts, open, high, low, close, volume
                FROM candles_1m
                WHERE token = ? AND ts > ? AND is_closed = 1
                ORDER BY ts ASC
            """
            
            cursor = conn.execute(query, (token, cutoff_time))
            rows = cursor.fetchall()
            
            if not rows:
                print(f"  No data found for {token}")
                continue
                
            # Convert to list of dicts
            candles_data = []
            for row in rows:
                candles_data.append({
                    'ts': row[0],
                    'open': row[1],
                    'high': row[2],
                    'low': row[3],
                    'close': row[4],
                    'volume': row[5],
                })
            
            print(f"  Loaded {len(candles_data)} candles for {token}")
            
            # Run backtest
            trades = backtest_token(token, candles_data)
            all_trades.extend(trades)
            
            # Calculate stats
            if trades:
                wins = [t for t in trades if t['pnl_pct'] > 0]
                losses = [t for t in trades if t['pnl_pct'] <= 0]
                
                win_rate = len(wins) / len(trades) * 100
                avg_pnl = sum(t['pnl_pct'] for t in trades) / len(trades)
                total_pnl = sum(t['pnl_pct'] for t in trades)
                
                token_stats[token] = {
                    'trades': len(trades),
                    'wins': len(wins),
                    'losses': len(losses),
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_pnl': total_pnl,
                }
                
                print(f"  {token}: {len(trades)} trades, {win_rate:.1f}% WR, {avg_pnl:.2f}% avg PnL")
            else:
                print(f"  {token}: No trades found")
                
        except Exception as e:
            print(f"Error processing {token}: {e}")
        finally:
            conn.close()
    
    # Summary
    print("\n=== SUMMARY ===")
    if all_trades:
        total_trades = len(all_trades)
        wins = [t for t in all_trades if t['pnl_pct'] > 0]
        losses = [t for t in all_trades if t['pnl_pct'] <= 0]
        
        win_rate = len(wins) / total_trades * 100
        avg_pnl = sum(t['pnl_pct'] for t in all_trades) / total_trades
        total_pnl = sum(t['pnl_pct'] for t in all_trades)
        
        print(f"Total trades: {total_trades}")
        print(f"Wins: {len(wins)}, Losses: {len(losses)}")
        print(f"Win rate: {win_rate:.1f}%")
        print(f"Avg PnL per trade: {avg_pnl:.2f}%")
        print(f"Total PnL: {total_pnl:.2f}%")
        
        print("\n=== TOKEN BREAKDOWN ===")
        for token, stats in token_stats.items():
            print(f"{token}: {stats['trades']} trades, {stats['win_rate']:.1f}% WR, {stats['avg_pnl']:.2f}% avg PnL")
            
        # Verify claims
        print("\n=== CLAIM VERIFICATION ===")
        
        # Claim 1: ARB has 67% WR, +0.66% avg PnL
        if 'ARB' in token_stats:
            arb_stats = token_stats['ARB']
            arb_claim_wr = 67
            arb_claim_pnl = 0.66
            
            print(f"ARB Claim: {arb_claim_wr}% WR, +{arb_claim_pnl}% avg PnL")
            print(f"ARB Actual: {arb_stats['win_rate']:.1f}% WR, {arb_stats['avg_pnl']:.2f}% avg PnL")
            
            if abs(arb_stats['win_rate'] - arb_claim_wr) < 5 and abs(arb_stats['avg_pnl'] - arb_claim_pnl) < 0.2:
                print("VERDICT: AGREE (within reasonable margin)")
            else:
                print("VERDICT: DISAGREE")
        else:
            print("ARB: No data available")
            
        # Claim 2: CFX has 61% WR, +0.18% avg PnL
        if 'CFX' in token_stats:
            cfx_stats = token_stats['CFX']
            cfx_claim_wr = 61
            cfx_claim_pnl = 0.18
            
            print(f"\nCFX Claim: {cfx_claim_wr}% WR, +{cfx_claim_pnl}% avg PnL")
            print(f"CFX Actual: {cfx_stats['win_rate']:.1f}% WR, {cfx_stats['avg_pnl']:.2f}% avg PnL")
            
            if abs(cfx_stats['win_rate'] - cfx_claim_wr) < 5 and abs(cfx_stats['avg_pnl'] - cfx_claim_pnl) < 0.1:
                print("VERDICT: AGREE (within reasonable margin)")
            else:
                print("VERDICT: DISAGREE")
        else:
            print("CFX: No data available")
            
        # Claim 3: 584 total dip opportunities across 5 tokens in 3 days
        print(f"\nTotal opportunities claimed: 584")
        print(f"Total opportunities actual: {total_trades}")
        
        if abs(total_trades - 584) < 50:
            print("VERDICT: AGREE (within reasonable margin)")
        else:
            print("VERDICT: DISAGREE")
            
        # Claim 4: 57% WR overall
        overall_claim_wr = 57
        print(f"\nOverall WR claimed: {overall_claim_wr}%")
        print(f"Overall WR actual: {win_rate:.1f}%")
        
        if abs(win_rate - overall_claim_wr) < 5:
            print("VERDICT: AGREE (within reasonable margin)")
        else:
            print("VERDICT: DISAGREE")
            
    else:
        print("No trades found across all tokens")
        
    # Save detailed results
    import json
    results = {
        'backtest_time': datetime.now().isoformat(),
        'tokens_tested': tokens,
        'entry_rules': ENTRY_RULES,
        'exit_rules': EXIT_RULES,
        'filters': FILTERS,
        'token_stats': token_stats,
        'total_trades': len(all_trades),
        'trades': all_trades[:100],  # Save first 100 trades for inspection
    }
    
    output_file = '/root/.hermes/data/ema300_dip_buyer_backtest_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
