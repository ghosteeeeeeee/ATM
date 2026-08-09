#!/usr/bin/env python3
"""
Engulfing Candle — detect large single-candle moves that signal momentum shift.

Enter SHORT after bearish engulfing (price drops sharply).
Enter LONG after bullish engulfing (price rises sharply).

Detection:
  1. Current candle moves > ENGULFING_MIN_MOVE% from previous close
  2. Previous N candles had tight range (< ENGULFING_PRIOR_RANGE%)
  3. Volume confirms the move (> ENGULFING_VOLUME_RATIOx average)

Based on MORPHO observation: 0.22% drop in 1 minute after tight consolidation.
"""
import sys
import os
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    ENGULFING_ENABLED,
    ENGULFING_PLUS_ENABLED,
    ENGULFING_MINUS_ENABLED,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'engulfing_long'
SIGNAL_TYPE_SHORT = 'engulfing_short'
SOURCE_LONG = 'engulfing+'
SOURCE_SHORT = 'engulfing-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[engulfing] {msg}", flush=True)


def _get_candles(token, table='candles_1m', limit=100):
    """Fetch OHLCV candles. Returns list of {open, high, low, close, volume} oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT open, high, low, close, volume FROM {table}
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        if not rows or len(rows) < 10:
            return []
        return [{'open': r[0], 'high': r[1], 'low': r[2], 'close': r[3], 'volume': r[4]}
                for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def detect_engulfing(candles):
    """Detect engulfing candle pattern.

    Returns {direction, confidence, value, price} or None.
    """
    from hermes_constants import (
        ENGULFING_MIN_MOVE, ENGULFING_PRIOR_RANGE,
        ENGULFING_VOLUME_RATIO, ENGULFING_LOOKBACK,
        ENGULFING_CONF_BASE, ENGULFING_CONF_CAP,
    )

    if len(candles) < ENGULFING_LOOKBACK + 2:
        return None

    current = candles[-1]
    prev = candles[-2]

    # Calculate current candle move from previous close
    if prev['close'] == 0:
        return None
    move_pct = abs(current['close'] - prev['close']) / prev['close'] * 100

    if move_pct < ENGULFING_MIN_MOVE:
        return None

    # Determine direction
    if current['close'] > prev['close']:
        direction = 'LONG'
    elif current['close'] < prev['close']:
        direction = 'SHORT'
    else:
        return None

    # Check prior consolidation — last N candles should have tight range
    prior_candles = candles[-(ENGULFING_LOOKBACK + 1):-1]  # exclude current
    if prior_candles:
        prior_highs = [c['high'] for c in prior_candles]
        prior_lows = [c['low'] for c in prior_candles]
        prior_range = (max(prior_highs) - min(prior_lows)) / min(prior_lows) * 100 if min(prior_lows) > 0 else 999
        if prior_range > ENGULFING_PRIOR_RANGE:
            return None  # not a tight consolidation before the move

    # Volume confirmation
    prior_volumes = [c['volume'] for c in prior_candles if c['volume'] and c['volume'] > 0]
    if not prior_volumes:
        return None  # no volume data — can't confirm, skip
    avg_volume = sum(prior_volumes) / len(prior_volumes)
    if avg_volume > 0 and not (current['volume'] and current['volume'] >= avg_volume * ENGULFING_VOLUME_RATIO):
        return None  # volume doesn't confirm

    # Confidence based on move strength
    conf = ENGULFING_CONF_BASE
    if move_pct > 0.30:
        conf += 10
    elif move_pct > 0.20:
        conf += 5
    conf = min(conf, ENGULFING_CONF_CAP)

    return {
        'direction': direction,
        'confidence': conf,
        'value': round(move_pct, 4),
        'price': current['close'],
    }


def scan_engulfing_signals():
    """Scan all tokens for engulfing patterns."""
    added = 0

    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Staleness check
        if price_age_minutes(token) > 10:
            continue

        # Get candles
        candles = _get_candles(token, 'candles_1m', 100)
        if not candles:
            continue

        sig = detect_engulfing(candles)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: kill-switch
        if direction == 'LONG' and not ENGULFING_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not ENGULFING_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
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
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=1)
            _log(f"{token} {direction} conf={sig['confidence']} move={sig['value']:.3f}%")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_engulfing_signals()


if __name__ == '__main__':
    n = scan_engulfing_signals()
    print(f"engulfing: {n} signals emitted")
