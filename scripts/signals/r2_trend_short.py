#!/usr/bin/env python3
"""
r2_trend.py — R² Trend Confirmation Signal for SHORT entries.

Detects confirmed downtrends on 1m candles via OLS regression.
Fires SHORT when:
  1. R² >= threshold (confirmed trend = not chop)
  2. Slope < 0 (downtrend)
  3. Price < regression line (bearish alignment)

Signal type: r2_trend_short
Source: r2-trend-short{N}
"""

import sqlite3
import sys
import os
import time
import numpy as np
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    R2_TREND_ENABLED,
    R2_TREND_SHORT_ENABLED,
    R2_TREND_SHORT_MIN_SLOPE,
    R2_TREND_SHORT_MIN_R2,
    R2_TREND_SHORT_MAX_RSI,
    R2_TREND_SHORT_MIN_SPEED,
    R2_TREND_SHORT_MIN_BB_POS,
    R2_TREND_SHORT_BLOCK_STALE,
    R2_TREND_SHORT_MAX_ACCEL,
    R2_TREND_SHORT_MIN_PRE_MOVE,
    R2_TREND_SHORT_MIN_BARS,
    CANDLES_STALENESS_SEC,
    SHORT_BLACKLIST,
)

# ── Constants ─────────────────────────────────────────────────────────────
R2_WINDOW            = 16
R2_THRESHOLD         = 0.60
SIGNAL_TYPE          = 'r2_trend_short'
SOURCE_PREFIX        = 'r2-trend-short'
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

def detect_r2_short(token, candles, price):
    """Detect confirmed downtrend on 1m candles via R² regression.

    Fires SHORT when:
      - R² >= R2_TREND_SHORT_MIN_R2 (confirmed trend, not chop)
      - Slope < 0 (downtrend)
      - Price < regression intercept (bearish alignment)
    """
    n = len(candles)
    if n < R2_WINDOW * 2:
        return None

    closes = [c['close'] for c in candles]
    y = closes[-R2_WINDOW:]
    slope, intercept, r2 = _ols_params(y)

    # SHORT conditions: slope < 0, price below line, R² strong enough
    if r2 < R2_TREND_SHORT_MIN_R2 or slope >= 0 or closes[-1] >= intercept:
        return None

    # ── Gap300 filter — don't SHORT when price too far below EMA300 ─────
    # Price extended below EMA = bounce risk. Mirror of LONG gap300 filter.
    try:
        conn_ema = sqlite3.connect(CANDLES_DB, timeout=5)
        try:
            rows_ema = conn_ema.execute(
                "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 310",
                (token.upper(),)
            ).fetchall()
        finally:
            conn_ema.close()
        if rows_ema and len(rows_ema) >= 300:
            closes_ema = [r[0] for r in reversed(rows_ema)]
            k_ema = 2.0 / 301
            ema_val = closes_ema[0]
            for p in closes_ema[1:]:
                ema_val = p * k_ema + ema_val * (1 - k_ema)
            gap300 = (closes_ema[-1] - ema_val) / ema_val * 100 if ema_val > 0 else 0
            if gap300 < -0.50:
                return None  # price too far below EMA300 — extended, skip SHORT
    except Exception:
        pass

    # ── Pre-entry move filter — block SHORT when price rising before entry ─
    try:
        conn_pm = sqlite3.connect(CANDLES_DB, timeout=5)
        try:
            rows_pm = conn_pm.execute(
                "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 16",
                (token.upper(),)
            ).fetchall()
        finally:
            conn_pm.close()
        if rows_pm and len(rows_pm) >= 15:
            closes_pm = [r[0] for r in reversed(rows_pm)]
            pre_move = (closes_pm[-1] - closes_pm[0]) / closes_pm[0] * 100 if closes_pm[0] > 0 else 0
            if pre_move > R2_TREND_SHORT_MIN_PRE_MOVE:
                return None  # price rising before entry — skip SHORT
    except Exception:
        pass

    # Transition detector: R² must be RISING from below threshold
    # Catches the START of a trend, not flat periods
    if len(closes) >= R2_WINDOW + 3:
        y_prev = closes[-(R2_WINDOW + 3):-3]
        _, _, r2_prev = _ols_params(y_prev)
        if not (r2_prev < R2_THRESHOLD and r2 >= R2_THRESHOLD):
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
        if b_i >= 0 or r2_i < R2_TREND_SHORT_MIN_R2:
            break
        bars_since = n - R2_WINDOW - i
        entry_idx = i

    bars_since = max(n - R2_WINDOW - entry_idx, 0)

    # Minimum bars filter — don't enter too early
    if bars_since < R2_TREND_SHORT_MIN_BARS:
        return None

    # Confidence scoring
    r2_bonus = min((r2 - R2_TREND_SHORT_MIN_R2) / (1.0 - R2_TREND_SHORT_MIN_R2) * R2_BONUS_MAX, R2_BONUS_MAX)
    recency_bonus = max(RECENCY_BONUS_MAX - bars_since, 0)

    confidence = int(min(
        BASE_CONFIDENCE + r2_bonus + recency_bonus,
        MAX_CONFIDENCE
    ))

    source = f'{SOURCE_PREFIX}{bars_since}'

    return {
        'direction':  'SHORT',
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
        if (time.time() - most_recent_ts) > CANDLES_STALENESS_SEC:
            return []

        return [{'close': r[1]} for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ── Scanner ─────────────────────────────────────────────────────────────

def scan_signals():
    if not R2_TREND_ENABLED or not R2_TREND_SHORT_ENABLED:
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

        if get_cooldown(token, direction='SHORT'):
            continue

        if token.upper() in SHORT_BLACKLIST:
            continue

        # ── Speed/momentum/accel filters ────────────────────────────────
        _conn_spd = None
        try:
            _conn_spd = sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes_runtime.db'), timeout=5)
            _cur_spd = _conn_spd.cursor()
            _cur_spd.execute('''SELECT speed_percentile, is_stale, momentum_score, price_acceleration FROM token_speeds WHERE token = ?''', (token.upper(),))
            _spd_row = _cur_spd.fetchone()
            if _spd_row:
                _speed, _is_stale, _mom, _accel = _spd_row
                # Block stale tokens (no momentum)
                if R2_TREND_SHORT_BLOCK_STALE and _is_stale:
                    continue
                # Require minimum speed
                if _speed is not None and _speed < R2_TREND_SHORT_MIN_SPEED:
                    continue
                # Block overextended: price accelerating down = about to reverse
                if _accel is not None and _accel > R2_TREND_SHORT_MAX_ACCEL:
                    continue
        except Exception as _e:
            print(f'  [r2_trend_short] WARN: failed to read token_speeds for {token}: {_e}')
        finally:
            if _conn_spd:
                _conn_spd.close()

        candles = _get_candles_1m(token)
        if not candles or len(candles) < R2_WINDOW * 2:
            continue

        sig = detect_r2_short(token, candles, price)
        if sig is None:
            continue

        # ── RSI filter: don't short overbought ────────────────────────────
        closes_list = [c['close'] for c in candles]
        if len(closes_list) >= 15:
            deltas = [closes_list[i] - closes_list[i-1] for i in range(1, len(closes_list))]
            gains = [d if d > 0 else 0 for d in deltas[-14:]]
            losses_rsi = [-d if d < 0 else 0 for d in deltas[-14:]]
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses_rsi) / 14
            if avg_loss > 0:
                rsi = 100 - (100 / (1 + avg_gain / avg_loss))
            else:
                rsi = 100.0
            if rsi > R2_TREND_SHORT_MAX_RSI:
                continue  # overbought — wait for weakness

        # ── BB position filter: don't short at band bottom ────────────────
        if len(closes_list) >= 20:
            mean_20 = np.mean(closes_list[-20:])
            std_20 = np.std(closes_list[-20:])
            if std_20 > 0:
                bb_pos = (closes_list[-1] - (mean_20 - 2 * std_20)) / (4 * std_20)
                if bb_pos < R2_TREND_SHORT_MIN_BB_POS:
                    continue  # at band bottom — bounce risk

        sid = add_signal(
            token=token.upper(),
            direction='SHORT',
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
            print(f'  SHORT {token:8s} conf={sig["confidence"]:.0f}% '
                  f'slope={sig["slope"]:.6f} r2={sig["r2"]:.4f} '
                  f'price={price:.6f} intercept={sig["intercept"]:.6f} '
                  f'bars={sig["bars_since"]} '
                  f'[{sig["source"]}]')

    return added


# ── signals_runner entry point ──────────────────────────────────────────

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    prices = get_all_latest_prices()
    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])
    print(f"[r2_trend_short] Testing on {len(test_tokens)} tokens...")
    n = scan_signals()
    print(f"[r2_trend_short] Done. {n} signals emitted.")
