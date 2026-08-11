#!/usr/bin/env python3
"""
spike_exhaustion_short — SHORT after vertical spike shows exhaustion.

Thesis: After a sharp spike (>1.5% in <5 min), price often reverses once
        momentum stalls. The spike is usually a stop hunt or algo-driven,
        not organic buying. Enter SHORT after exhaustion confirms.

Entry:  Spike detected (>1.5% in 5 candles on 1m)
        + Price stalls (3+ candles without new high)
        + Momentum weakening (close < previous close for 2+ of last 3)

Exit:   Stop above spike high
        Trail at 0.5% from peak

Data:   candles_1m from candles.db
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA
from hermes_constants import (
    SPIKE_EXHAUSTION_SHORT_ENABLED,
    SPIKE_EXHAUSTION_SHORT_PLUS_ENABLED,
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
        # Need enough candles: spike window + stall window + buffer
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

    # rows are newest-first, reverse for chronological
    candles = list(reversed(rows))
    closes = [c[4] for c in candles]
    highs = [c[2] for c in candles]

    # Step 1: Detect spike in the recent past (not the very latest)
    spike_end = len(candles) - SPIKE_EXHAUSTION_SHORT_STALL_CANDLES
    spike_start = spike_end - SPIKE_EXHAUSTION_SHORT_SPIKE_WINDOW

    if spike_start < 0 or spike_end >= len(candles):
        return None

    # Find the spike: look back SPIKE_WINDOW candles for a big move
    best_spike = 0
    best_spike_high = 0
    best_spike_start_price = 0

    for lookback in range(5, SPIKE_EXHAUSTION_SHORT_SPIKE_WINDOW + 1):
        start_idx = spike_end - lookback
        if start_idx < 0:
            continue
        start_price = closes[start_idx]
        end_price = closes[spike_end]
        if start_price <= 0:
            continue
        move_pct = (end_price - start_price) / start_price
        if move_pct > best_spike:
            best_spike = move_pct
            best_spike_high = max(highs[start_idx:spike_end + 1])
            best_spike_start_price = start_price

    if best_spike < SPIKE_EXHAUSTION_SHORT_SPIKE_THRESHOLD:
        return None  # no significant spike

    # Step 2: Check for exhaustion (stall after spike)
    stall_candles = candles[spike_end:]
    if len(stall_candles) < SPIKE_EXHAUSTION_SHORT_STALL_CANDLES:
        return None

    stall_closes = [c[4] for c in stall_candles]

    # Stall: no new high in last N candles
    stall_high = max(closes[spike_end:]) if closes[spike_end:] else 0
    spike_high_val = max(closes[spike_start:spike_end + 1]) if closes[spike_start:spike_end + 1] else 0
    if stall_high > spike_high_val:
        return None  # still making highs, not exhausted

    # Weakening: majority of last 3 candles are down
    last_3 = stall_closes[-3:] if len(stall_closes) >= 3 else stall_closes
    down_count = sum(1 for i in range(1, len(last_3)) if last_3[i] < last_3[i-1])
    if down_count < 2:
        return None  # not weakening enough

    # Current price should be below spike high
    current_price = closes[-1]
    if current_price >= spike_high_val:
        return None  # still at spike high, not reversing

    # Confidence based on spike magnitude and stall strength
    conf = SPIKE_EXHAUSTION_SHORT_CONF_BASE
    if best_spike > 0.02:
        conf += 10  # large spike = more likely to reverse
    if down_count == 3:
        conf += 5  # all 3 candles down = strong exhaustion
    conf = min(conf, SPIKE_EXHAUSTION_SHORT_CONF_CAP)

    return {
        'direction': 'SHORT',
        'confidence': conf,
        'value': best_spike,
        'price': current_price,
        'z_score': None,
    }


def scan_signals():
    """Scan all tokens and add signals via add_signal()."""
    if not SPIKE_EXHAUSTION_SHORT_ENABLED:
        return 0
    if not SPIKE_EXHAUSTION_SHORT_PLUS_ENABLED:
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
