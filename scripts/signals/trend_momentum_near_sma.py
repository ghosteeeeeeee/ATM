#!/usr/bin/env python3
"""
trend_momentum_near_sma — Buy in uptrend with momentum near SMA.

Thesis: Price in uptrend (close > SMA20) with positive momentum
        and near SMA (not extended) historically produces 47.8% WR
        with +$9.66/14d.

Entry:  close > SMA20 + 5-period momentum > 0.5% + within 0.5% of SMA
Exit:   Trail 0.8%, stop -1.2%

Data:   candles_1h from candles.db
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA
from hermes_constants import (
    TREND_MOMENTUM_NEAR_SMA_ENABLED,
    TREND_MOMENTUM_NEAR_SMA_PLUS_ENABLED,
    TREND_MOMENTUM_NEAR_SMA_MOMENTUM_THRESHOLD,
    TREND_MOMENTUM_NEAR_SMA_DIST_SMA_MAX,
    TREND_MOMENTUM_NEAR_SMA_SMA_PERIOD,
    TREND_MOMENTUM_NEAR_SMA_MOMENTUM_PERIOD,
    TREND_MOMENTUM_NEAR_SMA_CONF_BASE,
    TREND_MOMENTUM_NEAR_SMA_CONF_STRONG_MOM,
    TREND_MOMENTUM_NEAR_SMA_CONF_CLOSE_SMA,
    TREND_MOMENTUM_NEAR_SMA_CONF_CAP,
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
    """Check if token meets trend_momentum_near_sma entry conditions."""
    conn = None
    try:
        conn = sqlite3.connect(_get_db(), timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), TREND_MOMENTUM_NEAR_SMA_SMA_PERIOD + TREND_MOMENTUM_NEAR_SMA_MOMENTUM_PERIOD))
        rows = cur.fetchall()
        if len(rows) < TREND_MOMENTUM_NEAR_SMA_SMA_PERIOD:
            return None
        closes = [r[0] for r in reversed(rows)]
    except Exception:
        return None
    finally:
        if conn:
            conn.close()

    close = closes[-1]
    if close <= 0:
        return None

    # SMA
    sma = sum(closes[-TREND_MOMENTUM_NEAR_SMA_SMA_PERIOD:]) / TREND_MOMENTUM_NEAR_SMA_SMA_PERIOD

    # Momentum
    mom_period = TREND_MOMENTUM_NEAR_SMA_MOMENTUM_PERIOD
    if closes[-mom_period - 1] <= 0:
        return None
    momentum = (closes[-1] - closes[-mom_period - 1]) / closes[-mom_period - 1]

    # Distance from SMA
    dist_sma = abs(close - sma) / sma

    # Entry conditions
    if close <= sma:
        return None  # not uptrend
    if momentum <= TREND_MOMENTUM_NEAR_SMA_MOMENTUM_THRESHOLD:
        return None  # no momentum
    if dist_sma >= TREND_MOMENTUM_NEAR_SMA_DIST_SMA_MAX:
        return None  # too far from SMA

    # Confidence
    conf = TREND_MOMENTUM_NEAR_SMA_CONF_BASE
    if momentum > 0.01:
        conf += TREND_MOMENTUM_NEAR_SMA_CONF_STRONG_MOM
    if dist_sma < 0.002:
        conf += TREND_MOMENTUM_NEAR_SMA_CONF_CLOSE_SMA
    conf = min(conf, TREND_MOMENTUM_NEAR_SMA_CONF_CAP)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': momentum,
        'price': close,
        'z_score': None,
    }


def scan_signals():
    """Scan all tokens and add signals via add_signal()."""
    if not TREND_MOMENTUM_NEAR_SMA_ENABLED:
        return 0
    if not TREND_MOMENTUM_NEAR_SMA_PLUS_ENABLED:
        return 0

    added = 0
    conn = None
    try:
        conn = sqlite3.connect(_get_db(), timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token FROM candles_1h
            WHERE ts > strftime('%s', 'now') - 86400
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
            signal_type='trend_momentum_near_sma',
            source='trend_momentum_near_sma+',
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1h',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(tok, direction='LONG', hours=3)

    return added


def run():
    return scan_signals()


if __name__ == '__main__':
    added = run()
    print(f'Added {added} signals')
