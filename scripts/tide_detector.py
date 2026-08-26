#!/usr/bin/env python3
"""
tide_detector.py — Detect market tide changes using signal clustering.

Uses the lead-lag correlations from cluster analysis to detect when
the market phase is about to change. Provides early warning signals
that can be used by the weather vane to adjust directional penalties.

Key insight from cluster analysis:
- Squeeze/Accelerate appearing → expect Momentum in 2 days
- ZScore flooding → expect Bollinger bounces in 2 days
- Exhaustion appearing → move is ending, expect Range/Defensive

Usage:
    from tide_detector import detect_tide_change
    tide = detect_tide_change()
    # Returns: {'changing': True, 'from_phase': 'range', 'to_phase': 'trend_building',
    #           'confidence': 0.75, 'early_signals': ['Squeeze', 'Accelerate']}

    from tide_detector import get_tide_adjustment
    adj = get_tide_adjustment('LONG')
    # Returns: {'mult': 1.2, 'reason': 'tide rising — early signals suggest breakout'}
"""

import sqlite3
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from paths import RUNTIME_DB, HERMES_DATA

# ── Import clustering modules ─────────────────────────────────────────────────
try:
    from market_phase_gate import detect_phase, signal_family, FAMILY_MAP
    from signal_lifecycle_filter import SIGNAL_LIFECYCLE
    _CLUSTERING_ENABLED = True
except ImportError:
    _CLUSTERING_ENABLED = False

# ── Cache ─────────────────────────────────────────────────────────────────────
_tide_cache = None
_tide_cache_time = 0
_TIDE_CACHE_TTL = 300  # 5 min

# ── Lead-Lag Rules (from cluster analysis) ───────────────────────────────────
# These define which families predict which other families, and with what lag.

LEAD_LAG_RULES = [
    # Leader → Follower, lag in days, correlation strength
    {'leader': 'ZScore', 'follower': 'Pattern', 'lag_days': 1, 'corr': 0.905},
    {'leader': 'Wave', 'follower': 'R2', 'lag_days': 3, 'corr': 0.904},
    {'leader': 'Momentum', 'follower': 'Pattern', 'lag_days': 2, 'corr': 0.902},
    {'leader': 'ZScore', 'follower': 'Exhaustion', 'lag_days': 3, 'corr': 0.864},
    {'leader': 'Stop_Hunt', 'follower': 'HL_Copy', 'lag_days': 2, 'corr': 0.861},
    {'leader': 'Squeeze', 'follower': 'Trendline', 'lag_days': 2, 'corr': 0.799},
    {'leader': 'ZScore', 'follower': 'Bollinger', 'lag_days': 2, 'corr': 0.727},
    {'leader': 'Accelerate', 'follower': 'Momentum', 'lag_days': 2, 'corr': 0.720},
    {'leader': 'Trendline', 'follower': 'Accelerate', 'lag_days': 2, 'corr': 0.710},
    {'leader': 'Momentum', 'follower': 'Bollinger', 'lag_days': 3, 'corr': 0.704},
]

# ── Phase Transition Rules ───────────────────────────────────────────────────
# Map which families appearing means a transition is coming.

PHASE_TRANSITIONS = {
    # When these families spike, expect the listed phase next
    'Squeeze': {'next_phase': 'trend_building', 'lag_days': 2, 'confidence': 0.8},
    'Accelerate': {'next_phase': 'trend_building', 'lag_days': 2, 'confidence': 0.75},
    'Momentum': {'next_phase': 'explosion', 'lag_days': 1, 'confidence': 0.85},
    'ZScore': {'next_phase': 'range', 'lag_days': 2, 'confidence': 0.73},
    'Bollinger': {'next_phase': 'range', 'lag_days': 1, 'confidence': 0.7},
    'Exhaustion': {'next_phase': 'defensive', 'lag_days': 1, 'confidence': 0.86},
    'HL_Copy': {'next_phase': 'defensive', 'lag_days': 1, 'confidence': 0.8},
    'Support_Resistance': {'next_phase': 'defensive', 'lag_days': 1, 'confidence': 0.75},
}

# ── Direction Bias by Phase ──────────────────────────────────────────────────
# Which direction is favored in each phase.

PHASE_DIRECTION_BIAS = {
    'trend_building': {'LONG': 1.1, 'SHORT': 0.9},  # Slightly bullish
    'explosion': {'LONG': 1.2, 'SHORT': 0.8},        # Bullish (momentum)
    'range': {'LONG': 1.0, 'SHORT': 1.0},            # Neutral
    'defensive': {'LONG': 0.9, 'SHORT': 1.1},        # Slightly bearish (choppy)
    'mover_hunting': {'LONG': 1.0, 'SHORT': 1.0},    # Neutral
    'quiet': {'LONG': 1.0, 'SHORT': 1.0},            # Neutral
}


# ── Core Functions ────────────────────────────────────────────────────────────

def get_family_activity(lookback_days: int = 3) -> dict:
    """
    Get activity level for each signal family over the lookback period.
    
    Returns: {family: {'count': int, 'pct': float, 'trend': str}}
    """
    if not _CLUSTERING_ENABLED:
        return {}
    
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        rows = conn.execute('''
            SELECT signal_type, created_at
            FROM signals
            WHERE created_at >= ?
            ORDER BY created_at ASC
        ''', (cutoff,)).fetchall()
    except Exception:
        return {}
    finally:
        if conn:
            conn.close()
    
    if not rows:
        return {}
    
    # Count by family
    family_counts = Counter()
    for sig_type, _ in rows:
        fam = signal_family(sig_type)
        family_counts[fam] += 1
    
    total = sum(family_counts.values())
    if total < 50:
        return {}
    
    # Compute percentages and trend (compare first half vs second half)
    mid_point = len(rows) // 2
    first_half_families = Counter()
    second_half_families = Counter()
    
    for i, (sig_type, _) in enumerate(rows):
        fam = signal_family(sig_type)
        if i < mid_point:
            first_half_families[fam] += 1
        else:
            second_half_families[fam] += 1
    
    result = {}
    for fam, count in family_counts.items():
        pct = count / total * 100
        first_count = first_half_families.get(fam, 0)
        second_count = second_half_families.get(fam, 0)
        
        # Trend: rising, falling, or stable
        if second_count > first_count * 1.2:
            trend = 'rising'
        elif second_count < first_count * 0.8:
            trend = 'falling'
        else:
            trend = 'stable'
        
        result[fam] = {
            'count': count,
            'pct': pct,
            'trend': trend,
            'first_half': first_count,
            'second_half': second_count,
        }
    
    return result


def detect_tide_change() -> dict:
    """
    Detect if the market tide is about to change.
    
    Returns:
        {
            'changing': bool,           # True if a phase transition is likely
            'from_phase': str,          # Current phase
            'to_phase': str,            # Predicted next phase
            'confidence': float,        # 0-1, how confident in the prediction
            'early_signals': list,      # Which early-warning families are active
            'family_activity': dict,    # Full family activity data
            'direction_bias': dict,     # {'LONG': mult, 'SHORT': mult}
        }
    """
    global _tide_cache, _tide_cache_time
    
    now = time.time()
    if _tide_cache and (now - _tide_cache_time) < _TIDE_CACHE_TTL:
        return _tide_cache
    
    if not _CLUSTERING_ENABLED:
        return {'changing': False, 'from_phase': 'unknown', 'to_phase': 'unknown',
                'confidence': 0.0, 'early_signals': [], 'family_activity': {},
                'direction_bias': {'LONG': 1.0, 'SHORT': 1.0}}
    
    # Get current phase
    current_info = detect_phase()
    current_phase = current_info.get('phase', 'quiet')
    
    # Get family activity
    family_activity = get_family_activity(lookback_days=3)
    
    # Detect early-warning signals
    early_signals = []
    predictions = []
    
    for fam, data in family_activity.items():
        if fam in PHASE_TRANSITIONS and data['trend'] == 'rising':
            transition = PHASE_TRANSITIONS[fam]
            early_signals.append(fam)
            predictions.append({
                'next_phase': transition['next_phase'],
                'lag_days': transition['lag_days'],
                'confidence': transition['confidence'] * (data['pct'] / 20),  # Scale by activity
                'leader': fam,
            })
    
    # Find the strongest prediction
    changing = False
    predicted_phase = current_phase
    confidence = 0.0
    
    if predictions:
        # Sort by confidence
        predictions.sort(key=lambda x: -x['confidence'])
        best = predictions[0]
        
        if best['confidence'] > 0.5 and best['next_phase'] != current_phase:
            changing = True
            predicted_phase = best['next_phase']
            confidence = min(1.0, best['confidence'])
    
    # Get direction bias for predicted phase
    direction_bias = PHASE_DIRECTION_BIAS.get(predicted_phase, {'LONG': 1.0, 'SHORT': 1.0})
    
    result = {
        'changing': changing,
        'from_phase': current_phase,
        'to_phase': predicted_phase,
        'confidence': confidence,
        'early_signals': early_signals,
        'family_activity': family_activity,
        'direction_bias': direction_bias,
        'predictions': predictions[:3],  # Top 3 predictions
    }
    
    _tide_cache = result
    _tide_cache_time = now
    
    return result


def get_tide_adjustment(direction: str) -> dict:
    """
    Get a score adjustment based on tide change detection.
    
    Args:
        direction: 'LONG' or 'SHORT'
    
    Returns:
        {
            'mult': float,          # Multiplier for the direction
            'reason': str,          # Human-readable reason
            'tide_changing': bool,  # Whether a change is detected
            'predicted_phase': str, # What phase is coming
        }
    """
    tide = detect_tide_change()
    
    if not tide['changing']:
        return {
            'mult': 1.0,
            'reason': f"No tide change detected (current: {tide['from_phase']})",
            'tide_changing': False,
            'predicted_phase': tide['from_phase'],
        }
    
    # Tide is changing — apply direction bias
    bias = tide['direction_bias'].get(direction, 1.0)
    confidence = tide['confidence']
    
    # Interpolate between 1.0 (no change) and bias (full change)
    mult = 1.0 + (bias - 1.0) * confidence
    
    early_str = ', '.join(tide['early_signals'][:3])
    reason = (f"Tide changing: {tide['from_phase']} → {tide['to_phase']} "
              f"(conf={confidence:.0%}, early: {early_str})")
    
    return {
        'mult': mult,
        'reason': reason,
        'tide_changing': True,
        'predicted_phase': tide['to_phase'],
    }


# ── Weather Vane Integration ─────────────────────────────────────────────────

def get_weather_vane_adjustment(direction: str, current_dir_outcome_mult: float) -> dict:
    """
    Enhanced weather vane that considers tide changes.
    
    When the tide is changing, the weather vane should:
    1. Reduce penalties for the incoming phase's favored direction
    2. Increase penalties for the outgoing phase's favored direction
    3. Provide a "tide change bonus" for trades aligned with the predicted phase
    
    Args:
        direction: 'LONG' or 'SHORT'
        current_dir_outcome_mult: Current directional outcome multiplier
    
    Returns:
        {
            'adjusted_mult': float,  # Adjusted directional outcome multiplier
            'tide_boost': float,     # Additional boost/penalty from tide
            'reason': str,           # Explanation
        }
    """
    tide_adj = get_tide_adjustment(direction)
    
    if not tide_adj['tide_changing']:
        return {
            'adjusted_mult': current_dir_outcome_mult,
            'tide_boost': 1.0,
            'reason': 'No tide change',
        }
    
    # When tide is changing, boost the favored direction
    tide_boost = tide_adj['mult']
    
    # If current direction is being penalized but tide favors it, reduce penalty
    if current_dir_outcome_mult < 1.0 and tide_boost > 1.0:
        # Tide favors this direction — reduce the penalty
        adjusted = current_dir_outcome_mult + (tide_boost - 1.0) * 0.5
        adjusted = min(adjusted, 1.0)  # Don't boost above 1.0
        reason = f"Tide favors {direction} — reducing penalty from {current_dir_outcome_mult:.2f} to {adjusted:.2f}"
    elif current_dir_outcome_mult > 1.0 and tide_boost < 1.0:
        # Tide opposes this direction — reduce the boost
        adjusted = current_dir_outcome_mult - (1.0 - tide_boost) * 0.5
        adjusted = max(adjusted, 1.0)  # Don't reduce below 1.0
        reason = f"Tide opposes {direction} — reducing boost from {current_dir_outcome_mult:.2f} to {adjusted:.2f}"
    else:
        # Tide and weather vane agree — no adjustment needed
        adjusted = current_dir_outcome_mult
        reason = f"Tide and weather vane agree for {direction}"
    
    return {
        'adjusted_mult': adjusted,
        'tide_boost': tide_boost,
        'reason': reason,
    }


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Tide Detector — Self Test ===\n")
    
    # Get family activity
    activity = get_family_activity(lookback_days=3)
    print("Family Activity (3-day lookback):")
    print(f"  {'Family':25s} | {'Count':>6s} | {'%':>6s} | {'Trend':>8s}")
    print("  " + "-"*55)
    for fam, data in sorted(activity.items(), key=lambda x: -x[1]['pct'])[:10]:
        trend_arrow = '↑' if data['trend'] == 'rising' else ('↓' if data['trend'] == 'falling' else '→')
        print(f"  {fam:25s} | {data['count']:6d} | {data['pct']:5.1f}% | {data['trend']:>8s} {trend_arrow}")
    
    # Detect tide change
    tide = detect_tide_change()
    print(f"\nTide Detection:")
    print(f"  Changing: {tide['changing']}")
    print(f"  From: {tide['from_phase']}")
    print(f"  To: {tide['to_phase']}")
    print(f"  Confidence: {tide['confidence']:.0%}")
    print(f"  Early Signals: {tide['early_signals']}")
    
    # Get adjustments for each direction
    print(f"\nDirection Adjustments:")
    for direction in ['LONG', 'SHORT']:
        adj = get_tide_adjustment(direction)
        print(f"  {direction}: mult={adj['mult']:.2f} | {adj['reason']}")
    
    # Weather vane integration
    print(f"\nWeather Vane Integration:")
    for direction in ['LONG', 'SHORT']:
        for current_mult in [0.7, 1.0, 1.3]:
            wv = get_weather_vane_adjustment(direction, current_mult)
            print(f"  {direction} (current={current_mult:.2f}): adjusted={wv['adjusted_mult']:.2f} | {wv['reason']}")
    
    print("\n=== Test Complete ===")
