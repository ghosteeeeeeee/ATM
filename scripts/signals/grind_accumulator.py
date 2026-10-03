#!/usr/bin/env python3
"""
grind_accumulator.py — Enter during accumulation grind, ride the spike as profit.

Detects the "coil" phase before a pump:
  1. Compression: ATR is low, price range is tight
  2. Proximity: Price is near MA180 (not extended)
  3. Drift: Slight upward slope (higher lows, positive linreg)
  4. Volume: Contracting (accumulation, not distribution)

The signal fires BEFORE the spike, not after. The spike becomes exit.

This solves the "buying tops" problem:
  - pump-chain fires ON the spike → we buy the top
  - grind_accumulator fires BEFORE the spike → we buy the bottom

Source: grind-accum+ (LONG), grind-accum- (SHORT)
Signal type: grind_accumulator_long / grind_accumulator_short
"""

import sys
import os
import sqlite3
import time
import numpy as np
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    GRIND_ACCUM_ENABLED,
    GRIND_ACCUM_PLUS_ENABLED,
    GRIND_ACCUM_MINUS_ENABLED,
    GRIND_ACCUM_COOLDOWN_HOURS,
    GRIND_ACCUM_LOOKBACK,
    GRIND_ACCUM_MA_PERIOD,
    GRIND_ACCUM_ATR_PERIOD,
    GRIND_ACCUM_ATR_PCT_MAX,
    GRIND_ACCUM_RANGE_PCT_MAX,
    GRIND_ACCUM_SLOPE_MIN,
    GRIND_ACCUM_SLOPE_MAX,
    GRIND_ACCUM_VOL_RATIO_MAX,
    GRIND_ACCUM_VOL_WINDOW,
    GRIND_ACCUM_VOL_AVG_WINDOW,
    GRIND_ACCUM_PROXIMITY_PCT,
    GRIND_ACCUM_CONF_BASE,
    GRIND_ACCUM_CONF_FLOOR,
    GRIND_ACCUM_CONF_CAP,
    GRIND_ACCUM_PRICE_AGE_MAX,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

# ── Signal identity ───────────────────────────────────────────────────────
SIGNAL_TYPE_LONG = 'grind_accumulator_long'
SIGNAL_TYPE_SHORT = 'grind_accumulator_short'
SOURCE_LONG = 'grind-accum+'
SOURCE_SHORT = 'grind-accum-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(_SIGNAL_LOG), exist_ok=True)


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except OSError:
        pass


def _get_1m_candles(token: str, lookback: int) -> list:
    """Fetch 1m candles from candles.db. Returns list of dicts (oldest first)."""
    conn = None
    try:
        conn = sqlite3.connect(f'file:{_CANDLES_DB}?mode=ro', uri=True, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume FROM (
                SELECT ts, open, high, low, close, volume
                FROM candles_1m
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        if not rows:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception as e:
        _log(f"  [grind_accum] candles error {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _compute_atr(candles: list, period: int) -> list:
    """Return ATR(period) series (oldest first), None for indices < period-1."""
    if len(candles) < period:
        return [None] * len(candles)
    trs = []
    for i, c in enumerate(candles):
        h, l = c['high'], c['low']
        if i == 0:
            tr = h - l
        else:
            prev_c = candles[i - 1]['close']
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    atrs = []
    for i in range(len(trs)):
        if i < period - 1:
            atrs.append(None)
        else:
            atrs.append(sum(trs[i - period + 1:i + 1]) / period)
    return atrs


def _compute_ma(values: list, period: int) -> list:
    """Simple moving average, None for indices < period-1."""
    if len(values) < period:
        return [None] * len(values)
    ma = []
    for i in range(len(values)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(values[i - period + 1:i + 1]) / period)
    return ma


def _compute_linreg_slope(values: list) -> Optional[float]:
    """Linear regression slope, normalized as % per bar."""
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(valid) < 10:
        return None
    indices = np.array([v[0] for v in valid], dtype=float)
    vals = np.array([v[1] for v in valid], dtype=float)
    try:
        m, b = np.polyfit(indices, vals, 1)
        mean_val = np.mean(vals)
        if mean_val == 0:
            return None
        return m / mean_val * 100  # % per bar
    except Exception:
        return None


def detect_grind_accumulator(token: str, candles: list) -> Optional[dict]:
    """
    Detect accumulation grind pattern.
    
    Returns dict with signal details or None.
    
    Phase requirements:
      1. COMPRESSION: ATR% < threshold, range < threshold
      2. PROXIMITY: Price near MA180 (not extended)
      3. DRIFT: Positive linreg slope (but not too steep)
      4. VOLUME: Contracting (below average)
    """
    if len(candles) < GRIND_ACCUM_LOOKBACK:
        return None
    
    current = candles[-1]
    current_price = current['close']
    if current_price <= 0:
        return None
    
    # ── Phase 1: Compression (ATR + Range) ──
    atrs = _compute_atr(candles, GRIND_ACCUM_ATR_PERIOD)
    valid_atrs = [a for a in atrs if a is not None]
    if not valid_atrs:
        return None
    
    # Use recent ATR (last 20 bars) vs longer-term ATR
    recent_atr = sum(valid_atrs[-20:]) / min(20, len(valid_atrs[-20:]))
    atr_pct = (recent_atr / current_price) * 100
    
    if atr_pct > GRIND_ACCUM_ATR_PCT_MAX:
        return None  # Not compressed enough
    
    # Range check: tight range over lookback
    range_high = max(c['high'] for c in candles[-GRIND_ACCUM_LOOKBACK:])
    range_low = min(c['low'] for c in candles[-GRIND_ACCUM_LOOKBACK:])
    range_pct = ((range_high - range_low) / current_price) * 100
    
    if range_pct > GRIND_ACCUM_RANGE_PCT_MAX:
        return None  # Range too wide
    
    # ── Phase 2: Proximity to MA180 ──
    ma_values = [c['close'] for c in candles]
    ma180 = _compute_ma(ma_values, GRIND_ACCUM_MA_PERIOD)
    ma180_val = ma180[-1] if ma180[-1] is not None else None
    
    if ma180_val is None or ma180_val <= 0:
        return None
    
    proximity_pct = abs((current_price - ma180_val) / ma180_val) * 100
    
    if proximity_pct > GRIND_ACCUM_PROXIMITY_PCT:
        return None  # Price too far from MA180
    
    # ── Phase 3: Drift (positive slope, not too steep) ──
    # Use recent closes for slope
    recent_closes = [c['close'] for c in candles[-GRIND_ACCUM_LOOKBACK:]]
    slope = _compute_linreg_slope(recent_closes)
    
    if slope is None:
        return None
    
    if slope < GRIND_ACCUM_SLOPE_MIN:
        return None  # Not drifting up
    
    if slope > GRIND_ACCUM_SLOPE_MAX:
        return None  # Too steep — already pumped
    
    # ── Phase 4: Volume contraction ──
    volumes = [c['volume'] for c in candles]
    recent_vol = sum(volumes[-GRIND_ACCUM_VOL_WINDOW:]) / GRIND_ACCUM_VOL_WINDOW
    avg_vol = sum(volumes[-GRIND_ACCUM_VOL_AVG_WINDOW:]) / GRIND_ACCUM_VOL_AVG_WINDOW
    
    if avg_vol <= 0:
        return None
    
    vol_ratio = recent_vol / avg_vol
    
    if vol_ratio > GRIND_ACCUM_VOL_RATIO_MAX:
        return None  # Volume not contracting — already distributing
    
    # ── Higher lows check ──
    # Check that recent lows are trending up
    lows = [c['low'] for c in candles[-20:]]
    if len(lows) >= 10:
        first_half_low = min(lows[:10])
        second_half_low = min(lows[10:])
        if second_half_low < first_half_low:
            return None  # Lower lows — not accumulating
    
    # ── Calculate confidence ──
    confidence = GRIND_ACCUM_CONF_BASE
    
    # Better compression = higher confidence
    if atr_pct < GRIND_ACCUM_ATR_PCT_MAX * 0.5:
        confidence += 8
    elif atr_pct < GRIND_ACCUM_ATR_PCT_MAX * 0.75:
        confidence += 5
    
    # Better proximity = higher confidence
    if proximity_pct < GRIND_ACCUM_PROXIMITY_PCT * 0.3:
        confidence += 5
    elif proximity_pct < GRIND_ACCUM_PROXIMITY_PCT * 0.6:
        confidence += 3
    
    # Volume contraction bonus
    if vol_ratio < 0.5:
        confidence += 5
    elif vol_ratio < 0.7:
        confidence += 3
    
    # Slope sweet spot bonus
    if 0.002 <= slope <= 0.01:
        confidence += 5
    
    # Higher lows bonus
    if second_half_low > first_half_low:
        confidence += 3
    
    confidence = max(GRIND_ACCUM_CONF_FLOOR, min(GRIND_ACCUM_CONF_CAP, confidence))
    
    return {
        'direction': 'LONG',
        'price': current_price,
        'confidence': confidence,
        'atr_pct': round(atr_pct, 4),
        'range_pct': round(range_pct, 4),
        'proximity_pct': round(proximity_pct, 4),
        'slope': round(slope, 6),
        'vol_ratio': round(vol_ratio, 3),
        'ma180': round(ma180_val, 8),
    }


def scan_grind_accumulator_signals() -> int:
    """Scan all tokens for grind accumulator signals."""
    from signal_schema import get_all_latest_prices
    from position_manager import get_open_positions
    
    prices_dict = get_all_latest_prices()
    open_pos = {p['token']: p['direction'] for p in get_open_positions()}
    added = 0
    
    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        
        price = data.get('price')
        if not price or price <= 0:
            continue
        
        # Guard: open position
        if token in open_pos:
            continue
        
        # Guard: price staleness
        if price_age_minutes(token) > GRIND_ACCUM_PRICE_AGE_MAX:
            continue
        
        # Fetch candles
        candles = _get_1m_candles(token, GRIND_ACCUM_LOOKBACK)
        if not candles:
            continue
        
        # Detect
        sig = detect_grind_accumulator(token, candles)
        if sig is None:
            continue
        
        direction = sig['direction']
        
        # Guard: kill-switch
        if direction == 'LONG' and not GRIND_ACCUM_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not GRIND_ACCUM_MINUS_ENABLED:
            continue
        
        # Guard: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue
        
        # Guard: cooldown
        if get_cooldown(token, direction=direction):
            continue
        
        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
        
        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=sig['confidence'],
                value=sig['vol_ratio'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=GRIND_ACCUM_COOLDOWN_HOURS)
                _log(f"  {direction}-grind-accum {token:8s} conf={sig['confidence']}% "
                     f"atr%={sig['atr_pct']} range%={sig['range_pct']} "
                     f"prox%={sig['proximity_pct']} slope={sig['slope']} "
                     f"vol={sig['vol_ratio']}x price={sig['price']:.8g} "
                     f"[{source}]")
        except Exception as e:
            _log(f"  [grind_accum] add_signal error {token}: {e}")
    
    return added


def run() -> int:
    """Entry point for signals_runner."""
    if not GRIND_ACCUM_ENABLED:
        return 0
    return scan_grind_accumulator_signals()


if __name__ == '__main__':
    # Test mode — check current BTC state
    if not GRIND_ACCUM_ENABLED:
        print("GRIND_ACCUM_ENABLED=False")
        sys.exit(0)
    
    # Test on a few tokens
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    
    print(f"Grind Accumulator — testing {len(prices)} tokens...")
    total = scan_grind_accumulator_signals()
    print(f"\nTotal signals emitted: {total}")
