#!/usr/bin/env python3
"""resistance_break.py — Early breakout signal via resistance break detection.

Detects when price breaks above a tested resistance level and enters on the
pullback retest. This catches the same moves as open-skies but 7+ hours earlier.

Detection:
  1. Find resistance: max high in 200-bar lookback (1m candles)
  2. Count touches: how many times price tested this resistance
  3. Breakout: close exceeds resistance level
  4. Pullback: price dips back toward resistance (retest)
  5. Trend alignment: price above 50-bar EMA
  6. Volume confirmation: volume spike at breakout

Signal types:
  - resistance_break_long : LONG breakout

Pipeline: runs as a fast signal (every minute) via signals_runner.
"""
import sys
import os
import sqlite3
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    RESISTANCE_BREAK_ENABLED,
    RESISTANCE_BREAK_PLUS_ENABLED,
    RESISTANCE_BREAK_MINUS_ENABLED,
    RESISTANCE_BREAK_LOOKBACK,
    RESISTANCE_BREAK_MIN_TOUCHES,
    RESISTANCE_BREAK_PULLBACK_PCT,
    RESISTANCE_BREAK_PULLBACK_WINDOW,
    RESISTANCE_BREAK_EMA_PERIOD,
    RESISTANCE_BREAK_VOL_SPIKE_MIN,
    RESISTANCE_BREAK_COOLDOWN_HOURS,
    RESISTANCE_BREAK_CONF_BASE,
    RESISTANCE_BREAK_CONF_CAP,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'resistance_break_long'
SOURCE_LONG = 'resistance-break+'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[resistance-break] {msg}", flush=True)


def _get_1m_candles(token, limit=500):
    """Fetch 1m candles from DB. Returns list of dicts, oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

    if not rows:
        return []
    return [
        {'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]}
        for r in reversed(rows)
    ]


def _find_resistance(candles, lookback):
    """Find resistance level: max high in lookback period."""
    if len(candles) < lookback:
        return None, 0
    window = candles[-lookback:]
    resistance = max(c['high'] for c in window)
    return resistance, lookback


def _count_touches(candles, resistance, window=50):
    """Count how many times price touched resistance level."""
    if len(candles) < window:
        return 0
    recent = candles[-window:]
    touches = 0
    for c in recent:
        if abs(c['high'] - resistance) / resistance < 0.002:  # within 0.2%
            touches += 1
    return touches


def detect(token):
    """Detect resistance break LONG setup.

    Returns {direction, confidence, value, price, metadata} or None.
    """
    candles = _get_1m_candles(token, limit=500)
    if not candles or len(candles) < RESISTANCE_BREAK_LOOKBACK + 50:
        return None

    current = candles[-1]
    price = current['close']
    if price <= 0:
        return None

    # Find resistance level
    resistance, _ = _find_resistance(candles, RESISTANCE_BREAK_LOOKBACK)
    if resistance is None:
        return None

    # Must be breaking above resistance
    if price <= resistance:
        return None

    # Count touches at resistance (must be tested)
    touches = _count_touches(candles, resistance)
    if touches < RESISTANCE_BREAK_MIN_TOUCHES:
        return None

    # Wait for pullback: price must have dipped back toward resistance
    # Check last 30 bars for a low within pullback_pct of resistance
    pullback_found = False
    pullback_depth = 0
    if len(candles) > RESISTANCE_BREAK_PULLBACK_WINDOW:
        recent = candles[-RESISTANCE_BREAK_PULLBACK_WINDOW:]
        for c in recent:
            if c['low'] <= resistance * (1 + RESISTANCE_BREAK_PULLBACK_PCT):
                pullback_found = True
                # Depth = how far into the pullback zone price dipped (0-100%)
                pullback_zone = resistance * RESISTANCE_BREAK_PULLBACK_PCT
                if pullback_zone > 0:
                    depth = (pullback_zone - (c['low'] - resistance)) / pullback_zone * 100
                    pullback_depth = max(pullback_depth, max(0, depth))
                break

    if not pullback_found:
        return None

    # Trend alignment: price above SMA (labeled EMA for consistency with other signals)
    closes = [c['close'] for c in candles[-RESISTANCE_BREAK_EMA_PERIOD:]]
    if len(closes) < RESISTANCE_BREAK_EMA_PERIOD:
        return None
    sma = np.mean(closes)
    if price <= sma:
        return None

    # Volume confirmation
    volumes = [c['volume'] for c in candles[-20:]]
    vol_avg = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
    vol_spike = current['volume'] / vol_avg if vol_avg > 0 else 0
    if vol_spike < RESISTANCE_BREAK_VOL_SPIKE_MIN:
        return None

    # Compute confidence
    conf = RESISTANCE_BREAK_CONF_BASE

    # Touch bonus: more touches = stronger resistance = better breakout
    if touches >= 10:
        conf += 10
    elif touches >= 7:
        conf += 5

    # Pullback depth bonus: deeper pullback = stronger confirmation
    if pullback_depth > 0.5:
        conf += 5
    elif pullback_depth > 0.2:
        conf += 3

    # Volume bonus
    if vol_spike > 5.0:
        conf += 5
    elif vol_spike > 3.0:
        conf += 3

    # EMA distance bonus
    ema_dist = (price - sma) / sma * 100 if sma > 0 else 0
    if ema_dist > 1.0:
        conf += 3

    conf = min(conf, RESISTANCE_BREAK_CONF_CAP)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': touches,
        'price': price,
        'metadata': {
            'resistance': resistance,
            'touches': touches,
            'pullback_depth': pullback_depth,
            'vol_spike': vol_spike,
            'ema_dist': ema_dist,
        },
    }


def scan_signals():
    """Scan all tokens for resistance break LONG setups."""
    if not RESISTANCE_BREAK_ENABLED or not RESISTANCE_BREAK_PLUS_ENABLED:
        return 0

    added = 0

    # Get tokens with recent 1m data
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
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

    for token in tokens:
        if price_age_minutes(token) > 10:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(token, direction='LONG'):
            continue

        sig = detect(token)
        if not sig:
            continue

        # Layer 1 guards already checked above

        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=SIGNAL_TYPE_LONG,
            source=SOURCE_LONG,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=RESISTANCE_BREAK_COOLDOWN_HOURS)
            m = sig.get('metadata', {})
            _log(f"{token.upper()} LONG conf={sig['confidence']} "
                 f"R=${m.get('resistance', 0):.4f} touches={m.get('touches', 0)} "
                 f"pullback={m.get('pullback_depth', 0):.2f}% vol={m.get('vol_spike', 0):.1f}x")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Resistance Break Signal')
    parser.add_argument('--query', help='Query a specific token')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()

    if args.query:
        sig = detect(args.query)
        if sig:
            m = sig.get('metadata', {})
            print(f'{sig["direction"]} {args.query.upper()} conf={sig["confidence"]}')
            print(f'  resistance=${m.get("resistance", 0):.4f} touches={m.get("touches", 0)}')
            print(f'  pullback={m.get("pullback_depth", 0):.2f}% vol={m.get("vol_spike", 0):.1f}x')
        else:
            print(f'No signal for {args.query.upper()}')
    else:
        count = scan_signals()
        print(f'\n[resistance-break] Added {count} signals')
