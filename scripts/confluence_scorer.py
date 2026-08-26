#!/usr/bin/env python3
"""
confluence_scorer.py — Score multi-family agreement based on known strong combos.

From cluster analysis: signals from multiple families firing on the same coin
within the same day are high-probability setups. This module scores those combos.

Usage:
    from confluence_scorer import score_confluence, get_confluence_bonus
    
    # Score a list of signal families
    bonus = score_confluence(['Bollinger', 'Support_Resistance', 'Mover'])
    # Returns: 15 (bonus points)
    
    # Get bonus for a specific signal combo
    bonus = get_confluence_bonus(['bb_bounce_short', 'support_resistance', 'coin_tracker_hot_long'])
    # Returns: 15 (bonus points)
"""

import sqlite3
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from paths import RUNTIME_DB, HERMES_DATA

# Import family mapping from market_phase_gate
try:
    from market_phase_gate import signal_family, FAMILY_MAP
except ImportError:
    # Fallback if market_phase_gate not available
    FAMILY_MAP = {}
    def signal_family(sig_type):
        return 'Other'

# ── Cache ─────────────────────────────────────────────────────────────────────
_confluence_cache = None
_confluence_cache_time = 0
_CONFLUENCE_CACHE_TTL = 300  # 5 min

# ── Strong Confluence Combos (from cluster analysis) ──────────────────────────
# Each combo: families involved, bonus points, minimum families needed
# Source: plans/signal-cluster-analysis-2026-08-26.md (co-signal patterns)

STRONG_CONFLUENCES = [
    # bb_bounce + support_resistance = 444 co-occurrences (strongest)
    {'families': ['Bollinger', 'Support_Resistance'], 'bonus': 10, 'min_families': 2},
    
    # bb_bounce + coin_tracker_hot = 280 co-occurrences
    {'families': ['Bollinger', 'Mover'], 'bonus': 12, 'min_families': 2},
    
    # coin_tracker_hot + support_resistance = 255 co-occurrences
    {'families': ['Mover', 'Support_Resistance'], 'bonus': 10, 'min_families': 2},
    
    # hot-set + support_resistance = 208 co-occurrences
    {'families': ['Hot_Set', 'Support_Resistance'], 'bonus': 8, 'min_families': 2},
    
    # r2_trend + support_resistance = 201 co-occurrences
    {'families': ['R2', 'Support_Resistance'], 'bonus': 10, 'min_families': 2},
    
    # bb_bounce + r2_trend = 160 co-occurrences
    {'families': ['Bollinger', 'R2'], 'bonus': 8, 'min_families': 2},
    
    # bb_bounce + hot-set = 199 co-occurrences
    {'families': ['Bollinger', 'Hot_Set'], 'bonus': 7, 'min_families': 2},
    
    # bb_bounce + tl_break = 152 co-occurrences (mixed signal, but real)
    {'families': ['Bollinger', 'Trendline'], 'bonus': 3, 'min_families': 2},
    
    # return_exhaustion + support_resistance = 151 co-occurrences
    {'families': ['Exhaustion', 'Support_Resistance'], 'bonus': 8, 'min_families': 2},
    
    # squeeze_cross + tl_break = 117 co-occurrences ("powder keg")
    {'families': ['Squeeze', 'Trendline'], 'bonus': 10, 'min_families': 2},
    
    # Super-confluence: 3+ families (highest probability)
    {'families': ['Bollinger', 'Support_Resistance', 'Mover'], 'bonus': 15, 'min_families': 3},
    {'families': ['Bollinger', 'R2', 'Support_Resistance'], 'bonus': 15, 'min_families': 3},
    {'families': ['Bollinger', 'Hot_Set', 'Support_Resistance'], 'bonus': 12, 'min_families': 3},
    {'families': ['R2', 'Mover', 'Support_Resistance'], 'bonus': 12, 'min_families': 3},
    {'families': ['Exhaustion', 'Support_Resistance', 'Bollinger'], 'bonus': 10, 'min_families': 3},
]

# ── Weak Confluence Combos (contradictory families) ──────────────────────────
# These combos indicate conflicting signals — penalize

WEAK_CONFLUENCES = [
    # Trendline vs Bollinger (r=-0.386) — trending vs mean-reverting
    {'families': ['Trendline', 'Bollinger'], 'penalty': -15, 'reason': 'trending vs mean-reverting'},
    
    # Squeeze vs HL_Copy (r=-0.266) — compression vs defensive
    {'families': ['Squeeze', 'HL_Copy'], 'penalty': -10, 'reason': 'compression vs defensive'},
    
    # Trendline vs HL_Copy (r=-0.374) — trend vs copy-trading
    {'families': ['Trendline', 'HL_Copy'], 'penalty': -10, 'reason': 'trend vs copy-trading'},
    
    # Momentum vs Exhaustion — contradictory
    {'families': ['Momentum', 'Exhaustion'], 'penalty': -12, 'reason': 'momentum vs exhaustion'},
]

# ── Known Strong Coin-Specific Combos ────────────────────────────────────────
# From cluster analysis: certain coins have specific strong combos

COIN_STRONG_COMBOS = {
    # These are examples — will be populated by Hebbian V2 over time
    # 'SOL': [{'families': ['Bollinger', 'R2'], 'bonus': 5}],
}


def score_confluence(families: list, verbose: bool = False) -> dict:
    """
    Score a list of signal families for confluence.
    
    Args:
        families: List of family names (e.g., ['Bollinger', 'Support_Resistance', 'Mover'])
        verbose: If True, return detailed breakdown
    
    Returns:
        {
            'bonus': int,           # Total bonus/penalty points
            'strong_combos': list,  # Which strong combos matched
            'weak_combos': list,    # Which weak combos matched
            'family_count': int,    # Number of unique families
            'level': str,           # 'none', 'weak', 'moderate', 'strong', 'super'
        }
    """
    families_set = set(families)
    family_count = len(families_set)
    
    total_bonus = 0
    strong_matches = []
    weak_matches = []
    
    # Check strong combos
    for combo in STRONG_CONFLUENCES:
        overlap = families_set.intersection(set(combo['families']))
        if len(overlap) >= combo['min_families']:
            total_bonus += combo['bonus']
            strong_matches.append({
                'combo': combo['families'],
                'bonus': combo['bonus'],
                'matched': list(overlap),
            })
    
    # Check weak combos
    for combo in WEAK_CONFLUENCES:
        overlap = families_set.intersection(set(combo['families']))
        if len(overlap) >= 2:
            total_bonus += combo['penalty']
            weak_matches.append({
                'combo': combo['families'],
                'penalty': combo['penalty'],
                'reason': combo['reason'],
                'matched': list(overlap),
            })
    
    # Determine confluence level
    if family_count >= 3 and total_bonus > 15:
        level = 'super'
    elif family_count >= 3 and total_bonus > 8:
        level = 'strong'
    elif total_bonus > 5:
        level = 'moderate'
    elif total_bonus > 0:
        level = 'weak'
    else:
        level = 'none'
    
    result = {
        'bonus': total_bonus,
        'strong_combos': strong_matches,
        'weak_combos': weak_matches,
        'family_count': family_count,
        'level': level,
    }
    
    return result


def get_confluence_bonus(signal_types: list, verbose: bool = False) -> dict:
    """
    Get confluence bonus for a list of signal types (converts to families first).
    
    Args:
        signal_types: List of signal type names (e.g., ['bb_bounce_short', 'support_resistance'])
        verbose: If True, return detailed breakdown
    
    Returns:
        Same as score_confluence() but accepts signal types instead of families.
    """
    families = [signal_family(st) for st in signal_types]
    return score_confluence(families, verbose=verbose)


def get_coin_confluence(token: str, lookback_hours: int = 24) -> dict:
    """
    Get confluence score for a specific coin based on recent signals.
    
    Args:
        token: Coin ticker (e.g., 'SOL')
        lookback_hours: Hours to look back for signals
    
    Returns:
        Same as score_confluence() but coin-specific.
    """
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now() - timedelta(hours=lookback_hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        rows = conn.execute('''
            SELECT signal_type
            FROM signals
            WHERE token = ? AND created_at >= ?
        ''', (token.upper(), cutoff)).fetchall()
        conn.close()
    except Exception:
        return {'bonus': 0, 'level': 'none', 'error': 'db_read_failed'}
    
    if not rows:
        return {'bonus': 0, 'level': 'none', 'family_count': 0}
    
    signal_types = [row[0] for row in rows]
    families = list(set(signal_family(st) for st in signal_types))
    
    result = score_confluence(families)
    result['token'] = token
    result['signal_count'] = len(signal_types)
    result['unique_signals'] = list(set(signal_types))
    
    # Check coin-specific combos
    coin_bonus = COIN_STRONG_COMBOS.get(token.upper(), [])
    for combo in coin_bonus:
        overlap = set(families).intersection(set(combo['families']))
        if len(overlap) >= 2:
            result['bonus'] += combo['bonus']
            result['coin_specific'] = True
    
    return result


def detect_confluence_zone(lookback_days: int = 1) -> list:
    """
    Detect coins with 3+ families spiking simultaneously (= confluence zones).
    
    Returns list of coins with high confluence.
    """
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        rows = conn.execute('''
            SELECT token, signal_type
            FROM signals
            WHERE created_at >= ?
        ''', (cutoff,)).fetchall()
        conn.close()
    except Exception:
        return []
    
    # Group by token
    token_signals = defaultdict(list)
    for token, sig_type in rows:
        token_signals[token].append(sig_type)
    
    # Find coins with 3+ families
    confluence_zones = []
    for token, signals in token_signals.items():
        families = list(set(signal_family(st) for st in signals))
        if len(families) >= 3:
            result = score_confluence(families)
            if result['bonus'] > 5:  # meaningful confluence
                result['token'] = token
                result['families'] = families
                result['signal_count'] = len(signals)
                confluence_zones.append(result)
    
    # Sort by bonus (strongest confluence first)
    confluence_zones.sort(key=lambda x: -x['bonus'])
    
    return confluence_zones


# ── Confluence-Aware Score Multiplier ────────────────────────────────────────

def get_confluence_mult(families: list, phase: str = None) -> float:
    """
    Get a score multiplier based on confluence level.
    
    Args:
        families: List of family names present in the signal set
        phase: Current market phase (optional)
    
    Returns:
        float multiplier (0.8 to 1.3 range)
    """
    result = score_confluence(families)
    
    # Base multiplier from confluence level
    level_mults = {
        'super': 1.3,     # 3+ families, strong combo → +30%
        'strong': 1.2,    # 3+ families, moderate combo → +20%
        'moderate': 1.1,  # 2 families, good combo → +10%
        'weak': 1.0,      # 2 families, weak combo → neutral
        'none': 0.9,      # no confluence → slight penalty
    }
    
    mult = level_mults.get(result['level'], 0.9)
    
    # Phase-specific adjustments
    if phase == 'range':
        # In range phases, Bollinger+SR confluence is extra strong
        if 'Bollinger' in families and 'Support_Resistance' in families:
            mult += 0.1
    elif phase == 'defensive':
        # In defensive phases, HL_Copy+SR confluence is extra strong
        if 'HL_Copy' in families and 'Support_Resistance' in families:
            mult += 0.1
    
    return min(1.3, max(0.8, mult))  # clamp to 0.8-1.3


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Confluence Scorer — Self Test ===\n")
    
    # Test known strong combos
    test_combos = [
        ['Bollinger', 'Support_Resistance', 'Mover'],
        ['Bollinger', 'R2', 'Support_Resistance'],
        ['Trendline', 'Bollinger'],  # contradictory
        ['Squeeze', 'HL_Copy'],  # contradictory
        ['Momentum'],  # single family
        ['Bollinger', 'Support_Resistance'],
        ['Exhaustion', 'Support_Resistance'],
    ]
    
    for combo in test_combos:
        result = score_confluence(combo, verbose=True)
        print(f"Combo: {combo}")
        print(f"  Bonus: {result['bonus']:+d} pts")
        print(f"  Level: {result['level']}")
        print(f"  Strong matches: {len(result['strong_combos'])}")
        print(f"  Weak matches: {len(result['weak_combos'])}")
        print()
    
    # Test confluence zone detection
    print("Confluence Zones (coins with 3+ families):")
    zones = detect_confluence_zone(lookback_days=1)
    for zone in zones[:10]:
        print(f"  {zone.get('token', '?'):10s} | Bonus: {zone['bonus']:+3d} | Level: {zone['level']:10s} | Families: {zone.get('families', [])}")
    
    print("\n=== Test Complete ===")
