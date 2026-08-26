#!/usr/bin/env python3
"""
market_phase_gate.py — Detect current market phase from signal composition.

Reads the last N days of signals from signals_hermes_runtime.db, computes
which signal families dominate, and returns a phase classification with
per-family multipliers.

Usage:
    from market_phase_gate import get_phase_mult
    mult = get_phase_mult('Bollinger', lookback_days=3)
    # Returns 1.4 if in Range phase, 0.7 if in Trend phase, etc.

    from market_phase_gate import detect_phase
    phase = detect_phase(lookback_days=3)
    # Returns: {'phase': 'range', 'dominant_families': [...], 'confidence': 0.8}
"""

import sqlite3
import os
import time
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from paths import RUNTIME_DB, HERMES_DATA

# ── Cache ─────────────────────────────────────────────────────────────────────
_phase_cache = None
_phase_cache_time = 0
_PHASE_CACHE_TTL = 300  # 5 min cache

# ── Signal family definitions ─────────────────────────────────────────────────
FAMILY_MAP = {
    'Momentum': ['momentum', 'fast_momentum', 'mtf_momentum', 'velocity', 'phase_accel'],
    'MACD': ['hmacd', 'macd_accel', 'macd_1m', 'mtf_macd', 'macd_divergence_short', 'macd_divergence_long'],
    'Bollinger': ['bb_bounce', 'bb_bounce_short', 'bollinger_squeeze_long', 'bollinger_squeeze_short'],
    'Trend_MA': ['ma_cross', 'ma_cross_5m', 'ema9_sma20', 'ema20_50', 'ema_angle',
                  'ma_100_cross', 'ma_100_cross_long', 'ma_100_cross_short', 'ma_100_bounce'],
    'Range': ['range_finder', 'range_finder_short', 'range_breakout', 'range_breakout_short'],
    'ZScore': ['zscore_rising', 'zscore_rising_long', 'zscore_rising_short', 'hzscore', 'mtp_zscore'],
    'Exhaustion': ['exhaustion', 'return_exhaustion', 'return_exhaustion_short', 'return_exhaustion_long',
                    'spike_exhaustion_short'],
    'R2': ['r2_rev', 'r2_trend', 'r2_trend_long', 'r2_trend_short'],
    'Accelerate': ['accel_300', 'accel_300_long', 'accel_300_short', 'inverse_accel_300_long', 'inverse_accel_300_short'],
    'Squeeze': ['squeeze_cross', 'bollinger_squeeze_long', 'bollinger_squeeze_short', 'atr_compression'],
    'Trendline': ['tl_break', 'tl_break_long', 'tl_break_short', 'vortex_break_long', 'vortex_break_short'],
    'Mover': ['mover_long', 'mover_short', 'coin_tracker_hot_long', 'coin_tracker_hot_short', 'coin_tracker_hot'],
    'Pattern': ['pattern_wolf', 'pattern_micro_flag', 'pattern_channel_long', 'pattern_channel_short',
                 'hh_hl_choch', 'hh_hl_breakout', 'engulfing_long', 'engulfing_short'],
    'HL_Copy': ['hl_copy_plus', 'hl_copy_minus'],
    'Support_Resistance': ['support_resistance'],
    'Hot_Set': ['hot-set'],
    'Continuation': ['continuation_long', 'continuation_short'],
    'Wave': ['wave_catcher_long', 'wave_catcher_short', 'trend_momentum_near_sma', 'guppy'],
    'Stop_Hunt': ['stop_hunt_reversal_long', 'liquidation_hunt_long', 'liquidation_hunt_short'],
    'Confluence': ['signal_confluence'],
    'Volume': ['volume_hl', 'pump_catcher_long'],
    'ATR': ['atr_spike_long'],
}

# Reverse lookup: signal_type → family
_SIGNAL_TO_FAMILY = {}
for _fam, _members in FAMILY_MAP.items():
    for _m in _members:
        _SIGNAL_TO_FAMILY[_m] = _fam


def signal_family(signal_type: str) -> str:
    """Get the family for a signal type."""
    # Strip direction suffixes for lookup
    base = signal_type.replace('_long', '').replace('_short', '').replace('+', '').replace('-', '')
    return _SIGNAL_TO_FAMILY.get(base, _SIGNAL_TO_FAMILY.get(signal_type, 'Other'))


# ── Phase Detection ───────────────────────────────────────────────────────────

def detect_phase(lookback_days: int = 3) -> dict:
    """
    Detect the current market phase from recent signal composition.
    
    Returns:
        {
            'phase': str,           # 'trend_building', 'explosion', 'range', 'defensive', 'mover_hunting', 'quiet'
            'dominant_families': list,  # top 3 families by activity
            'family_pcts': dict,    # family → percentage of total signals
            'confidence': float,    # 0-1, how confident in phase detection
            'total_signals': int,   # total signals in lookback window
        }
    """
    global _phase_cache, _phase_cache_time
    
    now = time.time()
    if _phase_cache and (now - _phase_cache_time) < _PHASE_CACHE_TTL:
        return _phase_cache
    
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        rows = conn.execute('''
            SELECT signal_type, created_at
            FROM signals
            WHERE created_at >= ?
            ORDER BY created_at ASC
        ''', (cutoff,)).fetchall()
        conn.close()
    except Exception:
        return {'phase': 'quiet', 'dominant_families': [], 'family_pcts': {}, 'confidence': 0.0, 'total_signals': 0}
    
    if not rows:
        return {'phase': 'quiet', 'dominant_families': [], 'family_pcts': {}, 'confidence': 0.0, 'total_signals': 0}
    
    # Count by family
    family_counts = Counter()
    for sig_type, _ in rows:
        fam = signal_family(sig_type)
        family_counts[fam] += 1
    
    total = sum(family_counts.values())
    if total < 50:
        return {'phase': 'quiet', 'dominant_families': [], 'family_pcts': {}, 'confidence': 0.0, 'total_signals': total}
    
    # Compute percentages
    family_pcts = {fam: (cnt / total * 100) for fam, cnt in family_counts.items()}
    dominant = [fam for fam, _ in family_counts.most_common(3)]
    
    # Classify phase based on dominant families
    phase, confidence = _classify_phase(family_pcts, dominant)
    
    result = {
        'phase': phase,
        'dominant_families': dominant,
        'family_pcts': family_pcts,
        'confidence': confidence,
        'total_signals': total,
    }
    
    _phase_cache = result
    _phase_cache_time = now
    
    return result


def _classify_phase(family_pcts: dict, dominant: list) -> tuple:
    """Classify phase based on family percentages. Returns (phase, confidence)."""
    
    # Check for specific signatures
    zscore_pct = family_pcts.get('ZScore', 0)
    squeeze_pct = family_pcts.get('Squeeze', 0)
    trendline_pct = family_pcts.get('Trendline', 0)
    accelerate_pct = family_pcts.get('Accelerate', 0)
    momentum_pct = family_pcts.get('Momentum', 0)
    bollinger_pct = family_pcts.get('Bollinger', 0)
    range_pct = family_pcts.get('Range', 0)
    exhaustion_pct = family_pcts.get('Exhaustion', 0)
    hl_copy_pct = family_pcts.get('HL_Copy', 0)
    sr_pct = family_pcts.get('Support_Resistance', 0)
    mover_pct = family_pcts.get('Mover', 0)
    hotset_pct = family_pcts.get('Hot_Set', 0)
    r2_pct = family_pcts.get('R2', 0)
    
    # Phase classification rules (ordered by priority)
    
    # 1. ZScore Surge: ZScore dominates (>30%)
    if zscore_pct > 30:
        return 'explosion', min(1.0, zscore_pct / 50)
    
    # 2. Trend Building: Trendline + Squeeze + Accelerate dominate
    trend_family_pct = trendline_pct + squeeze_pct + accelerate_pct
    if trend_family_pct > 40 and dominant[0] in ['Trendline', 'Squeeze', 'Accelerate']:
        return 'trend_building', min(1.0, trend_family_pct / 60)
    
    # 3. Momentum Explosion: Hot_Set + Accelerate + Momentum dominate
    momentum_family_pct = hotset_pct + accelerate_pct + momentum_pct
    if momentum_family_pct > 35 and any(d in ['Hot_Set', 'Accelerate', 'Momentum'] for d in dominant[:2]):
        return 'explosion', min(1.0, momentum_family_pct / 50)
    
    # 4. Range-Bound: Bollinger + Range dominate
    range_family_pct = bollinger_pct + range_pct
    if range_family_pct > 30 and exhaustion_pct < 10:
        return 'range', min(1.0, range_family_pct / 50)
    
    # 5. Exhaustion/Range: Bollinger + Range + Exhaustion
    if range_family_pct > 25 and exhaustion_pct > 5:
        return 'range', min(1.0, (range_family_pct + exhaustion_pct) / 50)
    
    # 6. Defensive: HL_Copy + Support/Resistance dominate
    defensive_pct = hl_copy_pct + sr_pct
    if defensive_pct > 35 and dominant[0] in ['HL_Copy', 'Support_Resistance']:
        return 'defensive', min(1.0, defensive_pct / 50)
    
    # 7. Mover Hunting: Mover family dominates
    if mover_pct > 20 and dominant[0] == 'Mover':
        return 'mover_hunting', min(1.0, mover_pct / 40)
    
    # 8. Mixed/Uncertain — use dominant family
    if dominant:
        top_pct = family_pcts.get(dominant[0], 0)
        if top_pct > 25:
            # Map dominant family to a phase
            family_to_phase = {
                'Trendline': 'trend_building',
                'Squeeze': 'trend_building',
                'Accelerate': 'trend_building',
                'Bollinger': 'range',
                'Range': 'range',
                'HL_Copy': 'defensive',
                'Support_Resistance': 'defensive',
                'Mover': 'mover_hunting',
                'ZScore': 'explosion',
                'Hot_Set': 'explosion',
                'Momentum': 'trend_building',
                'Exhaustion': 'range',
                'R2': 'trend_building',
            }
            phase = family_to_phase.get(dominant[0], 'quiet')
            return phase, min(0.6, top_pct / 50)
    
    return 'quiet', 0.3


# ── Phase Multipliers ─────────────────────────────────────────────────────────

# Per-phase, per-family multipliers based on cluster analysis correlations.
# Positive correlations → boost. Negative correlations → penalty.
PHASE_MULTS = {
    'trend_building': {
        'Accelerate': 1.3,      # early warning — boost
        'Momentum': 1.2,        # building breakout — boost
        'Squeeze': 1.2,         # compression detected — boost
        'Trendline': 1.1,       # trend signals work — slight boost
        'R2': 1.1,              # trend strength — slight boost
        'Bollinger': 0.7,       # don't fade trends — penalty (r=-0.386)
        'Exhaustion': 0.5,      # move hasn't happened yet — penalty
        'HL_Copy': 0.8,         # not defensive mode — slight penalty (r=-0.374)
        'Range': 0.7,           # not ranging — penalty
    },
    'explosion': {
        'ZScore': 0.8,          # the event is NOW, late entry — penalty
        'Hot_Set': 1.0,         # concurrent — neutral
        'Mover': 1.2,           # ride the momentum — boost
        'R2': 1.3,              # trend strength confirmed — boost
        'Continuation': 1.2,    # ride the wave — boost
        'Bollinger': 0.6,       # don't fade explosions — penalty
        'Exhaustion': 0.5,      # too early for exhaustion — penalty
        'Trendline': 0.8,       # trend signals lag — slight penalty
    },
    'range': {
        'Bollinger': 1.4,       # mean reversion works — big boost (r=+0.738)
        'Range': 1.3,           # range signals accurate — boost
        'Support_Resistance': 1.2,  # key levels matter — boost
        'Exhaustion': 1.1,      # moves are tired — slight boost
        'Trendline': 0.6,       # false breakouts in range — penalty (r=-0.386)
        'Momentum': 0.7,        # momentum fades in range — penalty
        'Accelerate': 0.7,      # acceleration fails in range — penalty
        'HL_Copy': 0.9,         # neutral to slight penalty
    },
    'defensive': {
        'HL_Copy': 1.3,         # follow smart money — boost
        'Support_Resistance': 1.2,  # key levels matter — boost
        'Exhaustion': 1.1,      # moves are tired — slight boost
        'Stop_Hunt': 1.1,       # stop hunts common in chop — slight boost
        'Momentum': 0.6,        # choppy market kills momentum — penalty
        'Trendline': 0.5,       # false breakouts — penalty (r=-0.374)
        'Squeeze': 0.7,         # not compression mode — penalty (r=-0.266)
        'Accelerate': 0.7,      # no clear direction — penalty
    },
    'mover_hunting': {
        'Mover': 1.3,           # ride the movers — boost
        'R2': 1.2,              # trend strength helps — boost
        'Support_Resistance': 1.1,  # key levels for entries — slight boost
        'HL_Copy': 1.1,         # copy trading active — slight boost
        'Bollinger': 0.8,       # mean reversion less reliable — slight penalty
        'Trendline': 0.8,       # less reliable — slight penalty
    },
    'quiet': {
        # No strong phase — use neutral multipliers (all 1.0)
    },
}


def get_phase_mult(family: str, phase: str = None, lookback_days: int = 3) -> float:
    """
    Get the phase-specific multiplier for a signal family.
    
    Args:
        family: Signal family name (e.g., 'Bollinger', 'Trendline')
        phase: Optional pre-computed phase. If None, detects current phase.
        lookback_days: Days of signal history to use for phase detection.
    
    Returns:
        float multiplier (0.5 to 1.5 range typically)
    """
    if phase is None:
        phase_info = detect_phase(lookback_days)
        phase = phase_info['phase']
    
    phase_mults = PHASE_MULTS.get(phase, {})
    return phase_mults.get(family, 1.0)  # default: no multiplier


def get_phase_info(lookback_days: int = 3) -> dict:
    """Get full phase info including multipliers for logging."""
    info = detect_phase(lookback_days)
    info['multipliers'] = PHASE_MULTS.get(info['phase'], {})
    return info


# ── Inverse Correlation Guard ─────────────────────────────────────────────────

# Families that are inversely correlated (from cluster analysis).
# When one dominates, the other should be penalized.
INVERSE_FAMILIES = {
    'Trendline': ['Bollinger', 'HL_Copy'],      # r=-0.386, r=-0.374
    'Bollinger': ['Trendline'],                   # r=-0.386
    'Squeeze': ['HL_Copy'],                       # r=-0.266
    'HL_Copy': ['Trendline', 'Squeeze'],          # r=-0.374, r=-0.266
    'Momentum': ['Exhaustion'],                   # momentum wins when exhaustion loses
}


def inverse_penalty(family: str, dominant_families: list, threshold: float = 15.0) -> float:
    """
    Return penalty multiplier if this family contradicts the dominant families.
    
    Args:
        family: Signal family to check
        dominant_families: List of dominant families in current market
        threshold: Minimum % a family must have to be considered "dominant" (default 15%)
    
    Returns:
        float: 0.5 if contradicting, 1.0 if not
    """
    for dom in dominant_families:
        if dom in INVERSE_FAMILIES and family in INVERSE_FAMILIES[dom]:
            return 0.5  # 50% penalty — contradicting the market
    return 1.0


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Market Phase Gate — Self Test ===\n")
    
    info = get_phase_info()
    print(f"Current Phase: {info['phase']}")
    print(f"Confidence: {info['confidence']:.2f}")
    print(f"Total Signals: {info['total_signals']}")
    print(f"Dominant Families: {info['dominant_families']}")
    print(f"\nFamily Percentages:")
    for fam, pct in sorted(info['family_pcts'].items(), key=lambda x: -x[1])[:10]:
        print(f"  {fam:25s} {pct:5.1f}%")
    
    print(f"\nPhase Multipliers:")
    for fam, mult in sorted(info.get('multipliers', {}).items(), key=lambda x: -x[1]):
        direction = '↑' if mult > 1.0 else ('↓' if mult < 1.0 else '→')
        print(f"  {fam:25s} {mult:.1f}x {direction}")
    
    # Test inverse penalties
    print(f"\nInverse Penalties (dominant: {info['dominant_families']}):")
    for fam in info['dominant_families']:
        for test_fam in ['Trendline', 'Bollinger', 'Squeeze', 'HL_Copy']:
            pen = inverse_penalty(test_fam, info['dominant_families'])
            if pen < 1.0:
                print(f"  {test_fam} vs {fam}: {pen}x penalty")
    
    print("\n=== Test Complete ===")
