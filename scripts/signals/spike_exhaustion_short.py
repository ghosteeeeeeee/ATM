#!/usr/bin/env python3
"""
spike_exhaustion_short — SHORT after violent spike exhausts.

Thesis: After a huge spike (>2.5%), price stalls and reverses.
        The spike was algo-driven, not organic. Fade the exhaustion.

Pattern:
  1. Spike: >2.5% in <5 candles
  2. Stall: no new high for 3+ candles
  3. Weakening: red candle below spike high
  4. Enter SHORT

Entry:  Spike detected (>2.5%)
        + Stall (no new high for 3 candles)
        + Red candle below spike high
Exit:   Trail 0.5% from trough, stop +1% from entry

Data:   candles_1m from candles.db
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA
from hermes_constants import (
    SPIKE_EXHAUSTION_SHORT_ENABLED,
    SPIKE_EXHAUSTION_SHORT_MINUS_ENABLED,
    SPIKE_EXHAUSTION_SHORT_SPIKE_THRESHOLD,
    SPIKE_EXHAUSTION_SHORT_SPIKE_WINDOW,
    SPIKE_EXHAUSTION_SHORT_STALL_CANDLES,
    SPIKE_EXHAUSTION_SHORT_CONF_BASE,
    SPIKE_EXHAUSTION_SHORT_CONF_CAP,
    SHORT_BLACKLIST,
)
import sqlite3

_CANDLES_DB = None

def _get_db():
    global _CANDLES_DB
    if _CANDLES_DB is None:
        _CANDLES_DB = f'{HERMES_DATA}/candles.db'
    return _CANDLES_DB


def detect(token):
    """Check if token has a spike exhaustion pattern for SHORT."""
    conn = None
    try:
        conn = sqlite3.connect(_get_db(), timeout=10)
        cur = conn.cursor()
        window = SPIKE_EXHAUSTION_SHORT_SPIKE_WINDOW + SPIKE_EXHAUSTION_SHORT_STALL_CANDLES + 10
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

    candles = list(reversed(rows))
    closes = [c[4] for c in candles]
    opens = [c[1] for c in candles]
    highs = [c[2] for c in candles]

    # Find spike in recent past (not the very latest)
    search_end = len(candles) - SPIKE_EXHAUSTION_SHORT_STALL_CANDLES
    search_start = max(0, search_end - SPIKE_EXHAUSTION_SHORT_SPIKE_WINDOW)

    best_spike = 0
    best_spike_high = 0

    for lookback in range(3, SPIKE_EXHAUSTION_SHORT_SPIKE_WINDOW + 1):
        start_idx = search_end - lookback
        if start_idx < 0:
            continue
        start_price = closes[start_idx]
        if start_price <= 0:
            continue
        spike_high = max(highs[start_idx:search_end + 1])
        spike_pct = (spike_high - start_price) / start_price
        if spike_pct > best_spike:
            best_spike = spike_pct
            best_spike_high = spike_high

    if best_spike < SPIKE_EXHAUSTION_SHORT_SPIKE_THRESHOLD:
        return None

    # Check stall: no new high in last N candles
    stall_high = max(highs[search_end:]) if highs[search_end:] else 0
    if stall_high > best_spike_high:
        return None  # still making highs

    # Check weakening: current price below spike high, red candle
    current_price = closes[-1]
    if current_price >= best_spike_high:
        return None
    if closes[-1] >= opens[-1]:
        return None  # not red

    conf = SPIKE_EXHAUSTION_SHORT_CONF_BASE
    if best_spike > 0.03:
        conf += 10
    conf = min(conf, SPIKE_EXHAUSTION_SHORT_CONF_CAP)

    return {
        'direction': 'SHORT',
        'confidence': conf,
        'value': best_spike,
        'price': current_price,
        'z_score': None,
    }


def scan_signals():
    if not SPIKE_EXHAUSTION_SHORT_ENABLED:
        return 0
    if not SPIKE_EXHAUSTION_SHORT_MINUS_ENABLED:
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
        if tok.upper() in SHORT_BLACKLIST:
            continue
        if get_cooldown(tok, direction='SHORT'):
            continue

        sig = detect(tok)
        if not sig:
            continue

        sid = add_signal(
            token=tok.upper(),
            direction='SHORT',
            signal_type='spike_exhaustion_short',
            source='spike_exhaustion_short-',
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(tok, direction='SHORT', hours=2)

    return added


def run():
    return scan_signals()


if __name__ == '__main__':
    added = run()
    print(f'Added {added} signals')
