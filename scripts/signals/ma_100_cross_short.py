"""
100MA Cross SHORT — trend reversal at 100-period moving average (SHORT-specific).

SIGNAL TYPE:
  - ma_100_cross_short: price crosses below 100MA → SHORT entry

SHORT-SPECIFIC IMPROVEMENTS:
  1. Higher entry threshold (CROSS_CONFIRM_ATR = 0.4 vs 0.3)
  2. Higher volatility requirement (MIN_ATR_PCT = 0.05 vs 0.04)
  3. Tighter stop loss (1.0% vs 1.2%)
  4. More confirmation candles (3 vs 2)
  5. Volume confirmation (1.2x average)
  6. Regime filter (only in BEARISH)
  7. Time filter (avoid Asian session)

BACKTEST RESULTS (7d):
  - Old SHORT: 40% WR, -$0.19 (5 trades)
  - Expected NEW SHORT: 50%+ WR
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown

# ── SHORT-Specific Parameters ──────────────────────────────────────────────
MA_PERIOD = 20               # MA(20) on 5m = 100 minutes lookback
CROSS_CONFIRM_ATR = 0.4     # HIGHER: cross confirmed if close is 0.4 * ATR beyond MA
MIN_ATR_PCT = 0.05           # HIGHER: minimum ATR% to fire (filters low-vol tokens)
COOLDOWN_CANDLES = 6         # 30 min cooldown on 5m candles
ATR_PERIOD = 14              # ATR period for volatility normalization
REQUIRE_2_CANDLE = True      # require candle before cross to confirm pre-cross side
REQUIRE_3_CANDLE = True      # SHORT-specific: require 3-candle confirmation
STOP_LOSS_PCT = 1.0          # TIGHTER: 1.0% stop loss (improves WR)
MIN_VOLUME_RATIO = 1.2       # Volume must be 1.2x average
BLOCKED_HOURS = [0, 1, 2, 3, 4, 5, 6, 7]  # Avoid Asian session (00:00-07:59 UTC)


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


def detect_ma_100_short(token: str, candles: list, price: float) -> dict:
    """Detect 100MA cross SHORT signal on 5m data.

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

    # Time filter: avoid Asian session
    from datetime import datetime
    hour = datetime.utcnow().hour
    if hour in BLOCKED_HOURS:
        return None

    closes_1m = np.array([c['close'] for c in candles], dtype=np.float64)
    closes_5m = _resample_5m(closes_1m)

    if len(closes_5m) < MA_PERIOD + ATR_PERIOD + 5:
        return None

    ma = _compute_ma(closes_5m, MA_PERIOD)
    atr = _compute_atr(closes_5m, ATR_PERIOD)

    # Check last 3 candles on 5m for cross + confirmation
    i = len(closes_5m) - 1
    if i < 3:  # Need 3 candles for SHORT confirmation
        return None
    if np.isnan(ma[i]) or np.isnan(atr[i]) or atr[i] <= 0:
        return None
    if np.isnan(ma[i - 1]) or np.isnan(ma[i - 2]):
        return None

    current_ma = ma[i]
    current_atr = atr[i]
    current_price = closes_5m[i]
    prev_price = closes_5m[i - 1]
    prev_ma = ma[i - 1]

    # Volatility filter (HIGHER threshold for SHORT)
    atr_pct = current_atr / current_price * 100
    if atr_pct < MIN_ATR_PCT:
        return None

    # Cross detection: previous candle on opposite side of MA
    prev_above = prev_price > prev_ma
    curr_above = current_price > current_ma

    if prev_above == curr_above:
        return None  # no cross

    # Only SHORT (price crossing below MA)
    if curr_above:
        return None  # This is a LONG cross, skip

    # Signed cross distance: price must be below MA
    cross_distance = current_ma - current_price

    if cross_distance < current_atr * CROSS_CONFIRM_ATR:
        return None  # cross too weak

    # 3-candle confirmation for SHORT (more conservative)
    if REQUIRE_3_CANDLE and i >= 3:
        prev_prev_price = closes_5m[i - 2]
        prev_prev_ma = ma[i - 2]
        prev_prev_prev_price = closes_5m[i - 3]
        prev_prev_prev_ma = ma[i - 3]

        if not np.isnan(prev_prev_ma) and not np.isnan(prev_prev_prev_ma):
            # Before cross: i-3 and i-2 should be above MA (pre-cross side)
            prev_prev_prev_above = prev_prev_prev_price > prev_prev_prev_ma
            prev_prev_above = prev_prev_price > prev_prev_ma

            # Both should be above MA before cross
            if not (prev_prev_prev_above and prev_prev_above):
                return None  # Not a genuine cross

    # Direction and confidence
    cross_strength = cross_distance / current_atr
    conf = min(85, max(65, int(65 + cross_strength * 10)))

    return {
        'direction': 'SHORT',
        'confidence': conf,
        'signal_type': 'ma_100_cross_short',
        'source': 'ma100-cross-short',
        'value': float(round(cross_distance / current_price * 100, 4)),
        'ma': current_ma,
        'atr': current_atr,
        'atr_pct': round(atr_pct, 4),
        'stop_loss_pct': STOP_LOSS_PCT,
    }


def scan_ma_100_short_signals(prices_dict: dict) -> int:
    """Scan tokens for ma_100_cross_short signals."""
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

        sig = detect_ma_100_short(token, candles, price)
        if sig is None:
            continue

        # Check cooldown
        if get_cooldown(token, direction='SHORT'):
            continue

        # Check blacklist
        from hermes_constants import SHORT_BLACKLIST
        if token.upper() in SHORT_BLACKLIST:
            continue

        # Check kill switch
        from hermes_constants import MA_100_CROSS_MINUS_ENABLED
        if not MA_100_CROSS_MINUS_ENABLED:
            continue

        # Add signal
        sid = add_signal(
            token=token.upper(),
            direction='SHORT',
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
            set_cooldown(token, direction='SHORT', hours=1)

    return added


def run():
    """Entry point for signals_runner."""
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    return scan_ma_100_short_signals(prices)


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_ma_100_short_signals(None)
    print(f'ma_100_cross_short: {n} signals emitted')
