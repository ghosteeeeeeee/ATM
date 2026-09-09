#!/usr/bin/env python3
"""pullback_entry.py — Buy low-volume pullbacks after strong moves, before continuation.
Scale-agnostic pattern that repeats at different price levels and timeframes.

Entry: Post-impulse consolidation with volume dry-up = calm before next leg up.
Classification: Mean-reversion (buying the dip = contrarian, allowed in CHOP).
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    PULLBACK_ENTRY_ENABLED,
    PULLBACK_ENTRY_PLUS_ENABLED,
    PULLBACK_ENTRY_MINUS_ENABLED,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'pullback_entry_long'
SIGNAL_TYPE_SHORT = 'pullback_entry_short'
SOURCE_LONG       = 'pullback-entry+'
SOURCE_SHORT      = 'pullback-entry-'

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


def _calc_bb_width(closes, period=20):
    """Calculate Bollinger Band width as percentage."""
    if len(closes) < period:
        return None
    import statistics
    sma = statistics.mean(closes[-period:])
    std = statistics.stdev(closes[-period:])
    if sma <= 0:
        return None
    return (2 * std / sma) * 100


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


def _calc_ema(closes, period=20):
    """Calculate EMA."""
    if len(closes) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = closes[0]
    for price in closes[1:]:
        ema = (price - ema) * multiplier + ema
    return ema


def detect(token):
    """Detect pullback entry setup. Returns {direction, confidence, value, price} or None."""
    from hermes_constants import (
        PULLBACK_IMPULSE_MIN_PCT,
        PULLBACK_IMPULSE_LOOKBACK,
        PULLBACK_DIP_MIN_PCT,
        PULLBACK_VOLUME_RATIO,
        PULLBACK_BB_WIDTH_MAX,
        PULLBACK_RSI_MIN,
        PULLBACK_RSI_MAX,
        PULLBACK_EMA_PERIOD,
    )

    # Get 5m candles
    from hermes_constants import PULLBACK_MIN_CANDLES, PULLBACK_CANDLE_FETCH
    candles = _get_candles(token, 'candles_5m', PULLBACK_CANDLE_FETCH)
    if len(candles) < PULLBACK_MIN_CANDLES:
        return None

    closes = [c['close'] for c in candles]
    volumes = [c['volume'] for c in candles]
    price = closes[-1]

    # 1. Detect prior impulse (strong move up or down)
    impulse_lookback = min(PULLBACK_IMPULSE_LOOKBACK, len(closes) - 1)
    recent_high = max(closes[-impulse_lookback:])
    recent_low = min(closes[-impulse_lookback:])
    impulse_up = (recent_high - closes[-impulse_lookback - 1]) / closes[-impulse_lookback - 1] * 100
    impulse_down = (closes[-impulse_lookback - 1] - recent_low) / closes[-impulse_lookback - 1] * 100

    # 2. Detect pullback from impulse high/low
    pullback_from_high = (recent_high - price) / recent_high * 100
    pullback_from_low = (price - recent_low) / recent_low * 100

    # Determine direction based on which impulse is stronger
    if impulse_up > PULLBACK_IMPULSE_MIN_PCT and pullback_from_high >= PULLBACK_DIP_MIN_PCT:
        direction = 'LONG'
        impulse_pct = impulse_up
        pullback_pct = pullback_from_high
    elif impulse_down > PULLBACK_IMPULSE_MIN_PCT and pullback_from_low >= PULLBACK_DIP_MIN_PCT:
        direction = 'SHORT'
        impulse_pct = impulse_down
        pullback_pct = pullback_from_low
    else:
        return None

    # 3. Volume dry-up check
    from hermes_constants import PULLBACK_VOL_LOOKBACK
    if len(volumes) < PULLBACK_VOL_LOOKBACK:
        return None
    avg_vol = sum(volumes[-PULLBACK_VOL_LOOKBACK:]) / PULLBACK_VOL_LOOKBACK
    if avg_vol <= 0:
        return None
    current_vol = volumes[-1]
    vol_ratio = current_vol / avg_vol
    if vol_ratio > PULLBACK_VOLUME_RATIO:
        return None  # volume not dry enough

    # 4. BB squeeze check
    bb_width = _calc_bb_width(closes)
    if bb_width is None or bb_width > PULLBACK_BB_WIDTH_MAX:
        return None

    # 5. Trend intact check
    ema = _calc_ema(closes, PULLBACK_EMA_PERIOD)
    if ema is None:
        return None
    if direction == 'LONG' and price < ema:
        return None  # price below EMA = trend broken
    if direction == 'SHORT' and price > ema:
        return None  # price above EMA = trend broken

    # RSI check
    rsi = _calc_rsi(closes)
    if rsi is None:
        return None
    if direction == 'LONG' and (rsi < PULLBACK_RSI_MIN or rsi > PULLBACK_RSI_MAX):
        return None
    if direction == 'SHORT' and (rsi < (100 - PULLBACK_RSI_MAX) or rsi > (100 - PULLBACK_RSI_MIN)):
        return None

    # 6. Support level check (price near recent swing low for LONG, high for SHORT)
    # Already handled by pullback detection above

    # Calculate confidence
    from hermes_constants import (
        PULLBACK_CONF_BASE, PULLBACK_CONF_CAP,
        PULLBACK_CONF_IMPULSE_STRONG_PCT, PULLBACK_CONF_VOL_DRY_THRESHOLD,
        PULLBACK_CONF_BB_SQUEEZE_THRESHOLD, PULLBACK_CONF_BONUS_STRONG,
        PULLBACK_CONF_BONUS_DRY, PULLBACK_CONF_BONUS_SQUEEZE,
    )
    conf = PULLBACK_CONF_BASE
    # Bonus for strong impulse
    if impulse_pct > PULLBACK_CONF_IMPULSE_STRONG_PCT:
        conf += PULLBACK_CONF_BONUS_STRONG
    # Bonus for very low volume
    if vol_ratio < PULLBACK_CONF_VOL_DRY_THRESHOLD:
        conf += PULLBACK_CONF_BONUS_DRY
    # Bonus for tight BB squeeze
    if bb_width < PULLBACK_CONF_BB_SQUEEZE_THRESHOLD:
        conf += PULLBACK_CONF_BONUS_SQUEEZE
    conf = min(conf, PULLBACK_CONF_CAP)

    # Value = impulse size for TP calculation
    value = impulse_pct

    return {
        'direction': direction,
        'confidence': conf,
        'value': value,
        'price': price,
        'impulse_pct': impulse_pct,
        'pullback_pct': pullback_pct,
        'vol_ratio': vol_ratio,
        'bb_width': bb_width,
        'rsi': rsi,
    }


def scan_signals() -> int:
    """Scan all tokens for pullback entry setups."""
    from signal_schema import get_all_latest_prices

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue

        # Staleness check
        from hermes_constants import PULLBACK_STALENESS_MIN
        if price_age_minutes(token) > PULLBACK_STALENESS_MIN:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not PULLBACK_ENTRY_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not PULLBACK_ENTRY_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
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
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=None,
        )
        if sid:
            added += 1
            from hermes_constants import PULLBACK_ENTRY_COOLDOWN_HOURS
            set_cooldown(token, direction, hours=PULLBACK_ENTRY_COOLDOWN_HOURS)
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    n = run()
    print(f"pullback_entry: {n} signals emitted")
