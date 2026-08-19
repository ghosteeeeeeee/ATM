#!/usr/bin/env python3
"""
stop_hunt_reversal_long — Catch violent long after stop hunt.

Thesis: Sharp drops (stop hunts) are followed by violent reversals.
        The algo that triggered the stop hunt reverses price to grab
        liquidity on the other side. Buy the reversal.

Pattern:
  1. Sharp drop: >1% in <5 candles (stop hunt)
  2. Green reversal candle: close > open after the drop
  3. Enter LONG on confirmation
  4. Ride the violent move

Entry:  Stop hunt detected (>1% drop in 5 candles)
        + Green reversal candle (close > open)
        + Volume spike on reversal (optional confirmation)

Exit:   Stop below stop hunt low
        Trail at 0.5% from peak

Data:   candles_1m from candles.db
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA
from hermes_constants import (
    STOP_HUNT_REVERSAL_LONG_ENABLED,
    STOP_HUNT_REVERSAL_LONG_PLUS_ENABLED,
    STOP_HUNT_REVERSAL_LONG_DROP_THRESHOLD,
    STOP_HUNT_REVERSAL_LONG_DROP_WINDOW,
    STOP_HUNT_REVERSAL_LONG_REVERSAL_BODY_MIN,
    STOP_HUNT_REVERSAL_LONG_CONF_BASE,
    STOP_HUNT_REVERSAL_LONG_CONF_STRONG_REVERSAL,
    STOP_HUNT_REVERSAL_LONG_CONF_CAP,
    STOP_HUNT_REVERSAL_LONG_LARGE_HUNT,
    STOP_HUNT_REVERSAL_LONG_STRONG_REVERSAL,
    STOP_HUNT_REVERSAL_LONG_COOLDOWN_HOURS,
    STOP_HUNT_REVERSAL_LONG_TREND_SLOPE_MIN,
    STOP_HUNT_REVERSAL_LONG_TREND_WINDOW,
    LONG_BLACKLIST,
)
import sqlite3

_CANDLES_DB = None

def _get_db():
    global _CANDLES_DB
    if _CANDLES_DB is None:
        _CANDLES_DB = f'{HERMES_DATA}/candles.db'
    return _CANDLES_DB


def detect(token):
    """Check if token has a stop hunt + reversal pattern for LONG."""
    conn = None
    try:
        conn = sqlite3.connect(_get_db(), timeout=10)
        cur = conn.cursor()
        window = STOP_HUNT_REVERSAL_LONG_DROP_WINDOW + 10
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), window))
        rows = cur.fetchall()
        if len(rows) < window:
            return None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()

    # rows are newest-first, reverse for chronological
    candles = list(reversed(rows))
    closes = [c[4] for c in candles]
    opens = [c[1] for c in candles]
    lows = [c[3] for c in candles]
    highs = [c[2] for c in candles]

    # Look for stop hunt in the recent past (not the very latest candle)
    search_end = len(candles) - 2  # leave room for reversal + current
    search_start = max(0, search_end - STOP_HUNT_REVERSAL_LONG_DROP_WINDOW)

    # Find the lowest point (stop hunt low)
    best_drop = 0
    best_drop_start = 0
    best_drop_low = 0
    best_drop_low_idx = 0

    for start in range(search_start, search_end - 2):
        for end in range(start + 2, min(start + STOP_HUNT_REVERSAL_LONG_DROP_WINDOW + 1, search_end + 1)):
            start_price = closes[start]
            end_price = closes[end]
            if start_price <= 0:
                continue
            drop_pct = (start_price - end_price) / start_price  # positive = drop
            if drop_pct > best_drop:
                # Check if there's a low point below the end price
                low_point = min(lows[start:end + 1])
                if low_point < end_price:
                    best_drop = drop_pct
                    best_drop_start = start
                    best_drop_low = low_point
                    best_drop_low_idx = lows[start:end + 1].index(low_point) + start

    if best_drop < STOP_HUNT_REVERSAL_LONG_DROP_THRESHOLD:
        return None  # no significant stop hunt

    # Check for green reversal candle after the stop hunt low
    reversal_idx = best_drop_low_idx + 1
    if reversal_idx >= len(candles):
        return None

    reversal_candle = candles[reversal_idx]
    rev_open = reversal_candle[1]
    rev_close = reversal_candle[4]
    rev_low = reversal_candle[3]

    # Reversal: green candle (close > open) after the drop
    if rev_open <= 0 or rev_close <= rev_open:
        return None  # not a green reversal

    # Reversal body should be meaningful (not a doji)
    rev_body = (rev_close - rev_open) / rev_open
    if rev_body < STOP_HUNT_REVERSAL_LONG_REVERSAL_BODY_MIN:
        return None  # too small

    # Current price should be above reversal close (confirmation)
    current_price = closes[-1]
    if current_price < rev_close:
        return None  # price hasn't confirmed the reversal

    # ── Trend filter: block LONG when 1m slope is negative (downtrend) ──
    # Same principle as r2_trend_long: don't fight the trend.
    # Uses linear regression on last N candles to measure slope direction.
    trend_n = min(STOP_HUNT_REVERSAL_LONG_TREND_WINDOW, len(closes))
    if trend_n >= 10:
        trend_y = closes[-trend_n:]
        x_mean = (trend_n - 1) / 2.0
        y_mean = sum(trend_y) / trend_n
        cov = sum((i - x_mean) * (trend_y[i] - y_mean) for i in range(trend_n))
        var = sum((i - x_mean) ** 2 for i in range(trend_n))
        slope = cov / var if var > 0 else 0.0
        if slope < STOP_HUNT_REVERSAL_LONG_TREND_SLOPE_MIN:
            return None  # downtrend — don't catch falling knife

    # Confidence
    conf = STOP_HUNT_REVERSAL_LONG_CONF_BASE
    if best_drop > STOP_HUNT_REVERSAL_LONG_LARGE_HUNT:
        conf += 10
    if rev_body > STOP_HUNT_REVERSAL_LONG_STRONG_REVERSAL:
        conf += STOP_HUNT_REVERSAL_LONG_CONF_STRONG_REVERSAL
    conf = min(conf, STOP_HUNT_REVERSAL_LONG_CONF_CAP)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': best_drop,
        'price': current_price,
        'z_score': None,
    }


def scan_signals():
    """Scan all tokens and add signals via add_signal()."""
    if not STOP_HUNT_REVERSAL_LONG_ENABLED:
        return 0
    if not STOP_HUNT_REVERSAL_LONG_PLUS_ENABLED:
        return 0

    added = 0
    conn = None
    try:
        conn = sqlite3.connect(_get_db(), timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token FROM candles_1m
            WHERE ts > strftime('%s', 'now') - 3600
        """)
        tokens = [r[0] for r in cur.fetchall()]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

    for tok in tokens:
        if price_age_minutes(tok) > 10:
            continue
        if tok.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(tok, direction='LONG'):
            continue

        sig = detect(tok)
        if not sig:
            continue

        sid = add_signal(
            token=tok.upper(),
            direction='LONG',
            signal_type='stop_hunt_reversal_long',
            source='stop_hunt_reversal_long+',
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(tok, direction='LONG', hours=STOP_HUNT_REVERSAL_LONG_COOLDOWN_HOURS)

    return added


def run():
    return scan_signals()


if __name__ == '__main__':
    added = run()
    print(f'Added {added} signals')
