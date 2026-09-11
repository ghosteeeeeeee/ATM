#!/usr/bin/env python3
"""Analyze BTC momentum thresholds for pump-chain+ and pump-chain- signals."""

import json
import sqlite3
import os
from datetime import datetime, timedelta
import sys

# Load trades.json
trades_file = "/var/www/hermes/data/trades.json"
with open(trades_file, 'r') as f:
    data = json.load(f)

# Get last 50 closed trades
closed = data.get('closed', [])[:50]

print(f"Total closed trades in file: {len(data.get('closed', []))}")
print(f"Analyzing last 50 trades")
print("="*80)

# Filter for pump-chain+ and pump-chain- signals
pump_chain_plus = [t for t in closed if t.get('signal') == 'pump-chain+']
pump_chain_minus = [t for t in closed if t.get('signal') == 'pump-chain-']

print(f"\nPump-Chain+ trades: {len(pump_chain_plus)}")
print(f"Pump-Chain- trades: {len(pump_chain_minus)}")

# Load BTC candles from SQLite
candles_db = "/root/.hermes/data/candles.db"
conn = sqlite3.connect(candles_db)
cursor = conn.cursor()

# Check candles_1m structure
cursor.execute("PRAGMA table_info(candles_1m)")
columns = cursor.fetchall()
print(f"\ncandles_1m columns: {columns}")

# Check for BTC data
cursor.execute("SELECT DISTINCT symbol FROM candles_1m LIMIT 10")
symbols = cursor.fetchall()
print(f"Symbols in candles_1m: {symbols}")

# Get BTC 1m candles
def get_btc_price_at(trade_open_time):
    """Get BTC price at trade open time."""
    try:
        # Convert trade open time to timestamp
        open_dt = datetime.strptime(trade_open_time, "%Y-%m-%d %H:%M:%S.%f")
        open_ts = int(open_dt.timestamp())
        
        # Try to get BTC candle
        cursor.execute("""
            SELECT open, high, low, close, timestamp
            FROM candles_1m
            WHERE symbol='BTC' AND timestamp >= ? AND timestamp < ?
            ORDER BY timestamp ASC LIMIT 1
        """, (open_ts - 60, open_ts + 60))
        
        result = cursor.fetchone()
        if result:
            return result[0]  # Return open price
        return None
    except Exception as e:
        print(f"Error getting BTC price: {e}")
        return None

# Analyze pump-chain+ trades
print("\n" + "="*80)
print("PUMP-CHAIN+ ANALYSIS (LONG signals)")
print("="*80)

btc_prices_plus = []
wins_plus = 0
losses_plus = 0

for trade in pump_chain_plus:
    open_time = trade.get('opened')
    pnl = trade.get('pnl_usdt', 0)
    coin = trade.get('coin')
    
    btc_price = get_btc_price_at(open_time)
    if btc_price:
        btc_prices_plus.append((btc_price, pnl, coin, open_time))
        if pnl > 0:
            wins_plus += 1
        else:
            losses_plus += 1
    else:
        print(f"  Could not get BTC price for {coin} at {open_time}")

if btc_prices_plus:
    # Find the proposed threshold: BTC > +0.3%
    # We need to calculate BTC momentum at trade open
    # Use the first trade as baseline and calculate relative change
    
    # Sort by time
    btc_prices_plus.sort(key=lambda x: x[3])
    
    # Calculate average BTC price across all trades
    avg_btc = sum(p[0] for p in btc_prices_plus) / len(btc_prices_plus)
    
    # Find trades where BTC was above average by more than threshold
    threshold_pct = 0.3  # 0.3%
    
    above_threshold = []
    below_threshold = []
    
    for price, pnl, coin, open_time in btc_prices_plus:
        momentum = (price - avg_btc) / avg_btc * 100
        if momentum > threshold_pct:
            above_threshold.append((price, pnl, coin, momentum, open_time))
        else:
            below_threshold.append((price, pnl, coin, momentum, open_time))
    
    print(f"\nTotal pump-chain+ trades analyzed: {len(btc_prices_plus)}")
    print(f"Average BTC price at entry: ${avg_btc:,.2f}")
    print(f"\nTrades where BTC > +{threshold_pct}%: {len(above_threshold)}")
    
    if above_threshold:
        wins_above = sum(1 for _, pnl, _, _, _ in above_threshold if pnl > 0)
        losses_above = sum(1 for _, pnl, _, _, _ in above_threshold if pnl <= 0)
        win_rate_above = wins_above / len(above_threshold) * 100
        
        print(f"  Wins: {wins_above}")
        print(f"  Losses: {losses_above}")
        print(f"  Win Rate: {win_rate_above:.1f}%")
        print(f"  Claimed: 'loses 70%' (30% win rate)")
        
        # Show individual trades
        print(f"\n  Individual trades:")
        for price, pnl, coin, mom, open_time in above_threshold:
            print(f"    {coin}: BTC ${price:,.2f} (+{mom:.2f}%), PnL: ${pnl:+.2f}, Time: {open_time}")
    
    print(f"\nTrades where BTC <= +{threshold_pct}%: {len(below_threshold)}")
    if below_threshold:
        wins_below = sum(1 for _, pnl, _, _, _ in below_threshold if pnl > 0)
        losses_below = sum(1 for _, pnl, _, _, _ in below_threshold if pnl <= 0)
        win_rate_below = wins_below / len(below_threshold) * 100
        
        print(f"  Wins: {wins_below}")
        print(f"  Losses: {losses_below}")
        print(f"  Win Rate: {win_rate_below:.1f}%")

# Analyze pump-chain- trades
print("\n" + "="*80)
print("PUMP-CHAIN- ANALYSIS (SHORT signals)")
print("="*80)

btc_prices_minus = []
wins_minus = 0
losses_minus = 0

for trade in pump_chain_minus:
    open_time = trade.get('opened')
    pnl = trade.get('pnl_usdt', 0)
    coin = trade.get('coin')
    
    btc_price = get_btc_price_at(open_time)
    if btc_price:
        btc_prices_minus.append((btc_price, pnl, coin, open_time))
        if pnl > 0:
            wins_minus += 1
        else:
            losses_minus += 1
    else:
        print(f"  Could not get BTC price for {coin} at {open_time}")

if btc_prices_minus:
    # Sort by time
    btc_prices_minus.sort(key=lambda x: x[3])
    
    # Calculate average BTC price across all trades
    avg_btc_minus = sum(p[0] for p in btc_prices_minus) / len(btc_prices_minus)
    
    # Find the proposed threshold: BTC < -0.3%
    threshold_pct = -0.3  # -0.3%
    
    below_threshold_minus = []
    above_threshold_minus = []
    
    for price, pnl, coin, open_time in btc_prices_minus:
        momentum = (price - avg_btc_minus) / avg_btc_minus * 100
        if momentum < threshold_pct:
            below_threshold_minus.append((price, pnl, coin, momentum, open_time))
        else:
            above_threshold_minus.append((price, pnl, coin, momentum, open_time))
    
    print(f"\nTotal pump-chain- trades analyzed: {len(btc_prices_minus)}")
    print(f"Average BTC price at entry: ${avg_btc_minus:,.2f}")
    print(f"\nTrades where BTC < -{abs(threshold_pct)}%: {len(below_threshold_minus)}")
    
    if below_threshold_minus:
        wins_below_minus = sum(1 for _, pnl, _, _, _ in below_threshold_minus if pnl > 0)
        losses_below_minus = sum(1 for _, pnl, _, _, _ in below_threshold_minus if pnl <= 0)
        win_rate_below_minus = wins_below_minus / len(below_threshold_minus) * 100
        
        print(f"  Wins: {wins_below_minus}")
        print(f"  Losses: {losses_below_minus}")
        print(f"  Win Rate: {win_rate_below_minus:.1f}%")
        print(f"  Claimed: 'loses 60%' (40% win rate)")
        
        # Show individual trades
        print(f"\n  Individual trades:")
        for price, pnl, coin, mom, open_time in below_threshold_minus:
            print(f"    {coin}: BTC ${price:,.2f} ({mom:.2f}%), PnL: ${pnl:+.2f}, Time: {open_time}")
    
    print(f"\nTrades where BTC >= -{abs(threshold_pct)}%: {len(above_threshold_minus)}")
    if above_threshold_minus:
        wins_above_minus = sum(1 for _, pnl, _, _, _ in above_threshold_minus if pnl > 0)
        losses_above_minus = sum(1 for _, pnl, _, _, _ in above_threshold_minus if pnl <= 0)
        win_rate_above_minus = wins_above_minus / len(above_threshold_minus) * 100
        
        print(f"  Wins: {wins_above_minus}")
        print(f"  Losses: {losses_above_minus}")
        print(f"  Win Rate: {win_rate_above_minus:.1f}%")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nClaims to verify:")
print("1. pump-chain+ loses 70% when BTC > +0.3% → block these")
print("2. pump-chain- loses 60% when BTC < -0.3% → block these")
print("3. Expected: block 12/50 trades, 8 are losers, net +$28.90 saved")

# Calculate what would be blocked
if btc_prices_plus and above_threshold:
    blocked_plus = len(above_threshold)
    losers_blocked_plus = losses_above
    saved_plus = sum(abs(pnl) for _, pnl, _, _, _ in above_threshold if pnl <= 0)
    print(f"\nPump-Chain+ blocked: {blocked_plus} trades ({losers_blocked_plus} losers)")
    print(f"  Money saved from losers: ${saved_plus:.2f}")

if btc_prices_minus and below_threshold_minus:
    blocked_minus = len(below_threshold_minus)
    losers_blocked_minus = losses_below_minus
    saved_minus = sum(abs(pnl) for _, pnl, _, _, _ in below_threshold_minus if pnl <= 0)
    print(f"\nPump-Chain- blocked: {blocked_minus} trades ({losers_blocked_minus} losers)")
    print(f"  Money saved from losers: ${saved_minus:.2f}")

if btc_prices_plus and btc_prices_minus:
    total_blocked = len(above_threshold) + len(below_threshold_minus)
    total_losers_blocked = losers_blocked_plus + losers_blocked_minus
    total_saved = saved_plus + saved_minus
    print(f"\nTotal trades blocked: {total_blocked}/50")
    print(f"Total losers blocked: {total_losers_blocked}")
    print(f"Total money saved: ${total_saved:.2f}")
    print(f"\nClaim: block 12/50 trades, 8 are losers, net +$28.90 saved")
    print(f"Actual: block {total_blocked}/50 trades, {total_losers_blocked} losers, ${total_saved:.2f} saved")

conn.close()
