#!/usr/bin/env python3
"""squeeze_reversal — BB squeeze → mean-reversion breakout signal.

THESIS:
  After a sharp sell-off, price consolidates in a tight range (BB squeeze).
  When price is near the lower BB during the squeeze, it's primed for a
  mean-reversion bounce. The squeeze ensures that when the move comes,
  it's explosive (BB expansion = energy release).

ENTRY CONDITIONS (LONG):
  1. Recent sell-off: Price dropped >=2% in last 2 hours
  2. BB squeeze: BB Width < 0.8% for at least 1 hour
  3. Price near lower BB: Current price within 0.5% of BB Lower
  4. RSI not oversold: RSI > 35
  5. RSI not overbought: RSI < 65
  6. Price above EMA20: Confirms bounce started
  7. Velocity turning positive: vel_5m > 0

ENTRY CONDITIONS (SHORT — mirror):
  1. Recent rally: Price rose >=2% in last 2 hours
  2. BB squeeze: BB Width < 0.8% for at least 1 hour
  3. Price near upper BB: Current price within 0.5% of BB Upper
  4. RSI not overbought: RSI < 65
  5. RSI not oversold: RSI > 35
  6. Price below EMA20: Confirms rejection
  7. Velocity turning negative: vel_5m < 0

DATA SOURCE:
  - price_history (1m) from signals_hermes.db
"""

import sys, os, sqlite3, time, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    SQUEEZE_REVERSAL_ENABLED,
    SQUEEZE_REVERSAL_PLUS_ENABLED,
    SQUEEZE_REVERSAL_MINUS_ENABLED,
    SQUEEZE_REVERSAL_COOLDOWN_HOURS,
    SQUEEZE_REVERSAL_SELLOFF_PCT,
    SQUEEZE_REVERSAL_SELLOFF_WINDOW,
    SQUEEZE_REVERSAL_BB_PERIOD,
    SQUEEZE_REVERSAL_BB_MULT,
    SQUEEZE_REVERSAL_SQUEEZE_THRESH,
    SQUEEZE_REVERSAL_SQUEEZE_MIN_BARS,
    SQUEEZE_REVERSAL_PROXIMITY_PCT,
    SQUEEZE_REVERSAL_RSI_MIN,
    SQUEEZE_REVERSAL_RSI_MAX,
    SQUEEZE_REVERSAL_CONF_BASE,
    SQUEEZE_REVERSAL_CONF_FLOOR,
    SQUEEZE_REVERSAL_CONF_CAP,
    SQUEEZE_REVERSAL_CONF_SQUEEZE_BONUS,
    SQUEEZE_REVERSAL_CONF_SELLOFF_BONUS,
    SQUEEZE_REVERSAL_CONF_PROXIMITY_BONUS,
    SQUEEZE_REVERSAL_LOOKBACK_1M,
    SQUEEZE_REVERSAL_RSI_PERIOD,
    SQUEEZE_REVERSAL_MIN_BARS,
    SQUEEZE_REVERSAL_FRESHNESS_SECS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'squeeze_reversal_long'
SIGNAL_TYPE_SHORT = 'squeeze_reversal_short'
SOURCE_LONG = 'squeeze-reversal+'
SOURCE_SHORT = 'squeeze-reversal-'

_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')


def _log(msg):
    print(f'[squeeze-reversal] {msg}', flush=True)


def _get_prices(token, limit):
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


def _bb(prices, period, mult):
    """Compute Bollinger Bands. Returns (upper, middle, lower, width_pct) series."""
    n = len(prices)
    upper = [None] * n
    middle = [None] * n
    lower = [None] * n
    width_pct = [None] * n
    for i in range(period - 1, n):
        window = prices[i - period + 1:i + 1]
        sma = sum(window) / period
        variance = sum((x - sma) ** 2 for x in window) / period
        std = math.sqrt(variance)
        middle[i] = sma
        upper[i] = sma + mult * std
        lower[i] = sma - mult * std
        if sma > 0:
            width_pct[i] = (upper[i] - lower[i]) / sma * 100
    return upper, middle, lower, width_pct


def detect(token):
    """Detect squeeze_reversal signal for a token.

    Returns {direction, confidence, value, price} or None.
    """
    lookback = SQUEEZE_REVERSAL_LOOKBACK_1M
    prices = _get_prices(token, lookback)
    if len(prices) < SQUEEZE_REVERSAL_MIN_BARS:
        return None

    n = len(prices)
    current_price = prices[-1]

    # Compute indicators
    ema_series = _ema(prices, SQUEEZE_REVERSAL_BB_PERIOD)
    rsi_series = _rsi(prices, SQUEEZE_REVERSAL_RSI_PERIOD)
    bb_upper, bb_mid, bb_lower, bb_width = _bb(
        prices, SQUEEZE_REVERSAL_BB_PERIOD, SQUEEZE_REVERSAL_BB_MULT
    )

    current_ema = ema_series[-1]
    current_rsi = rsi_series[-1]
    current_bb_upper = bb_upper[-1]
    current_bb_lower = bb_lower[-1]
    current_bb_width = bb_width[-1]

    if current_ema is None or current_rsi is None or current_bb_width is None:
        return None

    # Sell-off / rally detection
    SW = SQUEEZE_REVERSAL_SELLOFF_WINDOW
    if n >= SW:
        price_2h_ago = prices[-SW]
        change_pct = (current_price - price_2h_ago) / price_2h_ago * 100
    else:
        change_pct = 0

    # BB squeeze: count consecutive bars with BB Width < threshold
    squeeze_bars = 0
    for i in range(n - 1, max(n - SQUEEZE_REVERSAL_SQUEEZE_MIN_BARS - 60, 0), -1):
        if bb_width[i] is not None and bb_width[i] < SQUEEZE_REVERSAL_SQUEEZE_THRESH:
            squeeze_bars += 1
        else:
            break

    # Proximity to BB band
    if current_bb_upper != current_bb_lower:
        proximity_lower = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower) * 100
        proximity_upper = (current_bb_upper - current_price) / (current_bb_upper - current_bb_lower) * 100
    else:
        proximity_lower = 50
        proximity_upper = 50

    # Velocity (5m proxy)
    vel_bars = 6
    if n >= vel_bars:
        vel_5m = (current_price - prices[-vel_bars]) / prices[-vel_bars] * 100
    else:
        vel_5m = 0

    # ── LONG signal ──
    # 1. Recent sell-off (price dropped >=2%)
    # 2. BB squeeze (width < threshold for min bars)
    # 3. Price near lower BB (proximity < threshold)
    # 4. RSI > min (not oversold)
    # 5. RSI < max (not overbought)
    # 6. Price above EMA20 (bounce confirmed)
    # 7. Velocity positive (momentum shifting)
    if (change_pct <= -SQUEEZE_REVERSAL_SELLOFF_PCT
        and squeeze_bars >= SQUEEZE_REVERSAL_SQUEEZE_MIN_BARS
        and proximity_lower < SQUEEZE_REVERSAL_PROXIMITY_PCT
        and current_rsi > SQUEEZE_REVERSAL_RSI_MIN
        and current_rsi < SQUEEZE_REVERSAL_RSI_MAX
        and current_price > current_ema
        and vel_5m > 0):

        conf = SQUEEZE_REVERSAL_CONF_BASE
        if squeeze_bars > SQUEEZE_REVERSAL_SQUEEZE_MIN_BARS * 2:
            conf += SQUEEZE_REVERSAL_CONF_SQUEEZE_BONUS
        if change_pct < -SQUEEZE_REVERSAL_SELLOFF_PCT * 1.5:
            conf += SQUEEZE_REVERSAL_CONF_SELLOFF_BONUS
        if proximity_lower < SQUEEZE_REVERSAL_PROXIMITY_PCT * 0.4:
            conf += SQUEEZE_REVERSAL_CONF_PROXIMITY_BONUS
        conf = max(SQUEEZE_REVERSAL_CONF_FLOOR, min(SQUEEZE_REVERSAL_CONF_CAP, conf))

        return {
            'direction': 'LONG',
            'confidence': conf,
            'value': change_pct,
            'price': current_price,
        }

    # ── SHORT signal ──
    # Mirror: rally, squeeze, near upper BB, negative velocity
    if (change_pct >= SQUEEZE_REVERSAL_SELLOFF_PCT
        and squeeze_bars >= SQUEEZE_REVERSAL_SQUEEZE_MIN_BARS
        and proximity_upper < SQUEEZE_REVERSAL_PROXIMITY_PCT
        and current_rsi < SQUEEZE_REVERSAL_RSI_MAX
        and current_rsi > SQUEEZE_REVERSAL_RSI_MIN
        and current_price < current_ema
        and vel_5m < 0):

        conf = SQUEEZE_REVERSAL_CONF_BASE
        if squeeze_bars > SQUEEZE_REVERSAL_SQUEEZE_MIN_BARS * 2:
            conf += SQUEEZE_REVERSAL_CONF_SQUEEZE_BONUS
        if change_pct > SQUEEZE_REVERSAL_SELLOFF_PCT * 1.5:
            conf += SQUEEZE_REVERSAL_CONF_SELLOFF_BONUS
        if proximity_upper < SQUEEZE_REVERSAL_PROXIMITY_PCT * 0.4:
            conf += SQUEEZE_REVERSAL_CONF_PROXIMITY_BONUS
        conf = max(SQUEEZE_REVERSAL_CONF_FLOOR, min(SQUEEZE_REVERSAL_CONF_CAP, conf))

        return {
            'direction': 'SHORT',
            'confidence': conf,
            'value': change_pct,
            'price': current_price,
        }

    return None


def scan_signals():
    added = 0
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        cutoff = int(time.time()) - SQUEEZE_REVERSAL_FRESHNESS_SECS
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
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']
        if direction == 'LONG' and not SQUEEZE_REVERSAL_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not SQUEEZE_REVERSAL_MINUS_ENABLED:
            continue
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue
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
            set_cooldown(token, direction, hours=SQUEEZE_REVERSAL_COOLDOWN_HOURS)
            _log(f'  {token} {direction} conf={sig["confidence"]:.0f} price=${sig["price"]:.6f}')

    return added


def run():
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
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
