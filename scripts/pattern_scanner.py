#!/usr/bin/env python3
"""
pattern_scanner.py — Real-time chart pattern detection for Hermes.

Data source: price_history (signals_hermes.db) — live 1m close prices.
No volume data from HL — uses ATR + price velocity as confirmation instead.

Patterns detected:
  - Bull/Bear flag (standard + micro)
  - Ascending/Descending triangle
  - Wolf wave (5-point reversal pattern)

Toggle patterns via PATTERN_*_ENABLED in hermes_constants.py.
"""

import sys, os, time, json, sqlite3
from datetime import datetime
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import add_signal
from paths import STATIC_DB

_PRICE_DB = STATIC_DB

def _get_candles_1m(token: str, lookback_minutes: int = 120) -> list:
    """Fetch 1m close prices from price_history, oldest first."""
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback_minutes))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []

        return [
            {'open_time': r[0], 'open': r[1], 'high': r[1],
             'low': r[1], 'close': r[1], 'volume': 0.0}
            for r in rows
        ]
    except Exception:
        return []


def _atr_1m(closes: list, period: int = 14) -> float:
    """ATR from 1m close prices (approximated as avg absolute bar-to-bar change)."""
    if len(closes) < period + 1:
        return 0.0
    changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    if not changes:
        return 0.0
    atr = sum(changes[:period]) / period
    for c in changes[period:]:
        atr = (atr * (period - 1) + c) / period
    return atr


def _price_velocity(closes: list, window: int = 5) -> float:
    """Price velocity: % change over last `window` candles. Positive = up, negative = down."""
    if len(closes) < window or closes[-window] == 0:
        return 0.0
    return (closes[-1] - closes[-window]) / closes[-window] * 100

# ── Pattern Signal Constants ──────────────────────────────────────────────────

FLAG_POLE_MIN_PCT = 3.0       # % move required to count as flag pole
FLAG_POLE_MAX_CANDLES = 8     # max candles for pole formation
FLAG_CONSOLIDATION_MAX_PCT = 1.5  # max % range during flag consolidation
FLAG_CONSOLIDATION_MIN_CANDLES = 3  # min candles in flag
FLAG_CONSOLIDATION_MAX_SLOPE = 0.0  # max consolidation slope (% per candle) — 0 = flat/down only

SUPPORT_RESISTANCE_LOOKBACK = 20  # candles for swing high/low detection

# ── Micro-Flag Constants (smaller-scale patterns) ───────────────────────────
MICRO_POLE_MIN_PCT = 0.3        # % move required (was 3.0%)
MICRO_POLE_MAX_CANDLES = 15     # max candles for pole (was 8)
MICRO_CONSOLIDATION_MAX_PCT = 0.15  # max % range during consolidation (was 1.5%)
MICRO_CONSOLIDATION_MIN_CANDLES = 3
MICRO_CONSOLIDATION_MAX_SLOPE = 0.0  # max consolidation slope
MICRO_COOLDOWN_HOURS = 6       # don't re-signal same token within 6h

# ── Breakout confirmation (replaces old volume + single-candle check) ────────
BREAKOUT_ATR_K_MIN = 0.5       # breakout candle must move >= 0.5 * ATR
BREAKOUT_FOLLOWTHROUGH_MIN = 3 # need 3+ candles closing beyond pole level
VELOCITY_MIN_PCT = 0.1         # breakout must have >= 0.1% velocity in last 5 bars

# Cooldown cache
_COOLDOWN_CACHE = {}  # {token_pattern: last_fire_ts}

# ── Core Detection ──────────────────────────────────────────────────────────

def detect_bull_flag(candles: list) -> dict | None:
    """
    Detect bull flag pattern in 1m price list.

    Bull flag requirements:
    1. Flag pole: >= 3% up-move in <= 8 candles, clean impulse (<30% drawdown from peak)
    2. Consolidation: 3-5 candles, range < 1.5%, flat or downward slope
    3. Breakout: 3+ candles closing above pole high, with ATR or velocity confirmation
    """
    if len(candles) < FLAG_POLE_MAX_CANDLES + FLAG_CONSOLIDATION_MIN_CANDLES + 3:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    # ── Step 1: Find flag pole ──────────────────────────────────────────────
    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - FLAG_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + FLAG_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[end] - closes[start]) / closes[start] * 100
            if pct >= FLAG_POLE_MIN_PCT and pct > best_pole_pct:
                # Clean impulse: max drawdown from PEAK within pole body (excluding peak) < 30% of pole
                body = closes[start:end]  # exclude the end point (peak)
                peak = closes[end]
                max_drawdown = max((peak - s) / peak * 100 for s in body) if body else 0
                if max_drawdown < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': peak,
                                  'low':  min(closes[start:end+1]),
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_end   = best_pole['end']
    pole_high  = best_pole['high']

    # ── Step 2: Find consolidation (flag) after pole ──────────────────────
    consolidation_start = pole_end + 1
    consolidation_closes = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < FLAG_CONSOLIDATION_MIN_CANDLES:
            break

        for w in range(FLAG_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100

            if c_range <= FLAG_CONSOLIDATION_MAX_PCT:
                # Check slope: consolidation should be flat or downward (bull flag)
                if w >= 2:
                    cons_slope = (window[-1] - window[0]) / window[0] * 100 / (w - 1)
                    if cons_slope > FLAG_CONSOLIDATION_MAX_SLOPE:
                        continue  # upward slope = not a bull flag
                consolidation_closes = list(window)
                break
        if consolidation_closes:
            break

    if not consolidation_closes:
        return None

    cons_high = max(consolidation_closes)
    cons_low  = min(consolidation_closes)
    cons_end_idx = consolidation_start + len(consolidation_closes) - 1

    # ── Step 3: Detect breakout with follow-through ────────────────────────
    # Need 3+ candles closing above pole high
    follow_count = 0
    breakout_strength = 0.0
    for i in range(cons_end_idx + 1, min(cons_end_idx + 1 + FLAG_POLE_MAX_CANDLES, len(closes))):
        if closes[i] > pole_high:
            follow_count += 1
            breakout_strength = max(breakout_strength, (closes[i] - pole_high) / atr if atr > 0 else 0)

    if follow_count < BREAKOUT_FOLLOWTHROUGH_MIN:
        return None

    # ATR or velocity confirmation on breakout zone
    breakout_close = closes[cons_end_idx + 1]
    breakout_pct = (breakout_close - pole_high) / pole_high * 100
    breakout_atr_ok = atr > 0 and breakout_pct >= (atr / pole_high * 100) * BREAKOUT_ATR_K_MIN

    # Local velocity: last 5 candles of breakout zone (not global)
    breakout_zone = closes[cons_end_idx + 1:cons_end_idx + 6]
    if len(breakout_zone) >= 5:
        local_velocity = (breakout_zone[-1] - breakout_zone[0]) / breakout_zone[0] * 100
    else:
        local_velocity = _price_velocity(closes, window=5)
    breakout_velocity_ok = local_velocity >= VELOCITY_MIN_PCT

    if not (breakout_atr_ok or breakout_velocity_ok):
        return None

    # ── Step 4: Calculate confidence ──────────────────────────────────────
    pole_score = min(best_pole_pct / 10, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / FLAG_CONSOLIDATION_MAX_PCT)
    follow_score = min(follow_count / 5, 1.0)

    confidence = (pole_score * 0.3 + consolidation_score * 0.3 + follow_score * 0.4) * 100
    confidence = round(min(confidence, 95), 1)

    target = breakout_close * (1 + best_pole_pct / 100)

    return {
        'pattern_type': 'bull_flag',
        'direction': 'LONG',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 2),
        'consolidation_candles': len(consolidation_closes),
        'consolidation_range_pct': round(cons_range_pct, 3),
        'breakout_px': round(breakout_close, 6),
        'follow_count': follow_count,
        'breakout_strength_atr': round(breakout_strength, 2),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


def detect_micro_bull_flag(candles: list) -> dict | None:
    """Detect micro bull flag — 0.3%+ pole for low-vol markets. Follow-through required."""
    if len(candles) < MICRO_POLE_MAX_CANDLES + MICRO_CONSOLIDATION_MIN_CANDLES + 3:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - MICRO_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + MICRO_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[end] - closes[start]) / closes[start] * 100
            if pct >= MICRO_POLE_MIN_PCT and pct > best_pole_pct:
                body = closes[start:end]  # exclude the end point (peak)
                peak = max(body) if body else closes[start]
                max_drawdown = max((peak - s) / peak * 100 for s in body) if body else 0
                if max_drawdown < max(pct * 0.5, 0.15):
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': closes[end], 'low': min(closes[start:end+1]),
                                  'open_px': closes[start], 'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_end   = best_pole['end']
    pole_high  = best_pole['high']

    consolidation_start = pole_end + 1
    consolidation_closes = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < MICRO_CONSOLIDATION_MIN_CANDLES:
            break
        for w in range(MICRO_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100
            if c_range <= MICRO_CONSOLIDATION_MAX_PCT:
                if w >= 2:
                    cons_slope = (window[-1] - window[0]) / window[0] * 100 / (w - 1)
                    if cons_slope > MICRO_CONSOLIDATION_MAX_SLOPE:
                        continue
                consolidation_closes = list(window)
                break
        if consolidation_closes:
            break

    if not consolidation_closes:
        return None

    cons_high = max(consolidation_closes)
    cons_low  = min(consolidation_closes)
    cons_end_idx = consolidation_start + len(consolidation_closes) - 1

    # Follow-through: 3+ candles above pole high
    follow_count = 0
    for i in range(cons_end_idx + 1, min(cons_end_idx + 1 + MICRO_POLE_MAX_CANDLES, len(closes))):
        if closes[i] > pole_high:
            follow_count += 1

    if follow_count < BREAKOUT_FOLLOWTHROUGH_MIN:
        return None

    breakout_close = closes[cons_end_idx + 1]
    local_velocity = _price_velocity(closes[cons_end_idx + 1:cons_end_idx + 6], window=min(5, max(2, len(closes) - cons_end_idx - 1))) if len(closes) > cons_end_idx + 1 else 0

    pole_score = min(best_pole_pct / 1.0, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / MICRO_CONSOLIDATION_MAX_PCT)
    follow_score = min(follow_count / 5, 1.0)

    confidence = (pole_score * 0.3 + consolidation_score * 0.3 + follow_score * 0.4) * 100
    confidence = round(min(confidence, 95), 1)

    target = breakout_close * (1 + best_pole_pct / 100)

    return {
        'pattern_type': 'micro_bull_flag',
        'direction': 'LONG',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 3),
        'consolidation_candles': len(consolidation_closes),
        'consolidation_range_pct': round(cons_range_pct, 4),
        'breakout_px': round(breakout_close, 6),
        'follow_count': follow_count,
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'signal_type': 'pattern_micro_flag',
        'source': 'pattern_scanner',
    }


def detect_micro_bear_flag(candles: list) -> dict | None:
    """Detect micro bear flag — mirror of micro bull flag for shorts."""
    if len(candles) < MICRO_POLE_MAX_CANDLES + MICRO_CONSOLIDATION_MIN_CANDLES + 3:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - MICRO_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + MICRO_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[start] - closes[end]) / closes[start] * 100
            if pct >= MICRO_POLE_MIN_PCT and pct > best_pole_pct:
                body = closes[start+1:end+1]  # exclude the start point (peak)
                trough = min(body)
                max_recovery = max((s - trough) / trough * 100 for s in body)
                if max_recovery < max(pct * 0.5, 0.15):
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(closes[start:end+1]), 'low': trough,
                                  'open_px': closes[start], 'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_end   = best_pole['end']
    pole_low   = best_pole['low']

    consolidation_start = pole_end + 1
    consolidation_closes = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < MICRO_CONSOLIDATION_MIN_CANDLES:
            break
        for w in range(MICRO_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100
            if c_range <= MICRO_CONSOLIDATION_MAX_PCT:
                if w >= 2:
                    cons_slope = (window[-1] - window[0]) / window[0] * 100 / (w - 1)
                    if cons_slope < -MICRO_CONSOLIDATION_MAX_SLOPE:
                        continue
                consolidation_closes = list(window)
                break
        if consolidation_closes:
            break

    if not consolidation_closes:
        return None

    cons_high = max(consolidation_closes)
    cons_low  = min(consolidation_closes)
    cons_end_idx = consolidation_start + len(consolidation_closes) - 1

    # Follow-through: 3+ candles below pole low
    follow_count = 0
    for i in range(cons_end_idx + 1, min(cons_end_idx + 1 + MICRO_POLE_MAX_CANDLES, len(closes))):
        if closes[i] < pole_low:
            follow_count += 1

    if follow_count < BREAKOUT_FOLLOWTHROUGH_MIN:
        return None

    breakdown_close = closes[cons_end_idx + 1]
    local_velocity = _price_velocity(closes[cons_end_idx + 1:cons_end_idx + 6], window=min(5, max(2, len(closes) - cons_end_idx - 1))) if len(closes) > cons_end_idx + 1 else 0

    pole_score = min(best_pole_pct / 1.0, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / MICRO_CONSOLIDATION_MAX_PCT)
    follow_score = min(follow_count / 5, 1.0)

    confidence = (pole_score * 0.3 + consolidation_score * 0.3 + follow_score * 0.4) * 100
    confidence = round(min(confidence, 95), 1)

    target = breakdown_close * (1 - best_pole_pct / 100)

    return {
        'pattern_type': 'micro_bear_flag',
        'direction': 'SHORT',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 3),
        'consolidation_candles': len(consolidation_closes),
        'consolidation_range_pct': round(cons_range_pct, 4),
        'breakdown_px': round(breakdown_close, 6),
        'follow_count': follow_count,
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'signal_type': 'pattern_micro_flag',
        'source': 'pattern_scanner',
    }


def detect_bear_flag(candles: list) -> dict | None:
    """Detect bear flag — strong DOWN move, flat/up consolidation, breakdown with follow-through."""
    if len(candles) < FLAG_POLE_MAX_CANDLES + FLAG_CONSOLIDATION_MIN_CANDLES + 3:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - FLAG_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + FLAG_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[start] - closes[end]) / closes[start] * 100
            if pct >= FLAG_POLE_MIN_PCT and pct > best_pole_pct:
                body = closes[start+1:end+1]  # exclude the start point (peak)
                trough = min(body) if body else closes[end]
                max_recovery = max((s - trough) / trough * 100 for s in body) if body else 0
                if max_recovery < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(closes[start:end+1]),
                                  'low':  trough,
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

    pole_end   = best_pole['end']
    pole_low   = best_pole['low']

    consolidation_start = pole_end + 1
    consolidation_closes = []

    for i in range(consolidation_start, len(closes)):
        remaining = closes[i:]
        if len(remaining) < FLAG_CONSOLIDATION_MIN_CANDLES:
            break
        for w in range(FLAG_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100
            if c_range <= FLAG_CONSOLIDATION_MAX_PCT:
                # Check slope: consolidation should be flat or upward (bear flag)
                if w >= 2:
                    cons_slope = (window[-1] - window[0]) / window[0] * 100 / (w - 1)
                    if cons_slope < -FLAG_CONSOLIDATION_MAX_SLOPE:
                        continue  # downward slope = not a bear flag
                consolidation_closes = list(window)
                break
        if consolidation_closes:
            break

    if not consolidation_closes:
        return None

    cons_high = max(consolidation_closes)
    cons_low  = min(consolidation_closes)
    cons_end_idx = consolidation_start + len(consolidation_closes) - 1

    # Need 3+ candles closing below pole low
    follow_count = 0
    breakout_strength = 0.0
    for i in range(cons_end_idx + 1, min(cons_end_idx + 1 + FLAG_POLE_MAX_CANDLES, len(closes))):
        if closes[i] < pole_low:
            follow_count += 1
            breakout_strength = max(breakout_strength, (pole_low - closes[i]) / atr if atr > 0 else 0)

    if follow_count < BREAKOUT_FOLLOWTHROUGH_MIN:
        return None

    breakdown_close = closes[cons_end_idx + 1]
    breakdown_pct = (pole_low - breakdown_close) / pole_low * 100
    breakdown_atr_ok = atr > 0 and breakdown_pct >= (atr / pole_low * 100) * BREAKOUT_ATR_K_MIN

    breakout_zone = closes[cons_end_idx + 1:cons_end_idx + 6]
    if len(breakout_zone) >= 5:
        local_velocity = (breakout_zone[0] - breakout_zone[-1]) / breakout_zone[-1] * 100
    else:
        local_velocity = _price_velocity(closes, window=5)
    breakdown_velocity_ok = local_velocity >= VELOCITY_MIN_PCT

    if not (breakdown_atr_ok or breakdown_velocity_ok):
        return None

    pole_score = min(best_pole_pct / 10, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / FLAG_CONSOLIDATION_MAX_PCT)
    follow_score = min(follow_count / 5, 1.0)

    confidence = (pole_score * 0.3 + consolidation_score * 0.3 + follow_score * 0.4) * 100
    confidence = round(min(confidence, 95), 1)

    target = breakdown_close * (1 - best_pole_pct / 100)

    return {
        'pattern_type': 'bear_flag',
        'direction': 'SHORT',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 2),
        'consolidation_candles': len(consolidation_closes),
        'consolidation_range_pct': round(cons_range_pct, 3),
        'breakdown_px': round(breakdown_close, 6),
        'follow_count': follow_count,
        'breakout_strength_atr': round(breakout_strength, 2),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


def detect_ascending_triangle(candles: list) -> dict | None:
    """Detect ascending triangle — higher lows + horizontal resistance. No volume checks."""
    if len(candles) < 30:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    # Find swing lows (local minima)
    swing_lows = []
    for i in range(2, len(candles) - 2):
        if closes[i] < closes[i-1] and closes[i] < closes[i+1] and closes[i] < closes[i-2] and closes[i] < closes[i+2]:
            swing_lows.append({'idx': i, 'px': closes[i]})

    if len(swing_lows) < 3:
        return None

    higher_lows = []
    for i in range(1, len(swing_lows)):
        if swing_lows[i]['px'] > swing_lows[i-1]['px']:
            higher_lows.append(swing_lows[i])

    if len(higher_lows) < 2:
        return None

    # Horizontal resistance (multiple touches at similar price)
    resistance_px = max(closes[-30:])
    resistance_touches = sum(1 for c in closes[-30:] if abs(c - resistance_px) / resistance_px < 0.003)

    if resistance_touches < 2:
        return None

    last_close = closes[-1]
    breakout = last_close > resistance_px * (1 + 0.001)
    velocity = _price_velocity(closes, window=5)

    if not breakout or velocity < VELOCITY_MIN_PCT:
        return None

    hl_score = min(len(higher_lows) / 4, 1.0)
    res_score = min(resistance_touches / 4, 1.0)
    velocity_score = min(abs(velocity) / 0.5, 1.0)
    confidence = round((hl_score * 0.35 + res_score * 0.35 + velocity_score * 0.3) * 100, 1)

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
        'velocity': round(velocity, 3),
        'target_px': round(target, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


def detect_descending_triangle(candles: list) -> dict | None:
    """Mirror of ascending triangle — horizontal support + lower highs → breakdown."""
    if len(candles) < 30:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    swing_highs = []
    for i in range(2, len(candles) - 2):
        if closes[i] > closes[i-1] and closes[i] > closes[i+1] and closes[i] > closes[i-2] and closes[i] > closes[i+2]:
            swing_highs.append({'idx': i, 'px': closes[i]})

    if len(swing_highs) < 3:
        return None

    lower_highs = []
    for i in range(1, len(swing_highs)):
        if swing_highs[i]['px'] < swing_highs[i-1]['px']:
            lower_highs.append(swing_highs[i])

    if len(lower_highs) < 2:
        return None

    support_px = min(closes[-30:])
    support_touches = sum(1 for c in closes[-30:] if abs(c - support_px) / support_px < 0.003)

    if support_touches < 2:
        return None

    last_close = closes[-1]
    breakdown = last_close < support_px * (1 - 0.001)
    velocity = _price_velocity(closes, window=5)

    if not breakdown or velocity > -VELOCITY_MIN_PCT:
        return None

    lh_score = min(len(lower_highs) / 4, 1.0)
    sup_score = min(support_touches / 4, 1.0)
    velocity_score = min(abs(velocity) / 0.5, 1.0)
    confidence = round((lh_score * 0.35 + sup_score * 0.35 + velocity_score * 0.3) * 100, 1)

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
        'breakdown_px': round(last_close, 6),
        'velocity': round(velocity, 3),
        'target_px': round(target, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


# ── Wolf Wave Detection ──────────────────────────────────────────────────────

def detect_wolf_wave(closes: list, atr: float = 0.0) -> dict | None:
    """
    Detect wolf wave pattern — 5-point reversal structure.

    Wolf wave structure:
      Point 1: Start of the wave
      Point 2: First peak/trough after 1
      Point 3: Pullback from 2 (opposite direction of 1→2)
      Point 4: Extension beyond 3 (continuation of 1→2 trend)
      Point 5: Final point where reversal begins

    The pattern predicts a reversal when price reaches the "nose line"
    (line connecting points 1 and 4).

    For bullish wolf wave (reversal UP):
      1→2 is DOWN, 2→3 is UP, 3→4 is DOWN, 4→5 is UP
      Points 1-3-5 form lower lows, 2-4 form lower highs (descending wedge)
      Target: line connecting 1→4 extrapolated forward

    For bearish wolf wave (reversal DOWN):
      Mirror — ascending wedge, reversal DOWN

    Uses 1m close prices. Requires at least 60 candles.
    """
    if len(closes) < 60 or atr <= 0:
        return None

    n = len(closes)

    # Find swing points (local extremes with 5-bar buffer)
    swing_highs = []
    swing_lows = []
    for i in range(5, n - 5):
        if all(closes[i] > closes[i-j] for j in range(1, 6)) and all(closes[i] > closes[i+j] for j in range(1, 6)):
            swing_highs.append((i, closes[i]))
        if all(closes[i] < closes[i-j] for j in range(1, 6)) and all(closes[i] < closes[i+j] for j in range(1, 6)):
            swing_lows.append((i, closes[i]))

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return None

    # Try bullish wolf wave: descending wedge (lower lows + lower highs)
    # Nose line connects P1 and P3 (the two lows) — price approaches from above
    best_bull = None
    for li in range(len(swing_lows) - 1):
        for hi in range(len(swing_highs) - 1):
            p1_idx, p1_px = swing_lows[li]       # start (low)
            p2_idx, p2_px = swing_highs[hi]      # first high
            p3_idx, p3_px = swing_lows[li + 1]   # second low (lower than p1)
            p4_idx, p4_px = swing_highs[hi + 1]  # second high (lower than p2)

            # Must be in order: 1 < 2 < 3 < 4
            if not (p1_idx < p2_idx < p3_idx < p4_idx):
                continue

            # Descending wedge: p3 < p1 and p4 < p2
            if not (p3_px < p1_px and p4_px < p2_px):
                continue

            # p3 should be close to p1 (within 5% of price) — not too far apart
            if abs(p3_px - p1_px) / p1_px > 0.05:
                continue

            # Nose line: line through P1 and P3 (the two lows)
            # Price approaches this line from above in a descending wedge
            nose_slope = (p3_px - p1_px) / (p3_idx - p1_idx) if p3_idx != p1_idx else 0
            nose_at_current = p1_px + nose_slope * (n - 1 - p1_idx)

            # Current price should be near or below nose line (reversal zone for LONG)
            current_px = closes[-1]
            dist_to_nose = (current_px - nose_at_current) / atr if atr > 0 else 0  # negative = price below nose

            # Only signal if price is within 1.5 ATR of nose line (approaching reversal)
            if dist_to_nose > 0.5 or dist_to_nose < -1.5:
                continue

            # Confidence based on pattern quality
            wedge_quality = min(abs(p1_px - p3_px) / atr, 2.0) / 2.0  # tighter wedge = better
            convergence = 1.0 - abs(p4_px - p3_px) / max(abs(p2_px - p1_px), 0.0001)  # lines converging
            convergence = max(0, min(1, convergence))
            confidence = (wedge_quality * 0.4 + convergence * 0.6) * 80 + 15
            confidence = round(min(confidence, 90), 1)

            # Target: projected from nose line
            target = nose_at_current * 1.02  # 2% above nose line for LONG

            if best_bull is None or confidence > best_bull['confidence']:
                best_bull = {
                    'pattern_type': 'wolf_wave_bull',
                    'direction': 'LONG',
                    'confidence': confidence,
                    'p1_px': round(p1_px, 6), 'p2_px': round(p2_px, 6),
                    'p3_px': round(p3_px, 6), 'p4_px': round(p4_px, 6),
                    'nose_line_px': round(nose_at_current, 6),
                    'dist_to_nose_atr': round(dist_to_nose, 2),
                    'target_px': round(target, 6),
                    'signal_type': 'pattern_wolf',
                    'source': 'pattern_scanner',
                }

    # Try bearish wolf wave: ascending wedge (higher highs + higher lows)
    # Nose line connects P1 and P3 (the two highs) — price approaches from below
    best_bear = None
    for hi in range(len(swing_highs) - 1):
        for li in range(len(swing_lows) - 1):
            p1_idx, p1_px = swing_highs[hi]      # start (high)
            p2_idx, p2_px = swing_lows[li]        # first low
            p3_idx, p3_px = swing_highs[hi + 1]   # second high (higher than p1)
            p4_idx, p4_px = swing_lows[li + 1]    # second low (higher than p2)

            if not (p1_idx < p2_idx < p3_idx < p4_idx):
                continue

            # Ascending wedge: p3 > p1 and p4 > p2
            if not (p3_px > p1_px and p4_px > p2_px):
                continue

            if abs(p3_px - p1_px) / p1_px > 0.05:
                continue

            # Nose line: line through P1 and P3 (the two highs)
            # Price approaches this line from below in an ascending wedge
            nose_slope = (p3_px - p1_px) / (p3_idx - p1_idx) if p3_idx != p1_idx else 0
            nose_at_current = p1_px + nose_slope * (n - 1 - p1_idx)

            current_px = closes[-1]
            dist_to_nose = (current_px - nose_at_current) / atr if atr > 0 else 0  # negative = price below nose

            if dist_to_nose > 1.5 or dist_to_nose < -0.5:
                continue

            wedge_quality = min(abs(p3_px - p1_px) / atr, 2.0) / 2.0
            convergence = 1.0 - abs(p4_px - p3_px) / max(abs(p2_px - p1_px), 0.0001)
            convergence = max(0, min(1, convergence))
            confidence = (wedge_quality * 0.4 + convergence * 0.6) * 80 + 15
            confidence = round(min(confidence, 90), 1)

            target = nose_at_current * 0.98  # 2% below nose line for SHORT

            if best_bear is None or confidence > best_bear['confidence']:
                best_bear = {
                    'pattern_type': 'wolf_wave_bear',
                    'direction': 'SHORT',
                    'confidence': confidence,
                    'p1_px': round(p1_px, 6), 'p2_px': round(p2_px, 6),
                    'p3_px': round(p3_px, 6), 'p4_px': round(p4_px, 6),
                    'nose_line_px': round(nose_at_current, 6),
                    'dist_to_nose_atr': round(dist_to_nose, 2),
                    'target_px': round(target, 6),
                    'signal_type': 'pattern_wolf',
                    'source': 'pattern_scanner',
                }

    # Return whichever has higher confidence
    if best_bull and best_bear:
        return best_bull if best_bull['confidence'] >= best_bear['confidence'] else best_bear
    return best_bull or best_bear


# ── Write Pattern Signal to DB ───────────────────────────────────────────────

def write_pattern_signal(token: str, pattern: dict) -> bool:
    """Write a pattern signal to the signals DB via add_signal().
    add_signal() applies directional blacklist guards — SHORT_BLACKLIST/LONG_BLACKLIST.
    Returns True only if signal was actually written to DB."""
    try:
        # Include pattern type in source for tracking which patterns work
        pattern_source = f"pattern_{pattern['pattern_type']}"
        result = add_signal(
            token=token.upper(),
            direction=pattern['direction'].upper(),
            signal_type=pattern['signal_type'],
            source=pattern_source,
            confidence=pattern['confidence'],
            value=pattern.get('breakout_px', pattern.get('nose_line_px', pattern.get('resistance_px', 0))),
            price=pattern.get('breakout_px', pattern.get('nose_line_px', pattern.get('resistance_px', 0))),
        )
        wrote_ok = result is not None
        if wrote_ok:
            print(f'[pattern_scanner] {token} {pattern["pattern_type"]} '
                  f'{pattern["direction"]} conf={pattern["confidence"]}% '
                  f'px=${pattern.get("breakout_px", pattern.get("nose_line_px", pattern.get("resistance_px", 0))):.4f}')
        else:
            print(f'[pattern_scanner] {token} BLOCKED (blacklist)')
        return wrote_ok
    except Exception as e:
        print(f'[pattern_scanner] write_pattern_signal error: {e}')
        return False


# ── Linear Regression Helpers ────────────────────────────────────────────────

def _linear_regression(closes: list):
    """Linear regression. Returns (slope, intercept, r2)."""
    n = len(closes)
    if n < 2:
        return 0.0, sum(closes) / n if closes else 0.0, 0.0
    sum_x = sum(range(n))
    sum_y = sum(closes)
    sum_xy = sum(i * c for i, c in enumerate(closes))
    sum_x2 = sum(i * i for i in range(n))
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 0.0, sum_y / n, 0.0
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    mean_y = sum_y / n
    ss_tot = sum((y - mean_y) ** 2 for y in closes)
    ss_res = sum((closes[i] - (intercept + slope * i)) ** 2 for i in range(n))
    r2 = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    return slope, intercept, r2


def _atr_from_closes(closes: list, period: int = 14) -> float:
    """ATR from close prices only (no OHLCV)."""
    if len(closes) < period + 1:
        return 0.0
    changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    if not changes:
        return 0.0
    atr = sum(changes[:period]) / period
    for c in changes[period:]:
        atr = (atr * (period - 1) + c) / period
    return atr


def _ema(closes: list, period: int) -> list:
    """Compute EMA series. Returns list with None for indices < period-1."""
    if len(closes) < period:
        return [None] * len(closes)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(closes[:period]) / period
    result.append(ema_val)
    for price in closes[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


# ── Channel Flag Detection (improved) ─────────────────────────────────────

# Channel flag constants
CH_FLAG_LOOKBACK       = 200    # 1m candles for channel detection
CH_FLAG_POLE_MIN_ATR   = 1.5   # pole must be >= 1.5 * ATR
CH_FLAG_POLE_MAX_BARS  = 30    # max bars for pole formation
CH_FLAG_CONS_MIN_BARS  = 5     # min consolidation bars
CH_FLAG_CONS_MAX_BARS  = 60    # max consolidation bars
CH_FLAG_R2_MIN         = 0.3   # minimum R² for channel boundaries
CH_FLAG_SQUEEZE_RATIO  = 0.85  # ATR must decline to 85% of pole ATR
CH_FLAG_BREAKOUT_ATR_K = 0.3   # breakout must be 0.3*ATR beyond channel
CH_FLAG_SURVIVAL_BARS  = 5     # post-breakout survival bars
CH_FLAG_COOLDOWN_HOURS = 4


def detect_channel_flag(closes: list, token: str = '') -> dict | None:
    """Detect channel-based flag with linear regression boundaries.

    Improvements over basic flag:
    1. Uses linear regression to fit channel boundaries (upper/lower)
    2. ATR-normalized thresholds (works across tokens/timeframes)
    3. Validates decreasing volatility (squeeze) during consolidation
    4. Breakout confirmation with survival zone
    5. Bounce count on channel boundary (like tl_break)

    Args:
        closes: list of float prices, oldest first
        token: token symbol for logging

    Returns:
        Signal dict or None.
    """
    if len(closes) < CH_FLAG_LOOKBACK:
        return None

    atr = _atr_from_closes(closes, 14)
    if atr <= 0:
        return None

    # ── Phase 1: Find the best pole (impulse move) ──────────────────────
    # Scan for the strongest directional move in the first 70% of the window
    search_end = int(len(closes) * 0.70)
    best_pole = None
    best_pole_score = 0

    for start in range(max(0, search_end - CH_FLAG_POLE_MAX_BARS * 3), search_end - 5):
        for end in range(start + 3, min(start + CH_FLAG_POLE_MAX_BARS + 1, search_end)):
            # Bull flag: upward pole
            up_pct = (closes[end] - closes[start]) / closes[start] * 100
            up_atr = (closes[end] - closes[start]) / atr if atr > 0 else 0

            if up_atr >= CH_FLAG_POLE_MIN_ATR:
                # Check pole cleanliness: drawdown from peak (exclude start)
                body = closes[start+1:end]
                if body:
                    peak = max(closes[start:end+1])
                    max_dd = max((peak - s) / atr for s in body) if atr > 0 else 0
                    if max_dd < up_atr * 0.4:  # clean impulse
                        score = up_atr * (1.0 - max_dd / max(up_atr, 0.01))
                        if score > best_pole_score:
                            best_pole = {'start': start, 'end': end, 'direction': 'LONG',
                                         'pct': up_pct, 'atr_moves': up_atr,
                                         'high': closes[end], 'low': closes[start]}
                            best_pole_score = score

            # Bear flag: downward pole
            down_pct = (closes[start] - closes[end]) / closes[start] * 100
            down_atr = (closes[start] - closes[end]) / atr if atr > 0 else 0

            if down_atr >= CH_FLAG_POLE_MIN_ATR:
                body = closes[start+1:end]
                if body:
                    trough = min(closes[start:end+1])
                    max_recovery = max((s - trough) / atr for s in body) if atr > 0 else 0
                    if max_recovery < down_atr * 0.4:
                        score = down_atr * (1.0 - max_recovery / max(down_atr, 0.01))
                        if score > best_pole_score:
                            best_pole = {'start': start, 'end': end, 'direction': 'SHORT',
                                         'pct': down_pct, 'atr_moves': down_atr,
                                         'high': closes[start], 'low': closes[end]}
                            best_pole_score = score

    if not best_pole:
        return None

    pole_end = best_pole['end']
    pole_direction = best_pole['direction']

    # ── Phase 2: Fit channel to consolidation zone ──────────────────────
    cons_start = pole_end + 1
    cons_end_min = cons_start + CH_FLAG_CONS_MIN_BARS
    cons_end_max = min(cons_start + CH_FLAG_CONS_MAX_BARS, len(closes))

    if cons_end_max < cons_end_min:
        return None

    # Find the best consolidation window (highest R² for channel fit)
    best_channel = None
    best_channel_score = 0

    for ce in range(cons_end_min, cons_end_max):
        cons_closes = closes[cons_start:ce]
        if len(cons_closes) < CH_FLAG_CONS_MIN_BARS:
            continue

        # Linear regression on consolidation
        slope, intercept, r2 = _linear_regression(cons_closes)

        if r2 < CH_FLAG_R2_MIN:
            continue

        # Check channel width: all points within 1.5 * ATR of regression line
        max_dev = 0
        for j, px in enumerate(cons_closes):
            line_px = slope * j + intercept
            dev = abs(px - line_px) / atr if atr > 0 else 0
            max_dev = max(max_dev, dev)

        if max_dev > 1.5:
            continue

        # Check slope: should be counter-trend (flat or opposing pole)
        avg_price = sum(cons_closes) / len(cons_closes)
        slope_pct_per_bar = abs(slope) / avg_price if avg_price > 0 else 0

        if pole_direction == 'LONG':
            # Bull flag: consolidation should slope down or flat
            if slope > slope_pct_per_bar * avg_price * 0.5:
                continue
        else:
            # Bear flag: consolidation should slope up or flat
            if slope < -slope_pct_per_bar * avg_price * 0.5:
                continue

        # Check for decreasing volatility (squeeze)
        pole_atr = _atr_from_closes(closes[max(0, pole_end - 20):pole_end + 1], 14)
        cons_atr = _atr_from_closes(cons_closes, 14)
        squeeze_ok = cons_atr < pole_atr * CH_FLAG_SQUEEZE_RATIO if pole_atr > 0 else True

        # Score: higher R² + tighter channel + squeeze = better
        score = r2 * 0.4 + (1.0 - max_dev / 1.5) * 0.3 + (0.3 if squeeze_ok else 0) * 0.3

        if score > best_channel_score:
            best_channel = {
                'start': cons_start, 'end': ce,
                'slope': slope, 'intercept': intercept, 'r2': r2,
                'max_dev': max_dev, 'squeeze_ok': squeeze_ok,
                'cons_atr': cons_atr, 'pole_atr': pole_atr,
            }
            best_channel_score = score

    if not best_channel:
        return None

    cons_end = best_channel['end']

    # ── Phase 3: Bounce validation on channel boundary ─────────────────
    channel_closes = closes[best_channel['start']:cons_end]
    bounce_count = 0

    for j in range(1, len(channel_closes) - 1):
        line_px = best_channel['slope'] * j + best_channel['intercept']
        dist = abs(channel_closes[j] - line_px) / atr if atr > 0 else 0

        if dist < 0.5:  # within 0.5 ATR of channel midline
            # Check rejection: next candle moves away
            next_line = best_channel['slope'] * (j + 1) + best_channel['intercept']
            next_dist = abs(channel_closes[j + 1] - next_line) / atr if atr > 0 else 0
            if next_dist > dist + 0.2:  # moved away = rejection
                bounce_count += 1

    if bounce_count < 2:
        return None

    # ── Phase 4: Breakout confirmation ──────────────────────────────────
    breakout_start = cons_end
    breakout_end = min(cons_end + 15, len(closes))

    if breakout_end <= breakout_start + 2:
        return None

    breakout_thresh = atr * CH_FLAG_BREAKOUT_ATR_K
    follow_count = 0
    breakout_strength = 0.0

    # Extrapolate channel line to breakout zone
    for i in range(breakout_start, breakout_end):
        j = i - best_channel['start']  # index relative to channel start
        channel_line = best_channel['slope'] * j + best_channel['intercept']
        price = closes[i]

        if pole_direction == 'LONG':
            if price > channel_line + breakout_thresh:
                follow_count += 1
                breakout_strength = max(breakout_strength, (price - channel_line) / atr)
        else:
            if price < channel_line - breakout_thresh:
                follow_count += 1
                breakout_strength = max(breakout_strength, (channel_line - price) / atr)

    if follow_count < 3:
        return None

    # ── Phase 5: Survival zone (fakeout guard) ──────────────────────────
    survival_start = breakout_end
    survival_end = min(survival_start + CH_FLAG_SURVIVAL_BARS, len(closes))

    fakeouts = 0
    for i in range(survival_start, survival_end):
        j = i - best_channel['start']
        channel_line = best_channel['slope'] * j + best_channel['intercept']
        price = closes[i]
        buffer = atr * 0.15

        if pole_direction == 'LONG':
            if price < channel_line - buffer:
                fakeouts += 1
        else:
            if price > channel_line + buffer:
                fakeouts += 1

    if fakeouts > 0:
        return None  # fakeout detected

    # ── Confidence scoring ──────────────────────────────────────────────
    conf = 55

    # Pole strength
    conf += min(15, int(best_pole['atr_moves'] - CH_FLAG_POLE_MIN_ATR) * 3)

    # Channel quality (R²)
    conf += min(10, int((best_channel['r2'] - CH_FLAG_R2_MIN) * 20))

    # Squeeze bonus
    if best_channel['squeeze_ok']:
        conf += 5

    # Bounce count
    conf += min(5, bounce_count - 2)

    # Breakout strength
    conf += min(5, int(breakout_strength * 3))

    # Follow-through
    conf += min(5, follow_count - 3)

    conf = min(conf, 90)

    # ── Build signal ────────────────────────────────────────────────────
    last_cons_price = closes[cons_end - 1] if cons_end > 0 else closes[-1]
    target = best_pole['high'] if pole_direction == 'LONG' else best_pole['low']
    measured_move = abs(target - last_cons_price) / atr if atr > 0 else 1.0

    signal_type = f'pattern_channel_{pole_direction.lower()}'

    return {
        'pattern_type': f'channel_{pole_direction.lower()}',
        'direction': pole_direction,
        'confidence': conf,
        'pole_pct': round(best_pole['pct'], 2),
        'pole_atr_moves': round(best_pole['atr_moves'], 2),
        'channel_r2': round(best_channel['r2'], 3),
        'channel_max_dev_atr': round(best_channel['max_dev'], 2),
        'squeeze_ok': best_channel['squeeze_ok'],
        'bounce_count': bounce_count,
        'follow_count': follow_count,
        'breakout_strength_atr': round(breakout_strength, 2),
        'consolidation_bars': cons_end - cons_start,
        'target_px': round(target, 6),
        'measured_move_atr': round(measured_move, 2),
        'signal_type': signal_type,
        'source': 'pattern_scanner',
    }


# ── Scan Token ───────────────────────────────────────────────────────────────

def scan_token(token: str, lookback_minutes: int = 240) -> list:
    """Run all enabled pattern detectors on a token. Returns list of detected patterns."""
    from hermes_constants import (
        PATTERN_FLAG_ENABLED, PATTERN_TRIANGLE_ENABLED,
        PATTERN_WOLF_ENABLED, PATTERN_MICRO_FLAG_ENABLED,
        PATTERN_CHANNEL_ENABLED,
    )

    candles = _get_candles_1m(token, lookback_minutes=lookback_minutes)
    if not candles or len(candles) < 20:
        return []

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)
    now = time.time()
    patterns = []

    def _check_cooldown(key: str, hours: float = 6) -> bool:
        last = _COOLDOWN_CACHE.get(key, 0)
        return (now - last) < hours * 3600

    def _add(p: dict):
        key = f'{token}_{p["pattern_type"]}'
        if _check_cooldown(key):
            return
        p['token'] = token.upper()
        patterns.append(p)
        _COOLDOWN_CACHE[key] = now

    if PATTERN_FLAG_ENABLED:
        bull = detect_bull_flag(candles)
        if bull:
            _add(bull)
        bear = detect_bear_flag(candles)
        if bear:
            _add(bear)

    if PATTERN_MICRO_FLAG_ENABLED:
        micro_bull = detect_micro_bull_flag(candles)
        if micro_bull:
            _add(micro_bull)
        micro_bear = detect_micro_bear_flag(candles)
        if micro_bear:
            _add(micro_bear)

    if PATTERN_TRIANGLE_ENABLED:
        asc = detect_ascending_triangle(candles)
        if asc:
            _add(asc)
        desc = detect_descending_triangle(candles)
        if desc:
            _add(desc)

    if PATTERN_WOLF_ENABLED:
        wolf = detect_wolf_wave(closes, atr)
        if wolf:
            _add(wolf)

    # Channel-based flags (improved detection)
    if PATTERN_CHANNEL_ENABLED:
        channel = detect_channel_flag(closes, token)
        if channel:
            _add(channel)

    return patterns


def scan_and_write(token: str, lookback_minutes: int = 240) -> list:
    """
    Scan a token for patterns and write any detected signals to DB.
    Returns list of patterns written (not blocked by SHORT_BLACKLIST/LONG_BLACKLIST).
    """
    patterns = scan_token(token, lookback_minutes=lookback_minutes)
    written = []
    for p in patterns:
        if write_pattern_signal(token, p):
            written.append(p)
    return written


# ── Signals Registry Interface ────────────────────────────────────────────────

def run(prices_dict: dict) -> tuple[int, list]:
    """Entry point for signals/__init__.py registry. Scans all tokens for patterns."""
    added = 0
    signaled_tokens = []
    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue
        written = scan_and_write(token, lookback_minutes=240)
        if written:
            added += len(written)
            signaled_tokens.append(token)
    return added, signaled_tokens


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