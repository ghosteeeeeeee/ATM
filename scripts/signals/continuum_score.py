#!/usr/bin/env python3
"""
continuum_score.py — Fire signals to existing trading system when continuum
engine reaches extreme scores.

CONTRARIAN logic (buy fear, sell greed):
  Score ≤ 5 → LONG signal (buy the dip when extremely bearish)
  Score ≥ 95 → SHORT signal (sell the top when extremely bullish)

Cooldown: 5 minutes between signals per direction.
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    CONTINUUM_SCORE_ENABLED,
    CONTINUUM_SCORE_LONG_ENABLED,
    CONTINUUM_SCORE_SHORT_ENABLED,
    CONTINUUM_SCORE_LONG_THRESHOLD,
    CONTINUUM_SCORE_SHORT_THRESHOLD,
    CONTINUUM_SCORE_COOLDOWN_MIN,
    CONTINUUM_SCORE_STALENESS_MIN,
    CONTINUUM_SCORE_CONF_BASE,
)

SIGNAL_TYPE_LONG = 'continuum_score_long'
SIGNAL_TYPE_SHORT = 'continuum_score_short'
SOURCE_LONG = 'continuum+'
SOURCE_SHORT = 'continuum-'

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _get_latest_score():
    """Get latest continuum score from DB. Returns (score, price, ts) or None."""
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
        cur = conn.execute(
            "SELECT state_score, price, ts FROM continuum_states "
            "WHERE token='BTC' ORDER BY ts DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            return row[0], row[1], row[2]
    except Exception as e:
        print(f"[continuum-score] Error reading DB: {e}")
    finally:
        if conn:
            conn.close()
    return None


def detect():
    """Check if continuum score triggers a signal."""
    result = _get_latest_score()
    if not result:
        return None
    
    score, price, ts = result
    
    # Null guard
    if score is None:
        return None
    
    # Check staleness (should be within last 5 minutes)
    age_minutes = (time.time() - ts) / 60
    if age_minutes > CONTINUUM_SCORE_STALENESS_MIN:
        print(f"[continuum-score] Stale data: {age_minutes:.0f}min old, skipping")
        return None
    
    # Score ≤ 5 → LONG signal (contrarian: buy when extremely bearish)
    if score <= CONTINUUM_SCORE_SHORT_THRESHOLD:
        return {
            'direction': 'LONG',
            'confidence': CONTINUUM_SCORE_CONF_BASE,
            'value': score,
            'price': price,
        }
    
    # Score ≥ 98 → SHORT signal (contrarian: sell when extremely bullish)
    if score >= CONTINUUM_SCORE_LONG_THRESHOLD:
        return {
            'direction': 'SHORT',
            'confidence': CONTINUUM_SCORE_CONF_BASE,
            'value': score,
            'price': price,
        }
    
    return None


def scan_signals():
    """Scan for continuum score signals."""
    if not CONTINUUM_SCORE_ENABLED:
        return 0
    
    added = 0
    sig = detect()
    if not sig:
        return 0
    
    direction = sig['direction']
    
    # Layer 1: per-direction kill-switch
    if direction == 'LONG' and not CONTINUUM_SCORE_LONG_ENABLED:
        return 0
    if direction == 'SHORT' and not CONTINUUM_SCORE_SHORT_ENABLED:
        return 0
    
    # Cooldown
    if get_cooldown('BTC', direction=direction):
        return 0
    
    sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
    source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
    
    sid = add_signal(
        token='BTC',
        direction=direction,
        signal_type=sig_type,
        source=source,
        confidence=sig['confidence'],
        value=sig['value'],
        price=sig['price'],
        exchange='hyperliquid',
        timeframe='1m',
    )
    
    if sid:
        added += 1
        set_cooldown('BTC', direction, hours=CONTINUUM_SCORE_COOLDOWN_MIN / 60.0)
        print(f"[continuum-score] Signal fired: {direction} | Score={sig['value']:.1f} | Price=${sig['price']:.1f}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    # Test mode
    result = _get_latest_score()
    if result:
        score, price, ts = result
        age = (time.time() - ts) / 60
        print(f"Current score: {score:.1f}")
        print(f"Price: ${price:.1f}")
        print(f"Age: {age:.0f} minutes")
        print(f"Long threshold: {CONTINUUM_SCORE_LONG_THRESHOLD}")
        print(f"Short threshold: {CONTINUUM_SCORE_SHORT_THRESHOLD}")
        
        sig = detect()
        if sig:
            print(f"Signal: {sig['direction']} | Confidence: {sig['confidence']}")
        else:
            print("No signal")
    else:
        print("No continuum data found")
