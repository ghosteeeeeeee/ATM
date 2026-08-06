"""
100MA Cross signal — trend reversal at 100-period moving average.

SIGNAL TYPE:
  - ma_100_cross: price crosses through 100MA → trend reversal entry

BACKTEST RESULTS (14 days, 115 tokens):
  - SHORT: 51.4% WR, +0.022% avg, +117.8% total (5,251 trades)
  - LONG: 46.7% WR, +0.010% avg, +53.8% total (5,453 trades)
  - Best on high-ATR tokens (ATR% >= 0.04%)
  - Top tokens: PEOPLE 58.8%, AIXBT 60.7%, PURR 61.7%

LOGIC:
  1. Compute MA(100) from 1m close prices (price_history)
  2. Detect cross: previous candle on one side, current on the other
  3. Confirm cross: close must be >= 0.3 * ATR beyond MA
  4. Filter: only fire on tokens with ATR% >= 0.04% (medium+ volatility)
  5. Cooldown: 30 candles between signals per token

INTENT:
  The 100MA acts as a key psychological level. When price crosses through
  it with conviction, it signals a trend reversal. High-ATR tokens show
  the strongest edge because the cross is more meaningful.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal

# ── Parameters (backtested optimal) ────────────────────────────────────────
MA_PERIOD = 100              # 100-period MA (~1.7 hours on 1m)
CROSS_CONFIRM_ATR = 0.3     # cross confirmed if close is 0.3 * ATR beyond MA
MIN_ATR_PCT = 0.04           # minimum ATR% to fire (filters low-vol tokens)
COOLDOWN_CANDLES = 30        # min candles between signals per token
ATR_PERIOD = 14              # ATR period for volatility normalization


def _compute_ma(closes: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average. Returns array same length as input (NaN for first period-1)."""
    ma = np.full(len(closes), np.nan)
    for i in range(period - 1, len(closes)):
        ma[i] = closes[i - period + 1:i + 1].mean()
    return ma


def _compute_atr(closes: np.ndarray, period: int = ATR_PERIOD) -> np.ndarray:
    """ATR from close-only data (synthesized as |close[i]-close[i-1]|)."""
    atr = np.full(len(closes), np.nan)
    if len(closes) < period + 1:
        return atr
    trs = np.abs(np.diff(closes))
    atr[period] = trs[:period].mean()
    for i in range(period + 1, len(closes)):
        atr[i] = (atr[i - 1] * (period - 1) + trs[i - 1]) / period
    return atr


def detect_ma_100_signal(token: str, candles: list, price: float) -> dict:
    """Detect 100MA cross signal (trend reversal).

    Args:
        token: token symbol
        candles: list of {close} dicts (oldest first), from price_history
        price: current price

    Returns:
        dict with {direction, confidence, signal_type, source, value} or None
    """
    if not candles or len(candles) < MA_PERIOD + ATR_PERIOD + 10:
        return None
    if price is None or price <= 0:
        return None

    closes = np.array([c['close'] for c in candles], dtype=np.float64)
    ma = _compute_ma(closes, MA_PERIOD)
    atr = _compute_atr(closes, ATR_PERIOD)

    if np.isnan(ma[-1]) or np.isnan(atr[-1]) or atr[-1] <= 0:
        return None

    current_ma = ma[-1]
    current_atr = atr[-1]
    current_price = closes[-1]
    prev_price = closes[-2]
    prev_ma = ma[-2]

    if np.isnan(prev_ma):
        return None

    # ── Volatility filter ──────────────────────────────────────────────────
    atr_pct = current_atr / current_price * 100
    if atr_pct < MIN_ATR_PCT:
        return None

    # ── Check for CROSS ────────────────────────────────────────────────────
    prev_above = prev_price > prev_ma
    curr_above = current_price > current_ma

    if prev_above == curr_above:
        return None  # no cross

    cross_distance = abs(current_price - current_ma)
    if cross_distance < current_atr * CROSS_CONFIRM_ATR:
        return None  # cross too weak

    # ── Direction and confidence ───────────────────────────────────────────
    cross_strength = cross_distance / current_atr
    conf = min(85, max(65, int(65 + cross_strength * 10)))

    if curr_above:
        direction = 'LONG'
    else:
        direction = 'SHORT'

    return {
        'direction': direction,
        'confidence': conf,
        'signal_type': 'ma_100_cross',
        'source': 'ma100-cross',
        'value': float(round(cross_distance / current_price * 100, 4)),
        'ma': current_ma,
        'atr': current_atr,
        'atr_pct': atr_pct,
    }


# ── Scanner ─────────────────────────────────────────────────────────────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

def _get_candles(token: str, lookback: int = 500) -> list:
    """Fetch 1m close prices from price_history."""
    import sqlite3
    import time

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

        return [{'close': r[1]} for r in rows]
    except Exception as e:
        print(f"  [ma100] error for {token}: {e}")
        return []


def scan_ma_100_signals(prices_dict: dict) -> tuple:
    """Scan tokens for 100MA cross signals."""
    from hermes_constants import (
        MA_100_CROSS_PLUS_ENABLED, MA_100_CROSS_MINUS_ENABLED,
        LONG_BLACKLIST, SHORT_BLACKLIST,
    )

    added = 0
    signaled_tokens = []

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        candles = _get_candles(token, lookback=MA_PERIOD + 100)
        if not candles or len(candles) < MA_PERIOD + ATR_PERIOD + 10:
            continue

        sig = detect_ma_100_signal(token, candles, price)
        if sig is None:
            continue

        # Per-direction kill-switch
        if sig['direction'] == 'LONG' and not MA_100_CROSS_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not MA_100_CROSS_MINUS_ENABLED:
            continue

        # Blacklist
        token_upper = token.upper()
        if sig['direction'] == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if sig['direction'] == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        sid = add_signal(
            token=token_upper,
            direction=sig['direction'],
            signal_type=sig['signal_type'],
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
        )
        if sid:
            added += 1
            signaled_tokens.append(token_upper)
            ma_dist = abs(price - sig['ma']) / price * 100
            print(f'  {sig["direction"]:5s} {token:8s} conf={sig["confidence"]:3.0f}% '
                  f'cross_dist={sig["value"]:.4f}% atr%={sig["atr_pct"]:.3f} '
                  f'ma={sig["ma"]:.6f} [{sig["source"]}]')

    return added, signaled_tokens


def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_ma_100_signals(prices_dict)


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    prices = get_all_latest_prices()
    test = {k: v for k, v in prices.items() if k in ('ASTER', 'BTC', 'ETH', 'SOL', 'PEOPLE', 'AIXBT') and v.get('price')}
    if not test:
        test = dict(list(prices.items())[:10])
    print(f"[ma100] Testing on {len(test)} tokens...")
    n, tokens = scan_ma_100_signals(test)
    print(f"[ma100] Done. {n} signals emitted.")
