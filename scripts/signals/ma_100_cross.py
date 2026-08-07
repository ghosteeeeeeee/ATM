"""
100MA Cross signal — trend reversal at 100-period moving average.

SIGNAL TYPE:
  - ma_100_cross: price crosses through 100MA → trend reversal entry

BACKTEST RESULTS (14 days, 115 tokens, 5m candles, MA(20)):
  - SHORT: 55.8% WR, +0.076% avg, +507.1% total (6,354 trades)
  - LONG: 51.7% WR, +0.056% avg, +368.1% total (6,574 trades)
  - 2-candle confirmation is the key filter — both sides above 50% WR

LOGIC:
  1. Compute MA(20) on 5m candles (= 100 minutes, same as MA(100) on 1m)
  2. Detect cross: previous candle on one side, current on the other
  3. Confirm cross: close must be >= 0.3 * ATR beyond MA (in trade direction)
  4. 2-candle confirmation: candle before cross must be on pre-cross side
  5. Filter: only fire on tokens with ATR% >= 0.04%
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown

# ── Parameters (backtested optimal) ────────────────────────────────────────
MA_PERIOD = 20               # MA(20) on 5m = 100 minutes lookback
CROSS_CONFIRM_ATR = 0.3     # cross confirmed if close is 0.3 * ATR beyond MA
MIN_ATR_PCT = 0.04           # minimum ATR% to fire (filters low-vol tokens)
COOLDOWN_CANDLES = 6         # 30 min cooldown on 5m candles
ATR_PERIOD = 14              # ATR period for volatility normalization
REQUIRE_2_CANDLE = True      # require candle before cross to confirm pre-cross side


def _resample_5m(closes_1m: np.ndarray) -> np.ndarray:
    """Resample 1m closes to 5m — close of each 5-bar window (last element)."""
    n = len(closes_1m)
    # Take the close at minute 5, 10, 15, ... (index 4, 9, 14, ...)
    indices = np.arange(4, n, 5)
    return closes_1m[indices]


def _compute_ma(closes: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    ma = np.full(len(closes), np.nan)
    for i in range(period - 1, len(closes)):
        ma[i] = closes[i - period + 1:i + 1].mean()
    return ma


def _compute_atr(closes: np.ndarray, period: int = ATR_PERIOD) -> np.ndarray:
    """ATR from close-only data."""
    atr = np.full(len(closes), np.nan)
    if len(closes) < period + 1:
        return atr
    trs = np.abs(np.diff(closes))
    atr[period] = trs[:period].mean()
    for i in range(period + 1, len(closes)):
        atr[i] = (atr[i - 1] * (period - 1) + trs[i - 1]) / period
    return atr


def detect_ma_100_signal(token: str, candles: list, price: float) -> dict:
    """Detect 100MA cross signal on 5m data.

    Args:
        token: token symbol
        candles: list of {close} dicts (oldest first), 1m data
        price: current price

    Returns:
        dict with {direction, confidence, signal_type, source, value} or None
    """
    if not candles or len(candles) < 600:  # need enough for 5m resample + MA
        return None
    if price is None or price <= 0:
        return None

    closes_1m = np.array([c['close'] for c in candles], dtype=np.float64)
    closes_5m = _resample_5m(closes_1m)

    if len(closes_5m) < MA_PERIOD + ATR_PERIOD + 5:
        return None

    ma = _compute_ma(closes_5m, MA_PERIOD)
    atr = _compute_atr(closes_5m, ATR_PERIOD)

    # Check last 2 candles on 5m for cross + confirmation
    i = len(closes_5m) - 1
    if i < 2:
        return None
    if np.isnan(ma[i]) or np.isnan(atr[i]) or atr[i] <= 0:
        return None
    if np.isnan(ma[i - 1]):
        return None

    current_ma = ma[i]
    current_atr = atr[i]
    current_price = closes_5m[i]
    prev_price = closes_5m[i - 1]
    prev_ma = ma[i - 1]

    # Volatility filter
    atr_pct = current_atr / current_price * 100
    if atr_pct < MIN_ATR_PCT:
        return None

    # Cross detection: previous candle on opposite side of MA
    prev_above = prev_price > prev_ma
    curr_above = current_price > current_ma

    if prev_above == curr_above:
        return None  # no cross

    # Signed cross distance: positive = price is beyond MA in trade direction
    if curr_above:
        cross_distance = current_price - current_ma    # LONG: price above MA
    else:
        cross_distance = current_ma - current_price    # SHORT: price below MA

    if cross_distance < current_atr * CROSS_CONFIRM_ATR:
        return None  # cross too weak

    # 2-candle confirmation: candle BEFORE the cross must have been on the
    # same side as i-1 (pre-cross side). This confirms i-2 and i-1 were
    # both on the pre-cross side, making the cross to i's side genuine.
    if REQUIRE_2_CANDLE and i >= 2:
        prev_prev_price = closes_5m[i - 2]
        prev_prev_ma = ma[i - 2]
        if not np.isnan(prev_prev_ma):
            # Before cross: i-2 and i-1 should be on same side (opposite of current)
            prev_prev_above = prev_prev_price > prev_prev_ma
            if prev_prev_above == curr_above:
                # i-2 was already on the current side — not a real cross, just noise
                return None

    # Direction and confidence
    cross_strength = cross_distance / current_atr
    conf = min(85, max(65, int(65 + cross_strength * 10)))

    direction = 'LONG' if curr_above else 'SHORT'

    return {
        'direction': direction,
        'confidence': conf,
        'signal_type': 'ma_100_cross',
        'source': f'ma100-cross{"+" if direction == "LONG" else "-"}',
        'value': float(round(cross_distance / current_price * 100, 4)),
        'ma': current_ma,
        'atr': current_atr,
        'atr_pct': atr_pct,
    }


# ── Scanner ─────────────────────────────────────────────────────────────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

def _get_candles(token: str, lookback: int = 2500) -> list:
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

        candles = _get_candles(token, lookback=2500)
        if not candles or len(candles) < 600:
            continue

        sig = detect_ma_100_signal(token, candles, price)
        if sig is None:
            continue

        if sig['direction'] == 'LONG' and not MA_100_CROSS_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not MA_100_CROSS_MINUS_ENABLED:
            continue

        token_upper = token.upper()
        if sig['direction'] == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if sig['direction'] == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        if get_cooldown(token_upper, direction=sig['direction']):
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
            timeframe='5m',
        )
        if sid:
            set_cooldown(token_upper, sig['direction'], hours=0.5)  # 30 min cooldown
            added += 1
            signaled_tokens.append(token_upper)
            ma_dist = abs(price - sig['ma']) / price * 100
            print(f'  {sig["direction"]:5s} {token:8s} conf={sig["confidence"]:3.0f}% '
                  f'cross={sig["value"]:.4f}% atr%={sig["atr_pct"]:.3f} '
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
