#!/usr/bin/env python3
"""
open_skies — LONG-only signal for coins with open skies (no resistance).

Thesis: Coins that have broken through all resistance with strong upward
momentum and no ceiling in sight. The structural R:R is excellent because
there's nothing stopping price from running.

Pattern:
  1. Price above SMA20 and SMA50 (uptrend confirmed)
  2. Zero resistance levels in S/R map (open skies)
  3. Multiple support levels below (safety net)
  4. Positive 20-bar return (momentum has legs)
  5. Volume spike (real buying, not noise)
  6. Higher highs forming (structurally bullish)

Data: candles_5m from candles.db, S/R from risk_reward_engine
"""

import sys
import os
import time
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    OPEN_SKIES_ENABLED,
    OPEN_SKIES_PLUS_ENABLED,
    OPEN_SKIES_MINUS_ENABLED,
    OPEN_SKIES_SMA_FAST,
    OPEN_SKIES_SMA_SLOW,
    OPEN_SKIES_MAX_RSI,
    OPEN_SKIES_MIN_RETURN_20,
    OPEN_SKIES_VOL_SPIKE_RATIO,
    OPEN_SKIES_MIN_SUPPORT_LEVELS,
    OPEN_SKIES_MAX_RESISTANCE,
    OPEN_SKIES_HH_MIN,
    OPEN_SKIES_HH_WINDOW,
    OPEN_SKIES_COOLDOWN_HOURS,
    OPEN_SKIES_CONF_BASE,
    OPEN_SKIES_CONF_CAP,
    OPEN_SKIES_VOL_SPIKE_STRONG,
    OPEN_SKIES_VOL_SPIKE_MODERATE,
    OPEN_SKIES_BONUS_STRONG,
    OPEN_SKIES_BONUS_MODERATE,
    OPEN_SKIES_RET_STRONG,
    OPEN_SKIES_RET_MODERATE,
    OPEN_SKIES_SUPPORT_STRONG,
    OPEN_SKIES_SUPPORT_MODERATE,
    OPEN_SKIES_SMA50_STRONG,
    OPEN_SKIES_SMA50_MODERATE,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'open_skies_long'
SOURCE_LONG = 'open-skies+'


def _log(msg):
    print(f"[open-skies] {msg}", flush=True)


def _get_candles(token, table='candles_5m', limit=100):
    """Fetch candles from DB. Returns list of (ts, open, high, low, close, volume) oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume
            FROM {table}
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
    return list(reversed(rows))


def _compute_sma(closes, period):
    """Simple Moving Average. Returns SMA value or None."""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _count_higher_highs(highs, window=10):
    """Count higher highs in last N bars. Each bar's high must exceed previous."""
    if len(highs) < window:
        return 0
    recent = highs[-window:]
    count = 0
    for i in range(1, len(recent)):
        if recent[i] > recent[i - 1]:
            count += 1
    return count


def _compute_rsi(closes, period=14):
    """Compute RSI. Returns float or None."""
    if len(closes) < period + 1:
        return None
    import numpy as np
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _get_volume_ratio(candles, window=5):
    """Compare recent volume to prior volume. Returns ratio or None."""
    if len(candles) < window * 2 + 1:
        return None

    # Extract volumes
    volumes = []
    for c in candles:
        if isinstance(c, (list, tuple)):
            volumes.append(c[5] if len(c) > 5 else 0)
        elif isinstance(c, dict):
            volumes.append(c.get('volume', 0))
        else:
            volumes.append(0)

    recent_avg = sum(volumes[-window:]) / window
    prior_avg = sum(volumes[-(window * 2):-window]) / window

    if prior_avg <= 0:
        return None
    return recent_avg / prior_avg


def _get_sr_map(token, price):
    """Get S/R map from risk_reward_engine. Returns list of levels."""
    try:
        from risk_reward_engine import build_sr_map
        return build_sr_map(token, price)
    except Exception:
        return []


def detect(token):
    """Detect open-skies LONG setup.

    Returns {direction, confidence, value, price} or None.
    """
    # Get candles
    candles = _get_candles(token, 'candles_5m', 100)
    if not candles or len(candles) < 60:
        return None

    # Current price
    price = candles[-1][4]
    if price <= 0:
        return None

    # Close prices and high prices
    closes = [c[4] for c in candles]
    highs = [c[2] for c in candles]

    # ── Dead token filter: 20-bar range must be > 1% ──
    if len(closes) >= 20:
        high_20 = max(closes[-20:])
        low_20 = min(closes[-20:])
        range_20 = (high_20 - low_20) / low_20 * 100 if low_20 > 0 else 0
        if range_20 < 1.0:
            return None  # dead token, no real market

    # ── Condition 1 & 2: Price above SMA20 and SMA50 ──
    sma_fast = _compute_sma(closes, OPEN_SKIES_SMA_FAST)
    sma_slow = _compute_sma(closes, OPEN_SKIES_SMA_SLOW)

    if sma_fast is None or sma_slow is None:
        return None

    if price <= sma_fast or price <= sma_slow:
        return None  # not in uptrend

    # ── RSI guard: don't enter overbought ──
    rsi = _compute_rsi(closes)
    if rsi is not None and rsi > OPEN_SKIES_MAX_RSI:
        return None  # overbought — chasing

    # ── Condition 3: No resistance levels (open skies) ──
    sr_map = _get_sr_map(token, price)
    resistance_levels = [l for l in sr_map if l.get('type') == 'resistance']

    if len(resistance_levels) > OPEN_SKIES_MAX_RESISTANCE:
        return None  # has resistance — not open skies

    # ── Condition 4: Support levels below (safety net) ──
    support_levels = [l for l in sr_map if l.get('type') == 'support']

    if len(support_levels) < OPEN_SKIES_MIN_SUPPORT_LEVELS:
        return None  # no floor — too risky

    # ── Condition 5: Positive 20-bar return ──
    if len(closes) >= 20:
        if closes[-20] <= 0:
            return None  # degenerate data
        ret_20 = (closes[-1] - closes[-20]) / closes[-20] * 100
    else:
        return None

    if ret_20 < OPEN_SKIES_MIN_RETURN_20:
        return None  # no momentum

    # ── Condition 6: Volume spike (must have volume data) ──
    vol_ratio = _get_volume_ratio(candles)
    if vol_ratio is None:
        return None  # no volume data — can't confirm breakout
    if vol_ratio < OPEN_SKIES_VOL_SPIKE_RATIO:
        return None  # no volume confirmation

    # ── Condition 7: Higher highs (using actual highs, not closes) ──
    hh_count = _count_higher_highs(highs, OPEN_SKIES_HH_WINDOW)
    if hh_count < OPEN_SKIES_HH_MIN:
        return None  # not structurally bullish

    # ── All conditions met — compute confidence ──
    conf = OPEN_SKIES_CONF_BASE

    # Bonus: volume spike magnitude
    if vol_ratio and vol_ratio > OPEN_SKIES_VOL_SPIKE_STRONG:
        conf += OPEN_SKIES_BONUS_STRONG
    elif vol_ratio and vol_ratio > OPEN_SKIES_VOL_SPIKE_MODERATE:
        conf += OPEN_SKIES_BONUS_MODERATE

    # Bonus: strong momentum (>3% in 20 bars)
    if ret_20 > OPEN_SKIES_RET_STRONG:
        conf += OPEN_SKIES_BONUS_STRONG
    elif ret_20 > OPEN_SKIES_RET_MODERATE:
        conf += OPEN_SKIES_BONUS_MODERATE

    # Bonus: many support levels (strong floor)
    if len(support_levels) >= OPEN_SKIES_SUPPORT_STRONG:
        conf += OPEN_SKIES_BONUS_MODERATE
    elif len(support_levels) >= OPEN_SKIES_SUPPORT_MODERATE:
        conf += 2

    # Bonus: price well above SMA50 (strong trend)
    sma50_dist = (price - sma_slow) / sma_slow * 100
    if sma50_dist > OPEN_SKIES_SMA50_STRONG:
        conf += OPEN_SKIES_BONUS_MODERATE
    elif sma50_dist > OPEN_SKIES_SMA50_MODERATE:
        conf += 2

    conf = min(conf, OPEN_SKIES_CONF_CAP)

    notes = (
        f"Open skies: {len(resistance_levels)} resistance, {len(support_levels)} support, "
        f"ret_20={ret_20:.1f}%, vol_ratio={vol_ratio:.1f}x, hh={hh_count}, "
        f"SMA20=${sma_fast:.4f}, SMA50=${sma_slow:.4f}"
    ) if vol_ratio is not None else (
        f"Open skies: {len(resistance_levels)} resistance, {len(support_levels)} support, "
        f"ret_20={ret_20:.1f}%, vol_ratio=N/A, hh={hh_count}, "
        f"SMA20=${sma_fast:.4f}, SMA50=${sma_slow:.4f}"
    )

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': ret_20,
        'price': price,
        'z_score': None,
        'notes': notes,
    }


def scan_signals():
    """Scan all tokens for open-skies LONG setups."""
    if not OPEN_SKIES_ENABLED or not OPEN_SKIES_PLUS_ENABLED:
        return 0

    added = 0

    # Get tokens with recent candle data
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token FROM candles_5m
            WHERE ts > strftime('%s', 'now') - 3600
        """)
        tokens = [r[0] for r in cur.fetchall()]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

    for token in tokens:
        # Guards
        if price_age_minutes(token) > 10:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(token, direction='LONG'):
            continue

        sig = detect(token)
        if not sig:
            continue

        # Layer 1: kill-switch (already checked above)
        # Layer 1: blacklists (already checked above)

        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=SIGNAL_TYPE_LONG,
            source=SOURCE_LONG,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=OPEN_SKIES_COOLDOWN_HOURS)
            _log(f"{token.upper()} LONG conf={sig['confidence']} {sig['notes']}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Open Skies Signal')
    parser.add_argument('--query', help='Query a specific token')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()

    if args.query:
        sig = detect(args.query)
        if sig:
            print(f'{sig["direction"]} {args.query.upper()} conf={sig["confidence"]}')
            print(f'  {sig["notes"]}')
        else:
            print(f'No signal for {args.query.upper()}')
    else:
        count = scan_signals()
        print(f'\n[open-skies] Added {count} signals')
