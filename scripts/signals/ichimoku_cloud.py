#!/usr/bin/env python3
"""
ichimoku_cloud.py — Ichimoku Kinko Hyo trend + cloud breakout signal.

Thesis: Multi-component agreement (Tenkan/Kijun cross + cloud breakout +
        future cloud bias + Chikou confirmation) = institutional trend.

Components:
  Tenkan-sen (Conversion Line):  (9-period high + 9-period low) / 2
  Kijun-sen (Base Line):         (26-period high + 26-period low) / 2
  Senkou Span A:                 (Tenkan + Kijun) / 2, shifted 26 bars ahead
  Senkou Span B:                 (52-period high + 52-period low) / 2, shifted 26 ahead
  Chikou Span:                   Close shifted 26 bars back (confirmation)

Entry signals:
  LONG:  Tenkan > Kijun + price above cloud + future cloud bullish (A > B) + Chikou confirming
  SHORT: Tenkan < Kijun + price below cloud + future cloud bearish (A < B) + Chikou confirming

Signal types: ichimoku_long, ichimoku_short
Sources: ichimoku+ (LONG), ichimoku- (SHORT)
Timeframe: 1h (Ichimoku needs 52+ period depth)
"""

import sys
import os
import sqlite3
import time
from typing import Optional, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    ICHIMOKU_ENABLED, ICHIMOKU_PLUS_ENABLED, ICHIMOKU_MINUS_ENABLED,
    LONG_BLACKLIST, SHORT_BLACKLIST,
    ICHIMOKU_TENKAN_PERIOD,
    ICHIMOKU_KIJUN_PERIOD,
    ICHIMOKU_SENKOU_B_PERIOD,
    ICHIMOKU_CLOUD_SHIFT,
    ICHIMOKU_MIN_SEPARATION_PCT,
    ICHIMOKU_CONF_BASE,
    ICHIMOKU_CONF_FLOOR,
    ICHIMOKU_CONF_CAP,
    ICHIMOKU_CLOUD_BREAK_THRESHOLD,
    ICHIMOKU_CLOUD_BREAK_BONUS,
    ICHIMOKU_TK_CROSS_BONUS,
    ICHIMOKU_FUTURE_CLOUD_BONUS,
    ICHIMOKU_COOLDOWN_HOURS,
)

# ── Signal type names ────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'ichimoku_long'
SIGNAL_TYPE_SHORT = 'ichimoku_short'
SOURCE_LONG       = 'ichimoku+'
SOURCE_SHORT      = 'ichimoku-'

# ── Data source ──────────────────────────────────────────────────────
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# Minimum bars needed: Senkou B period + cloud shift + buffer
_MIN_BARS = ICHIMOKU_SENKOU_B_PERIOD + ICHIMOKU_CLOUD_SHIFT + 10


# ═══════════════════════════════════════════════════════════════════════
# Ichimoku calculations
# ═══════════════════════════════════════════════════════════════════════

def _donchian_mid(highs: list, lows: list, period: int, idx: int) -> Optional[float]:
    """Donchian midline at index idx: (high[period] + low[period]) / 2."""
    if idx < period - 1:
        return None
    window_h = max(highs[idx - period + 1 : idx + 1])
    window_l = min(lows[idx - period + 1 : idx + 1])
    return (window_h + window_l) / 2.0


def _compute_ichimoku(highs: list, lows: list, closes: list) -> dict:
    """
    Compute all Ichimoku components from oldest-first OHLC arrays.
    Returns dict with arrays: tenkan, kijun, senkou_a, senkou_b, chikou.
    """
    n = len(closes)
    tenkan = [None] * n
    kijun = [None] * n
    senkou_a = [None] * n
    senkou_b = [None] * n
    chikou = [None] * n

    for i in range(n):
        tenkan[i] = _donchian_mid(highs, lows, ICHIMOKU_TENKAN_PERIOD, i)
        kijun[i] = _donchian_mid(highs, lows, ICHIMOKU_KIJUN_PERIOD, i)

        # Senkou Span A: (tenkan + kijun) / 2, shifted forward by cloud_shift
        if tenkan[i] is not None and kijun[i] is not None:
            sa_val = (tenkan[i] + kijun[i]) / 2.0
            target = i + ICHIMOKU_CLOUD_SHIFT
            if target < n:
                senkou_a[target] = sa_val

        # Senkou Span B: 52-period Donchian mid, shifted forward
        sb_val = _donchian_mid(highs, lows, ICHIMOKU_SENKOU_B_PERIOD, i)
        if sb_val is not None:
            target = i + ICHIMOKU_CLOUD_SHIFT
            if target < n:
                senkou_b[target] = sb_val

        # Chikou Span: close shifted back by cloud_shift
        if i >= ICHIMOKU_CLOUD_SHIFT:
            chikou[i - ICHIMOKU_CLOUD_SHIFT] = closes[i]

    return {
        'tenkan': tenkan,
        'kijun': kijun,
        'senkou_a': senkou_a,
        'senkou_b': senkou_b,
        'chikou': chikou,
    }


def _cloud_top(senkou_a: float, senkou_b: float) -> float:
    """Upper edge of the cloud."""
    return max(senkou_a, senkou_b)


def _cloud_bottom(senkou_a: float, senkou_b: float) -> float:
    """Lower edge of the cloud."""
    return min(senkou_a, senkou_b)


def _cloud_color(senkou_a: float, senkou_b: float) -> str:
    """Bullish if A > B (green cloud), bearish if A < B (red cloud)."""
    return 'bullish' if senkou_a > senkou_b else 'bearish'


# ═══════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════

def detect_ichimoku(token: str, highs: list, lows: list, closes: list) -> Optional[dict]:
    """
    Detect Ichimoku signal on OHLC data (oldest-first).

    LONG conditions (all must be true):
      1. Tenkan > Kijun (TK cross or already crossed)
      2. Price > cloud top (above Kumo)
      3. Future cloud bullish (Senkou A > Senkou B at current bar)
      4. Chikou > close 26 bars ago (momentum confirmation)

    SHORT conditions (inverted):
      1. Tenkan < Kijun
      2. Price < cloud bottom
      3. Future cloud bearish (Senkou A < Senkou B)
      4. Chikou < close 26 bars ago

    Returns signal dict or None.
    """
    n = len(closes)
    if n < _MIN_BARS:
        return None

    ich = _compute_ichimoku(highs, lows, closes)

    # Check last few bars for signal (prefer most recent)
    # Chikou[j] is only available when j + CLOUD_SHIFT < n (chikou is shifted backward)
    search_end = n - ICHIMOKU_CLOUD_SHIFT
    if search_end <= ICHIMOKU_SENKOU_B_PERIOD + ICHIMOKU_CLOUD_SHIFT:
        return None  # not enough data for all components
    search_start = max(ICHIMOKU_SENKOU_B_PERIOD + ICHIMOKU_CLOUD_SHIFT, search_end - 5)
    for j in range(search_start, search_end):
        tenkan = ich['tenkan'][j]
        kijun = ich['kijun'][j]
        sa = ich['senkou_a'][j]
        sb = ich['senkou_b'][j]
        chikou = ich['chikou'][j]

        if any(v is None for v in [tenkan, kijun, sa, sb]):
            continue

        price = closes[j]
        cloud_t = _cloud_top(sa, sb)
        cloud_b = _cloud_bottom(sa, sb)
        color = _cloud_color(sa, sb)

        # Chikou confirmation: chikou[j] = closes[j+26] (future close shifted back)
        # Compare future close against current close for momentum confirmation
        if chikou is None:
            continue

        # ── LONG ──────────────────────────────────────────────────────
        if (tenkan > kijun and
            price > cloud_t and
            color == 'bullish' and
            chikou > price):

            # Separation: how far above cloud?
            separation_pct = (price - cloud_t) / cloud_t if cloud_t > 0 else 0
            if separation_pct < ICHIMOKU_MIN_SEPARATION_PCT:
                continue  # too close to cloud — noise

            # TK cross: was there a cross in the last 3 bars?
            tk_cross = False
            for k in range(1, min(4, j + 1)):
                prev_t = ich['tenkan'][j - k]
                prev_k = ich['kijun'][j - k]
                if prev_t is not None and prev_k is not None and prev_t <= prev_k:
                    tk_cross = True
                    break

            # Confidence scoring
            conf = ICHIMOKU_CONF_BASE
            if tk_cross:
                conf += ICHIMOKU_TK_CROSS_BONUS
            if separation_pct > ICHIMOKU_CLOUD_BREAK_THRESHOLD:
                conf += ICHIMOKU_CLOUD_BREAK_BONUS
            if color == 'bullish':
                conf += ICHIMOKU_FUTURE_CLOUD_BONUS

            conf = max(ICHIMOKU_CONF_FLOOR, min(ICHIMOKU_CONF_CAP, int(conf)))

            return {
                'direction': 'LONG',
                'confidence': conf,
                'value': float(conf),
                'price': price,
                'tenkan': round(tenkan, 6),
                'kijun': round(kijun, 6),
                'cloud_top': round(cloud_t, 6),
                'cloud_bottom': round(cloud_b, 6),
                'cloud_color': color,
                'separation_pct': round(separation_pct * 100, 3),
                'tk_cross': tk_cross,
                'bars_since': max(n - 1 - j, 0),
            }

        # ── SHORT ─────────────────────────────────────────────────────
        if (tenkan < kijun and
            price < cloud_b and
            color == 'bearish' and
            chikou < price):

            separation_pct = (cloud_b - price) / cloud_b if cloud_b > 0 else 0
            if separation_pct < ICHIMOKU_MIN_SEPARATION_PCT:
                continue

            tk_cross = False
            for k in range(1, min(4, j + 1)):
                prev_t = ich['tenkan'][j - k]
                prev_k = ich['kijun'][j - k]
                if prev_t is not None and prev_k is not None and prev_t >= prev_k:
                    tk_cross = True
                    break

            conf = ICHIMOKU_CONF_BASE
            if tk_cross:
                conf += ICHIMOKU_TK_CROSS_BONUS
            if separation_pct > ICHIMOKU_CLOUD_BREAK_THRESHOLD:
                conf += ICHIMOKU_CLOUD_BREAK_BONUS
            if color == 'bearish':
                conf += ICHIMOKU_FUTURE_CLOUD_BONUS

            conf = max(ICHIMOKU_CONF_FLOOR, min(ICHIMOKU_CONF_CAP, int(conf)))

            return {
                'direction': 'SHORT',
                'confidence': conf,
                'value': float(conf),
                'price': price,
                'tenkan': round(tenkan, 6),
                'kijun': round(kijun, 6),
                'cloud_top': round(cloud_t, 6),
                'cloud_bottom': round(cloud_b, 6),
                'cloud_color': color,
                'separation_pct': round(separation_pct * 100, 3),
                'tk_cross': tk_cross,
                'bars_since': max(n - 1 - j, 0),
            }

    return None


# ═══════════════════════════════════════════════════════════════════════
# Data fetch
# ═══════════════════════════════════════════════════════════════════════

def _get_candles(token: str, table: str, limit: int) -> Tuple[list, list, list]:
    """
    Fetch OHLC from candles.db. Returns oldest-first (highs, lows, closes).
    DB connection properly cleaned up in finally block.
    """
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT high, low, close FROM {table}
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return [], [], []
        rows.reverse()  # oldest first
        highs = [r[0] for r in rows]
        lows = [r[1] for r in rows]
        closes = [r[2] for r in rows]
        return highs, lows, closes
    except Exception:
        return [], [], []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════

def scan_ichimoku_signals() -> int:
    """Scan all tradeable tokens for Ichimoku signals."""
    from tokens import get_all_tradeable_tokens

    added = 0
    for token in get_all_tradeable_tokens():
        token_upper = token.upper()

        if price_age_minutes(token_upper) > 10:
            continue

        # Layer 1: blacklists
        if token_upper in LONG_BLACKLIST and token_upper in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token_upper, direction='LONG') and get_cooldown(token_upper, direction='SHORT'):
            continue

        # Fetch 1h candles (Ichimoku needs 52+26 period depth)
        highs, lows, closes = _get_candles(token_upper, 'candles_1h', 120)
        if len(closes) < _MIN_BARS:
            continue

        sig = detect_ichimoku(token_upper, highs, lows, closes)
        if sig is None:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not ICHIMOKU_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not ICHIMOKU_MINUS_ENABLED:
            continue

        # Layer 1: per-direction blacklist
        if direction == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        # Cooldown check (per-direction)
        if get_cooldown(token_upper, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        try:
            sid = add_signal(
                token=token_upper,
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=sig['confidence'],
                value=sig['value'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='1h',
                z_score=None,
            )
            if sid:
                added += 1
                set_cooldown(token_upper, direction, hours=ICHIMOKU_COOLDOWN_HOURS)
                print(f"  {direction:5s}-ichimoku {token_upper:8s} "
                      f"conf={sig['confidence']}% "
                      f"tenkan={sig['tenkan']:.4f} kijun={sig['kijun']:.4f} "
                      f"cloud={sig['cloud_color']} sep={sig['separation_pct']:.2f}% "
                      f"[{source}]")
        except Exception as e:
            print(f"  [ichimoku] add_signal error for {token_upper}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════

def run():
    """Entry point for signals_runner. No prices_dict — reads from candles.db."""
    return scan_ichimoku_signals()


# ═══════════════════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    print("[ichimoku] Scanning all tokens...")
    n = scan_ichimoku_signals()
    print(f"[ichimoku] Done. {n} signals emitted.")
