#!/usr/bin/env python3
"""
macd_divergence.py — MACD Histogram Divergence Signal.

Detects bullish and bearish divergence between price action and MACD histogram:
  - BULLISH (LONG): Price makes a lower low, but MACD histogram makes a higher low
    → bearish momentum is fading, reversal upward expected
  - BEARISH (SHORT): Price makes a higher high, but MACD histogram makes a lower high
    → bullish momentum is fading, reversal downward expected

Architecture:
  5m candles → pivot detection → MACD histogram divergence → add_signal()
  → signals_hermes_runtime.db → signal_compactor → hotset.json → decider_run

Signal types:
  - macd_divergence_long  : bullish divergence (price lower low + MACD higher low)
  - macd_divergence_short : bearish divergence (price higher high + MACD lower high)

Source: macd-div+ / macd-div-
"""

import sys, os, sqlite3
from typing import Optional, Tuple, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA

# ── Paths ─────────────────────────────────────────────────────────────────────
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Signal metadata ─────────────────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'macd_divergence_long'
SIGNAL_TYPE_SHORT = 'macd_divergence_short'
SOURCE_LONG       = 'macd-div+'
SOURCE_SHORT      = 'macd-div-'
TIMEFRAME         = '5m'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema(data, period):
    """Return EMA series (oldest first), None for indices < period-1."""
    if len(data) < period:
        return [None] * len(data)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(data[:period]) / period
    result.append(ema_val)
    for price in data[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MACD computation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_macd_histogram(closes, fast=12, slow=26, signal_period=9):
    """Compute MACD histogram on a closes list. Returns hist list (oldest first).
    Values before warmup are None."""
    if len(closes) < slow + signal_period:
        return None

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    # MACD line = EMA(fast) - EMA(slow)
    macd_line = []
    for ef, es in zip(ema_fast, ema_slow):
        if ef is None or es is None:
            macd_line.append(None)
        else:
            macd_line.append(ef - es)

    # Signal line = EMA(signal_period) of MACD line
    first_valid = slow - 1
    macd_valid = macd_line[first_valid:]
    if len(macd_valid) < signal_period:
        return None

    ema_sig = _ema(macd_valid, signal_period)
    if ema_sig is None or len(ema_sig) < signal_period:
        return None

    signal_line = [None] * first_valid + ema_sig

    # Histogram = MACD line - signal line
    hist = []
    for m, s in zip(macd_line, signal_line):
        if m is None or s is None:
            hist.append(None)
        else:
            hist.append(m - s)

    return hist


# ═══════════════════════════════════════════════════════════════════════════════
# Pivot / swing-point detection
# ═══════════════════════════════════════════════════════════════════════════════

def _find_swing_lows(series, lookback=3):
    """Find indices where series makes a local minimum (pivot low).
    A swing low at index i requires series[i] < series[i-lookback..i] AND series[i] < series[i+1..i+lookback].
    Returns list of (index, value) tuples, oldest first."""
    swings = []
    n = len(series)
    for i in range(lookback, n - lookback):
        if series[i] is None:
            continue
        # Check left and right neighbors
        is_low = True
        for j in range(1, lookback + 1):
            left = series[i - j]
            right = series[i + j] if i + j < n else None
            if left is not None and series[i] >= left:
                is_low = False
                break
            if right is not None and series[i] >= right:
                is_low = False
                break
        if is_low:
            swings.append((i, series[i]))
    return swings


def _find_swing_highs(series, lookback=3):
    """Find indices where series makes a local maximum (pivot high).
    Returns list of (index, value) tuples, oldest first."""
    swings = []
    n = len(series)
    for i in range(lookback, n - lookback):
        if series[i] is None:
            continue
        is_high = True
        for j in range(1, lookback + 1):
            left = series[i - j]
            right = series[i + j] if i + j < n else None
            if left is not None and series[i] <= left:
                is_high = False
                break
            if right is not None and series[i] <= right:
                is_high = False
                break
        if is_high:
            swings.append((i, series[i]))
    return swings


# ═══════════════════════════════════════════════════════════════════════════════
# Divergence detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_divergence(closes, swing_lookback=3, min_pivot_distance=5):
    """Detect MACD histogram divergence against price.

    Args:
        closes: list of close prices, oldest-first
        swing_lookback: bars on each side to confirm a swing point
        min_pivot_distance: minimum bars between two pivots to count as distinct

    Returns:
        ('LONG', confidence)  — bullish divergence detected
        ('SHORT', confidence) — bearish divergence detected
        None                  — no signal
    """
    from hermes_constants import (
        MACD_DIV_CONF_BASE, MACD_DIV_CONF_FLOOR, MACD_DIV_CONF_CAP,
        MACD_DIV_FAST, MACD_DIV_SLOW, MACD_DIV_SIGNAL_PERIOD,
        MACD_DIV_SWING_LOOKBACK, MACD_DIV_MIN_PIVOT_DIST,
        MACD_DIV_MIN_HIST_SLOPE, MACD_DIV_MIN_PRICE_CHANGE_PCT,
        MACD_DIV_STRONG_PRICE_PCT, MACD_DIV_STRONG_HIST_RATIO,
        MACD_DIV_MEDIUM_PRICE_PCT, MACD_DIV_MEDIUM_HIST_RATIO,
    )

    fast = MACD_DIV_FAST
    slow = MACD_DIV_SLOW
    signal_period = MACD_DIV_SIGNAL_PERIOD
    swing_lookback = MACD_DIV_SWING_LOOKBACK
    min_dist = MACD_DIV_MIN_PIVOT_DIST

    hist = compute_macd_histogram(closes, fast=fast, slow=slow, signal_period=signal_period)
    if hist is None:
        return None

    # Find price swing lows and swing highs
    price_lows = _find_swing_lows(closes, lookback=swing_lookback)
    price_highs = _find_swing_highs(closes, lookback=swing_lookback)

    # Find MACD histogram swing lows and swing highs
    hist_lows = _find_swing_lows(hist, lookback=swing_lookback)
    hist_highs = _find_swing_highs(hist, lookback=swing_lookback)

    # Need at least 2 pivots in both price and hist to compare
    # ── Bullish divergence (LONG) ──────────────────────────────────────
    # Price makes lower low, MACD hist makes higher low
    if len(price_lows) >= 2 and len(hist_lows) >= 2:
        p1_idx, p1_val = price_lows[-2]
        p2_idx, p2_val = price_lows[-1]
        if p2_idx - p1_idx >= min_dist and p2_val < p1_val:
            price_change_pct = abs(p2_val - p1_val) / max(abs(p1_val), 1e-10)
            if price_change_pct >= MACD_DIV_MIN_PRICE_CHANGE_PCT:
                # Find hist lows near the price pivot points
                h1 = _find_nearest_hist_extreme(hist_lows, p1_idx, swing_lookback * 2)
                h2 = _find_nearest_hist_extreme(hist_lows, p2_idx, swing_lookback * 2)
                if h1 is not None and h2 is not None:
                    h1_idx, h1_val = h1
                    h2_idx, h2_val = h2
                    if h2_val > h1_val:
                        # Confirm histogram is turning up
                        cur_hist = hist[-1]
                        prev_hist = hist[-2] if len(hist) >= 2 else None
                        if cur_hist is not None and prev_hist is not None and cur_hist > prev_hist:
                            hist_recovery = abs(h2_val - h1_val) / max(abs(h1_val), 1e-10) if h1_val != 0 else 0
                            if price_change_pct > MACD_DIV_STRONG_PRICE_PCT and hist_recovery > MACD_DIV_STRONG_HIST_RATIO:
                                conf = MACD_DIV_CONF_CAP
                            elif price_change_pct > MACD_DIV_MEDIUM_PRICE_PCT or hist_recovery > MACD_DIV_MEDIUM_HIST_RATIO:
                                conf = MACD_DIV_CONF_BASE + 5
                            else:
                                conf = MACD_DIV_CONF_BASE
                            conf = min(MACD_DIV_CONF_CAP, max(MACD_DIV_CONF_FLOOR, conf))
                            return ('LONG', conf)

    # ── Bearish divergence (SHORT) ─────────────────────────────────────
    # Price makes higher high, MACD hist makes lower high
    if len(price_highs) >= 2 and len(hist_highs) >= 2:
        p1_idx, p1_val = price_highs[-2]
        p2_idx, p2_val = price_highs[-1]
        if p2_idx - p1_idx >= min_dist and p2_val > p1_val:
            price_change_pct = abs(p2_val - p1_val) / max(abs(p1_val), 1e-10)
            if price_change_pct >= MACD_DIV_MIN_PRICE_CHANGE_PCT:
                h1 = _find_nearest_hist_extreme(hist_highs, p1_idx, swing_lookback * 2)
                h2 = _find_nearest_hist_extreme(hist_highs, p2_idx, swing_lookback * 2)
                if h1 is not None and h2 is not None:
                    h1_idx, h1_val = h1
                    h2_idx, h2_val = h2
                    if h2_val < h1_val:
                        cur_hist = hist[-1]
                        prev_hist = hist[-2] if len(hist) >= 2 else None
                        if cur_hist is not None and prev_hist is not None and cur_hist < prev_hist:
                            hist_decline = abs(h1_val - h2_val) / max(abs(h1_val), 1e-10) if h1_val != 0 else 0
                            if price_change_pct > MACD_DIV_STRONG_PRICE_PCT and hist_decline > MACD_DIV_STRONG_HIST_RATIO:
                                conf = MACD_DIV_CONF_CAP
                            elif price_change_pct > MACD_DIV_MEDIUM_PRICE_PCT or hist_decline > MACD_DIV_MEDIUM_HIST_RATIO:
                                conf = MACD_DIV_CONF_BASE + 5
                            else:
                                conf = MACD_DIV_CONF_BASE
                            conf = min(MACD_DIV_CONF_CAP, max(MACD_DIV_CONF_FLOOR, conf))
                            return ('SHORT', conf)

    return None


def _find_nearest_hist_extreme(swings, target_idx, max_distance):
    """Find the swing point closest to target_idx within max_distance.
    Returns (index, value) or None."""
    best = None
    best_dist = max_distance + 1
    for idx, val in swings:
        dist = abs(idx - target_idx)
        if dist <= max_distance and dist < best_dist:
            best_dist = dist
            best = (idx, val)
    return best


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_5m_closes(token, lookback):
    """Fetch 5m close prices from candles.db. Returns oldest-first list or None."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT close FROM candles_5m WHERE token=? "
            "ORDER BY ts DESC LIMIT ?",
            (token.upper(), lookback)
        )
        rows = c.fetchall()
        if not rows:
            return None
        return [r[0] for r in reversed(rows)]
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_signals():
    """Scan all tokens for MACD divergence signals. Returns count added."""
    from hermes_constants import (
        MACD_DIVERGENCE_ENABLED, MACD_DIVERGENCE_PLUS_ENABLED, MACD_DIVERGENCE_MINUS_ENABLED,
        LONG_BLACKLIST, SHORT_BLACKLIST,
        MACD_DIV_LOOKBACK_BARS,
    )

    if not MACD_DIVERGENCE_ENABLED:
        return 0

    from signal_schema import get_all_latest_prices

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue
        if not data.get('price') or data['price'] <= 0:
            continue

        # Staleness check
        if price_age_minutes(token) > 10:
            continue

        # Cooldown check
        if get_cooldown(token, direction='LONG') or get_cooldown(token, direction='SHORT'):
            continue

        price = data['price']
        closes = _get_5m_closes(token, MACD_DIV_LOOKBACK_BARS)
        if closes is None or len(closes) < 40:
            continue

        result = detect_divergence(closes)
        if result is None:
            continue

        direction, confidence = result

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not MACD_DIVERGENCE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not MACD_DIVERGENCE_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=confidence,
            value=float(confidence),
            price=price,
            exchange='hyperliquid',
            timeframe=TIMEFRAME,
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=3)

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run():
    """Entry point for signals_runner. No prices_dict needed — reads from candles.db."""
    return scan_signals()
