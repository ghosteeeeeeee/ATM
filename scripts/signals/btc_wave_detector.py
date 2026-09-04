#!/usr/bin/env python3
"""
btc_wave_detector — BTC EMA300 crossover + volume surge signal.

Detects the "wave pattern": BTC crosses above EMA300, holds for N minutes,
and volume begins accelerating. High-conviction LONG setup.

Pattern (observed Sep 3 2026, +5.10% move):
  1. Chop/Coil: price oscillates around EMA300, low volume
  2. The Cross: price crosses above EMA300 and holds 60+ min
  3. Volume Explosion: 5m volume avg > 1.5x of 1h avg
  4. Entry: ride the wave

Data: candles_1m from candles.db (BTC only)
"""

import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    BTC_WAVE_DETECTOR_ENABLED,
    BTC_WAVE_EMA_PERIOD,
    BTC_WAVE_HOLD_BARS,
    BTC_WAVE_VOLUME_MULT,
    BTC_WAVE_COOLDOWN_HOURS,
    BTC_WAVE_MIN_CANDLES,
    BTC_WAVE_ZSCORE_MAX,
    BTC_WAVE_EMA_SLOPE_MIN,
    BTC_WAVE_PRICE_AGE_MAX,
    BTC_WAVE_STALENESS_MAX,
    BTC_WAVE_VOL_SHORT,
    BTC_WAVE_VOL_LONG,
    BTC_WAVE_CONF_BASE,
    BTC_WAVE_CONF_CAP,
    BTC_WAVE_CONF_BONUS_SLOPE,
    SHORT_BLACKLIST,
    LONG_BLACKLIST,
)

TOKEN = 'BTC'
SIGNAL_TYPE_LONG = 'btc_wave_long'
SOURCE_LONG = 'btc-wave+'

_CANDLES_DB = None


def _get_db():
    global _CANDLES_DB
    if _CANDLES_DB is None:
        _CANDLES_DB = f'{HERMES_DATA}/candles.db'
    return _CANDLES_DB


def _ema(data, period):
    """SMA-seeded EMA."""
    if len(data) < period:
        return None
    k = 2.0 / (period + 1)
    val = sum(data[:period]) / period
    for p in data[period:]:
        val = p * k + val * (1 - k)
    return val


def _get_candles(token, limit):
    """Fetch 1m candles. Returns oldest-first list of (ts, close, volume)."""
    conn = None
    try:
        conn = sqlite3.connect(_get_db(), timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, close, volume FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token, limit))
        rows = cur.fetchall()
        if not rows:
            return []
        return list(reversed(rows))  # oldest-first
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def detect(token):
    """Check BTC for EMA300 crossover + volume surge."""
    if token != TOKEN:
        return None

    # Check price freshness
    age = price_age_minutes(TOKEN)
    if age > BTC_WAVE_PRICE_AGE_MAX:
        return None

    candles = _get_candles(TOKEN, BTC_WAVE_MIN_CANDLES)
    if len(candles) < BTC_WAVE_MIN_CANDLES:
        return None

    closes = [c[1] for c in candles]
    volumes = [c[2] for c in candles]

    # Check candle freshness
    most_recent_ts = candles[-1][0]
    if time.time() - most_recent_ts > BTC_WAVE_STALENESS_MAX:
        return None

    # Compute EMA300
    ema300 = _ema(closes, BTC_WAVE_EMA_PERIOD)
    if ema300 is None:
        return None

    # Check: last N closes ALL above EMA300 (the "hold" filter)
    hold_bars = BTC_WAVE_HOLD_BARS
    if len(closes) < hold_bars:
        return None
    recent_closes = closes[-hold_bars:]
    if not all(c > ema300 for c in recent_closes):
        return None

    # Check: EMA300 slope at cross time (not declining sharply)
    ema_slope_pct = 0.0
    if len(closes) >= BTC_WAVE_EMA_PERIOD + 10:
        ema_prev = _ema(closes[:-10], BTC_WAVE_EMA_PERIOD)
        ema_now = _ema(closes, BTC_WAVE_EMA_PERIOD)
        if ema_prev and ema_now:
            ema_slope_pct = (ema_now - ema_prev) / ema_prev * 100
            if ema_slope_pct < BTC_WAVE_EMA_SLOPE_MIN:
                return None  # EMA300 declining too sharply, likely fake-out

    # Check: volume surge (short rolling avg vs long rolling avg)
    vol_5m_avg = sum(volumes[-BTC_WAVE_VOL_SHORT:]) / BTC_WAVE_VOL_SHORT if len(volumes) >= BTC_WAVE_VOL_SHORT else 0
    vol_1h_avg = sum(volumes[-BTC_WAVE_VOL_LONG:]) / BTC_WAVE_VOL_LONG if len(volumes) >= BTC_WAVE_VOL_LONG else 0
    if vol_1h_avg <= 0:
        return None
    vol_ratio = vol_5m_avg / vol_1h_avg
    if vol_ratio < BTC_WAVE_VOLUME_MULT:
        return None

    # Check: z-score not overbought (don't buy the top)
    if len(closes) >= 20:
        mean = sum(closes[-20:]) / 20
        std = (sum((c - mean) ** 2 for c in closes[-20:]) / 20) ** 0.5
        zscore = (closes[-1] - mean) / std if std > 0 else 0
        if abs(zscore) > BTC_WAVE_ZSCORE_MAX:
            return None  # overextended
    else:
        zscore = 0.0

    # Confidence scoring based on volume surge magnitude
    conf = BTC_WAVE_CONF_BASE
    if vol_ratio > 2.0:
        conf += 5
    if vol_ratio > 3.0:
        conf += 5
    if vol_ratio > 5.0:
        conf += 5
    conf = min(conf, BTC_WAVE_CONF_CAP)

    # Bonus: EMA300 slope positive (stronger trend)
    if ema_slope_pct > BTC_WAVE_CONF_BONUS_SLOPE:
        conf += 3

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': vol_ratio,
        'price': closes[-1],
        'z_score': zscore,
    }


def scan_signals() -> int:
    """Scan BTC for wave pattern."""
    if not BTC_WAVE_DETECTOR_ENABLED:
        return 0

    added = 0
    direction = 'LONG'

    # Layer 1: per-direction kill-switch
    if direction == 'LONG' and not BTC_WAVE_DETECTOR_ENABLED:
        return 0

    # Layer 1: blacklist
    if direction == 'LONG' and TOKEN in LONG_BLACKLIST:
        return 0

    # Cooldown
    if get_cooldown(TOKEN, direction=direction):
        return 0

    sig = detect(TOKEN)
    if sig is None:
        return 0

    # Layer 1: re-check direction (safety)
    if sig['direction'] != direction:
        return 0

    sig_type = SIGNAL_TYPE_LONG
    source = SOURCE_LONG

    sid = add_signal(
        token=TOKEN,
        direction=direction,
        signal_type=sig_type,
        source=source,
        confidence=sig['confidence'],
        value=sig.get('value'),
        price=sig['price'],
        exchange='hyperliquid',
        timeframe='1m',
        z_score=sig.get('z_score'),
    )
    if sid:
        added += 1
        set_cooldown(TOKEN, direction, hours=BTC_WAVE_COOLDOWN_HOURS)

    return added


def run():
    """Entry point for signals_runner.
    Uses run() with no params — signal reads from candles.db directly.
    """
    return scan_signals()
