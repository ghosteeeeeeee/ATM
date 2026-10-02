#!/usr/bin/env python3
"""ema_reclaim_long.py — EMA20 reclaim after decline (enter LONG).

Pattern: Decline → price reclaims EMA20 with confirming volume → join the reclaim.
Different from doji_bottom: mid-band RSI (35-55), volume confirmation (not dry-up),
trigger is EMA reclaim not indecision candle.

Classification: Mean-reversion (join reclaim). ALLOWED in CHOP/NEUTRAL.
"""
import sys, os, sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    EMA_RECLAIM_ENABLED,
    EMA_RECLAIM_DECLINE_MIN_PCT,
    EMA_RECLAIM_LOOKBACK,
    EMA_RECLAIM_VOL_MIN_RATIO,
    EMA_RECLAIM_RSI_MIN,
    EMA_RECLAIM_RSI_MAX,
    EMA_RECLAIM_CONF_BASE,
    EMA_RECLAIM_CONF_CAP,
    EMA_RECLAIM_COOLDOWN_HOURS,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'ema_reclaim_long'
SOURCE_LONG      = 'ema-reclaim-long'

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


def _ema(values, period):
    """Exponential moving average over a list, oldest-first. Returns None if too short."""
    if not values or len(values) < period:
        return None
    k = 2.0 / (period + 1)
    ema_val = sum(values[:period]) / period
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


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


def _detect_long(token):
    """Detect EMA20 reclaim after a decline.

    Returns {direction, confidence, value, price, ...} or None.
    """
    candles = _get_candles(token, 'candles_5m', 60)
    if len(candles) < 25:
        return None

    closes = [c['close'] for c in candles]
    volumes = [c['volume'] for c in candles]
    price = closes[-1]
    latest = candles[-1]

    # 1. Prior decline over LOOKBACK candles (before the reclaim candle)
    lookback = min(EMA_RECLAIM_LOOKBACK, len(closes) - 2)
    if lookback < 3:
        return None
    decline_start = closes[-lookback - 1]
    if decline_start <= 0:
        return None
    # decline measured from lookback-start close to the low before reclaim
    pre_reclaim_min = min(closes[-lookback - 1:-1])
    if pre_reclaim_min <= 0:
        return None
    decline_pct = (decline_start - pre_reclaim_min) / decline_start * 100
    if decline_pct < EMA_RECLAIM_DECLINE_MIN_PCT:
        return None

    # 2. Latest candle closes ABOVE EMA20 (reclaim) and body is green
    ema20 = _ema(closes, 20)
    if ema20 is None:
        return None
    if latest['close'] <= ema20:
        return None
    if latest['close'] <= latest['open']:
        return None

    # 3. Prior candles should have been below/near EMA (actual reclaim, not always-above)
    ema20_prev = _ema(closes[:-1], 20)
    if ema20_prev is not None and closes[-2] > ema20_prev and closes[-3] > (_ema(closes[:-2], 20) or ema20_prev):
        # already above for 2+ bars — not a fresh reclaim
        return None

    # 4. Volume confirmation: reclaim candle >= VOL_MIN_RATIO × avg (not exhaustion dry-up)
    if len(volumes) < 20:
        return None
    avg_vol = sum(volumes[-21:-1]) / 20
    if avg_vol <= 0:
        return None
    vol_ratio = volumes[-1] / avg_vol
    if vol_ratio < EMA_RECLAIM_VOL_MIN_RATIO:
        return None

    # 5. RSI mid-band — not oversold (doji territory), not overbought
    rsi = _calc_rsi(closes)
    if rsi is None or rsi < EMA_RECLAIM_RSI_MIN or rsi > EMA_RECLAIM_RSI_MAX:
        return None
    try:
        from signals.rsi_1m import compute_rsi_1m
        rsi_1m = compute_rsi_1m(token)
    except Exception:
        rsi_1m = None

    # Confidence
    conf = EMA_RECLAIM_CONF_BASE
    if vol_ratio >= 1.2:
        conf += 4
    if rsi >= 45:
        conf += 3
    # reclaim distance — further above EMA = stronger reclaim
    reclaim_pct = (latest['close'] - ema20) / ema20 * 100
    if reclaim_pct >= 0.3:
        conf += 3
    conf = min(conf, EMA_RECLAIM_CONF_CAP)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': decline_pct,
        'price': price,
        'decline_pct': decline_pct,
        'vol_ratio': vol_ratio,
        'rsi': rsi_1m if rsi_1m is not None else rsi,
        'ema20': ema20,
        'reclaim_pct': reclaim_pct,
    }


def scan_signals() -> int:
    """Scan all tokens for EMA20 reclaim setups."""
    from signal_schema import get_all_latest_prices

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if not EMA_RECLAIM_ENABLED:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(token, direction='LONG'):
            continue

        sig = _detect_long(token)
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
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=EMA_RECLAIM_COOLDOWN_HOURS)
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    n = run()
    print(f"ema_reclaim_long: {n} signals emitted")
