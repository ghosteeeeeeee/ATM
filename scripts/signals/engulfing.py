#!/usr/bin/env python3
"""Engulfing Candle — detect large single-candle moves that signal momentum shift.

Enter SHORT after bearish engulfing (price drops sharply).
Enter LONG after bullish engulfing (price rises sharply).

Detection (improved 2026-08-11):
  1. Current candle body > previous candle body (true engulfing)
  2. Current candle moves > ENGULFING_MIN_MOVE% from previous close
  3. Previous N candles had tight range (< ENGULFING_PRIOR_RANGE%)
  4. Volume confirms the move (> 1.2× average) — entry_gates.volume_gate
  5. 15m EMA trend alignment — don't fire counter-trend
  6. S/R proximity — prefer bounces near structural levels
  7. R:R pre-check — suppress if < 2:1 — entry_gates.rr_gate
  8. Candle close confirmation — skip forming candles — entry_gates.candle_close_gate
  9. Session timing — skip Sunday early morning — entry_gates.session_timing_gate

Based on MORPHO observation: 0.22% drop in 1 minute after tight consolidation.
Book sources: Porwal (engulfing at S/R), Woods (engulfing + volume + context)
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
    ENGULFING_PLUS_ENABLED,
    ENGULFING_MINUS_ENABLED,
    ENGULFING_MIN_MOVE, ENGULFING_PRIOR_RANGE,
    ENGULFING_LOOKBACK,
    ENGULFING_CONF_BASE, ENGULFING_CONF_CAP,
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
    _VALID_TABLES = {'candles_1m', 'candles_5m', 'candles_1h'}
    if table not in _VALID_TABLES:
        return []
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


def _get_5m_candles(token, limit=100):
    """Fetch 5m OHLCV candles for S/R detection."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close, volume FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        if not rows:
            return []
        return [{'open': r[0], 'high': r[1], 'low': r[2], 'close': r[3], 'volume': r[4]}
                for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_15m_trend(token):
    """Check 15m EMA20/50 trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_15m
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


def _is_near_sr(token, price, direction, candles_5m):
    """Check if price is near a structural S/R level.

    Returns True if within 4× ATR of a swing level on the reward side.
    """
    if not candles_5m or len(candles_5m) < 30:
        return False  # no data — don't block

    closes = [c['close'] for c in candles_5m]

    # Detect swing highs/lows
    swing_highs = []
    swing_lows = []
    n = 3
    for i in range(n, len(closes) - n):
        window = closes[i - n:i + n + 1]
        if closes[i] == max(window):
            swing_highs.append(closes[i])
        if closes[i] == min(window):
            swing_lows.append(closes[i])

    # Get ATR for proximity check
    try:
        import json
        from paths import ATR_CACHE_FILE
        with open(ATR_CACHE_FILE) as f:
            cache = json.load(f)
        atr_entry = cache.get(token.upper(), {})
        atr_pct = atr_entry.get('atr_pct', atr_entry.get('atr', 0.03))
    except Exception:
        atr_pct = 0.03

    atr_dist = price * atr_pct * 4  # 4× ATR proximity

    if direction == 'LONG':
        # Near support = swing low below price
        targets = [l for l in swing_lows if l < price and (price - l) <= atr_dist]
        return len(targets) > 0
    else:
        # Near resistance = swing high above price
        targets = [h for h in swing_highs if h > price and (h - price) <= atr_dist]
        return len(targets) > 0


def detect_engulfing(candles):
    """Detect engulfing candle pattern with body-vs-body check.

    Returns {direction, confidence, value, price} or None.
    """
    if len(candles) < ENGULFING_LOOKBACK + 2:
        return None

    current = candles[-1]
    prev = candles[-2]

    # Body sizes
    current_body = abs(current['close'] - current['open'])
    prev_body = abs(prev['close'] - prev['open'])

    # TRUE ENGULFING: current body must be larger than previous body
    if current_body <= prev_body:
        return None

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

    # Confidence based on move strength + body ratio
    conf = ENGULFING_CONF_BASE
    if move_pct > 0.30:
        conf += 10
    elif move_pct > 0.20:
        conf += 5
    # Body ratio bonus: much larger body = stronger signal
    if prev_body > 0:
        body_ratio = current_body / prev_body
        if body_ratio > 2.0:
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

        # Get 1m candles
        raw_candles = _get_candles(token, 'candles_1m', 100)
        if not raw_candles:
            continue

        # GATE: Candle close — use only confirmed closes
        candles = candle_close_gate(raw_candles, timeframe_seconds=60)
        if len(candles) < 2:
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

        # GATE: 15m trend alignment — block counter-trend engulfing
        trend = _get_15m_trend(token)
        if trend == 'BULLISH' and direction == 'SHORT':
            _log(f"{token} SHORT BLOCKED trend={trend} (counter-trend)")
            continue
        if trend == 'BEARISH' and direction == 'LONG':
            _log(f"{token} LONG BLOCKED trend={trend} (counter-trend)")
            continue

        # GATE: Volume confirmation
        if not volume_gate(candles, min_ratio=1.2):
            continue

        # GATE: R:R pre-check — need 5m candles for S/R detection
        candles_5m = _get_5m_candles(token, 100)
        rr_pass, sl, tp, rr = rr_gate(token, direction, price, candles_5m)
        if not rr_pass:
            continue

        # Confidence bonus: near S/R = higher quality entry
        near_sr = _is_near_sr(token, price, direction, candles_5m)
        if near_sr:
            sig['confidence'] = min(sig['confidence'] + 5, 88)

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
            _log(f"{token} {direction} conf={sig['confidence']} move={sig['value']:.3f}% "
                 f"trend={trend} sr={near_sr} rr={rr:.1f}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_engulfing_signals()


if __name__ == '__main__':
    n = scan_engulfing_signals()
    print(f"engulfing: {n} signals emitted")
