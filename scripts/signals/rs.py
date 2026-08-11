# Migrated from ../rs_signals.py — see signals/__init__.py registry
#!/usr/bin/env python3
"""
rs_signals.py — Support & Resistance Signal Scanner for Hermes.

SIGNAL TYPE: structural mean-reversion (primary — competes equally in hot-set scoring)
LOG_FILE: /var/www/hermes/logs/signals.log

== WHAT IT DETECTS ==
Detects swing-structure support and resistance levels from 1m OHLCV candles and fires
LONG when price bounces from a support level, SHORT when rejected from resistance.
It is a structural mean-reversion signal — the market "remembering" where it reversed.

== ALL CONDITIONS ==
 1. SWING DETECTION:    find local swing highs/lows via NumPy rolling max/min over
 a rolling window (RS_LEVEL_LOOKBACK) across ~4700 1m candles
 2. LEVEL CLUSTERING:  group nearby levels within ATR-based threshold → average into
 named structural levels with aggregated touch count
 3. MINIMUM TOUCHES:   levels must be touched at least RS_MIN_TOUCHES times to be valid
 4. ATR PROXIMITY:     price must be within RS_PROXIMITY_K ATRs of the level
 (volatility-adaptive, not a fixed %)
 5. BOUNCE CONFIRMATION: for LONG: candle closed near support, next candle closed >0.025%
 higher; for SHORT: closed near resistance, next candle closed >0.025% lower
 6. LEVEL NOT BROKEN: support broken with TWO confirming candles below = invalid for LONG;
 resistance broken with TWO confirming candles above = invalid for SHORT
 7. RECENCY WEIGHTING: recent touches count more than ancient ones
 (recency_score = recent + K×ancient) — fresh levels beat old exhausted ones
 8. REGIME-AWARE:      when both support and resistance are near, 5m regime picks direction;
 counter-regime signals get 20% confidence haircut
 9. TOUCH HARD CAP:    levels touched too many times (RS_TOUCH_HARD_CAP) are blocked as exhausted
10. BROKEN LEVEL PATHS: broken support SHORT and broken resistance LONG are both DISABLED
 (both were counter-trend traps in backtesting); broken levels that have since recovered
 are reclassified as active bounces

== INTENT ==
RS is a structural mean-reversion signal — it watches for price returning to a level it
has touched multiple times before and bouncing. The bounce confirmation requirement ensures
price actually COMMITS to the direction rather than just skating through the level. It
complements momentum signals like accel_300 by providing a counter-trend entry when price
reaches known structural levels. Recency weighting means the market's RECENT memory of a
level matters more than ancient touches — old levels that have been ignored are deprioritized.

== ARCHITECTURE ==
  - Reads 1m candles from price_history via signal_schema.get_ohlcv_1m()
  - Computes ATR(14) for volatility-normalized level proximity
  - Finds swing highs/lows in a rolling window → clusters into structural levels
  - Fires when price is within RS_PROXIMITY_K ATRs of a level with bounce confirmation
  - Writes via signal_schema.add_signal() (blacklists, merge logic applied)

== SIGNAL TYPES ==
  - support_resistance: direction=LONG → near support + bounce confirmation
  - support_resistance: direction=SHORT → near resistance + rejection confirmation
"""

import sys
import os
import time
import sqlite3
import json
from typing import Optional
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal
from hermes_constants import (
    RS_LOOKBACK_CANDLES,
    RS_LEVEL_LOOKBACK,
    RS_ATR_PERIOD,
    RS_CLUSTER_ATR,
    RS_PROXIMITY_K,
    RS_MIN_TOUCHES,
    RS_COOLDOWN_HOURS,
    RS_SIGNAL_TYPE,
    RS_SOURCE_PREFIX,
    RS_MIN_CONFIDENCE,
    RS_MAX_CONFIDENCE,
    RS_RECENCY_WINDOW,
    RS_RECENCY_BOOST_K,
    RS_BOUNCE_LOOKBACK,
    RS_BOUNCE_THRESH_ATR,
    RS_DECIDER_MIN_TOUCHES,
    RS_TOUCH_HARD_CAP,
    RS_BROKEN_SHORT_ENABLED,
    RS_BROKEN_RESISTANCE_LONG_ENABLED,
    RS_ATR_DIST_FALLBACK,
)

# Regime lookup for RS directionality
_REGIME_FILE = '/var/www/hermes/data/regime_5m.json'

def _get_regime_5m(token: str):
    """Return (regime_str, confidence) for a token from regime_5m.json."""
    try:
        with open(_REGIME_FILE) as f:
            data = json.load(f)
        if token.upper() in data.get('regimes', {}):
            reg = data['regimes'][token.upper()]
            return reg.get('regime', 'NEUTRAL'), reg.get('confidence', 0)
    except Exception:
        pass
    return 'NEUTRAL', 0


# ── 5m OHLCV candles (real wicks for pattern detection) ──────────────────────

_CANDLES_DB = '/root/.hermes/data/candles.db'


def _get_candles_5m(token: str, limit: int = 50) -> list:
    """Fetch real OHLCV 5m candles from candles.db for pattern detection.

    Returns list of {open, high, low, close, volume} oldest-first.
    These have real wick data (unlike synthesized price_history candles).
    """
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close, volume FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        if not rows:
            return []
        return [{'open': r[0], 'high': r[1], 'low': r[2], 'close': r[3], 'volume': r[4]}
                for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ── Candle pattern detection (Woods, Porwal) ─────────────────────────────────

def _detect_candle_pattern(candle: dict, prev_candle: dict = None) -> Optional[str]:
    """Detect high-probability candle patterns at S/R levels.

    Returns pattern name or None. Uses real OHLCV (with wicks).

    Patterns (from books):
    - pin_bar_bull: long lower wick (>66% of range), small body (<33%) at support
    - pin_bar_bear: long upper wick (>66% of range), small body (<33%) at resistance
    - engulfing_bull: body > prev body, closes above prev open, body overlaps
    - engulfing_bear: body > prev body, closes below prev open, body overlaps
    - doji: very small body (<10% of range) — indecision at key level
    """
    if not candle:
        return None

    o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
    total_range = h - l
    if total_range <= 0:
        return None

    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Pin bar: long wick + small body
    if lower_wick > total_range * 0.66 and body < total_range * 0.33:
        return 'pin_bar_bull'
    if upper_wick > total_range * 0.66 and body < total_range * 0.33:
        return 'pin_bar_bear'

    # Doji: very small body
    if body < total_range * 0.10:
        return 'doji'

    # Engulfing: body > prev body, opposite direction, body overlaps prev body
    if prev_candle:
        po, ph, pl, pc = prev_candle['open'], prev_candle['high'], prev_candle['low'], prev_candle['close']
        prev_body = abs(pc - po)
        if body > prev_body and prev_body > 0:
            # Bullish engulfing: prev red, current green, current body engulfs prev body
            if pc < po and c > o and o <= pc and c >= po:
                return 'engulfing_bull'
            # Bearish engulfing: prev green, current red, current body engulfs prev body
            if pc > po and c < o and o >= pc and c <= po:
                return 'engulfing_bear'

    return None


def _pattern_at_level(candles_5m: list, level: float, direction: str,
                       atr_value: float = None) -> dict:
    """Check if a candle pattern formed at the S/R level in recent candles.

    Scans last N candles for a pattern that touched the level and had a
    confirming move. Returns {pattern, confidence_bonus} or None.

    Books:
    - Pin bar at support → +10 confidence (Woods)
    - Engulfing at support → +8 confidence (Porwal)
    - Doji at support + confirmation → +5 confidence (Porwal)
    """
    if not candles_5m or len(candles_5m) < 3:
        return None

    # ATR-based touch threshold
    if atr_value and atr_value > 0:
        touch_thresh = atr_value * 0.3  # within 0.3 ATR = "at the level"
    else:
        touch_thresh = abs(level) * 0.003  # 0.3% fallback

    # Scan last 10 candles for pattern at level
    recent = candles_5m[-10:]
    for i in range(1, len(recent)):
        c = recent[i]
        prev = recent[i - 1]

        # Did this candle touch the level?
        touched = (abs(c['low'] - level) < touch_thresh or
                   abs(c['high'] - level) < touch_thresh or
                   abs(c['close'] - level) < touch_thresh)
        if not touched:
            continue

        pattern = _detect_candle_pattern(c, prev)
        if pattern is None:
            continue

        # Match pattern to direction
        if direction == 'LONG' and pattern in ('pin_bar_bull', 'engulfing_bull'):
            bonus = 10 if pattern == 'pin_bar_bull' else 8
            return {'pattern': pattern, 'confidence_bonus': bonus}
        if direction == 'SHORT' and pattern in ('pin_bar_bear', 'engulfing_bear'):
            bonus = 10 if pattern == 'pin_bar_bear' else 8
            return {'pattern': pattern, 'confidence_bonus': bonus}
        # Doji works both ways — smaller bonus
        if pattern == 'doji':
            return {'pattern': pattern, 'confidence_bonus': 5}

    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _atr(candles: list, period: int = RS_ATR_PERIOD) -> Optional[float]:
    """Compute ATR(period) from a list of OHLCV candles (oldest first).
    Returns ATR value or None if not enough data."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        high  = candles[i]['high']
        low   = candles[i]['low']
        prev  = candles[i-1]['close']
        tr = max(
            high - low,
            abs(high - prev),
            abs(low  - prev)
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    # Use Wilder's smoothed ATR
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _atr_pct(price: float, atr: float) -> float:
    """ATR as a percentage of price (for normalized distance)."""
    if price <= 0:
        return 0.0
    return atr / price * 100.0


def _rolling_max(arr, window):
    """Rolling max using NumPy — O(N) instead of O(N*window)."""
    n = len(arr)
    out = np.empty(n, dtype=np.float64)
    out[:window - 1] = arr[:window - 1]
    for i in range(window - 1, n):
        out[i] = arr[i - window + 1:i + 1].max()
    return out

def _rolling_min(arr, window):
    """Rolling min using NumPy — O(N) instead of O(N*window)."""
    n = len(arr)
    out = np.empty(n, dtype=np.float64)
    out[:window - 1] = arr[:window - 1]
    for i in range(window - 1, n):
        out[i] = arr[i - window + 1:i + 1].min()
    return out

def _find_swing_highs_lows(candles: list, window: int = RS_LEVEL_LOOKBACK):
    """Find local swing highs and lows using NumPy rolling max/min.

    Uses a CENTERED extrema check: a point qualifies as a swing high only if
    it is at or above the trailing rolling max (window behind) AND there is
    no higher price in the window ahead (forward rolling max). This prevents
    right-shoulder bias where the trailing-window max always flags the start
    of a plateau as a swing high.

    Returns:
        (swing_highs: list of (idx, price), swing_lows: list of (idx, price))
    """
    n = len(candles)
    if n < window * 2 + 1:
        return [], []

    highs = np.array([c['high'] for c in candles], dtype=np.float64)
    lows  = np.array([c['low']  for c in candles], dtype=np.float64)

    roll_high = _rolling_max(highs, window)
    roll_min  = _rolling_min(lows,  window)

    # Forward rolling max/min: look ahead from each point. A true swing high must
    # be >= everything in the window after it. NaN at boundaries fails naturally.
    # roll_high[i] = max(highs[i-window+1:i+1]); forward_high[i] = max(highs[i+1:i+window+1])
    # FIX: forward window at index i spans highs[i+1:i+window+1], whose max is
    # roll_high[i+window]. Append window NaNs at the front so the array length
    # stays n, with NaNs filling the last window positions where forward check is impossible.
    forward_high = np.concatenate([roll_high[window:], np.full(window, np.nan)])
    forward_min  = np.concatenate([roll_min[window:],  np.full(window,  np.nan)])

    swing_highs = [(i, highs[i]) for i in range(window, n - window)
                   if highs[i] == roll_high[i] and highs[i] >= forward_high[i]]
    swing_lows  = [(i, lows[i])  for i in range(window, n - window)
                   if lows[i]  == roll_min[i]  and lows[i]  <= forward_min[i]]

    return swing_highs, swing_lows


def _cluster_levels(levels: list, cluster_atr_pct: float) -> list:
    """Cluster price levels that are within cluster_atr_pct of each other.
    Each cluster is replaced by its average price (simple mean, not touch-count weighted).

    Args:
        levels: list of (price, touch_count) tuples
        cluster_atr_pct: clustering threshold as % of price (e.g. 0.003 = 0.3%)

    Returns:
        list of (clustered_price, total_touch_count)
    """
    if not levels:
        return []
    # Guard against zero/negative prices
    if any(p <= 0 for p, _ in levels):
        levels = [(p, c) for p, c in levels if p > 0]
        if not levels:
            return []
    # Sort by price
    sorted_levels = sorted(levels, key=lambda x: x[0])
    clusters = []
    current_cluster = [sorted_levels[0]]
    for level in sorted_levels[1:]:
        price, count = level
        # Compare against the ANCHOR level (first level in cluster), not the running
        # average. Using a running average causes cluster creep: [(100),(105),(106)]
        # with 5% threshold clusters all 3 (avg=103.67, 106 is 3.4% from avg)
        # when 106 should form its own cluster (6% from anchor 100).
        anchor_price = current_cluster[0][0]
        # If within cluster threshold of the anchor level, add to cluster
        if abs(price - anchor_price) / anchor_price * 100.0 <= cluster_atr_pct:
            current_cluster.append(level)
        else:
            clusters.append(current_cluster)
            current_cluster = [level]
    clusters.append(current_cluster)

    result = []
    for cluster in clusters:
        avg_price = sum(p for p, _ in cluster) / len(cluster)
        total_count = sum(c for _, c in cluster)
        result.append((avg_price, total_count))
    return result


def _price_near_level(price: float, level: float, atr_pct: float, k: float = RS_PROXIMITY_K) -> bool:
    """Return True if price is within k ATRs of the level."""
    if price <= 0 or level <= 0 or atr_pct <= 0:
        return False
    dist_pct = abs(price - level) / price * 100.0
    atr_dist = dist_pct / atr_pct
    return atr_dist <= k


def _bounce_confirmation(candles: list, level: float, direction: str,
                          atr_value: float = None,
                          lookback: int = RS_BOUNCE_LOOKBACK) -> bool:
    """Check if price recently bounced from the level.

    For LONG (near support): find at least one candle whose close was near the
    level, then verify the next candle's close moved UP by >0.05%.
    For SHORT (near resistance): close near level, next close moved DOWN >0.05%.

    Works on close-only (synthesized) candles: we detect bounces across candle
    boundaries using successive close prices. Intra-candle wicks cannot be
    detected since open=high=low=close for every candle.

    Returns True if bounce is confirmed.
    """
    if len(candles) < lookback:
        return False

    recent = candles[-lookback:]

    if atr_value is None or atr_value <= 0:
        # Fallback: use fixed 0.15% threshold
        thresh = level * 0.0015
    else:
        thresh = atr_value * RS_BOUNCE_THRESH_ATR

    # Bounce confirmation: check if price bounced from the level.
    # A "touch" requires the candle to be genuinely close to the level:
    # require candle to be within 0.2 * ATR of the level (only candles that actually
    # HIT the level trigger the bounce check — not just any candle within 1 ATR).
    # The 0.025% follow-through requires the NEXT candle to commit in the bounce direction.
    # FIX: was using full thresh (1.0 ATR), which caught any candle within 1 ATR and
    # caused false positives (a candle 0.8 ATR away with a later upward move counted as bounce).
    touch_thresh = thresh * 0.2  # only count as a touch if within 0.2 ATR

    if direction == 'LONG':
        for i, c in enumerate(recent):
            if abs(c['close'] - level) < touch_thresh:
                if i + 1 < len(recent):
                    next_close = recent[i + 1]['close']
                    # FIX: compare to LEVEL, not to candle close.
                    # Old: next_close > c['close'] * 1.00025 (any candle 0.2% away from level
                    # confirms with just 0.025% move above ITSELF — scale mismatch, 8:1 ratio).
                    # New: next_close must move 0.025% ABOVE the level itself.
                    if next_close > level * 1.00025:
                        return True
        return False

    else:  # SHORT
        for i, c in enumerate(recent):
            if abs(c['close'] - level) < touch_thresh:
                if i + 1 < len(recent):
                    next_close = recent[i + 1]['close']
                    # FIX: compare to LEVEL, not to candle close.
                    # New: next_close must move 0.025% BELOW the level itself.
                    if next_close < level * 0.99975:
                        return True
        return False


# ── ATR-distance guard ──────────────────────────────────────────────────────────
# The 0.3–0.6 ATR band is empirically a trap in backtesting (avg PnL = -0.095%).
# Levels this close feel "near" but price hasn't committed. Reject that band.
# _RS_ATR_BAND_SOFT_MIN  = 0.30  # below this: too close to call (could be AT the level)
# _RS_ATR_BAND_SOFT_MAX  = 0.60  # above this: comfortably outside, safe
# (DEPRECATED 2026-05-06 — removed ATR band filter, levels in this range are valid)


def _level_recently_broken(candles: list, level: float, lookback: Optional[int] = None,
                            direction: str = 'support') -> bool:
    """Return True if the level was *definitively* broken in the given direction.

    For 'support': price must have closed below the level and STAYED below
    (the candle AFTER the break must also be below the level).

    For 'resistance': price must have closed above the level and STAYED above
    (the candle AFTER the break must also be above the level).

    price_history is close-only (open=high=low=close for every candle), so we
    detect a level crossing by checking if two successive candle closes are
    on opposite sides of the level.

    A broken level must have TWO confirming candles on the far side — the
    initial cross and at least one follow-through candle. This prevents a
    bounce (cross then immediate reversal) from being mistaken for a break.

    Args:
        direction: 'support' checks if support was broken downward.
                   'resistance' checks if resistance was broken upward.
    """
    from hermes_constants import RS_LEVEL_BROKEN_LOOKBACK
    if lookback is None:
        lookback = RS_LEVEL_BROKEN_LOOKBACK
    if len(candles) < 2:
        return False

    recent = candles[-min(lookback, len(candles)):]

    if direction == 'support':
        # Support broken: prev_close > level > curr_close AND
        # the candle BEFORE the break was above support (genuine crossing, not already-broken state)
        for i in range(1, len(recent)):
            prev_close = recent[i - 1]['close']
            curr_close = recent[i]['close']
            # Must be a clean cross below
            if prev_close > level > curr_close:
                # Check this candle closed BELOW and STAYED below
                if i + 1 < len(recent) and recent[i + 1]['close'] < level:
                    return True
                # Single candle below is a bounce — not a confirmed break
    else:
        # Resistance broken: prev_close < level < curr_close AND
        # the candle AFTER the cross confirms price stayed above
        for i in range(1, len(recent)):
            prev_close = recent[i - 1]['close']
            curr_close = recent[i]['close']
            # Must be a clean cross above
            if prev_close < level < curr_close:
                # Check follow-through candle closed above
                if i + 1 < len(recent) and recent[i + 1]['close'] > level:
                    return True
                # Single candle above is a rejection bounce — not a confirmed break

    return False


def _build_level_touches(candles_or_highs_lows, level: float = None,
                         atr_value: float = None,
                         return_recency: bool = False) -> int:
    """Count touches using NumPy fast path or legacy loop.

    Fast path (preferred): pass (highs_array, lows_array) as first arg.
    Legacy path: pass candles list + level + window.

    Uses ATR-based threshold so touch counting is volatility-normalized:
    - price_history is close-only (open=high=low=close for every candle)
    - a "touch" = any candle's close within RS_BOUNCE_THRESH_ATR * ATR(14) of the level
    - this avoids the 0.15% fixed threshold over-counting on volatile tokens

    Args:
        return_recency: if True, returns tuple (total_touches, recency_weighted_score)
                        recency_weighted_score = recency_touches + RS_RECENCY_BOOST_K * ancient_touches
                        where recency_touches are touches in last RS_RECENCY_WINDOW candles.
    """
    # Fast path: (highs, lows) tuple from pre-extracted arrays
    if isinstance(candles_or_highs_lows, tuple):
        highs, lows = candles_or_highs_lows
        n = len(highs)
        if atr_value is not None and atr_value > 0:
            # ATR-normalized threshold — adapts to volatility
            threshold = atr_value * RS_BOUNCE_THRESH_ATR
        else:
            # Fallback: ~0.15% of price (old hardcoded behavior)
            threshold = abs(level) * 0.0015
        touch_mask = ((np.abs(highs - level) < threshold) |
                      (np.abs(lows  - level) < threshold))
        total = int(touch_mask.sum())

        if not return_recency:
            return total

        # Recency-weighted score: recent_touches × K + ancient_touches
        # Recent touches count MORE (multiplied by K); ancient touches count at face value.
        # Higher score = fresher, more reactive level.
        # Fix: was K * recent + ancient (ancient weighted MORE). Now: recent × K + ancient.
        recent_cutoff = RS_RECENCY_WINDOW
        if n >= recent_cutoff:
            recency_touches = int(touch_mask[-recent_cutoff:].sum())
            ancient_touches = total - recency_touches
        else:
            # Not enough candles to define an "ancient" window — all touches are recent
            recency_touches = total
            ancient_touches = 0
        recency_score = recency_touches * RS_RECENCY_BOOST_K + ancient_touches
        return total, recency_score

    # Legacy path: list of dict candles
    candles = candles_or_highs_lows
    if atr_value is not None and atr_value > 0:
        threshold = atr_value * RS_BOUNCE_THRESH_ATR
    else:
        threshold = abs(level) * 0.0015
    count = 0
    for c in candles:
        low_touch = abs(c['low'] - level)
        high_touch = abs(c['high'] - level)
        if low_touch < threshold or high_touch < threshold:
            count += 1
    return count


def _compute_confidence(atr_pct: float, distance_pct: float,
                         touch_count: int, bounces: bool,
                         recency_score: float = None) -> float:
    """Compute signal confidence.

    Base: 65 (R&S is structural, starts above floor)
    ATR proximity bonus: +1 to +15 (closer = more confident)
    Touch count bonus: +1 to +10 (more historical touches = stronger level)
    Bounce confirmation bonus: +5
    Penalty if no bounce: 0 (don't penalize — levels still valid without recent bounce)
    Recency bonus: +1 to +8 (fresh levels with recent touches get a boost)
    """
    base = 65.0

    # ATR proximity bonus: 0.0 ATRs → +15, at RS_PROXIMITY_K → +0
    if atr_pct > 0:
        atr_dist = distance_pct / atr_pct
        prox_bonus = max(0, 15 * (1 - atr_dist / RS_PROXIMITY_K))
    else:
        prox_bonus = 0

    # Touch count bonus: uses recency_score if available for fresh-level boost.
    # Log-scale so 1 touch gets a decent boost, 50+ touches maxes out.
    effective_touches = recency_score if recency_score is not None else touch_count
    touch_bonus = min(9, 3 + int(np.log1p(max(0, effective_touches - 1)) * 2.5))

    # Recency bonus: fresh levels (recent touches) get additional boost
    # 0 recent touches → +0, 50+ recent touches → +8
    if recency_score is not None and touch_count > 0:
        # Derive recent_touches from recency_score and touch_count:
        # recency_score = recent_touches * K + ancient_touches
        # touch_count = recent_touches + ancient_touches
        # → recent_touches = (recency_score - touch_count) / (K - 1)
        _k = RS_RECENCY_BOOST_K
        recent_touches = (recency_score - touch_count) / max(1e-9, _k - 1)
        recent_fraction = min(1.0, recent_touches * _k / (recency_score + 1e-9))
        recency_bonus = int(8 * recent_fraction) if recency_score > touch_count else 0
    else:
        recency_bonus = 0

    bounce_bonus = 5 if bounces else 0

    confidence = base + prox_bonus + touch_bonus + bounce_bonus + recency_bonus
    return min(RS_MAX_CONFIDENCE, max(RS_MIN_CONFIDENCE, round(confidence)))


# ── Core detection ─────────────────────────────────────────────────────────────

def detect_rs_signal(token: str, candles: list, price: float) -> Optional[dict]:
    """Detect support/resistance signals for a single token.

    Args:
        token:   HL symbol e.g. 'BTC'
        candles: list of OHLCV dicts (oldest first), from get_ohlcv_1m
        price:   current price from prices_dict

    Returns:
        dict with {direction, confidence, level, source, value} or None
    """
    if not candles or len(candles) < RS_LEVEL_LOOKBACK * 2:
        return None
    if price is None or price <= 0:
        return None

    atr = _atr(candles, RS_ATR_PERIOD)
    if atr is None:
        return None
    atr_pct = _atr_pct(price, atr)

    # Pre-extract arrays once for vectorized level touch counting
    highs = np.array([c['high'] for c in candles], dtype=np.float64)
    lows  = np.array([c['low']  for c in candles], dtype=np.float64)
    candles_arrays = (highs, lows)

    # Find swing levels
    swing_highs, swing_lows = _find_swing_highs_lows(candles, RS_LEVEL_LOOKBACK)

    # Build raw level lists with touch counts (fast NumPy path, ATR-normalized)
    # Using return_recency=True to get (total_touches, recency_weighted_score)
    # Recency score: recent_touches + K * ancient_touches (prioritizes fresh levels)
    raw_resistance = [(l,) + _build_level_touches(candles_arrays, l, atr_value=atr, return_recency=True)
                      for _, l in swing_highs]
    raw_support    = [(l,) + _build_level_touches(candles_arrays, l, atr_value=atr, return_recency=True)
                      for _, l in swing_lows]
    # Each entry now: (level, total_touches, recency_score)

    # Cluster nearby levels
    cluster_pct = RS_CLUSTER_ATR * atr_pct  # convert ATR units to % for clustering
    # Strip recency scores before clustering (cluster fn expects price,count)
    r_levels_raw = [(l, tc) for l, tc, rs in raw_resistance]
    s_levels_raw = [(l, tc) for l, tc, rs in raw_support]
    r_levels = _cluster_levels(r_levels_raw, cluster_pct)
    s_levels = _cluster_levels(s_levels_raw, cluster_pct)

    if not r_levels and not s_levels:
        return None

    # Build lookup: level -> recency_score for nearby levels
    # Use recency score for best-level selection (prioritizes fresh reactive levels)
    recency_by_level = {l: rs for l, tc, rs in raw_resistance}
    recency_by_level.update({l: rs for l, tc, rs in raw_support})

    # Map clustered levels back to nearest raw level recency (clustered prices are
    # averages that won't exactly match raw level keys in recency_by_level)
    def _get_clustered_recency(clustered_level, raw_levels_list):
        """Find the raw level closest to clustered_level and return its recency."""
        best = None
        best_dist = float('inf')
        for raw_l, raw_tc, raw_rs in raw_levels_list:
            d = abs(raw_l - clustered_level)
            if d < best_dist:
                best_dist = d
                best = raw_rs
        return best if best is not None else 0

    # Find the best valid level for each direction.
    # SELECTION LOGIC: recency_score is the PRIMARY key (fresh levels are prioritized
    # over ancient exhausted ones). Distance is a SECONDARY filter (must be near enough
    # to be relevant) and tiebreaker when two levels have equal recency.
    # Previously: distance was the primary key, recency was a display attribute.
    nearest_support    = None
    nearest_resistance = None
    best_support_recency = 0.0
    best_resist_recency  = 0.0
    best_support_dist    = float('inf')
    best_resist_dist     = float('inf')

    for level, touch_count in s_levels:
        if touch_count < RS_MIN_TOUCHES:
            continue
        dist_pct = abs(price - level) / price * 100.0
        if not _price_near_level(price, level, atr_pct):
            continue
        recency = _get_clustered_recency(level, raw_support)
        # Pick level with highest recency_score; use dist as tiebreaker
        if recency > best_support_recency or \
           (recency == best_support_recency and dist_pct < best_support_dist):
            best_support_recency = recency
            best_support_dist = dist_pct
            nearest_support = (level, touch_count)

    for level, touch_count in r_levels:
        if touch_count < RS_MIN_TOUCHES:
            continue
        dist_pct = abs(price - level) / price * 100.0
        if not _price_near_level(price, level, atr_pct):
            continue
        recency = _get_clustered_recency(level, raw_resistance)
        # Pick level with highest recency_score; use dist as tiebreaker
        if recency > best_resist_recency or \
           (recency == best_resist_recency and dist_pct < best_resist_dist):
            best_resist_recency = recency
            best_resist_dist = dist_pct
            nearest_resistance = (level, touch_count)

    # Determine best signal — regime-aware (Model B)
    # When both support and resistance are near, regime picks which direction to favor.
    # This prevents self-canceling RS signals in trending markets.
    regime, regime_conf = _get_regime_5m(token)

    # Validate: both directions were already checked for proximity above
    has_support = nearest_support is not None
    has_resistance = nearest_resistance is not None

    # Model B: regime picks direction when both signals compete
    if has_support and has_resistance:
        # In trending market: fire ONLY the regime-aligned signal
        if regime == 'LONG_BIAS':
            # Suppress resistance (rs-r), fire support (rs-s) only
            nearest_resistance = None
        elif regime == 'SHORT_BIAS':
            # Suppress support (rs-s), fire resistance (rs-r) only
            nearest_support = None
        # In NEUTRAL → keep existing behavior (higher confidence wins)
    elif has_support and regime == 'SHORT_BIAS':
        # Counter-regime LONG: 20% haircut applied downstream at signal construction (lines 520-524)
        pass  # signal still fires; compactor applies 0.5x reg_mult
    elif has_resistance and regime == 'LONG_BIAS':
        # Counter-regime SHORT: 20% haircut applied downstream at signal construction (lines 552-556)
        pass  # signal still fires; compactor applies 0.5x reg_mult

    # Re-check: compute signal from whichever direction(s) remain valid
    signal = None

    # Check LONG: price near support level + bounce
    if nearest_support is not None:
        level, touch_count = nearest_support
        # Hard cap: levels touched too many times are exhausted/trampled — block entirely
        # Guard against None/0: only block if RS_TOUCH_HARD_CAP is set to a real value
        if RS_TOUCH_HARD_CAP is not None and touch_count > RS_TOUCH_HARD_CAP:
            nearest_support = None
        else:
            recency = best_support_recency
            bounces = _bounce_confirmation(candles, level, 'LONG', atr_value=atr)
            broken  = _level_recently_broken(candles, level, direction='support')
            atr_dist = best_support_dist / atr_pct if atr_pct > 0 else RS_ATR_DIST_FALLBACK

            # Bounce confirmation is a HARD GATE for the normal bounce path — price must
            # bounce off the level to fire. A signal without a bounce is just "price near a
            # level" with no confirmation that the level is active.
            # The broken-level check runs INDEPENDENTLY — broken levels are evaluated
            # regardless of bounce status (broken-path is not gated by bounce confirmation).

            # Reclassify: if a broken support has since recovered above the level, it's no
            # longer acting as broken resistance — treat it as a bounce LONG instead.
            if broken and price > level:
                broken  = False   # reclassify: level is now supporting again
                # Re-validate: reclassified bounce must still pass bounce confirmation
                bounces = _bounce_confirmation(candles, level, 'LONG', atr_value=atr)

            if broken:
                # Support was breached — fire SHORT in the direction of the break.
                # RS_BROKEN_SHORT_ENABLED = False: disable this path — broken support SHORT
                # is a counter-trend trap (29% WR in sample), price often continues up.
                # Better path: broken support → LONG on recovery instead (caught above).
                if not RS_BROKEN_SHORT_ENABLED:
                    nearest_support = None
                else:
                    confidence = _compute_confidence(atr_pct, best_support_dist, touch_count, bounces=bounces, recency_score=recency)
                    if regime == 'LONG_BIAS' and regime_conf > 50:
                        confidence = confidence * 0.80
                    elif regime == 'NEUTRAL' and regime_conf > 55:
                        confidence = confidence * 0.85
                    source = f'{RS_SOURCE_PREFIX}-s-broken'
                    signal = {
                        'direction':  'SHORT',
                        'confidence': confidence,
                        'level':      level,
                        'source':     source,
                        'value':      float(confidence),
                        'atr_dist':   atr_dist,
                        'touches':    touch_count,
                        'recency_score': recency,
                        'bounce':     False,
                    }
            elif bounces:
                # Normal support bounce — price near support, bouncing upward.
                # Bounce confirmation is required for this path (hard gate).
                confidence = _compute_confidence(atr_pct, best_support_dist, touch_count, bounces, recency)
                # Counter-regime penalty: 20% haircut for SHORT_BIAS + LONG
                if regime == 'SHORT_BIAS' and regime_conf > 50:
                    confidence = confidence * 0.80
                # NEUTRAL penalty: 15% haircut
                elif regime == 'NEUTRAL' and regime_conf > 55:
                    confidence = confidence * 0.85
                source = f'{RS_SOURCE_PREFIX}-s{touch_count}'
                signal = {
                    'direction':  'LONG',
                    'confidence': confidence,
                    'level':      level,
                    'source':     source,
                    'value':      float(confidence),
                    'atr_dist':   atr_dist,
                    'touches':    touch_count,
                    'recency_score': recency,
                    'bounce':     bounces,
                }
            else:
                # broken=False and bounces=False — level is near but not bouncing and not broken.
                # Signal stays None; this is a valid "no signal" outcome.
                pass

    # Check SHORT: price near resistance level + rejection
    if nearest_resistance is not None:
        level, touch_count = nearest_resistance
        # Hard cap: levels touched too many times are exhausted/trampled — block entirely
        # Guard against None/0: only block if RS_TOUCH_HARD_CAP is set to a real value
        if RS_TOUCH_HARD_CAP is not None and touch_count > RS_TOUCH_HARD_CAP:
            nearest_resistance = None
        else:
            recency = best_resist_recency
            bounces = _bounce_confirmation(candles, level, 'SHORT', atr_value=atr)
            broken  = _level_recently_broken(candles, level, direction='resistance')
            atr_dist = best_resist_dist / atr_pct if atr_pct > 0 else RS_ATR_DIST_FALLBACK

            # Bounce confirmation is a HARD GATE for the normal bounce path — price must
            # bounce off the level to fire. Same logic as support path above.
            # The broken-level check runs INDEPENDENTLY — broken levels are evaluated
            # regardless of bounce status (broken-path is not gated by bounce confirmation).
            cand_signal = None  # always in scope below

            # Reclassify: if a broken resistance has since fallen back below the level,
            # it's no longer acting as broken support — treat it as a resistance SHORT.
            if broken and price < level:
                broken = False   # reclassify: level is now resistance again
                # Re-validate: a reclassified bounce must still pass bounce confirmation
                # (don't just assume bounces=True — verify the next candle confirmed rejection)
                bounces = _bounce_confirmation(candles, level, 'SHORT', atr_value=atr)

            if broken:
                # Resistance was breached — fire LONG in the direction of the break.
                # RS_BROKEN_RESISTANCE_LONG_ENABLED = False: disable this path — broken
                # resistance LONG is a counter-trend trap (BLUR/BRETT loss pattern). Price
                # broke through resistance, expecting bounce, but momentum is bearish and
                # price typically continues down.
                if not RS_BROKEN_RESISTANCE_LONG_ENABLED:
                    nearest_resistance = None
                    cand_signal = None
                else:
                    confidence = _compute_confidence(atr_pct, best_resist_dist, touch_count, bounces=bounces, recency_score=recency)
                    if regime == 'SHORT_BIAS' and regime_conf > 50:
                        confidence = confidence * 0.80
                    elif regime == 'NEUTRAL' and regime_conf > 55:
                        confidence = confidence * 0.85
                    source = f'{RS_SOURCE_PREFIX}-r-broken'
                    cand_signal = {
                        'direction':  'LONG',
                        'confidence': confidence,
                        'level':      level,
                        'source':     source,
                        'value':      float(confidence),
                        'atr_dist':   atr_dist,
                        'touches':    touch_count,
                        'recency_score': recency,
                        'bounce':     False,
                    }
            elif bounces:
                # Normal resistance rejection — price near resistance, bouncing downward.
                # Bounce confirmation is required for this path (hard gate).
                # NOTE: unlike the broken path, bounce SHORT is NOT gated by
                # RS_BROKEN_RESISTANCE_LONG_ENABLED — bounce SHORT is a valid mean-reversion
                # entry that should fire independently of whether broken-resistance LONG is enabled.
                confidence = _compute_confidence(atr_pct, best_resist_dist, touch_count, bounces, recency)
                # Counter-regime penalty: 20% haircut for LONG_BIAS + SHORT
                if regime == 'LONG_BIAS' and regime_conf > 50:
                    confidence = confidence * 0.80
                # NEUTRAL penalty: 15% haircut
                elif regime == 'NEUTRAL' and regime_conf > 55:
                    confidence = confidence * 0.85
                source = f'{RS_SOURCE_PREFIX}-r{touch_count}'
                cand_signal = {
                    'direction':  'SHORT',
                    'confidence': confidence,
                    'level':      level,
                    'source':     source,
                    'value':      float(confidence),
                    'atr_dist':   atr_dist,
                    'touches':    touch_count,
                    'recency_score': recency,
                    'bounce':     bounces,
                }
                # Only update signal if cand_signal was actually created (not blocked by killswitch)
                # AND either no signal exists yet OR cand_signal has strictly higher confidence
                if cand_signal is not None and (signal is None or cand_signal['confidence'] > signal['confidence']):
                    signal = cand_signal

    return signal


# ── Candle data (price_history — live 1m prices, updated every minute) ─────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'
_STALE_SENTINEL = object()  # marker for stale data (distinguishable from [])

def _get_candles_1m(token: str, lookback: int = RS_LOOKBACK_CANDLES) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices — the ONLY reliable
    source for live signal generation. timestamps are in SECONDS (Unix time).

    Returns list of {close} dicts, oldest first.
    Freshness guard: returns [] if most recent price is > 2 minutes old.
    """
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

        # Freshness guard — skip if most recent price is stale
        most_recent_ts = rows[-1][0]  # seconds
        if (time.time() - most_recent_ts) > 120:
            print(f"  [rs] {token}: stale price_history (last ts {most_recent_ts}, skipping)")
            return _STALE_SENTINEL

        # Synthesize ohlcv — price_history is close-only; open/high/low = close
        # This is acceptable: ATR uses |close[i]-close[i-1]| approximation,
        # and swing highs/lows will be detected from close values.
        return [{'open': r[1], 'high': r[1], 'low': r[1], 'close': r[1]} for r in rows]

    except Exception as e:
        print(f"  [rs] price_history error for {token}: {e}")
        return []


# ── Main scanner ────────────────────────────────────────────────────────────────

def scan_rs_signals(prices_dict: dict) -> tuple[int, list[str]]:
    """Scan pre-filtered tokens for support/resistance signals and write to DB.

    Guards applied here (no caller assumptions):
    - RS_ENABLED kill-switch
    - LONG_BLACKLIST / SHORT_BLACKLIST from hermes_constants
    - RS_PLUS_ENABLED / RS_MINUS_ENABLED per-direction kill-switches
    - RS_COOLDOWN_HOURS per-token cooldown enforcement

    Args:
        prices_dict: token -> {'price': float, ...}  (pre-filtered by caller)

    Returns:
        tuple[int, list[str]] — (count of signals written, list of token names that fired)
    """
    from hermes_constants import RS_ENABLED, LONG_BLACKLIST, SHORT_BLACKLIST, RS_COOLDOWN_HOURS, RS_SIGNAL_TYPE
    if not RS_ENABLED:
        return 0, []

    from signal_schema import add_signal, _get_conn, _runtime
    added = 0
    signaled_tokens = []

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Get candles from local price_history (4700 candles/token available)
        candles = _get_candles_1m(token, lookback=RS_LOOKBACK_CANDLES)
        # Distinguish stale data from genuinely absent levels
        if candles is _STALE_SENTINEL:
            continue
        if not candles or len(candles) < RS_LEVEL_LOOKBACK * 2:
            continue

        sig = detect_rs_signal(token, candles, price)
        if sig is None:
            continue

        # ── Per-direction kill-switch ─────────────────────────────────────────
        from hermes_constants import RS_PLUS_ENABLED, RS_MINUS_ENABLED
        if sig['direction'] == 'LONG' and not RS_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not RS_MINUS_ENABLED:
            continue

        # ── Blacklist guard ──────────────────────────────────────────────────
        token_upper = token.upper()
        if sig['direction'] == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if sig['direction'] == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        # ── Cooldown enforcement (RS_COOLDOWN_HOURS) ─────────────────────────────
        # Skip if a recent RS signal of the same direction already fired
        if RS_COOLDOWN_HOURS and RS_COOLDOWN_HOURS > 0:
            import datetime
            cooldown_cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=RS_COOLDOWN_HOURS)
            cooldown_cutoff_str = cooldown_cutoff.strftime('%Y-%m-%d %H:%M:%S')
            try:
                conn_cd = _get_conn(_runtime())
                cur_cd = conn_cd.cursor()
                cur_cd.execute("""
                    SELECT created_at FROM signal_history
                    WHERE token=? AND direction=? AND created_at > ?
                    ORDER BY created_at DESC LIMIT 1
                """, (token_upper, sig['direction'].upper(), cooldown_cutoff_str))
                row_cd = cur_cd.fetchone()
                conn_cd.close()
                if row_cd is not None:
                    continue  # within cooldown window
            except Exception:
                pass  # non-fatal: skip cooldown check if DB query fails

        sid = add_signal(
            token=token.upper(),
            direction=sig['direction'],
            signal_type=RS_SIGNAL_TYPE,
            source=sig['source'],
            confidence=sig['confidence'],
            value=float(sig['confidence']),
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
        )
        if sid:
            added += 1
            signaled_tokens.append(token.upper())
            level_pct = abs(price - sig['level']) / price * 100.0
            print(f'  {sig["direction"]:5s} {token:8s} conf={sig["confidence"]:3.0f}% '
                  f'level={sig["level"]:.6f} ({level_pct:.3f}% off) '
                  f'touches={sig["touches"]} bounce={sig["bounce"]} '
                  f'[{sig["source"]}]')

    return added, signaled_tokens


# ── Pipeline entry point ──────────────────────────────────────────────────────
def run(prices_dict=None):
    """Wrapper for signals_runner dispatcher.
    signals_runner calls getattr(mod, 'run', None) — this is the entry point.
    Dispatches to scan_rs_signals with the prices dict.

    Returns:
        tuple[int, list[str]]: (count of signals written, list of token names that fired)
    """
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_rs_signals(prices_dict)


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from signal_schema import get_all_latest_prices, init_db

    init_db()
    prices = get_all_latest_prices()

    # Focus on liquid tokens for test
    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[rs_signals] Testing on {len(test_tokens)} tokens...")
    n, tokens = scan_rs_signals(test_tokens)
    print(f"[rs_signals] Done. {n} signals emitted.")
