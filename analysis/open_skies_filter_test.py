#!/usr/bin/env python3
"""
Independent analysis: Test proposed RSI 30-60 filter for open-skies signal.

For each open-skies trade, we:
1. Fetch candle data at trade creation time
2. Compute RSI(14), trend direction (last 5 bars), higher highs, support levels
3. Test proposed filter: "trend UP AND RSI 30-60"
4. Report which trades would be blocked vs allowed
"""

import sqlite3
import numpy as np
import sys
import os

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA, CANDLES_DB

RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')


def get_open_skies_trades():
    """Get all open-skies trade outcomes from the runtime DB."""
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, signal_type, is_win, pnl_pct, pnl_usdt, 
               confidence, regime, created_at, closed_at
        FROM signal_outcomes 
        WHERE signal_type LIKE '%open-skies%' 
        ORDER BY created_at ASC
    """)
    trades = cur.fetchall()
    conn.close()
    return trades


def get_candles_at_time(token, target_ts, limit=100):
    """
    Fetch candles from candles_5m that were available at the given timestamp.
    target_ts is a string like '2026-09-05 01:06:36'.
    """
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_5m
        WHERE token = ? AND is_closed = 1 AND ts <= ?
        ORDER BY ts DESC
        LIMIT ?
    """, (token.upper(), target_ts, limit))
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return []
    return list(reversed(rows))  # oldest first


def compute_rsi(closes, period=14):
    """Compute RSI. Returns float or None."""
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


def get_trend_direction(closes, window=5):
    """Determine trend direction over last N bars. Returns 'UP', 'DOWN', or 'FLAT'."""
    if len(closes) < window:
        return 'UNKNOWN'
    recent = closes[-window:]
    # Check if last close > first close
    if recent[-1] > recent[0] * 1.001:  # >0.1% up
        return 'UP'
    elif recent[-1] < recent[0] * 0.999:  # >0.1% down
        return 'DOWN'
    else:
        return 'FLAT'


def count_higher_highs(highs, window=10):
    """Count higher highs in last N bars."""
    if len(highs) < window:
        return 0
    recent = highs[-window:]
    count = 0
    for i in range(1, len(recent)):
        if recent[i] > recent[i - 1]:
            count += 1
    return count


def get_support_resistance(token, price):
    """Get S/R map from risk_reward_engine. Returns (support_count, resistance_count)."""
    try:
        from risk_reward_engine import build_sr_map
        sr_map = build_sr_map(token, price)
        resistance_levels = [l for l in sr_map if l.get('type') == 'resistance']
        support_levels = [l for l in sr_map if l.get('type') == 'support']
        return len(support_levels), len(resistance_levels)
    except Exception as e:
        return None, None


def compute_sma(closes, period):
    """Simple Moving Average."""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def main():
    trades = get_open_skies_trades()
    print(f"Found {len(trades)} open-skies trades\n")
    
    results = []
    
    for trade in trades:
        trade_id, token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence, regime, created_at, closed_at = trade
        
        # Get candles at trade creation time
        candles = get_candles_at_time(token, created_at, limit=100)
        
        if not candles or len(candles) < 60:
            print(f"WARNING: {token} ({created_at}) - insufficient candle data ({len(candles)} candles)")
            results.append({
                'trade_id': trade_id,
                'token': token,
                'created_at': created_at,
                'pnl_pct': pnl_pct,
                'is_win': is_win,
                'regime': regime,
                'rsi': None,
                'trend': 'UNKNOWN',
                'higher_highs': 0,
                'support_count': None,
                'resistance_count': None,
                'filter_pass': False,
                'data_quality': 'INSUFFICIENT',
            })
            continue
        
        closes = [c[4] for c in candles]
        highs = [c[2] for c in candles]
        
        # Compute indicators
        rsi = compute_rsi(closes)
        trend = get_trend_direction(closes)
        hh_count = count_higher_highs(highs, window=10)
        price = closes[-1]
        
        # Get S/R levels
        support_count, resistance_count = get_support_resistance(token, price)
        
        # SMA20/50 for reference
        sma20 = compute_sma(closes, 20)
        sma50 = compute_sma(closes, 50)
        
        # Test proposed filter: "trend UP AND RSI 30-60"
        # This means: BLOCK if NOT (trend UP AND RSI 30-60)
        # So ALLOW only if trend UP AND RSI between 30 and 60
        filter_pass = (trend == 'UP' and rsi is not None and 30 <= rsi <= 60)
        
        result = {
            'trade_id': trade_id,
            'token': token,
            'created_at': created_at,
            'pnl_pct': pnl_pct,
            'is_win': is_win,
            'regime': regime,
            'signal_type': signal_type,
            'rsi': round(rsi, 2) if rsi else None,
            'trend': trend,
            'higher_highs': hh_count,
            'support_count': support_count,
            'resistance_count': resistance_count,
            'sma20': round(sma20, 4) if sma20 else None,
            'sma50': round(sma50, 4) if sma50 else None,
            'price': round(price, 4),
            'filter_pass': filter_pass,
            'data_quality': 'OK',
        }
        results.append(result)
        
        status = "WIN" if is_win else "LOSS"
        filter_status = "PASS (would trade)" if filter_pass else "BLOCK (filtered out)"
        
        print(f"{token:8s} {created_at}  PnL={pnl_pct:+7.2f}%  {status:4s}  RSI={rsi:6.1f}  trend={trend:5s}  hh={hh_count}  sup={support_count}  res={resistance_count}  regime={regime:8s}  → {filter_status}")
    
    # Summary
    print("\n" + "="*120)
    print("SUMMARY")
    print("="*120)
    
    total = len(results)
    valid = [r for r in results if r['data_quality'] == 'OK']
    passed = [r for r in valid if r['filter_pass']]
    blocked = [r for r in valid if not r['filter_pass']]
    
    wins_pass = [r for r in passed if r['is_win']]
    losses_pass = [r for r in passed if not r['is_win']]
    wins_block = [r for r in blocked if r['is_win']]
    losses_block = [r for r in blocked if not r['is_win']]
    
    print(f"\nTotal trades: {total}")
    print(f"Valid (sufficient data): {len(valid)}")
    print(f"Data quality issues: {total - len(valid)}")
    
    print(f"\n--- PROPOSED FILTER: trend UP AND RSI 30-60 ---")
    print(f"Would PASS (trade):  {len(passed)} ({len(passed)/len(valid)*100:.1f}% of valid)")
    print(f"  Wins passing:      {len(wins_pass)}")
    print(f"  Losses passing:    {len(losses_pass)}")
    
    print(f"\nWould BLOCK (skip):  {len(blocked)} ({len(blocked)/len(valid)*100:.1f}% of valid)")
    print(f"  Wins blocked:      {len(wins_block)}")
    print(f"  Losses blocked:    {len(losses_block)}")
    
    if len(passed) > 0:
        win_rate_pass = len(wins_pass) / len(passed) * 100
        avg_pnl_pass = sum(r['pnl_pct'] for r in passed) / len(passed)
        total_pnl_pass = sum(r['pnl_pct'] for r in passed)
        print(f"\n  Win rate (filtered): {win_rate_pass:.1f}% ({len(wins_pass)}W/{len(losses_pass)}L)")
        print(f"  Avg PnL (filtered):  {avg_pnl_pass:.2f}%")
        print(f"  Total PnL (filtered): {total_pnl_pass:.2f}%")
    
    if len(blocked) > 0:
        win_rate_block = len(wins_block) / len(blocked) * 100
        avg_pnl_block = sum(r['pnl_pct'] for r in blocked) / len(blocked)
        total_pnl_block = sum(r['pnl_pct'] for r in blocked)
        print(f"\n  Win rate (blocked): {win_rate_block:.1f}% ({len(wins_block)}W/{len(losses_block)}L)")
        print(f"  Avg PnL (blocked):  {avg_pnl_block:.2f}%")
        print(f"  Total PnL (blocked): {total_pnl_block:.2f}%")
    
    # Check big winners specifically
    print(f"\n--- BIG WINNER CHECK (>= +2%) ---")
    big_winners = [r for r in valid if r['pnl_pct'] >= 2.0]
    big_winner_blocked = [r for r in big_winners if not r['filter_pass']]
    print(f"Big winners (>= +2%): {len(big_winners)}")
    for bw in big_winners:
        status = "BLOCKED" if not bw['filter_pass'] else "PASSED"
        print(f"  {bw['token']:8s} {bw['pnl_pct']:+7.2f}%  RSI={bw['rsi']:6.1f}  trend={bw['trend']:5s}  → {status}")
    
    if big_winner_blocked:
        print(f"\n  ⚠️  {len(big_winner_blocked)} big winner(s) WOULD BE BLOCKED by proposed filter!")
    else:
        print(f"\n  ✅ No big winners would be blocked by proposed filter.")
    
    # RSI distribution
    print(f"\n--- RSI DISTRIBUTION ---")
    for r in valid:
        if r['rsi'] is not None:
            marker = "✓" if 30 <= r['rsi'] <= 60 else "✗"
            win = "W" if r['is_win'] else "L"
            print(f"  {r['token']:8s} RSI={r['rsi']:6.1f}  {marker}  {win}  PnL={r['pnl_pct']:+7.2f}%")
    
    # Wins above RSI 60 (would be blocked)
    print(f"\n--- WINS WITH RSI > 60 (would be blocked) ---")
    wins_high_rsi = [r for r in valid if r['is_win'] and r['rsi'] is not None and r['rsi'] > 60]
    for w in wins_high_rsi:
        print(f"  {w['token']:8s} RSI={w['rsi']:6.1f}  PnL={w['pnl_pct']:+7.2f}%")
    
    # Wins with trend NOT UP (would be blocked)
    print(f"\n--- WINS WITH TREND NOT UP (would be blocked) ---")
    wins_not_up = [r for r in valid if r['is_win'] and r['trend'] != 'UP']
    for w in wins_not_up:
        print(f"  {w['token']:8s} trend={w['trend']:5s}  PnL={w['pnl_pct']:+7.2f}%")
    
    # Current max RSI = 75 check
    print(f"\n--- CURRENT OPEN_SKIES_MAX_RSI = 75 CHECK ---")
    above_75 = [r for r in valid if r['rsi'] is not None and r['rsi'] > 75]
    between_60_75 = [r for r in valid if r['rsi'] is not None and 60 < r['rsi'] <= 75]
    print(f"Trades with RSI > 75: {len(above_75)}")
    for t in above_75:
        win = "W" if t['is_win'] else "L"
        print(f"  {t['token']:8s} RSI={t['rsi']:6.1f}  {win}  PnL={t['pnl_pct']:+7.2f}%")
    print(f"Trades with RSI 60-75 (would be newly blocked): {len(between_60_75)}")
    for t in between_60_75:
        win = "W" if t['is_win'] else "L"
        print(f"  {t['token']:8s} RSI={t['rsi']:6.1f}  {win}  PnL={t['pnl_pct']:+7.2f}%")
    
    # Regime analysis
    print(f"\n--- REGIME ANALYSIS ---")
    regimes = {}
    for r in valid:
        reg = r['regime']
        if reg not in regimes:
            regimes[reg] = {'wins': 0, 'losses': 0, 'pnl': 0}
        if r['is_win']:
            regimes[reg]['wins'] += 1
        else:
            regimes[reg]['losses'] += 1
        regimes[reg]['pnl'] += r['pnl_pct']
    
    for reg in sorted(regimes.keys()):
        data = regimes[reg]
        total_t = data['wins'] + data['losses']
        wr = data['wins'] / total_t * 100 if total_t > 0 else 0
        print(f"  {reg:8s}: {total_t:2d}T  {data['wins']}W/{data['losses']}L  WR={wr:.0f}%  PnL={data['pnl']:+.2f}%")
    
    # Confidence analysis
    print(f"\n--- CONFIDENCE ANALYSIS ---")
    confs = {}
    for r in valid:
        c = r.get('signal_type', 'unknown')
        confs.setdefault(c, []).append(r)
    
    for st in sorted(confs.keys()):
        trades_list = confs[st]
        wins = sum(1 for t in trades_list if t['is_win'])
        total_t = len(trades_list)
        wr = wins / total_t * 100
        avg_pnl = sum(t['pnl_pct'] for t in trades_list) / total_t
        print(f"  {st}: {total_t}T  {wins}W/{total_t-wins}L  WR={wr:.0f}%  avg={avg_pnl:+.2f}%")
    
    return results


if __name__ == '__main__':
    main()
