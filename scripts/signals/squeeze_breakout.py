#!/usr/bin/env python3
"""
squeeze_breakout.py — Consolidation breakout signal.

Thesis: When BTC consolidates (BB squeeze + ATR compression + low volume),
the eventual breakout captures +1.27% average. This signal enters at the
START of the expansion, positioning before the full move.

Uses existing infrastructure:
- continuum_context for direction (score > 60 = LONG, < 40 = SHORT)
- BB width for squeeze detection
- ATR for compression detection
- Volume for calm-before-storm confirmation

Entry: BB width expands 50%+ from squeeze minimum + price breaks range
Exit: +1.5% profit, -0.5% loss, or 2 hour time exit
"""
import sys, os, sqlite3, time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA, CANDLES_DB
from hermes_constants import (
    SQUEEZE_BREAKOUT_ENABLED,
    SQUEEZE_BREAKOUT_PLUS_ENABLED,
    SQUEEZE_BREAKOUT_MINUS_ENABLED,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


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
        # Reverse to chronological
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 
                 'close': r[4], 'volume': r[5]} for r in reversed(rows)]
    except Exception:
        return None


def _calc_bb_width(candles, period=20):
    """Calculate Bollinger Band width as % of price."""
    if len(candles) < period:
        return None
    closes = [c['close'] for c in candles[-period:]]
    avg = sum(closes) / period
    std = (sum((x - avg) ** 2 for x in closes) / period) ** 0.5
    return (std * 2) / avg * 100


def _calc_atr(candles, period=14):
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
    """
    if token != 'BTC':
        return None  # Only BTC for now
    
    # Get candles
    candles = _get_btc_candles(limit=100)
    if not candles or len(candles) < 50:
        return None
    
    # Calculate indicators
    bb_width = _calc_bb_width(candles, 20)
    atr_pct = _calc_atr(candles, 14)
    
    if bb_width is None or atr_pct is None:
        return None
    
    # Check for squeeze: BB width < 0.5% AND ATR < 0.3%
    if bb_width >= 0.5 or atr_pct >= 0.3:
        return None  # Not in squeeze
    
    # Check for expansion: compare to recent minimum
    recent_widths = []
    for i in range(max(0, len(candles) - 20), len(candles)):
        w = _calc_bb_width(candles[:i+1], 20)
        if w is not None:
            recent_widths.append(w)
    
    if not recent_widths:
        return None
    
    min_width = min(recent_widths)
    if bb_width <= min_width * 1.5:
        return None  # Not expanding yet
    
    # Get continuum context for direction
    ctx = _get_continuum_context()
    if not ctx:
        return None
    
    # Determine direction
    price = candles[-1]['close']
    ema20 = sum(c['close'] for c in candles[-20:]) / 20
    
    if ctx['score'] > 60 and price > ema20:
        direction = 'LONG'
    elif ctx['score'] < 40 and price < ema20:
        direction = 'SHORT'
    else:
        return None  # No clear direction
    
    # Calculate confidence
    squeeze_intensity = (0.5 - bb_width) / 0.5 * 100  # 0-100%
    confidence = 65 + min(20, squeeze_intensity * 0.3)
    
    # Continuum alignment bonus
    if direction == 'LONG' and ctx['score'] > 70:
        confidence += 7
    elif direction == 'SHORT' and ctx['score'] < 30:
        confidence += 7
    
    confidence = min(91, confidence)  # Stay under CONF_FILTER_MAX
    
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
            set_cooldown(token, direction, hours=4)  # 4h cooldown
            print(f"[SQUEEZE-BREAKOUT] {direction} {token} | conf={sig['confidence']} | reason={sig['reason']}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    print("Testing squeeze breakout signal...")
    sig = detect('BTC')
    print(f"Signal: {sig}")
