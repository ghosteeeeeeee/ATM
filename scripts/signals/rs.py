# Migrated from ../rs_signals.py — see signals/__init__.py registry
#!/usr/bin/env python3
"""
rs_signals.py — Support & Resistance Signal Scanner for Hermes.

Detects swing-structure support and resistance levels from 1m OHLCV candles,
fires LONG when price bounces from a support level, SHORT when rejected from
resistance. Primary signal — competes equally in hot-set scoring.

Architecture:
  - Reads 1m candles from price_history via signal_schema.get_ohlcv_1m()
  - Computes ATR(14) for volatility-normalized level proximity
  - Finds swing highs/lows in a rolling window → clusters into structural levels
  - Fires when price is within RS_PROXIMITY_K ATRs of a level with bounce confirmation
  - Writes via signal_schema.add_signal() (blacklists, merge logic applied)

Signal types:
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

# ── Constants ─────────────────────────────────────────────────────────────────

RS_LOOKBACK_CANDLES   = 4700  # max available in price_history (~3+ days of 1m)
RS_LEVEL_LOOKBACK     = 20    # swing high/low detection window (candles)
RS_ATR_PERIOD         = 14    # ATR lookback period
RS_CLUSTER_ATR        = 0.50  # cluster levels within 0.50 * ATR of each other
RS_PROXIMITY_K        = 0.70 # fire if price is within 0.70 * ATR of a level (tightened from 1.00)
RS_MIN_TOUCHES        = 3     # minimum historical touches to be a valid level (lowered from 8)
RS_COOLDOWN_HOURS     = 4     # cooldown between RS signals per token+direction
RS_SIGNAL_TYPE        = 'support_resistance'
RS_SOURCE_PREFIX      = 'rs'
RS_MIN_CONFIDENCE     = 50    # global floor (matches signal_schema minimum)
RS_MAX_CONFIDENCE     = 88    # cap — R&S is structural, not momentum

# Recency tuning: touches in last N candles count as "recent"
# Low-touch fresh levels (1-20 touches) have 44% WR and +0.80% avg
# vs ancient levels (100+ touches) with 40% WR and +0.03% avg
RS_RECENCY_WINDOW     = 200   # lookback for recency-weighted touch count
RS_RECENCY_BOOST_K    = 3.0   # multiplier: each recent touch counts as K ancient touches

# Bounce confirmation: what counts as a "bounce" off a level?
# A bounce means price got close to the level and recovered.
# We check the last RS_LEVEL_LOOKBACK candles for this behavior.
_BOUNCE_LOOKBACK      = 6     # candles to check for bounce confirmation
_BOUNCE_THRESH_ATR     = 1.00  # touch: price came within 1.00 * ATR(14) of the level

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

    swing_highs = [(i, highs[i]) for i in range(window, n - window)
                   if highs[i] == roll_high[i]]
    swing_lows  = [(i, lows[i])  for i in range(window, n - window)
                   if lows[i]  == roll_min[i]]

    return swing_highs, swing_lows


def _cluster_levels(levels: list, cluster_atr_pct: float) -> list:
    """Cluster price levels that are within cluster_atr_pct of each other.
    Each cluster is replaced by its average price weighted by touch count.

    Args:
        levels: list of (price, touch_count) tuples
        cluster_atr_pct: clustering threshold as % of price (e.g. 0.003 = 0.3%)

    Returns:
        list of (clustered_price, total_touch_count)
    """
    if not levels:
        return []
    # Sort by price
    sorted_levels = sorted(levels, key=lambda x: x[0])
    clusters = []
    current_cluster = [sorted_levels[0]]
    for level in sorted_levels[1:]:
        price, count = level
        cluster_price = sum(p for p, _ in current_cluster) / len(current_cluster)
        # If within cluster threshold of the cluster center, add to cluster
        if abs(price - cluster_price) / cluster_price * 100.0 <= cluster_atr_pct:
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
                          lookback: int = _BOUNCE_LOOKBACK) -> bool:
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
        thresh = atr_value * _BOUNCE_THRESH_ATR

    if direction == 'LONG':
        # Support bounce: close touched level, then either:
        #   (a) touch candle was bullish (close > open), OR
        #   (b) next candle moved >0.025% higher (partial follow-through)
        for i, c in enumerate(recent):
            if abs(c['close'] - level) < thresh:
                # Condition (a): touch candle itself was bullish
                if c['close'] > c['open']:
                    return True
                # Condition (b): check next candle for partial follow-through
                if i + 1 < len(recent):
                    next_close = recent[i + 1]['close']
                    if next_close > c['close'] * 1.00025:  # >0.025% upward
                        return True
        return False

    else:  # SHORT
        # Resistance rejection: close touched level, then either:
        #   (a) touch candle was bearish (close < open), OR
        #   (b) next candle moved >0.025% lower (partial follow-through)
        for i, c in enumerate(recent):
            if abs(c['close'] - level) < thresh:
                # Condition (a): touch candle itself was bearish
                if c['close'] < c['open']:
                    return True
                # Condition (b): check next candle for partial follow-through
                if i + 1 < len(recent):
                    next_close = recent[i + 1]['close']
                    if next_close < c['close'] * 0.99975:  # >0.025% downward
                        return True
        return False


# ── ATR-distance guard ──────────────────────────────────────────────────────────
# The 0.3–0.6 ATR band is empirically a trap in backtesting (avg PnL = -0.095%).
# Levels this close feel "near" but price hasn't committed. Reject that band.
# _RS_ATR_BAND_SOFT_MIN  = 0.30  # below this: too close to call (could be AT the level)
# _RS_ATR_BAND_SOFT_MAX  = 0.60  # above this: comfortably outside, safe
# (DEPRECATED 2026-05-06 — removed ATR band filter, levels in this range are valid)


def _level_recently_broken(candles: list, level: float, lookback: int = 20) -> bool:
    """Return True if price crossed *through* the level in the last `lookback` candles.

    price_history is close-only (open=high=low=close for every candle), so we detect
    a level crossing by checking if two successive candle closes are on opposite
    sides of the level:
      - Resistance broken: prev_close < level < curr_close  (price crossed above)
      - Support broken:    prev_close > level > curr_close  (price crossed below)

    A candle closing ON the level (prev_close < level < curr_close with curr_close
    equal to level) cannot occur with close-only data, so this is a pure close-crossing
    check between consecutive candles.
    """
    if len(candles) < lookback:
        return False

    recent = candles[-lookback:]
    for i in range(1, len(recent)):
        prev_close = recent[i - 1]['close']
        curr_close = recent[i]['close']
        # Resistance broken: price closed above from below
        if prev_close < level < curr_close:
            return True
        # Support broken: price closed below from above
        if prev_close > level > curr_close:
            return True
    return False


def _build_level_touches(candles_or_highs_lows, level: float = None,
                         atr_value: float = None,
                         return_recency: bool = False) -> int:
    """Count touches using NumPy fast path or legacy loop.

    Fast path (preferred): pass (highs_array, lows_array) as first arg.
    Legacy path: pass candles list + level + window.

    Uses ATR-based threshold so touch counting is volatility-normalized:
    - price_history is close-only (open=high=low=close for every candle)
    - a "touch" = any candle's close within _BOUNCE_THRESH_ATR * ATR(14) of the level
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
            threshold = atr_value * _BOUNCE_THRESH_ATR
        else:
            # Fallback: ~0.15% of price (old hardcoded behavior)
            threshold = abs(level) * 0.0015
        touch_mask = ((np.abs(highs - level) < threshold) |
                      (np.abs(lows  - level) < threshold))
        total = int(touch_mask.sum())

        if not return_recency:
            return total

        # Recency-weighted score: recent touches + K * ancient touches
        recent_cutoff = RS_RECENCY_WINDOW
        recency_touches = int(touch_mask[-recent_cutoff:].sum()) if n >= recent_cutoff else total
        ancient_touches = total - recency_touches
        recency_score = recency_touches + RS_RECENCY_BOOST_K * ancient_touches
        return total, recency_score

    # Legacy path: list of dict candles
    candles = candles_or_highs_lows
    if atr_value is not None and atr_value > 0:
        threshold = atr_value * _BOUNCE_THRESH_ATR
    else:
        threshold = abs(level) * 0.0015
    count = 0
    for c in candles:
        low_touch = abs(c['low'] - level)
        if low_touch < threshold:
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
        recent_fraction = min(1.0, (recency_score - touch_count) / (recency_score + 1e-9))
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

    if not r_levels and not s_levels:
        return None

    # Find the nearest valid level for each direction
    # For best level: use recency_score (fresh levels prioritized over ancient ones)
    # fall back to touch_count for display purposes
    nearest_support    = None
    nearest_resistance  = None
    best_support_dist   = float('inf')
    best_resist_dist    = float('inf')
    best_support_recency = 0.0
    best_resist_recency  = 0.0

    for level, touch_count in s_levels:
        if touch_count < RS_MIN_TOUCHES:
            continue
        dist_pct = abs(price - level) / price * 100.0
        recency = recency_by_level.get(level, 0)
        if _price_near_level(price, level, atr_pct) and dist_pct < best_support_dist:
            best_support_dist = dist_pct
            best_support_recency = recency
            nearest_support = (level, touch_count)

    for level, touch_count in r_levels:
        if touch_count < RS_MIN_TOUCHES:
            continue
        dist_pct = abs(price - level) / price * 100.0
        recency = recency_by_level.get(level, 0)
        if _price_near_level(price, level, atr_pct) and dist_pct < best_resist_dist:
            best_resist_dist = dist_pct
            best_resist_recency = recency
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
        recency = best_support_recency
        bounces = _bounce_confirmation(candles, level, 'LONG', atr_value=atr)
        broken  = _level_recently_broken(candles, level)
        atr_dist = best_support_dist / atr_pct if atr_pct > 0 else 999

        # Gate: reject recently-broken levels (level invalidation)
        if broken:
            nearest_support = None
        else:
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

    # Check SHORT: price near resistance level + rejection
    if nearest_resistance is not None:
        level, touch_count = nearest_resistance
        recency = best_resist_recency
        bounces = _bounce_confirmation(candles, level, 'SHORT', atr_value=atr)
        broken  = _level_recently_broken(candles, level)
        atr_dist = best_resist_dist / atr_pct if atr_pct > 0 else 999

        # Gate: reject recently-broken levels (level invalidation)
        if broken:
            nearest_resistance = None
        else:
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
                'bounce':     bounces,
            }
            # Use SHORT if it has higher confidence; otherwise keep LONG
            if signal is None or cand_signal['confidence'] > signal['confidence']:
                signal = cand_signal

    return signal


# ── Candle data (price_history — live 1m prices, updated every minute) ─────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

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
            return []

        # Synthesize ohlcv — price_history is close-only; open/high/low = close
        # This is acceptable: ATR uses |close[i]-close[i-1]| approximation,
        # and swing highs/lows will be detected from close values.
        return [{'open': r[1], 'high': r[1], 'low': r[1], 'close': r[1]} for r in rows]

    except Exception as e:
        print(f"  [rs] price_history error for {token}: {e}")
        return []


# ── Main scanner ────────────────────────────────────────────────────────────────

def scan_rs_signals(prices_dict: dict) -> tuple[int, list[str]]:
    from hermes_constants import RS_ENABLED
    if not RS_ENABLED:
        return 0
    """Scan pre-filtered tokens for support/resistance signals and write to DB.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here. This function
    focuses purely on R&S level detection and DB writing.

    Args:
        prices_dict: token -> {'price': float, ...}  (pre-filtered by caller)

    Returns:
        tuple[int, list[str]] — (count of signals written, list of token names that fired)
    """
    from signal_schema import add_signal

    added = 0
    signaled_tokens = []

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Get candles from local price_history (4700 candles/token available)
        candles = _get_candles_1m(token, lookback=RS_LOOKBACK_CANDLES)
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

        sid = add_signal(
            token=token.upper(),
            direction=sig['direction'],
            signal_type=RS_SIGNAL_TYPE,
            source=sig['source'],
            confidence=sig['confidence'],
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
    """
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_rs_signals(prices_dict)


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import get_all_latest_prices, init_db

    init_db()
    prices = get_all_latest_prices()

    # Focus on liquid tokens for test
    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[rs_signals] Testing on {len(test_tokens)} tokens...")
    n = scan_rs_signals(test_tokens)
    print(f"[rs_signals] Done. {n} signals emitted.")
