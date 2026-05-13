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

# ── Constants ─────────────────────────────────────────────────────────────────

# Lookback window (~10h = 120 candles at 5m to capture full diagonal pattern)
TL_LOOKBACK           = 120   # candles — wider window to capture full diagonal
TL_LOOKBACK_MIN       = 80    # minimum required

# Diagonal zone: first 70% of lookback (84 candles = ~7h)
# Breakout zone: last 30% of lookback (36 candles = ~3h)
TL_DIAGONAL_CUTOFF    = 0.70
TL_BREAKOUT_ZONE      = 0.30

# Diagonal detection: anchor at START (closes[0]), measure slope to end of zone
# The diagonal slope magnitude must be large enough to form a visible diagonal
TL_SLOPE_MAG_MIN      = 0.0000005   # barely above zero — filter only flat/ranging

# Bounce detection: price must be close to diagonal (within this ATR multiple)
# A bounce = price touched diagonal and next candle confirms the touch
TL_BOUNCE_ATR_K       = 2.0   # within 2.0 * ATR(14) of diagonal
TL_MIN_BOUNCES        = 2     # minimum 2 bounce touches in diagonal zone

# Breakout confirmation: price must be beyond diagonal by this much
TL_BREAKOUT_ATR_K     = 0.35  # 0.35 * ATR(14) beyond diagonal level
TL_FOLLOWTHROUGH_K    = 0.20  # 20%+ of breakout candles must stay beyond diagonal

# ATR settings
TL_ATR_PERIOD         = 14

# Confidence scoring
TL_BASE_CONFIDENCE    = 64
TL_BOUNCE_BONUS_MAX   = 12   # per extra bounce beyond 2
TL_SLOPE_BONUS_MAX    = 8    # steeper diagonal = more valid
TL_FOLLOWTHROUGH_BONUS = 10
TL_BREAKOUT_BONUS_MAX = 8
TL_MAX_CONFIDENCE     = 88

# Cooldown: don't fire again within this many hours
TL_COOLDOWN_HOURS     = 3

TL_SIGNAL_TYPE        = 'tl_break'
_PRICE_DB             = '/root/.hermes/data/candles.db'

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


def _linear_regression(closes: List[float]) -> Tuple[float, float]:
    """Compute slope and intercept of linear regression on closes."""
    n = len(closes)
    if n < 2:
        return 0.0, (sum(closes) / n) if closes else 0.0
    sum_x = sum(range(n))
    sum_y = sum(closes)
    sum_xy = sum(i * c for i, c in enumerate(closes))
    sum_x2 = sum(i * i for i in range(n))
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 0.0, sum_y / n
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _trendline_price(slope: float, intercept: float, index: int) -> float:
    """Get the trendline price at candle index `index`."""
    return slope * index + intercept


# ── Core Detection ─────────────────────────────────────────────────────────────

def _detect_diagonal(closes: List[float], diag_end: int) -> Optional[Dict]:
    """Detect diagonal trendline from closes[0] to closes[diag_end-1].

    Anchor at START (closes[0]). Direction from slope of start→end.
    Returns dict with slope, intercept, direction, n_touches or None.
    """
    if diag_end < 20:
        return None

    start_price = closes[0]
    end_price = closes[diag_end - 1]

    # Diagonal slope: start to end of zone
    diag_slope = (end_price - start_price) / (diag_end - 1)

    # Slope magnitude check — filter flat/ranging
    if abs(diag_slope) < TL_SLOPE_MAG_MIN:
        return None

    # Direction: down-slope → LONG breakout, up-slope → SHORT breakout
    if diag_slope < 0:
        direction = 'LONG'
    else:
        direction = 'SHORT'

    # ATR for normalization
    # We pass candles directly; caller computes ATR first

    return {
        'slope': diag_slope,
        'start_price': start_price,
        'direction': direction,
        'diag_end': diag_end,
    }


def _count_touches(closes: List[float], diag_slope: float, start_price: float,
                    diag_end: int, atr: float, direction: str) -> Tuple[int, List[int]]:
    """Count how many candles in the diagonal zone bounced off the diagonal line.

    A bounce: price was close to diagonal (within TL_BOUNCE_ATR_K * ATR),
    AND the next candle moves AWAY from the diagonal in the breakout direction.

    For LONG (diagonal slopes down → expect upside break):
      Bounce = candle touched diagonal from below, next candle went above diagonal
    For SHORT (diagonal slopes up → expect downside break):
      Bounce = candle touched diagonal from above, next candle went below diagonal

    Returns: (touch_count, list_of_bounce_indices)
    """
    bounce_indices = []
    thresh = atr * TL_BOUNCE_ATR_K
    diag_end_idx = min(diag_end, len(closes) - 2)  # need i+1

    for i in range(1, diag_end_idx):
        tl_i = start_price + diag_slope * i
        price = closes[i]
        diff = abs(price - tl_i)

        if diff > thresh:
            continue

        next_tl = start_price + diag_slope * (i + 1)
        next_price = closes[i + 1]

        if direction == 'LONG':
            # Bounce = price was below diagonal, next candle breaks above
            if price < tl_i and next_price > next_tl:
                bounce_indices.append(i)
        else:  # SHORT
            # Bounce = price was above diagonal, next candle breaks below
            if price > tl_i and next_price < next_tl:
                bounce_indices.append(i)

    return len(bounce_indices), bounce_indices


def _cluster_bounces_simple(bounce_indices: List[int], closes: List[float],
                             diag_slope: float, start_price: float,
                             atr: float) -> Optional[float]:
    """Cluster bounces by price level. If 2+ bounces are within 3*ATR, valid zone.

    For any pair of bounces with gap <= 3*ATR, compute their midpoint as zone.
    Use the pair with smallest gap as primary zone (most coherent level).
    """
    if len(bounce_indices) < 2:
        return None
    zone_half = atr * 3.0
    bp = sorted([start_price + diag_slope * idx for idx in bounce_indices])

    # Find all pairs with gap <= zone_half, pick the tightest one
    best_zone = None
    best_gap = float('inf')
    for i in range(len(bp)):
        for j in range(i + 1, len(bp)):
            gap = bp[j] - bp[i]
            if gap <= zone_half and gap < best_gap:
                best_gap = gap
                best_zone = (bp[i] + bp[j]) / 2.0

    return best_zone


def _detect_breakout(closes: List[float], diag_slope: float, start_price: float,
                     diag_end: int, breakout_end: int,
                     atr: float, direction: str) -> Tuple[bool, float, float]:
    """Detect if price has broken out of the diagonal in the breakout zone.

    Breakout zone: candles from diag_end to end of window.

    For LONG (diagonal slopes down): price must be ABOVE diagonal + threshold
    For SHORT (diagonal slopes up): price must be BELOW diagonal - threshold

    Returns: (breakout_detected, breakout_pct_atr, follow_through_score)
    """
    if breakout_end <= diag_end:
        return False, 0.0, 0.0

    breakout_candles = closes[diag_end:breakout_end]
    if len(breakout_candles) < 2:
        return False, 0.0, 0.0

    breakout_thresh = atr * TL_BREAKOUT_ATR_K

    if direction == 'LONG':
        # Diagonal level at start of breakout zone
        diag_level = start_price + diag_slope * diag_end
        # Check if most recent candle is above diagonal + threshold
        if breakout_candles[-1] <= diag_level + breakout_thresh:
            return False, 0.0, 0.0
        breakout_pct = (breakout_candles[-1] - diag_level) / atr
    else:  # SHORT
        diag_level = start_price + diag_slope * diag_end
        if breakout_candles[-1] >= diag_level - breakout_thresh:
            return False, 0.0, 0.0
        breakout_pct = (diag_level - breakout_candles[-1]) / atr

    # Follow-through: count candles in breakout zone that stayed beyond diagonal
    follow_count = 0
    for i, price in enumerate(breakout_candles[:-1]):  # exclude last (entry)
        diag_at_i = start_price + diag_slope * (diag_end + i)
        if direction == 'LONG' and price > diag_at_i:
            follow_count += 1
        elif direction == 'SHORT' and price < diag_at_i:
            follow_count += 1

    ft_score = min(1.0, follow_count / max(1, len(breakout_candles) - 1))

    return True, breakout_pct, ft_score


# ── Main Signal Detection ──────────────────────────────────────────────────────

def detect_tl_break(token: str, candles: list, price: float) -> Optional[Dict]:
    """Detect diagonal trendline breakout on a single token's candles.

    Anchor-at-start approach:
      - Trendline anchored at closes[0] (start of diagonal zone)
      - Diagonal slope = (closes[diag_end-1] - closes[0]) / (diag_end - 1)
      - Direction: down-slope → LONG, up-slope → SHORT
      - Breakout: price must be beyond diagonal in last 30% of window

    Returns signal dict if triggered, else None.
    """
    if len(candles) < TL_LOOKBACK_MIN:
        return None

    closes = [c['close'] for c in candles]

    atr = _atr(candles, TL_ATR_PERIOD)
    if atr is None:
        return None

    n = len(closes)
    diag_end = int(n * TL_DIAGONAL_CUTOFF)    # 84 for n=120
    breakout_end = n                          # 120

    # ── Phase 1: Diagonal detection ─────────────────────────────────────────
    diag = _detect_diagonal(closes, diag_end)
    if diag is None:
        return None

    diag_slope = diag['slope']
    start_price = diag['start_price']
    direction = diag['direction']

    # ── Phase 2: Bounce validation — 2+ bounces in diagonal zone ───────────
    n_touches, bounce_indices = _count_touches(
        closes, diag_slope, start_price, diag_end, atr, direction)
    if n_touches < TL_MIN_BOUNCES:
        return None

    # Zone validation: bounces must form a coherent resistance/support level
    # within 3*ATR of each other (diagonal bounces at different times)
    zone_price = _cluster_bounces_simple(bounce_indices, closes, diag_slope, start_price, atr)
    if zone_price is None:
        return None

    # ── Phase 3: Breakout confirmation in last 30% ───────────────────────────
    breakout, breakout_pct_atr, follow_through = _detect_breakout(
        closes, diag_slope, start_price, diag_end, breakout_end, atr, direction)

    if not breakout:
        return None

    # ── Phase 4: Confidence scoring ─────────────────────────────────────────
    base_conf = TL_BASE_CONFIDENCE

    # Bounce bonus: more touches = stronger zone
    bounce_bonus = min(TL_BOUNCE_BONUS_MAX,
                       (n_touches - TL_MIN_BOUNCES) * 5)

    # Slope magnitude bonus
    slope_ratio = min(1.0, (abs(diag_slope) - TL_SLOPE_MAG_MIN) / (TL_SLOPE_MAG_MIN * 5))
    slope_bonus = slope_ratio * TL_SLOPE_BONUS_MAX

    # Follow-through bonus
    ft_bonus = follow_through * TL_FOLLOWTHROUGH_BONUS

    # Breakout strength bonus
    breakout_bonus = min(TL_BREAKOUT_BONUS_MAX, breakout_pct_atr * 3)

    confidence = int(min(TL_MAX_CONFIDENCE,
                         base_conf + bounce_bonus + slope_bonus + ft_bonus + breakout_bonus))

    # ── Build signal ─────────────────────────────────────────────────────────
    signal_type = f'tl_break_{direction.lower()}'
    source = f'tl_break_{direction.lower()}'

    # Compute diagonal level at breakout start for metadata
    diag_level_at_breakout = start_price + diag_slope * diag_end

    value = str({
        'slope': round(diag_slope, 8),
        'diag_start': round(start_price, 6),
        'diag_level_breakout': round(diag_level_at_breakout, 6),
        'n_touches': n_touches,
        'breakout_pct_atr': round(breakout_pct_atr, 2),
        'follow_through': round(follow_through, 2),
        'atr': round(atr, 6),
    })

    return {
        'token': token.upper(),
        'direction': direction,
        'signal_type': signal_type,
        'source': source,
        'confidence': confidence,
        'value': value,
        'price': price,
        '_slope': diag_slope,
        '_start_price': start_price,
        '_n_touches': n_touches,
        '_breakout_pct_atr': breakout_pct_atr,
        '_follow_through': follow_through,
        '_atr': atr,
        '_diag_level_breakout': diag_level_at_breakout,
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

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
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
            z_score=None,
            z_score_tier=None,
        )

        if sid:
            added += 1
            signaled_tokens.append(token)
            print(f"[tl_break] {sig['direction']} {sig['token']} "
                  f"conf={sig['confidence']} slope={sig['_slope']:.7f} "
                  f"touches={sig['_n_touches']} breakout={sig['_breakout_pct_atr']:.2f}ATR "
                  f"ft={sig['_follow_through']:.2f}")

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