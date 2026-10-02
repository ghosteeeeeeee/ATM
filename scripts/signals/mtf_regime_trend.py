#!/usr/bin/env python3
"""MTF Regime Trend — Cross-timeframe regime alignment signal.

Thesis: 4h regime + momentum entry = trend following with acceleration confirmation.
Entry: 4h regime LONG_BIAS/SHORT_BIAS + momentum from recent low/high + not reversing + volume confirmation.
Exits: Handled downstream by position_manager (ATR SL, PM Trail, etc.)

Signal types:
  - mtf_regime_trend_long  : LONG (4h LONG_BIAS + upward momentum)
  - mtf_regime_trend_short : SHORT (4h SHORT_BIAS + downward momentum)

Family: Trend (pairs with Volume, Momentum for confluence)
"""

import sys
import os
import sqlite3

sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    MTF_REGIME_TREND_PLUS_ENABLED,
    MTF_REGIME_TREND_MINUS_ENABLED,
    MTF_REGIME_TREND_SLOPE_THRESHOLD,
    MTF_REGIME_TREND_PULLBACK_PCT,
    MTF_REGIME_TREND_VOLUME_MIN,
    MTF_REGIME_TREND_EMA_PERIOD,
    MTF_REGIME_TREND_ATR_PERIOD,
    MTF_REGIME_TREND_COOLDOWN_MINUTES,
    MTF_REGIME_TREND_CONF_BASE,
    MTF_REGIME_TREND_CONF_CAP,
    MTF_REGIME_TREND_SLOPE_BONUS_MAX,
    MTF_REGIME_TREND_PULLBACK_BONUS_MAX,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'mtf_regime_trend_long'
SIGNAL_TYPE_SHORT = 'mtf_regime_trend_short'
SOURCE_LONG = 'mtf-regime-trend+'
SOURCE_SHORT = 'mtf-regime-trend-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[mtf-regime-trend] {msg}", flush=True)


def _get_4h_regime(token):
    """Get 4h regime and slope from PostgreSQL momentum_cache."""
    try:
        import psycopg2
        conn = None
        try:
            conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
            cur = conn.cursor()
            cur.execute(
                "SELECT regime_4h, slope_4h FROM momentum_cache WHERE token = %s",
                (token.upper(),)
            )
            row = cur.fetchone()
        finally:
            if conn:
                conn.close()
        if row and row[0] and row[1] is not None:
            return row[0], float(row[1])
        return None, None
    except Exception:
        return None, None


def _get_candles(token, table='candles_1m', limit=350):
    """Fetch OHLCV candles oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume FROM (
                SELECT ts, open, high, low, close, volume
                FROM {table}
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC
                LIMIT ?
            ) sub ORDER BY ts ASC
        """, (token.upper(), limit))
        rows = cur.fetchall()
        # Skip corrupted rows (NULL OHLC) and coerce NULL volume — these crash
        # EMA/momentum/accel math downstream (TypeError/ZeroDivisionError).
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5] or 0.0}
                for r in rows
                if r[1] is not None and r[2] is not None and r[3] is not None and r[4] is not None]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _compute_ema(closes, period):
    """Compute EMA."""
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for c in closes[period:]:
        ema = c * k + ema * (1 - k)
    return ema


def _compute_atr(candles, period=14):
    """Compute ATR."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        tr = max(
            candles[i]['high'] - candles[i]['low'],
            abs(candles[i]['high'] - candles[i-1]['close']),
            abs(candles[i]['low'] - candles[i-1]['close'])
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def detect(token):
    """Detect MTF regime trend signal for a token."""
    # Get 4h regime
    regime_4h, slope_4h = _get_4h_regime(token)
    if regime_4h is None:
        return None

    # Check slope threshold
    if regime_4h == 'LONG_BIAS':
        direction = 'LONG'
        if slope_4h < MTF_REGIME_TREND_SLOPE_THRESHOLD:
            return None
    elif regime_4h == 'SHORT_BIAS':
        direction = 'SHORT'
        if slope_4h > -MTF_REGIME_TREND_SLOPE_THRESHOLD:
            return None
    else:
        return None  # NEUTRAL regime

    # Get 1m candles
    candles = _get_candles(token, 'candles_1m', 350)
    if len(candles) < MTF_REGIME_TREND_EMA_PERIOD + 10:
        return None

    closes = [c['close'] for c in candles]
    price = closes[-1]
    if not price or price <= 0:
        return None  # corrupted/zero price — never fire (SHORT momentum_pct would read 100%)

    # EMA300 filter
    ema300 = _compute_ema(closes, MTF_REGIME_TREND_EMA_PERIOD)
    if ema300 is None:
        return None

    if direction == 'LONG' and price < ema300:
        return None  # price below EMA300 — not in uptrend
    if direction == 'SHORT' and price > ema300:
        return None  # price above EMA300 — not in downtrend

    # RSI filter (2026-10-02)
    # LONG: block when RSI < 30 (oversold = catching falling knife)
    # SHORT: block when RSI > 70 (overbought = catching rising knife)
    # Backtest: RSI <30 LONG = 3T 0%WR -$0.70 (all losers), RSI >=40 = 3T 100%WR +$0.29
    if len(closes) >= 14:
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-14:]]
        losses = [-d if d < 0 else 0 for d in deltas[-14:]]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100
        if direction == 'LONG' and rsi < 30:
            return None  # oversold — catching falling knife
        if direction == 'SHORT' and rsi > 70:
            return None  # overbought — catching rising knife

    # Momentum entry (2026-10-01)
    # Enter when price is moving in the trend direction
    # LONG: price rising from recent low (momentum)
    # SHORT: price falling from recent high (momentum)
    momentum_lookback = 15  # minutes
    if len(candles) >= momentum_lookback:
        if direction == 'LONG':
            # For LONG: price should be rising from recent low
            recent_low = min(c['low'] for c in candles[-momentum_lookback:])
            if recent_low <= 0:
                return None
            momentum_pct = (price - recent_low) / recent_low * 100
            if momentum_pct < MTF_REGIME_TREND_PULLBACK_PCT:
                return None  # no upward momentum
        else:
            # For SHORT: price should be falling from recent high
            recent_high = max(c['high'] for c in candles[-momentum_lookback:])
            if recent_high <= 0:
                return None
            momentum_pct = (recent_high - price) / recent_high * 100
            if momentum_pct < MTF_REGIME_TREND_PULLBACK_PCT:
                return None  # no downward momentum

    # Momentum acceleration check (2026-10-01)
    # Price should be ACCELERATING in trend direction, not decelerating
    accel_lookback = 5  # last 5 minutes
    if len(candles) >= accel_lookback:
        recent_candles = candles[-accel_lookback:]
        last_3_changes = []
        for i in range(-3, 0):
            prev_close = recent_candles[i-1]['close']
            if not prev_close:
                return None  # zero/None close — corrupted data, skip token
            last_3_changes.append((recent_candles[i]['close'] - prev_close) / prev_close * 100)
        avg_change = sum(last_3_changes) / len(last_3_changes)
        if direction == 'LONG':
            # For LONG: price should be rising, not falling
            if avg_change < -0.05:  # price falling hard — not momentum
                return None
        else:
            # For SHORT: price should be falling, not rising
            if avg_change > 0.05:  # price rising hard — not momentum
                return None

    # Volume check
    volumes = [(c['volume'] or 0.0) for c in candles[-20:]]
    if len(volumes) >= 20:
        vol_avg = sum(volumes) / len(volumes)
        vol_now = candles[-1]['volume'] or 0.0
        if vol_avg > 0 and vol_now < vol_avg * MTF_REGIME_TREND_VOLUME_MIN:
            return None  # volume too low

    # ATR for confidence
    atr = _compute_atr(candles, MTF_REGIME_TREND_ATR_PERIOD)
    atr_pct = (atr / price * 100) if (atr and price > 0) else 1.0

    # Confidence scoring
    conf = MTF_REGIME_TREND_CONF_BASE
    slope_bonus = min(MTF_REGIME_TREND_SLOPE_BONUS_MAX, abs(slope_4h) * 5)
    conf += slope_bonus

    if direction == 'LONG' and len(candles) >= momentum_lookback:
        recent_low = min(c['low'] for c in candles[-momentum_lookback:])
        if recent_low > 0:
            momentum_pct = (price - recent_low) / recent_low * 100
            momentum_bonus = min(MTF_REGIME_TREND_PULLBACK_BONUS_MAX, momentum_pct * 20)
            conf += momentum_bonus
    elif direction == 'SHORT' and len(candles) >= momentum_lookback:
        recent_high = max(c['high'] for c in candles[-momentum_lookback:])
        if recent_high > 0:
            momentum_pct = (recent_high - price) / recent_high * 100
            momentum_bonus = min(MTF_REGIME_TREND_PULLBACK_BONUS_MAX, momentum_pct * 20)
            conf += momentum_bonus

    conf = min(MTF_REGIME_TREND_CONF_CAP, int(conf))

    reason = f'4h_{regime_4h.lower()}_slope_{slope_4h:+.2f}_atr_{atr_pct:.2f}'
    return direction, conf, reason, atr_pct


def scan_signals():
    """Scan tokens for MTF regime trend signals."""
    added = 0

    # Get tokens from PostgreSQL momentum_cache (tokens with strong 4h trends)
    try:
        import psycopg2
        conn = None
        try:
            conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
            cur = conn.cursor()
            cur.execute("""
                SELECT token, regime_4h, slope_4h FROM momentum_cache
                WHERE regime_4h IN ('LONG_BIAS', 'SHORT_BIAS')
                  AND ABS(slope_4h) > %s
            """, (MTF_REGIME_TREND_SLOPE_THRESHOLD,))
            tokens = [(r[0], r[1], r[2]) for r in cur.fetchall()]
        finally:
            if conn:
                conn.close()
    except Exception as e:
        _log(f"ERROR getting tokens: {e}")
        tokens = []

    for token, regime_4h, slope_4h in tokens:
        # Blacklist check
        if token.upper() in LONG_BLACKLIST and regime_4h == 'LONG_BIAS':
            continue
        if token.upper() in SHORT_BLACKLIST and regime_4h == 'SHORT_BIAS':
            continue

        # Cooldown check
        direction = 'LONG' if regime_4h == 'LONG_BIAS' else 'SHORT'
        if get_cooldown(token, direction=direction):
            continue

        # Detect signal — isolate per-token failures (bad candle data must not kill the scan)
        try:
            result = detect(token)
        except Exception as e:
            _log(f"ERROR detect {token}: {e}")
            continue
        if result is None:
            continue

        sig_direction, conf, reason, atr_pct = result

        # Kill-switch check
        if sig_direction == 'LONG' and not MTF_REGIME_TREND_PLUS_ENABLED:
            continue
        if sig_direction == 'SHORT' and not MTF_REGIME_TREND_MINUS_ENABLED:
            continue

        # Get current price
        candles = _get_candles(token, 'candles_1m', 5)
        if not candles:
            continue
        price = candles[-1]['close']

        signal_type = SIGNAL_TYPE_LONG if sig_direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if sig_direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=sig_direction,
            signal_type=signal_type,
            source=source,
            confidence=conf,
            value=abs(slope_4h),
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
        )
        if sid:
            added += 1
            set_cooldown(token, sig_direction, hours=MTF_REGIME_TREND_COOLDOWN_MINUTES / 60)
            _log(f"{sig_direction} {token} | conf={conf} | {reason}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    # Test mode
    print("Testing MTF Regime Trend signal...")
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else 'MOVE'
    result = detect(token)
    print(f"Token: {token}")
    print(f"Result: {result}")
