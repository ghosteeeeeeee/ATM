#!/usr/bin/env python3
"""
ema300_breakthrough.py — Price crashes through EMA300 with momentum.

15m candle detection:
- SHORT: price was above EMA300, crashes through downward (trend continuation)
- LONG: price was below EMA300, reverses through upward (reversal)

Backtested: SHORT 80% WR (15T), LONG 61% WR (54T).

Source: ema300-breakthrough+
Classification: Trend-following (SHORT = continuation, LONG = reversal)
"""

import sqlite3
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    EMA300_BREAKTHROUGH_ENABLED,
    EMA300_BREAKTHROUGH_PLUS_ENABLED,
    EMA300_BREAKTHROUGH_MINUS_ENABLED,
    EMA300_BREAKTHROUGH_EMA_PERIOD,
    EMA300_BREAKTHROUGH_MIN_BODY_RATIO,
    EMA300_BREAKTHROUGH_MIN_GAP_PCT,
    EMA300_BREAKTHROUGH_PRE_MOVE_WINDOW,
    EMA300_BREAKTHROUGH_PRE_MOVE_SHORT,
    EMA300_BREAKTHROUGH_PRE_MOVE_LONG,
    EMA300_BREAKTHROUGH_MIN_ATR_PCT,
    EMA300_BREAKTHROUGH_COOLDOWN,
    EMA300_BREAKTHROUGH_CONF_BASE,
    EMA300_BREAKTHROUGH_CONF_CAP,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'ema300_breakthrough_long'
SIGNAL_TYPE_SHORT = 'ema300_breakthrough_short'
SOURCE_LONG = 'ema300-breakthrough+'
SOURCE_SHORT = 'ema300-breakthrough-'

_CANDLES_DB = CANDLES_DB


def _get_candles_15m(token, limit=500):
    """Fetch 15m candles from candles.db. Returns oldest-first list."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT open, high, low, close, volume FROM candles_15m
            WHERE token = ? AND is_closed = 1 ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [{'open': r[0], 'high': r[1], 'low': r[2], 'close': r[3], 'volume': r[4]}
                for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _compute_ema(prices, period):
    """Compute EMA for a list of prices."""
    if not prices or len(prices) < period:
        return prices[-1] if prices else 0
    k = 2.0 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def _compute_atr(candles, period=14):
    """Compute ATR over last `period` candles."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]['high'], candles[i]['low'], candles[i-1]['close']
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    return atr


def _detect_breakthrough(token, candles):
    """Detect EMA300 breakthrough on 15m timeframe.

    Returns {direction, confidence, value, price} or None.
    """
    n = len(candles)
    if n < EMA300_BREAKTHROUGH_EMA_PERIOD + 20:
        return None

    closes = [c['close'] for c in candles]
    price = closes[-1]

    # Compute EMA300
    ema_vals = []
    ema = closes[0]
    k = 2.0 / (EMA300_BREAKTHROUGH_EMA_PERIOD + 1)
    for c in closes:
        ema = c * k + ema * (1 - k)
        ema_vals.append(ema)

    current_ema = ema_vals[-1]
    prev_ema = ema_vals[-2]

    # Current and previous candle
    curr = candles[-1]
    prev = candles[-2]

    # Body ratio check
    rng = curr['high'] - curr['low']
    if rng <= 0:
        return None
    body = abs(curr['close'] - curr['open'])
    body_ratio = body / rng

    if body_ratio < EMA300_BREAKTHROUGH_MIN_BODY_RATIO:
        return None

    # ATR check (avoid ultra-low-vol noise)
    atr = _compute_atr(candles)
    if atr is None:
        return None
    atr_pct = (atr / price) * 100
    if atr_pct < EMA300_BREAKTHROUGH_MIN_ATR_PCT:
        return None

    # Pre-move: price change over PRE_MOVE_WINDOW bars before current
    pre_window = EMA300_BREAKTHROUGH_PRE_MOVE_WINDOW
    if len(closes) < pre_window + 2:
        return None
    pre_move_price = closes[-(pre_window + 1)]
    pre_move = (closes[-2] - pre_move_price) / pre_move_price * 100

    # Gap at close: distance from EMA300 after breakout
    gap_pct = abs(curr['close'] - current_ema) / current_ema * 100

    # ── SHORT detection: price crashes through EMA300 downward ──────────
    # Previous candle closed ABOVE EMA300, current closes BELOW
    if prev['close'] > prev_ema and curr['close'] < current_ema:
        # Must be red candle
        if curr['close'] >= curr['open']:
            return None

        # Pre-move must show downtrend (price was falling)
        if pre_move > EMA300_BREAKTHROUGH_PRE_MOVE_SHORT:
            return None

        # Gap must confirm breakout
        if gap_pct < EMA300_BREAKTHROUGH_MIN_GAP_PCT:
            return None

        # Confidence scoring
        conf = EMA300_BREAKTHROUGH_CONF_BASE
        # Body strength bonus (up to +8)
        body_bonus = min(8, int((body_ratio - EMA300_BREAKTHROUGH_MIN_BODY_RATIO) / 0.10 * 8))
        conf += body_bonus
        # Pre-move magnitude bonus (up to +5) — stronger pre-move = more continuation
        pre_move_strength = min(5, int(abs(pre_move) / 3.0 * 5))
        conf += pre_move_strength
        # Gap size bonus (up to +5) — larger gap = cleaner breakout
        gap_bonus = min(5, int(gap_pct / 1.0 * 5))
        conf += gap_bonus
        conf = min(conf, EMA300_BREAKTHROUGH_CONF_CAP)

        return {
            'direction': 'SHORT',
            'confidence': conf,
            'source': SOURCE_SHORT,
            'signal_type': SIGNAL_TYPE_SHORT,
            'price': price,
            'value': float(conf),
            'pre_move': round(pre_move, 2),
            'gap_pct': round(gap_pct, 3),
            'body_ratio': round(body_ratio, 3),
            'atr_pct': round(atr_pct, 3),
        }

    # ── LONG detection: price reverses through EMA300 upward ────────────
    # Previous candle closed BELOW EMA300, current closes ABOVE
    if prev['close'] < prev_ema and curr['close'] > current_ema:
        # Must be green candle
        if curr['close'] <= curr['open']:
            return None

        # Pre-move must show prior decline (reversal, not trend continuation)
        if pre_move > EMA300_BREAKTHROUGH_PRE_MOVE_LONG:
            return None

        # Gap must confirm breakout
        if gap_pct < EMA300_BREAKTHROUGH_MIN_GAP_PCT:
            return None

        # Confidence scoring
        conf = EMA300_BREAKTHROUGH_CONF_BASE
        # Body strength bonus (up to +8)
        body_bonus = min(8, int((body_ratio - EMA300_BREAKTHROUGH_MIN_BODY_RATIO) / 0.10 * 8))
        conf += body_bonus
        # Pre-move magnitude bonus (up to +5) — stronger decline = bigger reversal potential
        pre_move_strength = min(5, int(abs(pre_move) / 3.0 * 5))
        conf += pre_move_strength
        # Gap size bonus (up to +5)
        gap_bonus = min(5, int(gap_pct / 1.0 * 5))
        conf += gap_bonus
        conf = min(conf, EMA300_BREAKTHROUGH_CONF_CAP)

        return {
            'direction': 'LONG',
            'confidence': conf,
            'source': SOURCE_LONG,
            'signal_type': SIGNAL_TYPE_LONG,
            'price': price,
            'value': float(conf),
            'pre_move': round(pre_move, 2),
            'gap_pct': round(gap_pct, 3),
            'body_ratio': round(body_ratio, 3),
            'atr_pct': round(atr_pct, 3),
        }

    return None


def scan_signals() -> int:
    """Scan all tokens for EMA300 breakthrough setups."""
    from signal_schema import get_all_latest_prices

    if not EMA300_BREAKTHROUGH_ENABLED:
        return 0

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue

        if price_age_minutes(token) > 15:
            continue

        candles = _get_candles_15m(token, limit=EMA300_BREAKTHROUGH_EMA_PERIOD + 50)
        if not candles or len(candles) < EMA300_BREAKTHROUGH_EMA_PERIOD + 20:
            continue

        sig = _detect_breakthrough(token, candles)
        if sig is None:
            continue

        direction = sig['direction']

        # Kill-switch
        if direction == 'LONG' and not EMA300_BREAKTHROUGH_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not EMA300_BREAKTHROUGH_MINUS_ENABLED:
            continue

        # Blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig['signal_type'],
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='15m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction=direction, hours=EMA300_BREAKTHROUGH_COOLDOWN / 60)
            print(f'  {direction:5s} {token:8s} conf={sig["confidence"]:.0f}% '
                  f'pre_move={sig["pre_move"]:+.2f}% gap={sig["gap_pct"]:.3f}% '
                  f'body={sig["body_ratio"]:.2f} [{sig["source"]}]')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    prices = get_all_latest_prices()
    test_tokens = {k: v for k, v in prices.items()
                   if k in ('ARB', 'CFX', 'FIL', 'AVNT', 'SYRUP', 'ENA', 'JUP') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])
    print(f"[ema300_breakthrough] Testing on {len(test_tokens)} tokens...")
    n = scan_signals()
    print(f"[ema300_breakthrough] Done. {n} signals emitted.")
