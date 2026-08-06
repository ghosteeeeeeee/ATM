#!/usr/bin/env python3
"""
Range Finder — mean-reversion signal for range-bound markets.

Fires LONG at range support, SHORT at range resistance.
Targets the opposite boundary (1-2% per trade).

LOGIC:
  1. Detect range: Bollinger Band width < threshold + slope near zero
  2. Define boundaries: upper/lower BB as resistance/support
  3. Entry: price near lower band + RSI oversold → LONG
            price near upper band + RSI overbought → SHORT
  4. Confirmation: price must be moving away from band (bounce)
  5. Filter: require 3+ touches of the band to confirm range is real

UNLIKE bb_bounce:
  - No 1H EMA trend filter (ranges have no trend)
  - Requires range confirmation (flat bands, multiple touches)
  - Tighter entry criteria (must be near band AND bouncing)
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal

# ── Parameters ───────────────────────────────────────────────────────────────
BB_PERIOD = 20               # Bollinger Band period
BB_STDDEV = 1.8              # Band width (1.8σ for more touches)
BB_WIDTH_MAX = 0.04          # Max band width % to consider range-bound (4%)
BB_SLOPE_MAX = 0.001         # Max BB middle slope per candle (flat bands)
LOOKBACK = 100               # 5m candles to analyze (8+ hours)
RSI_PERIOD = 14
RSI_OVERSOLD = 40            # RSI below this = oversold at support
RSI_OVERBOUGHT = 60          # RSI above this = overbought at resistance
TOUCH_MIN = 3                # Minimum band touches to confirm range
TOUCH_WINDOW = 50            # Lookback for counting touches
PROXIMITY_PCT = 0.50         # Price must be within 0.50% of band to trigger
BOUNCE_MIN_PCT = 0.05        # Minimum bounce away from band (0.05%)
COOLDOWN_CANDLES = 6         # 30 min cooldown on 5m candles


# ── State ───────────────────────────────────────────────────────────────
_cooldown = {}  # token -> timestamp of last signal


def _log(msg):
    print(f"[range-finder] {msg}", flush=True)


def _compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    """Bollinger Bands: middle (SMA), upper, lower, width %."""
    if len(closes) < period:
        return None, None, None, None, None
    middle = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    # Slope of middle band over last 10 candles
    if len(closes) >= period + 10:
        prev_middle = np.mean(closes[-(period + 10):-10])
        slope = (middle - prev_middle) / prev_middle if prev_middle > 0 else 0
    else:
        slope = 0
    return middle, upper, lower, width, slope


def _compute_rsi(closes, period=RSI_PERIOD):
    """RSI calculation."""
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _count_band_touches(closes, upper, lower, window=TOUCH_WINDOW):
    """Count how many times price touched upper/lower band in recent window.

    Touch = price within 1.0% of band. In a tight range, prices oscillate
    between bands without touching them exactly. 1.0% captures "near the band"
    which is what matters for range trading.
    """
    recent = closes[-window:] if len(closes) >= window else closes
    upper_touches = 0
    lower_touches = 0
    for c in recent:
        if abs(c - upper) / upper < 0.01:
            upper_touches += 1
        if abs(c - lower) / lower < 0.01:
            lower_touches += 1
    return upper_touches, lower_touches


def detect_range_signal(closes):
    """Detect range-bound signal on 5m data.

    Args:
        closes: list of float (5m close prices, oldest first)

    Returns:
        dict with {direction, confidence, range_width, rsi, touch_count} or None
    """
    if not closes or len(closes) < LOOKBACK:
        return None

    arr = np.array(closes, dtype=np.float64)

    # Compute Bollinger Bands
    middle, upper, lower, width, slope = _compute_bb(arr)
    if middle is None:
        return None

    # Range detection: narrow bands + flat slope
    if width > BB_WIDTH_MAX:
        return None  # bands too wide — trending market
    if abs(slope) > BB_SLOPE_MAX:
        return None  # bands sloping — trending market

    # Count band touches to confirm range is real
    upper_touches, lower_touches = _count_band_touches(arr, upper, lower)
    total_touches = upper_touches + lower_touches
    if total_touches < TOUCH_MIN:
        return None  # not enough touches — range not confirmed

    current = arr[-1]
    prev = arr[-2] if len(arr) >= 2 else current

    # RSI
    rsi = _compute_rsi(arr)
    if rsi is None:
        return None

    # Distance from bands
    dist_lower = abs(current - lower) / lower * 100 if lower > 0 else 999
    dist_upper = abs(current - upper) / upper * 100 if upper > 0 else 999

    # LONG: near lower band + RSI oversold + 2-candle bounce confirmation
    if dist_lower <= PROXIMITY_PCT and current > prev:
        if rsi > RSI_OVERSOLD:
            return None
        if current <= lower:
            return None  # still below band, no bounce yet
        # 2-candle confirmation: both of last 2 candles must be above band
        if len(arr) >= 3 and arr[-2] <= lower:
            return None  # previous candle was still below band — not a real bounce
        bounce_pct = (current - lower) / lower * 100 if lower > 0 else 0
        if bounce_pct < BOUNCE_MIN_PCT:
            return None

        # Confidence: more touches + wider range = higher confidence
        touch_bonus = min(20, total_touches * 3)
        range_bonus = int(width / BB_WIDTH_MAX * 15)  # wider range = more profit potential
        conf = min(80, 55 + touch_bonus + range_bonus)

        return {
            'direction': 'LONG',
            'confidence': conf,
            'range_width': round(width * 100, 2),
            'rsi': round(rsi, 1),
            'touch_count': total_touches,
            'upper': round(upper, 8),
            'lower': round(lower, 8),
            'middle': round(middle, 8),
            'bounce_pct': round(bounce_pct, 3),
        }

    # SHORT: near upper band + RSI overbought + 2-candle rejection
    if dist_upper <= PROXIMITY_PCT and current < prev:
        if rsi < RSI_OVERBOUGHT:
            return None
        if current >= upper:
            return None  # still above band, no rejection yet
        # 2-candle confirmation: both of last 2 candles must be below band
        if len(arr) >= 3 and arr[-2] >= upper:
            return None  # previous candle was still above band — not a real rejection
        bounce_pct = (upper - current) / upper * 100 if upper > 0 else 0
        if bounce_pct < BOUNCE_MIN_PCT:
            return None

        touch_bonus = min(20, total_touches * 3)
        range_bonus = int(width / BB_WIDTH_MAX * 15)
        conf = min(80, 55 + touch_bonus + range_bonus)

        return {
            'direction': 'SHORT',
            'confidence': conf,
            'range_width': round(width * 100, 2),
            'rsi': round(rsi, 1),
            'touch_count': total_touches,
            'upper': round(upper, 8),
            'lower': round(lower, 8),
            'middle': round(middle, 8),
            'bounce_pct': round(bounce_pct, 3),
        }

    return None


# ── Scanner ──────────────────────────────────────────────────────────────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'


def _get_candles_5m(token: str, lookback: int = 2500) -> list:
    """Fetch 1m closes and resample to 5m."""
    import sqlite3
    import time

    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []

        closes_1m = [r[1] for r in rows]
        # Resample to 5m: close of each 5-bar window
        closes_5m = closes_1m[4::5]
        return closes_5m
    except Exception as e:
        _log(f"error fetching candles for {token}: {e}")
        return []


def scan_range_signals(prices_dict: dict) -> tuple:
    """Scan tokens for range-finder signals."""
    from hermes_constants import (
        RANGE_FINDER_PLUS_ENABLED, RANGE_FINDER_MINUS_ENABLED,
        LONG_BLACKLIST, SHORT_BLACKLIST,
    )

    added = 0
    signaled_tokens = []
    now = time.time()

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Cooldown: don't re-fire for COOLDOWN_CANDLES * 5 minutes per token
        key = token.upper()
        if key in _cooldown and (now - _cooldown[key]) < COOLDOWN_CANDLES * 5 * 60:
            continue

        closes = _get_candles_5m(token, lookback=2500)
        if not closes or len(closes) < LOOKBACK:
            continue

        sig = detect_range_signal(closes)
        if sig is None:
            continue

        if sig['direction'] == 'LONG' and not RANGE_FINDER_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not RANGE_FINDER_MINUS_ENABLED:
            continue

        token_upper = token.upper()
        if sig['direction'] == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if sig['direction'] == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        sid = add_signal(
            token=token_upper,
            direction=sig['direction'],
            signal_type='range_finder',
            source='range_finder',
            confidence=sig['confidence'],
            value=sig['range_width'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            signaled_tokens.append(token_upper)
            _cooldown[key] = now
            _log(f'{sig["direction"]:5s} {token:8s} conf={sig["confidence"]:3.0f}% '
                 f'range={sig["range_width"]:.2f}% touches={sig["touch_count"]} '
                 f'rsi={sig["rsi"]:.1f} bounce={sig["bounce_pct"]:.3f}%')

    return added, signaled_tokens


def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_range_signals(prices_dict)


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    prices = get_all_latest_prices()
    test = {k: v for k, v in prices.items() if k in ('LINK', 'UMA', 'BTC', 'ETH', 'SOL') and v.get('price')}
    if not test:
        test = dict(list(prices.items())[:10])
    print(f"[range-finder] Testing on {len(test)} tokens...")
    n, tokens = scan_range_signals(test)
    print(f"[range-finder] Done. {n} signals emitted.")
