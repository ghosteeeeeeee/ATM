#!/usr/bin/env python3
"""
Range Breakout — breakout signal from tight ranges with retest confirmation.

Complement to range_finder: same range detection, opposite trade direction.
range_finder fires at range edges (mean reversion). This fires when price
EXITS the range (breakout) and confirms with a bounce back to the breakout level.

LOGIC:
  1. Detect range: BB width < threshold + slope near zero + band touches
  2. Breakout: recent close above upper band (LONG) or below lower band (SHORT)
  3. Retest: current price pulled back near the band (within 0.3%)
  4. Bounce: current close > prev close (LONG) or < prev close (SHORT)
  5. Invalidation: close back inside range after breakout = failed breakout, skip

FAKEOUT PROTECTION:
  - Volume not reliable (candles_5m has 0 volume for 97% of rows), skipped
  - Retest + bounce confirms the breakout level holds as new support/resistance
  - Invalidation kills the setup if price reverses back into range
"""

import sys
import os
import time
import sqlite3
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    RANGE_BREAKOUT_ENABLED, RANGE_BREAKOUT_PLUS_ENABLED, RANGE_BREAKOUT_MINUS_ENABLED,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

# ── Parameters (all from hermes_constants, read at call time) ────────────────
_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[range-breakout] {msg}", flush=True)


def _compute_bb(closes, period, stddev):
    """Bollinger Bands: middle (SMA), upper, lower, width %, slope."""
    if len(closes) < period:
        return None, None, None, None, None
    middle = float(np.mean(closes[-period:]))
    std = float(np.std(closes[-period:]))
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    if len(closes) >= period + 10:
        prev_middle = float(np.mean(closes[-(period + 10):-10]))
        slope = (middle - prev_middle) / prev_middle if prev_middle > 0 else 0
    else:
        slope = 0
    return middle, upper, lower, width, slope


def _compute_rsi(closes, period=14):
    """RSI calculation."""
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _count_band_touches(closes, upper, lower, window):
    """Count band touches in recent window. Touch = within 1.0% of band."""
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
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
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
            k = 2.0 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1.0 - k)
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
    """Fetch 1m closes from price_history and resample to 5m."""
    conn = None
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
        if not rows:
            return []

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 600:
            return []

        closes_1m = [r[1] for r in rows]
        closes_5m = closes_1m[4::5]
        return closes_5m
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def detect_breakout(closes, token):
    """Detect range breakout with retest confirmation.

    Args:
        closes: list of float (5m close prices, oldest first)
        token: str (for trend lookup)

    Returns:
        dict {direction, confidence, range_width, rsi, retest_bounce_pct} or None
    """
    from hermes_constants import (
        RANGE_BREAKOUT_LOOKBACK, RANGE_BREAKOUT_BB_PERIOD, RANGE_BREAKOUT_BB_STDDEV,
        RANGE_BREAKOUT_BB_WIDTH_MAX, RANGE_BREAKOUT_BB_SLOPE_MAX,
        RANGE_BREAKOUT_TOUCH_MIN, RANGE_BREAKOUT_TOUCH_WINDOW,
        RANGE_BREAKOUT_RETEST_PCT, RANGE_BREAKOUT_BOUNCE_MIN,
        RANGE_BREAKOUT_BREAKOUT_WINDOW, RANGE_BREAKOUT_INVALIDATION_WINDOW,
        RANGE_BREAKOUT_CONF_BASE, RANGE_BREAKOUT_CONF_CAP,
        RANGE_BREAKOUT_RSI_LONG_MAX, RANGE_BREAKOUT_RSI_SHORT_MIN,
    )

    if not closes or len(closes) < RANGE_BREAKOUT_LOOKBACK:
        return None

    arr = np.array(closes, dtype=np.float64)

    # ── Phase 1: Was there a range? ──────────────────────────────────────
    middle, upper, lower, width, slope = _compute_bb(
        arr, RANGE_BREAKOUT_BB_PERIOD, RANGE_BREAKOUT_BB_STDDEV
    )
    if middle is None:
        return None

    # Check if recent history was range-bound
    range_confirmed = False
    squeeze_bars = 0
    check_window = min(50, len(closes) - RANGE_BREAKOUT_BB_PERIOD)
    for i in range(check_window):
        idx = len(closes) - check_window + i
        if idx < RANGE_BREAKOUT_BB_PERIOD:
            continue
        m, u, l, w, s = _compute_bb(arr[:idx + 1], RANGE_BREAKOUT_BB_PERIOD, RANGE_BREAKOUT_BB_STDDEV)
        if m is not None and w < RANGE_BREAKOUT_BB_WIDTH_MAX and abs(s) < RANGE_BREAKOUT_BB_SLOPE_MAX:
            squeeze_bars += 1
            range_confirmed = True
        else:
            squeeze_bars = 0  # reset on non-squeeze bar

    if not range_confirmed:
        return None

    # Count band touches on current BB
    upper_touches, lower_touches = _count_band_touches(
        closes, upper, lower, RANGE_BREAKOUT_TOUCH_WINDOW
    )
    total_touches = upper_touches + lower_touches
    if total_touches < RANGE_BREAKOUT_TOUCH_MIN:
        return None

    # ── Phase 2: Did a breakout happen recently? ─────────────────────────
    direction = None
    breakout_idx = None
    bw = RANGE_BREAKOUT_BREAKOUT_WINDOW

    for i in range(1, bw + 1):
        idx = len(closes) - i
        if idx < 0:
            break
        # Recompute BB at breakout bar (bands shift as price moves)
        m, u, l, w, s = _compute_bb(arr[:idx + 1], RANGE_BREAKOUT_BB_PERIOD, RANGE_BREAKOUT_BB_STDDEV)
        if m is None:
            continue
        if closes[idx] > u:
            direction = 'LONG'
            breakout_idx = idx
            breakout_upper = u
            breakout_lower = l
            breakout_middle = m
            break
        elif closes[idx] < l:
            direction = 'SHORT'
            breakout_idx = idx
            breakout_upper = u
            breakout_lower = l
            breakout_middle = m
            break

    if direction is None:
        return None

    # ── Phase 3: Invalidation — close back inside range after breakout? ───
    inv_window = RANGE_BREAKOUT_INVALIDATION_WINDOW
    for i in range(1, inv_window + 1):
        idx = len(closes) - i
        if idx <= breakout_idx:
            break
        # Recompute BB at invalidation bar
        m, u, l, w, s = _compute_bb(arr[:idx + 1], RANGE_BREAKOUT_BB_PERIOD, RANGE_BREAKOUT_BB_STDDEV)
        if m is None:
            continue
        if direction == 'LONG' and closes[idx] < u:
            return None  # failed breakout — closed back below upper band
        if direction == 'SHORT' and closes[idx] > l:
            return None  # failed breakout — closed back above lower band

    # ── Phase 4: Retest + bounce NOW ─────────────────────────────────────
    current_close = closes[-1]
    prev_close = closes[-2] if len(closes) >= 2 else current_close
    rsi = _compute_rsi(closes)

    # Use the bands at the breakout bar for retest reference
    if direction == 'LONG':
        retest_level = breakout_upper
        retest_pct = RANGE_BREAKOUT_RETEST_PCT / 100.0
        # Current close must be near the breakout level (retest) and bouncing
        if abs(current_close - retest_level) / retest_level > retest_pct:
            return None
        if current_close <= prev_close:
            return None  # not bouncing
        bounce_pct = (current_close - breakout_upper) / breakout_upper * 100
    else:
        retest_level = breakout_lower
        retest_pct = RANGE_BREAKOUT_RETEST_PCT / 100.0
        if abs(current_close - retest_level) / retest_level > retest_pct:
            return None
        if current_close >= prev_close:
            return None  # not bouncing
        bounce_pct = (breakout_lower - current_close) / breakout_lower * 100

    if bounce_pct < RANGE_BREAKOUT_BOUNCE_MIN:
        return None

    # ── Phase 5: RSI sanity ──────────────────────────────────────────────
    if rsi is not None:
        if direction == 'LONG' and rsi > RANGE_BREAKOUT_RSI_LONG_MAX:
            return None
        if direction == 'SHORT' and rsi < RANGE_BREAKOUT_RSI_SHORT_MIN:
            return None

    # ── Confidence scoring ───────────────────────────────────────────────
    conf = RANGE_BREAKOUT_CONF_BASE
    squeeze_bonus = min(15, squeeze_bars)
    bounce_bonus = min(10, bounce_pct * 20)
    conf += squeeze_bonus + bounce_bonus

    # 1H trend bonus
    trend = _get_1h_trend(token)
    trend_bonus = 0
    if (direction == 'LONG' and trend == 'BULLISH') or \
       (direction == 'SHORT' and trend == 'BEARISH'):
        trend_bonus = 5
    conf += trend_bonus

    # ── Dynamic bonuses (like accel_300) ──────────────────────────────────
    # Strong bounce: bounce_pct > 0.15% = confirmed breakout
    if bounce_pct > 0.15:
        conf = min(88, conf + 3)
    # Deep squeeze: squeeze_bars > 10 = long consolidation = stronger breakout
    if squeeze_bars > 10:
        conf = min(88, conf + 3)
    # Wide range: range_width > 0.5% = established range, not noise
    if width * 100 > 0.5:
        conf = min(88, conf + 3)
    # Speed bonus: high velocity = breakout has momentum
    try:
        from speed_tracker import get_token_speed
        spd = get_token_speed(token)
        vel = spd.get('speed_percentile', 0) if spd else 0
        if vel >= 80:
            conf = min(88, conf + 5)
    except Exception:
        pass

    conf = min(RANGE_BREAKOUT_CONF_CAP, max(50, conf))

    return {
        'direction': direction,
        'confidence': conf,
        'range_width': round(width * 100, 2),
        'rsi': round(rsi, 1) if rsi is not None else None,
        'squeeze_bars': squeeze_bars,
        'bounce_pct': round(bounce_pct, 3),
        'trend': trend,
        'upper': round(upper, 8),
        'lower': round(lower, 8),
        'middle': round(middle, 8),
    }


def scan_signals() -> int:
    """Scan all tokens for range breakout signals."""
    from signal_schema import get_all_latest_prices

    added = 0
    now = time.time()

    for token, data in get_all_latest_prices().items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        token_upper = token.upper()

        # Price freshness
        if price_age_minutes(token) > 10:
            continue

        # Cooldown
        if get_cooldown(token, direction='LONG') or get_cooldown(token, direction='SHORT'):
            continue

        closes = _get_candles_5m(token, lookback=2500)
        if not closes or len(closes) < 100:
            continue

        sig = detect_breakout(closes, token)
        if sig is None:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not RANGE_BREAKOUT_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not RANGE_BREAKOUT_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        # Regime filter: block counter-trend breakouts
        trend = sig.get('trend', 'NEUTRAL')
        if direction == 'SHORT' and trend == 'BULLISH':
            continue
        if direction == 'LONG' and trend == 'BEARISH':
            continue

        # Spike exhaustion filter: block entries after sharp 5m moves
        try:
            from hermes_constants import SPIKE_EXHAUSTION_VEL_5M_THRESHOLD
            from paths import HERMES_DATA
            import sqlite3 as _sqlite3
            _conn = _sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes.db'), timeout=10)
            _cur = _conn.cursor()
            _cur.execute("""
                SELECT price FROM (
                    SELECT price, timestamp FROM price_history
                    WHERE token = ?
                    ORDER BY timestamp DESC LIMIT 6
                ) sub ORDER BY timestamp ASC
            """, (token_upper,))
            _prices = [r[0] for r in _cur.fetchall()]
            _conn.close()
            if len(_prices) >= 2 and _prices[0] > 0:
                _vel_5m = (_prices[-1] - _prices[0]) / _prices[0] * 100
                if abs(_vel_5m) > SPIKE_EXHAUSTION_VEL_5M_THRESHOLD:
                    continue  # spike exhaustion — skip
        except Exception:
            pass

        source = f'range_breakout{"+" if direction == "LONG" else "-"}'

        sid = add_signal(
            token=token_upper,
            direction=direction,
            signal_type='range_breakout',
            source=source,
            confidence=sig['confidence'],
            value=sig['range_width'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
            z_score=None,
        )
        if sid:
            added += 1
            from hermes_constants import RANGE_BREAKOUT_COOLDOWN_HOURS
            set_cooldown(token, direction=direction, hours=RANGE_BREAKOUT_COOLDOWN_HOURS)
            _log(f'{direction:5s} {token:8s} conf={sig["confidence"]:3.0f}% '
                 f'range={sig["range_width"]:.2f}% squeeze={sig["squeeze_bars"]} '
                 f'bounce={sig["bounce_pct"]:.3f}% trend={sig["trend"]}')

    return added


def run():
    """Entry point for signals_runner. Zero-arg: reads from DB directly."""
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_signals()
    print(f"[range-breakout] Done. {n} signals emitted.")
