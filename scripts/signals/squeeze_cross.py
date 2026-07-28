#!/usr/bin/env python3
"""
squeeze_cross.py — EMA Squeeze Expansion Signal

Fires when:
  1. ATR squeeze: current ATR < 0.9× rolling ATR average (volatility compression)
  2. EMA alignment: EMA(5) > EMA(180) for LONG, < for SHORT (trend bias)
  3. Gap widening: EMA gap is expanding vs N bars ago (expansion starting)
  4. Fresh momentum: close is moving in the signal direction (confirmation)

Architecture:
  - Reads 1m close prices from price_history (signals_hermes.db)
  - Computes EMA(5), EMA(180), ATR(14)
  - Detects squeeze + alignment + expansion conditions
  - Writes via signal_schema.add_signal()
"""

import sqlite3
import time
from typing import Optional

from hermes_constants import (
    SQUEEZE_CROSS_ENABLED,
    SQUEEZE_CROSS_PLUS_ENABLED,
    SQUEEZE_CROSS_MINUS_ENABLED,
    SQUEEZE_CROSS_EMA_FAST,
    SQUEEZE_CROSS_EMA_SLOW,
    SQUEEZE_CROSS_LOOKBACK,
    SQUEEZE_CROSS_ATR_PERIOD,
    SQUEEZE_CROSS_ATR_RATIO,
    SQUEEZE_CROSS_ATR_AVG_WIN,
    SQUEEZE_CROSS_WIDEN_BARS,
    SQUEEZE_CROSS_COOLDOWN,
    SQUEEZE_CROSS_CONF_BASE,
    SQUEEZE_CROSS_CONF_SQZ,
    SQUEEZE_CROSS_CONF_WIDEN,
    SQUEEZE_CROSS_CONF_MAX,
    SHORT_BLACKLIST,
    LONG_BLACKLIST,
)

SIGNAL_TYPE = 'squeeze_cross'
SOURCE_PREFIX = 'sqx'

EMA_FAST = SQUEEZE_CROSS_EMA_FAST
EMA_SLOW = SQUEEZE_CROSS_EMA_SLOW
LOOKBACK = SQUEEZE_CROSS_LOOKBACK
ATR_PERIOD = SQUEEZE_CROSS_ATR_PERIOD
ATR_SQUEEZE_RATIO = SQUEEZE_CROSS_ATR_RATIO
ATR_AVG_WINDOW = SQUEEZE_CROSS_ATR_AVG_WIN
WIDENING_BARS = SQUEEZE_CROSS_WIDEN_BARS
COOLDOWN_BARS = SQUEEZE_CROSS_COOLDOWN
CONFIDENCE_BASE = SQUEEZE_CROSS_CONF_BASE
CONFIDENCE_SQUEEZE_BONUS = SQUEEZE_CROSS_CONF_SQZ
CONFIDENCE_WIDENING_BONUS = SQUEEZE_CROSS_CONF_WIDEN
CONFIDENCE_MAX = SQUEEZE_CROSS_CONF_MAX


def _ema(values: list, period: int) -> list:
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


def _atr(closes: list, period: int) -> list:
    if len(closes) < period + 1:
        return [None] * len(closes)
    tr = [None]
    for i in range(1, len(closes)):
        tr.append(abs(closes[i] - closes[i - 1]))
    result = [None] * period
    valid_tr = [v for v in tr[1:period + 1] if v is not None]
    if len(valid_tr) < period:
        return [None] * len(closes)
    atr_val = sum(valid_tr) / period
    result.append(atr_val)
    for i in range(period + 1, len(closes)):
        if tr[i] is not None:
            atr_val = (atr_val * (period - 1) + tr[i]) / period
        result.append(atr_val)
    return result


_PRICE_DB = '/root/.hermes/data/signals_hermes.db'


def _get_closes(token: str, lookback: int = LOOKBACK) -> list:
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
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []
        return rows
    except Exception:
        return []


def detect_squeeze_cross(token: str, closes: list) -> Optional[dict]:
    """Detect EMA squeeze expansion: squeeze + alignment + widening + momentum.

    Args:
        token: token symbol
        closes: list of (ts, price) tuples, oldest first

    Returns:
        Signal dict or None.
    """
    if len(closes) < LOOKBACK:
        return None

    prices = [c[1] for c in closes]

    ema_fast = _ema(prices, EMA_FAST)
    ema_slow = _ema(prices, EMA_SLOW)
    atr_series = _atr(prices, ATR_PERIOD)

    if ema_fast[-1] is None or ema_slow[-1] is None or atr_series[-1] is None:
        return None

    # ── 1. ATR squeeze: volatility compression ────────────────────────────
    valid_atr = [v for v in atr_series[-ATR_AVG_WINDOW:] if v is not None]
    if len(valid_atr) < 10:
        return None
    atr_avg = sum(valid_atr) / len(valid_atr)
    atr_current = atr_series[-1]

    if atr_avg <= 0:
        return None

    squeeze_ratio = atr_current / atr_avg
    if squeeze_ratio >= ATR_SQUEEZE_RATIO:
        return None

    # ── 2. EMA alignment: directional bias ────────────────────────────────
    ema_diff = ema_fast[-1] - ema_slow[-1]
    if ema_diff > 0:
        direction = 'LONG'
    elif ema_diff < 0:
        direction = 'SHORT'
    else:
        return None

    # ── 3. Gap widening: expansion starting ────────────────────────────────
    prev_idx = -1 - WIDENING_BARS
    if ema_fast[prev_idx] is None or ema_slow[prev_idx] is None:
        return None

    gap_now = abs(ema_diff)
    gap_prev = abs(ema_fast[prev_idx] - ema_slow[prev_idx])

    if gap_prev <= 0:
        return None

    widening_ratio = gap_now / gap_prev
    if widening_ratio <= 1.0:
        return None

    # ── 4. Momentum confirmation: price moving in direction ────────────────
    momentum_bars = min(5, len(prices) - 1)
    if momentum_bars < 2:
        return None
    recent_move = (prices[-1] - prices[-1 - momentum_bars]) / prices[-1 - momentum_bars] * 100

    if direction == 'LONG' and recent_move <= 0:
        return None
    if direction == 'SHORT' and recent_move >= 0:
        return None

    # ── Confidence scoring ─────────────────────────────────────────────────
    squeeze_depth = max(0, ATR_SQUEEZE_RATIO - squeeze_ratio)
    squeeze_bonus = min(int(squeeze_depth * 100), CONFIDENCE_SQUEEZE_BONUS)

    widen_amount = min(widening_ratio - 1.0, 0.5)
    widening_bonus = min(int(widen_amount * 10), CONFIDENCE_WIDENING_BONUS)

    momentum_bonus = min(int(abs(recent_move) * 5), 10)

    confidence = min(
        CONFIDENCE_BASE + squeeze_bonus + widening_bonus + momentum_bonus,
        CONFIDENCE_MAX
    )

    price = prices[-1]
    source = f'{SOURCE_PREFIX}{"+" if direction == "LONG" else "-"}'

    return {
        'direction': direction,
        'confidence': confidence,
        'source': source,
        'ema_fast': round(ema_fast[-1], 6),
        'ema_slow': round(ema_slow[-1], 6),
        'gap_pct': round(gap_now / price * 100, 4),
        'widening_ratio': round(widening_ratio, 4),
        'squeeze_ratio': round(squeeze_ratio, 4),
        'atr_current': round(atr_current, 8),
        'atr_avg': round(atr_avg, 8),
        'momentum_pct': round(recent_move, 4),
        'price': price,
        'value': float(confidence),
    }


_last_signal = {}


def _cooldown_ok(token: str, direction: str) -> bool:
    key = f"{token}:{direction}"
    last = _last_signal.get(key, 0)
    if (time.time() - last) < COOLDOWN_BARS * 60:
        return False
    return True


def _mark_signal(token: str, direction: str) -> None:
    _last_signal[f"{token}:{direction}"] = time.time()


def scan_squeeze_cross_signals(prices_dict: dict = None) -> int:
    from signal_schema import add_signal, get_cooldown

    if not SQUEEZE_CROSS_ENABLED:
        return 0

    if not prices_dict:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()

    added = 0

    for token in prices_dict:
        if token in SHORT_BLACKLIST or token in LONG_BLACKLIST:
            continue

        closes = _get_closes(token)
        if not closes or len(closes) < LOOKBACK:
            continue

        try:
            sig = detect_squeeze_cross(token, closes)
        except Exception as e:
            print(f"  [squeeze_cross] error for {token}: {e}")
            continue

        if not sig:
            continue

        direction = sig['direction']

        if direction == 'LONG' and not SQUEEZE_CROSS_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not SQUEEZE_CROSS_MINUS_ENABLED:
            continue

        if not _cooldown_ok(token, direction):
            continue

        try:
            cd = get_cooldown(token, direction)
            if cd and (time.time() - cd) < COOLDOWN_BARS * 60:
                continue
        except Exception:
            pass

        price = sig['price']
        confidence = sig['confidence']

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=SIGNAL_TYPE,
                source=sig['source'],
                confidence=confidence,
                value=sig['value'],
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                _mark_signal(token, direction)
                print(f"  [squeeze_cross] {token} {direction} conf={confidence} "
                      f"squeeze={sig['squeeze_ratio']:.3f} widening={sig['widening_ratio']:.3f} "
                      f"momentum={sig['momentum_pct']:.3f}% price={price}")
        except Exception as e:
            print(f"  [squeeze_cross] add_signal error for {token}: {e}")

    return added


def run(prices_dict=None):
    added = scan_squeeze_cross_signals(prices_dict)
    if added > 0:
        print(f"[squeeze_cross] scan complete — {added} signals added")
    return added


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    prices = get_all_latest_prices()
    n = scan_squeeze_cross_signals(prices)
    print(f"[squeeze_cross] Done. {n} signals emitted.")
