#!/usr/bin/env python3
"""Volume Climax — Extreme volume spike + rejection candle = reversal.

From Warrior Trading: "When you see massive volume with a rejection candle
(wick), it signals institutional exhaustion." This is a reversal signal that
fires when volume climaxes at a price extreme.

DIFFERENT from exhaustion (which uses RSI/price extension):
  - This is purely volume + wick based (no RSI dependency)
  - Focuses on VOLUME CLIMAX specifically (not just overextension)
  - Wick rejection is the key confirmation (not just price level)

DIFFERENT from volume_breakout (which fires ON the volume spike):
  - This fires on the REJECTION after the spike
  - The spike happened, now price is rejecting the extreme
  - Reversal setup, not continuation

THESIS: When volume spikes to extreme levels and price rejects (long wick),
it means institutions are taking the other side. The crowd pushed price to
an extreme, and smart money is fading it. This is a high-probability reversal.

LOGIC:
  1. Volume spike: current volume > N× average (configurable)
  2. Rejection candle: long wick in the direction of the spike
  3. Price at an extreme: near recent high (SHORT) or low (LONG)
  4. Wick ratio: wick must be > X× body (strong rejection)
  5. Optional: 1h trend alignment for confirmation
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
    VOLUME_CLIMAX_ENABLED,
    VOLUME_CLIMAX_PLUS_ENABLED,
    VOLUME_CLIMAX_MINUS_ENABLED,
    VOLUME_CLIMAX_LOOKBACK,
    VOLUME_CLIMAX_SPIKE_MULT,
    VOLUME_CLIMAX_AVG_PERIOD,
    VOLUME_CLIMAX_WICK_RATIO,
    VOLUME_CLIMAX_EXTREME_WINDOW,
    VOLUME_CLIMAX_CONF_BASE,
    VOLUME_CLIMAX_CONF_CAP,
    VOLUME_CLIMAX_COOLDOWN_HOURS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'volume_climax_long'
SIGNAL_TYPE_SHORT = 'volume_climax_short'
SOURCE_LONG = 'volume-climax+'
SOURCE_SHORT = 'volume-climax-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[volume-climax] {msg}", flush=True)


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


def _is_at_extreme(candles, direction):
    """Check if current price is at a recent extreme (high for SHORT, low for LONG).

    Returns True if price is within top/bottom 10% of recent range.
    """
    if len(candles) < VOLUME_CLIMAX_EXTREME_WINDOW:
        return False

    recent = candles[-VOLUME_CLIMAX_EXTREME_WINDOW:]
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    range_high = max(highs)
    range_low = min(lows)

    if range_high == range_low:
        return False

    current_price = candles[-1]['close']
    range_size = range_high - range_low

    if direction == 'SHORT':
        # At extreme HIGH: price in top 10% of range
        position = (current_price - range_low) / range_size
        return position > 0.90
    else:
        # At extreme LOW: price in bottom 10% of range
        position = (current_price - range_low) / range_size
        return position < 0.10


def detect_volume_climax(candles):
    """Detect volume climax + rejection candle.

    Returns {direction, confidence, value, price} or None.
    """
    if len(candles) < max(VOLUME_CLIMAX_LOOKBACK, VOLUME_CLIMAX_AVG_PERIOD + 5):
        return None

    current = candles[-1]
    price = current['close']
    if price <= 0:
        return None

    # Volume spike check
    avg_vol = sum(c['volume'] for c in candles[-VOLUME_CLIMAX_AVG_PERIOD - 1:-1]) / VOLUME_CLIMAX_AVG_PERIOD
    if avg_vol <= 0:
        return None

    vol_ratio = current['volume'] / avg_vol
    if vol_ratio < VOLUME_CLIMAX_SPIKE_MULT:
        return None

    # Candle analysis
    body = abs(current['close'] - current['open'])
    if body == 0:
        return None

    upper_wick = current['high'] - max(current['open'], current['close'])
    lower_wick = min(current['open'], current['close']) - current['low']

    # Determine direction based on rejection
    # SHORT: rejection at highs (long upper wick = sellers rejecting higher prices)
    # LONG: rejection at lows (long lower wick = buyers rejecting lower prices)

    if upper_wick > body * VOLUME_CLIMAX_WICK_RATIO:
        # Bearish rejection: long upper wick
        direction = 'SHORT'
        wick_ratio = upper_wick / body
        # Must be at extreme high
        if not _is_at_extreme(candles, 'SHORT'):
            return None
    elif lower_wick > body * VOLUME_CLIMAX_WICK_RATIO:
        # Bullish rejection: long lower wick
        direction = 'LONG'
        wick_ratio = lower_wick / body
        if not _is_at_extreme(candles, 'LONG'):
            return None
    else:
        return None  # no rejection candle

    # Confidence: base + volume strength + wick strength
    conf = VOLUME_CLIMAX_CONF_BASE

    # Volume bonus: stronger spike = higher confidence
    if vol_ratio > VOLUME_CLIMAX_SPIKE_MULT * 2:
        conf += 10  # extreme volume
    elif vol_ratio > VOLUME_CLIMAX_SPIKE_MULT * 1.5:
        conf += 5

    # Wick strength bonus
    if wick_ratio > 3.0:
        conf += 8  # very strong rejection
    elif wick_ratio > 2.0:
        conf += 5
    elif wick_ratio > 1.5:
        conf += 3

    conf = min(conf, VOLUME_CLIMAX_CONF_CAP)

    return {
        'direction': direction,
        'confidence': conf,
        'value': round(vol_ratio, 2),  # volume ratio as the value
        'price': price,
    }


def scan_volume_climax_signals():
    """Scan all tokens for volume climax setups."""
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
        raw_candles = _get_candles(token, 'candles_5m', VOLUME_CLIMAX_LOOKBACK)
        if not raw_candles:
            continue

        # GATE: Candle close
        candles = candle_close_gate(raw_candles, timeframe_seconds=300)
        if len(candles) < 20:
            continue

        sig = detect_volume_climax(candles)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: kill-switch
        if direction == 'LONG' and not VOLUME_CLIMAX_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not VOLUME_CLIMAX_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        # GATE: 1h trend alignment (optional — reverse against trend is fine for climax)
        # Volume climax is a REVERSAL signal, so we don't block counter-trend
        # But we DO boost confidence if aligned with trend
        trend = _get_1h_trend(token)
        if trend == 'BULLISH' and direction == 'LONG':
            sig['confidence'] = min(sig['confidence'] + 3, VOLUME_CLIMAX_CONF_CAP)
        if trend == 'BEARISH' and direction == 'SHORT':
            sig['confidence'] = min(sig['confidence'] + 3, VOLUME_CLIMAX_CONF_CAP)

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
            set_cooldown(token, direction, hours=VOLUME_CLIMAX_COOLDOWN_HOURS)
            _log(f"{token} {direction} conf={sig['confidence']} vol_ratio={sig['value']:.1f} "
                 f"trend={trend} rr={rr:.1f}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_volume_climax_signals()


if __name__ == '__main__':
    n = scan_volume_climax_signals()
    print(f"volume_climax: {n} signals emitted")
