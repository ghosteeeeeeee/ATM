#!/usr/bin/env python3
"""doji_bottom.py — Detect doji exhaustion at bottoms (enter LONG).

Pattern: Strong decline → Doji (indecision) → Reversal likely.
Doji = body < 15% of range (near open ≈ close).

Entry signal (doji-bottom-long): Enter LONG on expected bounce.

Classification: Mean-reversion (buying extremes). ALLOWED in CHOP.
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    DOJI_TOP_ENABLED, DOJI_TOP_PLUS_ENABLED,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'doji_bottom_long'
SOURCE_LONG      = 'doji-bottom-long'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _get_candles(token, table, limit):
    """DB fetch for OHLCV. Returns oldest-first list of dicts."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT open, high, low, close, volume FROM {table}
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


def _calc_rsi(closes, period=14):
    """RSI with Wilder smoothing."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    if len(gains) < period:
        return None
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100
    return 100 - (100 / (1 + ag / al))


def _is_doji(candle, body_max_pct):
    """Check if a candle is a doji (body < body_max_pct% of range)."""
    h, l, o, c = candle['high'], candle['low'], candle['open'], candle['close']
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    body_pct = (body / rng) * 100
    return body_pct < body_max_pct


def _detect_long(token):
    """Detect doji exhaustion at bottom of decline.

    Returns {direction, confidence, value, price} or None.
    Emits LONG signal (system enters LONG on expected bounce).
    """
    from hermes_constants import (
        DOJI_BODY_MAX_PCT, DOJI_DECLINE_MIN_PCT,
        DOJI_VOLUME_DRY_RATIO, DOJI_RSI_OVERSOLD,
        DOJI_LOOKBACK, DOJI_CONF_BASE, DOJI_CONF_CAP,
    )

    candles = _get_candles(token, 'candles_5m', 50)
    if len(candles) < 20:
        return None

    closes = [c['close'] for c in candles]
    volumes = [c['volume'] for c in candles]
    price = closes[-1]

    # 1. Must be a doji on the latest candle
    latest = candles[-1]
    if not _is_doji(latest, DOJI_BODY_MAX_PCT):
        return None

    # 2. Prior decline: price fell > DOJI_DECLINE_MIN_PCT in last LOOKBACK candles
    lookback = min(DOJI_LOOKBACK, len(closes) - 1)
    if lookback < 3:
        return None
    decline_start = closes[-lookback - 1]
    if decline_start <= 0:
        return None
    decline_pct = (decline_start - closes[-1]) / decline_start * 100
    if decline_pct < DOJI_DECLINE_MIN_PCT:
        return None

    # 3. Volume drying up (sellers exhausted): current vol < DOJI_VOLUME_DRY_RATIO × avg
    if len(volumes) < 20:
        return None
    avg_vol = sum(volumes[-20:]) / 20
    if avg_vol <= 0:
        return None
    vol_ratio = volumes[-1] / avg_vol
    if vol_ratio > DOJI_VOLUME_DRY_RATIO:
        return None

    # 4. RSI oversold
    rsi = _calc_rsi(closes)
    if rsi is None or rsi > DOJI_RSI_OVERSOLD:
        return None

    # Confidence
    conf = DOJI_CONF_BASE
    # Bonus for extreme RSI
    if rsi < 25:
        conf += 5
    # Bonus for very low volume (sellers truly exhausted)
    if vol_ratio < 0.3:
        conf += 5
    conf = min(conf, DOJI_CONF_CAP)

    # Value = decline size for TP calculation
    value = decline_pct

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': value,
        'price': price,
        'decline_pct': decline_pct,
        'vol_ratio': vol_ratio,
        'rsi': rsi,
        'body_pct': (abs(latest['close'] - latest['open']) / (latest['high'] - latest['low'])) * 100 if latest['high'] != latest['low'] else 0,
    }


def scan_signals() -> int:
    """Scan all tokens for doji exhaustion-at-bottom setups."""
    from signal_schema import get_all_latest_prices

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue

        if price_age_minutes(token) > 10:
            continue

        sig = _detect_long(token)
        if not sig:
            continue

        # Kill-switch: master + direction
        if not DOJI_TOP_ENABLED:
            continue
        if not DOJI_TOP_PLUS_ENABLED:
            continue

        # Blacklists
        if token.upper() in LONG_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction='LONG'):
            continue

        # Emit LONG signal
        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=SIGNAL_TYPE_LONG,
            source=SOURCE_LONG,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=None,
        )
        if sid:
            added += 1
            from hermes_constants import DOJI_COOLDOWN_HOURS
            set_cooldown(token, direction='LONG', hours=DOJI_COOLDOWN_HOURS)
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    n = run()
    print(f"doji_bottom: {n} signals emitted")
