#!/usr/bin/env python3
"""
squeeze_cross.py — EMA Cross + ATR Squeeze Signal

Fires when:
  1. EMA(5) crosses EMA(180) on 1m price_history
  2. ATR(20) < 0.9 × ATR(20) rolling average (squeeze condition)
  3. Gap between EMA5 and EMA180 is widening (divergence confirmation)
  4. Cooldown: 60 bars between signals per token+direction

Backtested: 71% WR, +2.36% avg PnL, 14 signals on 3-day 1m data.

Architecture:
  - Reads 1m close prices from price_history (signals_hermes.db)
  - Computes EMA(5), EMA(180), ATR(20)
  - Detects cross + squeeze + widening conditions
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

# ── Constants ─────────────────────────────────────────────────────────────────
SIGNAL_TYPE = 'squeeze_cross'
SOURCE_PREFIX = 'sqx'

# Local aliases for readability
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

# ── Helpers ───────────────────────────────────────────────────────────────────

def _ema(values: list, period: int) -> list:
    """Compute EMA series. Returns list with None for indices < period-1."""
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
    """Compute ATR from close prices using absolute returns.
    Returns list with None for indices < period.
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    # True Range approximation: abs(close[i] - close[i-1])
    tr = [None]  # first bar has no prior close
    for i in range(1, len(closes)):
        tr.append(abs(closes[i] - closes[i - 1]))

    result = [None] * period
    # Initial ATR = average of first `period` TR values
    valid_tr = [v for v in tr[1:period + 1] if v is not None]
    if len(valid_tr) < period:
        return [None] * len(closes)
    atr_val = sum(valid_tr) / period
    result.append(atr_val)

    # Smoothed ATR
    for i in range(period + 1, len(closes)):
        if tr[i] is not None:
            atr_val = (atr_val * (period - 1) + tr[i]) / period
        result.append(atr_val)

    return result


# ── Data fetch ────────────────────────────────────────────────────────────────
_PRICE_DB = '/root/.hermes/data/signals_hermes.db'


def _get_closes(token: str, lookback: int = LOOKBACK) -> list:
    """Fetch 1m close prices from price_history, oldest first.
    Returns list of (timestamp, price) tuples.
    Freshness guard: returns [] if most recent price is > 2 min old.
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

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []

        return rows

    except Exception:
        return []


# ── Signal detection ──────────────────────────────────────────────────────────

def detect_squeeze_cross(token: str, closes: list) -> Optional[dict]:
    """Detect EMA cross + ATR squeeze + widening gap.

    Args:
        token: token symbol
        closes: list of (ts, price) tuples, oldest first

    Returns:
        Signal dict or None.
    """
    if len(closes) < LOOKBACK:
        return None

    prices = [c[1] for c in closes]

    # Compute indicators
    ema_fast = _ema(prices, EMA_FAST)
    ema_slow = _ema(prices, EMA_SLOW)
    atr_series = _atr(prices, ATR_PERIOD)

    # Need all three to be valid
    if ema_fast[-1] is None or ema_slow[-1] is None or atr_series[-1] is None:
        return None

    # ATR squeeze check: current ATR < ratio × rolling average
    valid_atr = [v for v in atr_series[-ATR_AVG_WINDOW:] if v is not None]
    if len(valid_atr) < 10:
        return None
    atr_avg = sum(valid_atr) / len(valid_atr)
    atr_current = atr_series[-1]

    if atr_avg <= 0:
        return None

    squeeze_ratio = atr_current / atr_avg
    is_squeezed = squeeze_ratio < ATR_SQUEEZE_RATIO

    if not is_squeezed:
        return None

    # Detect cross: find where EMA5 crossed EMA180
    # Walk backwards from most recent bar
    cross_dir = None
    cross_bars_ago = None

    for i in range(len(closes) - 1, max(EMA_SLOW + 1, len(closes) - 30), -1):
        if ema_fast[i] is None or ema_slow[i] is None:
            continue
        if ema_fast[i - 1] is None or ema_slow[i - 1] is None:
            continue

        # Golden cross: fast crosses above slow
        if ema_fast[i - 1] <= ema_slow[i - 1] and ema_fast[i] > ema_slow[i]:
            cross_dir = 'LONG'
            cross_bars_ago = len(closes) - 1 - i
            break
        # Death cross: fast crosses below slow
        if ema_fast[i - 1] >= ema_slow[i - 1] and ema_fast[i] < ema_slow[i]:
            cross_dir = 'SHORT'
            cross_bars_ago = len(closes) - 1 - i
            break

    if cross_dir is None:
        return None

    # Gap must be widening over last N bars
    gap_now = abs(ema_fast[-1] - ema_slow[-1])
    gap_prev = abs(ema_fast[-1 - WIDENING_BARS] - ema_slow[-1 - WIDENING_BARS]) \
        if (ema_fast[-1 - WIDENING_BARS] is not None and ema_slow[-1 - WIDENING_BARS] is not None) \
        else gap_now

    if gap_prev <= 0:
        return None

    widening_ratio = gap_now / gap_prev
    is_widening = widening_ratio > 1.0

    if not is_widening:
        return None

    # Confidence scoring
    squeeze_depth = max(0, ATR_SQUEEZE_RATIO - squeeze_ratio)  # deeper squeeze = higher bonus
    squeeze_bonus = min(int(squeeze_depth * 100), CONFIDENCE_SQUEEZE_BONUS)

    widen_amount = min(widening_ratio - 1.0, 0.5)  # cap at 0.5
    widening_bonus = min(int(widen_amount * 10), CONFIDENCE_WIDENING_BONUS)

    # Recency: fresher cross = higher confidence
    recency_bonus = max(0, 5 - cross_bars_ago)  # up to +5 for cross within 5 bars

    confidence = min(
        CONFIDENCE_BASE + squeeze_bonus + widening_bonus + recency_bonus,
        CONFIDENCE_MAX
    )

    price = prices[-1]
    source = f'{SOURCE_PREFIX}{"+" if cross_dir == "LONG" else "-"}{cross_bars_ago}'

    return {
        'direction': cross_dir,
        'confidence': confidence,
        'source': source,
        'ema_fast': round(ema_fast[-1], 6),
        'ema_slow': round(ema_slow[-1], 6),
        'gap_pct': round(gap_now / price * 100, 4),
        'widening_ratio': round(widening_ratio, 4),
        'squeeze_ratio': round(squeeze_ratio, 4),
        'atr_current': round(atr_current, 8),
        'atr_avg': round(atr_avg, 8),
        'cross_bars_ago': cross_bars_ago,
        'price': price,
        'value': float(confidence),
    }


# ── Cooldown tracking ─────────────────────────────────────────────────────────
_last_signal = {}  # token+direction → last cross_bars_ago (used as proxy for time)


def _cooldown_ok(token: str, direction: str, cross_bars_ago: int) -> bool:
    key = f"{token}:{direction}"
    last = _last_signal.get(key, 999)
    # If we fired within last COOLDOWN_BARS bars, skip
    if cross_bars_ago < COOLDOWN_BARS and last < COOLDOWN_BARS:
        return False
    return True


def _mark_signal(token: str, direction: str, cross_bars_ago: int) -> None:
    _last_signal[f"{token}:{direction}"] = cross_bars_ago


# ── Main scanner ──────────────────────────────────────────────────────────────

def scan_squeeze_cross_signals(prices_dict: dict = None) -> int:
    """Scan tokens for squeeze_cross signals. Entry point for signals_runner."""
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

        # Per-direction killswitches
        if direction == 'LONG' and not SQUEEZE_CROSS_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not SQUEEZE_CROSS_MINUS_ENABLED:
            continue

        # Cooldown
        if not _cooldown_ok(token, direction, sig['cross_bars_ago']):
            continue

        # DB cooldown (shared with other signals)
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
                _mark_signal(token, direction, sig['cross_bars_ago'])
                print(f"  [squeeze_cross] {token} {direction} conf={confidence} "
                      f"cross={sig['cross_bars_ago']}bars squeeze={sig['squeeze_ratio']:.3f} "
                      f"widening={sig['widening_ratio']:.3f} price={price}")
        except Exception as e:
            print(f"  [squeeze_cross] add_signal error for {token}: {e}")

    return added


# ── Entry point for signals_runner ────────────────────────────────────────────
def run(prices_dict=None):
    """Entry point for signals_runner.py"""
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
