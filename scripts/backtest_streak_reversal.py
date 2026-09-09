#!/usr/bin/env python3
"""Backtest: Streak Reversal Signal

Thesis: After 7-9 consecutive candles in the same direction (max 1 opposite candle),
the move is overextended and likely to revert.

Entry: Fire in OPPOSITE direction of the streak
Exit: Fixed TP/SL based on ATR
"""
import sqlite3
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Signal Parameters ──────────────────────────────────────────────────────
STREAK_MIN = 7           # minimum consecutive candles
STREAK_MAX = 9           # maximum consecutive candles
STREAK_MAX_OPPOSITE = 1  # max opposite candles allowed in streak
TIMEFRAME = 'candles_5m' # which candles to analyze
LOOKBACK = 15            # how many candles to look back for streak detection

# ── Exit Parameters ────────────────────────────────────────────────────────
TP_PCT = 0.8             # take profit %
SL_PCT = 1.2             # stop loss %
MIN_RR = 1.5             # minimum risk:reward


def get_candles(token, table=TIMEFRAME, limit=100):
    """Fetch OHLCV candles, oldest-first."""
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
        if not rows or len(rows) < LOOKBACK + 5:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in reversed(rows)]
    except Exception as e:
        print(f"  Error fetching {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def classify_candle(candle):
    """Return 'GREEN', 'RED', or 'DOJI'."""
    if candle['close'] > candle['open']:
        return 'GREEN'
    elif candle['close'] < candle['open']:
        return 'RED'
    return 'DOJI'


def detect_streak(candles, idx):
    """Detect a streak ending at candles[idx].
    
    Returns (streak_direction, streak_length, opposite_count) or None.
    streak_direction is the dominant direction ('GREEN' or 'RED').
    """
    if idx < STREAK_MIN:
        return None
    
    # Walk backwards from idx, count consecutive same-direction candles
    # Allow up to STREAK_MAX_OPPOSITE opposite candles
    
    # Start from the candle at idx
    dominant = classify_candle(candles[idx])
    if dominant == 'DOJI':
        return None
    
    opposite = 'RED' if dominant == 'GREEN' else 'GREEN'
    
    streak_len = 0
    opp_count = 0
    
    for i in range(idx, max(idx - LOOKBACK, -1), -1):
        c = classify_candle(candles[i])
        if c == dominant:
            streak_len += 1
        elif c == opposite:
            opp_count += 1
            if opp_count > STREAK_MAX_OPPOSITE:
                break
        else:  # DOJI
            break
    
    if STREAK_MIN <= streak_len <= STREAK_MAX and opp_count <= STREAK_MAX_OPPOSITE:
        return (dominant, streak_len, opp_count)
    
    return None


def compute_atr(candles, period=14):
    """Compute ATR over last `period` candles."""
    if len(candles) < period + 1:
        return None
    
    trs = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    
    if len(trs) < period:
        return None
    
    return sum(trs[-period:]) / period


def backtest_token(token, candles):
    """Backtest streak reversal on a single token's candles."""
    trades = []
    
    if len(candles) < LOOKBACK + 20:
        return trades
    
    for i in range(LOOKBACK, len(candles) - 10):  # leave room for exit
        streak = detect_streak(candles, i)
        if not streak:
            continue
        
        dominant, streak_len, opp_count = streak
        
        # Entry: opposite direction of streak
        if dominant == 'GREEN':
            direction = 'SHORT'  # reversal after uptrend
        else:
            direction = 'LONG'   # reversal after downtrend
        
        entry_price = candles[i]['close']
        
        # Compute ATR for exits
        atr = compute_atr(candles[:i+1], 14)
        if not atr or atr == 0:
            continue
        
        atr_pct = atr / entry_price * 100
        
        # Simulate exit: look forward up to 10 candles
        tp_price = entry_price * (1 + TP_PCT/100) if direction == 'LONG' else entry_price * (1 - TP_PCT/100)
        sl_price = entry_price * (1 - SL_PCT/100) if direction == 'LONG' else entry_price * (1 + SL_PCT/100)
        
        result = None
        for j in range(i+1, min(i+11, len(candles))):
            if direction == 'LONG':
                if candles[j]['high'] >= tp_price:
                    result = ('WIN', TP_PCT)
                    break
                if candles[j]['low'] <= sl_price:
                    result = ('LOSS', -SL_PCT)
                    break
            else:  # SHORT
                if candles[j]['low'] <= tp_price:
                    result = ('WIN', TP_PCT)
                    break
                if candles[j]['high'] >= sl_price:
                    result = ('LOSS', -SL_PCT)
                    break
        
        if result is None:
            # Timeout - exit at last candle's close
            exit_price = candles[min(i+10, len(candles)-1)]['close']
            if direction == 'LONG':
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100
            result = ('TIMEOUT', pnl_pct)
        
        trades.append({
            'token': token,
            'direction': direction,
            'entry_price': entry_price,
            'streak_len': streak_len,
            'opp_count': opp_count,
            'dominant': dominant,
            'result': result[0],
            'pnl_pct': result[1],
        })
    
    return trades


def main():
    print("=" * 70)
    print("STREAK REVERSAL BACKTEST")
    print(f"Params: streak={STREAK_MIN}-{STREAK_MAX}, max_opp={STREAK_MAX_OPPOSITE}, "
          f"TP={TP_PCT}%, SL={SL_PCT}%, timeframe=5m")
    print("=" * 70)
    
    conn = sqlite3.connect(_CANDLES_DB, timeout=10)
    tokens = [r[0] for r in conn.execute(
        f"SELECT DISTINCT token FROM {TIMEFRAME}"
    ).fetchall()]
    conn.close()
    
    print(f"\nScanning {len(tokens)} tokens...")
    
    all_trades = []
    token_stats = {}
    
    for token in sorted(tokens):
        candles = get_candles(token, TIMEFRAME, 200)
        if not candles:
            continue
        
        trades = backtest_token(token, candles)
        if trades:
            all_trades.extend(trades)
            
            wins = sum(1 for t in trades if t['result'] == 'WIN')
            losses = sum(1 for t in trades if t['result'] == 'LOSS')
            timeouts = sum(1 for t in trades if t['result'] == 'TIMEOUT')
            total_pnl = sum(t['pnl_pct'] for t in trades)
            
            token_stats[token] = {
                'trades': len(trades),
                'wins': wins,
                'losses': losses,
                'timeouts': timeouts,
                'pnl': total_pnl,
            }
            
            print(f"  {token}: {len(trades)} trades, {wins}W/{losses}L/{timeouts}T, PnL={total_pnl:+.2f}%")
    
    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if not all_trades:
        print("No trades found!")
        return
    
    total = len(all_trades)
    wins = sum(1 for t in all_trades if t['result'] == 'WIN')
    losses = sum(1 for t in all_trades if t['result'] == 'LOSS')
    timeouts = sum(1 for t in all_trades if t['result'] == 'TIMEOUT')
    total_pnl = sum(t['pnl_pct'] for t in all_trades)
    avg_pnl = total_pnl / total if total else 0
    win_rate = wins / total * 100 if total else 0
    
    # By direction
    longs = [t for t in all_trades if t['direction'] == 'LONG']
    shorts = [t for t in all_trades if t['direction'] == 'SHORT']
    
    long_wr = sum(1 for t in longs if t['result'] == 'WIN') / len(longs) * 100 if longs else 0
    short_wr = sum(1 for t in shorts if t['result'] == 'WIN') / len(shorts) * 100 if shorts else 0
    
    # By streak length
    streak_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0})
    for t in all_trades:
        s = streak_stats[t['streak_len']]
        s['trades'] += 1
        if t['result'] == 'WIN':
            s['wins'] += 1
        s['pnl'] += t['pnl_pct']
    
    print(f"\nTotal trades: {total}")
    print(f"Wins: {wins} ({win_rate:.1f}%)")
    print(f"Losses: {losses}")
    print(f"Timeouts: {timeouts}")
    print(f"Total PnL: {total_pnl:+.2f}%")
    print(f"Avg PnL/trade: {avg_pnl:+.3f}%")
    
    print(f"\nBy Direction:")
    print(f"  LONG:  {len(longs)} trades, {long_wr:.1f}% WR")
    print(f"  SHORT: {len(shorts)} trades, {short_wr:.1f}% WR")
    
    print(f"\nBy Streak Length:")
    for s in sorted(streak_stats.keys()):
        st = streak_stats[s]
        wr = st['wins'] / st['trades'] * 100 if st['trades'] else 0
        print(f"  {s} candles: {st['trades']} trades, {wr:.1f}% WR, PnL={st['pnl']:+.2f}%")
    
    # ── Verdict ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    
    if total < 20:
        print("⚠️  INSUFFICIENT SAMPLE SIZE (< 20 trades)")
    elif win_rate < 52:
        print(f"❌ FAIL: Win rate {win_rate:.1f}% < 52% minimum")
    elif avg_pnl < 0.05:
        print(f"❌ FAIL: Avg PnL {avg_pnl:.3f}% < 0.05% minimum (fee coverage)")
    elif total_pnl <= 0:
        print(f"❌ FAIL: Total PnL {total_pnl:+.2f}% <= 0")
    else:
        print(f"✅ PASS: {win_rate:.1f}% WR, {avg_pnl:+.3f}% avg PnL, {total_pnl:+.2f}% total")
        print("   Signal meets minimum quality thresholds")
    
    # ── Top/Bottom tokens ──────────────────────────────────────────────────
    if token_stats:
        print("\nTop 5 tokens by PnL:")
        for tok, st in sorted(token_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)[:5]:
            print(f"  {tok}: {st['trades']} trades, PnL={st['pnl']:+.2f}%")
        
        print("\nBottom 5 tokens by PnL:")
        for tok, st in sorted(token_stats.items(), key=lambda x: x[1]['pnl'])[:5]:
            print(f"  {tok}: {st['trades']} trades, PnL={st['pnl']:+.2f}%")


if __name__ == '__main__':
    main()
