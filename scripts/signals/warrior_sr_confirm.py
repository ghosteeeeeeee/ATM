#!/usr/bin/env python3
"""Warrior S/R Confirm — Support/Resistance level + candlestick pattern + volume.

From Warrior Trading: "Enter on confirmed pattern at support/resistance."
This signal detects price touching a structural S/R level with a candlestick
confirmation pattern (engulfing, hammer, shooting star) and volume spike.

DIFFERENT from range_finder (which identifies range boundaries):
  - This requires a specific candlestick PATTERN at the level
  - Volume must confirm the move
  - Works in trending AND ranging markets (not just ranges)

DIFFERENT from engulfing (which is pure candlestick):
  - This REQUIRES proximity to a structural S/R level
  - Engulfing fires anywhere; this fires only at key levels

LOGIC:
  1. Detect swing highs/lows as S/R levels (5m, 200-bar lookback)
  2. Check if current price is near a level (within ATR proximity)
  3. Detect candlestick confirmation pattern at the level
  4. Volume must spike above average (confirmation)
  5. 1h trend alignment — prefer trades with the trend

THESIS: S/R levels are where institutional orders cluster. Candlestick patterns
at these levels = institutional participation. Volume confirms conviction.
This is a high-probability setup because you're trading WITH institutional flow.
"""

import sys
import os
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA
from entry_gates import (
    rr_gate, volume_gate, candle_close_gate, session_timing_gate,
)

from hermes_constants import (
    WARRIOR_SR_CONFIRM_ENABLED,
    WARRIOR_SR_CONFIRM_PLUS_ENABLED,
    WARRIOR_SR_CONFIRM_MINUS_ENABLED,
    WARRIOR_SR_CONFIRM_LOOKBACK,
    WARRIOR_SR_CONFIRM_TOUCHES_MIN,
    WARRIOR_SR_CONFIRM_ATR_PROXIMITY,
    WARRIOR_SR_CONFIRM_VOLUME_RATIO,
    WARRIOR_SR_CONFIRM_SWING_WINDOW,
    WARRIOR_SR_CONFIRM_CONF_BASE,
    WARRIOR_SR_CONFIRM_CONF_CAP,
    WARRIOR_SR_CONFIRM_COOLDOWN_HOURS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'warrior_sr_confirm_long'
SIGNAL_TYPE_SHORT = 'warrior_sr_confirm_short'
SOURCE_LONG = 'warrior-sr-confirm+'
SOURCE_SHORT = 'warrior-sr-confirm-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[warrior-sr-confirm] {msg}", flush=True)


def _get_candles(token, table='candles_5m', limit=200):
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
        if not rows or len(rows) < 20:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]}
                for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_1h_trend(token):
    """Check 1h EMA20/50 trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 60
        """, (token.upper(),))
        rows = cur.fetchall()
        if not rows or len(rows) < 50:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]

        def ema(data, period):
            k = 2 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1 - k)
            return val

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        if ema50 == 0:
            return 'NEUTRAL'
        spread = abs(ema20 - ema50) / ema50 * 100
        if spread < 0.1:
            return 'NEUTRAL'
        return 'BULLISH' if ema20 > ema50 else 'BEARISH'
    except Exception:
        return 'NEUTRAL'
    finally:
        if conn:
            conn.close()


def _find_sr_levels(candles, window=5):
    """Find swing highs/lows as S/R levels.

    Returns (support_levels, resistance_levels) as sorted lists.
    """
    if len(candles) < window * 2 + 1:
        return [], []

    closes = [c['close'] for c in candles]
    swing_highs = []
    swing_lows = []

    for i in range(window, len(closes) - window):
        local_window = closes[i - window:i + window + 1]
        if closes[i] == max(local_window):
            swing_highs.append(closes[i])
        if closes[i] == min(local_window):
            swing_lows.append(closes[i])

    # Cluster nearby levels (within 0.5% of each other)
    def cluster_levels(levels, threshold_pct=0.5):
        if not levels:
            return []
        levels = sorted(levels)
        clustered = []
        current_cluster = [levels[0]]
        for lvl in levels[1:]:
            if abs(lvl - current_cluster[-1]) / current_cluster[-1] * 100 < threshold_pct:
                current_cluster.append(lvl)
            else:
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [lvl]
        clustered.append(sum(current_cluster) / len(current_cluster))
        return clustered

    return cluster_levels(swing_lows), cluster_levels(swing_highs)


def _is_near_level(price, levels, atr_pct, proximity_mult):
    """Check if price is within proximity of any level. Returns (is_near, nearest_level)."""
    if not levels:
        return False, None
    atr_dist = price * atr_pct * proximity_mult
    for lvl in levels:
        if abs(price - lvl) <= atr_dist:
            return True, lvl
    return False, None


def _detect_candlestick_pattern(candles):
    """Detect candlestick confirmation pattern at S/R level.

    Returns ('bullish', pattern_name) or ('bearish', pattern_name) or (None, None).

    Patterns detected:
    - Bullish engulfing: current body > prev body, close > open, close > prev close
    - Hammer: small body at top, long lower wick (>2x body), little upper wick
    - Bullish pin bar: long lower wick rejecting lower prices

    - Bearish engulfing: current body > prev body, close < open, close < prev close
    - Shooting star: small body at bottom, long upper wick (>2x body), little lower wick
    - Bearish pin bar: long upper wick rejecting higher prices
    """
    if len(candles) < 3:
        return None, None

    current = candles[-1]
    prev = candles[-2]

    curr_body = abs(current['close'] - current['open'])
    prev_body = abs(prev['close'] - prev['open'])

    if curr_body == 0 or prev_body == 0:
        return None, None

    curr_range = current['high'] - current['low']
    if curr_range == 0:
        return None, None

    # Bullish patterns
    if current['close'] > current['open']:  # green candle
        # Bullish engulfing
        if curr_body > prev_body and current['close'] > prev['close'] and prev['close'] < prev['open']:
            return 'bullish', 'engulfing'

        # Hammer: small body at top, long lower wick
        upper_wick = current['high'] - max(current['open'], current['close'])
        lower_wick = min(current['open'], current['close']) - current['low']
        if lower_wick > curr_body * 2 and upper_wick < curr_body * 0.5:
            return 'bullish', 'hammer'

        # Bullish pin bar: long lower wick rejecting support
        if lower_wick > curr_range * 0.6 and curr_body < curr_range * 0.3:
            return 'bullish', 'pin_bar'

    # Bearish patterns
    if current['close'] < current['open']:  # red candle
        # Bearish engulfing
        if curr_body > prev_body and current['close'] < prev['close'] and prev['close'] > prev['open']:
            return 'bearish', 'engulfing'

        # Shooting star: small body at bottom, long upper wick
        upper_wick = current['high'] - max(current['open'], current['close'])
        lower_wick = min(current['open'], current['close']) - current['low']
        if upper_wick > curr_body * 2 and lower_wick < curr_body * 0.5:
            return 'bearish', 'shooting_star'

        # Bearish pin bar: long upper wick rejecting resistance
        if upper_wick > curr_range * 0.6 and curr_body < curr_range * 0.3:
            return 'bearish', 'pin_bar'

    return None, None


def _get_cached_atr(token):
    """Fetch ATR% from atr_cache.json."""
    import json
    from paths import ATR_CACHE_FILE
    try:
        with open(ATR_CACHE_FILE) as f:
            cache = json.load(f)
        entry = cache.get(token.upper(), {})
        return entry.get('atr_pct', entry.get('atr', 0.03))
    except Exception:
        return 0.03


def detect_warrior_sr(candles_5m, atr_pct=0.03):
    """Detect Warrior S/R confirm setup.

    Returns {direction, confidence, value, price, pattern} or None.
    """
    if len(candles_5m) < WARRIOR_SR_CONFIRM_LOOKBACK:
        return None

    price = candles_5m[-1]['close']
    if price <= 0:
        return None

    # Find S/R levels
    support_levels, resistance_levels = _find_sr_levels(
        candles_5m, window=WARRIOR_SR_CONFIRM_SWING_WINDOW
    )

    # Detect candlestick pattern
    pattern_direction, pattern_name = _detect_candlestick_pattern(candles_5m)
    if not pattern_direction:
        return None

    # Check proximity to S/R level
    if pattern_direction == 'bullish':
        # At support: price near a support level
        near, level = _is_near_level(price, support_levels, atr_pct, WARRIOR_SR_CONFIRM_ATR_PROXIMITY)
        if not near:
            return None
        direction = 'LONG'
        value = abs(price - level) / price * 100 if level > 0 else 0
    else:
        # At resistance: price near a resistance level
        near, level = _is_near_level(price, resistance_levels, atr_pct, WARRIOR_SR_CONFIRM_ATR_PROXIMITY)
        if not near:
            return None
        direction = 'SHORT'
        value = abs(level - price) / price * 100 if price > 0 else 0

    # Confidence: base + pattern bonus + level strength
    conf = WARRIOR_SR_CONFIRM_CONF_BASE
    if pattern_name == 'engulfing':
        conf += 5  # strongest pattern
    elif pattern_name in ('hammer', 'shooting_star'):
        conf += 3

    # Count how many times this level was touched (more touches = stronger)
    all_levels = support_levels + resistance_levels
    if level:
        touches = sum(1 for l in all_levels if abs(l - level) / level * 100 < 1.0)
        if touches >= WARRIOR_SR_CONFIRM_TOUCHES_MIN + 1:
            conf += 5
        elif touches >= WARRIOR_SR_CONFIRM_TOUCHES_MIN:
            conf += 3

    conf = min(conf, WARRIOR_SR_CONFIRM_CONF_CAP)

    return {
        'direction': direction,
        'confidence': conf,
        'value': round(value, 4),
        'price': price,
        'pattern': pattern_name,
    }


def scan_warrior_sr_signals():
    """Scan all tokens for Warrior S/R confirm setups."""
    added = 0

    # GATE: Session timing
    if not session_timing_gate():
        return 0

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

        # Get 5m candles
        raw_candles = _get_candles(token, 'candles_5m', WARRIOR_SR_CONFIRM_LOOKBACK)
        if not raw_candles:
            continue

        # GATE: Candle close
        candles = candle_close_gate(raw_candles, timeframe_seconds=300)
        if len(candles) < 20:
            continue

        # Get ATR for this token
        atr_pct = _get_cached_atr(token)

        sig = detect_warrior_sr(candles, atr_pct=atr_pct)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: kill-switch
        if direction == 'LONG' and not WARRIOR_SR_CONFIRM_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not WARRIOR_SR_CONFIRM_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        # GATE: Volume confirmation
        if not volume_gate(candles, min_ratio=WARRIOR_SR_CONFIRM_VOLUME_RATIO):
            continue

        # GATE: 1h trend alignment
        trend = _get_1h_trend(token)
        if trend == 'BULLISH' and direction == 'SHORT':
            _log(f"{token} SHORT BLOCKED trend={trend} (counter-trend)")
            continue
        if trend == 'BEARISH' and direction == 'LONG':
            _log(f"{token} LONG BLOCKED trend={trend} (counter-trend)")
            continue

        # GATE: R:R pre-check
        rr_pass, sl, tp, rr = rr_gate(token, direction, price, raw_candles)
        if not rr_pass:
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
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=WARRIOR_SR_CONFIRM_COOLDOWN_HOURS)
            _log(f"{token} {direction} conf={sig['confidence']} pattern={sig['pattern']} "
                 f"trend={trend} rr={rr:.1f}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_warrior_sr_signals()


if __name__ == '__main__':
    n = scan_warrior_sr_signals()
    print(f"warrior_sr_confirm: {n} signals emitted")
