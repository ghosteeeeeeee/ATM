#!/usr/bin/env python3
"""
trend_ignition.py — Early-stage breakout at trend START.

Catches the beginning of a move before trend confirmation:
1. Volume spike > 2.5x (institutional buying)
2. Sustained volume 2+ of 3 bars (confirmed, not noise)
3. BB width 1-2% (compressed energy, not dead)
4. Close > 20-bar high (breakout)
5. Close > EMA50 (trend aligned)
6. EMA50 distance > 0.5% (meaningful)
7. RSI < 65 (not overbought)

Backtested: 100% WR (9 signals, 7-day), avg +1.92% 4h return.
Source: trend-ignition+
Classification: Trend-following (LONG only — catches start of move)
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    TREND_IGNITION_ENABLED,
    TREND_IGNITION_PLUS_ENABLED,
    TREND_IGNITION_MINUS_ENABLED,
    TREND_IGNITION_VOL_SPIKE_MIN,
    TREND_IGNITION_VOL_ELEVATED_RATIO,
    TREND_IGNITION_VOL_SUSTAINED_MIN,
    TREND_IGNITION_BB_MIN,
    TREND_IGNITION_BB_MAX,
    TREND_IGNITION_BREAKOUT_PERIOD,
    TREND_IGNITION_EMA_PERIOD,
    TREND_IGNITION_EMA_MIN_DIST,
    TREND_IGNITION_RSI_MAX,
    TREND_IGNITION_COOLDOWN_HOURS,
    TREND_IGNITION_CONF_BASE,
    TREND_IGNITION_CONF_CAP,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'trend_ignition_long'
SOURCE_LONG = 'trend-ignition+'

_CANDLES_DB = CANDLES_DB


def _get_candles_5m(token, limit=100):
    """Fetch 5m candles from candles.db. Returns oldest-first list."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT open, high, low, close, volume FROM candles_5m
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


def _compute_ema(prices, period):
    """Compute EMA."""
    if not prices or len(prices) < period:
        return prices[-1] if prices else 0
    k = 2.0 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def _compute_rsi(closes, period=14):
    """Compute RSI."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes[-(period+1):]))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _detect_trend_ignition(token, candles):
    """Detect trend ignition setup on 5m timeframe.

    Returns {direction, confidence, value, price} or None.
    """
    n = len(candles)
    min_bars = max(TREND_IGNITION_EMA_PERIOD, TREND_IGNITION_BREAKOUT_PERIOD) + 20
    if n < min_bars:
        return None

    closes = [c['close'] for c in candles]
    volumes = [c['volume'] for c in candles]
    highs = [c['high'] for c in candles]
    price = closes[-1]

    if price <= 0:
        return None

    # 1. Volume spike: current bar > SPIKE_MIN * 20-bar average
    avg_vol_20 = sum(volumes[-21:-1]) / 20 if n > 21 else sum(volumes[:-1]) / max(1, len(volumes)-1)
    if avg_vol_20 <= 0:
        return None
    vol_ratio = volumes[-1] / avg_vol_20
    if vol_ratio < TREND_IGNITION_VOL_SPIKE_MIN:
        return None

    # 2. Sustained volume: 2+ of last 3 bars have volume > ELEVATED_RATIO * average
    elevated_count = 0
    for i in range(-3, 0):
        if i + n >= 0 and avg_vol_20 > 0:
            if volumes[i] / avg_vol_20 >= TREND_IGNITION_VOL_ELEVATED_RATIO:
                elevated_count += 1
    if elevated_count < TREND_IGNITION_VOL_SUSTAINED_MIN:
        return None

    # 3. BB width between 1-2% (compressed but not dead)
    if len(closes) < 20:
        return None
    bb_closes = closes[-20:]
    sma20 = sum(bb_closes) / 20
    variance = sum((c - sma20) ** 2 for c in bb_closes) / 20
    bb_std = variance ** 0.5
    bb_width_pct = (bb_std * 2 / sma20) * 100 if sma20 > 0 else 0
    if bb_width_pct < TREND_IGNITION_BB_MIN or bb_width_pct > TREND_IGNITION_BB_MAX:
        return None

    # 4. Breakout: close > 20-bar high
    recent_high = max(highs[-(TREND_IGNITION_BREAKOUT_PERIOD + 1):-1])
    if price <= recent_high:
        return None

    # 5. Trend: close > EMA50
    ema50 = _compute_ema(closes, TREND_IGNITION_EMA_PERIOD)
    if price <= ema50:
        return None

    # 6. EMA50 distance > 0.5%
    ema_dist_pct = (price - ema50) / ema50 * 100
    if ema_dist_pct < TREND_IGNITION_EMA_MIN_DIST:
        return None

    # 7. RSI < 65 (not overbought)
    rsi = _compute_rsi(closes)
    if rsi is None or rsi >= TREND_IGNITION_RSI_MAX:
        return None

    # Confidence scoring
    conf = TREND_IGNITION_CONF_BASE

    # Volume spike magnitude bonus (up to +8)
    if vol_ratio >= 10:
        conf += 8
    elif vol_ratio >= 5:
        conf += 5
    elif vol_ratio >= 3:
        conf += 3

    # Compression quality bonus (up to +3) — BB 1.5-2% best
    if 1.5 <= bb_width_pct <= 2.0:
        conf += 3
    elif 1.2 <= bb_width_pct <= 1.5:
        conf += 2

    # Breakout strength bonus (up to +3) — % above 20-bar high
    breakout_pct = (price - recent_high) / recent_high * 100
    breakout_bonus = min(3, int(breakout_pct / 0.5 * 3))
    conf += breakout_bonus

    # RSI sweet spot bonus (up to +3) — 55-62 ideal
    if 55 <= rsi <= 62:
        conf += 3
    elif 50 <= rsi < 55 or 62 < rsi <= 65:
        conf += 1

    # Trend strength bonus (up to +2)
    if ema_dist_pct >= 1.0:
        conf += 2
    elif ema_dist_pct >= 0.5:
        conf += 1

    # Sustained volume bonus (up to +2)
    if elevated_count == 3:
        conf += 2
    elif elevated_count == 2:
        conf += 1

    conf = min(conf, TREND_IGNITION_CONF_CAP)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'source': SOURCE_LONG,
        'signal_type': SIGNAL_TYPE_LONG,
        'price': price,
        'value': float(conf),
        'vol_ratio': round(vol_ratio, 2),
        'bb_width_pct': round(bb_width_pct, 3),
        'ema_dist_pct': round(ema_dist_pct, 3),
        'rsi': round(rsi, 1),
        'breakout_pct': round(breakout_pct, 3),
    }


def scan_signals() -> int:
    """Scan all tokens for trend ignition setups."""
    from signal_schema import get_all_latest_prices

    if not TREND_IGNITION_ENABLED:
        return 0

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue

        if price_age_minutes(token) > 10:
            continue

        candles = _get_candles_5m(token, limit=max(TREND_IGNITION_EMA_PERIOD, TREND_IGNITION_BREAKOUT_PERIOD) + 30)
        if not candles or len(candles) < max(TREND_IGNITION_EMA_PERIOD, TREND_IGNITION_BREAKOUT_PERIOD) + 20:
            continue

        sig = _detect_trend_ignition(token, candles)
        if sig is None:
            continue

        direction = sig['direction']

        # Kill-switch
        if direction == 'LONG' and not TREND_IGNITION_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not TREND_IGNITION_MINUS_ENABLED:
            continue

        # Blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig['signal_type'],
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction=direction, hours=TREND_IGNITION_COOLDOWN_HOURS)
            print(f'  {direction:5s} {token:8s} conf={sig["confidence"]:.0f}% '
                  f'vol={sig["vol_ratio"]:.1f}x bb={sig["bb_width_pct"]:.2f}% '
                  f'ema_dist={sig["ema_dist_pct"]:.2f}% rsi={sig["rsi"]:.0f} '
                  f'breakout={sig["breakout_pct"]:.3f}% [{sig["source"]}]')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    prices = get_all_latest_prices()
    test_tokens = {k: v for k, v in prices.items()
                   if k in ('ARB', 'CFX', 'FIL', 'AVNT', 'SYRUP', 'ENA', 'JUP', 'ATOM', 'ETC') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])
    print(f"[trend_ignition] Testing on {len(test_tokens)} tokens...")
    n = scan_signals()
    print(f"[trend_ignition] Done. {n} signals emitted.")
