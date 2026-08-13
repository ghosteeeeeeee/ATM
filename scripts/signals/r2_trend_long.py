#!/usr/bin/env python3
"""
r2_trend_long.py — R² Trend Confirmation Signal for LONG entries.

Detects confirmed uptrends on 1m candles via OLS regression.
Fires LONG when:
  1. R² >= threshold (confirmed trend = not chop)
  2. Slope > 0 (uptrend)
  3. Price > regression line (bullish alignment)

Inspired by BSV backtest: R² > 0.6 with positive slope detected slow grinds
that missed by other signals.

Signal type: r2_trend_long
Source: r2l-long{N}
"""

import sys, os, sqlite3, time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    R2_TREND_LONG_ENABLED,
    R2_TREND_LONG_MIN_SLOPE,
    LONG_BLACKLIST,
)

# ── Constants ─────────────────────────────────────────────────────────────
R2_WINDOW            = 16
R2_THRESHOLD         = 0.60
SIGNAL_TYPE          = 'r2_trend_long'
SOURCE_PREFIX        = 'r2-trend-long'
LOOKBACK_CANDLES     = 50
COOLDOWN_MINUTES     = 15
MIN_CONFIDENCE       = 50
MAX_CONFIDENCE       = 88
BASE_CONFIDENCE      = 65
R2_BONUS_MAX         = 15
RECENCY_BONUS_MAX    = 10

_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')


# ── Linear Regression ───────────────────────────────────────────────────

def _ols_params(y_vals):
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


# ── Trend Detection ─────────────────────────────────────────────────────

def detect_r2_long(token, candles, price):
    """Detect confirmed uptrend on 1m candles via R² regression.

    Fires LONG when:
      - R² >= R2_THRESHOLD (confirmed trend, not chop)
      - Slope > 0 (uptrend)
      - Price > regression intercept (bullish alignment)
    """
    n = len(candles)
    if n < R2_WINDOW * 2:
        return None

    closes = [c['close'] for c in candles]
    y = closes[-R2_WINDOW:]
    slope, intercept, r2 = _ols_params(y)

    # LONG conditions: slope > 0, price above line, R² meaningful
    if slope <= 0 or closes[-1] <= intercept:
        return None

    # Transition detector: R² must be RISING from below threshold
    # This catches the START of a trend, not flat periods
    if len(closes) >= R2_WINDOW + 3:
        y_prev = closes[-(R2_WINDOW + 3):-3]
        _, _, r2_prev = _ols_params(y_prev)
        # R² must have been below threshold recently and now rising above it
        if not (r2_prev < R2_THRESHOLD and r2 >= R2_THRESHOLD):
            # Also allow if R² is rising strongly (even if already above threshold)
            if r2 < R2_THRESHOLD or (r2 - r2_prev) < 0.05:
                return None
    elif r2 < R2_THRESHOLD:
        return None

    # Find how many bars since slope flipped negative (trend started)
    bars_since = 0
    entry_idx = n - R2_WINDOW
    for i in range(n - R2_WINDOW, -1, -1):
        y_i = closes[i:i + R2_WINDOW]
        b_i, a_i, r2_i = _ols_params(y_i)
        if b_i <= 0 or r2_i < R2_THRESHOLD:
            break
        bars_since = n - R2_WINDOW - i
        entry_idx = i

    bars_since = max(n - R2_WINDOW - entry_idx, 0)

    # Confidence scoring
    r2_bonus = min((r2 - R2_THRESHOLD) / (1.0 - R2_THRESHOLD) * R2_BONUS_MAX, R2_BONUS_MAX)
    recency_bonus = max(RECENCY_BONUS_MAX - bars_since, 0)

    confidence = int(min(
        BASE_CONFIDENCE + r2_bonus + recency_bonus,
        MAX_CONFIDENCE
    ))

    source = f'{SOURCE_PREFIX}{bars_since}'

    return {
        'direction':  'LONG',
        'confidence': confidence,
        'source':     source,
        'slope':      round(slope, 8),
        'r2':         round(r2, 4),
        'intercept':  round(intercept, 6),
        'bars_since': bars_since,
        'value':      float(confidence),
    }


# ── Candle Data ─────────────────────────────────────────────────────────

def _get_candles_1m(token, lookback=LOOKBACK_CANDLES):
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price FROM price_history
                WHERE token = ? ORDER BY timestamp DESC LIMIT ?
            ) sub ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()

        if not rows:
            return []

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []

        return [{'close': r[1]} for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ── Scanner ─────────────────────────────────────────────────────────────

def scan_signals():
    if not R2_TREND_LONG_ENABLED:
        return 0

    from signal_schema import get_all_latest_prices

    prices = get_all_latest_prices()
    added = 0

    for token, data in prices.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        if price_age_minutes(token) > 10:
            continue

        if get_cooldown(token, direction='LONG'):
            continue

        if token.upper() in LONG_BLACKLIST:
            continue

        candles = _get_candles_1m(token)
        if not candles or len(candles) < R2_WINDOW * 2:
            continue

        sig = detect_r2_long(token, candles, price)
        if sig is None:
            continue

        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=SIGNAL_TYPE,
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
            added += 1
            set_cooldown(token, direction='LONG', hours=3)
            print(f'  LONG  {token:8s} conf={sig["confidence"]:.0f}% '
                  f'slope={sig["slope"]:.6f} r2={sig["r2"]:.4f} '
                  f'price={price:.6f} intercept={sig["intercept"]:.6f} '
                  f'bars={sig["bars_since"]} [{sig["source"]}]')

    return added


def run():
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_signals()
    print(f'[r2_trend_long] Done. {n} signals emitted.')
