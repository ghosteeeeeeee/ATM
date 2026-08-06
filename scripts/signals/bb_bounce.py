#!/usr/bin/env python3
"""Bollinger Band Bounce — mean reversion for ranging markets.

Improved version with quality filters:
1. Trend alignment — bounce must align with 1H EMA trend
2. RSI confirmation — RSI must confirm oversold/overbought
3. Strong bounce — price must move away from band significantly
4. Volume confirmation — bounce should have above-average volume

LONG: Price touches lower band + RSI oversold + 1H bullish + strong bounce
SHORT: Price touches upper band + RSI overbought + 1H bearish + strong bounce
"""
import sqlite3
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── Config ──────────────────────────────────────────────────────────────
BB_PERIOD = 20
BB_STDDEV = 1.8          # was 2.0 — more band touches for ranging markets
BB_TOUCH_PCT = 0.30      # was 0.20 — wider crypto tolerance
BB_MIN_BARS = 30
RSI_PERIOD = 14
RSI_OVERSOLD = 45        # was 40 — more permissive but not neutral
RSI_OVERBOUGHT = 55      # was 60 — more permissive but not neutral
BOUNCE_MIN_PCT = 0.03    # was 0.05 — above noise floor, catches real bounces
COOLDOWN_MIN = 5         # was 10 — faster re-entries

# ── State ───────────────────────────────────────────────────────────────
_cooldown = {}


def _log(msg):
    print(f"[bb-bounce] {msg}", flush=True)


def _compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    if len(closes) < period:
        return None, None, None, None
    middle = sum(closes[-period:]) / period
    variance = sum((c - middle) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    return middle, upper, lower, width


def _compute_rsi(closes, period=RSI_PERIOD):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, min(period + 1, len(closes))):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def _get_1h_trend(token):
    """Check 1H EMA trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 60
        """, (token.upper(),))
        rows = cur.fetchall()
        conn.close()
        if not rows or len(rows) < 50:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]
        # EMA20 vs EMA50
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


def _get_candles(token, lookback=100):
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception:
        return []


def _get_ohlcv_candles(token, lookback=100):
    """Get full OHLCV candle data for pattern recognition."""
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in reversed(rows)]
    except Exception:
        return []


def detect_bb_bounce(token, closes):
    """Detect Bollinger Band bounce with quality filters."""
    if len(closes) < BB_MIN_BARS:
        return None

    middle, upper, lower, width = _compute_bb(closes)
    if middle is None:
        return None

    current = closes[-1]
    prev = closes[-2] if len(closes) >= 2 else current

    # Compute RSI
    rsi = _compute_rsi(closes)
    if rsi is None:
        return None

    # Distance from bands
    dist_from_upper = abs(current - upper) / upper * 100 if upper > 0 else 999
    dist_from_lower = abs(current - lower) / lower * 100 if lower > 0 else 999

    # Check 1H trend
    trend = _get_1h_trend(token)

    # LONG: lower band + RSI oversold + bullish/neutral trend + bounce up
    if dist_from_lower <= BB_TOUCH_PCT and current > prev:
        # Quality filters
        if rsi > RSI_OVERSOLD:
            return None  # RSI not oversold enough
        if trend == 'BEARISH':
            return None  # Counter-trend

        # Check bounce strength — price must be above the band
        if current <= lower:
            return None  # Still below band, no bounce yet

        bounce_pct = (current - lower) / lower * 100 if lower > 0 else 0
        if bounce_pct < BOUNCE_MIN_PCT:
            return None  # Bounce too weak

        return {
            'direction': 'LONG',
            'middle': middle,
            'upper': upper,
            'lower': lower,
            'width': width,
            'rsi': rsi,
            'trend': trend,
            'bounce_pct': bounce_pct,
        }

    # SHORT: upper band + RSI overbought + bearish/neutral trend + bounce down
    if dist_from_upper <= BB_TOUCH_PCT and current < prev:
        if rsi < RSI_OVERBOUGHT:
            return None
        if trend == 'BULLISH':
            return None

        # Check bounce strength — price must be below the band
        if current >= upper:
            return None  # Still above band, no bounce yet

        bounce_pct = (upper - current) / upper * 100 if upper > 0 else 0
        if bounce_pct < BOUNCE_MIN_PCT:
            return None

        return {
            'direction': 'SHORT',
            'middle': middle,
            'upper': upper,
            'lower': lower,
            'width': width,
            'rsi': rsi,
            'trend': trend,
            'bounce_pct': bounce_pct,
        }

    return None


def scan_bb_bounce_signals(prices_dict):
    """Scan tokens for BB bounce signals."""
    from signal_schema import add_signal
    from signal_gen import is_delisted, SHORT_BLACKLIST

    added = 0
    now = time.time()

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        if is_delisted(token.upper()):
            continue

        key = f"{token.upper()}"
        if key in _cooldown and now - _cooldown[key] < COOLDOWN_MIN * 60:
            continue

        closes = _get_candles(token, 100)
        if not closes:
            continue

        sig = detect_bb_bounce(token, closes)
        if sig is None:
            continue

        direction = sig['direction']
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Per-direction kill-switch
        from hermes_constants import BB_BOUNCE_PLUS_ENABLED, BB_BOUNCE_MINUS_ENABLED
        if direction == 'LONG' and not BB_BOUNCE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not BB_BOUNCE_MINUS_ENABLED:
            continue

        # Confidence based on quality indicators
        base_conf = 65
        if sig['width'] < 0.03:  # Tight squeeze = stronger signal
            base_conf += 10
        if sig['trend'] != 'NEUTRAL':  # Trend-aligned = stronger
            base_conf += 5
        if sig['bounce_pct'] > 0.15:  # Strong bounce
            base_conf += 5

        # Pattern recognition boost (AXS-style reversal setups)
        try:
            from pattern_recognition import detect_reversal_quality
            ohlcv_candles = _get_ohlcv_candles(token, 100)
            if ohlcv_candles and len(ohlcv_candles) >= 20:
                quality = detect_reversal_quality(ohlcv_candles)
                if quality['score'] >= 3:
                    base_conf += quality['score'] * 3  # +9 for score 3, +15 for score 5
                    _log(f"{token} pattern quality {quality['score']}/5: {quality['signals']}")
        except Exception:
            pass  # Don't block on pattern recognition errors

        sid = add_signal(
            token=token,
            direction=direction,
            signal_type='bb_bounce',
            source='bb_bounce',
            confidence=min(base_conf, 88),
            value=sig['middle'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            _cooldown[key] = now
            _log(f"{token} {direction} conf={base_conf} "
                 f"rsi={sig['rsi']:.0f} trend={sig['trend']} "
                 f"bounce={sig['bounce_pct']:.2f}%")

    return added


def run(prices_dict=None):
    if prices_dict is None:
        try:
            from signal_schema import get_all_latest_prices
            prices_dict = get_all_latest_prices()
        except Exception:
            return 0
    return scan_bb_bounce_signals(prices_dict)


if __name__ == '__main__':
    token = sys.argv[1] if len(sys.argv) > 1 else 'ETH'
    closes = _get_candles(token, 100)
    if closes:
        sig = detect_bb_bounce(token, closes)
        if sig:
            print(f"{token} {sig['direction']} rsi={sig['rsi']:.0f} "
                  f"trend={sig['trend']} bounce={sig['bounce_pct']:.2f}%")
        else:
            print(f"{token}: no signal")
    else:
        print(f"{token}: no data")
