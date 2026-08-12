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
    'momentum': 0.25,
    'volume': 0.25,
    'volatility': 0.15,
    'spread': 0.15,
    'signals': 0.10,
    'regime': 0.10,
}

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

def macd(closes, fast=12, slow=26, signal=9):
    """MACD histogram. Returns (macd_line, signal_line, histogram)."""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = ema_fast - ema_slow
    return macd_line, None, macd_line

def atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(min(period, len(closes) - 1)):
        h, l, c_prev = highs[i], lows[i], closes[i + 1]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None

def spread_bps(bid, ask, price):
    """Spread in basis points."""
    if not bid or not ask or not price or price <= 0:
        return None
    return ((ask - bid) / price) * 10000

def volume_trend(volumes):
    """Volume trend: positive = increasing. Returns -1 to 1."""
    if not volumes or len(volumes) < 2:
        return 0.0
    n = len(volumes)
    split = max(1, n // 3)
    recent = sum(volumes[:split]) / split
    earlier = sum(volumes[split:split * 2]) / max(1, split)
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
    
    if above_20: bull += 1
    else: bear += 1
    
    if above_50: bull += 1
    else: bear += 1
    
    if ema20_above_50: bull += 1
    else: bear += 1
    
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
               price=None, signal_count=0, avg_confidence=None, regime='NEUTRAL'):
    """
    Compute all component scores and composite for a coin.
    Returns dict with all scores and health state.
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

    composite = (
        s_momentum * WEIGHTS['momentum'] +
        s_volume * WEIGHTS['volume'] +
        s_volatility * WEIGHTS['volatility'] +
        s_spread * WEIGHTS['spread'] +
        s_signals * WEIGHTS['signals'] +
        s_regime * WEIGHTS['regime']
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
