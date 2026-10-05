#!/usr/bin/env python3
"""trend_ride_long.py — Ride established uptrends with momentum confirmation.

THESIS:
  During established uptrends (price above rising EMAs), momentum-driven
  continuation produces profitable LONG entries when RSI is in the 50-70
  zone — positive momentum without overbought conditions. Existing LONG
  detectors (bb_bounce, support_resistance, volume_breakout) fire on
  bounces and breakouts — not on trend continuation. This signal captures
  the steady grind.

  Backtested (30d, signal-time RSI from _signal_metadata):
    RSI 50-70 LONG: 274T, 52.9% WR, +$2.10 overall
    EXTREME regime:  99T, 58.6% WR, +$5.69 (strong edge)
    HIGH regime:     91T, 51.6% WR, -$2.38 (no edge)
    NORMAL regime:   79T, 45.6% WR, -$1.38 (no edge)

ENTRY CONDITIONS (LONG only):
  1. Price > EMA20 (5m) — uptrend confirmed
  2. EMA20 > EMA50 (5m) — trend direction bullish
  3. RSI(14) between 50-70 — momentum zone (validated by backtest)
  4. Volume > 1.2x 20-period average — participation confirmed
  5. (Optional boost) 1h EMA20 > 1h EMA50 — higher TF alignment

DATA SOURCE:
  Primary: candles_5m (EMA20/50, RSI, volume)
  Higher TF: candles_1h (EMA20/50 trend confirmation)

Source string: trend-ride+ (LONG only)
Signal type: trend_ride_long
"""

import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    TREND_RIDE_LONG_ENABLED,
    TREND_RIDE_LONG_PLUS_ENABLED,
    LONG_BLACKLIST,
    TREND_RIDE_RSI_MIN,
    TREND_RIDE_RSI_MAX,
    TREND_RIDE_VOL_MULT,
    TREND_RIDE_CONF_BASE,
    TREND_RIDE_CONF_CAP,
    TREND_RIDE_COOLDOWN_HOURS,
    TREND_RIDE_EMA_FAST,
    TREND_RIDE_EMA_SLOW,
    TREND_RIDE_RSI_PERIOD,
    TREND_RIDE_VOL_PERIOD,
    TREND_RIDE_MAX_AGE_5M,
    TREND_RIDE_MAX_AGE_1H,
    TREND_RIDE_HTF_BONUS,
    TREND_RIDE_RSI_SWEET_MIN,
    TREND_RIDE_RSI_SWEET_MAX,
    TREND_RIDE_SWEET_BONUS,
)

SIGNAL_TYPE_LONG = 'trend_ride_long'
SOURCE_LONG = 'trend-ride+'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _get_closes(token, table, limit):
    """DB fetch with proper connection cleanup. Returns oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT close FROM {table}
            WHERE token = ? AND is_closed = 1 ORDER BY ts DESC LIMIT ?
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


def _get_ohlcv(token, table, limit):
    """Fetch OHLCV with proper connection cleanup. Returns oldest-first list of dicts."""
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


def _get_candle_age(token, table):
    """Get age in seconds of latest candle for token."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        c = conn.cursor()
        c.execute(f"SELECT ts FROM {table} WHERE token=? ORDER BY ts DESC LIMIT 1",
                  (token.upper(),))
        row = c.fetchone()
        if not row:
            return None
        return time.time() - row[0]
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _compute_ema(closes, period):
    """Exponential moving average. Returns latest EMA value."""
    if not closes or len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = closes[0]
    for price in closes[1:]:
        ema = price * k + ema * (1 - k)
    return ema


def _compute_rsi(closes, period):
    """Simple RSI (SMA of gains/losses over period). Returns None if insufficient data.
    Note: matches hl-sync-guardian.py:2457-2461 methodology (sum of positive changes / period)."""
    if not closes or len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _compute_avg_volume(candles, period):
    """Average volume over last N candles."""
    if not candles or len(candles) < period:
        return None
    vols = [c['volume'] for c in candles[-period:]]
    return sum(vols) / len(vols)


def detect(token):
    """Return {direction, confidence, value, price} or None."""
    # Staleness checks
    age_5m = _get_candle_age(token, 'candles_5m')
    if age_5m is None or age_5m > TREND_RIDE_MAX_AGE_5M:
        return None

    # Fetch 5m data (need EMA_SLOW + RSI_PERIOD + buffer)
    candles_5m = _get_ohlcv(token, 'candles_5m', max(TREND_RIDE_EMA_SLOW + 10, TREND_RIDE_VOL_PERIOD + 5, TREND_RIDE_RSI_PERIOD + 5))
    if len(candles_5m) < TREND_RIDE_EMA_SLOW + 1:
        return None

    closes_5m = [c['close'] for c in candles_5m]
    price = closes_5m[-1]

    # Condition 1+2: EMA alignment on 5m
    ema_fast = _compute_ema(closes_5m, TREND_RIDE_EMA_FAST)
    ema_slow = _compute_ema(closes_5m, TREND_RIDE_EMA_SLOW)
    if ema_fast is None or ema_slow is None:
        return None
    if not (price > ema_fast and ema_fast > ema_slow):
        return None

    # Condition 3: RSI in momentum zone
    rsi = _compute_rsi(closes_5m, TREND_RIDE_RSI_PERIOD)
    if rsi is None or not (TREND_RIDE_RSI_MIN <= rsi <= TREND_RIDE_RSI_MAX):
        return None

    # Condition 4: Volume confirmation (skip if volume data unavailable)
    avg_vol = _compute_avg_volume(candles_5m, TREND_RIDE_VOL_PERIOD)
    if avg_vol is not None and avg_vol > 0:
        last_vol = candles_5m[-1]['volume']
        if last_vol > 0 and last_vol < avg_vol * TREND_RIDE_VOL_MULT:
            return None

    # Optional boost: 1h EMA alignment
    conf = TREND_RIDE_CONF_BASE
    htf_aligned = False
    age_1h = _get_candle_age(token, 'candles_1h')
    if age_1h is not None and age_1h <= TREND_RIDE_MAX_AGE_1H:
        closes_1h = _get_closes(token, 'candles_1h', TREND_RIDE_EMA_SLOW + 10)
        if len(closes_1h) >= TREND_RIDE_EMA_SLOW + 1:
            ema_fast_1h = _compute_ema(closes_1h, TREND_RIDE_EMA_FAST)
            ema_slow_1h = _compute_ema(closes_1h, TREND_RIDE_EMA_SLOW)
            if ema_fast_1h is not None and ema_slow_1h is not None:
                if ema_fast_1h > ema_slow_1h:
                    htf_aligned = True
                    conf = min(conf + TREND_RIDE_HTF_BONUS, TREND_RIDE_CONF_CAP)

    # Confidence scaling by RSI position (mid-range = best)
    if TREND_RIDE_RSI_SWEET_MIN <= rsi <= TREND_RIDE_RSI_SWEET_MAX:
        conf = min(conf + TREND_RIDE_SWEET_BONUS, TREND_RIDE_CONF_CAP)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': round(rsi, 1),
        'price': price,
        'htf_aligned': htf_aligned,
    }


def scan_signals() -> int:
    added = 0
    # Get token universe from candles_5m (tokens with recent data)
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT token FROM candles_5m
            WHERE ts > strftime('%s','now') - 3600
        """)
        tokens = [r[0] for r in c.fetchall()]
    except Exception:
        tokens = []
    finally:
        if conn:
            conn.close()

    for token in tokens:
        # Guards
        if price_age_minutes(token) > 10:
            continue

        # Layer 1: kill-switch
        if not TREND_RIDE_LONG_PLUS_ENABLED:
            continue

        # Layer 1: blacklist
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
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, 'LONG', hours=TREND_RIDE_COOLDOWN_HOURS)
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    n = scan_signals()
    print(f'trend_ride_long: {n} signals added')
