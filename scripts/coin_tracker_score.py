#!/usr/bin/env python3
"""
coin_tracker_score.py — Scoring engine for coin health and composite scores.

Importable by other scripts. Standalone scoring logic, no DB writes.

Usage:
    from coin_tracker_score import score_coin, health_from_score, WEIGHTS
    result = score_coin(closes_5m, highs_5m, lows_5m, volumes_5m, ...)
"""
import time

WEIGHTS = {
    'momentum': 0.14,
    'volume': 0.10,
    'volatility': 0.07,
    'spread': 0.07,
    'signals': 0.04,    # reduced to prevent echo
    'regime': 0.04,
    'wyckoff': 0.14,
    'ewave': 0.09,
    'trend': 0.07,
    'setup': 0.08,
    'clustering': 0.04,
    'recency': 0.05,
    'liquidation': 0.07,  # NEW: liquidation cluster proximity + stop hunt signals
}
# ponytail: weights sum to 1.0 — verified

# ── Indicators ─────────────────────────────────────────────────────────────────

def ema(values, period):
    """Exponential moving average."""
    if not values or len(values) < period:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e

def rsi(closes, period=14):
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i - 1] - closes[i]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(closes, fast=12, slow=26, signal_period=9):
    """MACD histogram. Returns (macd_line, signal_line, histogram).
    Requires slow + signal_period + fast candles minimum."""
    if len(closes) < slow + signal_period:
        return None, None, None
    
    # Compute MACD line series for signal line EMA
    macd_series = []
    k_fast = 2 / (fast + 1)
    k_slow = 2 / (slow + 1)
    
    # Initialize EMAs
    ema_fast = sum(closes[:fast]) / fast
    ema_slow = sum(closes[:slow]) / slow
    
    # Compute MACD series from slow onwards
    for i in range(slow, len(closes)):
        if i >= fast:
            ema_fast = closes[i] * k_fast + ema_fast * (1 - k_fast)
        ema_slow = closes[i] * k_slow + ema_slow * (1 - k_slow)
        macd_series.append(ema_fast - ema_slow)
    
    if len(macd_series) < signal_period:
        return macd_series[-1] if macd_series else None, None, None
    
    # Signal line = EMA of MACD series
    k_signal = 2 / (signal_period + 1)
    signal_line = sum(macd_series[:signal_period]) / signal_period
    for m in macd_series[signal_period:]:
        signal_line = m * k_signal + signal_line * (1 - k_signal)
    
    macd_line = macd_series[-1]
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def atr(highs, lows, closes, period=14):
    """Average True Range with Wilder's smoothing."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        h, l, prev = highs[i], lows[i], closes[i-1]
        tr = max(h - l, abs(h - prev), abs(l - prev))
        trs.append(tr)
    if len(trs) < period:
        return None
    # ponytail: Wilder's smoothing (matches coin_tracker_analysis.py)
    atr_val = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val

def spread_bps(bid, ask, price):
    """Spread in basis points."""
    if not bid or not ask or not price or price <= 0:
        return None
    return ((ask - bid) / price) * 10000

def volume_trend(volumes):
    """Volume trend: positive = increasing. Returns -1 to 1.
    Data is oldest-first (index 0 = oldest)."""
    if not volumes or len(volumes) < 2:
        return 0.0
    n = len(volumes)
    split = max(1, n // 3)
    # Oldest-first: use last third as recent, middle third as earlier
    recent = sum(volumes[-split:]) / split
    earlier = sum(volumes[-split*2:-split]) / max(1, split)
    if earlier == 0:
        return 1.0 if recent > 0 else 0.0
    ratio = (recent - earlier) / earlier
    return max(-1.0, min(1.0, ratio))

# ── Component scorers (0-100) ──────────────────────────────────────────────────

def score_momentum(closes, ema_9=None, ema_20=None, ema_50=None):
    """Momentum score 0-100. Centered at 50, wide spread."""
    if not closes or len(closes) < 5:
        return 50.0
    # Price change over last 20 candles (or fewer if not available)
    lookback = min(19, len(closes) - 1)
    if closes[lookback] == 0:
        return 50.0
    price_change = (closes[0] - closes[lookback]) / closes[lookback] * 100
    # Map price change to score: -10% → 10, 0% → 50, +10% → 90
    score = 50.0 + max(-40, min(40, price_change * 4))
    # EMA alignment: strong bonus/penalty
    if ema_9 and ema_20:
        if ema_9 > ema_20:
            score += 15  # Uptrend
        else:
            score -= 15  # Downtrend
    if ema_20 and ema_50:
        if ema_20 > ema_50:
            score += 10
        else:
            score -= 10
    return max(0, min(100, score))

def score_volume(vol_recent, vol_avg, vol_trend):
    """Volume score 0-100. High relative volume = high score."""
    if not vol_avg or vol_avg == 0:
        return 30.0  # No data = low score
    ratio = vol_recent / vol_avg if vol_recent else 0
    # Map ratio to score: 0x → 10, 1x → 50, 3x → 90
    score = 10.0 + max(0, min(80, ratio * 25))
    # Trend bonus
    score += vol_trend * 15
    return max(0, min(100, score))

def score_volatility(atr_val, price):
    """Volatility score 0-100. Moderate volatility is best for trading."""
    if not atr_val or not price or price <= 0:
        return 30.0  # No data = low score
    atr_pct = (atr_val / price) * 100
    # Too quiet (<0.3%) = low, sweet spot (0.5-3%) = high, too wild (>10%) = low
    if atr_pct < 0.3:
        return 15.0
    elif atr_pct < 0.5:
        return 35.0
    elif atr_pct < 1.0:
        return 60.0 + (atr_pct - 0.5) * 40
    elif atr_pct < 3.0:
        return 80.0 + (3.0 - atr_pct) * 5  # Peak at 1%
    elif atr_pct < 10.0:
        return 60.0 - (atr_pct - 3) * 5
    else:
        return 20.0

def score_spread(spread):
    """Spread score 0-100. Tight spread = liquid = high score."""
    if spread is None:
        return 40.0
    if spread < 5:
        return 95.0
    elif spread < 10:
        return 85.0
    elif spread < 20:
        return 70.0
    elif spread < 50:
        return 50.0
    elif spread < 100:
        return 30.0
    else:
        return 10.0

def score_signals(signal_count, avg_confidence, mixed_overall=False, mixed_recent=False):
    """Signal confluence score 0-100. 
    - Based on unique signal types (1-10 range)
    - Mixed long+short signals reduce score (conflicted coin)
    - Recent conflicts (last 2h) penalize more heavily for 1m trading"""
    if signal_count == 0:
        return 20.0
    # Base: 1 type=30, 3 types=50, 5 types=65, 10+ types=80
    score = 20.0 + min(60, signal_count * 6)
    if avg_confidence:
        score += (avg_confidence - 50) * 0.1
    # Mixed signals overall = conflicted
    if mixed_overall:
        score *= 0.7  # 30% penalty
    # Recent conflict (last 2h) = severe penalty for 1m trading
    if mixed_recent:
        score *= 0.5  # Additional 50% penalty
    return max(0, min(100, score))

def score_regime(regime):
    """Regime alignment score 0-100. Moderate influence."""
    if regime in ('LONG_BIAS', 'BULL'):
        return 60.0
    elif regime in ('SHORT_BIAS', 'BEAR'):
        return 40.0
    return 50.0

def score_wyckoff(phase):
    """Wyckoff phase score 0-100. Phase transitions are high-value."""
    if phase == 'markup':
        return 80.0  # Best long setup
    elif phase == 'accumulation':
        return 70.0  # Building position
    elif phase == 'markdown':
        return 25.0  # Avoid longs
    elif phase == 'distribution':
        return 35.0  # Potential short
    return 50.0  # No pattern = neutral

def score_ewave(wave, direction):
    """Elliott Wave score 0-100. Wave 3 is strongest, wave 5 is late."""
    if wave is None:
        return 50.0
    if wave == 3:
        return 85.0  # Strongest wave
    elif wave == 1:
        return 65.0  # Early, good R:R
    elif wave == 5:
        return 55.0  # Late, lower conviction
    elif wave == 2:
        return 70.0  # Pullback = entry opportunity
    elif wave == 4:
        return 60.0  # Another pullback
    elif wave == 'C':
        return 45.0  # End of correction
    elif wave == 'A':
        return 35.0  # Start of correction
    elif wave == 'B':
        return 40.0  # Counter-trend bounce
    return 50.0

def score_trend_quality(trend_score):
    """Trend quality score 0-100. Pass through with scaling."""
    if trend_score is None:
        return 50.0
    return max(0, min(100, trend_score))

def score_liquidation(price, liq_data):
    """
    Liquidation cluster proximity score 0-100.

    High score = there's a liquidation cluster nearby = explosive move imminent.
    This is the SETUP quality from liquidation data.

    Scoring:
    - Active stop hunt signal → 90-100 (best setup, cascade imminent)
    - Cluster within 0.5% → 80-90 (very close, high energy)
    - Cluster within 1% → 65-80 (close, good setup)
    - Cluster within 2% → 50-65 (moderate proximity)
    - Cluster > 2% away → 40-50 (far, low energy)
    - No clusters at all → 50 (default neutral)
    """
    if not price or price <= 0 or not liq_data:
        return 50.0

    # Check for active stop hunt signal
    stop_hunts = liq_data.get('stop_hunt_signals', [])
    for sh in stop_hunts:
        if sh.get('coin', '').upper() == '':
            continue
        # We'll match by caller — this function receives pre-filtered data
        break

    # Get clusters for this coin (pre-filtered by caller)
    clusters = liq_data.get('_coin_clusters', [])

    if not clusters:
        return 50.0  # No data = neutral

    # Find nearest cluster by distance
    nearest_dist = min(abs(c.get('distance_pct', 100)) for c in clusters)
    nearest = next(c for c in clusters if abs(c.get('distance_pct', 100)) == nearest_dist)

    # Active stop hunt = highest score
    if liq_data.get('_has_stop_hunt'):
        score = 95.0
        # Bonus for cluster size
        size_bonus = min(5, nearest.get('total_notional_usd', 0) / 500_000_000)
        score += size_bonus
        return min(100, score)

    # Distance-based scoring
    if nearest_dist <= 0.5:
        score = 85.0
    elif nearest_dist <= 1.0:
        score = 72.0
    elif nearest_dist <= 1.5:
        score = 62.0
    elif nearest_dist <= 2.0:
        score = 55.0
    else:
        score = 45.0

    # Cluster size bonus (bigger cluster = more energy)
    size = nearest.get('total_notional_usd', 0)
    if size > 1_000_000_000:
        score += 8  # Massive cluster
    elif size > 500_000_000:
        score += 5
    elif size > 100_000_000:
        score += 3

    # High leverage bonus (more forced selling = bigger cascade)
    max_lev = nearest.get('max_leverage', 0)
    if max_lev >= 40:
        score += 3
    elif max_lev >= 20:
        score += 2

    # Order book imbalance bonus
    imbalance = liq_data.get('_imbalance', 1.0)
    if imbalance > 3.0:
        score += 3  # Heavy bid imbalance = support forming
    elif imbalance < 0.33:
        score += 3  # Heavy ask imbalance = resistance forming

    return max(0, min(100, score))


def compute_coin_regime(closes, ema_9=None, ema_20=None, ema_50=None, rsi_14=None):
    """Compute per-coin regime based on individual price action."""
    if not closes or len(closes) < 20:
        return 'NEUTRAL'
    
    price = closes[0]
    above_20 = price > ema_20 if ema_20 else None
    above_50 = price > ema_50 if ema_50 else None
    ema20_above_50 = ema_20 > ema_50 if ema_20 and ema_50 else None
    
    # Count bullish vs bearish signals
    bull = 0
    bear = 0
    
    if above_20 is True: bull += 1
    elif above_20 is False: bear += 1
    
    if above_50 is True: bull += 1
    elif above_50 is False: bear += 1
    
    if ema20_above_50 is True: bull += 1
    elif ema20_above_50 is False: bear += 1
    
    if rsi_14:
        if rsi_14 > 55: bull += 1
        elif rsi_14 < 45: bear += 1
    
    # Price momentum (last 10 candles)
    if len(closes) >= 10:
        momentum = (closes[0] - closes[9]) / closes[9] * 100
        if momentum > 0.5: bull += 1
        elif momentum < -0.5: bear += 1
    
    # Price momentum (last 20 candles)
    if len(closes) >= 20:
        momentum20 = (closes[0] - closes[19]) / closes[19] * 100
        if momentum20 > 1.0: bull += 1
        elif momentum20 < -1.0: bear += 1
    
    # EMA 9 slope (short-term momentum)
    if len(closes) >= 12 and ema_9:
        ema_9_prev = ema(closes[1:11], 9) if len(closes) >= 11 else None
        if ema_9_prev and ema_9 > ema_9_prev * 1.001: bull += 1
        elif ema_9_prev and ema_9 < ema_9_prev * 0.999: bear += 1
    
    # 3+ bull signals = BULL, 3+ bear signals = BEAR, else NEUTRAL
    if bull >= 3 and bull > bear:
        return 'BULL'
    elif bear >= 3 and bear > bull:
        return 'BEAR'
    return 'NEUTRAL'

# ── Health state ───────────────────────────────────────────────────────────────

def health_from_score(composite):
    """Map composite score to health state."""
    if composite >= 85:
        return 'ready'
    elif composite >= 70:
        return 'setup'
    elif composite >= 55:
        return 'hot'
    elif composite >= 40:
        return 'warm'
    elif composite >= 25:
        return 'cold'
    return 'dead'

# ── Composite scorer ───────────────────────────────────────────────────────────

def score_coin(closes_5m=None, highs_5m=None, lows_5m=None, volumes_5m=None,
               closes_1h=None, volumes_1h=None,
               price=None, signal_count=0, avg_confidence=None, regime='NEUTRAL',
               liq_data=None):
    """
    Compute all component scores and composite for a coin.
    Returns dict with all scores and health state.

    liq_data: optional dict with liquidation cluster data for this coin
              (pre-filtered: _coin_clusters, _has_stop_hunt, _imbalance keys)
    """
    closes_5m = closes_5m or []
    highs_5m = highs_5m or []
    lows_5m = lows_5m or []
    volumes_5m = volumes_5m or []
    volumes_1h = volumes_1h or []

    # Indicators
    ema_9 = ema(closes_5m, 9) if len(closes_5m) >= 9 else None
    ema_20 = ema(closes_5m, 20) if len(closes_5m) >= 20 else None
    ema_50 = ema(closes_5m, 50) if len(closes_5m) >= 50 else None
    rsi_14 = rsi(closes_5m, 14) if len(closes_5m) >= 15 else None
    _, _, macd_hist = macd(closes_5m) if len(closes_5m) >= 35 else (None, None, None)
    atr_14 = atr(highs_5m, lows_5m, closes_5m, 14) if len(closes_5m) >= 15 else None

    # Volume
    vol_recent = volumes_5m[0] if volumes_5m else 0
    vol_avg = sum(volumes_5m[:50]) / min(50, len(volumes_5m)) if volumes_5m else None
    vol_trend = volume_trend(volumes_5m[:60])

    # Spread (approximate from candle range)
    spread = None
    if highs_5m and lows_5m and price and price > 0:
        recent_range = highs_5m[0] - lows_5m[0]
        spread = (recent_range / price) * 10000

    # Component scores
    s_momentum = score_momentum(closes_5m, ema_9, ema_20, ema_50)
    s_volume = score_volume(vol_recent, vol_avg, vol_trend) if vol_avg else 50.0
    s_volatility = score_volatility(atr_14, price)
    s_spread = score_spread(spread)
    s_signals = score_signals(signal_count, avg_confidence)
    s_regime = score_regime(regime)

    # Default neutral scores for analysis components (not available in simplified mode)
    s_wyckoff = 50.0
    s_ewave = 50.0
    s_trend_quality = 50.0
    s_setup = 50.0
    s_clustering = 50.0
    s_recency = 75.0  # assume decent recency

    # Liquidation score (NEW — uses liquidation cluster data)
    s_liquidation = score_liquidation(price, liq_data) if liq_data else 50.0

    composite = (
        s_momentum * WEIGHTS['momentum'] +
        s_volume * WEIGHTS['volume'] +
        s_volatility * WEIGHTS['volatility'] +
        s_spread * WEIGHTS['spread'] +
        s_signals * WEIGHTS['signals'] +
        s_regime * WEIGHTS['regime'] +
        s_wyckoff * WEIGHTS['wyckoff'] +
        s_ewave * WEIGHTS['ewave'] +
        s_trend_quality * WEIGHTS['trend'] +
        s_setup * WEIGHTS['setup'] +
        s_clustering * WEIGHTS['clustering'] +
        s_recency * WEIGHTS['recency'] +
        s_liquidation * WEIGHTS['liquidation']
    )

    return {
        'health': health_from_score(composite),
        'composite': round(composite, 2),
        'momentum': round(s_momentum, 2),
        'volume': round(s_volume, 2),
        'volatility': round(s_volatility, 2),
        'spread': round(s_spread, 2),
        'signals': round(s_signals, 2),
        'regime': round(s_regime, 2),
        'liquidation': round(s_liquidation, 2),
        'indicators': {
            'ema_9': ema_9,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'rsi_14': rsi_14,
            'macd_hist': macd_hist,
            'atr_14': atr_14,
            'vol_avg': vol_avg,
            'vol_trend': vol_trend,
            'spread_bps': spread,
        }
    }
