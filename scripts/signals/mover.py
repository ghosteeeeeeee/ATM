#!/usr/bin/env python3
"""
mover.py — Fast Mover Signal v2.

Trend-following signal that catches coins in strong directional moves.
Avoids entering at peaks (LONG) or valleys (SHORT) — waits for pullbacks
within the trend for better R:R entries.

Signal types:
  - mover_long  : LONG (upward trend, not overextended)
  - mover_short : SHORT (downward trend, not oversold)

Thesis: Fast movers attract more capital (momentum begets momentum).
Key: Catch the move early, avoid chasing at extremes.
"""

import os
import sys
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA
from entry_gates import volume_gate, candle_close_gate, session_timing_gate

from hermes_constants import (
    MOVER_ENABLED,
    MOVER_PLUS_ENABLED,
    MOVER_MINUS_ENABLED,
    MOVER_TOP_N,
    MOVER_VELOCITY_MIN,
    MOVER_VELOCITY_WINDOW,
    MOVER_VOLUME_RATIO,
    MOVER_CONF_BASE,
    MOVER_CONF_CAP,
    MOVER_COOLDOWN_HOURS,
    MOVER_ACCEL_MIN,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'mover_long'
SIGNAL_TYPE_SHORT = 'mover_short'
SOURCE_LONG = 'mover+'
SOURCE_SHORT = 'mover-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[mover] {msg}", flush=True)


def _get_candles(token, table='candles_5m', limit=100):
    """Fetch OHLCV candles. Returns list of {ts, open, high, low, close, volume} oldest-first."""
    _VALID_TABLES = {'candles_1m', 'candles_5m', 'candles_15m', 'candles_1h'}
    if table not in _VALID_TABLES:
        return []
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume FROM {table}
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        if not rows or len(rows) < 10:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]}
                for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_closes(token, table='candles_5m', limit=100):
    """Fetch close prices only. Returns list oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT close FROM {table}
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def compute_velocity(closes, window=None):
    """Compute velocity (% price change per candle) over recent window.

    Returns (velocity_pct, direction) where direction is 'LONG' or 'SHORT'.
    Returns (0, None) if insufficient data.
    """
    if window is None:
        window = MOVER_VELOCITY_WINDOW
    if len(closes) < window + 1:
        return 0, None

    start_price = closes[-(window + 1)]
    end_price = closes[-1]

    if start_price == 0:
        return 0, None

    velocity_pct = (end_price - start_price) / start_price * 100
    direction = 'LONG' if velocity_pct > 0 else 'SHORT'

    return velocity_pct, direction


def compute_velocity_acceleration(closes, short_window=None, long_window=None):
    """Compute velocity acceleration (short-term velocity vs long-term velocity).

    Positive = accelerating upward, negative = accelerating downward.
    Returns acceleration_pct (difference in velocities).
    """
    if short_window is None:
        short_window = max(MOVER_VELOCITY_WINDOW // 3, 3)
    if long_window is None:
        long_window = MOVER_VELOCITY_WINDOW

    if len(closes) < long_window + 1:
        return 0

    # Long-term velocity
    long_start = closes[-(long_window + 1)]
    long_end = closes[-1]
    if long_start == 0:
        return 0
    long_vel = (long_end - long_start) / long_start * 100

    # Short-term velocity (last short_window candles)
    short_start = closes[-(short_window + 1)]
    short_end = closes[-1]
    if short_start == 0:
        return 0
    short_vel = (short_end - short_start) / short_start * 100

    # Acceleration = short-term velocity normalized to long-term
    # Positive means short-term is faster than long-term (accelerating)
    if abs(long_vel) < 0.001:
        return short_vel  # long-term flat, just use short-term
    return short_vel - long_vel * (short_window / long_window)


def compute_rsi(closes, period=14):
    """Compute RSI. Returns value 0-100."""
    if len(closes) < period + 1:
        return 50  # neutral default

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_bb_position(closes, period=20, stddev=2.0):
    """Compute position within Bollinger Bands (0 = lower band, 1 = upper band).

    Returns value 0-1 (can exceed if price outside bands).
    """
    if len(closes) < period:
        return 0.5  # neutral

    window = closes[-period:]
    sma = sum(window) / period
    variance = sum((x - sma) ** 2 for x in window) / period
    std = variance ** 0.5

    if std == 0:
        return 0.5

    upper = sma + stddev * std
    lower = sma - stddev * std
    price = closes[-1]

    if upper == lower:
        return 0.5
    return (price - lower) / (upper - lower)


def is_near_recent_extreme(closes, direction, lookback=20, proximity_pct=None):
    """Check if price is near recent high (LONG) or low (SHORT).

    For trend following: avoid entering at peaks/valleys.
    Returns True if too close to extreme (should NOT enter).
    """
    if proximity_pct is None:
        proximity_pct = MOVER_PROXIMITY_PCT

    if len(closes) < lookback:
        return False

    recent = closes[-lookback:]
    current = closes[-1]

    if direction == 'LONG':
        # Don't buy near recent high — wait for pullback
        recent_high = max(recent)
        if recent_high == 0:
            return False
        dist_to_high = (recent_high - current) / recent_high * 100
        return dist_to_high < proximity_pct  # too close to high = bad entry
    else:
        # Don't short near recent low — wait for bounce
        recent_low = min(recent)
        if recent_low == 0:
            return False
        dist_to_low = (current - recent_low) / recent_low * 100
        return dist_to_low < proximity_pct  # too close to low = bad entry


def detect_mover(token):
    """Detect if token is a fast mover worth trading.

    ACCELERATION-BASED: Catches moves that are SPEEDING UP, not just moving.
    This fires at the START of a move, not the end.

    Returns {direction, confidence, value, price} or None.
    """
    # Get 5m candles for velocity and trend
    closes_5m = _get_closes(token, 'candles_5m', 100)
    if len(closes_5m) < MOVER_VELOCITY_WINDOW + 1:
        return None

    # Get 1m candles for entry timing and volume
    candles_1m = _get_candles(token, 'candles_1m', 100)
    if len(candles_1m) < 20:
        return None

    # Compute velocity and acceleration
    velocity, direction = compute_velocity(closes_5m)
    if direction is None:
        return None

    acceleration = compute_velocity_acceleration(closes_5m)

    # ── PRIMARY FILTER: ACCELERATION ──────────────────────────────────────
    # The move must be SPEEDING UP, not just existing
    # For LONG: acceleration > 0 (velocity increasing)
    # For SHORT: acceleration < 0 (velocity decreasing/negative accelerating)
    if direction == 'LONG' and acceleration <= 0:
        return None  # not accelerating upward
    if direction == 'SHORT' and acceleration >= 0:
        return None  # not accelerating downward

    # Minimum acceleration threshold (must be meaningful)
    if abs(acceleration) < MOVER_ACCEL_MIN:  # at least 0.3% acceleration
        return None

    # ── SECONDARY: MINIMUM VELOCITY ───────────────────────────────────────
    # Must have some velocity, but lower threshold since acceleration is primary
    if abs(velocity) < MOVER_VELOCITY_MIN:  # at least 0.3% velocity (lower than before)
        return None

    # ── VOLUME CONFIRMATION ───────────────────────────────────────────────
    # Volume must confirm the move is real
    if not volume_gate(candles_1m, min_ratio=MOVER_VOLUME_RATIO):
        return None

    # Candle close gate — confirmed candles only
    confirmed_candles = candle_close_gate(candles_1m, timeframe_seconds=60)
    if len(confirmed_candles) < 2:
        return None

    # ── COMPUTE CONFIDENCE ────────────────────────────────────────────────
    conf = MOVER_CONF_BASE

    # Acceleration bonus: stronger acceleration = higher confidence
    accel_strength = abs(acceleration) / MOVER_ACCEL_MIN  # 1.0 = minimum, 2.0 = 2x min
    if accel_strength > 3.0:
        conf += 15
    elif accel_strength > 2.0:
        conf += 10
    elif accel_strength > 1.5:
        conf += 5

    # Velocity bonus: stronger velocity = higher confidence
    velocity_strength = abs(velocity) / MOVER_VELOCITY_MIN
    if velocity_strength > 5.0:
        conf += 10
    elif velocity_strength > 3.0:
        conf += 5

    conf = min(conf, MOVER_CONF_CAP)

    # Get current price
    price = closes_5m[-1]

    # Compute RSI and BB for logging only (not filtering)
    rsi = compute_rsi(closes_5m)
    bb_pos = compute_bb_position(closes_5m)

    return {
        'direction': direction,
        'confidence': conf,
        'value': round(velocity, 4),
        'price': price,
        'acceleration': round(acceleration, 4),
        'rsi': round(rsi, 2),
        'bb_position': round(bb_pos, 4),
    }


def scan_mover_signals():
    """Scan all tokens for fast mover signals."""
    added = 0

    # Session timing gate
    if not session_timing_gate():
        return 0

    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()

    # Collect all valid tokens with velocity
    candidates = []
    for token, data in prices.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Staleness check
        if price_age_minutes(token) > 10:
            continue

        # Blacklist check
        if token.upper() in LONG_BLACKLIST or token.upper() in SHORT_BLACKLIST:
            continue

        # Quick velocity check (no DB call yet)
        candidates.append(token)

    # Limit scan to top candidates by price (fastest to scan)
    # We'll do the actual velocity calculation in detect_mover
    scan_tokens = candidates[:200]  # safety cap

    for token in scan_tokens:
        # Cooldown check
        if get_cooldown(token):
            continue

        sig = detect_mover(token)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not MOVER_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not MOVER_MINUS_ENABLED:
            continue

        # Layer 1: blacklists (direction-specific)
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Direction-specific cooldown
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig.get('acceleration'),
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=MOVER_COOLDOWN_HOURS)
            _log(f"{token} {direction} vel={sig['value']:.3f}% "
                 f"accel={sig['acceleration']:.3f}% rsi={sig['rsi']:.1f} "
                 f"bb={sig['bb_position']:.3f} conf={sig['confidence']}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_mover_signals()


if __name__ == '__main__':
    n = scan_mover_signals()
    print(f"mover: {n} signals emitted")
