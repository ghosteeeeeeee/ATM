#!/usr/bin/env python3
"""
wave_catcher — Catch violent spikes in both directions.

Thesis: Price spikes (rapid velocity) are followed by continuation.
        Enter in the direction of the spike, ride the wave.

Pattern:
  1. Velocity: >0.3% per bar (3-bar momentum)
  2. Direction: LONG if rising, SHORT if falling
  3. Confirmation: Price above/below EMA60
  4. Entry: Ride the spike

Exit:   Trail 0.3% from entry, profit target 0.5-1.0%

Data:   candles_1m from candles.db
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA
from hermes_constants import (
    WAVE_CATCHER_ENABLED,
    WAVE_CATCHER_PLUS_ENABLED,
    WAVE_CATCHER_MINUS_ENABLED,
    WAVE_CATCHER_VELOCITY_THRESHOLD,
    WAVE_CATCHER_VELOCITY_WINDOW,
    WAVE_CATCHER_EMA_PERIOD,
    WAVE_CATCHER_MIN_ATR,
    WAVE_CATCHER_ZSCORE_MAX,
    WAVE_CATCHER_CONF_BASE,
    WAVE_CATCHER_CONF_CAP,
    WAVE_CATCHER_COOLDOWN_HOURS,
    SHORT_BLACKLIST,
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
    """Check if token has a velocity spike for wave catching."""
    conn = None
    try:
        conn = sqlite3.connect(_get_db(), timeout=10)
        cur = conn.cursor()
        window = WAVE_CATCHER_VELOCITY_WINDOW + WAVE_CATCHER_EMA_PERIOD + 20
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

    # ── Compute EMA60 for trend confirmation ──────────────────────────────
    ema_period = WAVE_CATCHER_EMA_PERIOD
    if len(closes) < ema_period:
        return None

    k = 2.0 / (ema_period + 1)
    ema_val = closes[0]
    for p in closes[1:]:
        ema_val = p * k + ema_val * (1 - k)
    ema60 = ema_val

    # ── Compute velocity (3-bar momentum) ─────────────────────────────────
    vel_window = WAVE_CATCHER_VELOCITY_WINDOW
    if len(closes) < vel_window + 1:
        return None

    velocity = (closes[-1] - closes[-vel_window - 1]) / closes[-vel_window - 1] * 100

    # ── Check velocity threshold ──────────────────────────────────────────
    if abs(velocity) < WAVE_CATCHER_VELOCITY_THRESHOLD:
        return None

    # ── Determine direction ───────────────────────────────────────────────
    direction = 'LONG' if velocity > 0 else 'SHORT'

    # ── Check EMA60 confirmation ──────────────────────────────────────────
    if direction == 'LONG' and closes[-1] < ema60:
        return None  # price below EMA60 — not confirmed
    if direction == 'SHORT' and closes[-1] > ema60:
        return None  # price above EMA60 — not confirmed

    # ── Check Z-score (not overextended) ──────────────────────────────────
    if len(closes) >= 20:
        mean = sum(closes[-20:]) / 20
        std = (sum((c - mean) ** 2 for c in closes[-20:]) / 20) ** 0.5
        zscore = (closes[-1] - mean) / std if std > 0 else 0
        if abs(zscore) > WAVE_CATCHER_ZSCORE_MAX:
            return None  # overextended — don't chase
    else:
        zscore = 0.0

    # ── Check ATR (need volatility) ───────────────────────────────────────
    if len(closes) >= 15:
        changes = [abs(closes[i] - closes[i-1]) for i in range(len(closes)-14, len(closes))]
        atr = sum(changes) / 14
        atr_pct = atr / closes[-1] * 100 if closes[-1] > 0 else 0
        if atr_pct < WAVE_CATCHER_MIN_ATR:
            return None  # too quiet — no wave to catch
    else:
        atr_pct = 0.0

    # ── Confidence scoring ────────────────────────────────────────────────
    conf = WAVE_CATCHER_CONF_BASE

    # Bonus: strong velocity
    if abs(velocity) > 0.5:
        conf += 5
    if abs(velocity) > 1.0:
        conf += 5

    # Bonus: good EMA separation
    ema_sep = abs(closes[-1] - ema60) / ema60 * 100
    if ema_sep > 0.3:
        conf += 3

    conf = min(conf, WAVE_CATCHER_CONF_CAP)

    return {
        'direction': direction,
        'confidence': conf,
        'value': velocity,
        'price': closes[-1],
        'z_score': zscore,
        'source': f'wave_catcher',
    }


def scan_signals():
    """Scan all tokens for wave_catcher signals."""
    if not WAVE_CATCHER_ENABLED:
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
        if tok.startswith('@'):
            continue
        if price_age_minutes(tok) > 10:
            continue

        sig = detect(tok)
        if sig is None:
            continue

        direction = sig['direction']

        # Check kill switches
        if direction == 'LONG' and not WAVE_CATCHER_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not WAVE_CATCHER_MINUS_ENABLED:
            continue

        # Check cooldown
        if get_cooldown(tok, direction=direction):
            continue

        # Check blacklists
        if direction == 'LONG' and tok.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and tok.upper() in SHORT_BLACKLIST:
            continue

        # Add signal
        sig_type = 'wave_catcher_long' if direction == 'LONG' else 'wave_catcher_short'
        source = 'wave_catcher+'
        conf = sig['confidence']

        sid = add_signal(
            token=tok.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=conf,
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=sig.get('z_score'),
            z_score_tier=None,
        )
        if sid:
            added += 1
            set_cooldown(tok, direction, hours=WAVE_CATCHER_COOLDOWN_HOURS)

    return added


# Entry point for signals_runner
def run(prices_dict=None):
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_signals()
