#!/usr/bin/env python3
"""
ma_cross_signals.py — 10 EMA × 200 EMA Crossover Signal Scanner for Hermes.

Detects golden cross (10 EMA crosses above 200 EMA = LONG) and death cross
(10 EMA crosses below 200 EMA = SHORT) on 1m candles. Primary signal —
competes equally in hot-set scoring.

Architecture:
  - Reads 1m candles from price_history via signal_schema.get_ohlcv_1m()
  - Computes EMA(10) and EMA(200) from close prices
  - Fires on crossover events with confidence scoring
  - Writes via signal_schema.add_signal() (blacklists, merge logic applied)

Signal types:
  - ma_cross: direction=LONG → golden cross (10 EMA crosses above 200 EMA)
  - ma_cross: direction=SHORT → death cross (10 EMA crosses below 200 EMA)
"""

import sys
import os
import sqlite3
import time
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

MA_FAST_PERIOD        = 10   # fast EMA period
MA_SLOW_PERIOD        = 200  # slow EMA period
MA_SIGNAL_TYPE        = 'ma_cross'
MA_SOURCE_PREFIX      = 'ma'
MA_LOOKBACK_CANDLES  = 250  # need ≥ slow_period for EMA warmup + cross detection
MA_COOLDOWN_MINUTES  = 15    # cooldown between signals per token+direction
MA_MIN_CONFIDENCE    = 50    # global floor (matches signal_schema minimum)
MA_MAX_CONFIDENCE    = 88    # cap
MA_BASE_CONFIDENCE   = 65    # base confidence for any cross
MA_SEP_BONUS_MAX     = 15    # max bonus from EMA separation
MA_RECENCY_BONUS_MAX = 10    # max bonus for fresh cross

# ── EMA Calculation ───────────────────────────────────────────────────────────

def _ema(values: list, period: int) -> Optional[float]:
    """Compute EMA(period) from a list of prices (oldest first).

    Returns the most recent EMA value, or None if not enough data.
    """
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def _ema_series(values: list, period: int) -> list:
    """Compute EMA series — returns EMA value at each index (oldest first).

    Returns a list with None for indices < period-1, then EMA values.
    """
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


# ── Cross Detection ────────────────────────────────────────────────────────────

def detect_ma_cross(token: str, candles: list, price: float) -> Optional[dict]:
    """Detect 10/200 EMA crossover on 1m candles.

    Args:
        token:  token symbol (e.g. 'BTC')
        candles: list of OHLCV dicts from price_history (oldest first)
        price:  current price (most recent close from candles)

    Returns:
        Signal dict or None if no cross detected.
        {
            'direction':  'LONG' or 'SHORT',
            'confidence': int (65-88),
            'source':     str  (e.g. 'ma-golden5'),
            'ema10':      float,
            'ema200':     float,
            'sep_pct':    float,   # EMA separation as % of price
            'bars_since': int,     # bars since cross
        }
    """
    n = len(candles)
    min_required = MA_SLOW_PERIOD + MA_FAST_PERIOD  # 210

    if n < min_required:
        return None

    # Extract closes oldest-first
    closes = [c['close'] for c in candles]

    # Compute EMA series for both periods
    ema10_series = _ema_series(closes, MA_FAST_PERIOD)
    ema200_series = _ema_series(closes, MA_SLOW_PERIOD)

    # Build aligned series by candle index
    # EMA10 is valid at candle indices [9..n-1], EMA200 at [199..n-1]
    # Their intersection is [199..n-1] — the only indices where both are valid
    ema10_by_idx  = {i: ema10_series[i]  for i in range(len(ema10_series))  if ema10_series[i]  is not None}
    ema200_by_idx = {i: ema200_series[i] for i in range(len(ema200_series)) if ema200_series[i] is not None}

    common_indices = sorted(set(ema10_by_idx.keys()) & set(ema200_by_idx.keys()))
    if len(common_indices) < 2:
        return None

    # Walk through common indices in ascending order, detect cross
    cross_idx = None
    cross_dir = None

    for j in range(1, len(common_indices)):
        idx_prev = common_indices[j - 1]
        idx_cur  = common_indices[j]
        e10_prev  = ema10_by_idx[idx_prev]
        e10_cur   = ema10_by_idx[idx_cur]
        e200_prev = ema200_by_idx[idx_prev]
        e200_cur  = ema200_by_idx[idx_cur]

        # Golden cross: 10 EMA crosses ABOVE 200 EMA
        if e10_prev <= e200_prev and e10_cur > e200_cur:
            cross_idx = idx_cur
            cross_dir = 'LONG'
            break
        # Death cross: 10 EMA crosses BELOW 200 EMA
        if e10_prev >= e200_prev and e10_cur < e200_cur:
            cross_idx = idx_cur
            cross_dir = 'SHORT'
            break

    if cross_idx is None:
        return None

    # Most recent EMA values
    ema10  = ema10_by_idx[common_indices[-1]]
    ema200 = ema200_by_idx[common_indices[-1]]

    # Bars since cross — cross_idx is absolute candle index (0 = oldest)
    bars_since = max(len(closes) - 1 - cross_idx, 0)

    # Confidence scoring
    sep_pct = abs(ema10 - ema200) / price * 100.0
    sep_bonus    = min(sep_pct * 3, MA_SEP_BONUS_MAX)        # up to +15 for 5%+ separation
    recency_bonus = max(MA_RECENCY_BONUS_MAX - bars_since, 0)  # up to +10 for fresh cross

    confidence = int(min(
        MA_BASE_CONFIDENCE + sep_bonus + recency_bonus,
        MA_MAX_CONFIDENCE
    ))

    # Source tag: ma-golden{N} (LONG) or ma-death{N} (SHORT)
    prefix = 'golden' if cross_dir == 'LONG' else 'death'
    source = f'{MA_SOURCE_PREFIX}-{prefix}{bars_since}'

    return {
        'direction':  cross_dir,
        'confidence': confidence,
        'source':     source,
        'ema10':      round(ema10, 6),
        'ema200':     round(ema200, 6),
        'sep_pct':    round(sep_pct, 4),
        'bars_since': bars_since,
        'value':      float(confidence),
    }


# ── Candle data (price_history — live 1m prices, updated every minute) ─────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

def _get_candles_1m(token: str, lookback: int = MA_LOOKBACK_CANDLES) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices — the ONLY reliable
    source for live signal generation. timestamps are in SECONDS (Unix time).

    Returns list of {close, timestamp} dicts, oldest first.
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
            print(f"  [ma_cross] {token}: stale price_history (last ts {most_recent_ts}, skipping)")
            return []

        # Return in same format as the old candles dict (close key for compatibility)
        return [{'close': r[1], 'timestamp': r[0]} for r in rows]

    except Exception as e:
        print(f"  [ma_cross] price_history error for {token}: {e}")
        return []


# ── Main scanner ────────────────────────────────────────────────────────────────

def scan_ma_cross_signals(prices_dict: dict) -> list:
    """Scan pre-filtered tokens for MA cross signals and write to DB.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here. This function
    focuses purely on MA cross detection and DB writing.

    Args:
        prices_dict: token -> {'price': float, ...}  (pre-filtered by caller)

    Returns:
        list — [{'token': str, 'direction': str}] for each signal successfully written.
    """
    from signal_schema import add_signal

    fired = []

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        candles = _get_candles_1m(token, lookback=MA_LOOKBACK_CANDLES)
        if not candles or len(candles) < MA_SLOW_PERIOD + MA_FAST_PERIOD:
            continue

        sig = detect_ma_cross(token, candles, price)
        if sig is None:
            continue

        sid = add_signal(
            token=token.upper(),
            direction=sig['direction'],
            signal_type=MA_SIGNAL_TYPE,
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
            fired.append({'token': token.upper(), 'direction': sig['direction']})

    return fired


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import get_all_latest_prices, init_db

    init_db()
    prices = get_all_latest_prices()

    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[ma_cross] Testing on {len(test_tokens)} tokens...")
    n = scan_ma_cross_signals(test_tokens)
    print(f"[ma_cross] Done. {n} signals emitted.")
