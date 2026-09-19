#!/usr/bin/env python3
"""grind_trend.py — Low-volatility accumulation grind signal.

THESIS:
  When price shows a consistent positive slope with low volatility and
  steady volume, smart money is quietly accumulating. The grind IS the
  signal — no breakout required. This catches "slow drift up" patterns
  that other signals miss because they require breakouts or clean EMA trends.

  Example: RESOLV +4.52% over 20 hours with 0.1-1% hourly gains,
  oscillating around EMA but consistently drifting up.

ENTRY CONDITIONS (LONG):
  1. Linear regression slope > threshold over last N bars (positive trend)
  2. Price > SMA of lookback period (trend direction)
  3. ATR% < max_threshold (low volatility = grind, not spike)
  4. RSI in neutral zone 35-65 (not overbought/oversold)
  5. Price making higher lows (structure check)

ENTRY CONDITIONS (SHORT):
  Inverted: negative slope, price < SMA, low volatility, RSI neutral

DATA SOURCE:
  - candles_1m from candles.db — always fresh
  - All indicators computed on the fly

Source strings: grind-trend+ (LONG), grind-trend- (SHORT)
"""

import sys, os, sqlite3, time, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    GRIND_TREND_ENABLED,
    GRIND_TREND_PLUS_ENABLED,
    GRIND_TREND_MINUS_ENABLED,
    GRIND_TREND_COOLDOWN_HOURS,
    GRIND_TREND_SLOPE_MIN,
    GRIND_TREND_ATR_MAX_PCT,
    GRIND_TREND_RSI_MIN,
    GRIND_TREND_RSI_MAX,
    GRIND_TREND_LOOKBACK,
    GRIND_TREND_SMA_PERIOD,
    GRIND_TREND_HL_LOOKBACK,
    GRIND_TREND_CONF_BASE,
    GRIND_TREND_CONF_FLOOR,
    GRIND_TREND_CONF_CAP,
    GRIND_TREND_CONF_SLOPE_BONUS,
    GRIND_TREND_CONF_ATR_BONUS,
    GRIND_TREND_CONF_HL_BONUS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'grind_trend_long'
SIGNAL_TYPE_SHORT = 'grind_trend_short'
SOURCE_LONG = 'grind-trend+'
SOURCE_SHORT = 'grind-trend-'


def _get_closes(token, table='candles_1m', limit=200):
    """Fetch closes from candles.db. Returns oldest-first list."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT close FROM {table}
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
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


def _get_ohlcv(token, table='candles_1m', limit=200):
    """Fetch OHLCV from candles.db. Returns oldest-first list of (open, high, low, close, volume)."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT open, high, low, close, volume FROM {table}
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return list(reversed(rows))
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _sma(data, period):
    """Simple moving average of last `period` values."""
    if len(data) < period:
        return None
    return sum(data[-period:]) / period


def _ema(data, period):
    """Exponential moving average."""
    if len(data) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = data[0]
    for p in data[1:]:
        ema = (p - ema) * multiplier + ema
    return ema


def _rsi(closes, period=14):
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr_pct(ohlcv, period=14):
    """ATR as percentage of price."""
    if len(ohlcv) < period + 1:
        return None
    true_ranges = []
    for i in range(1, len(ohlcv)):
        h, l, prev_c = ohlcv[i][1], ohlcv[i][2], ohlcv[i-1][3]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        true_ranges.append(tr)
    if len(true_ranges) < period:
        return None
    atr = sum(true_ranges[-period:]) / period
    current_price = ohlcv[-1][3]
    if current_price <= 0:
        return None
    return atr / current_price * 100


def _linear_regression_slope(data):
    """Linear regression slope of data points. Returns slope per bar."""
    n = len(data)
    if n < 3:
        return 0
    x_mean = (n - 1) / 2
    y_mean = sum(data) / n
    num = 0
    den = 0
    for i, y in enumerate(data):
        num += (i - x_mean) * (y - y_mean)
        den += (i - x_mean) ** 2
    if den == 0:
        return 0
    slope = num / den
    # Normalize by average price for percentage comparison
    if y_mean > 0:
        slope_pct = slope / y_mean * 100
    else:
        slope_pct = 0
    return slope_pct


def _higher_lows(closes, lookback=20):
    """Check if recent lows are trending up. Returns fraction of ascending lows."""
    if len(closes) < lookback:
        return 0
    recent = closes[-lookback:]
    # Compare each close to the previous one — count ascending steps
    ascending = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
    return ascending / (len(recent) - 1)


def detect(token):
    """
    Detect grind_trend pattern for a token.
    Returns {direction, confidence, value, price} or None.
    """
    ohlcv = _get_ohlcv(token, 'candles_1m', 200)
    if len(ohlcv) < 60:
        return None

    closes = [c[3] for c in ohlcv]
    price = closes[-1]

    # Compute indicators
    lookback = GRIND_TREND_LOOKBACK
    recent_closes = closes[-lookback:]

    slope = _linear_regression_slope(recent_closes)
    sma = _sma(closes, GRIND_TREND_SMA_PERIOD)
    rsi = _rsi(closes, 14)
    atr = _atr_pct(ohlcv, 14)
    hl_ratio = _higher_lows(closes, GRIND_TREND_HL_LOOKBACK)

    if sma is None or rsi is None or atr is None:
        return None

    # Check if SMA is rising (better for grinds that oscillate around SMA)
    sma_prev = _sma(closes[:-10], GRIND_TREND_SMA_PERIOD) if len(closes) > GRIND_TREND_SMA_PERIOD + 10 else None
    sma_rising = sma_prev is not None and sma > sma_prev

    # ── LONG detection ──
    if slope > GRIND_TREND_SLOPE_MIN and sma_rising:
        if atr < GRIND_TREND_ATR_MAX_PCT and GRIND_TREND_RSI_MIN <= rsi <= GRIND_TREND_RSI_MAX:
            # Calculate confidence
            conf = GRIND_TREND_CONF_BASE
            # Slope bonus: stronger trend = higher confidence
            if slope > GRIND_TREND_SLOPE_MIN * 2:
                conf += GRIND_TREND_CONF_SLOPE_BONUS
            # ATR bonus: lower volatility = higher confidence (grind quality)
            if atr < GRIND_TREND_ATR_MAX_PCT * 0.5:
                conf += GRIND_TREND_CONF_ATR_BONUS
            # Higher-lows bonus
            if hl_ratio > 0.6:
                conf += GRIND_TREND_CONF_HL_BONUS
            conf = min(conf, GRIND_TREND_CONF_CAP)
            conf = max(conf, GRIND_TREND_CONF_FLOOR)
            return {
                'direction': 'LONG',
                'confidence': conf,
                'value': slope,
                'price': price,
            }

    # ── SHORT detection ──
    if slope < -GRIND_TREND_SLOPE_MIN and not sma_rising:
        if atr < GRIND_TREND_ATR_MAX_PCT and GRIND_TREND_RSI_MIN <= rsi <= GRIND_TREND_RSI_MAX:
            conf = GRIND_TREND_CONF_BASE
            if abs(slope) > GRIND_TREND_SLOPE_MIN * 2:
                conf += GRIND_TREND_CONF_SLOPE_BONUS
            if atr < GRIND_TREND_ATR_MAX_PCT * 0.5:
                conf += GRIND_TREND_CONF_ATR_BONUS
            # For SHORT: lower-lows bonus
            lower_lows = 1 - hl_ratio
            if lower_lows > 0.6:
                conf += GRIND_TREND_CONF_HL_BONUS
            conf = min(conf, GRIND_TREND_CONF_CAP)
            conf = max(conf, GRIND_TREND_CONF_FLOOR)
            return {
                'direction': 'SHORT',
                'confidence': conf,
                'value': slope,
                'price': price,
            }

    return None


def scan_signals():
    """Scan all tokens for grind_trend pattern."""
    added = 0

    # Get all tokens with recent price data
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        rows = conn.execute("""
            SELECT DISTINCT token FROM candles_1m
            WHERE ts > strftime('%s', 'now') - 3600
        """).fetchall()
        tokens = [r[0] for r in rows]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

    for token in tokens:
        # Price age check
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: kill-switch
        if direction == 'LONG' and not GRIND_TREND_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not GRIND_TREND_MINUS_ENABLED:
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
            set_cooldown(token, direction, hours=GRIND_TREND_COOLDOWN_HOURS)

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='grind_trend signal')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    parser.add_argument('--token', type=str, help='Test specific token')
    args = parser.parse_args()

    if args.token:
        result = detect(args.token)
        if result:
            print(f"[{args.token}] {result['direction']} conf={result['confidence']} "
                  f"slope={result['value']:.6f} price={result['price']:.6f}")
        else:
            print(f"[{args.token}] No signal")
    elif args.dry:
        print("Dry run: scanning all tokens...")
        count = scan_signals()
        print(f"Would add {count} signals")
    else:
        added = run()
        print(f"Added {added} grind_trend signals")
