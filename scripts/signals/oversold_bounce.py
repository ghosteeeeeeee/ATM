#!/usr/bin/env python3
"""oversold_bounce.py — Mean reversion LONG at extreme oversold conditions.

Thesis: When RSI < 25 and z-score < -1, price is oversold due to algo cascades
or panic selling. These are overreactions that revert to mean. The same setup
that pullback_entry fires SHORT on (downward impulse + bounce) should fire LONG
when conditions are this extreme.

Entry: RSI(14) < 25 + z-score < -1 + BB position < 0.3 + momentum flat/falling
Exit: 1% TP, 1.5% SL, trailing at 0.5%
"""
import sys, os, sqlite3, time, statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    OVERSOLD_BOUNCE_ENABLED,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'oversold_bounce_long'
SOURCE_LONG      = 'oversold-bounce+'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _get_closes(token, table, limit):
    """DB fetch with proper connection cleanup. Returns oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT close FROM {table}
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


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
    """Calculate RSI."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    ag = sum(gains) / period
    al = sum(losses) / period
    if al == 0:
        return 100
    return 100 - (100 / (1 + ag / al))


def _calc_bb_position(closes, period=20):
    """Calculate BB position: -1 to 1 where 0 = middle, < 0 = below middle."""
    if len(closes) < period:
        return None
    sma = statistics.mean(closes[-period:])
    std = statistics.stdev(closes[-period:])
    if std == 0:
        return 0
    upper = sma + 2 * std
    lower = sma - 2 * std
    price = closes[-1]
    if upper == lower:
        return 0
    return (price - lower) / (upper - lower) * 2 - 1  # normalize to -1..1


def detect(token):
    """Detect oversold bounce setup. Returns {direction, confidence, value, price} or None."""
    from hermes_constants import (
        OVERSOLD_BOUNCE_RSI_MIN,
        OVERSOLD_BOUNCE_RSI_MAX,
        OVERSOLD_BOUNCE_Z_MAX,
        OVERSOLD_BOUNCE_BB_MAX,
        OVERSOLD_BOUNCE_VOL_RATIO_MAX,
        OVERSOLD_BOUNCE_MIN_CANDLES,
        OVERSOLD_BOUNCE_CANDLE_FETCH,
        OVERSOLD_BOUNCE_STALENESS_MIN,
        OVERSOLD_BOUNCE_CONF_BASE,
        OVERSOLD_BOUNCE_CONF_CAP,
        OVERSOLD_BOUNCE_RSI_PERIOD,
        OVERSOLD_BOUNCE_BB_PERIOD,
        OVERSOLD_BOUNCE_Z_LOOKBACK,
        OVERSOLD_BOUNCE_MOM_LOOKBACK,
        OVERSOLD_BOUNCE_MOM_THRESHOLD,
        OVERSOLD_BOUNCE_CONF_RSI_DEEP,
        OVERSOLD_BOUNCE_CONF_Z_DEEP,
        OVERSOLD_BOUNCE_CONF_BB_DEEP,
        OVERSOLD_BOUNCE_CONF_BONUS_RSI,
        OVERSOLD_BOUNCE_CONF_BONUS_Z,
        OVERSOLD_BOUNCE_CONF_BONUS_BB,
    )

    # Get 5m candles
    candles = _get_candles(token, 'candles_5m', OVERSOLD_BOUNCE_CANDLE_FETCH)
    if len(candles) < OVERSOLD_BOUNCE_MIN_CANDLES:
        return None

    closes = [c['close'] for c in candles]
    volumes = [c['volume'] for c in candles]
    price = closes[-1]

    # 1. RSI check — must be oversold but not cliff-edge
    rsi = _calc_rsi(closes, period=OVERSOLD_BOUNCE_RSI_PERIOD)
    if rsi is None:
        return None
    if rsi < OVERSOLD_BOUNCE_RSI_MIN:
        return None  # too extreme, likely falling knife
    if rsi > OVERSOLD_BOUNCE_RSI_MAX:
        return None  # not oversold enough

    # 2. Z-score check — price must be deeply below mean
    lookback = min(OVERSOLD_BOUNCE_Z_LOOKBACK, len(closes))
    mean = statistics.mean(closes[-lookback:])
    std = statistics.stdev(closes[-lookback:])
    z_score = (price - mean) / std if std > 0 else 0
    if z_score > OVERSOLD_BOUNCE_Z_MAX:
        return None  # not extended enough below mean

    # 3. BB position check — price must be below middle band
    bb_position = _calc_bb_position(closes, period=OVERSOLD_BOUNCE_BB_PERIOD)
    if bb_position is None:
        return None
    if bb_position > OVERSOLD_BOUNCE_BB_MAX:
        return None  # not in lower band

    # 4. Volume exhaustion check — sellers must be exhausting
    # Volume drying up = selling pressure fading = bounce imminent
    if len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
        if vol_ratio > OVERSOLD_BOUNCE_VOL_RATIO_MAX:
            return None  # volume too high, selling still active
    else:
        vol_ratio = 1

    # 5. Momentum check — must be falling or flat (sellers active/exhausted)
    # Rising momentum = already bouncing, don't chase
    if len(closes) >= OVERSOLD_BOUNCE_MOM_LOOKBACK + 1:
        vel = (closes[-1] - closes[-OVERSOLD_BOUNCE_MOM_LOOKBACK - 1]) / closes[-OVERSOLD_BOUNCE_MOM_LOOKBACK - 1] * 100
        momentum_state = 'rising' if vel > OVERSOLD_BOUNCE_MOM_THRESHOLD else 'falling' if vel < -OVERSOLD_BOUNCE_MOM_THRESHOLD else 'flat'
    else:
        momentum_state = 'flat'

    # Rising momentum = already bouncing, skip (don't chase)
    if momentum_state == 'rising':
        return None

    # 5. Staleness check — oversold conditions change quickly
    if price_age_minutes(token) > OVERSOLD_BOUNCE_STALENESS_MIN:
        return None

    # Calculate confidence
    conf = OVERSOLD_BOUNCE_CONF_BASE
    # Bonus for deeper oversold
    if rsi < OVERSOLD_BOUNCE_CONF_RSI_DEEP:
        conf += OVERSOLD_BOUNCE_CONF_BONUS_RSI
    # Bonus for deeper z-score
    if z_score < OVERSOLD_BOUNCE_CONF_Z_DEEP:
        conf += OVERSOLD_BOUNCE_CONF_BONUS_Z
    # Bonus for very low BB position
    if bb_position < OVERSOLD_BOUNCE_CONF_BB_DEEP:
        conf += OVERSOLD_BOUNCE_CONF_BONUS_BB
    conf = min(conf, OVERSOLD_BOUNCE_CONF_CAP)

    # Value = z-score magnitude for sizing (deeper = more extreme = larger position)
    value = abs(z_score)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': value,
        'price': price,
        'rsi': rsi,
        'z_score': z_score,
        'bb_position': bb_position,
        'momentum_state': momentum_state,
        'vol_ratio': vol_ratio,
    }


def scan_signals() -> int:
    """Scan all tokens for oversold bounce setups."""
    from signal_schema import get_all_latest_prices

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue

        # Layer 1: master kill-switch
        if not OVERSOLD_BOUNCE_ENABLED:
            continue

        # Layer 1: blacklists
        if token.upper() in LONG_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction='LONG'):
            continue

        sig = detect(token)
        if not sig:
            continue

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
            z_score=sig.get('z_score'),
            momentum_state=sig.get('momentum_state'),
        )
        if sid:
            added += 1
            from hermes_constants import OVERSOLD_BOUNCE_COOLDOWN_HOURS
            set_cooldown(token, 'LONG', hours=OVERSOLD_BOUNCE_COOLDOWN_HOURS)
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    n = run()
    print(f"oversold_bounce: {n} signals emitted")
