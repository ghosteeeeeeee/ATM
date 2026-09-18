#!/usr/bin/env python3
"""
Independent verification: Compute RSI for all open-skies trades and test the RSI 30-60 filter.
"""

import sys
import os
import sqlite3
import numpy as np
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from paths import HERMES_DATA, CANDLES_DB

def get_open_skies_trades():
    """Get all open-skies trades from signals_hermes_runtime.db signal_outcomes"""
    runtime_db = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
    
    conn = sqlite3.connect(runtime_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get all open_skies signal outcomes
    cur.execute("""
        SELECT *
        FROM signal_outcomes
        WHERE signal_type LIKE '%open_skies%'
        ORDER BY created_at DESC
    """)
    
    results = cur.fetchall()
    conn.close()
    
    return results

def compute_rsi_1h(closes, period=14):
    """Compute RSI from 1h candles using same method as open_skies.py."""
    if len(closes) < period + 1:
        return None
    
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_1h_candles(token, limit=100):
    """Get 1h candles from candles.db for the given token."""
    conn = sqlite3.connect(CANDLES_DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_1h
        WHERE token = ? AND is_closed = 1
        ORDER BY ts DESC
        LIMIT ?
    """, (token.upper(), limit))
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return []
    
    return list(reversed(rows))

def check_trend_up(closes):
    """Check if trend is UP based on SMA analysis."""
    if len(closes) < 50:
        return False
    
    sma_fast = sum(closes[-20:]) / 20
    sma_slow = sum(closes[-50:]) / 50
    price = closes[-1]
    
    # Price above both SMAs
    if price <= sma_fast or price <= sma_slow:
        return False
    
    # Recent 5 bars should be up
    if len(closes) >= 5:
        recent_5 = closes[-5:]
        if recent_5[-1] < recent_5[0]:
            return False
    
    return True

def main():
    print("=" * 80)
    print("INDEPENDENT VERIFICATION: Open-Skies RSI Filter Analysis")
    print("=" * 80)
    
    trades = get_open_skies_trades()
    
    if not trades:
        print("No trades found!")
        return
    
    print(f"\nAnalyzing {len(trades)} open-skies trades...\n")
    
    winners = []
    losers = []
    skipped = 0
    
    for trade in trades:
        token = trade['token']
        pnl = trade['pnl_pct']
        is_win = trade['is_win']
        
        # Get 1h candles
        candles = get_1h_candles(token, 100)
        
        if not candles or len(candles) < 15:
            skipped += 1
            print(f"⚠️  {token}: Insufficient candle data (only {len(candles)} candles)")
            continue
        
        closes = [c[4] for c in candles]
        
        # Compute RSI
        rsi = compute_rsi_1h(closes)
        
        if rsi is None:
            skipped += 1
            print(f"⚠️  {token}: Could not compute RSI")
            continue
        
        # Check trend
        trend_up = check_trend_up(closes)
        
        # RSI in 30-60 range
        rsi_30_60 = 30 <= rsi <= 60
        
        trade_info = {
            'token': token,
            'pnl': pnl,
            'rsi': rsi,
            'trend_up': trend_up,
            'rsi_30_60': rsi_30_60,
            'created_at': trade['created_at'],
            'regime': trade['regime']
        }
        
        if is_win:
            winners.append(trade_info)
        else:
            losers.append(trade_info)
    
    # Sort by PnL
    winners.sort(key=lambda x: x['pnl'], reverse=True)
    losers.sort(key=lambda x: x['pnl'])
    
    print(f"\nSkipped: {skipped} trades (insufficient data)")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {len(winners)} winners, {len(losers)} losers")
    print("=" * 80)
    
    print("\n📊 ALL WINNERS (sorted by PnL):")
    print("-" * 80)
    print(f"{'Token':<10} {'PnL%':>8} {'RSI':>8} {'Trend UP':>10} {'RSI 30-60':>10} {'Regime':>10}")
    print("-" * 80)
    
    winners_rsi_gt_60 = 0
    winners_rsi_30_60 = 0
    
    for w in winners:
        rsi_marker = "✓" if w['rsi_30_60'] else ""
        trend_marker = "✓" if w['trend_up'] else ""
        regime = w['regime'] if w['regime'] else 'N/A'
        print(f"{w['token']:<10} {w['pnl']:>+8.2f} {w['rsi']:>8.1f} {trend_marker:>10} {rsi_marker:>10} {regime:>10}")
        
        if w['rsi'] > 60:
            winners_rsi_gt_60 += 1
        if w['rsi_30_60']:
            winners_rsi_30_60 += 1
    
    print("-" * 80)
    print(f"Winners with RSI > 60: {winners_rsi_gt_60} of {len(winners)}")
    print(f"Winners with RSI 30-60: {winners_rsi_30_60} of {len(winners)}")
    
    print("\n📊 ALL LOSERS (sorted by PnL):")
    print("-" * 80)
    print(f"{'Token':<10} {'PnL%':>8} {'RSI':>8} {'Trend UP':>10} {'RSI 30-60':>10} {'Regime':>10}")
    print("-" * 80)
    
    losers_rsi_gt_60 = 0
    losers_rsi_30_60 = 0
    
    for l in losers:
        rsi_marker = "✓" if l['rsi_30_60'] else ""
        trend_marker = "✓" if l['trend_up'] else ""
        regime = l['regime'] if l['regime'] else 'N/A'
        print(f"{l['token']:<10} {l['pnl']:>+8.2f} {l['rsi']:>8.1f} {trend_marker:>10} {rsi_marker:>10} {regime:>10}")
        
        if l['rsi'] > 60:
            losers_rsi_gt_60 += 1
        if l['rsi_30_60']:
            losers_rsi_30_60 += 1
    
    print("-" * 80)
    print(f"Losers with RSI > 60: {losers_rsi_gt_60} of {len(losers)}")
    print(f"Losers with RSI 30-60: {losers_rsi_30_60} of {len(losers)}")
    
    # Test the proposed filter: trend UP AND RSI 30-60
    print("\n" + "=" * 80)
    print("TESTING PROPOSED FILTER: trend UP AND RSI 30-60")
    print("=" * 80)
    
    all_trades = winners + losers
    passed = [t for t in all_trades if t['trend_up'] and t['rsi_30_60']]
    
    passed_winners = [t for t in passed if t['pnl'] > 0]
    passed_losers = [t for t in passed if t['pnl'] <= 0]
    
    passed_pnl = sum(t['pnl'] for t in passed)
    
    print(f"\nTrades passing filter: {len(passed)} of {len(all_trades)}")
    print(f"Winners passing: {len(passed_winners)}")
    print(f"Losers passing: {len(passed_losers)}")
    
    if passed_winners:
        print(f"\nWinners that PASS the filter:")
        for w in passed_winners:
            print(f"  {w['token']}: {w['pnl']:+.2f}% (RSI={w['rsi']:.1f})")
    
    if passed_losers:
        print(f"\nLosers that PASS the filter:")
        for l in passed_losers:
            print(f"  {l['token']}: {l['pnl']:.2f}% (RSI={l['rsi']:.1f})")
    
    if len(passed) > 0:
        wr = len(passed_winners) / len(passed) * 100
        print(f"\nFilter Win Rate: {wr:.1f}%")
        print(f"Filter Total PnL: {passed_pnl:+.2f}%")
    else:
        print("\nNo trades pass this filter!")
    
    # Test current filter: RSI <= 75
    print("\n" + "=" * 80)
    print("TESTING CURRENT FILTER: RSI <= 75")
    print("=" * 80)
    
    passed_current = [t for t in all_trades if t['rsi'] <= 75]
    passed_winners_current = [t for t in passed_current if t['pnl'] > 0]
    passed_losers_current = [t for t in passed_current if t['pnl'] <= 0]
    passed_pnl_current = sum(t['pnl'] for t in passed_current)
    
    print(f"\nTrades passing filter: {len(passed_current)} of {len(all_trades)}")
    print(f"Winners passing: {len(passed_winners_current)}")
    print(f"Losers passing: {len(passed_losers_current)}")
    
    if len(passed_current) > 0:
        wr_current = len(passed_winners_current) / len(passed_current) * 100
        print(f"\nFilter Win Rate: {wr_current:.1f}%")
        print(f"Filter Total PnL: {passed_pnl_current:+.2f}%")
    
    # Test current + trend UP
    print("\n" + "=" * 80)
    print("TESTING: Current RSI<=75 + trend UP")
    print("=" * 80)
    
    passed_current_up = [t for t in all_trades if t['rsi'] <= 75 and t['trend_up']]
    passed_winners_cu = [t for t in passed_current_up if t['pnl'] > 0]
    passed_losers_cu = [t for t in passed_current_up if t['pnl'] <= 0]
    passed_pnl_cu = sum(t['pnl'] for t in passed_current_up)
    
    print(f"\nTrades passing: {len(passed_current_up)} of {len(all_trades)}")
    print(f"Winners: {len(passed_winners_cu)}")
    print(f"Losers: {len(passed_losers_cu)}")
    
    if len(passed_current_up) > 0:
        wr_cu = len(passed_winners_cu) / len(passed_current_up) * 100
        print(f"Win Rate: {wr_cu:.1f}%")
        print(f"Total PnL: {passed_pnl_cu:+.2f}%")
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\n{'Filter':<35} {'Trades':>8} {'Winners':>10} {'Losers':>10} {'WinRate':>10} {'TotalPnL':>12}")
    print("-" * 85)
    
    if len(passed) > 0:
        print(f"{'Proposed (trend UP + RSI 30-60)':<35} {len(passed):>8} {len(passed_winners):>10} {len(passed_losers):>10} {wr:>9.1f}% {passed_pnl:>+11.2f}%")
    else:
        print(f"{'Proposed (trend UP + RSI 30-60)':<35} {len(passed):>8} {'0':>10} {'0':>10} {'N/A':>10} {'0':>12}")
    
    if len(passed_current) > 0:
        print(f"{'Current (RSI<=75)':<35} {len(passed_current):>8} {len(passed_winners_current):>10} {len(passed_losers_current):>10} {wr_current:>9.1f}% {passed_pnl_current:>+11.2f}%")
    
    if len(passed_current_up) > 0:
        print(f"{'Current + trend UP':<35} {len(passed_current_up):>8} {len(passed_winners_cu):>10} {len(passed_losers_cu):>10} {wr_cu:>9.1f}% {passed_pnl_cu:>+11.2f}%")
    
    print(f"{'No filter (all trades)':<35} {len(all_trades):>8} {len(winners):>10} {len(losers):>10} {len(winners)/len(all_trades)*100:>9.1f}% {sum(t['pnl'] for t in all_trades):>+11.2f}%")
    
    # RSI distribution of winners
    print("\n" + "=" * 80)
    print("RSI DISTRIBUTION OF WINNERS")
    print("=" * 80)
    
    rsi_ranges = [
        (0, 30, "Oversold (0-30)"),
        (30, 60, "Neutral (30-60)"),
        (60, 70, "Mild momentum (60-70)"),
        (70, 80, "Strong momentum (70-80)"),
        (80, 100, "Extreme (80-100)")
    ]
    
    for low, high, label in rsi_ranges:
        count = sum(1 for w in winners if low <= w['rsi'] < high)
        if count > 0:
            total_pnl = sum(w['pnl'] for w in winners if low <= w['rsi'] < high)
            print(f"{label}: {count} winners, total PnL = {total_pnl:+.2f}%")
    
    # Data quality note
    print("\n" + "=" * 80)
    print("DATA QUALITY NOTE")
    print("=" * 80)
    print("RSI computed from 1h candles (most recent 100 available).")
    print("This may differ from the 5m RSI at actual signal detection time.")
    print("Trend check uses SMA20/SMA50 from 1h candles (same logic as signal).")

if __name__ == "__main__":
    main()
