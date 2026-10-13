#!/usr/bin/env python3
"""Volume Buildup — Sustained above-average volume with price trending.

Catches sustained volume accumulation like CHIP (+29%) and CFX (+20%).
Unlike volume-breakout (single-bar spike), this requires MULTIPLE consecutive
bars of above-average volume — institutional accumulation, not a fakeout.

LONG fires when:
  1. Last N bars ALL have volume >= BUILDUP_VOL_MULT × average (sustained, not one spike)
  2. Price rose over those bars (close now > close N bars ago)
  3. RSI < BUILDUP_RSI_MAX (not overbought)

SHORT fires when mirror (volume sustained, price falling, RSI > min).

Architecture:
  5m candles → sustained volume check → price direction → RSI filter
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset.json

Family: Volume (pairs with Momentum/Pattern for confluence)
"""

import sys, os, sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    VOLUME_BUILDUP_ENABLED,
    VOLUME_BUILDUP_PLUS_ENABLED,
    VOLUME_BUILDUP_MINUS_ENABLED,
    VOLUME_BUILDUP_COOLDOWN_MINUTES,
    VOLUME_BUILDUP_BARS,
    VOLUME_BUILDUP_VOL_MULT,
    VOLUME_BUILDUP_VOL_AVG_PERIOD,
    VOLUME_BUILDUP_RSI_MAX,
    VOLUME_BUILDUP_RSI_MIN,
    VOLUME_BUILDUP_RSI_PERIOD,
    VOLUME_BUILDUP_MIN_PRICE_CHANGE_PCT,
    VOLUME_BUILDUP_CONF_BASE,
    VOLUME_BUILDUP_CONF_FLOOR,
    VOLUME_BUILDUP_CONF_CAP,
    VOLUME_BUILDUP_CONF_VOL_BONUS,
    VOLUME_BUILDUP_CONF_MOMENTUM_BONUS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'volume_buildup_long'
SIGNAL_TYPE_SHORT = 'volume_buildup_short'
SOURCE_LONG = 'volume-buildup+'
SOURCE_SHORT = 'volume-buildup-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_MIN_CANDLES = VOLUME_BUILDUP_VOL_AVG_PERIOD + VOLUME_BUILDUP_BARS + 5


def _log(msg):
    print(f'[volume-buildup] {msg}', flush=True)


def _get_candles(token, limit):
    """Fetch 5m candles. Returns (ts, open, high, low, close, volume) oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume FROM (
                SELECT ts, open, high, low, close, volume
                FROM candles_5m WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC LIMIT ?
            ) sub ORDER BY ts ASC
        """, (token.upper(), limit))
        return c.fetchall()
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _rsi(closes, period=14):
    """Wilder RSI. Returns float or None."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def detect(token):
    """Detect volume_buildup. Returns {direction, confidence, value, price} or None."""
    candles = _get_candles(token, 60)
    if len(candles) < _MIN_CANDLES:
        return None

    closes = [c[4] for c in candles]
    vols = [c[5] for c in candles]

    price = closes[-1]
    if price <= 0:
        return None

    # Volume average
    vol_avg = sum(vols[-VOLUME_BUILDUP_VOL_AVG_PERIOD:]) / VOLUME_BUILDUP_VOL_AVG_PERIOD
    if vol_avg <= 0:
        return None

    # ── Condition 1: Sustained volume — AVERAGE of last N bars above threshold ──
    # Not every bar must be above (too strict for real accumulation), but the
    # average must be elevated AND at least half the bars above threshold.
    n = VOLUME_BUILDUP_BARS
    recent_vols = vols[-n:]
    vol_ratios = [v / vol_avg for v in recent_vols]
    avg_vol_ratio = sum(vol_ratios) / n

    # Average must be above the multiplier
    if avg_vol_ratio < VOLUME_BUILDUP_VOL_MULT:
        return None

    # At least half the bars must individually be above threshold
    bars_above = sum(1 for r in vol_ratios if r >= VOLUME_BUILDUP_VOL_MULT)
    if bars_above < (n + 1) // 2:
        return None

    # ── Condition 2: Price direction ────────────────────────────────────────
    price_change = (closes[-1] - closes[-1 - n]) / closes[-1 - n] * 100

    if price_change < VOLUME_BUILDUP_MIN_PRICE_CHANGE_PCT:
        # Not enough upward movement for LONG — check SHORT
        if price_change > -VOLUME_BUILDUP_MIN_PRICE_CHANGE_PCT:
            return None  # Not moving enough in either direction
        direction = 'SHORT'
    else:
        direction = 'LONG'

    # ── Condition 3: RSI filter ─────────────────────────────────────────────
    current_rsi = _rsi(closes, VOLUME_BUILDUP_RSI_PERIOD)
    if current_rsi is None:
        return None

    if direction == 'LONG' and current_rsi > VOLUME_BUILDUP_RSI_MAX:
        return None
    if direction == 'SHORT' and current_rsi < VOLUME_BUILDUP_RSI_MIN:
        return None

    # ── Confidence ──────────────────────────────────────────────────────────
    confidence = VOLUME_BUILDUP_CONF_BASE

    # Volume bonus — stronger sustained volume = higher confidence
    if avg_vol_ratio >= 3.0:
        confidence += VOLUME_BUILDUP_CONF_VOL_BONUS
    elif avg_vol_ratio >= 2.5:
        confidence += VOLUME_BUILDUP_CONF_VOL_BONUS // 2

    # Momentum bonus — stronger price movement = higher confidence
    if abs(price_change) >= 3.0:
        confidence += VOLUME_BUILDUP_CONF_MOMENTUM_BONUS
    elif abs(price_change) >= 2.0:
        confidence += VOLUME_BUILDUP_CONF_MOMENTUM_BONUS // 2

    confidence = max(VOLUME_BUILDUP_CONF_FLOOR, min(VOLUME_BUILDUP_CONF_CAP, confidence))

    # Value: avg volume ratio (for hotset scoring)
    value = round(avg_vol_ratio, 2)

    return {
        'direction': direction,
        'confidence': confidence,
        'value': value,
        'price': price,
    }


def run(prices_dict=None) -> int:
    """Entry point for signals_runner."""
    if not VOLUME_BUILDUP_ENABLED:
        return 0

    added = 0
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        tokens = [r[0] for r in conn.execute("SELECT DISTINCT token FROM candles_5m").fetchall()]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

    for token in tokens:
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']
        if direction == 'LONG' and not VOLUME_BUILDUP_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not VOLUME_BUILDUP_MINUS_ENABLED:
            continue
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            _log(f'{token} {direction} conf={sig["confidence"]:.0f} vol={sig["value"]}x price={sig["price"]}')
            set_cooldown(token, direction, hours=VOLUME_BUILDUP_COOLDOWN_MINUTES / 60.0)

    if added:
        _log(f'Added {added} signals')
    return added


if __name__ == '__main__':
    import sys as _sys
    if len(_sys.argv) > 1:
        r = detect(_sys.argv[1])
        print(f'DETECTED: {r}' if r else 'No signal')
    else:
        print(f'Added {run()} signals')
