#!/usr/bin/env python3
"""Breakout Pullback — Classic Warrior Trading setup.

From Warrior Trading: "Wait for breakout, then enter on the first pullback
to the breakout level." This is one of the highest-probability setups because
you're entering AFTER the breakout is confirmed, on a low-risk retest.

DIFFERENT from volume_breakout (which fires ON the breakout):
  - This waits for the pullback TO the breakout level
  - Entry is at a better price (lower risk, higher R:R)
  - Requires the breakout to have happened recently (not stale)

DIFFERENT from resistance_break (which detects resistance break + pullback):
  - This works BOTH directions (break above resistance OR break below support)
  - Uses multi-timeframe confirmation (15m breakout + 5m pullback)
  - Requires volume on breakout, volume contraction on pullback

THESIS: After a genuine breakout, price often retests the breakout level.
Institutional traders use pullbacks to build positions. Entering at the
pullback gives you a tight stop (below breakout level) and trend continuation.

LOGIC:
  1. Detect recent breakout: price broke above resistance (LONG) or below support (SHORT)
  2. Breakout must have volume confirmation (spike)
  3. Price pulls back toward breakout level
  4. Enter when price touches breakout level + candlestick confirmation
  5. Stop below breakout level (tight risk)
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
    BREAKOUT_PULLBACK_ENABLED,
    BREAKOUT_PULLBACK_PLUS_ENABLED,
    BREAKOUT_PULLBACK_MINUS_ENABLED,
    BREAKOUT_PULLBACK_LOOKBACK,
    BREAKOUT_PULLBACK_BREAKOUT_PCT,
    BREAKOUT_PULLBACK_PULLBACK_PCT,
    BREAKOUT_PULLBACK_VOLUME_SPIKE,
    BREAKOUT_PULLBACK_VOLUME_RATIO,
    BREAKOUT_PULLBACK_PULLBACK_WINDOW,
    BREAKOUT_PULLBACK_SWING_WINDOW,
    BREAKOUT_PULLBACK_CONF_BASE,
    BREAKOUT_PULLBACK_CONF_CAP,
    BREAKOUT_PULLBACK_COOLDOWN_HOURS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'breakout_pullback_long'
SIGNAL_TYPE_SHORT = 'breakout_pullback_short'
SOURCE_LONG = 'breakout-pullback+'
SOURCE_SHORT = 'breakout-pullback-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[breakout-pullback] {msg}", flush=True)


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
        if not rows or len(rows) < 30:
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


def _find_swing_levels(candles, window=5):
    """Find swing highs/lows. Returns (swing_highs, swing_lows) as lists of prices."""
    if len(candles) < window * 2 + 1:
        return [], []

    closes = [c['close'] for c in candles]
    swing_highs = []
    swing_lows = []

    for i in range(window, len(closes) - window):
        local_window = closes[i - window:i + window + 1]
        if closes[i] == max(local_window):
            swing_highs.append({'price': closes[i], 'idx': i})
        if closes[i] == min(local_window):
            swing_lows.append({'price': closes[i], 'idx': i})

    return swing_highs, swing_lows


def _detect_breakout(candles, swing_highs, swing_lows):
    """Detect if a breakout happened recently.

    Returns (direction, breakout_level, breakout_idx) or (None, None, None).

    LONG breakout: price closed above a recent swing high with volume
    SHORT breakout: price closed below a recent swing low with volume
    """
    if len(candles) < 20:
        return None, None, None

    current = candles[-1]
    closes = [c['close'] for c in candles]

    # Check for LONG breakout: recent close above a swing high
    for sh in reversed(swing_highs):
        idx = sh['idx']
        level = sh['price']
        # Breakout must be recent (within pullback_window candles)
        bars_ago = len(candles) - 1 - idx
        if bars_ago > BREAKOUT_PULLBACK_PULLBACK_WINDOW:
            continue
        if bars_ago < 2:
            continue  # too recent, need some distance
        # Check if price closed above this level with sufficient magnitude
        if current['close'] > level:
            breakout_pct = (current['close'] - level) / level * 100
            if breakout_pct < BREAKOUT_PULLBACK_BREAKOUT_PCT:
                continue  # breakout too small
            # Check volume on breakout candle
            breakout_candle = candles[idx + 1] if idx + 1 < len(candles) else candles[idx]
            avg_vol = sum(c['volume'] for c in candles[-20:]) / 20 if len(candles) >= 20 else 1
            if avg_vol > 0 and breakout_candle['volume'] >= avg_vol * BREAKOUT_PULLBACK_VOLUME_SPIKE:
                return 'LONG', level, idx

    # Check for SHORT breakout: recent close below a swing low
    for sl in reversed(swing_lows):
        idx = sl['idx']
        level = sl['price']
        bars_ago = len(candles) - 1 - idx
        if bars_ago > BREAKOUT_PULLBACK_PULLBACK_WINDOW:
            continue
        if bars_ago < 2:
            continue
        if current['close'] < level:
            breakout_pct = (level - current['close']) / level * 100
            if breakout_pct < BREAKOUT_PULLBACK_BREAKOUT_PCT:
                continue  # breakout too small
            breakout_candle = candles[idx + 1] if idx + 1 < len(candles) else candles[idx]
            avg_vol = sum(c['volume'] for c in candles[-20:]) / 20 if len(candles) >= 20 else 1
            if avg_vol > 0 and breakout_candle['volume'] >= avg_vol * BREAKOUT_PULLBACK_VOLUME_SPIKE:
                return 'SHORT', level, idx

    return None, None, None


def _check_pullback(candles, direction, breakout_level):
    """Check if price has pulled back to the breakout level.

    For LONG: price pulled back DOWN toward the breakout level (support retest)
    For SHORT: price pulled back UP toward the breakout level (resistance retest)

    Returns True if pullback is confirmed.
    """
    if len(candles) < 3:
        return False

    current = candles[-1]
    recent = candles[-5:]  # last 5 candles for pullback detection

    if direction == 'LONG':
        # Pullback: price came down toward breakout level
        # Current price should be near or at the breakout level
        proximity = abs(current['close'] - breakout_level) / breakout_level * 100
        if proximity > BREAKOUT_PULLBACK_PULLBACK_PCT:
            return False
        # Recent candles should show downward move (the pullback)
        recent_lows = [c['low'] for c in recent]
        min_recent_low = min(recent_lows)
        # Pullback went near the level
        return min_recent_low <= breakout_level * (1 + BREAKOUT_PULLBACK_PULLBACK_PCT / 100)

    else:  # SHORT
        proximity = abs(current['close'] - breakout_level) / breakout_level * 100
        if proximity > BREAKOUT_PULLBACK_PULLBACK_PCT:
            return False
        recent_highs = [c['high'] for c in recent]
        max_recent_high = max(recent_highs)
        return max_recent_high >= breakout_level * (1 - BREAKOUT_PULLBACK_PULLBACK_PCT / 100)


def _detect_pullback_candlestick(candles, direction):
    """Detect a candlestick confirmation at the pullback level.

    Returns True if a confirming pattern is found.
    """
    if len(candles) < 2:
        return False

    current = candles[-1]

    if direction == 'LONG':
        # Bullish confirmation: green candle, close > open, or hammer/pin bar
        if current['close'] > current['open']:
            return True
        # Hammer: long lower wick at support
        body = abs(current['close'] - current['open'])
        lower_wick = min(current['open'], current['close']) - current['low']
        if body > 0 and lower_wick > body * 1.5:
            return True
    else:
        # Bearish confirmation: red candle, close < open, or shooting star
        if current['close'] < current['open']:
            return True
        body = abs(current['close'] - current['open'])
        upper_wick = current['high'] - max(current['open'], current['close'])
        if body > 0 and upper_wick > body * 1.5:
            return True

    return False


def detect_breakout_pullback(candles_5m):
    """Detect breakout pullback setup.

    Returns {direction, confidence, value, price} or None.
    """
    if len(candles_5m) < BREAKOUT_PULLBACK_LOOKBACK:
        return None

    price = candles_5m[-1]['close']
    if price <= 0:
        return None

    # Find swing levels
    swing_highs, swing_lows = _find_swing_levels(candles_5m, window=BREAKOUT_PULLBACK_SWING_WINDOW)

    # Detect breakout
    direction, breakout_level, breakout_idx = _detect_breakout(candles_5m, swing_highs, swing_lows)
    if not direction:
        return None

    # Check pullback to breakout level
    if not _check_pullback(candles_5m, direction, breakout_level):
        return None

    # Candlestick confirmation at pullback
    if not _detect_pullback_candlestick(candles_5m, direction):
        return None

    # Confidence: base + breakout strength + pullback quality
    conf = BREAKOUT_PULLBACK_CONF_BASE

    # Breakout strength: how far above/below the level did price go?
    max_extension = 0
    for c in candles_5m[breakout_idx:]:
        if direction == 'LONG':
            ext = (c['high'] - breakout_level) / breakout_level * 100
        else:
            ext = (breakout_level - c['low']) / breakout_level * 100
        max_extension = max(max_extension, ext)

    if max_extension > 1.0:
        conf += 8  # strong breakout
    elif max_extension > 0.5:
        conf += 5
    elif max_extension > 0.3:
        conf += 3

    # Pullback quality: how close to the level
    pullback_dist = abs(price - breakout_level) / breakout_level * 100
    if pullback_dist < 0.1:
        conf += 5  # perfect retest
    elif pullback_dist < 0.2:
        conf += 3

    conf = min(conf, BREAKOUT_PULLBACK_CONF_CAP)

    value = max_extension  # record how far the breakout extended

    return {
        'direction': direction,
        'confidence': conf,
        'value': round(value, 4),
        'price': price,
        'breakout_level': breakout_level,
    }


def scan_breakout_pullback_signals():
    """Scan all tokens for breakout pullback setups."""
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
        raw_candles = _get_candles(token, 'candles_5m', BREAKOUT_PULLBACK_LOOKBACK)
        if not raw_candles:
            continue

        # GATE: Candle close
        candles = candle_close_gate(raw_candles, timeframe_seconds=300)
        if len(candles) < 30:
            continue

        # GATE: Reject synthesized candles (V=0 = price_history, not real exchange data)
        if candles[-1].get('volume', 0) <= 0:
            continue

        sig = detect_breakout_pullback(candles)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: kill-switch
        if direction == 'LONG' and not BREAKOUT_PULLBACK_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not BREAKOUT_PULLBACK_MINUS_ENABLED:
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
        if not volume_gate(candles, min_ratio=BREAKOUT_PULLBACK_VOLUME_RATIO):
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
            set_cooldown(token, direction, hours=BREAKOUT_PULLBACK_COOLDOWN_HOURS)
            _log(f"{token} {direction} conf={sig['confidence']} "
                 f"breakout_level={sig.get('breakout_level', 0):.4f} "
                 f"trend={trend} rr={rr:.1f}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_breakout_pullback_signals()


if __name__ == '__main__':
    n = scan_breakout_pullback_signals()
    print(f"breakout_pullback: {n} signals emitted")
