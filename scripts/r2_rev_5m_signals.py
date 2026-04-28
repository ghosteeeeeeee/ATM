#!/usr/bin/env python3
"""
r2_rev_5m_signals.py — R² Mean Reversion Signal on 5m Candles

Counter-trend / mean reversion strategy:
  LONG:  uptrend (slope > 0) AND price BELOW regression line → pullback to mean, expect bounce
  SHORT: downtrend (slope < 0) AND price ABOVE regression line → rally to mean, expect fade

Based on sweep results (2026-04-21, 416 days of 5m data):
  - LONG: LB=8, R2=0.40 → 21k trades, 52.9% WR, +622% net
  - SHORT: LB=8, R2=0.40 → 20k trades, 54.5% WR, +510% net

Both directions are profitable — combined strategy.

Architecture:
  - Reads 5m candles from candles.db (candles_5m table — not available in signal_schema)
  - Computes rolling OLS regression (window=8 bars = 40 min)
  - Entry: R² >= 0.40 AND slope direction matches AND price deviated from line
  - Exit: reverse cross (price crosses back over/under regression line)
  - Confidence: base 65 + R² bonus + recency bonus
  - Writes via signal_schema.add_signal()

Signal type: r2_rev_5m (LONG + SHORT)
Source: r2r5m-long{N} / r2r5m-short{N}
"""

import sys
import os
import sqlite3
import time
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB
from hermes_constants import CANDLES_STALENESS_SEC

# Alias for backward compatibility with existing local references
_CANDLES_DB = CANDLES_DB

# ── Constants ─────────────────────────────────────────────────────────────────

R2_WINDOW           = 8     # regression window in bars (8 × 5m = 40 min)
R2_THRESHOLD         = 0.40  # minimum R² to confirm a real regression fit
R2_SIGNAL_TYPE      = 'r2_rev_5m'
R2_SOURCE_PREFIX     = 'r2r5m'
R2_LOOKBACK_CANDLES = 50    # enough for regression + exit scan
R2_COOLDOWN_MINUTES = 15    # cooldown between signals per token
R2_MIN_CONFIDENCE   = 50
R2_MAX_CONFIDENCE   = 88
R2_BASE_CONFIDENCE  = 65
R2_R2_BONUS_MAX     = 15    # max bonus for high R²
R2_RECENCY_BONUS_MAX= 10    # max bonus for fresh entry

# ── Linear Regression ─────────────────────────────────────────────────────────

def _ols_params(y_vals: list) -> tuple:
    """Compute OLS slope, intercept, R² from a list of prices (oldest first)."""
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
    ss_res = sum((yi - (b * xi + a)) ** 2 for yi, xi in zip(y_vals, x))
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

def detect_r2_rev_signal(token: str, candles: list, price: float) -> Optional[dict]:
    """Detect R² mean reversion signal on 5m candles.

    Fires when:
      LONG:  slope > 0 (uptrend) AND price < regression line → pullback to mean
      SHORT: slope < 0 (downtrend) AND price > regression line → rally to mean

    Args:
        token:    token symbol (e.g. 'BTC')
        candles:  list of OHLCV dicts from candles.db (oldest first)
        price:    current price (most recent close from candles) — NOT USED internally;
                  all price comparisons use closes[-1] from the 5m candles

    Returns:
        Signal dict or None if no signal.
    """
    n = len(candles)
    if n < R2_WINDOW * 2:
        return None

    closes = [c['close'] for c in candles]

    # Precompute x stats
    xm, _ = _precompute_x(R2_WINDOW)

    # Check most recent window
    y = closes[-R2_WINDOW:]
    slope, intercept, r2 = _ols_params(y)

    # Entry conditions — mean reversion: fade extensions in the direction of the trend
    # LONG: uptrend (slope>0) pulling back BELOW the regression line → expect bounce
    # SHORT: downtrend (slope<0) rallying ABOVE the regression line → expect fade
    long_cond  = slope > 0 and r2 >= R2_THRESHOLD and closes[-1] < intercept
    short_cond = slope < 0 and r2 >= R2_THRESHOLD and closes[-1] > intercept

    if not long_cond and not short_cond:
        return None

    direction = 'LONG' if long_cond else 'SHORT'

    # Find how many bars since conditions broke (entry point)
    bars_since = 0
    entry_idx = n - R2_WINDOW
    for i in range(n - R2_WINDOW, -1, -1):
        y_i = closes[i:i + R2_WINDOW]
        b_i, a_i, r2_i = _ols_params(y_i)
        price_i = closes[i + R2_WINDOW - 1]
        x_i_vals = list(range(R2_WINDOW))
        x_i_mean = (R2_WINDOW - 1) / 2.0
        y_i_mean = sum(y_i) / R2_WINDOW
        reg_val_i = y_i_mean + b_i * (R2_WINDOW - 1 - x_i_mean)

        if direction == 'LONG':
            broken = b_i >= 0 or r2_i < R2_THRESHOLD or price_i >= reg_val_i
        else:
            broken = b_i <= 0 or r2_i < R2_THRESHOLD or price_i <= reg_val_i

        if broken:
            break
        bars_since = n - R2_WINDOW - i
        entry_idx = i

    bars_since = max(n - R2_WINDOW - entry_idx, 0)

    # Confidence scoring
    r2_bonus      = min((r2 - R2_THRESHOLD) / (1.0 - R2_THRESHOLD) * R2_R2_BONUS_MAX, R2_R2_BONUS_MAX)
    recency_bonus = max(R2_RECENCY_BONUS_MAX - bars_since, 0)

    confidence = int(min(
        R2_BASE_CONFIDENCE + r2_bonus + recency_bonus,
        R2_MAX_CONFIDENCE
    ))

    source = f'{R2_SOURCE_PREFIX}-{direction.lower()}{bars_since}'

    return {
        'direction':  direction,
        'confidence': confidence,
        'source':     source,
        'slope':      round(slope, 8),
        'r2':         round(r2, 4),
        'intercept':  round(intercept, 6),
        'bars_since': bars_since,
        'value':      float(confidence),
        'close_price': closes[-1],   # 5m candle close — use this, NOT the 1m price param
    }


# ── Candle data (candles.db — 5m data not in signal_schema) ───────────────────

def _get_candles_5m(token: str, lookback: int = R2_LOOKBACK_CANDLES) -> list:
    """Fetch 5m OHLCV candles from candles.db (oldest first).

    Freshness guard: skip if latest candle older than 15 minutes.
    """
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        # Freshness check
        c.execute("SELECT MAX(ts) FROM candles_5m WHERE token = ?", (token.upper(),))
        row = c.fetchone()
        if row and row[0]:
            age_seconds = time.time() - row[0]
            if age_seconds > CANDLES_STALENESS_SEC:
                conn.close()
                return []
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return []
        rows = list(reversed(rows))
        return [
            {'open_time': r[0], 'open': r[1], 'high': r[2],
             'low': r[3], 'close': r[4], 'volume': r[5]}
            for r in rows
        ]
    except Exception as e:
        print(f'  [r2_rev_5m] candles.db error for {token}: {e}')
        return []


# ── Main scanner ────────────────────────────────────────────────────────────────

def scan_r2_rev_5m_signals(prices_dict: dict) -> int:
    """Scan pre-filtered tokens for R² mean reversion signals on 5m.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

    Args:
        prices_dict: token -> {'price': float, ...}  (pre-filtered by caller)

    Returns:
        int — number of signals successfully written to DB.
    """
    from signal_schema import add_signal

    added = 0

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        candles = _get_candles_5m(token, lookback=R2_LOOKBACK_CANDLES)
        if not candles or len(candles) < R2_WINDOW * 2:
            continue

        sig = detect_r2_rev_signal(token, candles, price)
        if sig is None:
            continue

        sid = add_signal(
            token=token.upper(),
            direction=sig['direction'],
            signal_type=R2_SIGNAL_TYPE,
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['close_price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            print(f'  {sig["direction"]:5s} {token:8s} conf={sig["confidence"]:3.0f}% '
                  f'slope={sig["slope"]:.6f} r2={sig["r2"]:.4f} '
                  f'price={sig["close_price"]:.6f} intercept={sig["intercept"]:.6f} '
                  f'bars={sig["bars_since"]} '
                  f'[{sig["source"]}]')

    return added


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import get_all_latest_prices, init_db

    init_db()
    prices = get_all_latest_prices()

    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'BNB', 'XRP') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[r2_rev_5m] Testing on {len(test_tokens)} tokens...")
    n = scan_r2_rev_5m_signals(test_tokens)
    print(f"[r2_rev_5m] Done. {n} signals emitted.")