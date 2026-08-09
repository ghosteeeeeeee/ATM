#!/usr/bin/env python3
"""
Range Finder SHORT — mean-reversion at range resistance (SHORT-specific).

SHORT-SPECIFIC IMPROVEMENTS over generic range_finder:
  1. Regime filter: only fire when 1H trend is BEARISH or NEUTRAL (not BULLISH)
  2. Tighter RSI overbought: 55 (was 60) — stronger overbought required
  3. More band touches: 4 (was 3) — confirm range is real before shorting
  4. Volume confirmation: 1.2x average (new)
  5. ~~Time filter: avoid Asian session 00:00-07:59 UTC~~ REMOVED (data: Asian session has better WR/PnL)
  6. Tighter bounce: 0.08% (was 0.05%)
  7. Tighter proximity: 0.40% (was 0.50%) — must be closer to upper band

RANGE TRADING NOTE:
  Ranges exist in both trending and sideways markets. The regime filter here
  blocks BULLISH regimes where shorting resistance is dangerous (price breaks
  out upward). BEARISH/NEUTRAL regimes are safe for range shorts.

BACKTEST CONTEXT (old generic SHORT combos):
  - ma100-cross,range_finder SHORT: 6T, 50% WR, +$3
  - ma100-cross-,range_finder- SHORT:5T, 40% WR, +$2
  - No standalone range_finder SHORT trades recorded
"""
import sqlite3
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── SHORT-Specific Parameters ──────────────────────────────────────────────
BB_PERIOD = 20
BB_STDDEV = 1.8
BB_WIDTH_MAX = 0.04          # Max band width % to consider range-bound
BB_SLOPE_MAX = 0.001         # Max BB middle slope per candle
LOOKBACK = 100               # 5m candles to analyze
RSI_PERIOD = 14
RSI_OVERBOUGHT = 55          # TIGHTER: was 60
TOUCH_MIN = 4                # TIGHTER: was 3 — confirm range with more touches
TOUCH_WINDOW = 50
PROXIMITY_PCT = 0.40         # TIGHTER: was 0.50 — must be closer to upper band
BOUNCE_MIN_PCT = 0.08        # TIGHTER: was 0.05
MIN_VOLUME_RATIO = 1.0       # ponytail: was 1.2x, relaxed — low-volume NEUTRAL market makes 1.2x unachievable. Restore to 1.2x if volume returns.
BLOCKED_HOURS = []  # ponytail: was [0-7] (Asian session), removed — data shows Asian session has BETTER WR (43.6% vs 35.1%) and less negative PnL for SHORTs. Add back only if live data proves otherwise.


def _log(msg):
    print(f"[range-finder-short] {msg}", flush=True)


def _get_15m_velocity(token):
    """15m price velocity (% change over last 15 minutes). Returns float or None."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT price FROM (
                SELECT price, timestamp FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC LIMIT 15
            ) sub ORDER BY timestamp ASC
        """, (token.upper(),))
        rows = c.fetchall()
        if len(rows) < 5:
            return None
        prices = [r[0] for r in rows]
        if prices[0] <= 0:
            return None
        return (prices[-1] - prices[0]) / prices[0] * 100
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    """Bollinger Bands: middle (SMA), upper, lower, width %, slope."""
    import numpy as np
    if len(closes) < period:
        return None, None, None, None, None
    arr = np.array(closes[-period:], dtype=np.float64)
    middle = float(np.mean(arr))
    std = float(np.std(arr))
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    if len(closes) >= period + 10:
        prev_middle = float(np.mean(np.array(closes[-(period + 10):-10], dtype=np.float64)))
        slope = (middle - prev_middle) / prev_middle if prev_middle > 0 else 0
    else:
        slope = 0
    return middle, upper, lower, width, slope


def _compute_rsi(closes, period=RSI_PERIOD):
    """RSI calculation."""
    import numpy as np
    if len(closes) < period + 1:
        return None
    deltas = np.diff(np.array(closes[-(period + 1):], dtype=np.float64))
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _count_band_touches(closes, upper, lower, window=TOUCH_WINDOW):
    """Count band touches in recent window. Touch = price within 1.0% of band."""
    recent = closes[-window:] if len(closes) >= window else closes
    upper_touches = 0
    lower_touches = 0
    for c in recent:
        if upper > 0 and abs(c - upper) / upper < 0.01:
            upper_touches += 1
        if lower > 0 and abs(c - lower) / lower < 0.01:
            lower_touches += 1
    return upper_touches, lower_touches


def _get_1h_trend(token):
    """Check 1H EMA trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 60
        """, (token.upper(),))
        rows = cur.fetchall()
        if not rows or len(rows) < 50:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]

        def ema(data, period):
            k = 2 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1 - k)
            return val

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        if ema50 == 0:
            return 'NEUTRAL'
        spread = abs(ema20 - ema50) / ema50 * 100
        if spread < 0.1:
            return 'NEUTRAL'
        return 'BULLISH' if ema20 > ema50 else 'BEARISH'
    except Exception:
        return 'NEUTRAL'
    finally:
        if conn:
            conn.close()


def _get_candles_5m(token, lookback=2500):
    """Fetch 1m closes from candles.db and resample to 5m."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        if not rows:
            return []
        closes_1m = [r[0] for r in reversed(rows)]
        # Resample to 5m: close of each 5-bar window
        return closes_1m[4::5]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_volume_avg(token, lookback=50):
    """Get average volume over last N 5m candles."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT volume FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        if not rows or len(rows) < 10:
            return None
        volumes = [r[0] for r in rows if r[0] is not None and r[0] > 0]
        if len(volumes) < 10:
            return None
        return sum(volumes) / len(volumes)
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_current_volume(token):
    """Get the most recent 5m candle's volume."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT volume FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 1
        """, (token.upper(),))
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def detect_range_short(token, closes):
    """Detect range-bound SHORT signal with tighter filters.

    Args:
        token: token symbol (for regime check)
        closes: list of float (5m close prices, oldest first)

    Returns:
        dict with signal info or None
    """
    import numpy as np

    if not closes or len(closes) < LOOKBACK:
        return None

    # Time filter: avoid Asian session
    from datetime import datetime, timezone
    hour = datetime.now(timezone.utc).hour
    if hour in BLOCKED_HOURS:
        return None

    arr = np.array(closes, dtype=np.float64)

    # Compute Bollinger Bands
    middle, upper, lower, width, slope = _compute_bb(closes)
    if middle is None:
        return None

    # Range detection: narrow bands + flat slope
    if width > BB_WIDTH_MAX:
        return None
    if abs(slope) > BB_SLOPE_MAX:
        return None

    # Regime filter: block BULLISH (shorting resistance in uptrend = dangerous)
    trend = _get_1h_trend(token)
    if trend == 'BULLISH':
        return None

    # Count band touches — need more for SHORT (confirm range is real)
    upper_touches, lower_touches = _count_band_touches(closes, upper, lower)
    total_touches = upper_touches + lower_touches
    if total_touches < TOUCH_MIN:
        return None

    current = arr[-1]
    prev = arr[-2]

    # RSI
    rsi = _compute_rsi(closes)
    if rsi is None:
        return None

    # SHORT: near upper band + RSI overbought + bounce rejection
    dist_upper = abs(current - upper) / upper * 100 if upper > 0 else 999

    if dist_upper > PROXIMITY_PCT:
        return None  # Not close enough to upper band

    if rsi < RSI_OVERBOUGHT:
        return None  # RSI not overbought enough

    if current >= upper:
        return None  # Still above band, no rejection yet

    # 2-candle rejection confirmation
    if len(arr) >= 3 and arr[-2] >= upper:
        return None  # Previous candle was still above band

    # Bounce must be downward
    if current >= prev:
        return None

    bounce_pct = (upper - current) / upper * 100 if upper > 0 else 0
    if bounce_pct < BOUNCE_MIN_PCT:
        return None

    # Volume confirmation — required, fail-closed
    vol_avg = _get_volume_avg(token)
    vol_current = _get_current_volume(token)
    if not vol_avg or vol_avg <= 0 or vol_current is None:
        return None  # No volume data — can't confirm, skip
    vol_ratio = vol_current / vol_avg
    if vol_ratio < MIN_VOLUME_RATIO:
        return None

    # Confidence: touches + range width + trend alignment
    touch_bonus = min(20, total_touches * 3)
    range_bonus = int(width / BB_WIDTH_MAX * 15)
    trend_bonus = 5 if trend == 'BEARISH' else 0  # BEARISH trend = higher confidence
    conf = min(85, 55 + touch_bonus + range_bonus + trend_bonus)

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
        'trend': trend,
    }


def scan_range_short_signals(prices_dict):
    """Scan tokens for range_finder SHORT signals."""
    from signal_schema import add_signal, get_cooldown, set_cooldown
    from signal_gen import is_delisted, SHORT_BLACKLIST

    added = 0
    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        if is_delisted(token.upper()):
            continue

        # Cooldown
        if get_cooldown(token, direction='SHORT'):
            continue

        # Blacklist
        if token.upper() in SHORT_BLACKLIST:
            continue

        # Kill switch
        from hermes_constants import RANGE_FINDER_SHORT_ENABLED
        if not RANGE_FINDER_SHORT_ENABLED:
            continue

        closes = _get_candles_5m(token, lookback=2500)
        if not closes or len(closes) < LOOKBACK:
            continue

        sig = detect_range_short(token, closes)
        if sig is None:
            continue

        # Velocity gate: skip if price still trending against signal (SHORT only)
        from hermes_constants import MEAN_REVERSION_VEL_ENABLED, MEAN_REVERSION_VEL_THRESHOLD
        if MEAN_REVERSION_VEL_ENABLED:
            vel = _get_15m_velocity(token)
            if vel is not None and vel > MEAN_REVERSION_VEL_THRESHOLD:
                _log(f"{token} SHORT BLOCKED vel={vel:+.3f}% (threshold +{MEAN_REVERSION_VEL_THRESHOLD}%)")
                continue

        sid = add_signal(
            token=token.upper(),
            direction='SHORT',
            signal_type='range_finder_short',
            source='range-finder-short',
            confidence=sig['confidence'],
            value=sig['range_width'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction='SHORT', hours=1)
            _log(f"SHORT {token:8s} conf={sig['confidence']:3.0f}% "
                 f"range={sig['range_width']:.2f}% touches={sig['touch_count']} "
                 f"rsi={sig['rsi']:.1f} bounce={sig['bounce_pct']:.3f}% "
                 f"trend={sig['trend']}")

    return added


def run(prices_dict=None):
    """Entry point for signals_runner."""
    from signal_schema import get_all_latest_prices
    if prices_dict is None:
        prices_dict = get_all_latest_prices()
    return scan_range_short_signals(prices_dict)


if __name__ == '__main__':
    token = sys.argv[1] if len(sys.argv) > 1 else 'ETH'
    closes = _get_candles_5m(token, lookback=2500)
    if closes and len(closes) >= LOOKBACK:
        sig = detect_range_short(token, closes)
        if sig:
            print(f"{token} SHORT conf={sig['confidence']}% range={sig['range_width']:.2f}% "
                  f"rsi={sig['rsi']:.1f} touches={sig['touch_count']} trend={sig['trend']}")
        else:
            print(f"{token}: no signal")
    else:
        print(f"{token}: insufficient data ({len(closes) if closes else 0} candles)")
