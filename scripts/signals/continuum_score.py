#!/usr/bin/env python3
"""
continuum_score.py — Fire signals to existing trading system when continuum
engine reaches extreme scores OR transitions between zones.

Two signal modes:

1. CONTRARIAN (buy fear, sell greed):
   Score ≤ 15 → LONG signal (buy the dip when deeply bearish)
   Score ≥ 85 → SHORT signal (sell the top when deeply bullish)

2. MOMENTUM (zone transitions — ride the wave):
   Score crosses ABOVE 50 from below → LONG (bullish momentum building)
   Score crosses BELOW 50 from above → SHORT (bearish momentum building)

The momentum signals capture the "trendlines forming" — when BTC's continuum
score transitions from bear to bull (or vice versa), altcoins follow.

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
    CONTINUUM_SCORE_LONG_THRESHOLD,        # ≥ this → SHORT (contrarian)
    CONTINUUM_SCORE_SHORT_THRESHOLD,       # ≤ this → LONG (contrarian)
    CONTINUUM_SCORE_COOLDOWN_MIN,
    CONTINUUM_SCORE_STALENESS_MIN,
    CONTINUUM_SCORE_CONF_BASE,
    CONTINUUM_SCORE_MOMENTUM_ENABLED,      # new: zone-transition signals
    CONTINUUM_SCORE_MOMENTUM_THRESHOLD,    # new: how far past 50 to trigger
    CONTINUUM_SCORE_MOMENTUM_CONF,         # new: confidence for momentum signals
)

SIGNAL_TYPE_LONG = 'continuum_score_long'
SIGNAL_TYPE_SHORT = 'continuum_score_short'
SOURCE_LONG = 'continuum+'
SOURCE_SHORT = 'continuum-'

# Momentum signals use distinct source tags for signal_compactor differentiation
SOURCE_MOMENTUM_LONG = 'continuum-mom+'
SOURCE_MOMENTUM_SHORT = 'continuum-mom-'

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _get_recent_scores(token: str = 'BTC', limit: int = 5):
    """Get recent scores from DB. Returns list of (score, price, ts) tuples, oldest first."""
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
        cur = conn.execute(
            "SELECT state_score, price, ts FROM continuum_states "
            "WHERE token = ? ORDER BY ts DESC LIMIT ?",
            (token.upper(), limit)
        )
        rows = cur.fetchall()
        if not rows:
            return []
        # Reverse to oldest-first
        return [(r[0], r[1], r[2]) for r in reversed(rows)]
    except Exception as e:
        print(f"[continuum-score] Error reading DB: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _get_latest_score(token: str = 'BTC'):
    """Get latest continuum score from DB. Returns (score, price, ts) or None."""
    scores = _get_recent_scores(token, limit=1)
    if scores:
        s, p, t = scores[0]
        if s is not None:
            return s, p, t
    return None


def detect_contrarian(token: str = 'BTC'):
    """Detect contrarian signal (buy fear, sell greed at extremes)."""
    result = _get_latest_score(token)
    if not result:
        return None
    
    score, price, ts = result
    
    # Check staleness
    age_minutes = (time.time() - ts) / 60
    if age_minutes > CONTINUUM_SCORE_STALENESS_MIN:
        return None
    
    # Score ≤ 15 → LONG (contrarian: buy when deeply bearish)
    if score <= CONTINUUM_SCORE_SHORT_THRESHOLD:
        # Confidence scales with how extreme: score=0 → 90 conf, score=15 → 70 conf
        extremity = (CONTINUUM_SCORE_SHORT_THRESHOLD - score) / CONTINUUM_SCORE_SHORT_THRESHOLD
        conf = CONTINUUM_SCORE_CONF_BASE + extremity * 10
        return {
            'direction': 'LONG',
            'confidence': min(92, conf),
            'value': score,
            'price': price,
            'reason': f'contrarian_bear_{score:.1f}',
        }
    
    # Score ≥ 85 → SHORT (contrarian: sell when deeply bullish)
    if score >= CONTINUUM_SCORE_LONG_THRESHOLD:
        extremity = (score - CONTINUUM_SCORE_LONG_THRESHOLD) / (100 - CONTINUUM_SCORE_LONG_THRESHOLD)
        conf = CONTINUUM_SCORE_CONF_BASE + extremity * 10
        return {
            'direction': 'SHORT',
            'confidence': min(92, conf),
            'value': score,
            'price': price,
            'reason': f'contrarian_bull_{score:.1f}',
        }
    
    return None


def detect_momentum(token: str = 'BTC'):
    """
    Detect momentum signal from zone transitions.
    
    When score crosses above 50 from below → LONG (bullish momentum building)
    When score crosses below 50 from above → SHORT (bearish momentum building)
    
    This captures the "trendlines forming" — the early stage of a regime shift
    that altcoins will follow.
    """
    if not CONTINUUM_SCORE_MOMENTUM_ENABLED:
        return None
    
    scores = _get_recent_scores(token, limit=5)
    if len(scores) < 2:
        return None
    
    # Check staleness
    latest_score, latest_price, latest_ts = scores[-1]
    if latest_score is None:
        return None
    age_minutes = (time.time() - latest_ts) / 60
    if age_minutes > CONTINUUM_SCORE_STALENESS_MIN:
        return None
    
    # Look for zone transition in recent scores
    prev_score = scores[-2][0]
    if prev_score is None:
        return None
    
    momentum_threshold = CONTINUUM_SCORE_MOMENTUM_THRESHOLD
    
    # Score crossed ABOVE 50 from below — bullish momentum
    if prev_score < 50 and latest_score >= (50 + momentum_threshold):
        distance = latest_score - 50
        conf = CONTINUUM_SCORE_MOMENTUM_CONF + min(10, distance / 2)
        return {
            'direction': 'LONG',
            'confidence': min(88, conf),
            'value': latest_score,
            'price': latest_price,
            'reason': f'momentum_cross_up_{prev_score:.1f}_to_{latest_score:.1f}',
        }
    
    # Score crossed BELOW 50 from above — bearish momentum
    if prev_score > 50 and latest_score <= (50 - momentum_threshold):
        distance = 50 - latest_score
        conf = CONTINUUM_SCORE_MOMENTUM_CONF + min(10, distance / 2)
        return {
            'direction': 'SHORT',
            'confidence': min(88, conf),
            'value': latest_score,
            'price': latest_price,
            'reason': f'momentum_cross_down_{prev_score:.1f}_to_{latest_score:.1f}',
        }
    
    return None


def detect(token: str = 'BTC'):
    """
    Detect any continuum score signal for a token.
    Tries contrarian first (higher priority), then momentum.
    """
    # Contrarian has priority — extreme scores are stronger signals
    sig = detect_contrarian(token)
    if sig:
        return sig
    
    # Then try momentum (zone transitions)
    sig = detect_momentum(token)
    if sig:
        return sig
    
    return None


def scan_signals():
    """Scan for continuum score signals."""
    if not CONTINUUM_SCORE_ENABLED:
        return 0
    
    added = 0
    sig = detect('BTC')
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
    
    # Use different source tags for contrarian vs momentum
    reason = sig.get('reason', '')
    if reason.startswith('momentum_'):
        source = SOURCE_MOMENTUM_LONG if direction == 'LONG' else SOURCE_MOMENTUM_SHORT
    else:
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
        print(f"[continuum-score] Signal fired: {direction} | Score={sig['value']:.1f} | "
              f"Conf={sig['confidence']} | reason={reason}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    # Test mode
    print("=== Continuum Score Signal Test ===")
    
    result = _get_latest_score()
    if result:
        score, price, ts = result
        age = (time.time() - ts) / 60
        print(f"Current score: {score:.1f}")
        print(f"Price: ${price:.1f}")
        print(f"Age: {age:.0f} minutes")
        print(f"Contrarian LONG threshold: ≤{CONTINUUM_SCORE_SHORT_THRESHOLD}")
        print(f"Contrarian SHORT threshold: ≥{CONTINUUM_SCORE_LONG_THRESHOLD}")
        print(f"Momentum threshold: ±{CONTINUUM_SCORE_MOMENTUM_THRESHOLD} past 50")
        print()
        
        sig = detect_contrarian()
        if sig:
            print(f"Contrarian signal: {sig['direction']} | Conf: {sig['confidence']} | reason={sig['reason']}")
        else:
            print("No contrarian signal")
        
        sig = detect_momentum()
        if sig:
            print(f"Momentum signal: {sig['direction']} | Conf: {sig['confidence']} | reason={sig['reason']}")
        else:
            print("No momentum signal")
    else:
        print("No continuum data found")
