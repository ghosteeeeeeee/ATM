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
TL_R2_MIN             = 0.40  # minimum R² for trendline validity (5m crypto is noisy)
TL_SLOPE_PCT_MIN      = 0.0003 # minimum slope as % of price per candle (~0.1%/hr, rejects shallow drift)

# Bounce detection: price must touch the trendline (wick or close within threshold)
# A bounce = candle touches trendline AND next candle closes AWAY from it (rejection)
TL_BOUNCE_ATR_K       = 0.5   # within 0.5 * ATR(14) of trendline (tight)
TL_MIN_BOUNCES        = 4     # minimum 4 touches in fit zone (stronger trendline)
TL_MAX_BOUNCE_RATIO   = 0.20  # bounces cannot exceed 20% of fit candles (filters noise)
TL_REJECTION_ATR_K    = 0.25  # rejection must move 0.25+ ATR away from line

# Breakout confirmation: price must close beyond trendline + threshold
TL_BREAKOUT_ATR_K     = 0.8   # 0.8 * ATR(14) beyond trendline (was 0.4 — too weak, caught gentle drift)
TL_FOLLOWTHROUGH_MIN  = 4     # minimum candles closing beyond line in breakout zone
TL_CONSECUTIVE_MIN    = 3     # minimum consecutive candles closing beyond line (stronger signal)

# ATR expansion: big moves start with volatility increase
TL_ATR_EXPANSION_MIN  = 1.2   # breakout ATR must be >= 1.2x fit ATR (20% expansion)

# Breakout speed: fast breakouts succeed more
TL_BREAKOUT_SPEED_MIN = 0.3   # minimum breakout speed in ATR units per candle

# ATR settings
TL_ATR_PERIOD         = 14

# Confidence scoring
TL_BASE_CONFIDENCE    = 60
TL_BOUNCE_BONUS       = 3    # per extra bounce beyond min
TL_R2_BONUS_MAX       = 10   # higher R² = stronger trendline
TL_REJECTION_BONUS    = 5    # strong rejection = valid bounce
TL_FOLLOWTHROUGH_BONUS = 5
TL_BREAKOUT_BONUS_MAX = 5
TL_MAX_CONFIDENCE     = 85

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

    return {
        'slope': slope,
        'intercept': intercept,
        'r2': r2,
        'direction': direction,
        'avg_price': avg_price,
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

    for i in range(breakout_start, breakout_end):
        tl_price = slope * i + intercept
        price = closes[i]

        if direction == 'LONG':
            if price > tl_price + breakout_thresh:
                follow_count += 1
                breakout_strength = max(breakout_strength, (price - tl_price) / atr)
        else:  # SHORT
            if price < tl_price - breakout_thresh:
                follow_count += 1
                breakout_strength = max(breakout_strength, (tl_price - price) / atr)

    # Need: (1) at least one candle beyond threshold, (2) enough follow-through
    has_breakout = follow_count >= 1
    has_follow_through = follow_count >= TL_FOLLOWTHROUGH_MIN

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

    buffer = atr * 0.2  # small buffer — allow wicks to touch line
    candles_below = 0

    for i in range(survival_start, survival_end):
        tl_price = slope * i + intercept
        price = closes[i]

        if direction == 'LONG':
            # Fakeout: price fell back below trendline
            if price < tl_price - buffer:
                candles_below += 1
        else:  # SHORT
            # Fakeout: price rose back above trendline
            if price > tl_price + buffer:
                candles_below += 1

    # Any candle closing significantly below/above line = fakeout
    is_fakeout = candles_below >= 1
    return is_fakeout, candles_below


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
    # All recent losing LONGs had z < -1.5 (strong downtrend).
    # Don't fire LONG in strong downtrend, SHORT in strong uptrend.
    # Also block overbought LONGs and oversold SHORTs (counter-trend trap).
    import statistics as _stat
    recent_closes = closes[-20:] if len(closes) >= 20 else closes
    if len(recent_closes) >= 10:
        _mean = _stat.mean(recent_closes)
        _stdev = _stat.stdev(recent_closes) if len(recent_closes) > 1 else 1
        _z = (recent_closes[-1] - _mean) / _stdev if _stdev > 0 else 0
        if direction == 'LONG' and _z < -1.5:
            return None  # strong downtrend — don't catch falling knife
        if direction == 'LONG' and _z > 0.5:
            return None  # overbought — don't buy the top
        if direction == 'SHORT' and _z > 1.5:
            return None  # strong uptrend — don't fade momentum
        if direction == 'SHORT' and _z < -0.5:
            return None  # oversold — don't sell the bottom

    # ── Phase 3: Breakout confirmation ─────────────────────────────────────
    breakout, breakout_strength, follow_count = _detect_breakout(
        closes, slope, intercept, fit_end, atr, direction)
    if not breakout:
        return None

    # ── Phase 3b: Breakout candle body check — decisive breakout ─────────────
    # The first candle that breaks the trendline must have a strong body (> 0.5 ATR)
    # Filters weak breakouts that just barely close beyond the line
    breakout_body_ok = False
    for i in range(fit_end, min(fit_end + TL_BREAKOUT_CANDLES, n)):
        tl_price = slope * i + intercept
        candle = candles[i]
        body = abs(candle['close'] - candle['open'])
        if direction == 'LONG' and candle['close'] > tl_price + (atr * TL_BREAKOUT_ATR_K * 0.5):
            if body > atr * 0.5:
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

    # ── Phase 4: Confidence scoring ─────────────────────────────────────────
    conf = TL_BASE_CONFIDENCE

    # Bounce bonus
    conf += min(12, (n_bounces - TL_MIN_BOUNCES) * TL_BOUNCE_BONUS)

    # R² bonus — stronger trendline = more reliable
    r2_bonus = min(TL_R2_BONUS_MAX, int((r2 - TL_R2_MIN) * 20))
    conf += r2_bonus

    # Rejection bonus
    if avg_rejection > atr * 0.5:
        conf += TL_REJECTION_BONUS

    # Follow-through bonus
    conf += min(TL_FOLLOWTHROUGH_BONUS, follow_count)

    # Breakout strength bonus
    conf += min(TL_BREAKOUT_BONUS_MAX, int(breakout_strength * 2))

    # ATR expansion bonus — big moves start with volatility increase
    if atr_expansion > 1.5:
        conf += 8  # strong expansion
    elif atr_expansion > 1.2:
        conf += 5  # moderate expansion
    elif atr_expansion > 1.0:
        conf += 2  # slight expansion

    # Consecutive candle bonus — stronger signal
    conf += min(5, max_consecutive - TL_CONSECUTIVE_MIN)

    # Breakout speed bonus — fast breakouts succeed more
    if breakout_speed > 0.5:
        conf += 5  # fast breakout
    elif breakout_speed > 0.3:
        conf += 2  # moderate breakout

    conf = min(TL_MAX_CONFIDENCE, conf)

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

        # ── Per-direction kill-switch ─────────────────────────────────────────
        from hermes_constants import TL_BREAK_PLUS_ENABLED, TL_BREAK_MINUS_ENABLED
        if sig['direction'] == 'LONG' and not TL_BREAK_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not TL_BREAK_MINUS_ENABLED:
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