#!/usr/bin/env python3
"""
squeeze_breakout.py — Consolidation breakout signal.

Thesis: When BTC consolidates (BB squeeze + ATR compression + low volume),
the eventual breakout captures +1.27% average. This signal enters at the
START of the expansion, positioning before the full move.

Uses existing infrastructure:
- continuum_context for direction (score > 50 = LONG, < 50 = SHORT)
- BB width for squeeze detection
- ATR for compression detection
- Volume for calm-before-storm confirmation
- Price breakout confirmation

Entry: BB width expands 2x+ from squeeze minimum + price breaks range + volume < 80% avg
Exit: +1.0% profit, -0.8% loss, or 2 hour time exit (handled by execution layer)
R:R = 1.25:1

Fixes (2026-09-21):
- Expansion detection fires only on FIRST candle of expansion
- Expansion threshold raised from 1.5x to 2.0x
- Added volume check (calm before storm)
- Added price breakout confirmation
- Widened continuum thresholds to 50/50
- R:R improved to 1.25:1
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA, CANDLES_DB
from hermes_constants import (
    SQUEEZE_BREAKOUT_ENABLED,
    SQUEEZE_BREAKOUT_PLUS_ENABLED,
    SQUEEZE_BREAKOUT_MINUS_ENABLED,
    SQUEEZE_BREAKOUT_BB_SQUEEZE_THRESH,
    SQUEEZE_BREAKOUT_ATR_SQUEEZE_THRESH,
    SQUEEZE_BREAKOUT_VOLUME_PCT,
    SQUEEZE_BREAKOUT_BB_PERIOD,
    SQUEEZE_BREAKOUT_ATR_PERIOD,
    SQUEEZE_BREAKOUT_EXPANSION_LOOKBACK,
    SQUEEZE_BREAKOUT_EXPANSION_MULT,
    SQUEEZE_BREAKOUT_COOLDOWN_HOURS,
    SQUEEZE_BREAKOUT_CONTINUUM_LONG_THRESH,
    SQUEEZE_BREAKOUT_CONTINUUM_SHORT_THRESH,
    SQUEEZE_BREAKOUT_SQUEEZE_RANGE_BARS,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')

# State tracking — prevents firing on every expansion candle
_last_expansion_fired = 0  # timestamp of last signal


def _get_btc_candles(limit=100):
    """Get recent BTC 15m candles."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_15m
            WHERE token = 'BTC' AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return None
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 
                 'close': r[4], 'volume': r[5]} for r in reversed(rows)]
    except Exception:
        return None


def _calc_bb_width(candles, period=SQUEEZE_BREAKOUT_BB_PERIOD):
    """Calculate Bollinger Band width as % of price."""
    if len(candles) < period:
        return None
    closes = [c['close'] for c in candles[-period:]]
    avg = sum(closes) / period
    std = (sum((x - avg) ** 2 for x in closes) / period) ** 0.5
    return (std * 2) / avg * 100


def _calc_atr(candles, period=SQUEEZE_BREAKOUT_ATR_PERIOD):
    """Calculate ATR as % of price."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    atr = sum(trs[-period:]) / period
    return atr / candles[-1]['close'] * 100


def _get_continuum_context():
    """Get BTC continuum context for direction."""
    try:
        import sqlite3 as s3
        conn = s3.connect(CONTINUUM_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT state_score, ema300_position, trend_quality
            FROM continuum_states
            WHERE token = 'BTC'
            ORDER BY ts DESC LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                'score': row[0],
                'ema300_position': row[1],
                'trend_quality': row[2],
            }
    except Exception:
        pass
    return None


def detect(token='BTC'):
    """
    Detect squeeze breakout signal.
    Returns {direction, confidence, value, price, reason} or None.
    
    Fires ONLY on the FIRST candle of expansion from a squeeze.
    """
    global _last_expansion_fired
    
    if token != 'BTC':
        return None
    
    candles = _get_btc_candles(limit=100)
    if not candles or len(candles) < 50:
        return None
    
    bb_width = _calc_bb_width(candles, SQUEEZE_BREAKOUT_BB_PERIOD)
    atr_pct = _calc_atr(candles, SQUEEZE_BREAKOUT_ATR_PERIOD)
    
    if bb_width is None or atr_pct is None:
        return None
    
    # Check for squeeze: BB width < threshold AND ATR < threshold AND volume below average
    if bb_width >= SQUEEZE_BREAKOUT_BB_SQUEEZE_THRESH or atr_pct >= SQUEEZE_BREAKOUT_ATR_SQUEEZE_THRESH:
        return None
    
    # Volume check: must be below threshold of 20-period average (calm before storm)
    if len(candles) >= SQUEEZE_BREAKOUT_BB_PERIOD:
        vol_avg = sum(c['volume'] for c in candles[-SQUEEZE_BREAKOUT_BB_PERIOD:]) / SQUEEZE_BREAKOUT_BB_PERIOD
        if candles[-1]['volume'] > vol_avg * SQUEEZE_BREAKOUT_VOLUME_PCT:
            return None  # Volume too high — not calm enough
    
    # Check for expansion: compare to lookback minimum
    recent_widths = []
    for i in range(max(0, len(candles) - SQUEEZE_BREAKOUT_EXPANSION_LOOKBACK), len(candles)):
        w = _calc_bb_width(candles[:i+1], SQUEEZE_BREAKOUT_BB_PERIOD)
        if w is not None:
            recent_widths.append(w)
    
    if not recent_widths:
        return None
    
    min_width = min(recent_widths)
    
    # Expansion threshold
    if bb_width <= min_width * SQUEEZE_BREAKOUT_EXPANSION_MULT:
        return None
    
    # First candle check: previous candle must NOT have been expanding
    if len(candles) >= 2:
        prev_width = _calc_bb_width(candles[:-1], SQUEEZE_BREAKOUT_BB_PERIOD)
        if prev_width is not None and prev_width > min_width * SQUEEZE_BREAKOUT_EXPANSION_MULT:
            return None
    
    # State check: cooldown between signals
    now = time.time()
    if now - _last_expansion_fired < SQUEEZE_BREAKOUT_COOLDOWN_HOURS * 3600:
        return None
    
    # Get continuum context
    ctx = _get_continuum_context()
    if not ctx:
        return None
    
    # Direction with price breakout confirmation
    price = candles[-1]['close']
    ema20 = sum(c['close'] for c in candles[-SQUEEZE_BREAKOUT_BB_PERIOD:]) / SQUEEZE_BREAKOUT_BB_PERIOD
    squeeze_low = min(c['low'] for c in candles[-SQUEEZE_BREAKOUT_SQUEEZE_RANGE_BARS:])
    squeeze_high = max(c['high'] for c in candles[-SQUEEZE_BREAKOUT_SQUEEZE_RANGE_BARS:])
    
    if ctx['score'] > SQUEEZE_BREAKOUT_CONTINUUM_LONG_THRESH and price > ema20 and price > squeeze_high:
        direction = 'LONG'
    elif ctx['score'] < SQUEEZE_BREAKOUT_CONTINUUM_SHORT_THRESH and price < ema20 and price < squeeze_low:
        direction = 'SHORT'
    else:
        return None
    
    # Mark as fired
    _last_expansion_fired = now
    
    # Confidence
    squeeze_intensity = (0.5 - bb_width) / 0.5 * 100
    confidence = 65 + min(20, squeeze_intensity * 0.3)
    if direction == 'LONG' and ctx['score'] > 60:
        confidence += 7
    elif direction == 'SHORT' and ctx['score'] < 40:
        confidence += 7
    confidence = min(91, confidence)
    
    return {
        'direction': direction,
        'confidence': confidence,
        'value': bb_width,
        'price': price,
        'z_score': None,
        'reason': f'squeeze_breakout_{bb_width:.2f}%_atr_{atr_pct:.2f}%_score_{ctx["score"]:.0f}',
    }


def scan_signals():
    """Scan for squeeze breakout signals."""
    added = 0
    
    for token in ['BTC']:
        if token in LONG_BLACKLIST or token in SHORT_BLACKLIST:
            continue
        
        sig = detect(token)
        if not sig:
            continue
        
        direction = sig['direction']
        
        if direction == 'LONG' and not SQUEEZE_BREAKOUT_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not SQUEEZE_BREAKOUT_MINUS_ENABLED:
            continue
        
        if get_cooldown(token, direction=direction):
            continue
        
        sig_type = f'squeeze_breakout_{direction.lower()}'
        source = f'squeeze-breakout{"+" if direction == "LONG" else "-"}'
        
        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='15m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=SQUEEZE_BREAKOUT_COOLDOWN_HOURS)
            print(f"[SQUEEZE-BREAKOUT] {direction} {token} | conf={sig['confidence']} | reason={sig['reason']}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    print("Testing squeeze breakout signal...")
    sig = detect('BTC')
    print(f"Signal: {sig}")
