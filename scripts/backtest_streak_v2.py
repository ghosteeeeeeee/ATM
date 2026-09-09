#!/usr/bin/env python3
"""Backtest: Streak Reversal — Parameter Sweep

Test multiple parameter combinations to find what works.
"""
import sqlite3
import os
import sys
from collections import defaultdict
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
TIMEFRAME = 'candles_5m'


def get_candles(token, table=TIMEFRAME, limit=200):
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume
            FROM {table}
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        if not rows:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in reversed(rows)]
    except:
        return []
    finally:
        if conn:
            conn.close()


def classify_candle(c):
    if c['close'] > c['open']:
        return 'GREEN'
    elif c['close'] < c['open']:
        return 'RED'
    return 'DOJI'


def detect_streak(candles, idx, streak_min, streak_max, max_opp):
    if idx < streak_min:
        return None
    
    dominant = classify_candle(candles[idx])
    if dominant == 'DOJI':
        return None
    
    opposite = 'RED' if dominant == 'GREEN' else 'GREEN'
    streak_len = 0
    opp_count = 0
    
    for i in range(idx, max(idx - 20, -1), -1):
        c = classify_candle(candles[i])
        if c == dominant:
            streak_len += 1
        elif c == opposite:
            opp_count += 1
            if opp_count > max_opp:
                break
        else:
            break
    
    if streak_min <= streak_len <= streak_max and opp_count <= max_opp:
        return (dominant, streak_len, opp_count)
    return None


def backtest_token(token, candles, params):
    streak_min, streak_max, max_opp, tp_pct, sl_pct, exit_candles = params
    trades = []
    
    lookback = streak_max + 5
    if len(candles) < lookback + exit_candles + 5:
        return trades
    
    for i in range(lookback, len(candles) - exit_candles):
        streak = detect_streak(candles, i, streak_min, streak_max, max_opp)
        if not streak:
            continue
        
        dominant, streak_len, opp_count = streak
        direction = 'SHORT' if dominant == 'GREEN' else 'LONG'
        entry_price = candles[i]['close']
        
        tp_price = entry_price * (1 + tp_pct/100) if direction == 'LONG' else entry_price * (1 - tp_pct/100)
        sl_price = entry_price * (1 - sl_pct/100) if direction == 'LONG' else entry_price * (1 + sl_pct/100)
        
        result = None
        for j in range(i+1, min(i+exit_candles+1, len(candles))):
            if direction == 'LONG':
                if candles[j]['high'] >= tp_price:
                    result = ('WIN', tp_pct)
                    break
                if candles[j]['low'] <= sl_price:
                    result = ('LOSS', -sl_pct)
                    break
            else:
                if candles[j]['low'] <= tp_price:
                    result = ('WIN', tp_pct)
                    break
                if candles[j]['high'] <= sl_price:
                    result = ('LOSS', -sl_pct)
                    break
        
        if result is None:
            exit_price = candles[min(i+exit_candles, len(candles)-1)]['close']
            if direction == 'LONG':
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100
            result = ('TIMEOUT', pnl_pct)
        
        trades.append({
            'result': result[0],
            'pnl_pct': result[1],
            'direction': direction,
            'streak_len': streak_len,
        })
    
    return trades


def run_sweep():
    # Parameter grid
    streak_mins = [5, 7, 9]
    streak_maxs = [9, 12, 15]
    max_opps = [0, 1, 2]
    tp_pcts = [0.5, 0.8, 1.0, 1.5]
    sl_pcts = [0.8, 1.0, 1.2, 1.5]
    exit_candles_list = [5, 10, 15]
    
    # Get all tokens
    conn = sqlite3.connect(_CANDLES_DB, timeout=10)
    tokens = [r[0] for r in conn.execute(
        f"SELECT DISTINCT token FROM {TIMEFRAME}"
    ).fetchall()]
    conn.close()
    
    # Pre-load all candle data
    print("Loading candle data...")
    all_candles = {}
    for token in tokens:
        candles = get_candles(token, TIMEFRAME, 200)
        if candles and len(candles) > 30:
            all_candles[token] = candles
    print(f"Loaded {len(all_candles)} tokens with sufficient data\n")
    
    # Run sweep
    best_results = []
    total_combos = len(streak_mins) * len(streak_maxs) * len(max_opps) * len(tp_pcts) * len(sl_pcts) * len(exit_candles_list)
    print(f"Testing {total_combos} parameter combinations...\n")
    
    count = 0
    for smin, smax, mop, tp, sl, ec in product(streak_mins, streak_maxs, max_opps, tp_pcts, sl_pcts, exit_candles_list):
        if smin > smax:
            continue
        if tp >= sl:  # need positive R:R
            continue
        
        count += 1
        params = (smin, smax, mop, tp, sl, ec)
        
        all_trades = []
        for token, candles in all_candles.items():
            trades = backtest_token(token, candles, params)
            all_trades.extend(trades)
        
        if len(all_trades) < 20:
            continue
        
        total = len(all_trades)
        wins = sum(1 for t in all_trades if t['result'] == 'WIN')
        losses = sum(1 for t in all_trades if t['result'] == 'LOSS')
        timeouts = sum(1 for t in all_trades if t['result'] == 'TIMEOUT')
        total_pnl = sum(t['pnl_pct'] for t in all_trades)
        avg_pnl = total_pnl / total
        win_rate = wins / total * 100
        
        # Filter for quality
        if win_rate >= 50 and avg_pnl > 0 and total_pnl > 0:
            best_results.append({
                'params': params,
                'trades': total,
                'wins': wins,
                'losses': losses,
                'timeouts': timeouts,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl,
            })
    
    # Sort by total PnL
    best_results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    print(f"Tested {count} valid combinations")
    print(f"Found {len(best_results)} passing combos (WR>=50%, PnL>0)\n")
    
    if best_results:
        print("TOP 10 RESULTS:")
        print("-" * 100)
        print(f"{'Streak':>8} {'MaxOpp':>7} {'TP%':>5} {'SL%':>5} {'Exit':>5} {'Trades':>7} {'Wins':>5} {'WR%':>6} {'AvgPnL':>7} {'TotalPnL':>9}")
        print("-" * 100)
        for r in best_results[:10]:
            smin, smax, mop, tp, sl, ec = r['params']
            print(f"{smin}-{smax:>5} {mop:>7} {tp:>5.1f} {sl:>5.1f} {ec:>5} {r['trades']:>7} {r['wins']:>5} {r['win_rate']:>6.1f} {r['avg_pnl']:>7.3f} {r['total_pnl']:>9.2f}")
        
        # Detailed breakdown of best
        best = best_results[0]
        print(f"\n{'='*70}")
        print(f"BEST PARAMS: streak={best['params'][0]}-{best['params'][1]}, max_opp={best['params'][2]}, "
              f"TP={best['params'][3]}%, SL={best['params'][4]}%, exit={best['params'][5]}candles")
        print(f"{'='*70}")
        print(f"Trades: {best['trades']}")
        print(f"Win Rate: {best['win_rate']:.1f}%")
        print(f"Avg PnL: {best['avg_pnl']:+.3f}%")
        print(f"Total PnL: {best['total_pnl']:+.2f}%")
        print(f"Timeouts: {best['timeouts']} ({best['timeouts']/best['trades']*100:.0f}%)")
    else:
        print("No parameter combination passed quality thresholds.")
        print("\nRunning brute force analysis on best available...")
        
        # Show top 10 even if not passing
        all_results = []
        for smin, smax, mop, tp, sl, ec in product(streak_mins, streak_maxs, max_opps, tp_pcts, sl_pcts, exit_candles_list):
            if smin > smax or tp >= sl:
                continue
            
            params = (smin, smax, mop, tp, sl, ec)
            all_trades = []
            for token, candles in all_candles.items():
                trades = backtest_token(token, candles, params)
                all_trades.extend(trades)
            
            if len(all_trades) < 15:
                continue
            
            total = len(all_trades)
            wins = sum(1 for t in all_trades if t['result'] == 'WIN')
            total_pnl = sum(t['pnl_pct'] for t in all_trades)
            avg_pnl = total_pnl / total
            win_rate = wins / total * 100
            timeouts = sum(1 for t in all_trades if t['result'] == 'TIMEOUT')
            
            all_results.append({
                'params': params,
                'trades': total,
                'wins': wins,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl,
                'timeouts': timeouts,
            })
        
        all_results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print("\nTOP 10 (even if not passing):")
        print("-" * 100)
        for r in all_results[:10]:
            smin, smax, mop, tp, sl, ec = r['params']
            flag = "✓" if r['win_rate'] >= 50 and r['avg_pnl'] > 0 else "✗"
            print(f"{flag} streak={smin}-{smax} opp={mop} TP={tp}% SL={sl}% exit={ec}c | "
                  f"{r['trades']}t {r['win_rate']:.0f}%WR avg={r['avg_pnl']:+.3f}% total={r['total_pnl']:+.2f}% timeout={r['timeouts']}")


if __name__ == '__main__':
    run_sweep()
