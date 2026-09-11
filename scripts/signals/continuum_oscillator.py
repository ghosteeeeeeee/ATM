#!/usr/bin/env python3
"""
continuum_oscillator.py — Score cadence oscillator signal for BTC.

Thesis: The continuum score oscillates between troughs and peaks with a
cadence of 30-60 minutes. When we detect the score is RISING through
a meaningful range, we enter LONG. When FALLING, we enter SHORT.

This captures the "riding the wave" pattern — not waiting for extremes,
but entering during the momentum phase of the oscillation.

Improvements (2026-09-12):
- Uses continuum_context for linreg-enhanced confidence
- Faster cadence detection (6-tick window instead of 10)
- Score magnitude influences confidence directly
- Cooldown reduced to 1h (was 2h)

Entry LONG: Score rising through neutral zone (40→60+)
Entry SHORT: Score falling through neutral zone (60→40-)
"""
import sys, os, sqlite3, time, json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA, WWW_DATA

from hermes_constants import (
    CONTINUUM_OSC_ENABLED,
    CONTINUUM_OSC_PLUS_ENABLED,
    CONTINUUM_OSC_MINUS_ENABLED,
    CONTINUUM_OSC_SCORE_RISING_THRESHOLD,
    CONTINUUM_OSC_SCORE_FALLING_THRESHOLD,
    CONTINUUM_OSC_MIN_SCORE,
    CONTINUUM_OSC_MAX_SCORE,
    CONTINUUM_OSC_COOLDOWN_HOURS,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _get_recent_scores(token: str, limit: int = 30) -> list:
    """Get recent continuum scores from continuum.db.
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
        return [(r[0], r[1]) for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _detect_cadence(scores: list) -> dict:
    """
    Detect the score cadence pattern using a fast 6-tick window (3 min).
    
    Returns dict with:
    - trend: 'RISING', 'FALLING', 'FLAT'
    - magnitude: how much the score changed
    - phase: 'PEAK', 'TROUGH', 'RISING', 'FALLING', 'FLAT'
    - current_score: latest score
    - change: signed change (positive = rising)
    """
    if len(scores) < 6:
        return {'trend': 'FLAT', 'magnitude': 0, 'duration': 0, 'phase': 'UNKNOWN',
                'current_score': 50, 'change': 0}
    
    # Use last 6 ticks (3 minutes) for fast detection
    recent = [s[1] for s in scores[-6:]]
    if any(s is None for s in recent):
        return {'trend': 'FLAT', 'magnitude': 0, 'duration': 0, 'phase': 'UNKNOWN',
                'current_score': 50, 'change': 0}
    
    # Split into first half and second half of the window
    first_half = sum(recent[:3]) / 3
    second_half = sum(recent[3:]) / 3
    change = second_half - first_half
    
    current_score = recent[-1]
    
    # Determine phase
    if current_score >= 90:
        phase = 'PEAK'
    elif current_score <= 20:
        phase = 'TROUGH'
    elif change > 1.5:
        phase = 'RISING'
    elif change < -1.5:
        phase = 'FALLING'
    else:
        phase = 'FLAT'
    
    # Calculate duration of current trend (ticks in the same direction)
    duration = 0
    if len(scores) >= 3:
        for i in range(len(scores) - 1, max(0, len(scores) - 20), -1):
            if i == len(scores) - 1:
                continue
            if i < 0 or i + 1 >= len(scores):
                break
            if scores[i + 1][1] > scores[i][1]:
                duration += 1
            elif scores[i + 1][1] < scores[i][1]:
                break
            else:
                duration += 0.5  # flat tick
    
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
    
    Returns {direction, confidence, value, price, reason} or None.
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
    
    # LONG signal: score rising from trough zone
    if (cadence['phase'] == 'RISING' and 
        cadence['current_score'] >= CONTINUUM_OSC_MIN_SCORE and
        cadence['magnitude'] >= CONTINUUM_OSC_SCORE_RISING_THRESHOLD):
        
        # Confidence scales with magnitude and score level
        conf = 65 + min(18, cadence['magnitude'] * 3)
        conf = min(88, conf)
        
        return {
            'direction': 'LONG',
            'confidence': conf,
            'value': cadence['magnitude'],
            'price': price,
            'z_score': None,
            'reason': f'osc_rising_{cadence["magnitude"]:.1f}_score_{cadence["current_score"]:.0f}',
        }
    
    # SHORT signal: score falling from peak zone
    if (cadence['phase'] == 'FALLING' and
        cadence['current_score'] <= CONTINUUM_OSC_MAX_SCORE and
        cadence['magnitude'] >= CONTINUUM_OSC_SCORE_FALLING_THRESHOLD):
        
        conf = 65 + min(18, cadence['magnitude'] * 3)
        conf = min(88, conf)
        
        return {
            'direction': 'SHORT',
            'confidence': conf,
            'value': cadence['magnitude'],
            'price': price,
            'z_score': None,
            'reason': f'osc_falling_{cadence["magnitude"]:.1f}_score_{cadence["current_score"]:.0f}',
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
