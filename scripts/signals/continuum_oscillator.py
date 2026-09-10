#!/usr/bin/env python3
"""
continuum_oscillator.py — Score cadence oscillator signal for BTC.

Thesis: The continuum score oscillates between 60-65 (troughs) and 90-100 (peaks)
with a 30-60 minute cadence. Rising score = momentum building = LONG opportunity.
Falling score = momentum fading = SHORT opportunity.

Entry LONG: Score rising from 60 → 80+ (momentum building)
Entry SHORT: Score falling from 90 → 60 (momentum fading)

This is a momentum oscillator signal derived from the continuum engine's
composite score. It captures the cadence pattern observed in live trading.
"""
import sys, os, sqlite3, time, json, math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA, WWW_DATA

from hermes_constants import (
    CONTINUUM_OSC_ENABLED,
    CONTINUUM_OSC_PLUS_ENABLED,
    CONTINUUM_OSC_MINUS_ENABLED,
    CONTINUUM_OSC_SCORE_RISING_THRESHOLD,  # Score must rise by this much
    CONTINUUM_OSC_SCORE_FALLING_THRESHOLD,  # Score must fall by this much
    CONTINUUM_OSC_MIN_SCORE,  # Minimum score for LONG entry
    CONTINUUM_OSC_MAX_SCORE,  # Maximum score for SHORT entry
    CONTINUUM_OSC_COOLDOWN_HOURS,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

# ── Continuum score data source ────────────────────────────────────────────────
# The score is computed by continuum_engine.py and stored in continuum.db
# We read the last N scores to detect the cadence pattern.

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _get_recent_scores(token: str, limit: int = 30) -> list:
    """Get recent continuum scores for a token from continuum.db.
    Returns list of (timestamp, score) tuples, oldest first."""
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, state_score FROM continuum_states
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        # Reverse to oldest-first
        return [(r[0], r[1]) for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_current_score(token: str) -> float:
    """Get the most recent continuum score for a token."""
    scores = _get_recent_scores(token, limit=1)
    if scores:
        return scores[0][1]
    return 50.0  # Default neutral


def _detect_cadence(scores: list) -> dict:
    """
    Detect the score cadence pattern.
    
    Returns dict with:
    - trend: 'RISING', 'FALLING', 'FLAT'
    - magnitude: how much the score changed
    - duration: how long the trend has been active
    - phase: 'PEAK', 'TROUGH', 'RISING', 'FALLING'
    """
    if len(scores) < 5:
        return {'trend': 'FLAT', 'magnitude': 0, 'duration': 0, 'phase': 'UNKNOWN'}
    
    # Get recent scores (last 10 ticks = 5 minutes)
    recent = [s[1] for s in scores[-10:]]
    
    # Calculate trend
    first_half = sum(recent[:5]) / 5
    second_half = sum(recent[5:]) / 5
    change = second_half - first_half
    
    # Determine phase
    current_score = recent[-1]
    if current_score >= 95:
        phase = 'PEAK'
    elif current_score <= 65:
        phase = 'TROUGH'
    elif change > 2:
        phase = 'RISING'
    elif change < -2:
        phase = 'FALLING'
    else:
        phase = 'FLAT'
    
    # Calculate duration of current trend
    duration = 0
    if len(scores) >= 3:
        for i in range(len(scores)-1, 0, -1):
            if i == len(scores)-1:
                continue
            if scores[i][1] > scores[i-1][1]:
                duration += 1
            else:
                break
    
    return {
        'trend': 'RISING' if change > 1 else ('FALLING' if change < -1 else 'FLAT'),
        'magnitude': abs(change),
        'duration': duration,
        'phase': phase,
        'current_score': current_score,
        'change': change,
    }


def detect(token: str) -> dict:
    """
    Detect continuum oscillator signal for a token.
    
    Returns {direction, confidence, value, price} or None.
    """
    # Get recent scores
    scores = _get_recent_scores(token, limit=30)
    if len(scores) < 10:
        return None
    
    # Detect cadence
    cadence = _detect_cadence(scores)
    
    # Get current price (from hl_cache)
    try:
        with open(os.path.join(WWW_DATA, 'hl_cache.json')) as f:
            cache = json.load(f)
        price = float(cache.get('allMids', {}).get(token, 0))
        if price <= 0:
            return None
    except Exception:
        return None
    
    # LONG signal: score rising from trough
    if (cadence['phase'] == 'RISING' and 
        cadence['current_score'] >= CONTINUUM_OSC_MIN_SCORE and
        cadence['magnitude'] >= CONTINUUM_OSC_SCORE_RISING_THRESHOLD):
        
        # Confidence based on magnitude and current score
        conf = 60 + min(20, cadence['magnitude'] * 2)
        conf = min(88, conf)  # Cap at 88
        
        return {
            'direction': 'LONG',
            'confidence': conf,
            'value': cadence['magnitude'],
            'price': price,
            'z_score': None,
            'reason': f'score_rising_{cadence["magnitude"]:.1f}',
        }
    
    # SHORT signal: score falling from peak
    if (cadence['phase'] == 'FALLING' and
        cadence['current_score'] <= CONTINUUM_OSC_MAX_SCORE and
        cadence['magnitude'] >= CONTINUUM_OSC_SCORE_FALLING_THRESHOLD):
        
        conf = 60 + min(20, cadence['magnitude'] * 2)
        conf = min(88, conf)
        
        return {
            'direction': 'SHORT',
            'confidence': conf,
            'value': cadence['magnitude'],
            'price': price,
            'z_score': None,
            'reason': f'score_falling_{cadence["magnitude"]:.1f}',
        }
    
    return None


def scan_signals() -> int:
    """Scan all tokens for continuum oscillator signals."""
    added = 0
    
    # Only scan BTC (continuum engine tracks BTC)
    tokens = ['BTC']
    
    for token in tokens:
        # Layer 1: blacklists
        if token.upper() in LONG_BLACKLIST or token.upper() in SHORT_BLACKLIST:
            continue
        
        # Detect signal
        sig = detect(token)
        if not sig:
            continue
        
        direction = sig['direction']
        
        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not CONTINUUM_OSC_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not CONTINUUM_OSC_MINUS_ENABLED:
            continue
        
        # Cooldown
        if get_cooldown(token, direction=direction):
            continue
        
        sig_type = f'continuum_osc_{direction.lower()}'
        source = f'continuum-osc{"+" if direction == "LONG" else "-"}'
        
        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=CONTINUUM_OSC_COOLDOWN_HOURS)
            print(f"[CONTINUUM-OSC] {direction} {token} | conf={sig['confidence']} | reason={sig['reason']}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    # Test mode
    print("Testing continuum oscillator signal...")
    scores = _get_recent_scores('BTC', limit=30)
    print(f"Recent scores: {len(scores)}")
    if scores:
        cadence = _detect_cadence(scores)
        print(f"Cadence: {cadence}")
        sig = detect('BTC')
        print(f"Signal: {sig}")
