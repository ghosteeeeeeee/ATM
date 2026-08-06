"""
100MA Bounce/Cross signal — mean-reversion at moving average with trend continuation.

SIGNAL TYPES:
  - ma_100_bounce: price bounces off 100MA → trend continuation entry
  - ma_100_cross: price crosses through 100MA → trend reversal entry

LOGIC:
  1. Compute MA(100) from 1m close prices (price_history)
  2. BOUNCE: price nears MA, bounces in trend direction → continuation
  3. CROSS: price closes beyond MA by threshold → reversal
  4. Trend filter: only fire continuation in direction of broader trend

INTENT:
  The 100MA acts as dynamic support/resistance. Bounces = trend intact,
  crosses = trend changing. Two complementary signals from the same indicator.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal

# ── Parameters ──────────────────────────────────────────────────────────────
MA_PERIOD = 100              # 100-period MA (~1.7 hours on 1m)
BOUNCE_TOUCH_ATR = 0.5      # price must be within 0.5 * ATR of MA to count as "touching"
BOUNCE_FOLLOW_ATR = 0.15     # bounce confirmed if next candle moves 0.15 * ATR away from MA
CROSS_CONFIRM_ATR = 0.2      # cross confirmed if close is 0.2 * ATR beyond MA
MIN_SEPARATION_CANDLES = 5   # min candles between signals (avoid noise)
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
    # Wilder's smoothed
    atr[period] = trs[:period].mean()
    for i in range(period + 1, len(closes)):
        atr[i] = (atr[i - 1] * (period - 1) + trs[i - 1]) / period
    return atr


def detect_ma_100_signal(token: str, candles: list, price: float) -> dict:
    """Detect 100MA bounce or cross signal.

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

    # ── Trend direction (from MA slope) ────────────────────────────────────
    # MA rising = uptrend, MA falling = downtrend
    ma_slope = current_ma - prev_ma
    trend = 'LONG' if ma_slope > 0 else 'SHORT'

    # ── Check for CROSS (reversal) ─────────────────────────────────────────
    # Price was on one side of MA, now on the other
    prev_above = prev_price > prev_ma
    curr_above = current_price > current_ma

    if prev_above != curr_above:
        # Cross happened! Check if it's significant
        cross_distance = abs(current_price - current_ma)
        if cross_distance >= current_atr * CROSS_CONFIRM_ATR:
            # Reversal signal: if price crossed ABOVE → LONG (trend reversing up)
            # If price crossed BELOW → SHORT (trend reversing down)
            if curr_above:
                direction = 'LONG'
                signal_type = 'ma_100_cross'
                # Confidence based on cross strength
                cross_strength = cross_distance / current_atr
                conf = min(85, max(65, int(65 + cross_strength * 10)))
            else:
                direction = 'SHORT'
                signal_type = 'ma_100_cross'
                cross_strength = cross_distance / current_atr
                conf = min(85, max(65, int(65 + cross_strength * 10)))

            return {
                'direction': direction,
                'confidence': conf,
                'signal_type': signal_type,
                'source': f'ma100-cross',
                'value': float(round(cross_distance / current_price * 100, 4)),
                'ma': current_ma,
                'atr': current_atr,
            }

    # ── Check for BOUNCE (continuation) ────────────────────────────────────
    # Price near MA and bouncing in trend direction
    distance_to_ma = abs(current_price - current_ma)
    touch_threshold = current_atr * BOUNCE_TOUCH_ATR

    if distance_to_ma <= touch_threshold:
        # Price is near MA. Check for bounce confirmation.
        # Look at last 3 candles: did price touch MA and bounce away?
        for lookback in range(1, min(4, len(closes))):
            idx = -1 - lookback
            if abs(closes[idx] - ma[idx]) <= touch_threshold:
                # Found a touch. Check if current candle bounced away
                bounce_dir = current_price - closes[idx]
                follow_threshold = current_atr * BOUNCE_FOLLOW_ATR

                if bounce_dir > follow_threshold and trend == 'LONG':
                    # Bounced UP from MA in uptrend → continuation LONG
                    bounce_strength = bounce_dir / current_atr
                    conf = min(85, max(65, int(65 + bounce_strength * 8)))
                    return {
                        'direction': 'LONG',
                        'confidence': conf,
                        'signal_type': 'ma_100_bounce',
                        'source': f'ma100-bounce',
                        'value': float(round(distance_to_ma / current_price * 100, 4)),
                        'ma': current_ma,
                        'atr': current_atr,
                    }
                elif bounce_dir < -follow_threshold and trend == 'SHORT':
                    # Bounced DOWN from MA in downtrend → continuation SHORT
                    bounce_strength = abs(bounce_dir) / current_atr
                    conf = min(85, max(65, int(65 + bounce_strength * 8)))
                    return {
                        'direction': 'SHORT',
                        'confidence': conf,
                        'signal_type': 'ma_100_bounce',
                        'source': f'ma100-bounce',
                        'value': float(round(distance_to_ma / current_price * 100, 4)),
                        'ma': current_ma,
                        'atr': current_atr,
                    }

    return None


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

        # Freshness guard
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []

        return [{'close': r[1]} for r in rows]
    except Exception as e:
        print(f"  [ma100] error for {token}: {e}")
        return []


def scan_ma_100_signals(prices_dict: dict) -> tuple:
    """Scan tokens for 100MA signals.

    Args:
        prices_dict: token -> {'price': float, ...}

    Returns:
        (count, list of tokens that fired)
    """
    from hermes_constants import (
        MA_100_BOUNCE_ENABLED, MA_100_CROSS_ENABLED,
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

        # Direction kill-switch
        if sig['direction'] == 'LONG' and not MA_100_BOUNCE_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not MA_100_CROSS_ENABLED:
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
                  f'sig={sig["signal_type"]} ma={sig["ma"]:.6f} '
                  f'({ma_dist:.3f}% off) [{sig["source"]}]')

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
    test = {k: v for k, v in prices.items() if k in ('ASTER', 'BTC', 'ETH', 'SOL') and v.get('price')}
    if not test:
        test = dict(list(prices.items())[:10])
    print(f"[ma100] Testing on {len(test)} tokens...")
    n, tokens = scan_ma_100_signals(test)
    print(f"[ma100] Done. {n} signals emitted.")
