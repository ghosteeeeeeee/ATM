#!/usr/bin/env python3
"""
grind_breakout_v2.py — Volume-confirmed resistance breakout with compression.

THESIS:
  When a token consolidates in a tight range (low BB width, dead volume),
  then breaks above the range high with a volume surge AND positive
  acceleration, the move has institutional backing. The compression phase
  is accumulation; the breakout with volume is the markup beginning.

  This catches moves like CHIP (+29.4%) and CFX (+20.7%) EARLY — before
  pump-chain signals fire (which wait for a much larger price move).

ENTRY CONDITIONS (LONG):
  1. BB(20, 2.0) width was below BB_COMPRESS_MAX within last COMPRESS_LOOKBACK bars
  2. Volume during compression was below COMPRESS_VOL_MAX × average
  3. Current close > highest high of last RESISTANCE_BARS bars
  4. Volume >= VOL_SURGE_MULT × average
  5. Breakout bar body >= BREAKOUT_BODY_MIN of its range
  6. Acceleration > ACCEL_MIN (velocity increasing)
  7. Not overextended: price < MAX_MOVE_FROM_RANGE% above breakout level

ENTRY CONDITIONS (SHORT): Mirror (support breakdown, volume surge, negative acceleration)

DATA SOURCE:
  - candles_5m from candles.db (local, zero API calls)
  - token_speeds from signals_hermes_runtime.db (acceleration)
"""

import sys
import os
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    GRIND_BREAKOUT_V2_ENABLED,
    GRIND_BREAKOUT_V2_PLUS_ENABLED,
    GRIND_BREAKOUT_V2_MINUS_ENABLED,
    GRIND_BREAKOUT_V2_COOLDOWN_HOURS,
    GRIND_BREAKOUT_V2_RESISTANCE_BARS,
    GRIND_BREAKOUT_V2_VOL_SURGE_MULT,
    GRIND_BREAKOUT_V2_VOL_AVG_PERIOD,
    GRIND_BREAKOUT_V2_ACCEL_MIN,
    GRIND_BREAKOUT_V2_MACD_RISE_ENABLED,
    GRIND_BREAKOUT_V2_MAX_MOVE_FROM_RANGE,
    GRIND_BREAKOUT_V2_BREAKOUT_BODY_MIN,
    GRIND_BREAKOUT_V2_BB_COMPRESS_MAX,
    GRIND_BREAKOUT_V2_BB_EXPAND_MULT,
    GRIND_BREAKOUT_V2_COMPRESS_LOOKBACK,
    GRIND_BREAKOUT_V2_COMPRESS_VOL_MAX,
    GRIND_BREAKOUT_V2_BB_PERIOD,
    GRIND_BREAKOUT_V2_BB_STDDEV,
    GRIND_BREAKOUT_V2_CONF_BASE,
    GRIND_BREAKOUT_V2_CONF_FLOOR,
    GRIND_BREAKOUT_V2_CONF_CAP,
    GRIND_BREAKOUT_V2_CONF_VOL_BONUS,
    GRIND_BREAKOUT_V2_CONF_VOL_BONUS_MULT,
    GRIND_BREAKOUT_V2_CONF_VOL_HALF_MULT,
    GRIND_BREAKOUT_V2_CONF_ACCEL_BONUS,
    GRIND_BREAKOUT_V2_CONF_ACCEL_BONUS_MIN,
    GRIND_BREAKOUT_V2_CONF_MACD_BONUS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'grind_breakout_long'
SIGNAL_TYPE_SHORT = 'grind_breakout_short'
SOURCE_LONG = 'grind-breakout-v2+'
SOURCE_SHORT = 'grind-breakout-v2-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

# Minimum candles needed: BB_PERIOD + some buffer
_MIN_CANDLES = GRIND_BREAKOUT_V2_BB_PERIOD + 10


def _log(msg):
    print(f'[grind-breakout-v2] {msg}', flush=True)


def _get_candles(token, limit):
    """Fetch 5m candles. Returns list of (ts, open, high, low, close, volume) oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return list(reversed(rows))
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_acceleration(token):
    """Read price_acceleration from token_speeds. Returns float or None."""
    conn = None
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
        c = conn.cursor()
        c.execute("SELECT price_acceleration FROM token_speeds WHERE token = ?", (token.upper(),))
        row = c.fetchone()
        return float(row[0]) if row and row[0] is not None else None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_macd_hist(candles):
    """Compute MACD histogram from 5m closes. Returns (hist_now, hist_prev) or (None, None)."""
    closes = [c[4] for c in candles]
    if len(closes) < 35:
        return None, None

    def _ema(vals, period):
        k = 2 / (period + 1)
        e = sum(vals[:period]) / period
        for v in vals[period:]:
            e = v * k + e * (1 - k)
        return e

    # Compute MACD line series
    macd_line = []
    for i in range(26, len(closes) + 1):
        chunk = closes[max(0, i - 35):i]
        if len(chunk) >= 26:
            macd_line.append(_ema(chunk, 12) - _ema(chunk, 26))

    if len(macd_line) < 10:
        return None, None

    # Signal line as a SERIES (EMA9 of MACD) — needed for correct hist_prev
    signal_series = []
    k = 2 / (9 + 1)
    sig = sum(macd_line[:9]) / 9
    signal_series.append(sig)
    for m in macd_line[9:]:
        sig = m * k + sig * (1 - k)
        signal_series.append(sig)

    # Histogram = MACD - Signal at each bar
    if len(signal_series) < 2:
        return None, None
    hist_now = macd_line[-1] - signal_series[-1]
    hist_prev = macd_line[-2] - signal_series[-2]

    return hist_now, hist_prev


def _bb_width(closes, period, stddev):
    """Compute BB width as % of SMA. Returns float or None."""
    if len(closes) < period:
        return None
    window = closes[-period:]
    sma = sum(window) / period
    if sma <= 0:
        return None
    variance = sum((x - sma) ** 2 for x in window) / period
    std = variance ** 0.5
    bb_upper = sma + stddev * std
    bb_lower = sma - stddev * std
    return (bb_upper - bb_lower) / sma * 100


def detect(token):
    """Detect grind_breakout_v2 signal for a token.

    Returns {direction, confidence, value, price, z_score} or None.
    """
    # Load candles: need BB_PERIOD for current BB + COMPRESS_LOOKBACK for compression check
    lookback = GRIND_BREAKOUT_V2_BB_PERIOD + GRIND_BREAKOUT_V2_COMPRESS_LOOKBACK + 10
    candles = _get_candles(token, lookback)
    if len(candles) < _MIN_CANDLES:
        return None

    closes = [c[4] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    vols = [c[5] for c in candles]

    current_price = closes[-1]
    if current_price <= 0:
        return None

    # ── Volume average ──────────────────────────────────────────────────────
    vol_avg = sum(vols[-GRIND_BREAKOUT_V2_VOL_AVG_PERIOD:]) / GRIND_BREAKOUT_V2_VOL_AVG_PERIOD
    if vol_avg <= 0:
        return None
    current_vol_ratio = vols[-1] / vol_avg

    # ── Condition 1+5: Compression before breakout + BB expansion ──────────
    # BB width must have been below BB_COMPRESS_MAX within last COMPRESS_LOOKBACK bars,
    # AND BB must now be > BB_EXPAND_MULT × min BB in compression window.
    # The expansion requirement confirms a real volatility expansion (coil → spring),
    # not just a token that's always been quiet.
    compressed = False
    min_bb_in_window = 999.0
    compress_start = max(GRIND_BREAKOUT_V2_BB_PERIOD, len(candles) - 1 - GRIND_BREAKOUT_V2_COMPRESS_LOOKBACK)
    for i in range(compress_start, len(candles) - 1):  # exclude current bar
        bb_w = _bb_width(closes[:i+1], GRIND_BREAKOUT_V2_BB_PERIOD, GRIND_BREAKOUT_V2_BB_STDDEV)
        if bb_w is None:
            continue
        if bb_w < min_bb_in_window:
            min_bb_in_window = bb_w
        if bb_w < GRIND_BREAKOUT_V2_BB_COMPRESS_MAX:
            compressed = True

    if not compressed:
        return None

    # BB expansion: current BB must be significantly wider than compression level
    current_bb = _bb_width(closes, GRIND_BREAKOUT_V2_BB_PERIOD, GRIND_BREAKOUT_V2_BB_STDDEV)
    if current_bb is None or min_bb_in_window >= 999.0:
        return None
    if current_bb < min_bb_in_window * GRIND_BREAKOUT_V2_BB_EXPAND_MULT:
        return None

    # ── Condition 2: Resistance breakout (LONG) or support breakdown (SHORT) ─
    res_bars = GRIND_BREAKOUT_V2_RESISTANCE_BARS
    resistance = max(highs[-res_bars-1:-1])  # exclude current bar
    support = min(lows[-res_bars-1:-1])

    direction = None
    breakout_level = None

    if current_price > resistance:
        direction = 'LONG'
        breakout_level = resistance
    elif current_price < support:
        direction = 'SHORT'
        breakout_level = support
    else:
        return None

    # ── Condition 3: Breakout bar body quality ──────────────────────────────
    bar_open = candles[-1][1]
    bar_high = candles[-1][2]
    bar_low = candles[-1][3]
    bar_range = bar_high - bar_low
    if bar_range <= 0:
        return None

    if direction == 'LONG':
        bar_body = current_price - bar_open  # close - open
    else:
        bar_body = bar_open - current_price  # open - close

    body_ratio = bar_body / bar_range
    if body_ratio < GRIND_BREAKOUT_V2_BREAKOUT_BODY_MIN:
        return None

    # ── Condition 4: Volume surge ───────────────────────────────────────────
    if current_vol_ratio < GRIND_BREAKOUT_V2_VOL_SURGE_MULT:
        return None

    # ── Condition 6: Acceleration ───────────────────────────────────────────
    accel = _get_acceleration(token)
    if accel is None:
        # Fallback: compute from candle closes
        if len(closes) >= 3:
            vel_now = (closes[-1] - closes[-2]) / closes[-2] * 100 if closes[-2] > 0 else 0
            vel_prev = (closes[-2] - closes[-3]) / closes[-3] * 100 if closes[-3] > 0 else 0
            accel = vel_now - vel_prev
        else:
            return None

    if direction == 'LONG' and accel <= GRIND_BREAKOUT_V2_ACCEL_MIN:
        return None
    if direction == 'SHORT' and accel >= -GRIND_BREAKOUT_V2_ACCEL_MIN:
        return None

    # ── Condition 7: Not overextended ───────────────────────────────────────
    if breakout_level and breakout_level > 0:
        move_from_range = abs(current_price - breakout_level) / breakout_level * 100
        if move_from_range > GRIND_BREAKOUT_V2_MAX_MOVE_FROM_RANGE:
            return None

    # ── Optional: MACD histogram confirmation ───────────────────────────────
    macd_bonus = 0
    if GRIND_BREAKOUT_V2_MACD_RISE_ENABLED:
        hist_now, hist_prev = _get_macd_hist(candles)
        if hist_now is not None and hist_prev is not None:
            if direction == 'LONG' and hist_now > hist_prev:
                macd_bonus = GRIND_BREAKOUT_V2_CONF_MACD_BONUS
            elif direction == 'SHORT' and hist_now < hist_prev:
                macd_bonus = GRIND_BREAKOUT_V2_CONF_MACD_BONUS
            # If MACD disagrees, still allow but no bonus (not a hard filter)

    # ── Confidence ──────────────────────────────────────────────────────────
    confidence = GRIND_BREAKOUT_V2_CONF_BASE

    # Volume bonus
    if current_vol_ratio >= GRIND_BREAKOUT_V2_CONF_VOL_BONUS_MULT:
        confidence += GRIND_BREAKOUT_V2_CONF_VOL_BONUS
    elif current_vol_ratio >= GRIND_BREAKOUT_V2_CONF_VOL_HALF_MULT:
        confidence += GRIND_BREAKOUT_V2_CONF_VOL_BONUS // 2

    # Acceleration bonus
    if abs(accel) > GRIND_BREAKOUT_V2_CONF_ACCEL_BONUS_MIN:
        confidence += GRIND_BREAKOUT_V2_CONF_ACCEL_BONUS

    # MACD bonus
    confidence += macd_bonus

    # Clamp
    confidence = max(GRIND_BREAKOUT_V2_CONF_FLOOR, min(GRIND_BREAKOUT_V2_CONF_CAP, confidence))

    # ── Z-score (for hotset scoring) ────────────────────────────────────────
    if len(closes) >= 20:
        sma20 = sum(closes[-20:]) / 20
        var20 = sum((c - sma20) ** 2 for c in closes[-20:]) / 20
        std20 = var20 ** 0.5
        z_score = (current_price - sma20) / std20 if std20 > 0 else 0
    else:
        z_score = 0

    # ── Value: % move from breakout level ───────────────────────────────────
    value = round((current_price - breakout_level) / breakout_level * 100, 4) if breakout_level else 0

    return {
        'direction': direction,
        'confidence': confidence,
        'value': value,
        'price': current_price,
        'z_score': round(z_score, 4),
    }


def run(prices_dict=None) -> int:
    """Entry point for signals_runner. Scans all tokens from candles DB."""
    if not GRIND_BREAKOUT_V2_ENABLED:
        return 0

    added = 0

    # Get all tokens from candles_5m
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("SELECT DISTINCT token FROM candles_5m")
        tokens = [r[0] for r in c.fetchall()]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

    for token in tokens:
        # Skip if price is stale
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']

        # Per-direction kill-switch
        if direction == 'LONG' and not GRIND_BREAKOUT_V2_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not GRIND_BREAKOUT_V2_MINUS_ENABLED:
            continue

        # Blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
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
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            _log(f'{token} {direction} conf={sig["confidence"]:.0f} price={sig["price"]} z={sig.get("z_score", 0):.2f}')
            set_cooldown(token, direction, hours=GRIND_BREAKOUT_V2_COOLDOWN_HOURS)

    if added:
        _log(f'Added {added} signals')
    return added


if __name__ == '__main__':
    import sys as _sys
    if len(_sys.argv) > 1:
        result = detect(_sys.argv[1])
        if result:
            print(f'DETECTED: {result}')
        else:
            print('No signal')
    else:
        count = run()
        print(f'Added {count} signals')
