#!/usr/bin/env python3
"""
bollinger_squeeze.py — Bollinger Band Squeeze + Breakout signal.

Uses raw price_history ticks (no OHLCV candles needed).
Aggregates ticks into 5m candles on the fly.

Signal logic:
  1. Squeeze: bandwidth (upper-lower)/mid < threshold → energy building
  2. Breakout: price crosses band after squeeze → directional signal
  3. Confidence: based on squeeze duration + breakout magnitude + volume

Source tag: bb-squeeze
"""

import sys, os, sqlite3, math, time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal
from paths import RUNTIME_DB, STATIC_DB
import hermes_constants as hc

# ── Pull all constants from hermes_constants ──────────────────────────────────
BB_PERIOD       = hc.BOLLINGER_SQUEEZE_PERIOD
BB_MULT         = hc.BOLLINGER_SQUEEZE_MULT
SQUEEZE_THRESH  = hc.BOLLINGER_SQUEEZE_THRESH
SQUEEZE_MIN_BARS= hc.BOLLINGER_SQUEEZE_MIN_BARS
BREAK_PCT       = hc.BOLLINGER_SQUEEZE_BREAK_PCT
CANDLE_SECONDS  = hc.BOLLINGER_SQUEEZE_CANDLE_SEC
LOOKBACK_HOURS  = hc.BOLLINGER_SQUEEZE_LOOKBACK_H
COOLDOWN_MIN    = hc.BOLLINGER_SQUEEZE_COOLDOWN_MIN
SIGNAL_TYPE_L   = 'bollinger_squeeze_long'
SIGNAL_TYPE_S   = 'bollinger_squeeze_short'
SOURCE_TAG      = 'bb-squeeze'

_runtime_db = RUNTIME_DB
_static_db  = STATIC_DB


def _get_ticks(token, cutoff_ts):
    """Fetch recent ticks for a token from price_history."""
    conn = sqlite3.connect(_static_db)
    c = conn.cursor()
    c.execute(
        'SELECT price, timestamp FROM price_history WHERE token = ? AND timestamp > ? ORDER BY timestamp',
        (token, cutoff_ts))
    rows = c.fetchall()
    conn.close()
    return rows


def _aggregate_candles(ticks, candle_seconds=CANDLE_SECONDS):
    """Aggregate ticks into OHLCV candles. Returns list of (ts, open, high, low, close, vol)."""
    if not ticks:
        return []
    buckets = defaultdict(lambda: [None, 0, 0, 0, 0])
    for price, ts in ticks:
        bucket = ts // candle_seconds
        b = buckets[bucket]
        if b[0] is None:
            b[0] = price
        b[1] = max(b[1], price)
        b[2] = b[1] if b[2] == 0 else min(b[2], price)
        b[3] = price
        b[4] += 1
    candles = []
    for bucket in sorted(buckets.keys()):
        o, h, l, c, v = buckets[bucket]
        if o is not None:
            candles.append((bucket * candle_seconds, o, h, l, c, v))
    return candles


def _compute_bb(candles, period=BB_PERIOD, mult=BB_MULT):
    """Compute Bollinger Bands. Returns list of (ts, sma, upper, lower, bandwidth)."""
    if len(candles) < period:
        return []
    closes = [c[4] for c in candles]
    results = []
    for i in range(period - 1, len(candles)):
        window = closes[i - period + 1:i + 1]
        sma = sum(window) / period
        variance = sum((x - sma) ** 2 for x in window) / period
        stddev = math.sqrt(variance)
        upper = sma + mult * stddev
        lower = sma - mult * stddev
        bw = (upper - lower) / sma if sma > 0 else 0
        results.append((candles[i][0], sma, upper, lower, bw))
    return results


def _detect_signal(bb_series, candles):
    """Detect squeeze → breakout pattern. Returns (direction, confidence, details) or None."""
    if len(bb_series) < SQUEEZE_MIN_BARS + 2:
        return None

    recent = bb_series[-(SQUEEZE_MIN_BARS + 2):]
    latest = bb_series[-1]
    latest_close = candles[-1][4]

    squeeze_bars = 0
    for ts, sma, upper, lower, bw in recent[:-1]:
        if bw < SQUEEZE_THRESH:
            squeeze_bars += 1

    if squeeze_bars < SQUEEZE_MIN_BARS:
        return None

    _, sma, upper, lower, bw = latest
    prev_upper = recent[-2][2]
    prev_lower = recent[-2][3]
    prev_close = candles[-2][4]

    if latest_close > upper and prev_close <= prev_upper:
        pct_above = (latest_close - upper) / upper * 100 if upper > 0 else 0
        if pct_above >= BREAK_PCT:
            conf = min(85, 60 + squeeze_bars * 2 + int(pct_above * 5))
            return ('LONG', conf, f'squeeze={squeeze_bars}bars break={pct_above:.2f}%')

    if latest_close < lower and prev_close >= prev_lower:
        pct_below = (lower - latest_close) / lower * 100 if lower > 0 else 0
        if pct_below >= BREAK_PCT:
            conf = min(85, 60 + squeeze_bars * 2 + int(pct_below * 5))
            return ('SHORT', conf, f'squeeze={squeeze_bars}bars break={pct_below:.2f}%')

    return None


def _in_cooldown(token, direction):
    """Check if token+direction is in cooldown."""
    try:
        conn = sqlite3.connect(_runtime_db)
        c = conn.cursor()
        c.execute('''
            SELECT 1 FROM cooldown_tracker
            WHERE token = ? AND direction = ? AND expires_at > datetime('now')
        ''', (token.upper(), direction))
        r = c.fetchone()
        conn.close()
        return r is not None
    except Exception:
        return False


def scan_bollinger_squeeze():
    """Main scan entry point. Called by signals_runner."""
    t0 = time.time()
    cutoff_ts = int(time.time()) - (LOOKBACK_HOURS * 3600)

    conn = sqlite3.connect(_static_db)
    c = conn.cursor()
    c.execute('SELECT DISTINCT token FROM price_history WHERE timestamp > ?', (cutoff_ts,))
    tokens = [r[0] for r in c.fetchall()]
    conn.close()

    signals_found = []

    for token in tokens:
        ticks = _get_ticks(token, cutoff_ts)
        if len(ticks) < BB_PERIOD * 3:
            continue

        candles = _aggregate_candles(ticks)
        if len(candles) < BB_PERIOD + 2:
            continue

        bb = _compute_bb(candles)
        if not bb:
            continue

        result = _detect_signal(bb, candles)
        if result is None:
            continue

        direction, confidence, details = result

        # Check directional enable flags
        if direction == 'LONG' and not hc.BOLLINGER_SQUEEZE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not hc.BOLLINGER_SQUEEZE_MINUS_ENABLED:
            continue

        if _in_cooldown(token, direction):
            continue

        price = candles[-1][4]
        signal_type = SIGNAL_TYPE_L if direction == 'LONG' else SIGNAL_TYPE_S
        source_tag = f'{SOURCE_TAG}+' if direction == 'LONG' else f'{SOURCE_TAG}-'

        add_signal(
            token=token,
            direction=direction,
            signal_type=signal_type,
            source=source_tag,
            confidence=confidence,
            value=details,
            price=price,
            timeframe='5m',
        )
        signals_found.append(f'{token} {direction} conf={confidence} {details}')

    elapsed = time.time() - t0
    if signals_found:
        print(f'  [bb-squeeze] {len(signals_found)} signals in {elapsed:.1f}s: {signals_found}')
    else:
        print(f'  [bb-squeeze] 0 signals in {elapsed:.1f}s')

    return signals_found


if __name__ == '__main__':
    scan_bollinger_squeeze()
