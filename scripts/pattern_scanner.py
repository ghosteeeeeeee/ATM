#!/usr/bin/env python3
"""
pattern_scanner.py — Real-time chart pattern detection for Hermes.

Reads 1m OHLCV candles from local SQLite (signal_schema → ohlcv_1m table).
Writes pattern signals to signals DB (signal_type = 'pattern_flag', etc.)
Used as cascade flip confluence only (Phase 1) — not primary entry signals.

Data flow:
  get_ohlcv_1m(token)          ← local SQLite (seeded by price_collector via Binance)
  detect_bull_flag(candles)     ← core detection logic
  detect_bear_flag(candles)     ← mirror for shorts
  write_pattern_signal(...)     ← emits to signals DB
"""

import sys, os, time, json
from datetime import datetime
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import (
    get_ohlcv_1m,
    get_latest_price,
    _get_conn,
    RUNTIME_DB,
)

# ── Pattern Signal Constants ──────────────────────────────────────────────────

FLAG_POLE_MIN_PCT = 3.0       # % move required to count as flag pole
FLAG_POLE_MAX_CANDLES = 8     # max candles for pole formation
FLAG_CONSOLIDATION_MAX_PCT = 1.5  # max % range during flag consolidation
FLAG_CONSOLIDATION_MIN_CANDLES = 3  # min candles in flag
FLAG_BREAKOUT_CONFIRM_PCT = 0.2   # price must exceed pole high by this %

SUPPORT_RESISTANCE_LOOKBACK = 20  # candles for swing high/low detection

# ── Micro-Flag Constants (smaller-scale patterns) ───────────────────────────
# For sideways/low-volatility markets where 3% poles never form on 1m candles
MICRO_POLE_MIN_PCT = 0.3        # % move required (was 3.0%)
MICRO_POLE_MAX_CANDLES = 15     # max candles for pole (was 8)
MICRO_CONSOLIDATION_MAX_PCT = 0.15  # max % range during consolidation (was 1.5%)
MICRO_CONSOLIDATION_MIN_CANDLES = 3
MICRO_BREAKOUT_CONFIRM_PCT = 0.05   # price must exceed pole high by this %
MICRO_COOLDOWN_HOURS = 6       # don't re-signal same token within 6h

# ── Core Detection ──────────────────────────────────────────────────────────

def detect_bull_flag(candles: list) -> dict | None:
    """
    Detect bull flag pattern in 1m OHLCV candle list.
    Returns signal dict or None if no pattern found.

    Bull flag requirements:
    1. Flag pole: >= 3% up-move in <= 8 consecutive candles
    2. Consolidation: 3-5 candles, parallel/down-sloping channel, range < 1.5%
    3. Breakout: candle closes above pole high + volume confirmation
    """
    if len(candles) < FLAG_POLE_MAX_CANDLES + FLAG_CONSOLIDATION_MIN_CANDLES + 2:
        return None

    closes = [c['close'] for c in candles]
    highs  = [c['high']  for c in candles]
    lows   = [c['low']   for c in candles]
    vols   = [c['volume'] for c in candles]

    # ── Step 1: Find flag pole ──────────────────────────────────────────────
    # Look for strongest upward impulse
    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - FLAG_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + FLAG_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[end] - closes[start]) / closes[start] * 100
            if pct >= FLAG_POLE_MIN_PCT and pct > best_pole_pct:
                # Ensure this looks like a clean impulse (no major pullbacks mid-pole)
                segment = closes[start:end+1]
                max_drawdown = max((segment[i] - segment[j]) / segment[j] * 100
                                   for i in range(len(segment)) for j in range(i+1, len(segment)))
                if max_drawdown < pct * 0.3:  # pole shouldn't have >30% drawdown inside it
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(highs[start:end+1]),
                                  'low':  min(lows[start:end+1]),
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_start = best_pole['start']
    pole_end   = best_pole['end']
    pole_high  = best_pole['high']
    pole_open  = best_pole['open_px']

    # ── Step 2: Find consolidation (flag) after pole ──────────────────────
    consolidation_start = pole_end + 1
    consolidation_candles = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < FLAG_CONSOLIDATION_MIN_CANDLES:
            break

        # Try different consolidation windows (3, 4, 5 candles)
        for w in range(FLAG_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100

            if c_range <= FLAG_CONSOLIDATION_MAX_PCT:
                consolidation_candles = candles[consolidation_start + i - consolidation_start:
                                                consolidation_start + i - consolidation_start + w]
                break
        if consolidation_candles:
            break

    if not consolidation_candles:
        return None

    cons_high = max(c['high'] for c in consolidation_candles)
    cons_low  = min(c['low']  for c in consolidation_candles)
    cons_start_idx = candles.index(consolidation_candles[0])
    cons_end_idx   = candles.index(consolidation_candles[-1])

    # ── Step 3: Detect breakout ───────────────────────────────────────────
    # Breakout = candle closes above pole high with volume confirmation
    if cons_end_idx + 1 >= len(candles):
        return None

    breakout_candle = candles[cons_end_idx + 1]
    breakout_close  = breakout_candle['close']
    breakout_vol    = breakout_candle['volume']

    # Volume: should be above average of consolidation volume
    cons_avg_vol = sum(c['volume'] for c in consolidation_candles) / len(consolidation_candles)

    # Breakout price confirmation — requires BOTH price breakout AND volume confirmation
    breakout_exceeds_pole = (breakout_close > pole_high * (1 + FLAG_BREAKOUT_CONFIRM_PCT / 100))
    volume_confirmed = breakout_vol > cons_avg_vol * 0.5  # at least 50% of consolidation avg

    if not breakout_exceeds_pole or not volume_confirmed:
        return None

    # ── Step 4: Calculate confidence ──────────────────────────────────────
    # Pole strength (higher = more reliable)
    pole_score = min(best_pole_pct / 10, 1.0)  # 3% = 0.3, 6% = 0.6, 10% = 1.0

    # Consolidation tightness (tighter = more reliable)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / FLAG_CONSOLIDATION_MAX_PCT)

    # Volume confirmation (higher = more reliable)
    vol_ratio = breakout_vol / cons_avg_vol if cons_avg_vol > 0 else 0
    volume_score = min(vol_ratio / 3, 1.0)  # 3x avg = 1.0, 1.5x = 0.5

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + volume_score * 0.3) * 100
    confidence = round(min(confidence, 95), 1)

    # ── Step 5: Identify pattern details ──────────────────────────────────
    breakout_px = pole_high * (1 + FLAG_BREAKOUT_CONFIRM_PCT / 100)
    measured_move = (cons_low - pole_open) / pole_open * 100  # flag pullback depth
    target = breakout_close * (1 + best_pole_pct / 100)  # pole height projects from breakout

    return {
        'pattern_type': 'bull_flag',
        'direction': 'LONG',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 2),
        'consolidation_candles': len(consolidation_candles),
        'consolidation_range_pct': round(cons_range_pct, 3),
        'breakout_px': round(breakout_px, 6),
        'breakout_vol': round(breakout_vol, 2),
        'volume_ratio': round(vol_ratio, 2),
        'measured_move_pct': round(measured_move, 2),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'pole_high_px': round(pole_high, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


def detect_micro_bull_flag(candles: list) -> dict | None:
    """
    Detect micro bull flag pattern in 1m OHLCV candle list.
    For use in low-volatility / sideways markets where standard 3% flags never form.

    Micro flag requirements:
    1. Flag pole: >= 0.3% up-move in <= 15 consecutive candles
    2. Consolidation: 3-5 candles, range < 0.15%
    3. Breakout: candle closes above pole high + volume confirmation
    """
    if len(candles) < MICRO_POLE_MAX_CANDLES + MICRO_CONSOLIDATION_MIN_CANDLES + 2:
        return None

    closes = [c['close'] for c in candles]
    highs  = [c['high']  for c in candles]
    lows   = [c['low']   for c in candles]
    vols   = [c['volume'] for c in candles]

    # ── Step 1: Find micro flag pole ────────────────────────────────────────
    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - MICRO_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + MICRO_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[end] - closes[start]) / closes[start] * 100
            if pct >= MICRO_POLE_MIN_PCT and pct > best_pole_pct:
                segment = closes[start:end+1]
                max_drawdown = max((segment[i] - segment[j]) / segment[j] * 100
                                   for i in range(len(segment)) for j in range(i+1, len(segment)))
                if max_drawdown < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(highs[start:end+1]),
                                  'low':  min(lows[start:end+1]),
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_start = best_pole['start']
    pole_end   = best_pole['end']
    pole_high  = best_pole['high']
    pole_open  = best_pole['open_px']

    # ── Step 2: Find consolidation after pole ───────────────────────────────
    consolidation_start = pole_end + 1
    consolidation_candles = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < MICRO_CONSOLIDATION_MIN_CANDLES:
            break
        for w in range(MICRO_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100
            if c_range <= MICRO_CONSOLIDATION_MAX_PCT:
                consolidation_candles = candles[consolidation_start + i - consolidation_start:
                                                consolidation_start + i - consolidation_start + w]
                break
        if consolidation_candles:
            break

    if not consolidation_candles:
        return None

    cons_high = max(c['high'] for c in consolidation_candles)
    cons_low  = min(c['low']  for c in consolidation_candles)
    cons_end_idx = candles.index(consolidation_candles[-1])

    # ── Step 3: Detect breakout ──────────────────────────────────────────────
    if cons_end_idx + 1 >= len(candles):
        return None

    breakout_candle = candles[cons_end_idx + 1]
    breakout_close  = breakout_candle['close']
    breakout_vol    = breakout_candle['volume']

    cons_avg_vol = sum(c['volume'] for c in consolidation_candles) / len(consolidation_candles)

    breakout_exceeds_pole = (breakout_close > pole_high * (1 + MICRO_BREAKOUT_CONFIRM_PCT / 100))
    volume_confirmed = breakout_vol > cons_avg_vol * 0.5

    if not breakout_exceeds_pole or not volume_confirmed:
        return None

    # ── Step 4: Calculate confidence ─────────────────────────────────────────
    pole_score = min(best_pole_pct / 1.0, 1.0)   # 0.3% = 0.3, 0.6% = 0.6, 1.0% = 1.0
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / MICRO_CONSOLIDATION_MAX_PCT)
    vol_ratio = breakout_vol / cons_avg_vol if cons_avg_vol > 0 else 0
    volume_score = min(vol_ratio / 3, 1.0)

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + volume_score * 0.3) * 100
    confidence = round(min(confidence, 95), 1)

    # ── Step 5: Pattern details ──────────────────────────────────────────────
    breakout_px = pole_high * (1 + MICRO_BREAKOUT_CONFIRM_PCT / 100)
    measured_move = (cons_low - pole_open) / pole_open * 100
    target = breakout_close * (1 + best_pole_pct / 100)

    return {
        'pattern_type': 'micro_bull_flag',
        'direction': 'LONG',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 3),
        'consolidation_candles': len(consolidation_candles),
        'consolidation_range_pct': round(cons_range_pct, 4),
        'breakout_px': round(breakout_px, 6),
        'breakout_vol': round(breakout_vol, 2),
        'volume_ratio': round(vol_ratio, 2),
        'measured_move_pct': round(measured_move, 3),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'pole_high_px': round(pole_high, 6),
        'signal_type': 'pattern_micro_flag',
        'source': 'pattern_scanner',
    }


def detect_micro_bear_flag(candles: list) -> dict | None:
    """
    Detect micro bear flag — mirror of micro bull flag for shorts.
    Strong DOWN move, small UP consolidation, breakdown below pole low.
    """
    if len(candles) < MICRO_POLE_MAX_CANDLES + MICRO_CONSOLIDATION_MIN_CANDLES + 2:
        return None

    closes = [c['close'] for c in candles]
    highs  = [c['high']  for c in candles]
    lows   = [c['low']   for c in candles]
    vols   = [c['volume'] for c in candles]

    # ── Step 1: Find micro flag pole (downward) ─────────────────────────────
    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - MICRO_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + MICRO_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[start] - closes[end]) / closes[start] * 100  # negative for down
            if pct >= MICRO_POLE_MIN_PCT and pct > best_pole_pct:
                segment = closes[start:end+1]
                max_recovery = max((segment[j] - segment[i]) / segment[i] * 100
                                  for i in range(len(segment)) for j in range(i+1, len(segment)))
                if max_recovery < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(highs[start:end+1]),
                                  'low':  min(lows[start:end+1]),
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_end   = best_pole['end']
    pole_low   = best_pole['low']
    pole_open  = best_pole['open_px']

    # ── Step 2: Find UP consolidation after pole ───────────────────────────
    consolidation_start = pole_end + 1
    consolidation_candles = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < MICRO_CONSOLIDATION_MIN_CANDLES:
            break
        for w in range(MICRO_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100
            if c_range <= MICRO_CONSOLIDATION_MAX_PCT:
                consolidation_candles = candles[consolidation_start + i - consolidation_start:
                                                consolidation_start + i - consolidation_start + w]
                break
        if consolidation_candles:
            break

    if not consolidation_candles:
        return None

    cons_high = max(c['high'] for c in consolidation_candles)
    cons_low  = min(c['low']  for c in consolidation_candles)
    cons_end_idx = candles.index(consolidation_candles[-1])

    # ── Step 3: Detect breakdown ──────────────────────────────────────────────
    if cons_end_idx + 1 >= len(candles):
        return None

    breakdown_candle = candles[cons_end_idx + 1]
    breakdown_close = breakdown_candle['close']
    breakdown_vol   = breakdown_candle['volume']

    cons_avg_vol = sum(c['volume'] for c in consolidation_candles) / len(consolidation_candles)

    breakdown_below_pole = (breakdown_close < pole_low * (1 - MICRO_BREAKOUT_CONFIRM_PCT / 100))
    volume_confirmed = breakdown_vol > cons_avg_vol * 0.5

    if not breakdown_below_pole or not volume_confirmed:
        return None

    # ── Step 4: Calculate confidence ────────────────────────────────────────
    pole_score = min(best_pole_pct / 1.0, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / MICRO_CONSOLIDATION_MAX_PCT)
    vol_ratio = breakdown_vol / cons_avg_vol if cons_avg_vol > 0 else 0
    volume_score = min(vol_ratio / 3, 1.0)

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + volume_score * 0.3) * 100
    confidence = round(min(confidence, 95), 1)

    # ── Step 5: Pattern details ─────────────────────────────────────────────
    breakout_px = pole_low * (1 - MICRO_BREAKOUT_CONFIRM_PCT / 100)
    measured_move = (pole_open - cons_high) / pole_open * 100
    target = breakdown_close * (1 - best_pole_pct / 100)

    return {
        'pattern_type': 'micro_bear_flag',
        'direction': 'SHORT',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 3),
        'consolidation_candles': len(consolidation_candles),
        'consolidation_range_pct': round(cons_range_pct, 4),
        'breakout_px': round(breakout_px, 6),
        'breakout_vol': round(breakdown_vol, 2),
        'volume_ratio': round(vol_ratio, 2),
        'measured_move_pct': round(measured_move, 3),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'pole_low_px': round(pole_low, 6),
        'signal_type': 'pattern_micro_flag',
        'source': 'pattern_scanner',
    }


def detect_bear_flag(candles: list) -> dict | None:
    """
    Detect bear flag pattern in 1m OHLCV candle list.
    Mirror of bull flag — strong DOWN move, then small UP consolidation, breakdown below pole low.
    """
    if len(candles) < FLAG_POLE_MAX_CANDLES + FLAG_CONSOLIDATION_MIN_CANDLES + 2:
        return None

    closes = [c['close'] for c in candles]
    highs  = [c['high']  for c in candles]
    lows   = [c['low']   for c in candles]
    vols   = [c['volume'] for c in candles]

    # ── Step 1: Find bear flag pole (strong down move) ─────────────────────
    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - FLAG_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + FLAG_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[start] - closes[end]) / closes[start] * 100  # negative = down
            if pct >= FLAG_POLE_MIN_PCT and pct > best_pole_pct:
                segment = closes[start:end+1]
                max_drawup = max((segment[j] - segment[i]) / segment[i] * 100
                                 for i in range(len(segment)) for j in range(i+1, len(segment)))
                if max_drawup < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(highs[start:end+1]),
                                  'low':  min(lows[start:end+1]),
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_start = best_pole['start']
    pole_end   = best_pole['end']
    pole_low   = best_pole['low']
    pole_open  = best_pole['open_px']

    # ── Step 2: Find consolidation (flag) after pole ──────────────────────
    consolidation_start = pole_end + 1
    consolidation_candles = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < FLAG_CONSOLIDATION_MIN_CANDLES:
            break

        for w in range(FLAG_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100

            if c_range <= FLAG_CONSOLIDATION_MAX_PCT:
                consolidation_candles = candles[consolidation_start + i - consolidation_start:
                                                consolidation_start + i - consolidation_start + w]
                break
        if consolidation_candles:
            break

    if not consolidation_candles:
        return None

    cons_high = max(c['high'] for c in consolidation_candles)
    cons_low  = min(c['low']  for c in consolidation_candles)
    cons_end_idx = candles.index(consolidation_candles[-1])

    # ── Step 3: Detect breakdown ───────────────────────────────────────────
    if cons_end_idx + 1 >= len(candles):
        return None

    breakdown_candle = candles[cons_end_idx + 1]
    breakdown_close  = breakdown_candle['close']
    breakdown_vol    = breakdown_candle['volume']

    cons_avg_vol = sum(c['volume'] for c in consolidation_candles) / len(consolidation_candles)

    breakdown_below_pole = (breakdown_close < pole_low * (1 - FLAG_BREAKOUT_CONFIRM_PCT / 100))
    volume_confirmed = breakdown_vol > cons_avg_vol * 0.5  # volume must confirm breakdown

    if not breakdown_below_pole or not volume_confirmed:
        return None

    # ── Step 4: Confidence ─────────────────────────────────────────────────
    pole_score = min(best_pole_pct / 10, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / FLAG_CONSOLIDATION_MAX_PCT)
    vol_ratio = breakdown_vol / cons_avg_vol if cons_avg_vol > 0 else 0
    volume_score = min(vol_ratio / 3, 1.0)

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + volume_score * 0.3) * 100
    confidence = round(min(confidence, 95), 1)

    breakout_px = pole_low * (1 - FLAG_BREAKOUT_CONFIRM_PCT / 100)
    measured_move = (pole_open - cons_high) / cons_high * 100
    target = breakdown_close * (1 - best_pole_pct / 100)

    return {
        'pattern_type': 'bear_flag',
        'direction': 'SHORT',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 2),
        'consolidation_candles': len(consolidation_candles),
        'consolidation_range_pct': round(cons_range_pct, 3),
        'breakout_px': round(breakout_px, 6),
        'breakout_vol': round(breakdown_vol, 2),
        'volume_ratio': round(vol_ratio, 2),
        'measured_move_pct': round(measured_move, 2),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'pole_low_px': round(pole_low, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


def detect_ascending_triangle(candles: list) -> dict | None:
    """
    Detect ascending triangle pattern (higher lows + horizontal resistance).
    Common in crypto — often resolves to upside.

    Requirements:
    1. At least 3 higher lows (each low > previous low)
    2. Horizontal resistance (2+ touches at same/similar price)
    3. Breakout above resistance on volume
    """
    if len(candles) < 30:
        return None

    closes = [c['close'] for c in candles]
    lows   = [c['low']   for c in candles]
    highs  = [c['high']  for c in candles]
    vols   = [c['volume'] for c in candles]

    # Find swing lows (local minima)
    swing_lows = []
    for i in range(2, len(candles) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
            swing_lows.append({'idx': i, 'px': lows[i]})

    if len(swing_lows) < 3:
        return None

    # Check for higher lows pattern
    higher_lows = []
    for i in range(1, len(swing_lows)):
        if swing_lows[i]['px'] > swing_lows[i-1]['px']:
            higher_lows.append(swing_lows[i])

    if len(higher_lows) < 2:
        return None

    # Find horizontal resistance (multiple touches at similar price)
    recent_highs = highs[-30:]
    resistance_px = max(recent_highs)
    resistance_touches = sum(1 for h in recent_highs if abs(h - resistance_px) / resistance_px < 0.003)

    if resistance_touches < 2:
        return None

    # Check last candle for breakout
    last_close = closes[-1]
    last_vol   = vols[-1]
    avg_vol    = sum(vols[-30:]) / 30

    breakout = last_close > resistance_px * (1 + 0.001)  # close above resistance
    volume_ok = last_vol > avg_vol * 0.5  # volume must confirm breakout

    if not breakout or not volume_ok:
        return None

    # Confidence based on number of higher lows and resistance touches
    hl_score = min(len(higher_lows) / 4, 1.0)  # 4+ higher lows = 1.0
    res_score = min(resistance_touches / 4, 1.0)  # 4+ touches = 1.0
    vol_score = min((last_vol / avg_vol) / 3, 1.0) if avg_vol > 0 else 0
    confidence = round((hl_score * 0.35 + res_score * 0.35 + vol_score * 0.3) * 100, 1)

    last_low = higher_lows[-1]['px']
    measured_move = (resistance_px - last_low) / last_low * 100
    target = resistance_px + (resistance_px - last_low)

    return {
        'pattern_type': 'ascending_triangle',
        'direction': 'LONG',
        'confidence': confidence,
        'resistance_px': round(resistance_px, 6),
        'support_px': round(last_low, 6),
        'higher_lows_count': len(higher_lows),
        'resistance_touches': resistance_touches,
        'breakout_px': round(last_close, 6),
        'volume_ratio': round(last_vol / avg_vol, 2) if avg_vol > 0 else 0,
        'measured_move_pct': round(measured_move, 2),
        'target_px': round(target, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


def detect_descending_triangle(candles: list) -> dict | None:
    """Mirror of ascending triangle — horizontal support + lower highs → breakdown."""
    if len(candles) < 30:
        return None

    closes = [c['close'] for c in candles]
    lows   = [c['low']   for c in candles]
    highs  = [c['high']  for c in candles]
    vols   = [c['volume'] for c in candles]

    # Find swing highs
    swing_highs = []
    for i in range(2, len(candles) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
            swing_highs.append({'idx': i, 'px': highs[i]})

    if len(swing_highs) < 3:
        return None

    # Check for lower highs
    lower_highs = []
    for i in range(1, len(swing_highs)):
        if swing_highs[i]['px'] < swing_highs[i-1]['px']:
            lower_highs.append(swing_highs[i])

    if len(lower_highs) < 2:
        return None

    # Horizontal support
    recent_lows = lows[-30:]
    support_px = min(recent_lows)
    support_touches = sum(1 for l in recent_lows if abs(l - support_px) / support_px < 0.003)

    if support_touches < 2:
        return None

    last_close = closes[-1]
    last_vol   = vols[-1]
    avg_vol    = sum(vols[-30:]) / 30

    breakdown = last_close < support_px * (1 - 0.001)
    volume_ok = last_vol > avg_vol * 0.5  # volume must confirm breakdown

    if not breakdown or not volume_ok:
        return None

    lh_score = min(len(lower_highs) / 4, 1.0)
    sup_score = min(support_touches / 4, 1.0)
    vol_score = min((last_vol / avg_vol) / 3, 1.0) if avg_vol > 0 else 0
    confidence = round((lh_score * 0.35 + sup_score * 0.35 + vol_score * 0.3) * 100, 1)

    last_high = lower_highs[-1]['px']
    measured_move = (last_high - support_px) / support_px * 100
    target = support_px - (last_high - support_px)

    return {
        'pattern_type': 'descending_triangle',
        'direction': 'SHORT',
        'confidence': confidence,
        'support_px': round(support_px, 6),
        'resistance_px': round(last_high, 6),
        'lower_highs_count': len(lower_highs),
        'support_touches': support_touches,
        'breakout_px': round(last_close, 6),
        'volume_ratio': round(last_vol / avg_vol, 2) if avg_vol > 0 else 0,
        'measured_move_pct': round(measured_move, 2),
        'target_px': round(target, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


# ── Write Pattern Signal to DB ───────────────────────────────────────────────

def write_pattern_signal(token: str, pattern: dict) -> bool:
    """Write a pattern signal to the signals DB."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # ISO format — matches SQLite datetime() comparisons in expiry
    try:
        conn = _get_conn(RUNTIME_DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO signals (
                token, direction, signal_type, source, confidence,
                price, exchange, timeframe, decision,
                z_score, momentum_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            token.upper(),
            pattern['direction'],
            pattern['signal_type'],
            pattern['source'],
            pattern['confidence'],
            pattern.get('breakout_px', 0),
            'hyperliquid',
            '1m',
            'PENDING',
            None, None, now
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'[pattern_scanner] write_pattern_signal error: {e}')
        return False


# ── Scan Token ───────────────────────────────────────────────────────────────

def scan_token(token: str, lookback_minutes: int = 240) -> list:
    """
    Run all pattern detectors on a token's candle data.
    Returns list of detected patterns (may be empty).
    """
    candles = get_ohlcv_1m(token, lookback_minutes=lookback_minutes)
    if not candles or len(candles) < 20:
        return []

    patterns = []

    # Bull flag
    bull = detect_bull_flag(candles)
    if bull:
        bull['token'] = token.upper()
        patterns.append(bull)

    # Bear flag
    bear = detect_bear_flag(candles)
    if bear:
        bear['token'] = token.upper()
        patterns.append(bear)

    # Ascending triangle
    asc = detect_ascending_triangle(candles)
    if asc:
        asc['token'] = token.upper()
        patterns.append(asc)

    # Descending triangle
    desc = detect_descending_triangle(candles)
    if desc:
        desc['token'] = token.upper()
        patterns.append(desc)

    # Micro bull flag (smaller-scale for low-volatility markets)
    micro_bull = detect_micro_bull_flag(candles)
    if micro_bull:
        micro_bull['token'] = token.upper()
        patterns.append(micro_bull)

    # Micro bear flag
    micro_bear = detect_micro_bear_flag(candles)
    if micro_bear:
        micro_bear['token'] = token.upper()
        patterns.append(micro_bear)

    return patterns


def scan_and_write(token: str, lookback_minutes: int = 240) -> list:
    """
    Scan a token for patterns and write any detected signals to DB.
    Returns list of patterns found.
    """
    patterns = scan_token(token, lookback_minutes=lookback_minutes)
    for p in patterns:
        write_pattern_signal(token, p)
        print(f"[pattern_scanner] {token} {p['pattern_type']} {p['direction']} "
              f"conf={p['confidence']}% breakout=${p.get('breakout_px', p.get('resistance_px', 0)):.4f}")
    return patterns


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys as _sys

    if len(_sys.argv) < 2:
        print("Usage: python3 pattern_scanner.py <TOKEN> [lookback_minutes]")
        print("Example: python3 pattern_scanner.py IMX 240")
        _sys.exit(1)

    token = _sys.argv[1]
    lookback = int(_sys.argv[2]) if len(_sys.argv) > 2 else 240

    patterns = scan_and_write(token, lookback_minutes=lookback)
    if not patterns:
        print(f'[pattern_scanner] No patterns found for {token}')
    else:
        print(f'[pattern_scanner] {token}: {len(patterns)} pattern(s) detected')