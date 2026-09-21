#!/usr/bin/env python3
"""
btc_grind_spike.py — BTC Accumulation Grind + Volume Spike LONG Signal.

Catches the repeating pattern: BTC grinds up in low volatility (accumulation),
then a volume spike breaks it out. Entry at the FIRST spike, before the
bigger continuation move hours later.

Pattern phases (observed Sep 3, Sep 18 2026):
  1. ACCUMULATION — Low ATR, tight range, gradual upward drift (higher lows)
  2. SHAKEOUT — Brief dip to grab liquidity (optional, not required)
  3. FIRST SPIKE — Volume spikes 2-3x average, price breaks above range
  4. CONSOLIDATION — Price holds higher, volume dies down
  5. CONTINUATION — Second bigger spike (this is what we're front-running)

Data: 1m candles from candles.db (BTC only)
Signal type: btc_grind_spike_long
Source tag: grind-spike+@vol{X}
"""

import sys
import os
import sqlite3
import time
import numpy as np
from typing import Optional, Tuple, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

# ── Paths ─────────────────────────────────────────────────────────────────────
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(_SIGNAL_LOG), exist_ok=True)

# ── Signal constants ───────────────────────────────────────────────────────────
# Accumulation detection
ACCUM_LOOKBACK = 60          # candles to look back for accumulation (60 min)
ACCUM_ATR_PERIOD = 14        # ATR period
ACCUM_ATR_PCT_MAX = 0.15     # max ATR/close % to qualify as compressed
ACCUM_RANGE_PCT_MAX = 0.5    # max range (high-low)/close % over lookback
ACCUM_SLOPE_MIN = 0.001      # min upward slope (positive = grind up)

# Volume spike detection
VOL_SPIKE_MULT = 2.5         # current vol must be >= 2.5x average
VOL_AVG_PERIOD = 30          # bars for average volume (30 min)
VOL_SPIKE_CONFIRM_BARS = 2   # check vol spike sustained for N bars

# Price confirmation
PRICE_BREAK_PCT = 0.1        # close must break above range high by this %
MIN_BODY_PCT = 0.02          # min candle body as % of price (bullish candle)

# Signal settings
COOLDOWN_MINUTES = 20        # 20min cooldown between signals
LOOKBACK_1M = 100            # 1m candles to fetch (60 accum + 40 buffer)
SIGNAL_TYPE_LONG = 'btc_grind_spike_long'
SOURCE_TAG = 'grind-spike+'


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except OSError:
        pass


def _get_1m_candles(token: str, lookback: int = LOOKBACK_1M) -> list:
    """Fetch 1m candles (oldest first) with volume."""
    conn = None
    try:
        conn = sqlite3.connect(f'file:{_CANDLES_DB}?mode=ro', uri=True, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume FROM (
                SELECT ts, open, high, low, close, volume
                FROM candles_1m
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        if not rows:
            return []
        most_recent_ts = rows[-1][0]
        candle_age = time.time() - most_recent_ts
        if candle_age > 600:  # 10 min staleness limit for 1m candles
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception as e:
        _log(f"  [btc_grind_spike] candles error {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _compute_atr(candles: list, period: int = 14) -> list:
    """Return ATR(period) series aligned to candles (None for indices < period-1)."""
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


def _compute_linreg_slope(values: list) -> Optional[float]:
    """Linear regression slope of values, normalized as % per bar."""
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


def detect_btc_grind_spike(candles: list) -> Optional[dict]:
    """
    Detect BTC accumulation grind + volume spike pattern.
    
    Returns dict with signal details or None.
    """
    if len(candles) < LOOKBACK_1M:
        return None
    
    current = candles[-1]
    
    # ── Phase 1: Detect accumulation/compression ──
    # Look at the 60 candles BEFORE the current spike candle
    accum_candles = candles[-(ACCUM_LOOKBACK + 1):-1]
    if len(accum_candles) < ACCUM_LOOKBACK:
        return None
    
    # ATR check: low volatility = compressed
    atrs = _compute_atr(accum_candles, ACCUM_ATR_PERIOD)
    valid_atrs = [a for a in atrs if a is not None]
    if not valid_atrs:
        return None
    
    current_price = accum_candles[-1]['close']
    if current_price <= 0:
        return None
    
    avg_atr = sum(valid_atrs) / len(valid_atrs)
    atr_pct = (avg_atr / current_price) * 100
    
    if atr_pct > ACCUM_ATR_PCT_MAX:
        return None  # Not compressed enough
    
    # Range check: tight range over lookback
    range_high = max(c['high'] for c in accum_candles)
    range_low = min(c['low'] for c in accum_candles)
    range_pct = ((range_high - range_low) / current_price) * 100
    
    if range_pct > ACCUM_RANGE_PCT_MAX:
        return None  # Range too wide
    
    # Slope check: should be grinding UP (or at least not crashing)
    closes = [c['close'] for c in accum_candles]
    slope = _compute_linreg_slope(closes)
    if slope is None:
        return None
    
    if slope < ACCUM_SLOPE_MIN:
        return None  # Not grinding up
    
    # ── Phase 2: Detect volume spike on current candle ──
    volumes = [c['volume'] for c in candles]
    
    # Use a wider average window for volume comparison
    vol_avg_window = volumes[-(VOL_AVG_PERIOD + 1):-1]
    if not vol_avg_window:
        return None
    
    avg_vol = sum(vol_avg_window) / len(vol_avg_window)
    if avg_vol <= 0:
        return None
    
    current_vol = volumes[-1]
    vol_ratio = current_vol / avg_vol
    
    if vol_ratio < VOL_SPIKE_MULT:
        return None  # No volume spike
    
    # ── Phase 3: Price confirmation ──
    # Bullish candle: close > open
    if current['close'] <= current['open']:
        return None  # Not bullish
    
    # Body size check
    body_pct = ((current['close'] - current['open']) / current['close']) * 100
    if body_pct < MIN_BODY_PCT:
        return None  # Too small a body
    
    # Close should either:
    # (a) break above the accumulation range high, OR
    # (b) be significantly above the last accumulation close + have strong vol
    break_above_high = ((current['close'] - range_high) / range_high) * 100
    accum_last_close = accum_candles[-1]['close']
    break_above_close = ((current['close'] - accum_last_close) / accum_last_close) * 100 if accum_last_close > 0 else 0
    
    # Accept if: breaks above range high, OR (above accum close + strong vol spike >3x)
    if break_above_high < PRICE_BREAK_PCT and not (break_above_close > 0.02 and vol_ratio > 3.0):
        return None  # Not a valid breakout
    
    # ── Phase 4: Sustained volume (optional confirmation) ──
    # Check if the 1-2 bars AFTER the spike also have elevated volume
    # (this helps filter false breakouts)
    sustained = True
    if len(candles) >= 2:
        prev_vol = volumes[-2]
        if prev_vol < avg_vol * 1.5:
            # Previous bar wasn't elevated — this might be a one-off spike
            # Still allow, but reduce confidence
            sustained = False
    
    # ── Calculate confidence ──
    confidence = 55  # base
    
    # Volume spike strength
    vol_bonus = min(20, (vol_ratio - VOL_SPIKE_MULT) * 8)
    confidence += int(vol_bonus)
    
    # Compression quality (lower ATR% = better)
    comp_bonus = min(10, (ACCUM_ATR_PCT_MAX - atr_pct) / ACCUM_ATR_PCT_MAX * 10)
    confidence += int(comp_bonus)
    
    # Slope quality (gentle grind is ideal)
    if 0.002 <= slope <= 0.01:  # sweet spot
        confidence += 5
    
    # Breakout magnitude (use whichever break measure is larger)
    break_pct = max(break_above_high, break_above_close)
    break_bonus = min(10, break_pct * 5)
    confidence += int(break_bonus)
    
    # Sustained volume bonus
    if sustained:
        confidence += 5
    
    confidence = max(55, min(85, confidence))
    
    return {
        'direction': 'LONG',
        'price': current['close'],
        'confidence': confidence,
        'vol_ratio': round(vol_ratio, 2),
        'atr_pct': round(atr_pct, 4),
        'range_pct': round(range_pct, 4),
        'slope': round(slope, 6),
        'break_pct': round(break_pct, 4),
        'body_pct': round(body_pct, 4),
        'sustained': sustained,
    }


def run(prices_dict=None) -> int:
    """Entry point for signals_runner — BTC only."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()

    added = 0
    token = 'BTC'
    
    # Check if BTC has a price
    data = prices_dict.get(token)
    if not data or not data.get('price') or data['price'] <= 0:
        return 0
    
    price = data['price']
    
    # Skip if already in a position
    try:
        from position_manager import get_open_positions
        open_pos = {p['token']: p['direction'] for p in get_open_positions()}
        if token in open_pos:
            return 0
    except Exception as e:
        _log(f"  [WARN] Position check failed for {token}: {e}")
    
    # Cooldown check
    if get_cooldown(token, direction='LONG'):
        return 0
    
    # Fetch 1m candles
    candles = _get_1m_candles(token)
    if not candles:
        return 0
    
    # Detect pattern
    sig = detect_btc_grind_spike(candles)
    if sig is None:
        return 0
    
    # Emit signal
    try:
        sid = add_signal(
            token=token,
            direction='LONG',
            signal_type=SIGNAL_TYPE_LONG,
            source=f'{SOURCE_TAG}@vol{sig["vol_ratio"]}',
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
            set_cooldown(token, 'LONG', hours=COOLDOWN_MINUTES / 60.0)
            _log(f"  LONG-btc-grind-spike {token:8s} conf={sig['confidence']}% "
                 f"vol={sig['vol_ratio']}x atr%={sig['atr_pct']} "
                 f"range%={sig['range_pct']} slope={sig['slope']} "
                 f"break%={sig['break_pct']} "
                 f"price={sig['price']:.1f} [{SOURCE_TAG}]")
    except Exception as e:
        _log(f"  [btc_grind_spike] add_signal error: {e}")
    
    return added


if __name__ == '__main__':
    # Test mode — check current BTC state
    candles = _get_1m_candles('BTC')
    if not candles:
        print("No BTC candle data available")
    else:
        print(f"BTC: {len(candles)} 1m candles loaded")
        print(f"Current price: {candles[-1]['close']:.1f}")
        print(f"Last candle: {candles[-1]['ts']} vol={candles[-1]['volume']:.1f}")
        
        sig = detect_btc_grind_spike(candles)
        if sig:
            print(f"\n🟢 SIGNAL DETECTED!")
            print(f"  Direction: {sig['direction']}")
            print(f"  Confidence: {sig['confidence']}%")
            print(f"  Vol ratio: {sig['vol_ratio']}x")
            print(f"  ATR%: {sig['atr_pct']}")
            print(f"  Range%: {sig['range_pct']}")
            print(f"  Slope: {sig['slope']}")
            print(f"  Break%: {sig['break_pct']}")
            print(f"  Sustained: {sig['sustained']}")
        else:
            print("\n⚪ No signal")
            
            # Show diagnostics
            if len(candles) >= LOOKBACK_1M:
                accum = candles[-(ACCUM_LOOKBACK + 1):-1]
                atrs = _compute_atr(accum, ACCUM_ATR_PERIOD)
                valid_atrs = [a for a in atrs if a is not None]
                if valid_atrs:
                    avg_atr = sum(valid_atrs) / len(valid_atrs)
                    price = accum[-1]['close']
                    print(f"  ATR%: {(avg_atr/price)*100:.4f} (max: {ACCUM_ATR_PCT_MAX})")
                
                range_h = max(c['high'] for c in accum)
                range_l = min(c['low'] for c in accum)
                print(f"  Range%: {((range_h-range_l)/price)*100:.4f} (max: {ACCUM_RANGE_PCT_MAX})")
                
                closes = [c['close'] for c in accum]
                slope = _compute_linreg_slope(closes)
                if slope is not None:
                    print(f"  Slope: {slope:.6f} (min: {ACCUM_SLOPE_MIN})")
                else:
                    print(f"  Slope: N/A (insufficient data, min: {ACCUM_SLOPE_MIN})")
                
                volumes = [c['volume'] for c in candles]
                avg_vol = sum(volumes[-VOL_AVG_PERIOD-1:-1]) / VOL_AVG_PERIOD
                cur_vol = volumes[-1]
                print(f"  Vol ratio: {cur_vol/avg_vol:.2f}x (need: {VOL_SPIKE_MULT}x)")
                
                cur = candles[-1]
                print(f"  Bullish candle: {cur['close'] > cur['open']}")
                body_pct = ((cur['close'] - cur['open']) / cur['close']) * 100 if cur['close'] > 0 else 0
                print(f"  Body%: {body_pct:.4f} (min: {MIN_BODY_PCT})")
                break_pct = ((cur['close'] - range_h) / range_h) * 100
                print(f"  Break%: {break_pct:.4f} (min: {PRICE_BREAK_PCT})")
