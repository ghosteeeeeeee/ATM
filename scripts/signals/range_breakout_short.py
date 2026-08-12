#!/usr/bin/env python3
"""
Range Breakout SHORT — breakout signal for SHORT entries.

SHORT-SPECIFIC IMPROVEMENTS over generic range_breakout:
  1. Regime filter: only fire when 1H trend is BEARISH or NEUTRAL (not BULLISH)
  2. Tighter RSI threshold: require stronger overbought
  3. Velocity filter: require price rising into SHORT (vel > 0)
  4. Spike exhaustion filter: block after sharp rises
  5. Stronger breakout confirmation

BACKTEST CONTEXT (generic range_breakout SHORT):
  - 12 trades, 9 wins (75% WR), avg PnL +0.373%, total +$0.46
  - Short is the profitable side — this module tunes it further

LOGIC:
  1. Detect range: BB width < threshold + slope near zero + band touches
  2. Breakout: recent close below lower band (SHORT)
  3. Retest: current price pulled back near the band
  4. Bounce: current close < prev close (SHORT)
  5. Invalidation: close back inside range after breakout = failed breakout, skip
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
    RANGE_BREAKOUT_SHORT_ENABLED,
    SHORT_BLACKLIST,
)

# ── SHORT-Specific Parameters ──────────────────────────────────────────────
_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# BB parameters
BB_PERIOD = 30
BB_STDDEV = 1.8
BB_WIDTH_MAX = 0.04        # Max band width % to consider range-bound (4%)
BB_SLOPE_MAX = 0.001       # Max BB middle slope per candle (flat bands)

# Breakout parameters
LOOKBACK = 100             # 5m candles to analyze (8+ hours)
BREAKOUT_WINDOW = 3        # bars to check for breakout
INVALIDATION_WINDOW = 2    # bars to check for invalidation
RETEST_PCT = 0.3           # max % from breakout level for retest
BOUNCE_MIN = 0.05          # min % bounce from breakout level

# Touch parameters
TOUCH_MIN = 3              # min band touches in window
TOUCH_WINDOW = 30          # bars to count touches

# RSI parameters
RSI_PERIOD = 14
RSI_SHORT_MIN = 0           # SHORT: no RSI filter (breakout can happen at any RSI level, velocity filter is sufficient)

# Velocity parameters
VEL_5M_MAX = 0.1           # SHORT: block if vel > 0.1% (selling into rally = bad)

# Cooldown
COOLDOWN_HOURS = 0.25      # 15 min between signals per token+direction

# Confidence
CONF_BASE = 65
CONF_CAP = 88


def _log(msg):
    print(f"[range-breakout-short] {msg}", flush=True)


def _compute_bb(closes, period, stddev):
    """Bollinger Bands: middle (SMA), upper, lower, width %, slope."""
    if len(closes) < period:
        return None, None, None, None, None
    middle = float(np.mean(closes[-period:]))
    variance = float(np.var(closes[-period:]))
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    # Slope: change in middle over last 5 bars
    if len(closes) >= period + 5:
        prev_middle = float(np.mean(closes[-period - 5:-5]))
        slope = (middle - prev_middle) / prev_middle if prev_middle > 0 else 0
    else:
        slope = 0
    return middle, upper, lower, width, slope


def _compute_rsi(closes, period=14):
    """RSI calculation."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _count_band_touches(closes, upper, lower, window):
    """Count how many times price touched each band in the window."""
    upper_touches = 0
    lower_touches = 0
    recent = closes[-window:] if len(closes) >= window else closes
    for i, c in enumerate(recent):
        if c >= upper * 0.998:  # within 0.2% of upper
            upper_touches += 1
        if c <= lower * 1.002:  # within 0.2% of lower
            lower_touches += 1
    return upper_touches, lower_touches


def _get_candles_5m(token, lookback=100):
    """Get 5m candle closes from candles.db."""
    if not os.path.exists(_CANDLES_DB):
        return []
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_1h_trend(token):
    """Check 1H EMA trend for regime filter."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 50
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 20:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]
        ema20 = sum(closes[-20:]) / 20
        ema50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else ema20
        current = closes[-1]
        if current > ema20 > ema50:
            return 'BULLISH'
        elif current < ema20 < ema50:
            return 'BEARISH'
        return 'NEUTRAL'
    except Exception:
        return 'NEUTRAL'
    finally:
        if conn:
            conn.close()


def detect_breakout_short(closes, token):
    """
    Detect range breakout for SHORT entries.

    Returns:
        dict {direction, confidence, range_width, rsi, squeeze_bars, bounce_pct, trend} or None
    """
    if not closes or len(closes) < LOOKBACK:
        return None

    arr = np.array(closes, dtype=np.float64)

    # ── Phase 1: Was there a range? ──────────────────────────────────────
    middle, upper, lower, width, slope = _compute_bb(arr, BB_PERIOD, BB_STDDEV)
    if middle is None:
        return None

    # Check if recent history was range-bound
    range_confirmed = False
    squeeze_bars = 0
    check_window = min(50, len(closes) - BB_PERIOD)
    for i in range(check_window):
        idx = len(closes) - check_window + i
        if idx < BB_PERIOD:
            continue
        m, u, l, w, s = _compute_bb(arr[:idx + 1], BB_PERIOD, BB_STDDEV)
        if m is not None and w < BB_WIDTH_MAX and abs(s) < BB_SLOPE_MAX:
            squeeze_bars += 1
            range_confirmed = True
        else:
            squeeze_bars = 0

    if not range_confirmed:
        return None

    # Count band touches
    upper_touches, lower_touches = _count_band_touches(closes, upper, lower, TOUCH_WINDOW)
    total_touches = upper_touches + lower_touches
    if total_touches < TOUCH_MIN:
        return None

    # ── Phase 2: Did a breakout happen recently? (SHORT only) ──────────
    breakout_idx = None
    bw = BREAKOUT_WINDOW

    for i in range(1, bw + 1):
        idx = len(closes) - i
        if idx < 0:
            break
        m, u, l, w, s = _compute_bb(arr[:idx + 1], BB_PERIOD, BB_STDDEV)
        if m is None:
            continue
        if closes[idx] < l:
            breakout_idx = idx
            breakout_upper = u
            breakout_lower = l
            breakout_middle = m
            break

    if breakout_idx is None:
        return None  # no SHORT breakout found

    # ── Phase 3: Invalidation — close back inside range? ────────────────
    for i in range(1, INVALIDATION_WINDOW + 1):
        idx = len(closes) - i
        if idx <= breakout_idx:
            break
        m, u, l, w, s = _compute_bb(arr[:idx + 1], BB_PERIOD, BB_STDDEV)
        if m is None:
            continue
        if closes[idx] > l:
            return None  # failed breakout — closed back above lower band

    # ── Phase 4: Retest + bounce NOW ─────────────────────────────────────
    current_close = closes[-1]
    prev_close = closes[-2] if len(closes) >= 2 else current_close
    rsi = _compute_rsi(closes)

    retest_level = breakout_lower
    retest_pct = RETEST_PCT / 100.0
    if abs(current_close - retest_level) / retest_level > retest_pct:
        return None
    if current_close >= prev_close:
        return None  # not bouncing down
    bounce_pct = (breakout_lower - current_close) / breakout_lower * 100

    if bounce_pct < BOUNCE_MIN:
        return None

    # ── Phase 5: RSI sanity (SHORT-specific) ─────────────────────────────
    if rsi is not None and rsi < RSI_SHORT_MIN:
        return None  # not overbought enough for SHORT

    # ── Confidence scoring ───────────────────────────────────────────────
    conf = CONF_BASE
    squeeze_bonus = min(15, squeeze_bars)
    bounce_bonus = min(10, bounce_pct * 20)
    conf += squeeze_bonus + bounce_bonus

    # 1H trend bonus (SHORT + BEARISH = aligned)
    trend = _get_1h_trend(token)
    if trend == 'BEARISH':
        conf += 5

    # Dynamic bonuses
    if bounce_pct > 0.15:
        conf = min(88, conf + 3)
    if squeeze_bars > 10:
        conf = min(88, conf + 3)
    if width * 100 > 0.5:
        conf = min(88, conf + 3)

    # Speed bonus
    try:
        from speed_tracker import get_token_speed
        spd = get_token_speed(token)
        vel = spd.get('speed_percentile', 0) if spd else 0
        if vel >= 80:
            conf = min(88, conf + 5)
    except Exception:
        pass

    conf = min(CONF_CAP, max(50, conf))

    return {
        'direction': 'SHORT',
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
    """Scan all tokens for SHORT range breakout signals."""
    from signal_schema import get_all_latest_prices

    added = 0
    now = time.time()

    # Kill-switch
    if not RANGE_BREAKOUT_SHORT_ENABLED:
        return 0

    for token, data in get_all_latest_prices().items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        token_upper = token.upper()

        # Price freshness
        if price_age_minutes(token) > 10:
            continue

        # Cooldown
        if get_cooldown(token, direction='SHORT'):
            continue

        closes = _get_candles_5m(token, lookback=2500)
        if not closes or len(closes) < 100:
            continue

        sig = detect_breakout_short(closes, token)
        if sig is None:
            continue

        # Blacklist
        if token_upper in SHORT_BLACKLIST:
            continue

        # Regime filter: block SHORT in BULLISH trend
        trend = sig.get('trend', 'NEUTRAL')
        if trend == 'BULLISH':
            continue

        # Velocity filter: block SHORT when price is rising (selling into rally)
        _conn_vel = None
        try:
            from paths import HERMES_DATA
            import sqlite3 as _sqlite3
            _conn_vel = _sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes.db'), timeout=10)
            _cur = _conn_vel.cursor()
            _cur.execute("""
                SELECT price FROM (
                    SELECT price, timestamp FROM price_history
                    WHERE token = ?
                    ORDER BY timestamp DESC LIMIT 6
                ) sub ORDER BY timestamp ASC
            """, (token_upper,))
            _prices = [r[0] for r in _cur.fetchall()]
            if len(_prices) >= 2 and _prices[0] > 0:
                _vel_5m = (_prices[-1] - _prices[0]) / _prices[0] * 100
                if _vel_5m > VEL_5M_MAX:
                    continue  # price rising — don't sell into rally
        except Exception:
            pass
        finally:
            if _conn_vel:
                _conn_vel.close()

        # Spike exhaustion filter
        _conn_se = None
        try:
            from hermes_constants import SPIKE_EXHAUSTION_VEL_5M_THRESHOLD
            from paths import HERMES_DATA as _HERMES_DATA_SE
            import sqlite3 as _sqlite3_se
            _conn_se = _sqlite3_se.connect(os.path.join(_HERMES_DATA_SE, 'signals_hermes.db'), timeout=10)
            _cur = _conn_se.cursor()
            _cur.execute("""
                SELECT price FROM (
                    SELECT price, timestamp FROM price_history
                    WHERE token = ?
                    ORDER BY timestamp DESC LIMIT 6
                ) sub ORDER BY timestamp ASC
            """, (token_upper,))
            _prices_se = [r[0] for r in _cur.fetchall()]
            if len(_prices_se) >= 2 and _prices_se[0] > 0:
                _vel_se = (_prices_se[-1] - _prices_se[0]) / _prices_se[0] * 100
                if abs(_vel_se) > SPIKE_EXHAUSTION_VEL_5M_THRESHOLD:
                    continue  # spike exhaustion — skip
        except Exception:
            pass
        finally:
            if _conn_se:
                _conn_se.close()

        source = 'range_breakout-'

        sid = add_signal(
            token=token_upper,
            direction='SHORT',
            signal_type='range_breakout_short',
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
            set_cooldown(token, direction='SHORT', hours=RANGE_BREAKOUT_COOLDOWN_HOURS)
            _log(f'SHORT  {token:8s} conf={sig["confidence"]:3.0f}% '
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
    print(f"[range-breakout-short] Done. {n} signals emitted.")
