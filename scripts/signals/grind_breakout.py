#!/usr/bin/env python3
"""grind_breakout — Steady grind + late breakout signal.

THESIS:
  When price establishes a steady trend (consistent direction, positive slope)
  and then accelerates (velocity increasing, breaking above recent highs),
  the grind phase was accumulation and the breakout is distribution beginning.

ENTRY CONDITIONS (LONG):
  1. Price above EMA20 for >=60% of last 30 bars (trend purity)
  2. Linear regression slope > threshold (positive trend)
  3. velocity_5m > velocity_15m * 1.2 (acceleration)
  4. Current close > highest high of last 20 bars (breakout)
  5. RSI 35-65 (quality filter — not overbought/oversold)
  6. <=3 consecutive green candles (not chasing)

DATA SOURCE:
  - price_history (1m) from signals_hermes.db — always fresh
  - All indicators computed on the fly from 1m data
"""

import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    GRIND_BREAKOUT_ENABLED,
    GRIND_BREAKOUT_PLUS_ENABLED,
    GRIND_BREAKOUT_MINUS_ENABLED,
    GRIND_BREAKOUT_COOLDOWN_HOURS,
    GRIND_BREAKOUT_PURITY_MIN,
    GRIND_BREAKOUT_SLOPE_MIN,
    GRIND_BREAKOUT_EMA_PERIOD,
    GRIND_BREAKOUT_PURPOSE_LOOKBACK,
    GRIND_BREAKOUT_ACCEL_MULT,
    GRIND_BREAKOUT_MIN_VELOCITY,
    GRIND_BREAKOUT_BREAKOUT_WINDOW,
    GRIND_BREAKOUT_BREAKOUT_BUFFER,
    GRIND_BREAKOUT_RSI_MAX,
    GRIND_BREAKOUT_RSI_MIN,
    GRIND_BREAKOUT_MAX_CONSEC_GREEN,
    GRIND_BREAKOUT_MAX_CONSEC_RED,
    GRIND_BREAKOUT_CONF_BASE,
    GRIND_BREAKOUT_CONF_FLOOR,
    GRIND_BREAKOUT_CONF_CAP,
    GRIND_BREAKOUT_CONF_SLOPE_BONUS,
    GRIND_BREAKOUT_CONF_ACCEL_BONUS,
    GRIND_BREAKOUT_CONF_BREAKOUT_BONUS,
    GRIND_BREAKOUT_CONF_PURITY_BONUS,
    GRIND_BREAKOUT_LOOKBACK_1M,
    GRIND_BREAKOUT_RSI_PERIOD,
    GRIND_BREAKOUT_MIN_BARS,
    GRIND_BREAKOUT_VEL_SHORT_BARS,
    GRIND_BREAKOUT_VEL_LONG_BARS,
    GRIND_BREAKOUT_CONSEC_LOOKBACK,
    GRIND_BREAKOUT_BREAKOUT_BONUS_BUFFER,
    GRIND_BREAKOUT_PURITY_BONUS_MIN,
    GRIND_BREAKOUT_FRESHNESS_SECS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'grind_breakout_long'
SIGNAL_TYPE_SHORT = 'grind_breakout_short'
SOURCE_LONG = 'grind-breakout+'
SOURCE_SHORT = 'grind-breakout-'

_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')


def _log(msg):
    print(f'[grind-breakout] {msg}', flush=True)


def _get_prices(token, limit):
    """Fetch 1m prices from price_history. Returns oldest-first list."""
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT price FROM price_history
            WHERE token = ? ORDER BY timestamp DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _ema(prices, period):
    """Compute EMA series. Returns list same length as prices."""
    if len(prices) < period:
        return [None] * len(prices)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    ema = sum(prices[:period]) / period
    result.append(ema)
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
        result.append(ema)
    return result


def _rsi(prices, period=14):
    """Compute RSI series. Returns list same length as prices."""
    result = [None] * len(prices)
    if len(prices) < period + 1:
        return result
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        result[period] = 100.0
    else:
        result[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            result[i + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return result


def detect(token):
    """Detect grind_breakout signal for a token.

    Returns {direction, confidence, value, price} or None.
    """
    lookback = GRIND_BREAKOUT_LOOKBACK_1M
    prices = _get_prices(token, lookback)
    if len(prices) < GRIND_BREAKOUT_MIN_BARS:
        return None

    n = len(prices)
    current_price = prices[-1]

    # Precompute indicators
    ema_series = _ema(prices, GRIND_BREAKOUT_EMA_PERIOD)
    rsi_series = _rsi(prices, GRIND_BREAKOUT_RSI_PERIOD)

    current_ema = ema_series[-1]
    current_rsi = rsi_series[-1]
    if current_ema is None or current_rsi is None:
        return None

    # Purity: % of last PURPOSE_LOOKBACK bars above/below EMA
    PL = GRIND_BREAKOUT_PURPOSE_LOOKBACK
    recent_prices = prices[-PL:]
    recent_ema = ema_series[-PL:]
    valid = [(p, e) for p, e in zip(recent_prices, recent_ema) if e is not None]
    if len(valid) < PL // 2:
        return None
    above_count = sum(1 for p, e in valid if p > e)
    purity_long = above_count / len(valid)
    purity_short = 1 - purity_long

    # Linear regression slope (normalized)
    window = prices[-PL:]
    x = list(range(len(window)))
    x_mean = sum(x) / len(x)
    y_mean = sum(window) / len(window)
    num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, window))
    den = sum((xi - x_mean) ** 2 for xi in x)
    slope = num / den if den > 0 else 0
    slope_norm = slope / y_mean if y_mean > 0 else 0

    # Breakout: highest/lowest of last BREAKOUT_WINDOW
    BW = GRIND_BREAKOUT_BREAKOUT_WINDOW
    range_high = max(prices[-(BW + 1):-1])
    range_low = min(prices[-(BW + 1):-1])

    # Velocity (5m vs 15m proxy from 1m data)
    if n >= GRIND_BREAKOUT_VEL_SHORT_BARS:
        vel_5m = (current_price - prices[-GRIND_BREAKOUT_VEL_SHORT_BARS]) / prices[-GRIND_BREAKOUT_VEL_SHORT_BARS] * 100
    else:
        vel_5m = 0
    if n >= GRIND_BREAKOUT_VEL_LONG_BARS:
        vel_15m = (current_price - prices[-GRIND_BREAKOUT_VEL_LONG_BARS]) / prices[-GRIND_BREAKOUT_VEL_LONG_BARS] * 100
    else:
        vel_15m = 0

    # Consecutive candles (5m approximated as 5 1m bars)
    consec_green = 0
    for i in range(n - 1, max(n - GRIND_BREAKOUT_CONSEC_LOOKBACK - 1, 0), -1):
        if prices[i] > prices[i - 1]:
            consec_green += 1
        else:
            break
    consec_red = 0
    for i in range(n - 1, max(n - GRIND_BREAKOUT_CONSEC_LOOKBACK - 1, 0), -1):
        if prices[i] < prices[i - 1]:
            consec_red += 1
        else:
            break

    # ── LONG signal ──
    if (purity_long >= GRIND_BREAKOUT_PURITY_MIN
        and slope_norm > GRIND_BREAKOUT_SLOPE_MIN
        and vel_5m > vel_15m * GRIND_BREAKOUT_ACCEL_MULT
        and vel_5m > GRIND_BREAKOUT_MIN_VELOCITY
        and current_price > range_high * (1 + GRIND_BREAKOUT_BREAKOUT_BUFFER)
        and current_rsi < GRIND_BREAKOUT_RSI_MAX
        and consec_green <= GRIND_BREAKOUT_MAX_CONSEC_GREEN):

        # Confidence scoring
        conf = GRIND_BREAKOUT_CONF_BASE
        if abs(slope_norm) > GRIND_BREAKOUT_SLOPE_MIN * 2:
            conf += GRIND_BREAKOUT_CONF_SLOPE_BONUS
        if abs(vel_5m) > abs(vel_15m) * 2:
            conf += GRIND_BREAKOUT_CONF_ACCEL_BONUS
        if current_price > range_high * (1 + GRIND_BREAKOUT_BREAKOUT_BONUS_BUFFER):
            conf += GRIND_BREAKOUT_CONF_BREAKOUT_BONUS
        if purity_long > GRIND_BREAKOUT_PURITY_BONUS_MIN:
            conf += GRIND_BREAKOUT_CONF_PURITY_BONUS
        conf = max(GRIND_BREAKOUT_CONF_FLOOR, min(GRIND_BREAKOUT_CONF_CAP, conf))

        return {
            'direction': 'LONG',
            'confidence': conf,
            'value': slope_norm,
            'price': current_price,
        }

    # ── SHORT signal ──
    if (purity_short >= GRIND_BREAKOUT_PURITY_MIN
        and slope_norm < -GRIND_BREAKOUT_SLOPE_MIN
        and vel_5m < vel_15m * GRIND_BREAKOUT_ACCEL_MULT
        and vel_5m < -GRIND_BREAKOUT_MIN_VELOCITY
        and current_price < range_low * (1 - GRIND_BREAKOUT_BREAKOUT_BUFFER)
        and current_rsi > GRIND_BREAKOUT_RSI_MIN
        and consec_red <= GRIND_BREAKOUT_MAX_CONSEC_RED):

        conf = GRIND_BREAKOUT_CONF_BASE
        if abs(slope_norm) > GRIND_BREAKOUT_SLOPE_MIN * 2:
            conf += GRIND_BREAKOUT_CONF_SLOPE_BONUS
        if abs(vel_5m) > abs(vel_15m) * 2:
            conf += GRIND_BREAKOUT_CONF_ACCEL_BONUS
        if current_price < range_low * (1 - GRIND_BREAKOUT_BREAKOUT_BONUS_BUFFER):
            conf += GRIND_BREAKOUT_CONF_BREAKOUT_BONUS
        if purity_short > GRIND_BREAKOUT_PURITY_BONUS_MIN:
            conf += GRIND_BREAKOUT_CONF_PURITY_BONUS
        conf = max(GRIND_BREAKOUT_CONF_FLOOR, min(GRIND_BREAKOUT_CONF_CAP, conf))

        return {
            'direction': 'SHORT',
            'confidence': conf,
            'value': slope_norm,
            'price': current_price,
        }

    return None


def scan_signals():
    """Scan all tokens for grind_breakout signals."""
    added = 0

    # Get all tokens with recent price data
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        cutoff = int(time.time()) - GRIND_BREAKOUT_FRESHNESS_SECS
        c.execute("""
            SELECT DISTINCT token FROM price_history
            WHERE timestamp > ?
        """, (cutoff,))
        tokens = [r[0] for r in c.fetchall()]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

    for token in tokens:
        # Layer 1: freshness check
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not GRIND_BREAKOUT_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not GRIND_BREAKOUT_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=GRIND_BREAKOUT_COOLDOWN_HOURS)
            _log(f'  {token} {direction} conf={sig["confidence"]:.0f} price=${sig["price"]:.6f}')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry', action='store_true', help='Dry run')
    parser.add_argument('--token', type=str, help='Test single token')
    args = parser.parse_args()

    if args.token:
        sig = detect(args.token)
        if sig:
            _log(f'{args.token}: {sig}')
        else:
            _log(f'{args.token}: no signal')
    else:
        added = scan_signals()
        _log(f'Scan complete: {added} signals added')
