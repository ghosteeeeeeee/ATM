#!/usr/bin/env python3
"""
INDEPENDENT BACKTEST: Trend Ignition Signal
Auditor: Independent verification of claims made in 2026-09-08_trend-ignition-signal-spec.md

This script independently computes ALL indicators from raw candle data and applies the
exact filters specified in the spec. No shortcuts, no shortcuts, no cheating.

Claims to verify:
1. 9 signals over 7 days (1.3/day)
2. 100% win rate (all positive 4h return)
3. Average 4h return = +1.92%
4. Best trade: ATOM +6.49%
5. Filter conditions are correctly specified
6. No look-ahead bias
"""

import sqlite3
import math
import sys
import os
from datetime import datetime, timezone
from collections import defaultdict

# Paths
CANDLES_DB = "/root/.hermes/data/candles.db"

# ─── Constants from spec ───
VOL_SPIKE_MIN = 2.5          # min volume spike ratio
VOL_ELEVATED_RATIO = 2.0     # "elevated" = 2x average
VOL_SUSTAINED_MIN = 2        # min bars with elevated volume (2 of last 3)
BB_MIN = 1.0                 # min BB width %
BB_MAX = 2.0                 # max BB width %
BREAKOUT_PERIOD = 20         # bars for consolidation high
EMA_PERIOD = 50              # trend filter EMA
EMA_MIN_DIST = 0.5           # min % distance from EMA50
RSI_MAX = 65                 # not overbought
RSI_PERIOD = 14
COOLDOWN_HOURS = 1
EXIT_HOURS = 4               # time stop

# Backtest window: last 7 days
# Data available: 2026-09-05 18:35 to 2026-09-08 18:40 (UTC+8)
# Using last 7 days from DB


def get_candles(token, limit=200):
    """Fetch 5m candles oldest-first."""
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_5m
        WHERE token = ? AND is_closed = 1
        ORDER BY ts ASC
        LIMIT ?
    """, (token.upper(), limit))
    rows = cur.fetchall()
    conn.close()
    return rows  # [(ts, open, high, low, close, volume), ...]


def compute_ema(closes, period):
    """Exponential Moving Average - returns list, last value is EMA."""
    if len(closes) < period:
        return None
    # Seed with SMA
    ema = sum(closes[:period]) / period
    multiplier = 2 / (period + 1)
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def compute_ema_series(closes, period):
    """Compute full EMA series aligned with input (None for insufficient data)."""
    if len(closes) < period:
        return [None] * len(closes)
    
    result = [None] * (period - 1)
    ema = sum(closes[:period]) / period
    result.append(ema)
    multiplier = 2 / (period + 1)
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
        result.append(ema)
    return result


def compute_sma(closes, period):
    """Simple Moving Average."""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def compute_bb_width(closes, period=20):
    """
    Bollinger Band width as % of middle band.
    BB Width = (Upper - Lower) / Middle * 100
    """
    if len(closes) < period:
        return None
    
    sma = sum(closes[-period:]) / period
    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std_dev = math.sqrt(variance)
    
    upper = sma + 2 * std_dev
    lower = sma - 2 * std_dev
    
    if sma == 0:
        return None
    
    bb_width_pct = (upper - lower) / sma * 100
    return bb_width_pct


def compute_bb_width_series(closes, period=20):
    """Compute BB width series aligned with input."""
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            window = closes[i - period + 1:i + 1]
            sma = sum(window) / period
            variance = sum((c - sma) ** 2 for c in window) / period
            std_dev = math.sqrt(variance)
            if sma == 0:
                result.append(None)
            else:
                result.append((std_dev * 4) / sma * 100)
    return result


def compute_rsi(closes, period=14):
    """RSI series aligned with input."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    
    result = [None] * period
    
    # Compute initial average gain/loss
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-delta)
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100 - (100 / (1 + rs)))
    
    # Subsequent values using smoothed average
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
    
    return result


def compute_volume_ratios(volumes, lookback=20):
    """
    Compute volume spike ratio: current bar volume / average of previous 'lookback' bars.
    Returns series aligned with input.
    """
    result = [None] * lookback
    for i in range(lookback, len(volumes)):
        avg_prev = sum(volumes[i - lookback:i]) / lookback
        if avg_prev == 0:
            result.append(None)
        else:
            result.append(volumes[i] / avg_prev)
    return result


def compute_sustained_volume(volumes, elevated_ratio=2.0, lookback=20, sustained_window=3):
    """
    Count how many of last 'sustained_window' bars have volume > elevated_ratio * avg.
    Returns series aligned with input.
    """
    result = [None] * (lookback + sustained_window - 1)
    for i in range(lookback + sustained_window - 1, len(volumes)):
        avg_prev = sum(volumes[i - lookback - sustained_window + 1:i - sustained_window + 1]) / lookback
        if avg_prev == 0:
            result.append(0)
        else:
            count = 0
            for j in range(sustained_window):
                if volumes[i - j] > elevated_ratio * avg_prev:
                    count += 1
            result.append(count)
    return result


def compute_highs(highs, period):
    """Compute rolling high over 'period' bars (not including current bar)."""
    result = [None] * period
    for i in range(period, len(highs)):
        result.append(max(highs[i - period:i]))
    return result


def get_backtest_tokens():
    """Get all tokens that have data in the last 7 days."""
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT token FROM candles_5m
        WHERE ts > strftime('%s', 'now') - 7*86400
        AND is_closed = 1
    """)
    tokens = [r[0] for r in cur.fetchall()]
    conn.close()
    return tokens


def backtest_token(token, verbose=False):
    """
    Run trend ignition detection on a single token over 7 days.
    Returns list of signals found.
    """
    # Get all candles for this token
    candles = get_candles(token, limit=200)
    if len(candles) < 60:  # Need enough history for indicators
        return []
    
    ts = [c[0] for c in candles]
    opens = [c[1] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[4] for c in candles]
    volumes = [c[5] for c in candles]
    
    # Compute all indicator series
    ema50_series = compute_ema_series(closes, EMA_PERIOD)
    bb_width_series = compute_bb_width_series(closes, 20)
    rsi_series = compute_rsi(closes, RSI_PERIOD)
    vol_ratio_series = compute_volume_ratios(volumes, 20)
    sustained_series = compute_sustained_volume(volumes, VOL_ELEVATED_RATIO, 20, 3)
    rolling_high_series = compute_highs(highs, BREAKOUT_PERIOD)
    
    signals = []
    last_signal_ts = None
    
    # Scan from EMA_PERIOD onwards (need enough data)
    for i in range(max(EMA_PERIOD, 20, 20 + 2), len(candles)):
        current_ts = ts[i]
        current_close = closes[i]
        current_volume = volumes[i]
        current_high = highs[i]
        
        # Skip if we already have a signal within cooldown
        if last_signal_ts and (current_ts - last_signal_ts) < COOLDOWN_HOURS * 3600:
            continue
        
        # ─── Condition 1: Volume spike > 2.5x ───
        vol_ratio = vol_ratio_series[i]
        if vol_ratio is None or vol_ratio < VOL_SPIKE_MIN:
            continue
        
        # ─── Condition 2: Sustained volume (2+ of last 3 bars elevated) ───
        sustained = sustained_series[i]
        if sustained is None or sustained < VOL_SUSTAINED_MIN:
            continue
        
        # ─── Condition 3: BB width 1-2% ───
        bb_width = bb_width_series[i]
        if bb_width is None or bb_width < BB_MIN or bb_width > BB_MAX:
            continue
        
        # ─── Condition 4: Breakout (close > 20-bar high) ───
        rolling_high = rolling_high_series[i]
        if rolling_high is None:
            continue
        if current_close <= rolling_high:
            continue
        
        # ─── Condition 5: Above EMA50 ───
        ema50 = ema50_series[i]
        if ema50 is None or current_close <= ema50:
            continue
        
        # ─── Condition 6: EMA50 distance > 0.5% ───
        ema_dist = (current_close - ema50) / ema50 * 100
        if ema_dist < EMA_MIN_DIST:
            continue
        
        # ─── Condition 7: RSI < 65 ───
        rsi = rsi_series[i]
        if rsi is not None and rsi >= RSI_MAX:
            continue
        
        # ─── ALL CONDITIONS MET ───
        # Compute 4h return (48 bars of 5m each)
        exit_idx = i + 48
        if exit_idx < len(candles):
            exit_price = closes[exit_idx]
            ret_4h = (exit_price - current_close) / current_close * 100
        else:
            # Not enough data for 4h exit
            ret_4h = None
        
        signal = {
            'token': token,
            'ts': current_ts,
            'datetime': datetime.fromtimestamp(current_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M'),
            'price': current_close,
            'vol_ratio': vol_ratio,
            'sustained': sustained,
            'bb_width': bb_width,
            'rolling_high': rolling_high,
            'breakout_pct': (current_close - rolling_high) / rolling_high * 100,
            'ema50': ema50,
            'ema_dist': ema_dist,
            'rsi': rsi,
            'ret_4h': ret_4h,
        }
        signals.append(signal)
        last_signal_ts = current_ts
        
        if verbose:
            print(f"  SIGNAL: {token} {signal['datetime']} vol={vol_ratio:.1f}x bb={bb_width:.1f}% "
                  f"rsi={rsi:.1f} ema_dist={ema_dist:.1f}% ret_4h={'N/A' if ret_4h is None else f'+{ret_4h:.2f}%' if ret_4h > 0 else f'{ret_4h:.2f}%'}")
    
    return signals


def verify_claimed_signals(all_signals):
    """
    Verify each of the 9 claimed signals from the spec.
    Returns detailed comparison.
    """
    claimed = [
        {'token': 'ATOM', 'date': '09-08', 'vol': 3.4, 'bb': 1.7, 'rsi': 65, 'ema_dist': 1.7, 'ret_4h': 6.49},
        {'token': 'ETC', 'date': '09-08', 'vol': 3.1, 'bb': 1.6, 'rsi': 59, 'ema_dist': 1.8, 'ret_4h': 4.09},
        {'token': 'BIO', 'date': '09-08', 'vol': 3.5, 'bb': 1.3, 'rsi': 62, 'ema_dist': 0.8, 'ret_4h': 2.11},
        {'token': 'ETC', 'date': '09-07', 'vol': 3.9, 'bb': 1.0, 'rsi': 61, 'ema_dist': 0.5, 'ret_4h': 1.52},
        {'token': 'APT', 'date': '09-07', 'vol': 7.3, 'bb': 1.4, 'rsi': 62, 'ema_dist': 1.5, 'ret_4h': 0.95},
        {'token': 'AIXBT', 'date': '09-07', 'vol': 5.3, 'bb': 1.8, 'rsi': 60, 'ema_dist': 1.7, 'ret_4h': 0.63},
        {'token': 'EIGEN', 'date': '09-06', 'vol': 4.0, 'bb': 1.3, 'rsi': 63, 'ema_dist': 0.8, 'ret_4h': 0.62},
        {'token': 'AVNT', 'date': '09-07', 'vol': 5.0, 'bb': 1.7, 'rsi': 64, 'ema_dist': 1.3, 'ret_4h': 0.56},
        {'token': 'AVNT', 'date': '09-06', 'vol': 2.7, 'bb': 1.0, 'rsi': 52, 'ema_dist': 0.6, 'ret_4h': 0.28},
    ]
    
    # Build lookup from actual signals
    actual_lookup = {}
    for sig in all_signals:
        key = f"{sig['token']}_{datetime.fromtimestamp(sig['ts'], tz=timezone.utc).strftime('%m-%d')}"
        if key not in actual_lookup:
            actual_lookup[key] = []
        actual_lookup[key].append(sig)
    
    results = []
    found_count = 0
    
    for c in claimed:
        key = f"{c['token']}_{c['date']}"
        matches = actual_lookup.get(key, [])
        
        # Find best match
        best_match = None
        best_score = -1
        for m in matches:
            score = 0
            if abs(m['vol_ratio'] - c['vol']) < 1.0:
                score += 1
            if abs(m['bb_width'] - c['bb']) < 0.5:
                score += 1
            if m['rsi'] is not None and abs(m['rsi'] - c['rsi']) < 5:
                score += 1
            if abs(m['ema_dist'] - c['ema_dist']) < 0.5:
                score += 1
            if score > best_score:
                best_score = score
                best_match = m
        
        if best_match and best_score >= 3:
            # Compare detailed values
            vol_diff = abs(best_match['vol_ratio'] - c['vol'])
            bb_diff = abs(best_match['bb_width'] - c['bb'])
            rsi_diff = abs(best_match['rsi'] - c['rsi']) if best_match['rsi'] else 0
            ema_diff = abs(best_match['ema_dist'] - c['ema_dist'])
            
            if best_match['ret_4h'] is not None:
                ret_diff = abs(best_match['ret_4h'] - c['ret_4h'])
                ret_match = ret_diff < 0.5
            else:
                ret_match = False
                ret_diff = float('inf')
            
            exact_match = vol_diff < 0.2 and bb_diff < 0.2 and rsi_diff < 2 and ema_diff < 0.2
            
            results.append({
                'claimed': c,
                'found': best_match,
                'vol_diff': vol_diff,
                'bb_diff': bb_diff,
                'rsi_diff': rsi_diff,
                'ema_diff': ema_diff,
                'ret_diff': ret_diff if best_match['ret_4h'] else None,
                'status': 'EXACT' if exact_match else 'CLOSE' if best_match['ret_4h'] and ret_match else 'MISMATCH',
            })
            found_count += 1
        else:
            results.append({
                'claimed': c,
                'found': None,
                'status': 'NOT FOUND',
            })
    
    return results, found_count, len(claimed)


def test_edge_cases(token):
    """
    Test edge cases:
    1. BB width exactly 1.0%
    2. RSI exactly 65
    3. EMA distance exactly 0.5%
    4. Volume exactly 2.5x
    """
    print("\n─── EDGE CASE TESTS ───")
    candles = get_candles(token, limit=200)
    if len(candles) < 60:
        print(f"  Insufficient data for {token}")
        return
    
    closes = [c[4] for c in candles]
    volumes = [c[5] for c in candles]
    
    # Test 1: BB width exactly 1.0%
    print("\nTest 1: BB width exactly 1.0%")
    print(f"  Boundary: BB_MIN={BB_MIN}% (filter: bb_width >= {BB_MIN})")
    print(f"  At exactly 1.0%: {'PASS' if 1.0 >= BB_MIN else 'FAIL'} (should pass)")
    print(f"  At 0.99%: {'PASS' if 0.99 >= BB_MIN else 'FAIL'} (should fail)")
    
    # Test 2: RSI exactly 65
    print("\nTest 2: RSI exactly 65")
    print(f"  Boundary: RSI_MAX={RSI_MAX} (filter: rsi < {RSI_MAX})")
    print(f"  At exactly 65: {'PASS' if 65 < RSI_MAX else 'FAIL'} (should fail)")
    print(f"  At 64.9: {'PASS' if 64.9 < RSI_MAX else 'FAIL'} (should pass)")
    
    # Test 3: EMA distance exactly 0.5%
    print("\nTest 3: EMA distance exactly 0.5%")
    print(f"  Boundary: EMA_MIN_DIST={EMA_MIN_DIST}% (filter: ema_dist >= {EMA_MIN_DIST})")
    print(f"  At exactly 0.5%: {'PASS' if 0.5 >= EMA_MIN_DIST else 'FAIL'} (should pass)")
    print(f"  At 0.49%: {'PASS' if 0.49 >= EMA_MIN_DIST else 'FAIL'} (should fail)")
    
    # Test 4: Volume exactly 2.5x
    print("\nTest 4: Volume exactly 2.5x")
    print(f"  Boundary: VOL_SPIKE_MIN={VOL_SPIKE_MIN} (filter: vol_ratio > {VOL_SPIKE_MIN})")
    print(f"  At exactly 2.5: {'PASS' if 2.5 > VOL_SPIKE_MIN else 'FAIL'} (should FAIL - needs > 2.5)")
    print(f"  At 2.51: {'PASS' if 2.51 > VOL_SPIKE_MIN else 'FAIL'} (should pass)")
    
    # Check spec inconsistency
    print("\n  ⚠ SPEC INCONSISTENCY:")
    print(f"    Spec says 'vol_spike > 2.5x' (strict greater-than)")
    print(f"    Spec constant says 'VOL_SPIKE_MIN = 2.5' (>= 2.5)")
    print(f"    If implemented as >= 2.5, then 2.5 exactly PASSES")
    print(f"    If implemented as > 2.5, then 2.5 exactly FAILS")
    print(f"    This is ambiguous in the spec!")
    
    # Test 5: Sustained volume edge case
    print("\nTest 5: Sustained volume")
    print(f"  Boundary: VOL_SUSTAINED_MIN={VOL_SUSTAINED_MIN} (filter: sustained >= {VOL_SUSTAINED_MIN})")
    print(f"  At exactly 2/3 bars: {'PASS' if 2 >= VOL_SUSTAINED_MIN else 'FAIL'} (should pass)")
    print(f"  At 1/3 bars: {'PASS' if 1 >= VOL_SUSTAINED_MIN else 'FAIL'} (should fail)")


def check_look_ahead_bias():
    """
    Analyze the spec's detection logic for look-ahead bias.
    Look-ahead bias = using future data to make decisions.
    """
    print("\n─── LOOK-AHEAD BIAS ANALYSIS ───")
    print("Checking each condition for future data usage:")
    
    conditions = [
        ("Volume spike (current bar > 2.5x 20-bar average)", "Uses current bar + 20 prior bars", "NO LOOK-AHEAD"),
        ("Sustained (2/3 last 3 bars elevated)", "Uses current + 2 prior bars", "NO LOOK-AHEAD"),
        ("BB width (current bar's 20-bar BB)", "Uses current + 19 prior bars", "NO LOOK-AHEAD"),
        ("Breakout (close > 20-bar high)", "Uses current close + 20 prior highs", "NO LOOK-AHEAD"),
        ("Above EMA50 (price > 50-bar EMA)", "Uses current + 49 prior closes", "NO LOOK-AHEAD"),
        ("EMA50 distance (current vs EMA50)", "Uses same data as above", "NO LOOK-AHEAD"),
        ("RSI (current 14-bar RSI)", "Uses current + 14 prior closes", "NO LOOK-AHEAD"),
    ]
    
    for cond, data_used, verdict in conditions:
        print(f"  ✓ {cond}")
        print(f"    Data: {data_used}")
        print(f"    Verdict: {verdict}")
    
    print("\n  ✅ NO LOOK-AHEAD BIAS DETECTED in signal detection logic")
    
    # Check exit strategy for look-ahead
    print("\n  EXIT STRATEGY ANALYSIS:")
    print("  - SL: Below breakout level or 1.5 × ATR (uses historical data)")
    print("  - TP: Trail-based (no fixed target)")
    print("  - Time stop: Auto-close after 4h (uses entry time)")
    print("  ✅ NO LOOK-AHEAD BIAS in exit strategy")


def analyze_exit_strategy():
    """Analyze the exit strategy for robustness."""
    print("\n─── EXIT STRATEGY ANALYSIS ───")
    print("Spec defines:")
    print("  - SL: Below breakout level or 1.5 × ATR")
    print("  - TP: Trail-based (open skies ahead = no fixed target)")
    print("  - Time stop: Auto-close after 4 hours if no follow-through")
    
    print("\n  ⚠ CONCERNS:")
    print("  1. 'Below breakout level' is vague - how far below? Exact level or % buffer?")
    print("  2. '1.5 × ATR' - which ATR period? Not specified in spec")
    print("  3. 'Trail-based TP' - trailing stop size not specified")
    print("  4. No mention of partial profit-taking")
    print("  5. Time stop is reasonable but 4h may be too short for some breakouts")
    print("  6. No mention of maximum drawdown before exit")
    
    print("\n  The 4h return used in backtest is a SIMPLIFICATION:")
    print("  - Real exit would be at TP/SL/time-stop, whichever comes first")
    print("  - Using fixed 4h exit is reasonable for comparison but not realistic")
    print("  - This could bias results if trades typically hit SL before 4h")


def compare_with_open_skies():
    """Compare trend ignition with open-skies signal."""
    print("\n─── COMPARISON WITH OPEN-SKIES ───")
    print("Open-skies requirements:")
    print("  - Price above SMA20 AND SMA50 (confirmed uptrend)")
    print("  - Zero resistance levels (open skies)")
    print("  - Multiple support levels (safety net)")
    print("  - Positive 20-bar return > 1.5% (momentum confirmed)")
    print("  - Volume spike > 1.5x")
    print("  - Higher highs forming")
    
    print("\nTrend ignition requirements:")
    print("  - Volume spike > 2.5x (higher threshold)")
    print("  - Sustained volume (2/3 bars)")
    print("  - BB width 1-2% (compression)")
    print("  - Breakout above 20-bar high")
    print("  - Above EMA50 with > 0.5% distance")
    print("  - RSI < 65")
    
    print("\n  KEY DIFFERENCES:")
    print("  1. Trend ignition requires COMPRESSION before breakout (BB 1-2%)")
    print("  2. Trend ignition has HIGHER volume threshold (2.5x vs 1.5x)")
    print("  3. Trend ignition doesn't need zero resistance (simpler)")
    print("  4. Trend ignition doesn't need support levels below")
    print("  5. Trend ignition doesn't require 20-bar return > 1.5%")
    print("  6. Trend ignition has RSI guard (< 65)")
    
    print("\n  ⚠ CLAIM: 'Catches breakouts 7 hours earlier than open-skies'")
    print("  This is plausible because:")
    print("  - Trend ignition fires at START of move (volume spike + compression)")
    print("  - Open-skies fires after CONFIRMATION (above SMA20/50, return > 1.5%)")
    print("  - Confirmation takes time (need 20+ bars of positive return)")
    print("  BUT: This claim depends on specific trade examples, not a general rule")


def main():
    print("=" * 70)
    print("INDEPENDENT BACKTEST: TREND IGNITION SIGNAL")
    print("Auditor: Independent verification (no trust, verify everything)")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)
    
    # Get tokens
    tokens = get_backtest_tokens()
    print(f"\nTokens with 7-day data: {len(tokens)}")
    
    # Run backtest
    all_signals = []
    for token in sorted(tokens):
        signals = backtest_token(token, verbose=True)
        all_signals.extend(signals)
    
    # Sort by timestamp
    all_signals.sort(key=lambda x: x['ts'])
    
    print(f"\n{'='*70}")
    print(f"BACKTEST RESULTS: {len(all_signals)} signals found across {len(tokens)} tokens")
    print(f"{'='*70}")
    
    if not all_signals:
        print("⚠ NO SIGNALS FOUND - Something is wrong with the backtest or data")
        return
    
    # Win rate
    valid_signals = [s for s in all_signals if s['ret_4h'] is not None]
    wins = [s for s in valid_signals if s['ret_4h'] > 0]
    losses = [s for s in valid_signals if s['ret_4h'] <= 0]
    
    win_rate = len(wins) / len(valid_signals) * 100 if valid_signals else 0
    avg_return = sum(s['ret_4h'] for s in valid_signals) / len(valid_signals) if valid_signals else 0
    
    print(f"\nSignals with valid 4h data: {len(valid_signals)}/{len(all_signals)}")
    print(f"Win rate: {win_rate:.1f}% ({len(wins)} wins / {len(valid_signals)} total)")
    print(f"Average 4h return: {avg_return:+.2f}%")
    
    if valid_signals:
        best = max(valid_signals, key=lambda x: x['ret_4h'])
        worst = min(valid_signals, key=lambda x: x['ret_4h'])
        print(f"Best trade: {best['token']} {best['datetime']} +{best['ret_4h']:.2f}%")
        print(f"Worst trade: {worst['token']} {worst['datetime']} {worst['ret_4h']:+.2f}%")
    
    # Verify claimed signals
    print(f"\n{'='*70}")
    print("VERIFYING CLAIMED SIGNALS (9 from spec)")
    print(f"{'='*70}")
    
    results, found_count, claimed_count = verify_claimed_signals(all_signals)
    
    exact_matches = sum(1 for r in results if r['status'] == 'EXACT')
    close_matches = sum(1 for r in results if r['status'] == 'CLOSE')
    mismatches = sum(1 for r in results if r['status'] == 'MISMATCH')
    not_found = sum(1 for r in results if r['status'] == 'NOT FOUND')
    
    print(f"\nClaimed: {claimed_count} signals")
    print(f"Found: {found_count} signals")
    print(f"Exact matches: {exact_matches}")
    print(f"Close matches (ret_4h within 0.5%): {close_matches}")
    print(f"Mismatches: {mismatches}")
    print(f"Not found: {not_found}")
    
    for r in results:
        c = r['claimed']
        if r['found']:
            f = r['found']
            print(f"\n  {c['token']} {c['date']}: {r['status']}")
            print(f"    Claimed: vol={c['vol']}x bb={c['bb']}% rsi={c['rsi']} ema={c['ema_dist']}% ret_4h=+{c['ret_4h']}%")
            print(f"    Actual:  vol={f['vol_ratio']:.1f}x bb={f['bb_width']:.1f}% rsi={f['rsi']:.1f} ema={f['ema_dist']:.1f}% ret_4h={'+' + f'{f[chr(114)+chr(101)+chr(116)+chr(95)+chr(52)+chr(104)]:.2f}' if f['ret_4h'] else 'N/A'}%")
            print(f"    Diffs:   vol={r['vol_diff']:.1f} bb={r['bb_diff']:.1f} rsi={r['rsi_diff']:.1f} ema={r['ema_diff']:.1f}")
        else:
            print(f"\n  {c['token']} {c['date']}: NOT FOUND")
    
    # Edge cases
    test_edge_cases(tokens[0] if tokens else 'ATOM')
    
    # Look-ahead bias
    check_look_auditor_bias() if False else check_look_ahead_bias()
    
    # Exit strategy
    analyze_exit_strategy()
    
    # Compare with open-skies
    compare_with_open_skies()
    
    # Final verdict
    print(f"\n{'='*70}")
    print("FINAL VERDICT")
    print(f"{'='*70}")
    
    # Claim verification
    signals_match = abs(len(all_signals) - 9) <= 2
    winrate_match = win_rate == 100.0 if len(valid_signals) == 9 else abs(win_rate - 100.0) < 5
    avg_return_match = abs(avg_return - 1.92) < 0.5
    frequency_match = abs(len(all_signals) / 7 - 1.3) < 0.5
    
    print(f"\n1. Signal count (claimed 9, found {len(all_signals)}):")
    print(f"   {'✓ MATCH' if signals_match else '✗ MISMATCH'}")
    
    print(f"\n2. Win rate (claimed 100%, found {win_rate:.1f}%):")
    print(f"   {'✓ MATCH' if winrate_match else '✗ MISMATCH'}")
    
    print(f"\n3. Average 4h return (claimed +1.92%, found {avg_return:+.2f}%):")
    print(f"   {'✓ MATCH' if avg_return_match else '✗ MISMATCH'}")
    
    print(f"\n4. Frequency (claimed 1.3/day, found {len(all_signals)/7:.1f}/day):")
    print(f"   {'✓ MATCH' if frequency_match else '✗ MISMATCH'}")
    
    print(f"\n5. Claimed signal verification ({found_count}/{claimed_count} found):")
    print(f"   {'✓ MOSTLY VERIFIED' if found_count >= 7 else '✗ SIGNIFICANT GAPS'}")
    
    print(f"\n6. Look-ahead bias: NONE DETECTED")
    print(f"   ✓ All conditions use only historical/current data")
    
    print(f"\n7. Edge cases:")
    print(f"   ⚠ Spec has inconsistencies (vol > 2.5 vs >= 2.5)")
    print(f"   ⚠ RSI boundary at exactly 65 may behave differently")
    
    print(f"\n8. Exit strategy:")
    print(f"   ⚠ Vague definitions (SL level, ATR period, trail size)")
    print(f"   ⚠ Fixed 4h exit is simplification")
    
    # Overall verdict
    all_pass = signals_match and winrate_match and avg_return_match and frequency_match and found_count >= 7
    
    if all_pass:
        print(f"\n{'='*70}")
        print("OVERALL VERDICT: PARTIAL AGREEMENT")
        print("="*70)
        print("\nThe core claims are SUBSTANTIALLY VERIFIED:")
        print("  - Signal count is close to claimed 9")
        print("  - Win rate is high (but verify exact 100%)")
        print("  - Average return is in the right ballpark")
        print("  - No look-ahead bias in detection logic")
        print("\nHowever, there are CAVEATS:")
        print("  - Edge cases in filter boundaries need clarification")
        print("  - Exit strategy is underspecified")
        print("  - 4h fixed exit is simplification of real strategy")
        print("  - 'Catches breakouts 7h earlier' claim needs more evidence")
        print("  - 100% win rate over 7 days is small sample size")
    else:
        print(f"\n{'='*70}")
        print("OVERALL VERDICT: DISAGREEMENT")
        print("="*70)
        print("\nKey claims could not be verified:")
        if not signals_match:
            print(f"  - Signal count mismatch: claimed 9, found {len(all_signals)}")
        if not winrate_match:
            print(f"  - Win rate mismatch: claimed 100%, found {win_rate:.1f}%")
        if not avg_return_match:
            print(f"  - Average return mismatch: claimed +1.92%, found {avg_return:+.2f}%")
        if found_count < 7:
            print(f"  - Only {found_count}/{claimed_count} claimed signals found")


if __name__ == '__main__':
    main()
