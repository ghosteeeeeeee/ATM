#!/usr/bin/env python3
"""
signal_lifecycle_filter.py — Signal Lifecycle Filters based on cluster analysis.

Tags signals as 'early', 'concurrent', or 'lagging' based on when they
appear relative to market moves. Adjusts SL/TP multipliers accordingly.

From cluster analysis (plans/signal-cluster-analysis-2026-08-26.md):
- EARLY signals (Accelerate, Momentum, Trendline): fire 2-3 days BEFORE big moves
- CONCURRENT signals (ZScore, R2, Hot_Set): fire DURING the event
- LAGGING signals (Exhaustion, Stop_Hunt): fire AFTER the move completes

Usage:
    from signal_lifecycle_filter import get_lifecycle_params
    params = get_lifecycle_params('accel_300_long')
    # Returns: {'role': 'early', 'sl_mult': 1.5, 'tp_mult': 2.0, 'hold_time': '3-5d'}

    from signal_lifecycle_filter import get_lifecycle_mult
    mult = get_lifecycle_mult('bb_bounce_short', 'LONG')
    # Returns: 0.85 (penalty for lagging signal)
"""

# ── Signal Lifecycle Roles ────────────────────────────────────────────────────
# From cluster analysis: which signals are early/concurrent/lagging

SIGNAL_LIFECYCLE = {
    # ── EARLY: Expect 1-3 day delay before profit ──────────────────────────
    # These fire BEFORE the big move. Need wider SL (room to develop).
    'accel_300_long': 'early',
    'accel_300_short': 'early',
    'inverse_accel_300_long': 'early',
    'inverse_accel_300_short': 'early',
    'momentum': 'early',
    'fast_momentum': 'early',
    'mtf_momentum': 'early',
    'velocity': 'early',
    'phase_accel': 'early',
    'squeeze_cross': 'early',
    'bollinger_squeeze_long': 'early',
    'bollinger_squeeze_short': 'early',
    'atr_compression': 'early',
    
    # ── CONCURRENT: Expect immediate move ──────────────────────────────────
    # These fire DURING the event. Normal SL/TP.
    'zscore_rising_long': 'concurrent',
    'zscore_rising_short': 'concurrent',
    'hzscore': 'concurrent',
    'mtp_zscore': 'concurrent',
    'r2_trend_long': 'concurrent',
    'r2_trend_short': 'concurrent',
    'r2_rev': 'concurrent',
    'hot-set': 'concurrent',
    'tl_break_long': 'concurrent',
    'tl_break_short': 'concurrent',
    'vortex_break_long': 'concurrent',
    'vortex_break_short': 'concurrent',
    'range_breakout': 'concurrent',
    'range_breakout_short': 'concurrent',
    'ma_100_cross': 'concurrent',
    'ma_100_cross_long': 'concurrent',
    'ma_100_cross_short': 'concurrent',
    'ma_cross': 'concurrent',
    'ma_cross_5m': 'concurrent',
    'ema9_sma20': 'concurrent',
    'ema20_50': 'concurrent',
    'continuation_long': 'concurrent',
    'continuation_short': 'concurrent',
    'wave_catcher_long': 'concurrent',
    'wave_catcher_short': 'concurrent',
    'trend_momentum_near_sma': 'concurrent',
    'coin_tracker_hot_long': 'concurrent',
    'coin_tracker_hot_short': 'concurrent',
    'mover_long': 'concurrent',
    'mover_short': 'concurrent',
    'signal_confluence': 'concurrent',
    'support_resistance': 'concurrent',
    'hl_copy_plus': 'concurrent',
    'hl_copy_minus': 'concurrent',
    
    # ── CONCURRENT: Exhaustion fires DURING events (auditor verified) ──────
    'return_exhaustion_long': 'concurrent',
    'return_exhaustion_short': 'concurrent',
    'spike_exhaustion_short': 'concurrent',
    'exhaustion': 'concurrent',
    'stop_hunt_reversal_long': 'lagging',
    'liquidation_hunt_long': 'lagging',
    'liquidation_hunt_short': 'lagging',
    'bb_bounce': 'lagging',         # mean reversion after move
    'bb_bounce_short': 'lagging',   # mean reversion after move
    'macd_divergence_long': 'lagging',
    'macd_divergence_short': 'lagging',
    'slow_grind_short': 'lagging',
}

# Strip suffixes for lookup
_SUFFIXES = ['_long', '_short', '+', '-']

def _normalize_signal(signal_type: str) -> str:
    """Strip direction suffixes for lifecycle lookup."""
    s = signal_type.lower()
    for suffix in _SUFFIXES:
        s = s.replace(suffix, '')
    return s

def get_lifecycle_role(signal_type: str) -> str:
    """
    Get the lifecycle role for a signal type.
    
    Returns: 'early', 'concurrent', 'lagging', or 'unknown'
    """
    # Try exact match first
    if signal_type in SIGNAL_LIFECYCLE:
        return SIGNAL_LIFECYCLE[signal_type]
    
    # Try normalized lookup
    normalized = _normalize_signal(signal_type)
    if normalized in SIGNAL_LIFECYCLE:
        return SIGNAL_LIFECYCLE[normalized]
    
    # Check if any key starts with the normalized name
    for key, role in SIGNAL_LIFECYCLE.items():
        if _normalize_signal(key) == normalized:
            return role
    
    return 'concurrent'  # default: treat unknown as concurrent


# ── Lifecycle-Specific Parameters ─────────────────────────────────────────────

LIFECYCLE_PARAMS = {
    'early': {
        'sl_mult': 1.5,       # wider SL — needs room to develop (2-3 days)
        'tp_mult': 2.0,       # bigger TP — bigger move expected
        'hold_time': '3-5d',  # longer hold period
        'entry_scale': 'scale_in',  # scale in over 2-3 entries
        'score_mult': 0.9,    # slight score penalty (early = uncertain timing)
        'description': 'Early warning — move expected in 1-3 days',
    },
    'concurrent': {
        'sl_mult': 1.0,       # normal SL
        'tp_mult': 1.5,       # normal TP
        'hold_time': '1-2d',  # normal hold period
        'entry_scale': 'single',  # single entry
        'score_mult': 1.0,    # no score adjustment
        'description': 'Concurrent — move happening now',
    },
    'lagging': {
        'sl_mult': 0.8,       # tight SL — move is tired, catch reversal fast
        'tp_mult': 0.8,       # smaller TP — limited upside
        'hold_time': 'hours', # short hold period
        'entry_scale': 'single',  # single entry, quick exit
        'score_mult': 0.85,   # score penalty (lagging = risky)
        'description': 'Lagging — move exhausted, reversal risk',
    },
    'unknown': {
        'sl_mult': 1.0,
        'tp_mult': 1.0,
        'hold_time': '1-2d',
        'entry_scale': 'single',
        'score_mult': 1.0,
        'description': 'Unknown lifecycle role — use defaults',
    },
}


def get_lifecycle_params(signal_type: str) -> dict:
    """
    Get lifecycle parameters for a signal type.
    
    Returns:
        {
            'role': str,           # 'early', 'concurrent', 'lagging'
            'sl_mult': float,      # SL multiplier (1.5 for early, 0.8 for lagging)
            'tp_mult': float,      # TP multiplier (2.0 for early, 0.8 for lagging)
            'hold_time': str,      # Expected hold period
            'entry_scale': str,    # 'scale_in' or 'single'
            'score_mult': float,   # Score adjustment (0.9 for early, 0.85 for lagging)
            'description': str,    # Human-readable description
        }
    """
    role = get_lifecycle_role(signal_type)
    params = LIFECYCLE_PARAMS.get(role, LIFECYCLE_PARAMS['unknown']).copy()
    params['role'] = role
    return params


def get_lifecycle_mult(signal_type: str, direction: str = None) -> float:
    """
    Get a score multiplier based on lifecycle role.
    
    Early signals get slight penalty (uncertain timing).
    Lagging signals get bigger penalty (reversal risk).
    Concurrent signals are neutral.
    
    Returns:
        float: score multiplier (0.85 to 1.0)
    """
    role = get_lifecycle_role(signal_type)
    params = LIFECYCLE_PARAMS.get(role, LIFECYCLE_PARAMS['unknown'])
    return params['score_mult']


def get_sl_tp_adjustment(signal_type: str, base_sl: float, base_tp: float) -> tuple:
    """
    Get adjusted SL/TP based on lifecycle role.
    
    Args:
        signal_type: Signal type name
        base_sl: Base SL percentage (e.g., 1.2)
        base_tp: Base TP percentage (e.g., 2.5)
    
    Returns:
        (adjusted_sl, adjusted_tp) tuple
    """
    params = get_lifecycle_params(signal_type)
    adjusted_sl = base_sl * params['sl_mult']
    adjusted_tp = base_tp * params['tp_mult']
    return adjusted_sl, adjusted_tp


# ── Lifecycle Stats ───────────────────────────────────────────────────────────

def get_lifecycle_stats() -> dict:
    """Get counts of signals by lifecycle role."""
    stats = {'early': 0, 'concurrent': 0, 'lagging': 0, 'unknown': 0}
    for signal_type in SIGNAL_LIFECYCLE:
        role = SIGNAL_LIFECYCLE[signal_type]
        stats[role] = stats.get(role, 0) + 1
    return stats


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Signal Lifecycle Filter — Self Test ===\n")
    
    # Test role lookup
    test_signals = [
        'accel_300_long', 'accel_300_short', 'momentum', 'fast_momentum',
        'zscore_rising_long', 'zscore_rising_short', 'r2_trend_long',
        'hot-set', 'tl_break_long', 'vortex_break_short',
        'bb_bounce', 'bb_bounce_short', 'return_exhaustion_long',
        'spike_exhaustion_short', 'macd_divergence_long',
        'stop_hunt_reversal_long', 'liquidation_hunt_short',
        'hl_copy_plus', 'coin_tracker_hot_long', 'support_resistance',
        'ma_100_cross_long', 'continuation_long', 'wave_catcher_long',
    ]
    
    print("Role Lookup:")
    print(f"  {'Signal':30s} | {'Role':12s} | {'SL Mult':>7s} | {'TP Mult':>7s} | {'Score':>5s}")
    print("  " + "-"*75)
    
    for sig in test_signals:
        params = get_lifecycle_params(sig)
        print(f"  {sig:30s} | {params['role']:12s} | {params['sl_mult']:7.1f} | {params['tp_mult']:7.1f} | {params['score_mult']:5.2f}")
    
    # Test SL/TP adjustment
    print("\nSL/TP Adjustment (base SL=1.2%, TP=2.5%):")
    base_sl, base_tp = 1.2, 2.5
    for sig in ['accel_300_long', 'zscore_rising_long', 'bb_bounce', 'r2_trend_long']:
        adj_sl, adj_tp = get_sl_tp_adjustment(sig, base_sl, base_tp)
        print(f"  {sig:30s} → SL: {adj_sl:.1f}% | TP: {adj_tp:.1f}%")
    
    # Stats
    stats = get_lifecycle_stats()
    print(f"\nSignal Counts by Role:")
    for role, count in stats.items():
        print(f"  {role:12s}: {count}")
    
    print("\n=== Test Complete ===")
