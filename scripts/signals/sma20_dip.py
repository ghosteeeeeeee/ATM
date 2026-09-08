#!/usr/bin/env python3
"""
sma20_dip — Buy pullback to SMA20 in established uptrends.

Thesis: In established uptrends (price > SMA50), price pulls back to SMA20
and bounces. SMA20 acts as dynamic support. Enter at the dip, ride the
continuation.

Pattern:
  1. Uptrend: price > SMA50, SMA20 > SMA50
  2. Pullback: price within 1% of SMA20
  3. Momentum: RSI 55-75 (bullish, not extreme)
  4. Trend strength: BB position > 0.50 (above middle band)
  5. Volume: avg vol > 50 (real market)

Reference: INJ LONG 2026-09-07 +40.57% (5x), entry at SMA20

Data: candles_1m from candles.db
"""
import sys, os, sqlite3, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    SMA20_DIP_ENABLED,
    SMA20_DIP_PLUS_ENABLED,
    SMA20_DIP_MINUS_ENABLED,
    SMA20_DIP_SMA_FAST,
    SMA20_DIP_SMA_SLOW,
    SMA20_DIP_MAX_SMA20_DIST,
    SMA20_DIP_RSI_MIN,
    SMA20_DIP_RSI_MAX,
    SMA20_DIP_BB_MIN_POSITION,
    SMA20_DIP_MIN_AVG_VOL,
    SMA20_DIP_COOLDOWN_HOURS,
    SMA20_DIP_CONF_BASE,
    SMA20_DIP_CONF_CAP,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'sma20_dip_long'
SOURCE_LONG = 'sma20-dip+'


def _log(msg):
    print(f"[sma20-dip] {msg}", flush=True)


def _get_candles(token, table='candles_1m', limit=100):
    """Fetch candles from DB. Returns list of (ts, open, high, low, close, volume) oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume
            FROM {table}
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

    if not rows:
        return []
    return list(reversed(rows))


def _sma(data, period):
    """Simple Moving Average. Returns float or None."""
    if len(data) < period:
        return None
    return sum(data[-period:]) / period


def _rsi(data, period=14):
    """RSI. Returns float or None."""
    if len(data) < period + 1:
        return None
    deltas = np.diff(data[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


def detect(token):
    """Detect sma20_dip LONG setup.

    Returns {direction, confidence, value, price} or None.
    """
    # Get candles
    candles = _get_candles(token, 'candles_1m', 100)
    if not candles or len(candles) < 60:
        return None

    # Current price
    price = candles[-1][4]
    if price <= 0:
        return None

    # Close prices
    closes = [c[4] for c in candles]

    # ── Condition 1: Price above SMA50 (uptrend) ──
    sma50 = _sma(closes, SMA20_DIP_SMA_SLOW)
    if sma50 is None:
        return None
    if price <= sma50:
        return None  # not in uptrend

    # ── Condition 2: Price within 1% of SMA20 (pullback to buy zone) ──
    sma20 = _sma(closes, SMA20_DIP_SMA_FAST)
    if sma20 is None:
        return None
    sma20_dist = abs(price - sma20) / sma20 * 100
    if sma20_dist > SMA20_DIP_MAX_SMA20_DIST:
        return None  # too far from SMA20

    # ── Condition 3: SMA20 > SMA50 (trend intact) ──
    if sma20 <= sma50:
        return None  # trend broken

    # ── Condition 4: RSI bullish (55-75) ──
    rsi_val = _rsi(closes)
    if rsi_val is None:
        return None
    if rsi_val < SMA20_DIP_RSI_MIN or rsi_val > SMA20_DIP_RSI_MAX:
        return None  # not in bullish range

    # ── Condition 5: BB position > 0.50 (strong trend) ──
    arr = closes[-20:] if len(closes) >= 20 else closes
    middle = np.mean(arr)
    std = np.std(arr)
    bb_upper = middle + 2 * std
    bb_lower = middle - 2 * std
    bb_pos = (closes[-1] - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
    if bb_pos < SMA20_DIP_BB_MIN_POSITION:
        return None  # weak trend

    # ── Condition 6: Volume active ──
    volumes = [c[5] for c in candles]
    avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else None
    if avg_vol is None or avg_vol < SMA20_DIP_MIN_AVG_VOL:
        return None  # no volume data or dead market

    # ── All conditions met — compute confidence ──
    conf = SMA20_DIP_CONF_BASE

    # Bonus: tight SMA20 proximity (closer = better entry)
    if sma20_dist < 0.3:
        conf += 5  # very close to SMA20
    elif sma20_dist < 0.5:
        conf += 3  # close to SMA20

    # Bonus: RSI sweet spot (65-75 = strong but not extreme)
    if 65 <= rsi_val <= 75:
        conf += 3

    # Bonus: strong trend (BB > 0.80)
    if bb_pos > 0.80:
        conf += 3

    # Bonus: volume confirmation (>1x avg)
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
    if vol_ratio > 1.0:
        conf += 2

    conf = min(conf, SMA20_DIP_CONF_CAP)

    # Notes
    notes = (
        f"SMA20 dip: price=\${price:.4f} SMA20=\${sma20:.4f} dist={sma20_dist:.2f}% "
        f"RSI={rsi_val:.1f} BB={bb_pos:.3f} vol={vol_ratio:.1f}x"
    )

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': sma20_dist,
        'price': price,
        'z_score': None,
        'notes': notes,
    }


def scan_signals():
    """Scan all tokens for sma20_dip LONG setups."""
    if not SMA20_DIP_ENABLED or not SMA20_DIP_PLUS_ENABLED:
        return 0

    added = 0

    # Get tokens with recent candle data
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token FROM candles_1m
            WHERE ts > strftime('%s', 'now') - 3600
        """)
        tokens = [r[0] for r in cur.fetchall()]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

    for token in tokens:
        # Guards
        if price_age_minutes(token) > 10:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(token, direction='LONG'):
            continue

        sig = detect(token)
        if not sig:
            continue

        # Layer 1: kill-switch (already checked above)
        # Layer 1: blacklists (already checked above)

        sid = add_signal(
            token=token.upper(),
            direction='LONG',
            signal_type=SIGNAL_TYPE_LONG,
            source=SOURCE_LONG,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=SMA20_DIP_COOLDOWN_HOURS)
            _log(f"{token.upper()} LONG conf={sig['confidence']} {sig['notes']}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='SMA20 Dip Signal')
    parser.add_argument('--query', help='Query a specific token')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()

    if args.query:
        sig = detect(args.query)
        if sig:
            print(f'{sig["direction"]} {args.query.upper()} conf={sig["confidence"]}')
            print(f'  {sig["notes"]}')
        else:
            print(f'No signal for {args.query.upper()}')
    else:
        count = scan_signals()
        print(f'\n[sma20-dip] Added {count} signals')
