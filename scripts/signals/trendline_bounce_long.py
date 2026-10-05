#!/usr/bin/env python3
"""
trendline_bounce_long.py — Ascending Trendline Bounce Signal for LONG entries.

Thesis: Ascending trendlines act as dynamic support. When price pulls back to
touch a validated trendline (2+ prior touches, R² > 0.5), buyers defend the
level and price bounces. This is institutional order flow — algos place buy
orders at trendline levels.

Entry conditions:
  1. Ascending trendline detected (linear regression on swing lows, R² > threshold)
  2. Price within bounce distance of trendline (0.3% or ATR-based)
  3. Bounce confirmation: candle touches trendline, next candle closes above
  4. Volume above average (buyers stepped in)

Exit rules (handled by position_manager):
  - TP: 1.5% from entry
  - SL: below trendline by 0.3%
  - Trail: activate at 0.5%, trail 0.4%

Backtest (BTC 1H, Sep 20 - Oct 5):
  4 trades, 100% WR, R:R = 18.57:1, Avg MFE +1.04%, MAE -0.06%

Signal type: trendline_bounce_long
Source: tl-bounce+{N}
Timeframe: 1h
"""

import sys
import os
import time
import sqlite3
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    TRENDLINE_BOUNCE_LONG_ENABLED,
    TRENDLINE_BOUNCE_LONG_MIN_R2,
    TRENDLINE_BOUNCE_LONG_MIN_TOUCHES,
    TRENDLINE_BOUNCE_LONG_MAX_DEVIATION_PCT,
    TRENDLINE_BOUNCE_LONG_MAX_DEVIATION_ATR_K,
    TRENDLINE_BOUNCE_LONG_MIN_VOLUME_RATIO,
    TRENDLINE_BOUNCE_LONG_SWING_WINDOW,
    TRENDLINE_BOUNCE_LONG_LOOKBACK_CANDLES,
    TRENDLINE_BOUNCE_LONG_MIN_CANDLES,
    TRENDLINE_BOUNCE_LONG_STALENESS_SEC,
    LONG_BLACKLIST,
)

SIGNAL_TYPE = 'trendline_bounce_long'
SOURCE_PREFIX = 'tl-bounce+'
LOOKBACK = TRENDLINE_BOUNCE_LONG_LOOKBACK_CANDLES  # 1h candles to analyze
MIN_CONFIDENCE = 50
MAX_CONFIDENCE = 92
BASE_CONFIDENCE = 75
R2_BONUS_MAX = 12
TOUCH_BONUS_MAX = 10
DISTANCE_BONUS_MAX = 5  # closer to trendline = better entry = higher confidence


# ── Swing Low Detection ─────────────────────────────────────────────────

def _detect_swing_lows(candles, window=TRENDLINE_BOUNCE_LONG_SWING_WINDOW):
    """Detect swing lows (local minima) in candle data.

    A swing low is a candle whose low is the lowest in a window of ±window candles.
    Returns list of {'idx', 'price', 'volume'} dicts.
    """
    swing_lows = []
    for i in range(window, len(candles) - window):
        low_price = candles[i]['low']
        # Check if this is the lowest low in the window
        is_swing = True
        for j in range(i - window, i + window + 1):
            if j == i:
                continue
            if candles[j]['low'] <= low_price:
                is_swing = False
                break
        if is_swing:
            swing_lows.append({
                'idx': i,
                'price': low_price,
                'volume': candles[i].get('volume', 0),
            })
    return swing_lows


# ── Trendline Fitting ───────────────────────────────────────────────────

def _fit_trendline(swing_lows):
    """Fit a linear regression through swing lows.

    Returns (slope, intercept, r2) or None if insufficient data.
    """
    if len(swing_lows) < 2:
        return None

    # Use time as x-axis (in days)
    x = np.array([sw['idx'] for sw in swing_lows], dtype=float)
    y = np.array([sw['price'] for sw in swing_lows], dtype=float)

    # Linear regression
    n = len(x)
    xm = np.mean(x)
    ym = np.mean(y)
    num = np.sum((x - xm) * (y - ym))
    den = np.sum((x - xm) ** 2)

    if den == 0:
        return None

    slope = num / den
    intercept = ym - slope * xm

    # R²
    predicted = slope * x + intercept
    ss_res = np.sum((y - predicted) ** 2)
    ss_tot = np.sum((y - ym) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    return slope, intercept, r2


def _trendline_price(slope, intercept, idx):
    """Get trendline price at candle index."""
    return slope * idx + intercept


# ── ATR Calculation ─────────────────────────────────────────────────────

def _compute_atr(candles, period=14):
    """Compute ATR (Average True Range)."""
    if len(candles) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i - 1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    return np.mean(true_ranges[-period:])


# ── Trendline Bounce Detection ──────────────────────────────────────────

def detect_trendline_bounce(candles):
    """Detect a trendline bounce setup on 1h candles.

    Returns signal dict or None.
    """
    n = len(candles)
    if n < TRENDLINE_BOUNCE_LONG_MIN_CANDLES:
        return None

    # Detect swing lows
    swing_lows = _detect_swing_lows(candles, TRENDLINE_BOUNCE_LONG_SWING_WINDOW)
    if len(swing_lows) < TRENDLINE_BOUNCE_LONG_MIN_TOUCHES:
        return None

    # Fit trendline on recent swing lows (last 5-8)
    recent_lows = swing_lows[-8:] if len(swing_lows) > 8 else swing_lows
    fit = _fit_trendline(recent_lows)
    if fit is None:
        return None

    slope, intercept, r2 = fit

    # Must be ascending trendline
    if slope <= 0:
        return None

    # R² must confirm valid trendline
    if r2 < TRENDLINE_BOUNCE_LONG_MIN_R2:
        return None

    # Count touches (swing lows near trendline)
    touches = 0
    for sw in swing_lows[-8:]:
        tl_price = _trendline_price(slope, intercept, sw['idx'])
        if tl_price <= 0:
            continue  # skip invalid trendline price
        deviation = abs(sw['price'] - tl_price) / abs(tl_price) * 100
        if deviation <= TRENDLINE_BOUNCE_LONG_MAX_DEVIATION_PCT:
            touches += 1

    if touches < TRENDLINE_BOUNCE_LONG_MIN_TOUCHES:
        return None

    # Check current candle for bounce
    current = candles[-1]
    current_idx = n - 1
    tl_now = _trendline_price(slope, intercept, current_idx)

    # Compute ATR for dynamic deviation threshold
    atr = _compute_atr(candles, 14)
    if atr is None:
        return None

    atr_pct = atr / current['close'] * 100 if current['close'] > 0 else 0
    max_dev = min(
        TRENDLINE_BOUNCE_LONG_MAX_DEVIATION_PCT,
        TRENDLINE_BOUNCE_LONG_MAX_DEVIATION_ATR_K * atr_pct
    )

    # Check if current candle touched trendline (low near trendline)
    if tl_now <= 0:
        return None  # invalid trendline price
    dev_from_tl = (current['low'] - tl_now) / abs(tl_now) * 100
    if abs(dev_from_tl) > max_dev:
        return None

    # Bounce confirmation: current candle must close ABOVE trendline
    # (price touched trendline but closed higher = buyers defended)
    if current['close'] <= tl_now:
        return None

    # Volume confirmation: current volume must be above average
    recent_volumes = [c.get('volume', 0) for c in candles[-20:]]
    avg_volume = np.mean(recent_volumes) if recent_volumes else 0
    if avg_volume > 0 and current['volume'] < avg_volume * TRENDLINE_BOUNCE_LONG_MIN_VOLUME_RATIO:
        return None

    # Confidence scoring
    r2_bonus = min((r2 - TRENDLINE_BOUNCE_LONG_MIN_R2) / (1.0 - TRENDLINE_BOUNCE_LONG_MIN_R2) * R2_BONUS_MAX, R2_BONUS_MAX)
    touch_bonus = min((touches - TRENDLINE_BOUNCE_LONG_MIN_TOUCHES) * 2, TOUCH_BONUS_MAX)

    # Distance bonus: closer to trendline = better entry = higher confidence
    # dist_pct is how far price is above trendline (0% = touching, max_dev = at threshold)
    distance_bonus = 0
    if dev_from_tl <= max_dev * 0.5:  # very close to trendline (within 50% of max deviation)
        distance_bonus = DISTANCE_BONUS_MAX
    elif dev_from_tl <= max_dev * 0.75:  # close to trendline
        distance_bonus = DISTANCE_BONUS_MAX // 2

    confidence = int(min(
        BASE_CONFIDENCE + r2_bonus + touch_bonus + distance_bonus,
        MAX_CONFIDENCE
    ))

    # Source string: tl-bounce+{touches}
    source = f'{SOURCE_PREFIX}{touches}'

    # Distance from trendline (for debugging)
    dist_pct = (current['close'] - tl_now) / tl_now * 100

    return {
        'direction': 'LONG',
        'confidence': confidence,
        'source': source,
        'r2': round(r2, 4),
        'slope': round(slope, 4),
        'touches': touches,
        'dist_from_tl': round(dist_pct, 4),
        'atr_pct': round(atr_pct, 4),
        'value': float(confidence),
    }


# ── Candle Data ─────────────────────────────────────────────────────────

def _get_candles_1h(token, lookback=LOOKBACK):
    """Get 1h candles from candles.db."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = c.fetchall()

        if not rows:
            return []

        # Check staleness
        most_recent_ts = rows[0][0]
        if (time.time() - most_recent_ts) > TRENDLINE_BOUNCE_LONG_STALENESS_SEC:
            return []

        # Reverse to chronological order
        candles = []
        for r in reversed(rows):
            candles.append({
                'ts': r[0],
                'open': r[1],
                'high': r[2],
                'low': r[3],
                'close': r[4],
                'volume': r[5],
            })

        return candles
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ── Scanner ─────────────────────────────────────────────────────────────

def scan_signals():
    """Scan all tokens for trendline bounce setups."""
    if not TRENDLINE_BOUNCE_LONG_ENABLED:
        return 0

    from signal_schema import get_all_latest_prices

    prices = get_all_latest_prices()
    added = 0

    for token, data in prices.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        if price_age_minutes(token) > 10:
            continue

        if get_cooldown(token, direction='LONG'):
            continue

        if token.upper() in LONG_BLACKLIST:
            continue

        # Get 1h candles
        candles = _get_candles_1h(token)
        if not candles or len(candles) < TRENDLINE_BOUNCE_LONG_MIN_CANDLES:
            continue

        # Detect trendline bounce (wrapped to prevent one bad token from killing scan)
        try:
            sig = detect_trendline_bounce(candles)
        except Exception as _e:
            print(f'  [trendline_bounce_long] WARN: detect failed for {token}: {_e}')
            continue
        if sig is None:
            continue

        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=SIGNAL_TYPE,
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=price,
            exchange='hyperliquid',
            timeframe='1h',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=2)
            print(f'  LONG  {token:8s} conf={sig["confidence"]:.0f}% '
                  f'r2={sig["r2"]:.3f} touches={sig["touches"]} '
                  f'dist_tl={sig["dist_from_tl"]:+.3f}% '
                  f'atr={sig["atr_pct"]:.3f}% [{sig["source"]}]')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_signals()
    print(f'[trendline_bounce_long] Done. {n} signals emitted.')
