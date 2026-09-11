#!/usr/bin/env python3
"""
Independent Backtest: EMA300 Breakthrough Signal
Verifies 4 claims about SHORT/LONG breakthrough win rates.
"""

import sqlite3
import math
from collections import defaultdict
from datetime import datetime

DB_PATH = '/root/.hermes/data/candles.db'

# Parameters from spec
EMA_PERIOD = 300
MIN_BODY_RATIO = 0.70
MIN_GAP_PCT = 0.30
PRE_MOVE_WINDOW = 5
OUTCOME_WINDOW = 4  # candles (4 * 15m = 60 minutes)


def calc_ema(closes, period):
    """Calculate EMA for a series of closes."""
    emas = [None] * len(closes)
    if len(closes) < period:
        return emas
    
    # SMA for initial value
    sma = sum(closes[:period]) / period
    emas[period - 1] = sma
    
    multiplier = 2 / (period + 1)
    for i in range(period, len(closes)):
        emas[i] = (closes[i] - emas[i-1]) * multiplier + emas[i-1]
    
    return emas


def run_backtest():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all tokens
    cursor.execute('SELECT DISTINCT token FROM candles_15m')
    tokens = [row[0] for row in cursor.fetchall()]
    
    print(f"Total tokens to analyze: {len(tokens)}")
    
    # Storage for all breakthrough signals
    all_signals = []
    
    for token_idx, token in enumerate(tokens):
        if token_idx % 50 == 0:
            print(f"Processing token {token_idx+1}/{len(token)}: {token}")
        
        # Get candles sorted by timestamp
        cursor.execute('''
            SELECT ts, open, high, low, close, volume 
            FROM candles_15m 
            WHERE token = ? 
            ORDER BY ts ASC
        ''', (token,))
        candles = cursor.fetchall()
        
        if len(candles) < EMA_PERIOD + PRE_MOVE_WINDOW + OUTCOME_WINDOW:
            continue
        
        # Extract close prices
        closes = [c[4] for c in candles]
        
        # Calculate EMA300
        emas = calc_ema(closes, EMA_PERIOD)
        
        # Scan for breakthrough candles
        for i in range(EMA_PERIOD + PRE_MOVE_WINDOW, len(candles) - OUTCOME_WINDOW):
            if emas[i] is None or emas[i-1] is None:
                continue
            
            ts, o, h, l, c, v = candles[i]
            prev_ts, prev_o, prev_h, prev_l, prev_c, prev_v = candles[i-1]
            
            ema_current = emas[i]
            ema_prev = emas[i-1]
            
            # Body ratio
            candle_range = h - l
            if candle_range <= 0:
                continue
            body = abs(c - o)
            body_ratio = body / candle_range
            
            # Gap at close (distance from close to EMA300 as % of EMA300)
            gap_pct = abs(c - ema_current) / ema_current * 100
            
            # Pre-move: price change over PRE_MOVE_WINDOW candles
            pre_move_start_idx = i - PRE_MOVE_WINDOW
            if pre_move_start_idx < 0:
                continue
            pre_move_start_close = closes[pre_move_start_idx]
            pre_move = (c - pre_move_start_close) / pre_move_start_close * 100
            
            # Outcome: price change over next OUTCOME_WINDOW candles
            outcome_close = closes[i + OUTCOME_WINDOW]
            outcome_pnl = (outcome_close - c) / c * 100
            
            # Determine signal type
            is_short = False
            is_long = False
            
            # SHORT: prev close > EMA, current close < EMA, candle is RED
            if prev_c > ema_prev and c < ema_current and c < o:
                is_short = True
            
            # LONG: prev close < EMA, current close > EMA, candle is GREEN
            if prev_c < ema_prev and c > ema_current and c > o:
                is_long = True
            
            if not is_short and not is_long:
                continue
            
            signal = {
                'token': token,
                'ts': ts,
                'datetime': datetime.utcfromtimestamp(ts).isoformat(),
                'direction': 'SHORT' if is_short else 'LONG',
                'open': o,
                'high': h,
                'low': l,
                'close': c,
                'ema': ema_current,
                'body_ratio': body_ratio,
                'gap_pct': gap_pct,
                'pre_move': pre_move,
                'outcome_pnl': outcome_pnl,
            }
            all_signals.append(signal)
    
    conn.close()
    
    print(f"\nTotal signals found: {len(all_signals)}")
    
    # Analyze results
    analyze_results(all_signals)


def analyze_results(signals):
    """Analyze and print results for all claim scenarios."""
    
    print("\n" + "="*80)
    print("INDEPENDENT BACKTEST RESULTS")
    print("="*80)
    
    # Claim 1: SHORT breakthrough with pre_move < -2% + body>70% + gap>0.3% = 80% WR (15 trades)
    print("\n--- CLAIM 1: SHORT + pre_move < -2% + body > 70% + gap > 0.3% ---")
    claim1 = [s for s in signals if s['direction'] == 'SHORT' 
              and s['pre_move'] < -2.0 
              and s['body_ratio'] > 0.70 
              and s['gap_pct'] > 0.30]
    print_claim_result(claim1, "SHORT pre_move<-2% + body>70% + gap>0.3%")
    
    # Claim 2: SHORT breakthrough with pre_move < -1.5% + body>70% = 69% WR (29 trades)
    print("\n--- CLAIM 2: SHORT + pre_move < -1.5% + body > 70% ---")
    claim2 = [s for s in signals if s['direction'] == 'SHORT'
              and s['pre_move'] < -1.5
              and s['body_ratio'] > 0.70]
    print_claim_result(claim2, "SHORT pre_move<-1.5% + body>70%")
    
    # Claim 3: LONG breakthrough with pre_move < -2% (reversal) = 61% WR (54 trades)
    print("\n--- CLAIM 3: LONG + pre_move < -2% (reversal) ---")
    claim3 = [s for s in signals if s['direction'] == 'LONG'
              and s['pre_move'] < -2.0]
    print_claim_result(claim3, "LONG pre_move<-2% (reversal)")
    
    # Claim 4: LONG trend continuation (pre_move > 2%) = 37.5% WR (doesn't work)
    print("\n--- CLAIM 4: LONG + pre_move > 2% (trend continuation) ---")
    claim4 = [s for s in signals if s['direction'] == 'LONG'
              and s['pre_move'] > 2.0]
    print_claim_result(claim4, "LONG pre_move>2% (trend continuation)")
    
    # Additional robustness checks
    print("\n" + "="*80)
    print("ROBUSTNESS CHECKS")
    print("="*80)
    
    # Check SHORT with various pre_move thresholds
    print("\n--- SHORT by pre_move threshold (body > 70%, gap > 0.3%) ---")
    for threshold in [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5]:
        filtered = [s for s in signals if s['direction'] == 'SHORT'
                   and s['pre_move'] < threshold
                   and s['body_ratio'] > 0.70
                   and s['gap_pct'] > 0.30]
        print_claim_result(filtered, f"SHORT pre_move<{threshold}%")
    
    # Check LONG with various pre_move thresholds
    print("\n--- LONG by pre_move threshold (body > 70%, gap > 0.3%) ---")
    for threshold in [3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0, -0.5, -1.0, -1.5, -2.0, -2.5, -3.0]:
        filtered = [s for s in signals if s['direction'] == 'LONG'
                   and s['pre_move'] < threshold
                   and s['body_ratio'] > 0.70
                   and s['gap_pct'] > 0.30]
        print_claim_result(filtered, f"LONG pre_move<{threshold}%")
    
    # Check impact of body ratio threshold
    print("\n--- SHORT body ratio sensitivity (pre_move < -2%, gap > 0.3%) ---")
    for br_threshold in [0.50, 0.60, 0.70, 0.80, 0.90]:
        filtered = [s for s in signals if s['direction'] == 'SHORT'
                   and s['pre_move'] < -2.0
                   and s['body_ratio'] > br_threshold
                   and s['gap_pct'] > 0.30]
        print_claim_result(filtered, f"SHORT body>{br_threshold}")
    
    # Check gap threshold sensitivity
    print("\n--- SHORT gap sensitivity (pre_move < -2%, body > 70%) ---")
    for gap_threshold in [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
        filtered = [s for s in signals if s['direction'] == 'SHORT'
                   and s['pre_move'] < -2.0
                   and s['body_ratio'] > 0.70
                   and s['gap_pct'] > gap_threshold]
        print_claim_result(filtered, f"SHORT gap>{gap_threshold}%")
    
    # Outcome window sensitivity
    print("\n--- Outcome window sensitivity ---")
    # This would need re-computation, so skip for now
    
    # Check all raw signals
    print("\n--- All SHORT raw (no filters) ---")
    all_short = [s for s in signals if s['direction'] == 'SHORT']
    print_claim_result(all_short, "SHORT raw")
    
    print("\n--- All LONG raw (no filters) ---")
    all_long = [s for s in signals if s['direction'] == 'LONG']
    print_claim_result(all_long, "LONG raw")
    
    # Print some sample signals for verification
    print("\n" + "="*80)
    print("SAMPLE SIGNALS (for verification)")
    print("="*80)
    
    if claim1:
        print("\n--- Claim 1 samples (SHORT + pre_move<-2% + body>70% + gap>0.3%) ---")
        for s in claim1[:5]:
            print(f"  {s['token']} @ {s['datetime']}: close={s['close']:.6f}, ema={s['ema']:.6f}, "
                  f"body_ratio={s['body_ratio']:.3f}, gap={s['gap_pct']:.3f}%, "
                  f"pre_move={s['pre_move']:.3f}%, outcome={s['outcome_pnl']:.3f}%")


def print_claim_result(signals, label):
    """Print win rate and stats for a set of signals."""
    if not signals:
        print(f"  {label}: NO SIGNALS FOUND")
        return
    
    wins = sum(1 for s in signals if s['outcome_pnl'] > 0)
    losses = sum(1 for s in signals if s['outcome_pnl'] <= 0)
    wr = wins / len(signals) * 100
    avg_pnl = sum(s['outcome_pnl'] for s in signals) / len(signals)
    avg_win = sum(s['outcome_pnl'] for s in signals if s['outcome_pnl'] > 0) / max(1, wins)
    avg_loss = sum(s['outcome_pnl'] for s in signals if s['outcome_pnl'] <= 0) / max(1, losses)
    
    print(f"  {label}:")
    print(f"    Trades: {len(signals)}")
    print(f"    Win Rate: {wr:.1f}% ({wins}W / {losses}L)")
    print(f"    Avg PnL: {avg_pnl:.3f}%")
    print(f"    Avg Win: {avg_win:.3f}%")
    print(f"    Avg Loss: {avg_loss:.3f}%")
    if avg_loss != 0:
        print(f"    Profit Factor: {abs(avg_win * wins / (avg_loss * losses)):.2f}")


if __name__ == '__main__':
    run_backtest()
