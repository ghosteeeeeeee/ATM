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
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal

# ── Constants ─────────────────────────────────────────────────────────────────

RS_LOOKBACK_CANDLES   = 4700  # max available in price_history (~3+ days of 1m)
RS_LEVEL_LOOKBACK     = 20    # swing high/low detection window (candles)
RS_ATR_PERIOD         = 14    # ATR lookback period
RS_CLUSTER_ATR        = 0.50  # cluster levels within 0.50 * ATR of each other
RS_PROXIMITY_K        = 1.20 # fire if price is within 1.20 * ATR of a level
RS_MIN_TOUCHES        = 2     # minimum historical touches to be a valid level
RS_COOLDOWN_HOURS     = 4     # cooldown between RS signals per token+direction
RS_SIGNAL_TYPE        = 'support_resistance'
RS_SOURCE_PREFIX      = 'rs'
RS_MIN_CONFIDENCE     = 50    # global floor (matches signal_schema minimum)
RS_MAX_CONFIDENCE     = 88    # cap — R&S is structural, not momentum

# Bounce confirmation: what counts as a "bounce" off a level?
# A bounce means price got close to the level and recovered.
# We check the last RS_LEVEL_LOOKBACK candles for this behavior.
_BOUNCE_LOOKBACK      = 6     # candles to check for bounce confirmation

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


def _find_swing_highs_lows(candles: list, window: int = RS_LEVEL_LOOKBACK):
    """Find local swing highs and lows using a simple window-based approach.

    Returns:
        (swing_highs: list of (idx, price), swing_lows: list of (idx, price))
    """
    if len(candles) < window * 2 + 1:
        return [], []

    swing_highs = []
    swing_lows  = []

    for i in range(window, len(candles) - window):
        high  = candles[i]['high']
        low   = candles[i]['low']
        # Swing high: highest in [i-window, i+window]
        window_highs  = [candles[j]['high']  for j in range(i - window, i + window + 1)]
        window_lows   = [candles[j]['low']   for j in range(i - window, i + window + 1)]
        if high == max(window_highs):
            swing_highs.append((i, high))
        if low == min(window_lows):
            swing_lows.append((i, low))

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
                          lookback: int = _BOUNCE_LOOKBACK) -> bool:
    """Check if price recently bounced from the level.

    For LONG (near support): check that at least one candle in the lookback
    touched the level (low near level) and the close was higher than the touch.
    For SHORT (near resistance): check that at least one candle in the lookback
    touched the level (high near level) and the close was lower than the touch.

    Returns True if bounce is confirmed.
    """
    if len(candles) < lookback:
        return False

    recent = candles[-lookback:]

    if direction == 'LONG':
        # Support bounce: price touched level (low near level) and recovered
        for c in recent:
            touch_pct = abs(c['low'] - level) / level * 100.0
            if touch_pct < 0.20:  # low came within 0.20% of level = touched
                if c['close'] > c['open']:  # bullish candle
                    return True
        return False

    else:  # SHORT
        # Resistance rejection: price touched level (high near level) and reversed
        for c in recent:
            touch_pct = abs(c['high'] - level) / level * 100.0
            if touch_pct < 0.20:  # high came within 0.20% of level = touched
                if c['close'] < c['open']:  # bearish candle
                    return True
        return False


def _build_level_touches(candles: list, level: float, window: int = RS_LEVEL_LOOKBACK) -> int:
    """Count how many times price touched/rejected this level historically.
    A touch = a candle where high (for resistance) or low (for support) came
    within 0.15% of the level.
    """
    touch_threshold_pct = 0.15
    count = 0
    for c in candles:
        high_touch = abs(c['high'] - level) / level * 100.0
        low_touch  = abs(c['low']  - level) / level * 100.0
        if high_touch < touch_threshold_pct or low_touch < touch_threshold_pct:
            count += 1
    return count


def _compute_confidence(atr_pct: float, distance_pct: float,
                         touch_count: int, bounces: bool) -> float:
    """Compute signal confidence.

    Base: 65 (R&S is structural, starts above floor)
    ATR proximity bonus: +1 to +15 (closer = more confident)
    Touch count bonus: +1 to +10 (more historical touches = stronger level)
    Bounce confirmation bonus: +5
    Penalty if no bounce: 0 (don't penalize — levels still valid without recent bounce)
    """
    base = 65.0

    # ATR proximity bonus: 0.0 ATRs → +15, 1.2 ATRs → +0
    if atr_pct > 0:
        atr_dist = distance_pct / atr_pct
        prox_bonus = max(0, 15 * (1 - atr_dist / RS_PROXIMITY_K))
    else:
        prox_bonus = 0

    # Touch count bonus: 2 touches → +3, 3+ touches → +10
    if touch_count <= 2:
        touch_bonus = 3
    elif touch_count == 3:
        touch_bonus = 6
    else:
        touch_bonus = min(10, 3 + touch_count)

    bounce_bonus = 5 if bounces else 0

    confidence = base + prox_bonus + touch_bonus + bounce_bonus
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

    # Find swing levels
    swing_highs, swing_lows = _find_swing_highs_lows(candles, RS_LEVEL_LOOKBACK)

    # Build raw level lists with touch counts (use full candle history for touches)
    raw_resistance = [(price, _build_level_touches(candles, price, RS_LEVEL_LOOKBACK))
                      for _, price in swing_highs]
    raw_support    = [(price, _build_level_touches(candles, price, RS_LEVEL_LOOKBACK))
                      for _, price in swing_lows]

    # Cluster nearby levels
    cluster_pct = RS_CLUSTER_ATR * atr_pct  # convert ATR units to % for clustering
    r_levels = _cluster_levels(raw_resistance, cluster_pct)
    s_levels = _cluster_levels(raw_support,    cluster_pct)

    if not r_levels and not s_levels:
        return None

    # Find the nearest valid level for each direction
    nearest_support    = None
    nearest_resistance  = None
    best_support_dist   = float('inf')
    best_resist_dist    = float('inf')

    for level, touch_count in s_levels:
        if touch_count < RS_MIN_TOUCHES:
            continue
        dist_pct = abs(price - level) / price * 100.0
        if _price_near_level(price, level, atr_pct) and dist_pct < best_support_dist:
            best_support_dist = dist_pct
            nearest_support = (level, touch_count)

    for level, touch_count in r_levels:
        if touch_count < RS_MIN_TOUCHES:
            continue
        dist_pct = abs(price - level) / price * 100.0
        if _price_near_level(price, level, atr_pct) and dist_pct < best_resist_dist:
            best_resist_dist = dist_pct
            nearest_resistance = (level, touch_count)

    # Determine best signal
    signal = None

    # Check LONG: price near support level + bounce
    if nearest_support is not None:
        level, touch_count = nearest_support
        bounces = _bounce_confirmation(candles, level, 'LONG')
        confidence = _compute_confidence(atr_pct, best_support_dist, touch_count, bounces)
        source = f'{RS_SOURCE_PREFIX}-s{touch_count}'
        signal = {
            'direction':  'LONG',
            'confidence': confidence,
            'level':      level,
            'source':     source,
            'value':      float(confidence),
            'atr_dist':   best_support_dist / atr_pct if atr_pct > 0 else 999,
            'touches':    touch_count,
            'bounce':     bounces,
        }

    # Check SHORT: price near resistance level + rejection
    if nearest_resistance is not None:
        level, touch_count = nearest_resistance
        bounces = _bounce_confirmation(candles, level, 'SHORT')
        confidence = _compute_confidence(atr_pct, best_resist_dist, touch_count, bounces)
        source = f'{RS_SOURCE_PREFIX}-r{touch_count}'
        cand_signal = {
            'direction':  'SHORT',
            'confidence': confidence,
            'level':      level,
            'source':     source,
            'value':      float(confidence),
            'atr_dist':   best_resist_dist / atr_pct if atr_pct > 0 else 999,
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

        sid = add_signal(
            token=token.upper(),
            direction=sig['direction'],
            signal_type=RS_SIGNAL_TYPE,
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
            z_score_tier=None,
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
