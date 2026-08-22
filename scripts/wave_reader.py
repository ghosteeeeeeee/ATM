#!/usr/bin/env python3
"""
Wave Reader — Deep Pattern Analysis
=====================================
Reads the market like a seasoned surfer reads the ocean:
- Which waves come first? (leading indicators)
- What happens after a crash? (aftershock patterns)
- Which signals predict the next move? (predictive power)
- What's the sequence of events in a pump/crash?
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

DB_PATH = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def analyze_crash_sequences(conn):
    """
    CRASH SEQUENCES — What happens before/during/after a big drop?
    Like reading the warning signs before a wipeout.
    """
    print("\n" + "=" * 70)
    print("🔴 CRASH SEQUENCE ANALYSIS — Reading the Wipeouts")
    print("=" * 70)
    
    # Find tokens that had big losses (>3% in a single trade)
    crashes = conn.execute("""
        SELECT token, direction, signal_type, pnl_pct, confidence, created_at
        FROM signal_outcomes
        WHERE pnl_pct < -3.0
        ORDER BY created_at
    """).fetchall()
    
    if not crashes:
        print("  No significant crashes found.")
        return
    
    print(f"\n  Found {len(crashes)} significant crashes (PnL < -3%)")
    
    # For each crash, look at what signals preceded it
    crash_leaders = defaultdict(list)
    
    for crash in crashes:
        # What signals fired for this token in the 6 hours before the crash?
        crash_time = crash['created_at']
        leaders = conn.execute("""
            SELECT signal_type, direction, confidence, created_at
            FROM signals
            WHERE token = ? 
            AND created_at < ?
            AND created_at >= datetime(?, '-6 hours')
            ORDER BY created_at DESC
        """, (crash['token'], crash_time, crash_time)).fetchall()
        
        # What was the last signal before the crash?
        if leaders:
            last_signal = leaders[0]
            crash_leaders[last_signal['signal_type']].append({
                'token': crash['token'],
                'crash_pnl': crash['pnl_pct'],
                'time_before_crash': last_signal['created_at'],
            })
    
    print(f"\n  📊 LEADING SIGNALS BEFORE CRASHES:")
    print(f"  {'Signal Type':<35} {'Count':>6} {'Avg Crash PnL':>15}")
    print(f"  {'─' * 35} {'─' * 6} {'─' * 15}")
    
    for signal_type, events in sorted(crash_leaders.items(), key=lambda x: -len(x[1])):
        if len(events) >= 3:
            avg_pnl = sum(e['crash_pnl'] for e in events) / len(events)
            print(f"  {signal_type:<35} {len(events):>6} {avg_pnl:>14.2f}%")

def analyze_pump_sequences(conn):
    """
    PUMP SEQUENCES — What happens before/during/after a big pump?
    Like reading the signs before a clean barrel.
    """
    print("\n" + "=" * 70)
    print("🟢 PUMP SEQUENCE ANALYSIS — Reading the Barrels")
    print("=" * 70)
    
    # Find tokens that had big wins (>3% in a single trade)
    pumps = conn.execute("""
        SELECT token, direction, signal_type, pnl_pct, confidence, created_at
        FROM signal_outcomes
        WHERE pnl_pct > 3.0
        ORDER BY created_at
    """).fetchall()
    
    if not pumps:
        print("  No significant pumps found.")
        return
    
    print(f"\n  Found {len(pumps)} significant pumps (PnL > 3%)")
    
    # For each pump, look at what signals preceded it
    pump_leaders = defaultdict(list)
    
    for pump in pumps:
        # What signals fired for this token in the 6 hours before the pump?
        pump_time = pump['created_at']
        leaders = conn.execute("""
            SELECT signal_type, direction, confidence, created_at
            FROM signals
            WHERE token = ? 
            AND created_at < ?
            AND created_at >= datetime(?, '-6 hours')
            ORDER BY created_at DESC
        """, (pump['token'], pump_time, pump_time)).fetchall()
        
        # What was the last signal before the pump?
        if leaders:
            last_signal = leaders[0]
            pump_leaders[last_signal['signal_type']].append({
                'token': pump['token'],
                'pump_pnl': pump['pnl_pct'],
                'time_before_pump': last_signal['created_at'],
            })
    
    print(f"\n  📊 LEADING SIGNALS BEFORE PUMPS:")
    print(f"  {'Signal Type':<35} {'Count':>6} {'Avg Pump PnL':>15}")
    print(f"  {'─' * 35} {'─' * 6} {'─' * 15}")
    
    for signal_type, events in sorted(pump_leaders.items(), key=lambda x: -len(x[1])):
        if len(events) >= 3:
            avg_pnl = sum(e['pump_pnl'] for e in events) / len(events)
            print(f"  {signal_type:<35} {len(events):>6} {avg_pnl:>14.2f}%")

def analyze_signal_followthrough(conn):
    """
    SIGNAL FOLLOW-THROUGH — After a signal fires, what actually happens?
    Like watching if a wave actually breaks or closes out.
    """
    print("\n" + "=" * 70)
    print("📈 SIGNAL FOLLOW-THROUGH — Did the Wave Break?")
    print("=" * 70)
    
    # For each signal type with enough outcomes, calculate follow-through
    followthrough = conn.execute("""
        SELECT 
            signal_type,
            COUNT(*) as total,
            SUM(is_win) as wins,
            ROUND(100.0 * SUM(is_win) / COUNT(*), 1) as winrate,
            ROUND(AVG(pnl_pct), 2) as avg_pnl,
            ROUND(MAX(pnl_pct), 2) as best_trade,
            ROUND(MIN(pnl_pct), 2) as worst_trade,
            ROUND(AVG(confidence), 1) as avg_conf
        FROM signal_outcomes
        GROUP BY signal_type
        HAVING total >= 10
        ORDER BY avg_pnl DESC
    """).fetchall()
    
    print(f"\n  {'Signal Type':<35} {'Trades':>7} {'Win%':>6} {'Avg PnL':>8} {'Best':>8} {'Worst':>8} {'Conf':>6}")
    print(f"  {'─' * 35} {'─' * 7} {'─' * 6} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 6}")
    
    for row in followthrough:
        marker = "🟢" if row['avg_pnl'] > 0 else "🔴"
        print(f"  {marker} {row['signal_type']:<33} {row['total']:>7} {row['winrate']:>5}% "
              f"{row['avg_pnl']:>7.2f}% {row['best_trade']:>7.2f}% {row['worst_trade']:>7.2f}% {row['avg_conf']:>5}")

def analyze_token_regimes(conn):
    """
    TOKEN REGIMES — Which tokens are in which state?
    Like reading the ocean floor: reef, sandbar, or deep water.
    """
    print("\n" + "=" * 70)
    print("🗺️ TOKEN REGIME MAP — The Ocean Floor")
    print("=" * 70)
    
    # Token performance by regime
    token_regimes = conn.execute("""
        SELECT 
            token,
            COUNT(*) as trades,
            SUM(is_win) as wins,
            ROUND(100.0 * SUM(is_win) / COUNT(*), 1) as winrate,
            ROUND(SUM(pnl_pct), 2) as total_pnl,
            ROUND(AVG(pnl_pct), 2) as avg_pnl
        FROM signal_outcomes
        GROUP BY token
        HAVING trades >= 5
        ORDER BY total_pnl DESC
    """).fetchall()
    
    # Classify tokens
    reef = []  # Consistent winners (like a reef that consistently produces good waves)
    sandbar = []  # Inconsistent (shifting like sand)
    deep = []  # Consistent losers (like deep water - hard to catch waves)
    
    for t in token_regimes:
        if t['winrate'] > 55 and t['avg_pnl'] > 0.1:
            reef.append(t)
        elif t['winrate'] < 35 or t['avg_pnl'] < -0.5:
            deep.append(t)
        else:
            sandbar.append(t)
    
    print(f"\n  🪸 REEF (Consistent Winners): {len(reef)} tokens")
    for t in reef[:10]:
        print(f"     {t['token']:>10}: {t['trades']} trades, {t['winrate']}% win, PnL: {t['total_pnl']:.2f}%")
    
    print(f"\n  🏖️ SANDBAR (Inconsistent): {len(sandbar)} tokens")
    for t in sandbar[:10]:
        print(f"     {t['token']:>10}: {t['trades']} trades, {t['winrate']}% win, PnL: {t['total_pnl']:.2f}%")
    
    print(f"\n  🌊 DEEP WATER (Consistent Losers): {len(deep)} tokens")
    for t in deep[:10]:
        print(f"     {t['token']:>10}: {t['trades']} trades, {t['winrate']}% win, PnL: {t['total_pnl']:.2f}%")

def analyze_time_patterns(conn):
    """
    TIME PATTERNS — When do crashes and pumps happen?
    Like reading tide tables: some hours are better than others.
    """
    print("\n" + "=" * 70)
    print("⏰ TIME PATTERNS — When Do the Waves Break?")
    print("=" * 70)
    
    # Hourly performance
    hourly = conn.execute("""
        SELECT 
            CAST(strftime('%H', created_at) AS INTEGER) as hour,
            COUNT(*) as trades,
            SUM(is_win) as wins,
            ROUND(100.0 * SUM(is_win) / COUNT(*), 1) as winrate,
            ROUND(SUM(pnl_pct), 2) as total_pnl,
            ROUND(AVG(pnl_pct), 2) as avg_pnl
        FROM signal_outcomes
        GROUP BY hour
        ORDER BY hour
    """).fetchall()
    
    print(f"\n  {'Hour':>5} {'Trades':>7} {'Win%':>6} {'Total PnL':>10} {'Avg PnL':>8} {'Rating':>10}")
    print(f"  {'─' * 5} {'─' * 7} {'─' * 6} {'─' * 10} {'─' * 8} {'─' * 10}")
    
    for row in hourly:
        if row['avg_pnl'] > 0.2:
            rating = "🟢 STRONG"
        elif row['avg_pnl'] > 0:
            rating = "🟡 OK"
        elif row['avg_pnl'] > -0.2:
            rating = "🟠 WEAK"
        else:
            rating = "🔴 BAD"
        
        print(f"  {row['hour']:>5} {row['trades']:>7} {row['winrate']:>5}% {row['total_pnl']:>9.2f}% {row['avg_pnl']:>7.2f}% {rating}")
    
    # Day of week patterns
    daily = conn.execute("""
        SELECT 
            CASE CAST(strftime('%w', created_at) AS INTEGER)
                WHEN 0 THEN 'Sun'
                WHEN 1 THEN 'Mon'
                WHEN 2 THEN 'Tue'
                WHEN 3 THEN 'Wed'
                WHEN 4 THEN 'Thu'
                WHEN 5 THEN 'Fri'
                WHEN 6 THEN 'Sat'
            END as day_name,
            COUNT(*) as trades,
            SUM(is_win) as wins,
            ROUND(100.0 * SUM(is_win) / COUNT(*), 1) as winrate,
            ROUND(SUM(pnl_pct), 2) as total_pnl
        FROM signal_outcomes
        GROUP BY strftime('%w', created_at)
        ORDER BY strftime('%w', created_at)
    """).fetchall()
    
    print(f"\n  📅 DAY OF WEEK PERFORMANCE:")
    for row in daily:
        marker = "🟢" if row['total_pnl'] > 0 else "🔴"
        print(f"  {marker} {row['day_name']}: {row['trades']} trades, {row['winrate']}% win, PnL: {row['total_pnl']:.2f}%")

def analyze_signal_type_performance(conn):
    """
    SIGNAL TYPE DEEP DIVE — Which signal types are the surfers?
    """
    print("\n" + "=" * 70)
    print("🏄 SIGNAL TYPE DEEP DIVE — Who Rides Best?")
    print("=" * 70)
    
    # Simplified signal type categories
    categories = {
        'Momentum': ['momentum', 'fast_momentum', 'accel_300', 'inverse_accel_300', 'phase_accel'],
        'Trend': ['ma_cross', 'ma_100_cross', 'ema20_50', 'ema9_sma20', 'squeeze_cross'],
        'Z-Score': ['mtp_zscore', 'zscore_pump', 'zscore_rising', 'hzscore'],
        'Bollinger': ['bollinger_squeeze', 'bb_bounce'],
        'Copy Trader': ['hl_copy', 'coin_tracker_hot'],
        'Pattern': ['wyckoff', 'engulfing', 'tl_break', 'range_breakout', 'range_finder'],
        'Exhaustion': ['exhaustion', 'return_exhaustion', 'spike_exhaustion'],
        'Volume': ['volume_hl'],
        'Wave': ['wave_catcher'],
    }
    
    # Get performance by base signal type
    signal_perf = conn.execute("""
        SELECT 
            signal_type,
            COUNT(*) as trades,
            SUM(is_win) as wins,
            ROUND(100.0 * SUM(is_win) / COUNT(*), 1) as winrate,
            ROUND(SUM(pnl_pct), 2) as total_pnl,
            ROUND(AVG(pnl_pct), 2) as avg_pnl
        FROM signal_outcomes
        GROUP BY signal_type
        HAVING trades >= 3
        ORDER BY total_pnl DESC
    """).fetchall()
    
    # Map to categories
    category_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0})
    
    for row in signal_perf:
        sig = row['signal_type'].lower()
        matched = False
        for cat, keywords in categories.items():
            if any(kw in sig for kw in keywords):
                category_stats[cat]['trades'] += row['trades']
                category_stats[cat]['wins'] += row['wins']
                category_stats[cat]['pnl'] += row['total_pnl']
                matched = True
                break
        if not matched:
            category_stats['Other']['trades'] += row['trades']
            category_stats['Other']['wins'] += row['wins']
            category_stats['Other']['pnl'] += row['total_pnl']
    
    print(f"\n  {'Category':<20} {'Trades':>7} {'Win%':>6} {'Total PnL':>10} {'Rating':>10}")
    print(f"  {'─' * 20} {'─' * 7} {'─' * 6} {'─' * 10} {'─' * 10}")
    
    for cat, stats in sorted(category_stats.items(), key=lambda x: -x[1]['pnl']):
        if stats['trades'] > 0:
            wr = 100.0 * stats['wins'] / stats['trades']
            marker = "🟢" if stats['pnl'] > 0 else "🔴"
            print(f"  {marker} {cat:<18} {stats['trades']:>7} {wr:>5.1f}% {stats['pnl']:>9.2f}%")

def main():
    """Main entry point."""
    conn = get_db()
    try:
        analyze_crash_sequences(conn)
        analyze_pump_sequences(conn)
        analyze_signal_followthrough(conn)
        analyze_token_regimes(conn)
        analyze_time_patterns(conn)
        analyze_signal_type_performance(conn)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
