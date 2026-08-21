#!/usr/bin/env python3
"""
atr_spike.py — Catch staged LONG moves from ATR compression.

When ATR compresses to historic lows and price starts moving up,
fire a LONG signal. Quality over quantity — trend alignment and
EMA proximity gates filter noise.

Data: price_history (signals_hermes.db) — 1m close prices
Speed: Fast (iterates all tokens, ~10s)

Signal type: atr_spike_long
Source tag:  atr-spike+
"""

import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import STATIC_DB, RUNTIME_DB

from hermes_constants import (
    ATR_SPIKE_ENABLED,
    ATR_SPIKE_PLUS_ENABLED,
    ATR_SPIKE_COMPRESSION_MAX_PCT,
    ATR_SPIKE_COMPRESSION_MIN_BARS,
    ATR_SPIKE_BREAKOUT_MIN_PCT,
    ATR_SPIKE_TREND_FILTER,
    ATR_SPIKE_EMA_PROXIMITY_PCT,
    ATR_SPIKE_SL_PCT,
    ATR_SPIKE_CONF_BASE,
    ATR_SPIKE_CONF_PCT_BOOST,
    ATR_SPIKE_CONF_CAP,
    ATR_SPIKE_COOLDOWN_MIN,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'atr_spike_long'
SOURCE_LONG = 'atr-spike+'

_PRICE_DB = STATIC_DB


def _get_closes_1m(token: str, lookback: int = 120) -> list:
    """Fetch 1m close prices from price_history, oldest first."""
    conn = None
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
        """, (token.upper(), lookback))
        rows = c.fetchall()
        if not rows:
            return []
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []
        return [r[1] for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _compute_atr(closes: list, period: int = 14) -> float:
    """ATR-14 from close prices (approximated as avg absolute bar-to-bar change)."""
    if len(closes) < period + 1:
        return 0.0
    changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    if not changes:
        return 0.0
    atr = sum(changes[:period]) / period
    for c in changes[period:]:
        atr = (atr * (period - 1) + c) / period
    return atr


def _check_trend_alignment(token: str) -> bool:
    """Check if EMA20 > EMA50 on 15m candles (uptrend)."""
    if not ATR_SPIKE_TREND_FILTER:
        return True
    try:
        from paths import CANDLES_DB
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT close FROM candles_15m
                WHERE token = ? ORDER BY ts DESC LIMIT 60
            """, (token.upper(),))
            rows = cur.fetchall()
            if len(rows) < 50:
                return True  # can't check, assume aligned
            closes = [r[0] for r in reversed(rows)]

            # EMA20
            k20 = 2 / 21
            ema20 = closes[0]
            for p in closes[1:]:
                ema20 = p * k20 + ema20 * (1 - k20)

            # EMA50
            k50 = 2 / 51
            ema50 = closes[0]
            for p in closes[1:]:
                ema50 = p * k50 + ema50 * (1 - k50)

            return ema20 > ema50
        finally:
            conn.close()
    except Exception:
        return True  # fail open


def _check_ema_proximity(token: str) -> bool:
    """Check if price is within ATR_SPIKE_EMA_PROXIMITY_PCT of EMA20 on 15m."""
    if ATR_SPIKE_EMA_PROXIMITY_PCT <= 0:
        return True
    try:
        from paths import CANDLES_DB
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT close FROM candles_15m
                WHERE token = ? ORDER BY ts DESC LIMIT 30
            """, (token.upper(),))
            rows = cur.fetchall()
            if len(rows) < 20:
                return True
            closes = [r[0] for r in reversed(rows)]

            # EMA20
            k20 = 2 / 21
            ema20 = closes[0]
            for p in closes[1:]:
                ema20 = p * k20 + ema20 * (1 - k20)

            current = closes[-1]
            dist_pct = abs(current - ema20) / ema20 * 100
            return dist_pct <= ATR_SPIKE_EMA_PROXIMITY_PCT
        finally:
            conn.close()
    except Exception:
        return True  # fail open


def detect(token: str) -> dict | None:
    """Detect ATR compression breakout for a single token.
    Returns {direction, confidence, value, price} or None.
    """
    closes = _get_closes_1m(token, lookback=120)
    if len(closes) < 30:
        return None

    current_price = closes[-1]
    prev_price = closes[-2]
    candle_pct = (current_price - prev_price) / prev_price * 100

    # Must be a green candle
    if candle_pct <= 0:
        return None

    # Must meet breakout threshold
    if candle_pct < ATR_SPIKE_BREAKOUT_MIN_PCT:
        return None

    # Check compression: ATR in last 15 candles must be below threshold
    recent_atrs = []
    for i in range(max(15, len(closes) - 60), len(closes) - 1):
        window = closes[max(0, i - 14):i + 1]
        atr = _compute_atr(window)
        price = closes[i] if i < len(closes) else closes[-1]
        atr_pct = atr / price * 100 if price > 0 else 999
        recent_atrs.append(atr_pct)

    if not recent_atrs:
        return None

    # Current ATR must be below threshold
    current_atr = _compute_atr(closes[-15:])
    current_atr_pct = current_atr / current_price * 100 if current_price > 0 else 999
    if current_atr_pct >= ATR_SPIKE_COMPRESSION_MAX_PCT:
        return None

    # Must have been compressed for minimum duration
    compressed_count = sum(1 for a in recent_atrs if a < ATR_SPIKE_COMPRESSION_MAX_PCT)
    if compressed_count < ATR_SPIKE_COMPRESSION_MIN_BARS:
        return None

    # Quality gates
    if not _check_trend_alignment(token):
        return None
    if not _check_ema_proximity(token):
        return None

    # Confidence based on breakout magnitude
    conf = ATR_SPIKE_CONF_BASE + (candle_pct / ATR_SPIKE_BREAKOUT_MIN_PCT - 1) * ATR_SPIKE_CONF_PCT_BOOST
    conf = min(conf, ATR_SPIKE_CONF_CAP)
    conf = max(conf, 50)

    return {
        'direction': 'LONG',
        'confidence': round(conf, 1),
        'value': round(candle_pct, 4),
        'price': current_price,
    }


def scan_signals() -> int:
    """Scan all tokens for ATR spike signals."""
    added = 0

    from signal_schema import get_all_latest_prices
    prices_dict = get_all_latest_prices()

    for token in prices_dict:
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue

        # Cooldown check
        if get_cooldown(token, direction='LONG'):
            continue

        sig = detect(token)
        if not sig:
            continue

        # Per-direction kill-switch
        if not ATR_SPIKE_PLUS_ENABLED:
            continue

        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=SIGNAL_TYPE_LONG,
            source=SOURCE_LONG,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=1)

    return added


def run():
    """Entry point for signals_runner."""
    if not ATR_SPIKE_ENABLED:
        return 0
    return scan_signals()
