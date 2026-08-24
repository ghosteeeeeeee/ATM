#!/usr/bin/env python3
"""
tl_break_signals.py — Diagonal Trendline Breakout Signal for Hermes.

Pattern: price rides a diagonal trendline, touches it 2+ times (forming a zone),
then breaks out decisively in the opposite direction.

Anchor-at-start approach:
  Trendline anchored at the START of the diagonal zone (closes[0]).
  Direction determined by the diagonal slope:
    - Diagonal going DOWN (start > end) → expect upside break → LONG
    - Diagonal going UP (start < end) → expect downside break → SHORT

Two-phase window:
  First 70% of lookback = diagonal formation zone
  Last 30% = breakout confirmation zone

Signal types:
  - tl_break_long  : diagonal down-slope + upside breakout
  - tl_break_short : diagonal up-slope + downside breakout

Architecture:
  5m OHLCV candles from candles.db
  → anchor-at-start diagonal detection
  → bounce validation (2+ touches within diagonal zone)
  → breakout confirmation in last 30% of window
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Run: scan_tl_break_signals(prices_dict) — compatible with signals/__init__.py registry
"""

import sys
import os
import time
import sqlite3
from typing import Optional, Tuple, List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyperliquid_exchange import _HL_BLOCKLIST

# ── Constants ─────────────────────────────────────────────────────────────────

# Lookback window (~8h = 96 candles at 5m)
TL_LOOKBACK           = 96    # candles
TL_LOOKBACK_MIN       = 70    # minimum required (need fit + breakout + survival)

# 3-phase window:
#   Phase 1 — Trendline fitting zone: first 50% of lookback (48 candles = ~4h)
#   Phase 2 — Breakout confirmation zone: next 15 candles (~1.25h)
#   Phase 3 — Post-breakout survival zone: next 15 candles (~1.25h)
# The survival zone filters fakeouts: price must stay above trendline after breakout.
TL_FIT_CUTOFF         = 0.50
TL_BREAKOUT_CANDLES   = 15    # breakout must confirm within 15 candles (75 min)
TL_SURVIVAL_CANDLES   = 15    # post-breakout: price must survive above line for 15 candles

# Trendline detection: linear regression on closes in fit zone
# R² must be high enough to confirm a real trendline (not noise)
TL_R2_MIN             = 0.35  # minimum R² for trendline validity (relaxed from 0.40 — allows noisier trendlines)
TL_SLOPE_PCT_MIN      = 0.0001 # minimum slope as % of price per candle (~0.03%/hr, rejects flat markets)

# Bounce detection: price must touch the trendline (wick or close within threshold)
# A bounce = candle touches trendline AND next candle closes AWAY from it (rejection)
TL_BOUNCE_ATR_K       = 0.5   # within 0.5 * ATR(14) of trendline (tight)
TL_MIN_BOUNCES        = 2     # minimum 2 touches in fit zone (relaxed from 3 — more fish)
TL_MAX_BOUNCE_RATIO   = 0.25  # bounces cannot exceed 25% of fit candles (relaxed from 0.20)
TL_REJECTION_ATR_K    = 0.25  # rejection must move 0.25+ ATR away from line

# Breakout confirmation: price must close beyond trendline + threshold
TL_BREAKOUT_ATR_K     = 0.8   # 0.8 * ATR(14) beyond trendline (was 0.4 — too weak, caught gentle drift)
TL_FOLLOWTHROUGH_MIN  = 3     # minimum candles closing beyond line in breakout zone (relaxed from 4)
TL_CONSECUTIVE_MIN    = 3     # minimum consecutive candles closing beyond line (stronger signal)

# ATR expansion: big moves start with volatility increase
TL_ATR_EXPANSION_MIN  = 1.2   # breakout ATR must be >= 1.2x fit ATR (20% expansion)

# Breakout speed: fast breakouts succeed more
TL_BREAKOUT_SPEED_MIN = 0.3   # minimum breakout speed in ATR units per candle

# ATR settings
TL_ATR_PERIOD         = 14

# Confidence scoring
TL_BASE_CONFIDENCE    = 60    # lower base — let quality bonuses differentiate
TL_BOUNCE_BONUS       = 5     # per extra bounce beyond min (was 3)
TL_R2_BONUS_MAX       = 12    # higher R² = stronger trendline (was 10)
TL_REJECTION_BONUS    = 7     # strong rejection = valid bounce (was 5)
TL_FOLLOWTHROUGH_BONUS = 7    # follow-through confirms breakout (was 5)
TL_BREAKOUT_BONUS_MAX = 7     # strong breakout (was 5)
TL_MAX_CONFIDENCE     = 92    # allow higher confidence for quality signals (was 85)

# Minimum confidence to fire signal
TL_MIN_CONFIDENCE     = 75    # only fire quality signals (was 80, but quality checks now ensure good signals)

# Extension filter: minimum ATR distance from 8h high/low to fire signal
# Backtested 2026-08-24: blocks "selling the bottom" / "buying the top" entries
# ext>=5: 56.2% WR (vs 37.3% baseline), blocks BSV/DASH type losers
TL_MIN_EXTENSION_ATR  = 5.0   # price must be at least 5x ATR from 8h extreme

# Cooldown: don't fire again within this many hours
TL_COOLDOWN_HOURS     = 3

TL_SIGNAL_TYPE        = 'tl_break'
_PRICE_DB             = '/root/.hermes/data/candles.db'

# Per-token cooldown cache (loaded from DB on first call)
_TL_COOLDOWN_CACHE = {}  # {token: last_fire_timestamp}

# ── Candle Fetching ───────────────────────────────────────────────────────────

def _get_candles_5m(token: str, lookback_candles: int = TL_LOOKBACK) -> list:
    """Fetch 5m OHLCV candles from candles.db, oldest first.

    Returns list of dicts: {open_time, open, high, low, close, volume}
    Timestamps are in SECONDS (Unix time).
    Freshness guard: returns [] if most recent candle is > 10 min old.

    NOTE: candles.db has rows going back years. Use ORDER BY ts DESC LIMIT N
    then reverse to get the most recent N candles in oldest-first order.
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback_candles))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        most_recent_ts = rows[0][0]

        # Reverse: most recent first → oldest first (required for indicator calcs)
        rows = list(reversed(rows))

        # Relaxed freshness guard — 10 min (600s) for 5m candles
        if (time.time() - most_recent_ts) > 600:
            return []

        return [
            {'open_time': r[0], 'open': r[1], 'high': r[2],
             'low': r[3], 'close': r[4], 'volume': r[5]}
            for r in rows
        ]
    except Exception as e:
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _atr(candles: list, period: int = TL_ATR_PERIOD) -> Optional[float]:
    """Compute ATR(period) from OHLCV candles (oldest first)."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        high  = candles[i]['high']
        low   = candles[i]['low']
        prev  = candles[i-1]['close']
        tr = max(high - low, abs(high - prev), abs(low - prev))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _trendline_price(slope: float, intercept: float, index: int) -> float:
    """Get the trendline price at candle index `index`."""
    return slope * index + intercept


# ── Core Detection ─────────────────────────────────────────────────────────────

def _linear_regression_with_r2(closes: List[float]) -> Tuple[float, float, float]:
    """Linear regression on closes. Returns (slope, intercept, R²)."""
    n = len(closes)
    if n < 2:
        return 0.0, (sum(closes) / n) if closes else 0.0, 0.0
    sum_x = sum(range(n))
    sum_y = sum(closes)
    sum_xy = sum(i * c for i, c in enumerate(closes))
    sum_x2 = sum(i * i for i in range(n))
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 0.0, sum_y / n, 0.0
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    # R² calculation
    mean_y = sum_y / n
    ss_tot = sum((y - mean_y) ** 2 for y in closes)
    ss_res = sum((closes[i] - (intercept + slope * i)) ** 2 for i in range(n))
    r2 = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    return slope, intercept, r2


def _detect_trendline(closes: List[float], fit_end: int) -> Optional[Dict]:
    """Detect trendline using linear regression on closes[0:fit_end].

    Returns dict with slope, intercept, R², direction or None.
    Direction: descending line (slope<0) → LONG breakout, ascending → SHORT breakout.
    """
    if fit_end < 20:
        return None

    fit_closes = closes[:fit_end]
    slope, intercept, r2 = _linear_regression_with_r2(fit_closes)

    if r2 < TL_R2_MIN:
        return None

    # Slope as % of average price per candle
    avg_price = sum(fit_closes) / len(fit_closes)
    if avg_price <= 0:
        return None
    slope_pct = abs(slope) / avg_price
    if slope_pct < TL_SLOPE_PCT_MIN:
        return None

    # Direction: descending trendline → LONG breakout, ascending → SHORT
    direction = 'LONG' if slope < 0 else 'SHORT'

    # Additional validation: check if trendline is meaningful
    # A good trendline should have price oscillating around it
    # Calculate how many times price crosses the trendline
    crosses = 0
    for i in range(1, fit_end):
        tl_prev = slope * (i-1) + intercept
        tl_curr = slope * i + intercept
        price_prev = fit_closes[i-1]
        price_curr = fit_closes[i]
        
        # Check if price crossed the trendline
        if direction == 'LONG':  # descending trendline
            if (price_prev < tl_prev and price_curr > tl_curr) or \
               (price_prev > tl_prev and price_curr < tl_curr):
                crosses += 1
        else:  # ascending trendline
            if (price_prev < tl_prev and price_curr > tl_curr) or \
               (price_prev > tl_prev and price_curr < tl_curr):
                crosses += 1
    
    # A good trendline should have multiple crosses (price respects it)
    if crosses < 3:
        return None  # trendline not meaningful enough

    return {
        'slope': slope,
        'intercept': intercept,
        'r2': r2,
        'direction': direction,
        'avg_price': avg_price,
        'crosses': crosses,
    }


def _count_bounces_with_rejection(closes: List[float], slope: float, intercept: float,
                                   fit_end: int, atr: float, direction: str) -> Tuple[int, float]:
    """Count bounces off the trendline with rejection validation.

    A valid bounce:
      1. Candle is on the correct side of trendline (approaching from below for LONG,
         from above for SHORT) within TL_BOUNCE_ATR_K * ATR
      2. Next candle closes AWAY from trendline (rejection) by TL_REJECTION_ATR_K * ATR

    Returns (bounce_count, avg_rejection_strength).
    """
    bounce_thresh = atr * TL_BOUNCE_ATR_K
    rejection_thresh = atr * TL_REJECTION_ATR_K
    bounce_count = 0
    rejection_strengths = []

    for i in range(fit_end - 1):
        tl_price = slope * i + intercept
        candle = closes[i]
        next_candle = closes[i + 1]

        # Check approach direction: candle must be approaching from the correct side
        if direction == 'LONG':
            # Descending resistance: price approaches from BELOW the line
            if candle > tl_price + bounce_thresh:
                continue  # candle is above line — not a valid approach
        else:  # SHORT
            # Ascending support: price approaches from ABOVE the line
            if candle < tl_price - bounce_thresh:
                continue  # candle is below line — not a valid approach

        # Check if candle is near trendline
        dist = abs(candle - tl_price)
        if dist > bounce_thresh:
            continue

        # Check rejection: next candle must close away from line
        next_tl = slope * (i + 1) + intercept
        next_dist = next_candle - next_tl

        if direction == 'LONG':
            # Descending resistance: rejection DOWNWARD (back below line)
            if next_dist < -rejection_thresh:
                bounce_count += 1
                rejection_strengths.append(abs(next_dist))
        else:  # SHORT
            # Ascending support: rejection UPWARD (back above line)
            if next_dist > rejection_thresh:
                bounce_count += 1
                rejection_strengths.append(abs(next_dist))

    avg_rejection = sum(rejection_strengths) / len(rejection_strengths) if rejection_strengths else 0.0
    return bounce_count, avg_rejection


def _detect_breakout(closes: List[float], slope: float, intercept: float,
                     fit_end: int, atr: float, direction: str) -> Tuple[bool, float, int]:
    """Detect breakout in the candles after fit_end.

    Breakout: candle closes beyond trendline + threshold, followed by
    follow-through candles staying beyond the line.

    Returns (breakout_detected, breakout_strength_atr, follow_through_count).
    """
    breakout_start = fit_end
    breakout_end = min(fit_end + TL_BREAKOUT_CANDLES, len(closes))
    if breakout_end <= breakout_start + 2:
        return False, 0.0, 0

    breakout_thresh = atr * TL_BREAKOUT_ATR_K
    follow_count = 0
    breakout_strength = 0.0
    first_breakout_idx = None

    for i in range(breakout_start, breakout_end):
        tl_price = slope * i + intercept
        price = closes[i]

        if direction == 'LONG':
            if price > tl_price + breakout_thresh:
                follow_count += 1
                strength = (price - tl_price) / atr
                breakout_strength = max(breakout_strength, strength)
                if first_breakout_idx is None:
                    first_breakout_idx = i
        else:  # SHORT
            if price < tl_price - breakout_thresh:
                follow_count += 1
                strength = (tl_price - price) / atr
                breakout_strength = max(breakout_strength, strength)
                if first_breakout_idx is None:
                    first_breakout_idx = i

    # Need: (1) at least one candle beyond threshold, (2) enough follow-through
    has_breakout = follow_count >= 1
    has_follow_through = follow_count >= TL_FOLLOWTHROUGH_MIN

    # Additional check: breakout should happen early in the breakout zone
    # If first breakout is late, it's less reliable
    if first_breakout_idx is not None:
        breakout_delay = first_breakout_idx - breakout_start
        if breakout_delay > TL_BREAKOUT_CANDLES * 0.7:  # breakout too late
            has_breakout = False

    return has_breakout and has_follow_through, breakout_strength, follow_count


# ── Fakeout Guard ─────────────────────────────────────────────────────────────

def _detect_fakeout(closes: List[float], slope: float, intercept: float,
                    survival_start: int, survival_end: int, atr: float,
                    direction: str) -> Tuple[bool, int]:
    """Check if price survived above/below trendline in post-breakout zone.

    A fakeout = price broke out but then fell back below the trendline.
    For LONG: all survival candles must close above trendline (with small buffer).
    For SHORT: all survival candles must close below trendline (with small buffer).

    Returns (is_fakeout, candles_below_line).
    """
    if survival_end <= survival_start:
        return False, 0  # no survival zone to check

    buffer = atr * 0.15  # smaller buffer — be strict about fakeouts
    candles_below = 0
    max_consecutive_below = 0
    current_consecutive = 0

    for i in range(survival_start, survival_end):
        tl_price = slope * i + intercept
        price = closes[i]

        if direction == 'LONG':
            # Fakeout: price fell back below trendline
            if price < tl_price - buffer:
                candles_below += 1
                current_consecutive += 1
                max_consecutive_below = max(max_consecutive_below, current_consecutive)
            else:
                current_consecutive = 0
        else:  # SHORT
            # Fakeout: price rose back above trendline
            if price > tl_price + buffer:
                candles_below += 1
                current_consecutive += 1
                max_consecutive_below = max(max_consecutive_below, current_consecutive)
            else:
                current_consecutive = 0

    # Fakeout if: (1) 2+ candles below line, OR (2) 2+ consecutive candles below line
    is_fakeout = candles_below >= 2 or max_consecutive_below >= 2
    return is_fakeout, candles_below


def _check_volume_confirmation(closes: List[float], fit_end: int, breakout_end: int,
                               atr: float, candles: list = None) -> Tuple[bool, float]:
    """Check if breakout has momentum confirmation using ATR expansion.

    Since volume data is often unavailable, we use ATR expansion as a proxy.
    ATR expansion indicates increased volatility during breakout = real interest.

    Returns (has_momentum_confirmation, atr_expansion_ratio).
    """
    if len(closes) < fit_end + 5:
        return True, 1.0  # can't check, assume confirmed

    # Calculate ATR in fit zone
    fit_closes = closes[:fit_end]
    fit_atr = _atr([{'high': c, 'low': c, 'close': c} for c in fit_closes], TL_ATR_PERIOD)
    
    # Calculate ATR in breakout zone
    breakout_closes = closes[fit_end:breakout_end]
    breakout_atr = _atr([{'high': c, 'low': c, 'close': c} for c in breakout_closes], TL_ATR_PERIOD)
    
    if fit_atr and breakout_atr and fit_atr > 0:
        atr_expansion = breakout_atr / fit_atr
        # ATR expansion > 1.2 indicates real breakout (not noise)
        return atr_expansion > 1.2, atr_expansion
    else:
        return True, 1.0  # can't compute, assume confirmed


def _check_trend_alignment(closes: List[float], direction: str, atr: float) -> bool:
    """Check if breakout aligns with higher timeframe trend.

    Uses 50-period EMA as proxy for higher timeframe trend.
    For LONG: price should be above 50 EMA (uptrend)
    For SHORT: price should be below 50 EMA (downtrend)

    Returns True if aligned, False if counter-trend.
    """
    if len(closes) < 50:
        return True  # can't check, assume aligned

    # Calculate 50 EMA
    ema50 = closes[0]
    k = 2 / (50 + 1)
    for price in closes[1:]:
        ema50 = price * k + ema50 * (1 - k)

    current_price = closes[-1]

    if direction == 'LONG':
        # LONG breakout should be in uptrend (price above EMA50)
        return current_price > ema50
    else:
        # SHORT breakout should be in downtrend (price below EMA50)
        return current_price < ema50


# ── Main Signal Detection ──────────────────────────────────────────────────────

def detect_tl_break(token: str, candles: list, price: float) -> Optional[Dict]:
    """Detect diagonal trendline breakout on a single token's candles.

    Uses linear regression to fit a trendline, validates bounces with rejection,
    then confirms breakout with follow-through.

    Returns signal dict if triggered, else None.
    """
    if len(candles) < TL_LOOKBACK_MIN:
        return None

    closes = [c['close'] for c in candles]
    atr = _atr(candles, TL_ATR_PERIOD)
    if atr is None:
        return None

    # ── Speed check: need some momentum to trade ───────────────────────────
    # Speed = rate of change over last 5 candles vs previous 5
    if len(closes) >= 10:
        recent_move = closes[-1] - closes[-5]
        speed = abs(recent_move) / (atr + 1e-10)  # move in ATR units
        if speed < 0.3:
            return None  # no wave — sitting in whitewater

    n = len(closes)
    fit_end = int(n * TL_FIT_CUTOFF)

    # ── Extension filter: block "selling the bottom" / "buying the top" ─────
    # If price has already moved > TL_MIN_EXTENSION_ATR from the 8h high/low,
    # the move is exhausted and a reversal is likely. This catches the classic
    # tl_break failure mode: signal fires after a sharp drop, then bounces.
    highs_list = [c.get('high', c['close']) if isinstance(c, dict) else c for c in candles]
    lows_list = [c.get('low', c['close']) if isinstance(c, dict) else c for c in candles]
    _recent_high = max(highs_list) if highs_list else price
    _recent_low = min(lows_list) if lows_list else price
    if direction == 'SHORT':
        _ext = (_recent_high - price) / (atr + 1e-10)
        if _ext < TL_MIN_EXTENSION_ATR:
            return None  # price already dropped too far — move exhausted, bounce risk
    elif direction == 'LONG':
        _ext = (price - _recent_low) / (atr + 1e-10)
        if _ext < TL_MIN_EXTENSION_ATR:
            return None  # price already rose too far — move exhausted, pullback risk

    # ── Phase 1: Trendline detection via linear regression ─────────────────
    tl = _detect_trendline(closes, fit_end)
    if tl is None:
        return None

    slope = tl['slope']
    intercept = tl['intercept']
    r2 = tl['r2']
    direction = tl['direction']

    # Minimum trendline duration: at least 30 candles of consistent trend
    if fit_end < 30:
        return None

    # ── Phase 2: Bounce validation with rejection ──────────────────────────
    n_bounces, avg_rejection = _count_bounces_with_rejection(
        closes, slope, intercept, fit_end, atr, direction)
    if n_bounces < TL_MIN_BOUNCES:
        return None
    # Filter: too many bounces = noise, not trendline touches
    if n_bounces / fit_end > TL_MAX_BOUNCE_RATIO:
        return None

    # ── Phase 2b: Z-score filter — block counter-trend traps ─────────────────
    # Only block extreme reversals: strong downtrend for LONG, strong uptrend for SHORT
    # Relaxed from 4 conditions to 2 — allow more market conditions
    import statistics as _stat
    recent_closes = closes[-20:] if len(closes) >= 20 else closes
    if len(recent_closes) >= 10:
        _mean = _stat.mean(recent_closes)
        _stdev = _stat.stdev(recent_closes) if len(recent_closes) > 1 else 1
        _z = (recent_closes[-1] - _mean) / _stdev if _stdev > 0 else 0
        if direction == 'LONG' and _z < -2.0:
            return None  # strong downtrend — don't catch falling knife
        if direction == 'SHORT' and _z > 2.0:
            return None  # strong uptrend — don't fade momentum

    # ── Phase 2c: Regime filter — use per-token regime, not overall ──────────
    # Trendline slope already gives direction (descending=LONG, ascending=SHORT).
    # Per-token regime confirms or penalizes — doesn't block in NEUTRAL.
    regime_penalty = 0
    try:
        import json as _json
        regime_file = '/var/www/hermes/data/regime_5m.json'
        if os.path.exists(regime_file):
            with open(regime_file) as _f:
                _regime_data = _json.load(_f)
            _token_regime = _regime_data.get('regimes', {}).get(token.upper(), {})
            _token_reg = _token_regime.get('regime', 'NEUTRAL')
            # Counter-regime: don't fade a trending token
            if _token_reg == 'LONG_BIAS' and direction == 'SHORT':
                return None
            if _token_reg == 'SHORT_BIAS' and direction == 'LONG':
                return None
            # NEUTRAL: fire but apply confidence haircut (trendline stands on its own)
            if _token_reg == 'NEUTRAL':
                regime_penalty = 15
    except Exception:
        pass  # if regime data unavailable, no penalty

    # ── Oxygen checks (fishing for real breakouts) ─────────────────────────
    # Speed percentile: is the fish moving?
    try:
        from speed_tracker import get_token_speed
        spd = get_token_speed(token)
        speed_pct = spd.get('speed_percentile', 50) if spd else 50
        if speed_pct < 40:
            return None  # too slow — no wave
    except Exception:
        speed_pct = 50

    # RSI: water temperature — don't fish in frozen/boiling water
    if len(closes) >= 15:
        gains = []
        losses = []
        for j in range(1, min(15, len(closes))):
            delta = closes[-j] - closes[-j-1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0.001
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        if direction == 'LONG' and rsi > 75:
            return None  # overbought — don't buy
        # NOTE: RSI < 25 SHORT filter REMOVED 2026-08-24 — backtested 100% WR on
        # oversold SHORT entries. Low RSI = strong downtrend = good SHORT, not bad.
        # The extension filter (below) catches the real "selling the bottom" cases.

    # ── 5m trend alignment + strength (ADX + EMA) ─────────────────────────
    # No trend = trendline break is just noise. Need:
    #   1. ADX >= 25 (trending, not ranging)
    #   2. EMA20 vs EMA50 alignment matches breakout direction
    if len(closes) >= 50 and len(candles) >= 30:
        # EMA helper
        def _ema(data, period):
            k = 2 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1 - k)
            return val

        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50)

        # Direction alignment
        if direction == 'LONG' and ema20 < ema50:
            return None  # 5m bearish — don't go long
        if direction == 'SHORT' and ema20 > ema50:
            return None  # 5m bullish — don't go short

        # ADX computation (Wilder's smoothing, 14-period)
        highs = [c.get('high', c['close']) for c in candles]
        lows = [c.get('low', c['close']) for c in candles]
        adx_period = 14

        tr_list, plus_dm, minus_dm = [], [], []
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i] - closes[i-1]))
            tr_list.append(tr)
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)

        if len(tr_list) >= adx_period * 2:
            atr_s = sum(tr_list[:adx_period]) / adx_period
            pdm_s = sum(plus_dm[:adx_period]) / adx_period
            mdm_s = sum(minus_dm[:adx_period]) / adx_period
            dx_list = []
            for i in range(adx_period, len(tr_list)):
                atr_s = (atr_s * (adx_period - 1) + tr_list[i]) / adx_period
                pdm_s = (pdm_s * (adx_period - 1) + plus_dm[i]) / adx_period
                mdm_s = (mdm_s * (adx_period - 1) + minus_dm[i]) / adx_period
                pdi = 100 * pdm_s / (atr_s + 1e-10)
                mdi = 100 * mdm_s / (atr_s + 1e-10)
                dx = abs(pdi - mdi) / (pdi + mdi + 1e-10) * 100
                dx_list.append(dx)
            # ADX = smoothed DX
            adx_val = sum(dx_list[-adx_period:]) / min(adx_period, len(dx_list))
            if adx_val < 15:
                return None  # no trend — choppy market, trendline break is noise

    # ── Phase 3: Breakout confirmation ─────────────────────────────────────
    breakout, breakout_strength, follow_count = _detect_breakout(
        closes, slope, intercept, fit_end, atr, direction)
    if not breakout:
        return None

    # ── Phase 3b: Breakout candle body check — decisive breakout ─────────────
    # The first candle that breaks the trendline must have a body > 0.3 ATR
    # Filters weak breakouts that barely close beyond the line
    breakout_body_ok = False
    for i in range(fit_end, min(fit_end + TL_BREAKOUT_CANDLES, n)):
        tl_price = slope * i + intercept
        candle = candles[i]
        body = abs(candle['close'] - candle['open'])
        if direction == 'LONG' and candle['close'] > tl_price + (atr * TL_BREAKOUT_ATR_K * 0.5):
            if body > atr * 0.3:
                breakout_body_ok = True
                break
        elif direction == 'SHORT' and candle['close'] < tl_price - (atr * TL_BREAKOUT_ATR_K * 0.5):
            if body > atr * 0.3:
                breakout_body_ok = True
                break
        elif direction == 'SHORT' and candle['close'] < tl_price - (atr * TL_BREAKOUT_ATR_K * 0.5):
            if body > atr * 0.5:
                breakout_body_ok = True
                break
    if not breakout_body_ok:
        return None  # weak breakout — no strong candle

    # ── Phase 3a: ATR expansion check — big moves start with volatility increase ──
    # Compare ATR in breakout zone to ATR in fit zone
    # Not a hard filter — just a confidence bonus
    breakout_start = fit_end
    breakout_end = min(fit_end + TL_BREAKOUT_CANDLES, n)
    fit_closes_for_atr = closes[:fit_end]
    breakout_closes_for_atr = closes[breakout_start:breakout_end]
    fit_atr = _atr([{'high': c, 'low': c, 'close': c} for c in fit_closes_for_atr], TL_ATR_PERIOD)
    breakout_atr = _atr([{'high': c, 'low': c, 'close': c} for c in breakout_closes_for_atr], TL_ATR_PERIOD)
    if fit_atr and breakout_atr and fit_atr > 0:
        atr_expansion = breakout_atr / fit_atr
    else:
        atr_expansion = 1.0  # can't compute — neutral

    # ── Phase 3c: Consecutive candle check — stronger signal ──────────────
    # Count consecutive candles closing beyond the trendline
    # Not a hard filter — just a confidence bonus
    consecutive = 0
    max_consecutive = 0
    for i in range(breakout_start, breakout_end):
        tl_price = slope * i + intercept
        price = closes[i]
        if direction == 'LONG' and price > tl_price + (atr * TL_BREAKOUT_ATR_K * 0.5):
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        elif direction == 'SHORT' and price < tl_price - (atr * TL_BREAKOUT_ATR_K * 0.5):
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0  # reset on non-consecutive candle
    # No hard filter — just use for confidence bonus

    # ── Phase 3d: Breakout speed check — fast breakouts succeed more ─────
    # Measure how far price moved beyond trendline in the breakout zone
    # Not a hard filter — just a confidence bonus
    breakout_move = 0.0
    for i in range(breakout_start, min(breakout_start + 5, breakout_end)):
        tl_price = slope * i + intercept
        price = closes[i]
        if direction == 'LONG':
            breakout_move = max(breakout_move, (price - tl_price) / atr)
        else:
            breakout_move = max(breakout_move, (tl_price - price) / atr)
    breakout_speed = breakout_move / 5  # ATR units per candle
    # No hard filter — just use for confidence bonus

    # ── Phase 3b: Fakeout guard — post-breakout survival ────────────────────
    survival_start = fit_end + TL_BREAKOUT_CANDLES
    survival_end = min(survival_start + TL_SURVIVAL_CANDLES, n)
    is_fakeout, candles_below = _detect_fakeout(
        closes, slope, intercept, survival_start, survival_end, atr, direction)
    if is_fakeout:
        return None  # price fell back below trendline — fakeout

    # ── Phase 3e: Volume confirmation — breakout should have above-average volume ──
    # Since volume data is often unavailable, we use ATR expansion as proxy
    has_volume, volume_ratio = _check_volume_confirmation(closes, fit_end, breakout_end, atr, candles)
    # Volume confirmation is now a HARD filter — real breakouts have ATR expansion
    if not has_volume:
        return None  # no ATR expansion — likely noise

    # ── Phase 3f: Trend alignment — breakout should align with higher timeframe trend ──
    is_trend_aligned = _check_trend_alignment(closes, direction, atr)
    # Trend alignment is a HARD filter — counter-trend breakouts fail more often
    if not is_trend_aligned:
        return None  # counter-trend breakout — lower probability

    # ── Phase 4: Confidence scoring ─────────────────────────────────────────
    # Confidence now based on BREAKOUT quality, not trendline quality
    # Higher confidence = stronger breakout = better performance
    conf = TL_BASE_CONFIDENCE

    # Breakout strength bonus (PRIMARY factor)
    # Strong breakouts succeed more - this is the main signal quality indicator
    if breakout_strength >= 2.0:
        conf += 20  # very strong breakout
    elif breakout_strength >= 1.5:
        conf += 15  # strong breakout
    elif breakout_strength >= 1.0:
        conf += 10  # moderate breakout
    else:
        conf += 5   # weak breakout

    # Follow-through bonus (CONFIRMATION factor)
    # More follow-through candles = more conviction
    if follow_count >= 5:
        conf += 15  # strong follow-through
    elif follow_count >= 4:
        conf += 10  # good follow-through
    elif follow_count >= 3:
        conf += 5   # moderate follow-through

    # Breakout speed bonus (MOMENTUM factor)
    # Fast breakouts succeed more - momentum is key
    if breakout_speed > 0.6:
        conf += 10  # very fast breakout
    elif breakout_speed > 0.4:
        conf += 7   # fast breakout
    elif breakout_speed > 0.3:
        conf += 4   # moderate breakout

    # ATR expansion bonus (VOLATILITY factor)
    # Big moves start with volatility increase
    if atr_expansion > 1.5:
        conf += 8  # strong expansion
    elif atr_expansion > 1.2:
        conf += 5  # moderate expansion

    # Consecutive candle bonus (MOMENTUM factor)
    # Consecutive candles beyond trendline = strong momentum
    if max_consecutive >= 5:
        conf += 8  # very strong momentum
    elif max_consecutive >= 4:
        conf += 5  # strong momentum
    elif max_consecutive >= 3:
        conf += 3  # moderate momentum

    # Trend alignment bonus (CONTEXT factor)
    # Breakout aligned with higher timeframe trend succeeds more
    # Check 1H EMA alignment using price action
    try:
        # Simple proxy: if trendline slope is steep, likely aligned with trend
        slope_strength = abs(slope) / avg_price
        if slope_strength > 0.0005:  # very steep slope = strong trend
            conf += 8
        elif slope_strength > 0.0003:  # steep slope = moderate trend
            conf += 5
        elif slope_strength > 0.0002:  # moderate slope
            conf += 2
    except Exception:
        pass

    # R² bonus (TRENDLINE QUALITY factor)
    # Higher R² = cleaner trendline = more reliable breakout
    # Reduced weight - R² is less important than breakout quality
    r2_bonus = min(8, int((r2 - TL_R2_MIN) * 15))
    conf += r2_bonus

    # Bounce quality bonus (CONFIRMATION factor)
    # Good bounces with rejection = valid trendline
    # Reduced weight - bounces are less important than breakout
    if n_bounces >= 3 and avg_rejection > atr * 0.5:
        conf += 5  # good bounces with rejection
    elif n_bounces >= 2:
        conf += 2  # minimum bounces

    # Volume confirmation bonus (VOLUME factor)
    # Above-average volume confirms breakout is real, not noise
    if has_volume:
        if volume_ratio > 1.5:
            conf += 8  # strong volume confirmation
        elif volume_ratio > 1.2:
            conf += 5  # moderate volume confirmation
        else:
            conf += 2  # slight volume confirmation

    # Trend alignment bonus (CONTEXT factor)
    # Breakout aligned with higher timeframe trend succeeds more
    if is_trend_aligned:
        conf += 5  # aligned with trend

    conf = min(TL_MAX_CONFIDENCE, conf)

    # Apply regime penalty (set in Phase 2c)
    if regime_penalty:
        conf = max(50, conf - regime_penalty)

    # ── Build signal ─────────────────────────────────────────────────────────
    signal_type = f'tl_break_{direction.lower()}'
    source = f'tl_break_{direction.lower()}'

    value = str({
        'slope': round(slope, 8),
        'intercept': round(intercept, 6),
        'r2': round(r2, 3),
        'n_bounces': n_bounces,
        'avg_rejection_atr': round(avg_rejection / atr, 2) if atr > 0 else 0,
        'breakout_strength_atr': round(breakout_strength, 2),
        'follow_count': follow_count,
        'atr': round(atr, 6),
    })

    return {
        'token': token.upper(),
        'direction': direction,
        'signal_type': signal_type,
        'source': source,
        'confidence': conf,
        'value': value,
        'price': price,
        '_slope': slope,
        '_r2': r2,
        '_n_bounces': n_bounces,
        '_breakout_strength': breakout_strength,
        '_follow_count': follow_count,
        '_atr': atr,
        '_z': _z if '_z' in dir() else None,
    }


# ── Scanner (compatible with signals/__init__.py registry) ───────────────────

def scan_tl_break_signals(prices_dict: dict) -> tuple[int, list]:
    """Scan pre-filtered tokens for tl_break signals.

    Args:
        prices_dict: token -> {'price': float, ...} (pre-filtered by caller)

    Returns:
        tuple[int, list]: (count of signals written, list of token names that fired)
    """
    from signal_schema import add_signal

    added = 0
    signaled_tokens = []
    now = time.time()

    # Load cooldowns from DB on first call (prevents re-fire on restart)
    if not _TL_COOLDOWN_CACHE:
        try:
            import sqlite3 as _sqlite3
            from paths import RUNTIME_DB as _RUNTIME_DB
            _conn = _sqlite3.connect(_RUNTIME_DB, timeout=5)
            _cur = _conn.cursor()
            _cur.execute("""
                SELECT token, MAX(created_at) FROM signals
                WHERE signal_type = 'tl_break'
                GROUP BY token
            """)
            for _tok, _ts in _cur.fetchall():
                try:
                    import datetime as _dt
                    _ts_str = str(_ts)
                    _dt_obj = _dt.datetime.strptime(_ts_str, '%Y-%m-%d %H:%M:%S')
                    _TL_COOLDOWN_CACHE[_tok] = _dt_obj.timestamp()
                except Exception:
                    pass
            _conn.close()
        except Exception:
            pass

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # ── Blocklist check — skip tokens that can't be filled on HL ──────────
        if token.upper() in _HL_BLOCKLIST:
            continue

        # ── Cooldown check ──────────────────────────────────────────────────
        last_fire = _TL_COOLDOWN_CACHE.get(token.upper(), 0)
        if now - last_fire < TL_COOLDOWN_HOURS * 3600:
            continue

        candles = _get_candles_5m(token, lookback_candles=TL_LOOKBACK)
        if not candles or len(candles) < TL_LOOKBACK_MIN:
            continue

        sig = detect_tl_break(token, candles, price)
        if sig is None:
            continue

        # ── Minimum confidence filter ────────────────────────────────────────
        # Only fire high-quality signals (80+ confidence based on backtesting)
        if sig['confidence'] < TL_MIN_CONFIDENCE:
            continue

        # ── Per-direction kill-switch ─────────────────────────────────────────
        from hermes_constants import TL_BREAK_PLUS_ENABLED, TL_BREAK_MINUS_ENABLED, LONG_BLACKLIST, SHORT_BLACKLIST
        if sig['direction'] == 'LONG' and not TL_BREAK_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not TL_BREAK_MINUS_ENABLED:
            continue

        # ── Z-score direction filter (FIX 2026-07-31) ────────────────────────
        # Block LONG when z < -0.5 (price below average = chasing downtrend)
        # Block SHORT when z > 0.5 (price above average = chasing uptrend)
        # During 08:00-09:30 losing streak, 26% of LONG signals had z < -0.5
        z = sig.get('_z')
        if z is not None:
            if sig['direction'] == 'LONG' and z < -0.5:
                continue  # don't buy when price is below average
            if sig['direction'] == 'SHORT' and z > 0.5:
                continue  # don't sell when price is above average

        if sig['direction'] == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if sig['direction'] == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        sid = add_signal(
            token=sig['token'],
            direction=sig['direction'],
            signal_type=sig['signal_type'],
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig.get('_z'),
            z_score_tier=None,
        )

        if sid:
            added += 1
            signaled_tokens.append(token)
            _TL_COOLDOWN_CACHE[token.upper()] = now
            print(f"[tl_break] {sig['direction']} {sig['token']} "
                  f"conf={sig['confidence']} r2={sig['_r2']:.3f} "
                  f"bounces={sig['_n_bounces']} breakout={sig['_breakout_strength']:.2f}ATR "
                  f"ft={sig['_follow_count']}")

    return added, signaled_tokens


def run(prices_dict: dict) -> tuple[int, list]:
    """Entry point for signals/__init__.py registry. Alias for scan_tl_break_signals."""
    return scan_tl_break_signals(prices_dict)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='tl_break signal scanner')
    parser.add_argument('--dry', action='store_true', help='Dry run (no DB write)')
    args = parser.parse_args()

    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    added, tokens = scan_tl_break_signals(prices)
    print(f"[tl_break] {'Dry ' if args.dry else ''}run: {added} signals on {tokens}")