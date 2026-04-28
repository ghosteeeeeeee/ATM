#!/usr/bin/env python3
"""
r2_trend_signals.py — R² Trend Confirmation Signal Scanner for Hermes.

Uses OLS linear regression on 1m close prices to detect confirmed downtrends.
Signal fires when:
  1. R² >= threshold (confirmed trend = not chop)
  2. Slope is negative (downtrend)
  3. Price is below the regression line (bearish alignment)

Based on backtest findings (2026-04-20):
  - 10 tokens, 1m candles, window=16, R²>=0.60
  - SHORT only: 38.3% WR, +2843% net P&L (10 tokens)
  - Exit on slope flipping positive (reverse cross)
  - R² acts as a trend quality filter — rejects chop, confirms real trends

Architecture:
  - Reads 1m candles from price_history via signal_schema.get_ohlcv_1m()
  - Computes rolling OLS regression (window=16 bars)
  - Short signal when: r2 >= threshold AND slope < 0 AND price < intercept
  - Confidence: base 65 + R² bonus + recency bonus
  - Writes via signal_schema.add_signal()

Signal type: r2_trend (SHORT only)
"""

import sqlite3
import sys
import os
import time
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

R2_WINDOW             = 16    # regression window in bars (16 × 1m = 16 min)
R2_THRESHOLD         = 0.60  # minimum R² to confirm a real trend
R2_SIGNAL_TYPE       = 'r2_trend'
R2_SOURCE_PREFIX     = 'r2s'    # r2-short source tag
R2_LOOKBACK_CANDLES  = 50    # enough for regression + exit scan
R2_COOLDOWN_MINUTES  = 15    # cooldown between signals per token
R2_MIN_CONFIDENCE    = 50    # global floor
R2_MAX_CONFIDENCE    = 88    # cap
R2_BASE_CONFIDENCE   = 65    # base confidence
R2_R2_BONUS_MAX      = 15    # max bonus for high R²
R2_RECENCY_BONUS_MAX = 10    # max bonus for fresh cross

# ── Linear Regression ─────────────────────────────────────────────────────────

def _ols_params(y_vals: list) -> tuple:
    """Compute OLS slope, intercept, R² from a list of prices (oldest first).

    Returns (slope, intercept, r2). intercept is the predicted value at x=n-1.
    """
    n = len(y_vals)
    if n < 3:
        return 0.0, y_vals[-1] if y_vals else 0.0, 0.0
    x = list(range(n))
    xm = (n - 1) / 2.0
    ym = sum(y_vals) / n
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y_vals))
    den = sum((xi - xm) ** 2 for xi in x)
    if den == 0:
        return 0.0, ym, 0.0
    b = num / den
    a = ym - b * xm
    ss_res = sum((yi - (b * xi + a)) ** 2 for xi, yi in zip(x, y_vals))
    ss_tot = sum((yi - ym) ** 2 for yi in y_vals)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return b, a, r2


def _precompute_x(window: int) -> tuple:
    """Precompute x stats for fast rolling OLS. Call once per window size."""
    x = list(range(window))
    xm = (window - 1) / 2.0
    x_sq = sum((xi - xm) ** 2 for xi in x)
    return xm, x_sq


# ── Trend Detection ─────────────────────────────────────────────────────────────

def detect_r2_short(token: str, candles: list, price: float) -> Optional[dict]:
    """Detect confirmed downtrend on 1m candles via R² regression.

    Fires SHORT when:
      - R² >= R2_THRESHOLD (confirmed trend, not chop)
      - Slope < 0 (downtrend)
      - Price < regression intercept (bearish alignment across all bars)

    Args:
        token:    token symbol (e.g. 'BTC')
        candles:  list of OHLCV dicts from price_history (oldest first)
        price:    current price (most recent close from candles)

    Returns:
        Signal dict or None if no confirmed downtrend.
        {
            'direction':  'SHORT',
            'confidence': int (65-88),
            'source':     str  (e.g. 'r2s-short5'),
            'slope':      float,
            'r2':         float,
            'intercept':  float,
            'bars_since': int,
        }
    """
    n = len(candles)
    if n < R2_WINDOW * 2:
        return None

    closes = [c['close'] for c in candles]

    # Precompute x stats
    xm, x_sq = _precompute_x(R2_WINDOW)

    # Check most recent window
    y = closes[-R2_WINDOW:]
    slope, intercept, r2 = _ols_params(y)

    if r2 < R2_THRESHOLD or slope >= 0 or closes[-1] >= intercept:
        return None

    # Find how many bars since slope flipped positive (find entry point)
    bars_since = 0
    entry_idx = n - R2_WINDOW
    for i in range(n - R2_WINDOW, -1, -1):
        y_i = closes[i:i + R2_WINDOW]
        b_i, a_i, r2_i = _ols_params(y_i)
        if b_i >= 0 or r2_i < R2_THRESHOLD:
            break
        bars_since = n - R2_WINDOW - i
        entry_idx = i

    bars_since = max(n - R2_WINDOW - entry_idx, 0)

    # Confidence scoring
    r2_bonus     = min((r2 - R2_THRESHOLD) / (1.0 - R2_THRESHOLD) * R2_R2_BONUS_MAX, R2_R2_BONUS_MAX)
    recency_bonus = max(R2_RECENCY_BONUS_MAX - bars_since, 0)

    confidence = int(min(
        R2_BASE_CONFIDENCE + r2_bonus + recency_bonus,
        R2_MAX_CONFIDENCE
    ))

    # Source tag: r2s-short{N}
    source = f'{R2_SOURCE_PREFIX}-short{bars_since}'

    return {
        'direction':  'SHORT',
        'confidence': confidence,
        'source':     source,
        'slope':      round(slope, 8),
        'r2':         round(r2, 4),
        'intercept':   round(intercept, 6),
        'bars_since': bars_since,
        'value':      float(confidence),
    }


# ── Candle data (price_history — live 1m prices, updated every minute) ─────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

def _get_candles_1m(token: str, lookback: int = R2_LOOKBACK_CANDLES) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices — the ONLY reliable source.
    timestamps are in SECONDS (Unix time).

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
            print(f"  [r2_trend] {token}: stale price_history (last ts {most_recent_ts}, skipping)")
            return []

        return [{'close': r[1]} for r in rows]

    except Exception as e:
        print(f"  [r2_trend] price_history error for {token}: {e}")
        return []


# ── Main scanner ────────────────────────────────────────────────────────────────

def scan_r2_trend_signals(prices_dict: dict) -> list:
    """Scan pre-filtered tokens for R² confirmed downtrend signals.

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

        candles = _get_candles_1m(token, lookback=R2_LOOKBACK_CANDLES)
        if not candles or len(candles) < R2_WINDOW * 2:
            continue

        sig = detect_r2_short(token, candles, price)
        if sig is None:
            continue

        sid = add_signal(
            token=token.upper(),
            direction=sig['direction'],
            signal_type=R2_SIGNAL_TYPE,
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
            print(f'  SHORT {token:8s} conf={sig["confidence"]:.0f}% '
                  f'slope={sig["slope"]:.6f} r2={sig["r2"]:.4f} '
                  f'price={price:.6f} intercept={sig["intercept"]:.6f} '
                  f'bars={sig["bars_since"]} '
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
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[r2_trend] Testing on {len(test_tokens)} tokens...")
    n = scan_r2_trend_signals(test_tokens)
    print(f"[r2_trend] Done. {n} signals emitted.")