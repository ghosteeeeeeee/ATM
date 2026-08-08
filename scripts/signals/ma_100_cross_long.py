"""
100MA Cross LONG — trend reversal at 100-period moving average (LONG-specific).

SIGNAL TYPE:
  - ma_100_cross_long: price crosses above 100MA → LONG entry

LONG-SPECIFIC PARAMETERS:
  1. Standard entry threshold (CROSS_CONFIRM_ATR = 0.3)
  2. Standard volatility requirement (MIN_ATR_PCT = 0.04)
  3. Standard stop loss (1.2%)
  4. 2-candle confirmation
  5. No volume requirement
  6. No regime filter
  7. No time filter

BACKTEST RESULTS (7d):
  - LONG: 75% WR, +$0.08 (8 trades)
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown

# ── LONG-Specific Parameters ───────────────────────────────────────────────
MA_PERIOD = 20               # MA(20) on 5m = 100 minutes lookback
CROSS_CONFIRM_ATR = 0.3     # STANDARD: cross confirmed if close is 0.3 * ATR beyond MA
MIN_ATR_PCT = 0.04           # STANDARD: minimum ATR% to fire (filters low-vol tokens)
COOLDOWN_CANDLES = 6         # 30 min cooldown on 5m candles
ATR_PERIOD = 14              # ATR period for volatility normalization
REQUIRE_2_CANDLE = True      # require candle before cross to confirm pre-cross side
STOP_LOSS_PCT = 1.0          # TIGHTER: 1.0% stop loss (improves WR)


def _resample_5m(closes_1m: np.ndarray) -> np.ndarray:
    """Resample 1m closes to 5m — close of each 5-bar window (last element)."""
    n = len(closes_1m)
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


def detect_ma_100_long(token: str, candles: list, price: float) -> dict:
    """Detect 100MA cross LONG signal on 5m data.

    Args:
        token: token symbol
        candles: list of {close} dicts (oldest first), 1m data
        price: current price

    Returns:
        dict with {direction, confidence, signal_type, source, value} or None
    """
    if not candles or len(candles) < 600:
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

    # Only LONG (price crossing above MA)
    if not curr_above:
        return None  # This is a SHORT cross, skip

    # Signed cross distance: price must be above MA
    cross_distance = current_price - current_ma

    if cross_distance < current_atr * CROSS_CONFIRM_ATR:
        return None  # cross too weak

    # 2-candle confirmation
    if REQUIRE_2_CANDLE and i >= 2:
        prev_prev_price = closes_5m[i - 2]
        prev_prev_ma = ma[i - 2]
        if not np.isnan(prev_prev_ma):
            prev_prev_above = prev_prev_price > prev_prev_ma
            if prev_prev_above == curr_above:
                return None  # Not a genuine cross

    # Direction and confidence
    cross_strength = cross_distance / current_atr
    conf = min(85, max(65, int(65 + cross_strength * 10)))

    return {
        'direction': 'LONG',
        'confidence': conf,
        'signal_type': 'ma_100_cross_long',
        'source': 'ma100-cross-long',
        'value': float(round(cross_distance / current_price * 100, 4)),
        'ma': current_ma,
        'atr': current_atr,
        'atr_pct': round(atr_pct, 4),
        'stop_loss_pct': STOP_LOSS_PCT,
    }


def scan_ma_100_long_signals(prices_dict: dict) -> int:
    """Scan tokens for ma_100_cross_long signals."""
    from signal_schema import get_all_latest_prices
    if prices_dict is None:
        prices_dict = get_all_latest_prices()

    added = 0
    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Get 1m candles
        try:
            import sqlite3
            from paths import HERMES_DATA
            conn = sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=10)
            cur = conn.cursor()
            cur.execute("""
                SELECT close FROM candles_1m
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT 700
            """, (token.upper(),))
            rows = cur.fetchall()
            conn.close()

            if not rows or len(rows) < 600:
                continue

            candles = [{'close': r[0]} for r in reversed(rows)]
        except Exception:
            continue

        sig = detect_ma_100_long(token, candles, price)
        if sig is None:
            continue

        # Check cooldown
        if get_cooldown(token, direction='LONG'):
            continue

        # Check blacklist
        from hermes_constants import LONG_BLACKLIST
        if token.upper() in LONG_BLACKLIST:
            continue

        # Check kill switch
        from hermes_constants import MA_100_CROSS_PLUS_ENABLED
        if not MA_100_CROSS_PLUS_ENABLED:
            continue

        # Add signal
        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=sig['signal_type'],
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=1)

    return added


def run():
    """Entry point for signals_runner."""
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    return scan_ma_100_long_signals(prices)


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_ma_100_long_signals(None)
    print(f'ma_100_cross_long: {n} signals emitted')
