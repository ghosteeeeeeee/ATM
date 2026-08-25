#!/usr/bin/env python3
"""risk_reward_engine.py — Structural R:R evaluation gate.

Replaces the simple rr_gate() with a composite evaluation that considers:
1. Multi-source S/R levels (candle swings + order book + liquidation clusters)
2. Volatility width (ATR% + Bollinger Band width)
3. Liquidity proximity (distance to nearest cluster)
4. Structural reward (target = nearest S/R, not arbitrary TP)

Data sources (all existing, no new API calls):
- volatility_gate.get_atr_pct() — ATR% from 1h candles
- candles.db — 5m candles for swing detection + BB width
- liquidation_clusters.json — order book S/R + liquidation clusters
- rs_signals — swing high/low detection + clustering

Usage:
    from risk_reward_engine import evaluate_rr
    result = evaluate_rr(token, direction, price, candles_5m=None)
    if not result['pass']:
        continue

CLI:
    python3 risk_reward_engine.py ETH LONG 3500.0
    python3 risk_reward_engine.py --quick SOL SHORT 180.0
    python3 risk_reward_engine.py --scan
"""
import sys
import os
import time
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, CANDLES_DB, ATR_CACHE_FILE

# ── Imports from existing modules ───────────────────────────────────────────
import hermes_constants as hc
from volatility_gate import get_atr_pct, classify_volatility

# rs_signals imports (swing detection + clustering)
try:
    from rs_signals import _find_swing_highs_lows, _cluster_levels, _build_level_touches
    _HAS_RS_SIGNALS = True
except ImportError:
    _HAS_RS_SIGNALS = False

# liquidation_map imports (order book S/R + clusters)
try:
    from liquidation_map import get_sr_levels, load_clusters
    _HAS_LIQ_MAP = True
except ImportError:
    _HAS_LIQ_MAP = False

# ── Cache ───────────────────────────────────────────────────────────────────
_sr_cache = {}     # token -> (timestamp, sr_map)
_vol_cache = {}    # token -> (timestamp, vol_width)
_liq_cache = None  # global liquidation data (refreshed per call)
_liq_cache_ts = 0
_log_dedup = {}    # key -> last_log_ts (prevent spam)
_LOG_DEDUP_TTL = 60  # don't repeat same log within 60s

_CACHE_TTL = getattr(hc, 'RR_ENGINE_CACHE_TTL', 300)


def _log(msg):
    print(f"[rr-engine] {msg}", flush=True)


# ── S/R Map Builder ─────────────────────────────────────────────────────────

def _get_candles_5m(token, limit=300):
    """Fetch 5m candles from candles.db. Returns list of dicts or empty list."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

    if not rows:
        return []

    # Reverse to chronological (oldest first)
    rows.reverse()
    return [
        {'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]}
        for r in rows
    ]


def _build_candle_sr(candles_5m, atr_pct, lookback=None):
    """Build S/R levels from candle swing detection.

    Returns list of {price, touches, type, source} sorted by proximity to last price.
    """
    if not _HAS_RS_SIGNALS:
        return []

    if lookback is None:
        lookback = getattr(hc, 'RR_ENGINE_SR_LOOKBACK', 300)

    if not candles_5m or len(candles_5m) < 30:
        return []

    # Use last N candles for swing detection
    use_candles = candles_5m[-lookback:] if len(candles_5m) > lookback else candles_5m

    swing_highs, swing_lows = _find_swing_highs_lows(use_candles, window=20)
    if not swing_highs and not swing_lows:
        return []

    # Extract prices for clustering
    high_prices = [(h[1], 1) for h in swing_highs]
    low_prices = [(l[1], 1) for l in swing_lows]

    # Cluster nearby levels
    cluster_atr_pct = getattr(hc, 'RR_ENGINE_SR_CLUSTER_ATR', 1.0)
    clustered_highs = _cluster_levels(high_prices, cluster_atr_pct)
    clustered_lows = _cluster_levels(low_prices, cluster_atr_pct)

    current_price = candles_5m[-1]['close']
    levels = []

    for price, touches in clustered_highs:
        dist_pct = abs(price - current_price) / current_price * 100
        level_type = 'resistance' if price > current_price else 'support'
        levels.append({
            'price': price,
            'touches': touches,
            'type': level_type,
            'source': 'CANDLE',
            'distance_pct': dist_pct,
        })

    for price, touches in clustered_lows:
        dist_pct = abs(price - current_price) / current_price * 100
        level_type = 'resistance' if price > current_price else 'support'
        levels.append({
            'price': price,
            'touches': touches,
            'type': level_type,
            'source': 'CANDLE',
            'distance_pct': dist_pct,
        })

    # Filter by min touches
    min_touches = getattr(hc, 'RR_ENGINE_SR_MIN_TOUCHES', 3)
    levels = [l for l in levels if l['touches'] >= min_touches]

    # Sort by proximity
    levels.sort(key=lambda x: x['distance_pct'])
    return levels


def _build_liq_sr(token):
    """Build S/R levels from liquidation clusters + order book.

    Returns list of {price, strength, type, source, distance_pct}.
    """
    if not _HAS_LIQ_MAP:
        return []

    try:
        book_levels = get_sr_levels(token)
    except Exception:
        book_levels = []

    # Also get liquidation clusters as S/R
    liq_levels = []
    try:
        data = load_clusters()
        clusters = data.get('liquidation_clusters', {}).get(token.upper(), [])
        price = None  # will set from first cluster

        for cl in clusters[:10]:
            dist = abs(cl.get('distance_pct', 999))
            if dist > getattr(hc, 'RR_ENGINE_LIQ_MAX_DIST', 2.0):
                continue

            cl_price = cl.get('price', 0)
            if cl_price <= 0:
                continue

            if price is None:
                price = cl.get('current_price', 0)

            # Cluster below price = support (forced selling creates floor)
            # Cluster above price = resistance (forced buying creates ceiling)
            level_type = 'support' if cl.get('distance_pct', 0) < 0 else 'resistance'

            liq_levels.append({
                'price': cl_price,
                'strength': cl.get('total_size', 0),
                'total_notional': cl.get('total_notional_usd', 0),
                'type': level_type,
                'source': 'LIQUIDATION',
                'distance_pct': dist,
                'position_count': cl.get('count', 0),
                'max_leverage': cl.get('max_leverage', 0),
            })
    except Exception:
        pass

    return book_levels + liq_levels


def _merge_sr_maps(candle_levels, liq_levels, price, atr_pct):
    """Merge candle and liquidation S/R into unified map, sorted by proximity."""
    all_levels = []

    for level in candle_levels:
        all_levels.append(level)

    for level in liq_levels:
        all_levels.append(level)

    # Sort by proximity to current price
    all_levels.sort(key=lambda x: x.get('distance_pct', 999))

    return all_levels


def build_sr_map(token, price, candles_5m=None, atr_pct=None):
    """Build the complete S/R map for a token.

    Returns list of levels sorted by proximity, with candle + liq + book sources.
    """
    # Check cache
    now = time.time()
    cache_key = token.upper()
    if cache_key in _sr_cache:
        cached_ts, cached_map = _sr_cache[cache_key]
        if now - cached_ts < _CACHE_TTL:
            return cached_map

    # Fetch candles if not provided
    if candles_5m is None:
        candles_5m = _get_candles_5m(token)

    # Get ATR% if not provided
    if atr_pct is None:
        atr_pct = get_atr_pct(token)

    # Build candle S/R
    candle_sr = _build_candle_sr(candles_5m, atr_pct)

    # Build liquidation S/R
    liq_sr = _build_liq_sr(token)

    # Merge
    merged = _merge_sr_maps(candle_sr, liq_sr, price, atr_pct)

    # Cache
    _sr_cache[cache_key] = (now, merged)
    return merged


# ── Volatility Width ────────────────────────────────────────────────────────

def _compute_bb_width(closes):
    """Compute Bollinger Band width as a fraction of middle band.

    Returns (width, position) where:
    - width: (upper - lower) / middle (e.g., 0.04 = 4%)
    - position: 0-1, where price sits in the band (0=lower, 1=upper)
    """
    period = getattr(hc, 'RR_ENGINE_BB_PERIOD', 20)
    stddev = getattr(hc, 'RR_ENGINE_BB_STDDEV', 1.8)

    if not closes or len(closes) < period:
        return None, None

    arr = closes[-period:]
    sma = sum(arr) / len(arr)
    if sma <= 0:
        return None, None

    variance = sum((x - sma) ** 2 for x in arr) / len(arr)
    std = variance ** 0.5

    upper = sma + stddev * std
    lower = sma - stddev * std
    width = (upper - lower) / sma

    # Position: 0 = at lower band, 1 = at upper band
    band_range = upper - lower
    if band_range > 0:
        position = (closes[-1] - lower) / band_range
    else:
        position = 0.5

    return width, position


def compute_vol_width(token, candles_5m=None):
    """Compute volatility width metrics.

    Returns dict with atr_pct, atr_regime, bb_width, bb_position, bb_squeeze, energy_score.
    """
    now = time.time()
    cache_key = token.upper()
    if cache_key in _vol_cache:
        cached_ts, cached = _vol_cache[cache_key]
        if now - cached_ts < _CACHE_TTL:
            return cached

    # ATR% from volatility_gate (correctly converts dollar ATR to %)
    atr_pct = get_atr_pct(token)
    if atr_pct is None:
        # Fallback: use ATR_PCT_FALLBACK but classify as NORMAL, not EXTREME
        atr_pct = getattr(hc, 'ATR_PCT_FALLBACK', 0.03) * 100  # convert from fraction to %
        # ATR_PCT_FALLBACK=0.03 means 3%, but classify_volatility expects % value
        # 0.03% < 0.48% → FLAT (safe fallback, not EXTREME)
        if atr_pct > 1.5:
            atr_pct = 0.75  # safe NORMAL fallback

    regime = classify_volatility(atr_pct)

    # Bollinger Band width from 5m candles
    if candles_5m is None:
        candles_5m = _get_candles_5m(token, limit=30)

    closes = [c['close'] for c in candles_5m] if candles_5m else []
    bb_width, bb_position = _compute_bb_width(closes)

    squeeze_thresh = getattr(hc, 'RR_ENGINE_BB_SQUEEZE_THRESH', 0.04)
    bb_squeeze = bb_width is not None and bb_width < squeeze_thresh

    # Energy score: 0-1 composite
    # Higher ATR% = more energy, wider BB = more energy
    atr_score = min(1.0, atr_pct / 2.0)  # normalize: 2% ATR = 1.0
    bb_score = min(1.0, (bb_width or 0) / 0.08) if bb_width else 0.3  # 8% BB = 1.0
    energy_score = 0.6 * atr_score + 0.4 * bb_score

    result = {
        'atr_pct': round(atr_pct, 4),
        'atr_regime': regime,
        'bb_width': round(bb_width, 4) if bb_width else None,
        'bb_position': round(bb_position, 3) if bb_position is not None else None,
        'bb_squeeze': bb_squeeze,
        'energy_score': round(energy_score, 3),
    }

    _vol_cache[cache_key] = (now, result)
    return result


# ── Liquidity Proximity ─────────────────────────────────────────────────────

def compute_liquidity_proximity(token, price, direction, liq_data=None):
    """Evaluate how liquidation clusters affect the trade setup.

    Returns dict with clusters_ahead, clusters_behind, magnet_score, cascade_risk, etc.
    """
    if liq_data is None:
        try:
            liq_data = load_clusters()
        except Exception:
            liq_data = {}

    clusters = liq_data.get('liquidation_clusters', {}).get(token.upper(), [])
    max_dist = getattr(hc, 'RR_ENGINE_LIQ_MAX_DIST', 2.0)

    clusters_ahead = []  # in trade direction (TP magnets)
    clusters_behind = []  # against trade direction (SL risk)

    for cl in clusters:
        dist_pct = cl.get('distance_pct', 999)
        if abs(dist_pct) > max_dist:
            continue

        cl_price = cl.get('price', 0)
        if cl_price <= 0:
            continue

        # For LONG: clusters above = TP magnets, clusters below = SL risk
        # For SHORT: clusters below = TP magnets, clusters above = SL risk
        if direction == 'LONG':
            if cl_price > price:
                clusters_ahead.append(cl)
            else:
                clusters_behind.append(cl)
        else:  # SHORT
            if cl_price < price:
                clusters_ahead.append(cl)
            else:
                clusters_behind.append(cl)

    # Nearest cluster in each direction
    nearest_ahead = min(clusters_ahead, key=lambda c: abs(c.get('distance_pct', 999)), default=None)
    nearest_behind = min(clusters_behind, key=lambda c: abs(c.get('distance_pct', 999)), default=None)

    # Magnet score: 0-1, how much clusters pull price in trade direction
    if nearest_ahead:
        dist = abs(nearest_ahead.get('distance_pct', 5))
        size = nearest_ahead.get('total_size', 0)
        magnet_score = min(1.0, (1.0 - dist / max_dist) * 0.7 + min(1.0, size / 1000000) * 0.3)
    else:
        magnet_score = 0.0

    # Cascade risk: 0-1, risk of hitting cluster before reaching TP
    if nearest_behind:
        dist = abs(nearest_behind.get('distance_pct', 5))
        size = nearest_behind.get('total_size', 0)
        leverage = nearest_behind.get('max_leverage', 1)
        cascade_risk = min(1.0, (1.0 - dist / max_dist) * 0.5 +
                          min(1.0, size / 1000000) * 0.3 +
                          min(1.0, leverage / 50) * 0.2)
    else:
        cascade_risk = 0.0

    # Liquidity bonus (score adjustment)
    magnet_bonus = getattr(hc, 'RR_ENGINE_LIQ_MAGNET_BONUS', 10)
    fight_penalty = getattr(hc, 'RR_ENGINE_LIQ_FIGHT_PENALTY', -10)
    liquidity_bonus = int(magnet_score * magnet_bonus + (1 - cascade_risk) * 0)

    # If cascade risk is high, apply penalty
    if cascade_risk > getattr(hc, 'RR_ENGINE_LIQ_CASCADE_RISK_THRESH', 0.5):
        liquidity_bonus += fight_penalty

    return {
        'clusters_ahead': len(clusters_ahead),
        'clusters_behind': len(clusters_behind),
        'nearest_ahead_dist': round(abs(nearest_ahead.get('distance_pct', 0)), 3) if nearest_ahead else None,
        'nearest_ahead_usd': round(nearest_ahead.get('total_size', 0), 0) if nearest_ahead else None,
        'nearest_behind_dist': round(abs(nearest_behind.get('distance_pct', 0)), 3) if nearest_behind else None,
        'nearest_behind_usd': round(nearest_behind.get('total_size', 0), 0) if nearest_behind else None,
        'magnet_score': round(magnet_score, 3),
        'cascade_risk': round(cascade_risk, 3),
        'liquidity_bonus': liquidity_bonus,
    }


# ── Structural R:R Calculation ─────────────────────────────────────────────

def _get_tp_max_pct(regime):
    """Get regime-adjusted TP max distance."""
    if regime == 'FLAT':
        return getattr(hc, 'RR_ENGINE_TP_MAX_PCT_FLAT', 0.030)
    elif regime == 'HIGH':
        return getattr(hc, 'RR_ENGINE_TP_MAX_PCT_HIGH', 0.020)
    elif regime == 'EXTREME':
        return getattr(hc, 'RR_ENGINE_TP_MAX_PCT_EXTREME', 0.020)
    else:  # NORMAL
        return getattr(hc, 'RR_ENGINE_TP_MAX_PCT_NORMAL', 0.025)


def _get_rr_min(regime):
    """Get regime-adjusted minimum R:R."""
    if regime == 'FLAT':
        return getattr(hc, 'RR_ENGINE_MIN_RATIO_FLAT', 2.5)
    elif regime == 'HIGH':
        return getattr(hc, 'RR_ENGINE_MIN_RATIO_HIGH', 1.5)
    elif regime == 'EXTREME':
        return getattr(hc, 'RR_ENGINE_MIN_RATIO_EXTREME', 2.0)
    else:  # NORMAL
        return getattr(hc, 'RR_ENGINE_MIN_RATIO_NORMAL', 2.0)


def compute_structural_rr(price, direction, sr_map, vol_width, liquidity):
    """Compute R:R based on structural levels.

    SL: ATR-based, extended beyond nearby structural level if needed.
    TP: nearest S/R in trade direction, fallback to ATR-based.
    """
    atr_pct = vol_width.get('atr_pct', 1.0)
    regime = vol_width.get('atr_regime', 'NORMAL')

    # SL distance: ATR-based
    atr_mult = getattr(hc, 'RR_ENGINE_SL_ATR_MULT', 1.0)
    sl_distance_pct = atr_pct * atr_mult / 100.0  # convert ATR% to decimal

    # Ensure minimum SL
    sl_distance_pct = max(sl_distance_pct, getattr(hc, 'ATR_SL_MIN', 0.015))

    # Check if there's a strong structural level between entry and SL
    # If so, extend SL beyond it (avoid getting stopped at a level that should hold)
    structural_buffer = getattr(hc, 'RR_ENGINE_SL_STRUCTURAL_BUFFER', 0.002)
    sl_price = price - (price * sl_distance_pct) if direction == 'LONG' else price + (price * sl_distance_pct)

    # Look for structural levels between entry and SL that could cause stop hunts
    for level in sr_map:
        level_price = level['price']
        level_touches = level.get('touches', level.get('strength', 0))
        if level_touches < 5:
            continue  # weak level, don't adjust

        if direction == 'LONG':
            # Support level between entry and SL — extend SL below it
            if price > level_price > sl_price:
                sl_price = level_price - (price * structural_buffer)
                sl_distance_pct = (price - sl_price) / price
        else:
            # Resistance level between entry and SL — extend SL above it
            if price < level_price < sl_price:
                sl_price = level_price + (price * structural_buffer)
                sl_distance_pct = (sl_price - price) / price

    # TP: find nearest S/R in trade direction
    tp_max = _get_tp_max_pct(regime)
    tp_distance_pct = atr_pct * getattr(hc, 'RR_ENGINE_TP_ATR_MULT', 2.0) / 100.0
    tp_distance_pct = max(tp_distance_pct, getattr(hc, 'RR_ENGINE_TP_MIN_PCT', 0.005))
    tp_distance_pct = min(tp_distance_pct, tp_max)

    tp_price = price + (price * tp_distance_pct) if direction == 'LONG' else price - (price * tp_distance_pct)
    tp_source = 'ATR'
    target_level = None

    # Find nearest S/R in trade direction
    for level in sr_map:
        level_price = level['price']
        dist_pct = abs(level_price - price) / price

        if direction == 'LONG' and level_price > price:
            # Reward side: find closest resistance above
            if dist_pct <= tp_max and dist_pct >= getattr(hc, 'RR_ENGINE_TP_MIN_PCT', 0.005):
                tp_price = level_price
                tp_distance_pct = dist_pct
                tp_source = level.get('source', 'STRUCTURAL')
                target_level = level
                break
        elif direction == 'SHORT' and level_price < price:
            # Reward side: find closest support below
            if dist_pct <= tp_max and dist_pct >= getattr(hc, 'RR_ENGINE_TP_MIN_PCT', 0.005):
                tp_price = level_price
                tp_distance_pct = dist_pct
                tp_source = level.get('source', 'STRUCTURAL')
                target_level = level
                break

    # Also check liquidation clusters as TP targets (cascades provide exit liquidity)
    if tp_source == 'ATR' and liquidity.get('clusters_ahead', 0) > 0:
        nearest = liquidity.get('nearest_ahead_dist')
        # nearest is in PERCENT (e.g., 1.5 = 1.5%), tp_max is in DECIMAL (e.g., 0.025 = 2.5%)
        nearest_decimal = nearest / 100.0 if nearest else None
        if nearest_decimal and nearest_decimal <= tp_max and nearest_decimal >= getattr(hc, 'RR_ENGINE_TP_MIN_PCT', 0.005):
            tp_distance_pct = nearest_decimal
            tp_price = price + (price * tp_distance_pct) if direction == 'LONG' else price - (price * tp_distance_pct)
            tp_source = 'LIQUIDATION'

    # R:R ratio
    if sl_distance_pct <= 0:
        rr_ratio = 999  # fail-open
    else:
        rr_ratio = tp_distance_pct / sl_distance_pct

    return {
        'sl_price': round(sl_price, 8),
        'tp_price': round(tp_price, 8),
        'sl_distance_pct': round(sl_distance_pct * 100, 4),
        'tp_distance_pct': round(tp_distance_pct * 100, 4),
        'rr_ratio': round(rr_ratio, 2),
        'sl_source': 'ATR',
        'tp_source': tp_source,
        'target_level': target_level,
    }


# ── Legacy rr_gate (for comparison) ────────────────────────────────────────

def _legacy_rr(token, direction, price, candles_5m=None):
    """Run the old rr_gate logic directly (avoid recursion through entry_gates)."""
    try:
        from hermes_constants import ATR_SL_MIN, ATR_TP_MIN

        # Get ATR% using the same logic as legacy rr_gate
        atr_pct = get_atr_pct(token)
        if atr_pct is None:
            atr_pct = getattr(hc, 'ATR_PCT_FALLBACK', 0.03) * 100

        # Legacy SL/TP calculation
        sl_distance = price * ATR_SL_MIN * 1.0  # ENTRY_RR_SL_ATR_MULT = 1.0
        tp_distance = price * ATR_TP_MIN

        if sl_distance <= 0:
            return {'pass': True, 'sl': 0, 'tp': 0, 'rr': 999}

        rr = tp_distance / sl_distance
        sl = price - sl_distance if direction.upper() == 'LONG' else price + sl_distance
        tp = price + tp_distance if direction.upper() == 'LONG' else price - tp_distance

        return {'pass': rr >= 2.0, 'sl': sl, 'tp': tp, 'rr': rr}
    except Exception:
        return {'pass': True, 'sl': 0, 'tp': 0, 'rr': 999}


# ── Scoring ─────────────────────────────────────────────────────────────────

def _compute_score(rr_ratio, vol_width, liquidity, sr_map):
    """Compute 0-100 composite quality score.

    Components:
    - R:R quality (50 pts) — higher R:R = more points
    - Liquidity flow (25 pts) — trading toward clusters = bonus
    - S/R clarity (25 pts) — clear structural target = bonus
    """
    score = 0

    # 1. R:R Quality (50 pts)
    # R:R of 2.0 = 25pts, 3.0 = 37.5pts, 4.0+ = 50pts (capped)
    # Floor of 5 pts even for R:R < 1
    rr_pts = min(50, max(5, rr_ratio * 12.5))
    score += rr_pts

    # 2. Liquidity Flow (25 pts)
    # magnet_score contributes positively, cascade_risk contributes negatively
    magnet = liquidity.get('magnet_score', 0)
    cascade = liquidity.get('cascade_risk', 0)
    liq_pts = max(0, min(25, int(magnet * 20 - cascade * 10 + 12)))
    score += liq_pts

    # 3. S/R Clarity (25 pts)
    # Clear target in sweet spot = full points, no target = 0
    if sr_map:
        nearest_dist = sr_map[0].get('distance_pct', 999)
        if 0.3 < nearest_dist < 2.0:
            score += 25  # clear target in sweet spot
        elif nearest_dist < 0.3:
            score += 12  # too close, may not reach
        elif nearest_dist < 3.0:
            score += 15  # a bit far but reachable
        else:
            score += 5   # no clear target nearby
    else:
        score += 0      # no S/R data at all

    # Grade
    if score >= 80:
        grade = 'A'
    elif score >= 65:
        grade = 'B'
    elif score >= 50:
        grade = 'C'
    elif score >= 35:
        grade = 'D'
    else:
        grade = 'F'

    return score, grade


# ── Main Entry Point ────────────────────────────────────────────────────────

def evaluate_rr(token, direction, price, candles_5m=None, signal_type=None):
    """Structural R:R evaluation — main entry point.

    Returns dict with:
        pass: bool (True = allow, False = block)
        rr_ratio: float
        sl_price, tp_price: float
        score: int (0-100)
        grade: str (A-F)
        block_reason: str
        notes: str
        sr_map: list
        vol_width: dict
        liquidity: dict
        legacy_rr: dict (for shadow mode comparison)
    """
    try:
        if price <= 0:
            return _result(False, 0, 0, 0, 0, 'F', 'degenerate_price', 'Price <= 0')

        token_upper = token.upper()
        direction = direction.upper()

        # Get volatility width
        vol_width = compute_vol_width(token_upper, candles_5m)
        regime = vol_width.get('atr_regime', 'NORMAL')
        atr_pct = vol_width.get('atr_pct', 1.0)

        # Build S/R map
        sr_map = build_sr_map(token_upper, price, candles_5m, atr_pct)

        # Compute liquidity proximity
        liquidity = compute_liquidity_proximity(token_upper, price, direction)

        # Compute structural R:R
        rr = compute_structural_rr(price, direction, sr_map, vol_width, liquidity)
        rr_ratio = rr['rr_ratio']

        # Get regime-adjusted minimum
        rr_min = _get_rr_min(regime)

        # Score
        score, grade = _compute_score(rr_ratio, vol_width, liquidity, sr_map)

        # Minimum score gate
        min_score = getattr(hc, 'RR_ENGINE_MIN_SCORE', 50)

        # Determine pass/fail
        block_reason = None
        passed = True

        if rr_ratio < rr_min:
            block_reason = f'R:R {rr_ratio:.2f} < {rr_min:.1f} minimum for {regime} regime'
            passed = False
        elif score < min_score:
            block_reason = f'Score {score} < {min_score} minimum (grade {grade})'
            passed = False

        # Shadow mode: always pass but log what would have been blocked
        shadow = getattr(hc, 'RR_ENGINE_SHADOW', True)
        force = getattr(hc, 'RR_ENGINE_FORCE', False)

        # Legacy comparison
        legacy = _legacy_rr(token_upper, direction, price, candles_5m)

        # Build notes
        notes_parts = []
        notes_parts.append(f"R:R={rr_ratio:.2f} (min={rr_min:.1f})")
        notes_parts.append(f"Score={score} Grade={grade}")
        notes_parts.append(f"SL={rr['sl_price']:.6f} ({rr['sl_distance_pct']:.2f}%) TP={rr['tp_price']:.6f} ({rr['tp_distance_pct']:.2f}%)")
        notes_parts.append(f"TP via {rr['tp_source']}")
        notes_parts.append(f"Regime={regime} ATR={atr_pct:.2f}% BB={vol_width.get('bb_width', 'N/A')}")
        notes_parts.append(f"S/R levels: {len(sr_map)} | Liq: {liquidity['clusters_ahead']} ahead, {liquidity['clusters_behind']} behind")
        notes = ' | '.join(notes_parts)

        # Log in shadow mode (with dedup to prevent spam)
        if not passed and shadow and not force:
            log_key = f"{token_upper}:{direction}:shadow_block"
            now_ts = time.time()
            if log_key not in _log_dedup or now_ts - _log_dedup[log_key] > _LOG_DEDUP_TTL:
                _log(f"SHADOW BLOCK {token_upper} {direction} ${price:.4f}: {block_reason}")
                _log(f"  {notes}")
                _log_dedup[log_key] = now_ts
            passed = True  # shadow mode: don't actually block

        if passed and force and block_reason:
            _log(f"FORCE BLOCK {token_upper} {direction} ${price:.4f}: {block_reason}")
            _log(f"  {notes}")

        return {
            'pass': passed,
            'rr_ratio': rr_ratio,
            'sl_price': rr['sl_price'],
            'tp_price': rr['tp_price'],
            'entry_price': price,
            'risk_pct': rr['sl_distance_pct'],
            'reward_pct': rr['tp_distance_pct'],
            'score': score,
            'grade': grade,
            'block_reason': block_reason,
            'notes': notes,
            'sr_map': sr_map[:5],  # top 5 levels for logging
            'vol_width': vol_width,
            'liquidity': liquidity,
            'legacy_rr': legacy,
            'tp_source': rr['tp_source'],
            'target_level': rr.get('target_level'),
        }

    except Exception as e:
        if getattr(hc, 'RR_ENGINE_FAIL_OPEN', True):
            return _result(True, 999, 0, 0, 0, 'A', None, f'fail-open: {e}')
        else:
            raise


def _result(passed, rr, sl, tp, score, grade, reason, notes):
    """Helper to build result dict."""
    return {
        'pass': passed,
        'rr_ratio': rr,
        'sl_price': sl,
        'tp_price': tp,
        'entry_price': 0,
        'risk_pct': 0,
        'reward_pct': 0,
        'score': score,
        'grade': grade,
        'block_reason': reason,
        'notes': notes,
        'sr_map': [],
        'vol_width': {},
        'liquidity': {},
        'legacy_rr': {},
        'tp_source': 'UNKNOWN',
        'target_level': None,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Risk-Reward Engine')
    parser.add_argument('token', nargs='?', help='Token symbol')
    parser.add_argument('direction', nargs='?', help='LONG or SHORT')
    parser.add_argument('price', nargs='?', type=float, help='Entry price')
    parser.add_argument('--quick', action='store_true', help='Quick one-liner output')
    parser.add_argument('--scan', action='store_true', help='Scan top tokens')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args()

    if args.scan:
        # Scan top tokens
        from tokens import get_all_tradeable_tokens
        tokens = get_all_tradeable_tokens()[:20]
        print(f"{'Token':<8} {'Dir':<6} {'R:R':>6} {'Score':>6} {'Grade':>5} {'TP Source':<12} {'Verdict':<8}")
        print('-' * 65)
        for tok in tokens:
            # Get latest price
            try:
                from signal_schema import get_all_latest_prices
                prices = get_all_latest_prices()
                price_data = prices.get(tok.upper())
                if not price_data:
                    continue
                price = price_data.get('price', 0)
                if price <= 0:
                    continue
            except Exception:
                continue

            for direction in ['LONG', 'SHORT']:
                result = evaluate_rr(tok, direction, price)
                verdict = 'PASS' if result['pass'] else 'BLOCK'
                print(f"{tok:<8} {direction:<6} {result['rr_ratio']:>6.2f} {result['score']:>6} "
                      f"{result['grade']:>5} {result['tp_source']:<12} {verdict:<8}")

    elif args.token and args.direction and args.price:
        result = evaluate_rr(args.token, args.direction, args.price)

        if args.json:
            import json as json_mod
            # Remove non-serializable items
            out = {k: v for k, v in result.items() if k != 'target_level'}
            print(json_mod.dumps(out, indent=2, default=str))
        elif args.quick:
            tok_name = args.token.upper()
            print(f"{tok_name} {args.direction.upper()} | "
                  f"R:R={result['rr_ratio']:.2f} Score={result['score']} Grade={result['grade']} | "
                  f"SL={result['sl_price']:.6f} TP={result['tp_price']:.6f} | "
                  f"{'PASS' if result['pass'] else 'BLOCK: ' + (result['block_reason'] or '')}")
        else:
            print(f"\n{'='*60}")
            print(f"Token: {args.token.upper()} | Direction: {args.direction.upper()} | Entry: ${args.price:.4f}")
            print(f"{'='*60}")

            print(f"\n── Volatility ──")
            vw = result['vol_width']
            print(f"  ATR%: {vw.get('atr_pct', 'N/A')}% ({vw.get('atr_regime', 'N/A')} regime)")
            print(f"  BB Width: {vw.get('bb_width', 'N/A')}")
            print(f"  BB Position: {vw.get('bb_position', 'N/A')}")
            print(f"  BB Squeeze: {vw.get('bb_squeeze', 'N/A')}")
            print(f"  Energy: {vw.get('energy_score', 'N/A')}")

            print(f"\n── S/R Map (top 5) ──")
            for i, level in enumerate(result.get('sr_map', [])[:5]):
                print(f"  {i+1}. ${level['price']:.6f} ({level['distance_pct']:.2f}%) "
                      f"[{level['type']}] via {level['source']} ({level.get('touches', level.get('strength', '?'))} touches)")

            print(f"\n── Liquidity ──")
            liq = result['liquidity']
            print(f"  Clusters ahead: {liq['clusters_ahead']}")
            print(f"  Clusters behind: {liq['clusters_behind']}")
            print(f"  Magnet score: {liq['magnet_score']}")
            print(f"  Cascade risk: {liq['cascade_risk']}")

            print(f"\n── R:R Calculation ──")
            print(f"  SL: ${result['sl_price']:.6f} ({result['risk_pct']:.2f}% risk)")
            print(f"  TP: ${result['tp_price']:.6f} ({result['reward_pct']:.2f}% reward)")
            print(f"  R:R: {result['rr_ratio']:.2f}")
            print(f"  TP source: {result['tp_source']}")

            print(f"\n── Score ──")
            print(f"  Total: {result['score']}/100 — Grade {result['grade']}")

            print(f"\n── Verdict ──")
            if result['pass']:
                print(f"  ✅ PASS")
            else:
                print(f"  ❌ BLOCKED: {result['block_reason']}")

            # Legacy comparison
            legacy = result.get('legacy_rr', {})
            if legacy:
                print(f"\n── Legacy Comparison ──")
                print(f"  Old rr_gate: {'PASS' if legacy.get('pass') else 'BLOCK'} "
                      f"(R:R={legacy.get('rr', 0):.2f})")
                print(f"  New engine:  {'PASS' if result['pass'] else 'BLOCK'} "
                      f"(R:R={result['rr_ratio']:.2f}, Score={result['score']})")
                if legacy.get('pass') != result['pass']:
                    print(f"  ⚠️  DISAGREEMENT — engine {'blocks' if not result['pass'] else 'allows'} "
                          f"what legacy {'allows' if legacy.get('pass') else 'blocks'}")

            print()
    else:
        parser.print_help()
