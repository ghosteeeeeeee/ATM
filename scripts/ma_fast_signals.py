#!/usr/bin/env python3
"""
ma_fast_signals.py — 8 EMA × 50 EMA Crossover Signal Scanner for Hermes.

Detects EMA(8) crossing EMA(50) on 1m candles for SHORT signals only.
Based on backtest findings (2026-04-20):
  - 163 tokens, 3+ months of 1m data
  - SHORT direction dominates: 27% WR, avg winner >> avg loser, net +4214%
  - LONG direction catastrophic across ALL pairs (-1800% to -4000%)
  - 8/50 is the sweet spot: fast enough to catch reversals early,
    not so fast it's noise
  - Exit on reverse EMA cross (no fixed TP/SL clipping)

Architecture:
  - Reads 1m candles from price_history via signal_schema.get_ohlcv_1m()
  - Computes EMA(8) and EMA(50) from close prices
  - Fires SHORT only on crossover events
  - Separation filter: min 0.05% to avoid noise crosses
  - Writes via signal_schema.add_signal()

Signal type: ma_fast (SHORT only)
"""

import sys
import os
import time
import sqlite3
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

MA_FAST_PERIOD       = 8    # fast EMA period
MA_SLOW_PERIOD       = 50   # slow EMA period
MA_SIGNAL_TYPE       = 'ma_fast'
MA_SOURCE_PREFIX     = 'maf'   # ma-fast source tag prefix
MA_LOOKBACK_CANDLES  = 150   # need ≥ slow_period + buffer for cross detection
MA_COOLDOWN_MINUTES  = 15    # cooldown between signals per token
MA_MIN_CONFIDENCE    = 50    # global floor
MA_MAX_CONFIDENCE    = 88    # cap
MA_BASE_CONFIDENCE   = 65    # base confidence for any cross
MA_SEP_BONUS_MAX     = 15    # max bonus from EMA separation
MA_RECENCY_BONUS_MAX = 10    # max bonus for fresh cross
MA_MIN_SEP_PCT       = 0.05  # minimum EMA separation % to fire (filters noise crosses)

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

def detect_ma_fast_cross(token: str, candles: list, price: float) -> Optional[dict]:
    """Detect 8/50 EMA crossover on 1m candles — SHORT only.

    Args:
        token:    token symbol (e.g. 'BTC')
        candles:  list of OHLCV dicts from price_history (oldest first)
        price:    current price (most recent close from candles)

    Returns:
        Signal dict or None if no cross detected.
        {
            'direction':  'SHORT' (LONG not emitted — longs are catastrophic),
            'confidence': int (65-88),
            'source':     str  (e.g. 'maf-short5'),
            'ema8':       float,
            'ema50':      float,
            'sep_pct':    float,   # EMA separation as % of price
            'bars_since': int,     # bars since cross
        }
    """
    n = len(candles)
    min_required = MA_SLOW_PERIOD + MA_FAST_PERIOD  # 58

    if n < min_required:
        return None

    closes = [c['close'] for c in candles]

    # Compute EMA series for both periods
    ema8_series  = _ema_series(closes, MA_FAST_PERIOD)
    ema50_series = _ema_series(closes, MA_SLOW_PERIOD)

    # Build aligned series by candle index
    # EMA8 valid at candle indices [7..n-1], EMA50 at [49..n-1]
    # Intersection: [49..n-1]
    ema8_by_idx  = {i: ema8_series[i]  for i in range(len(ema8_series))  if ema8_series[i]  is not None}
    ema50_by_idx = {i: ema50_series[i] for i in range(len(ema50_series)) if ema50_series[i] is not None}

    common_indices = sorted(set(ema8_by_idx.keys()) & set(ema50_by_idx.keys()))
    if len(common_indices) < 2:
        return None

    # Walk through common indices in ascending order, detect cross
    cross_idx = None

    for j in range(1, len(common_indices)):
        idx_prev = common_indices[j - 1]
        idx_cur  = common_indices[j]
        ef_prev  = ema8_by_idx[idx_prev]
        ef_cur   = ema8_by_idx[idx_cur]
        es_prev  = ema50_by_idx[idx_prev]
        es_cur   = ema50_by_idx[idx_cur]

        # Death cross: EMA8 crosses BELOW EMA50 = SHORT
        if ef_prev >= es_prev and ef_cur < es_cur:
            cross_idx = idx_cur
            break

    if cross_idx is None:
        return None

    # Most recent EMA values
    ema8  = ema8_by_idx[common_indices[-1]]
    ema50 = ema50_by_idx[common_indices[-1]]

    # Bars since cross
    bars_since = max(len(closes) - 1 - cross_idx, 0)

    # Separation check — filter out noise crosses
    sep_pct = abs(ema8 - ema50) / price * 100.0
    if sep_pct < MA_MIN_SEP_PCT:
        return None

    # Confidence scoring
    sep_bonus     = min(sep_pct * 3, MA_SEP_BONUS_MAX)
    recency_bonus = max(MA_RECENCY_BONUS_MAX - bars_since, 0)

    confidence = int(min(
        MA_BASE_CONFIDENCE + sep_bonus + recency_bonus,
        MA_MAX_CONFIDENCE
    ))

    # Source tag: maf-short{N}
    source = f'{MA_SOURCE_PREFIX}-short{bars_since}'

    return {
        'direction':  'SHORT',
        'confidence': confidence,
        'source':     source,
        'ema8':       round(ema8, 6),
        'ema50':      round(ema50, 6),
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
            print(f"  [ma_fast] {token}: stale price_history (last ts {most_recent_ts}, skipping)")
            return []

        return [{'close': r[1]} for r in rows]

    except Exception as e:
        print(f"  [ma_fast] price_history error for {token}: {e}")
        return []


# ── Main scanner ────────────────────────────────────────────────────────────────

def scan_ma_fast_signals(prices_dict: dict) -> list:
    """Scan pre-filtered tokens for 8/50 MA cross SHORT signals and write to DB.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

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

        sig = detect_ma_fast_cross(token, candles, price)
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
            sep = sig['sep_pct']
            bars = sig['bars_since']
            print(f'  SHORT {token:8s} conf={sig["confidence"]:.0f}% '
                  f'ema8={sig["ema8"]:.4f} ema50={sig["ema50"]:.4f} '
                  f'sep={sep:.3f}% bars={bars} '
                  f'[{sig["source"]}]')

    return fired


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import get_all_latest_prices, init_db

    init_db()
    prices = get_all_latest_prices()

    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'SAGA', 'SCR') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[ma_fast] Testing on {len(test_tokens)} tokens...")
    n = scan_ma_fast_signals(test_tokens)
    print(f"[ma_fast] Done. {n} signals emitted.")
