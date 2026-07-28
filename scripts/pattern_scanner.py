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

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

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
FLAG_BREAKOUT_CONFIRM_PCT = 0.2   # price must exceed pole high by this %

SUPPORT_RESISTANCE_LOOKBACK = 20  # candles for swing high/low detection

# ── Micro-Flag Constants (smaller-scale patterns) ───────────────────────────
MICRO_POLE_MIN_PCT = 0.3        # % move required (was 3.0%)
MICRO_POLE_MAX_CANDLES = 15     # max candles for pole (was 8)
MICRO_CONSOLIDATION_MAX_PCT = 0.15  # max % range during consolidation (was 1.5%)
MICRO_CONSOLIDATION_MIN_CANDLES = 3
MICRO_BREAKOUT_CONFIRM_PCT = 0.05   # price must exceed pole high by this %
MICRO_COOLDOWN_HOURS = 6       # don't re-signal same token within 6h

# ── ATR-based confirmation (replaces volume) ───────────────────────────────
# HL doesn't provide volume — use ATR expansion + price velocity as breakout confirmation
BREAKOUT_ATR_K_MIN = 0.5       # breakout candle must move >= 0.5 * ATR
VELOCITY_MIN_PCT = 0.1         # breakout must have >= 0.1% velocity in last 5 bars

# Cooldown cache
_COOLDOWN_CACHE = {}  # {token_pattern: last_fire_ts}

# ── Core Detection ──────────────────────────────────────────────────────────

def detect_bull_flag(candles: list) -> dict | None:
    """
    Detect bull flag pattern in 1m price list.
    Returns signal dict or None if no pattern found.

    Bull flag requirements:
    1. Flag pole: >= 3% up-move in <= 8 consecutive candles
    2. Consolidation: 3-5 candles, range < 1.5%
    3. Breakout: candle closes above pole high + ATR confirmation
    """
    if len(candles) < FLAG_POLE_MAX_CANDLES + FLAG_CONSOLIDATION_MIN_CANDLES + 2:
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
                segment = closes[start:end+1]
                max_drawdown = max((segment[i] - segment[j]) / segment[j] * 100
                                   for i in range(len(segment)) for j in range(i+1, len(segment)))
                if max_drawdown < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(closes[start:end+1]),
                                  'low':  min(closes[start:end+1]),
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
                    best_pole_pct = pct

    if not best_pole:
        return None

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

        for w in range(FLAG_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100

            if c_range <= FLAG_CONSOLIDATION_MAX_PCT:
                consolidation_candles = closes[consolidation_start + i - consolidation_start:
                                                consolidation_start + i - consolidation_start + w]
                break
        if consolidation_candles:
            break

    if not consolidation_candles:
        return None

    cons_high = max(consolidation_candles)
    cons_low  = min(consolidation_candles)
    cons_end_idx = consolidation_start + len(consolidation_candles) - 1

    # ── Step 3: Detect breakout ───────────────────────────────────────────
    if cons_end_idx + 1 >= len(closes):
        return None

    breakout_close = closes[cons_end_idx + 1]
    breakout_pct = (breakout_close - pole_high) / pole_high * 100

    # Breakout confirmation: price exceeds pole high + ATR/velocity check
    breakout_price_ok = breakout_close > pole_high * (1 + FLAG_BREAKOUT_CONFIRM_PCT / 100)
    breakout_atr_ok = atr > 0 and breakout_pct >= (atr / pole_high * 100) * BREAKOUT_ATR_K_MIN
    velocity = _price_velocity(closes, window=5)
    breakout_velocity_ok = velocity >= VELOCITY_MIN_PCT

    if not breakout_price_ok or not (breakout_atr_ok or breakout_velocity_ok):
        return None

    # ── Step 4: Calculate confidence ──────────────────────────────────────
    pole_score = min(best_pole_pct / 10, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / FLAG_CONSOLIDATION_MAX_PCT)
    velocity_score = min(abs(velocity) / 0.5, 1.0)

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + velocity_score * 0.3) * 100
    confidence = round(min(confidence, 95), 1)

    target = breakout_close * (1 + best_pole_pct / 100)

    return {
        'pattern_type': 'bull_flag',
        'direction': 'LONG',
        'confidence': confidence,
        'pole_pct': round(best_pole_pct, 2),
        'consolidation_candles': len(consolidation_candles),
        'consolidation_range_pct': round(cons_range_pct, 3),
        'breakout_px': round(breakout_close, 6),
        'velocity': round(velocity, 3),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'signal_type': 'pattern_flag',
        'source': 'pattern_scanner',
    }


def detect_micro_bull_flag(candles: list) -> dict | None:
    """Detect micro bull flag — 0.3%+ pole for low-vol markets. No volume checks."""
    if len(candles) < MICRO_POLE_MAX_CANDLES + MICRO_CONSOLIDATION_MIN_CANDLES + 2:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

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
                                  'high': max(closes[start:end+1]),
                                  'low':  min(closes[start:end+1]),
                                  'open_px': closes[start],
                                  'close_px': closes[end]}
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
                consolidation_closes = closes[consolidation_start + i - consolidation_start:
                                               consolidation_start + i - consolidation_start + w]
                break
        if consolidation_closes:
            break

    if not consolidation_closes:
        return None

    cons_high = max(consolidation_closes)
    cons_low  = min(consolidation_closes)
    cons_end_idx = consolidation_start + len(consolidation_closes) - 1

    if cons_end_idx + 1 >= len(closes):
        return None

    breakout_close = closes[cons_end_idx + 1]
    breakout_pct = (breakout_close - pole_high) / pole_high * 100

    breakout_price_ok = breakout_close > pole_high * (1 + MICRO_BREAKOUT_CONFIRM_PCT / 100)
    velocity = _price_velocity(closes, window=5)
    breakout_velocity_ok = velocity >= VELOCITY_MIN_PCT

    if not breakout_price_ok or not breakout_velocity_ok:
        return None

    pole_score = min(best_pole_pct / 1.0, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / MICRO_CONSOLIDATION_MAX_PCT)
    velocity_score = min(abs(velocity) / 0.3, 1.0)

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + velocity_score * 0.3) * 100
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
        'velocity': round(velocity, 3),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'signal_type': 'pattern_micro_flag',
        'source': 'pattern_scanner',
    }


def detect_micro_bear_flag(candles: list) -> dict | None:
    """Detect micro bear flag — mirror of micro bull flag for shorts."""
    if len(candles) < MICRO_POLE_MAX_CANDLES + MICRO_CONSOLIDATION_MIN_CANDLES + 2:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - MICRO_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + MICRO_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[start] - closes[end]) / closes[start] * 100
            if pct >= MICRO_POLE_MIN_PCT and pct > best_pole_pct:
                segment = closes[start:end+1]
                max_recovery = max((segment[j] - segment[i]) / segment[i] * 100
                                  for i in range(len(segment)) for j in range(i+1, len(segment)))
                if max_recovery < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(closes[start:end+1]),
                                  'low':  min(closes[start:end+1]),
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
        if len(remaining) < MICRO_CONSOLIDATION_MIN_CANDLES:
            break
        for w in range(MICRO_CONSOLIDATION_MIN_CANDLES, min(6, len(remaining))):
            window = remaining[:w]
            c_range = (max(window) - min(window)) / min(window) * 100
            if c_range <= MICRO_CONSOLIDATION_MAX_PCT:
                consolidation_closes = closes[consolidation_start + i - consolidation_start:
                                               consolidation_start + i - consolidation_start + w]
                break
        if consolidation_closes:
            break

    if not consolidation_closes:
        return None

    cons_high = max(consolidation_closes)
    cons_low  = min(consolidation_closes)
    cons_end_idx = consolidation_start + len(consolidation_closes) - 1

    if cons_end_idx + 1 >= len(closes):
        return None

    breakdown_close = closes[cons_end_idx + 1]
    breakdown_pct = (pole_low - breakdown_close) / pole_low * 100

    breakdown_price_ok = breakdown_close < pole_low * (1 - MICRO_BREAKOUT_CONFIRM_PCT / 100)
    velocity = _price_velocity(closes, window=5)
    breakdown_velocity_ok = velocity <= -VELOCITY_MIN_PCT

    if not breakdown_price_ok or not breakdown_velocity_ok:
        return None

    pole_score = min(best_pole_pct / 1.0, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / MICRO_CONSOLIDATION_MAX_PCT)
    velocity_score = min(abs(velocity) / 0.3, 1.0)

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + velocity_score * 0.3) * 100
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
        'velocity': round(velocity, 3),
        'target_px': round(target, 6),
        'cons_support': round(cons_low, 6),
        'cons_resistance': round(cons_high, 6),
        'signal_type': 'pattern_micro_flag',
        'source': 'pattern_scanner',
    }


def detect_bear_flag(candles: list) -> dict | None:
    """Detect bear flag — strong DOWN move, small UP consolidation, breakdown below pole low."""
    if len(candles) < FLAG_POLE_MAX_CANDLES + FLAG_CONSOLIDATION_MIN_CANDLES + 2:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr_1m(closes)

    best_pole = None
    best_pole_pct = 0

    for start in range(len(closes) - FLAG_POLE_MAX_CANDLES):
        for end in range(start + 2, min(start + FLAG_POLE_MAX_CANDLES + 1, len(closes))):
            pct = (closes[start] - closes[end]) / closes[start] * 100
            if pct >= FLAG_POLE_MIN_PCT and pct > best_pole_pct:
                segment = closes[start:end+1]
                max_recovery = max((segment[j] - segment[i]) / segment[i] * 100
                                  for i in range(len(segment)) for j in range(i+1, len(segment)))
                if max_recovery < pct * 0.3:
                    best_pole = {'start': start, 'end': end, 'pct': pct,
                                  'high': max(closes[start:end+1]),
                                  'low':  min(closes[start:end+1]),
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
                consolidation_closes = closes[consolidation_start + i - consolidation_start:
                                               consolidation_start + i - consolidation_start + w]
                break
        if consolidation_closes:
            break

    if not consolidation_closes:
        return None

    cons_high = max(consolidation_closes)
    cons_low  = min(consolidation_closes)
    cons_end_idx = consolidation_start + len(consolidation_closes) - 1

    if cons_end_idx + 1 >= len(closes):
        return None

    breakdown_close = closes[cons_end_idx + 1]
    breakdown_pct = (pole_low - breakdown_close) / pole_low * 100

    breakdown_price_ok = breakdown_close < pole_low * (1 - FLAG_BREAKOUT_CONFIRM_PCT / 100)
    breakdown_atr_ok = atr > 0 and breakdown_pct >= (atr / pole_low * 100) * BREAKOUT_ATR_K_MIN
    velocity = _price_velocity(closes, window=5)
    breakdown_velocity_ok = velocity <= -VELOCITY_MIN_PCT

    if not breakdown_price_ok or not (breakdown_atr_ok or breakdown_velocity_ok):
        return None

    pole_score = min(best_pole_pct / 10, 1.0)
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    consolidation_score = 1.0 - (cons_range_pct / FLAG_CONSOLIDATION_MAX_PCT)
    velocity_score = min(abs(velocity) / 0.5, 1.0)

    confidence = (pole_score * 0.4 + consolidation_score * 0.3 + velocity_score * 0.3) * 100
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
        'velocity': round(velocity, 3),
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
        result = add_signal(
            token=token.upper(),
            direction=pattern['direction'].upper(),
            signal_type=pattern['signal_type'],
            source=pattern['source'],
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


# ── Scan Token ───────────────────────────────────────────────────────────────

def scan_token(token: str, lookback_minutes: int = 240) -> list:
    """Run all enabled pattern detectors on a token. Returns list of detected patterns."""
    from hermes_constants import (
        PATTERN_FLAG_ENABLED, PATTERN_TRIANGLE_ENABLED,
        PATTERN_WOLF_ENABLED, PATTERN_MICRO_FLAG_ENABLED,
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