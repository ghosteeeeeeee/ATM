#!/usr/bin/env python3
"""
volatility_gate_v2 — Enhanced volatility gate with signal clustering integration.

Combines:
1. Volatility regime (FLAT/NORMAL/HIGH/EXTREME) from ATR%
2. Market phase (trend_building/explosion/range/defensive) from signal composition
3. Signal lifecycle roles (early/concurrent/lagging)
4. Inverse correlation penalties

Thesis: Signal effectiveness depends on BOTH volatility regime AND market phase.
- Bollinger bounces work in FLAT + Range phase
- Trendline breaks work in NORMAL + Trend phase
- Mover signals work in HIGH + Explosion phase
- Exhaustion works in any phase when moves are tired

Usage:
    from volatility_gate_v2 import should_trade_v2
    result = should_trade_v2('SOL', 'bb_bounce+')
    # Returns: ('TRADE', {'regime': 'FLAT', 'phase': 'range', 'combined_mult': 1.4})

    from volatility_gate_v2 import get_combined_multiplier
    mult = get_combined_multiplier('bb_bounce+', 'FLAT', 'range')
    # Returns: 1.4 (Bollinger boosted in FLAT + Range)
"""

import sys, os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import HERMES_DATA
import sqlite3

# ── Import signal clustering modules ─────────────────────────────────────────
try:
    from market_phase_gate import detect_phase, signal_family, get_phase_mult, inverse_penalty
    from signal_lifecycle_filter import get_lifecycle_params, get_lifecycle_mult
    _CLUSTERING_ENABLED = True
except ImportError:
    _CLUSTERING_ENABLED = False

# ── Original volatility regime signal sets (from volatility_gate.py) ──────────
# Kept for backward compatibility and fallback

REGIME_SIGNALS = {
    'FLAT': {
        'bb_bounce', 'bb_bounce+',
        'bb_bounce+,range_finder+',
        'trend_momentum_near_sma',
        'hzscore', 'range_finder',
        'accel-300', 'accel-300-',
        'slow-grind-',
        'hl_copy_trader',
        'stop_hunt_reversal_long', 'stop_hunt_reversal_long+',
        'return_exhaustion_long',
        'spike_exhaustion_short', 'spike_exhaustion_short-',
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',
        'macd-div', 'macd-div+', 'macd-div-',
        'confluence+', 'confluence-',
        'range-reversion-long+', 'range-reversion-long',  # mean reversion LONG — buy at range bottom
    },
    'NORMAL': {
        'pump-catcher+', 'pump-catcher-',
        'bb_bounce', 'bb_bounce+',
        'bb_bounce+,range_finder+', 'bb_bounce+,hzscore+',
        'bb-bounce-short,hzscore-',
        'bb-bounce-short',
        'tl_break', 'tl_break_long', 'tl_break_short',
        'trend_momentum_near_sma',
        'hzscore', 'range_finder', 'range_breakout',
        'accel-300', 'accel-300-',
        'range_breakout+', 'range_breakout_short',
        'r2-trend-long', 'r2l',
        'r2-trend-short',
        'slow-grind-',
        'wave_catcher', 'wave_catcher+', 'wave_catcher-',
        'mover', 'mover+', 'mover-',
        'ct-hot', 'ct-hot+', 'ct-hot-',
        'hl_copy_trader',
        'continuation', 'continuation+',
        'stop_hunt_reversal_long', 'stop_hunt_reversal_long+',
        'return_exhaustion_long',
        'spike_exhaustion_short', 'spike_exhaustion_short-',
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',
        'macd-div', 'macd-div+', 'macd-div-',
        'confluence+', 'confluence-',
        'range-reversion-long+', 'range-reversion-long',  # mean reversion LONG — buy at range bottom
    },
    'HIGH': {
        'pump-catcher+', 'pump-catcher-',
        'bb_bounce', 'bb_bounce+',
        'bb_bounce+,range_finder+', 'bb_bounce+,hzscore+',
        'tl_break', 'tl_break_long', 'tl_break_short',
        'accel-300-vel',
        'continuation', 'continuation+',
        'hzscore', 'range_finder',
        'accel-300', 'accel-300-',
        'range_breakout+', 'range_breakout_short',
        'wave_catcher', 'wave_catcher+', 'wave_catcher-',
        'r2-trend-long', 'r2-trend-short',
        'slow-grind-',
        'mover', 'mover+', 'mover-',
        'ct-hot', 'ct-hot+', 'ct-hot-',
        'hl_copy_trader',
        'stop_hunt_reversal_long', 'stop_hunt_reversal_long+',
        'return_exhaustion_long',
        'spike_exhaustion_short', 'spike_exhaustion_short-',
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',
        'confluence+', 'confluence-',
        'macd-div', 'macd-div+', 'macd-div-',
        'range-reversion-long+', 'range-reversion-long',  # mean reversion LONG — buy at range bottom
    },
    'EXTREME': {
        'continuation+,hzscore+', 'hzscore+,mover+',
        'mover+', 'mover-',
        'bb_bounce',
        'wave_catcher', 'wave_catcher+', 'wave_catcher-',
        'ct-hot', 'ct-hot+', 'ct-hot-',
        'hl_copy_trader',
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',
        'tl_break', 'tl_break_long', 'tl_break_short',
        'confluence+', 'confluence-',
        'macd-div', 'macd-div+', 'macd-div-',
    },
}


# ── Volatility-Phase Combined Multipliers ─────────────────────────────────────
# From cluster analysis: signal effectiveness varies by BOTH volatility AND phase.
# This matrix defines boost/penalty for each (regime, phase) combination.

VOL_PHASE_MULTS = {
    # FLAT volatility + Range phase: Mean reversion heaven
    ('FLAT', 'range'): {
        'Bollinger': 1.5,       # Bollinger bounces thrive
        'Range': 1.4,           # Range signals accurate
        'Support_Resistance': 1.3,  # Key levels matter
        'Exhaustion': 1.2,      # Moves are tired
        'Trendline': 0.5,       # False breakouts
        'Momentum': 0.6,        # Momentum fades
    },
    # FLAT volatility + Defensive phase: Choppy, follow smart money
    ('FLAT', 'defensive'): {
        'HL_Copy': 1.4,         # Follow copy traders
        'Support_Resistance': 1.3,
        'Bollinger': 1.1,       # Slight boost
        'Trendline': 0.5,       # False breakouts
        'Momentum': 0.5,        # Choppy kills momentum
    },
    # NORMAL volatility + Trend Building: Breakout forming
    ('NORMAL', 'trend_building'): {
        'Accelerate': 1.4,      # Early warning
        'Momentum': 1.3,        # Building breakout
        'Squeeze': 1.3,         # Compression detected
        'Trendline': 1.2,       # Trend signals work
        'Bollinger': 0.6,       # Don't fade trends
        'Exhaustion': 0.5,      # Too early
    },
    # NORMAL volatility + Range: Steady oscillation
    ('NORMAL', 'range'): {
        'Bollinger': 1.3,       # Mean reversion works
        'Range': 1.3,           # Range signals accurate
        'Trendline': 0.7,       # Mixed signals
        'Momentum': 0.8,        # Fades in range
    },
    # HIGH volatility + Explosion: Ride the momentum
    ('HIGH', 'explosion'): {
        'Mover': 1.4,           # Ride the movers
        'R2': 1.3,              # Trend strength
        'Continuation': 1.2,    # Ride the wave
        'Bollinger': 0.5,       # Don't fade explosions
        'Exhaustion': 0.4,      # Too early
    },
    # HIGH volatility + Trend Building: Breakout imminent
    ('HIGH', 'trend_building'): {
        'Accelerate': 1.3,
        'Momentum': 1.2,
        'Squeeze': 1.2,
        'Trendline': 1.1,
        'Bollinger': 0.6,
    },
    # EXTREME volatility: Storm mode — only structural signals
    ('EXTREME', '*'): {
        'Mover': 1.2,           # Ride the storm
        'HL_Copy': 1.1,         # Follow smart money
        'Continuation': 1.1,    # Ride the wave
        'Bollinger': 0.4,       # Don't fade storms
        'Trendline': 0.5,       # Structural breaks unreliable
        'Exhaustion': 0.3,      # Storms don't exhaust
    },
}


# ── Core Functions ────────────────────────────────────────────────────────────

def get_atr_pct(token):
    """Get current ATR(14) as percentage of close price for a token."""
    conn = None
    try:
        conn = sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close
            FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT 20
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 15:
            return None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()

    candles = list(reversed(rows))
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i][1], candles[i][2], candles[i-1][3]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    if len(trs) < 14:
        return None

    atr14 = sum(trs[-14:]) / 14
    close = candles[-1][3]
    if close <= 0:
        return None

    return (atr14 / close) * 100


def classify_volatility(atr_pct):
    """Classify volatility regime from ATR%."""
    if atr_pct is None:
        return 'UNKNOWN'
    if atr_pct < 0.48:
        return 'FLAT'
    elif atr_pct < 1.0:
        return 'NORMAL'
    elif atr_pct < 1.5:
        return 'HIGH'
    else:
        return 'EXTREME'


def get_current_phase():
    """Get current market phase from signal clustering."""
    if not _CLUSTERING_ENABLED:
        return 'unknown'
    try:
        info = detect_phase()
        return info.get('phase', 'unknown')
    except Exception:
        return 'unknown'


def get_vol_phase_mult(family, regime, phase):
    """Get combined multiplier from volatility regime + market phase."""
    # Check specific (regime, phase) combination
    key = (regime, phase)
    if key in VOL_PHASE_MULTS:
        return VOL_PHASE_MULTS[key].get(family, 1.0)
    
    # Check wildcard (regime, '*') for EXTREME
    wildcard_key = (regime, '*')
    if wildcard_key in VOL_PHASE_MULTS:
        return VOL_PHASE_MULTS[wildcard_key].get(family, 1.0)
    
    # No specific multiplier — use phase-only multiplier
    if _CLUSTERING_ENABLED:
        try:
            return get_phase_mult(family, phase)
        except Exception:
            pass
    
    return 1.0


def get_combined_multiplier(signal_type, regime, phase):
    """
    Get combined multiplier from volatility + phase + lifecycle.
    
    This is the core innovation: instead of just checking if a signal
    "works" in a regime, we compute a multiplier that considers:
    1. Volatility regime fit
    2. Market phase fit
    3. Signal lifecycle role
    4. Inverse correlations
    
    Returns: float multiplier (0.3 to 2.0 range)
    """
    mult = 1.0
    family = None
    
    # 1. Volatility-phase combined multiplier
    if _CLUSTERING_ENABLED:
        try:
            family = signal_family(signal_type)
            vol_phase_mult = get_vol_phase_mult(family, regime, phase)
            mult *= vol_phase_mult
        except Exception:
            pass
    
    # 2. Lifecycle multiplier
    if _CLUSTERING_ENABLED:
        try:
            lifecycle_mult = get_lifecycle_mult(signal_type)
            mult *= lifecycle_mult
        except Exception:
            pass
    
    # 3. Inverse correlation penalty (uses cached family from step 1)
    if _CLUSTERING_ENABLED and family:
        try:
            info = detect_phase()
            dom_fams = info.get('dominant_families', [])
            inv_mult = inverse_penalty(family, dom_fams)
            mult *= inv_mult
        except Exception:
            pass
    
    # Clamp to reasonable range (prevent extreme multipliers from crushing scores)
    return max(0.3, min(2.0, mult))


def should_trade_v2(token, signal=None):
    """
    Enhanced entry point: combines volatility regime + market phase + clustering.
    
    Returns: ('TRADE', info_dict) or ('SKIP', reason)
    """
    atr_pct = get_atr_pct(token)
    if atr_pct is None:
        return ('SKIP', 'no_data')
    
    regime = classify_volatility(atr_pct)
    phase = get_current_phase()
    
    info = {
        'regime': regime,
        'phase': phase,
        'atr_pct': atr_pct,
    }
    
    # If signal is provided, check if it works in this regime
    if signal:
        # First check original volatility gate
        regime_sigs = REGIME_SIGNALS.get(regime, set())
        works_in_regime = False
        
        if signal in regime_sigs:
            works_in_regime = True
        else:
            sig_parts = signal.split(',')
            for part in sig_parts:
                part = part.strip()
                if part in regime_sigs:
                    works_in_regime = True
                    break
                base = part.rstrip('+-')
                if base in regime_sigs:
                    works_in_regime = True
                    break
                base_no_num = re.sub(r'\d+$', '', base)
                if base_no_num in regime_sigs:
                    works_in_regime = True
                    break
        
        if not works_in_regime:
            if regime == 'EXTREME':
                return ('SKIP', f'storm: ATR={atr_pct:.4f}% > 1.5% (signal not suited)')
            else:
                return ('SKIP', f'{signal} not suited for {regime} (ATR={atr_pct:.4f}%)')
        
        # Compute combined multiplier
        combined_mult = get_combined_multiplier(signal, regime, phase)
        info['combined_mult'] = combined_mult
        info['signal'] = signal
        
        # Apply multiplier to confidence (if available)
        # A mult > 1.0 means this is a high-probability setup
        # A mult < 1.0 means this is a lower-probability setup
    
    # EXTREME regime: skip unless specific structural signals
    if regime == 'EXTREME' and not signal:
        return ('SKIP', f'storm: ATR={atr_pct:.4f}% > 1.5%')
    
    return ('TRADE', info)


def get_sl_multiplier_v2(atr_pct, signal_type=None):
    """
    Enhanced SL multiplier: combines volatility + lifecycle.
    
    Volatility SL:
    - FLAT: 0.8x (tighter, range-bound)
    - NORMAL: 1.0x (standard)
    - HIGH: 1.3x (wider, more movement)
    - EXTREME: 0 (don't trade)
    
    Lifecycle SL (multiplied on top):
    - Early: 1.5x (needs room)
    - Concurrent: 1.0x (standard)
    - Lagging: 0.8x (tight, catch reversal)
    """
    # Base volatility multiplier
    if atr_pct is None:
        vol_mult = 1.0
    elif atr_pct < 0.48:
        vol_mult = 0.8    # FLAT: tighter
    elif atr_pct < 1.0:
        vol_mult = 1.0    # NORMAL: standard
    elif atr_pct < 1.5:
        vol_mult = 1.3    # HIGH: wider
    else:
        vol_mult = 0      # EXTREME: don't trade
    
    # Lifecycle multiplier
    lifecycle_mult = 1.0
    if signal_type and _CLUSTERING_ENABLED:
        try:
            params = get_lifecycle_params(signal_type)
            lifecycle_mult = params.get('sl_mult', 1.0)
        except Exception:
            pass
    
    return vol_mult * lifecycle_mult


def get_tp_multiplier_v2(atr_pct, signal_type=None):
    """
    Enhanced TP multiplier: combines volatility + lifecycle.
    """
    # Base volatility multiplier
    if atr_pct is None:
        vol_mult = 1.0
    elif atr_pct < 0.48:
        vol_mult = 0.8    # FLAT: smaller moves
    elif atr_pct < 1.0:
        vol_mult = 1.0    # NORMAL: standard
    elif atr_pct < 1.5:
        vol_mult = 1.3    # HIGH: bigger moves
    else:
        vol_mult = 0      # EXTREME: don't trade
    
    # Lifecycle multiplier
    lifecycle_mult = 1.0
    if signal_type and _CLUSTERING_ENABLED:
        try:
            params = get_lifecycle_params(signal_type)
            lifecycle_mult = params.get('tp_mult', 1.0)
        except Exception:
            pass
    
    return vol_mult * lifecycle_mult


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Volatility Gate V2 — Self Test ===\n")
    
    test_tokens = ['BTC', 'ETH', 'SOL', 'ALGO', 'CC', 'AVNT']
    test_signals = ['bb_bounce+', 'tl_break_long', 'accel-300', 'mover+', 'return_exhaustion_long']
    
    phase = get_current_phase()
    print(f"Current Market Phase: {phase}\n")
    
    print(f"{'Token':8s} | {'ATR%':>8s} | {'Regime':8s} | {'Signal':20s} | {'Mult':>6s} | {'Decision'}")
    print("-" * 85)
    
    for tok in test_tokens:
        atr = get_atr_pct(tok)
        if atr is None:
            continue
        regime = classify_volatility(atr)
        
        for sig in test_signals[:2]:  # Test first 2 signals
            result = should_trade_v2(tok, sig)
            decision = result[0]
            info = result[1] if isinstance(result[1], dict) else {}
            mult = info.get('combined_mult', 1.0)
            
            print(f"{tok:8s} | {atr:7.4f}% | {regime:8s} | {sig:20s} | {mult:6.2f} | {decision}")
    
    # Test SL/TP adjustments
    print(f"\nSL/TP Adjustments (base SL=1.2%, TP=2.5%):")
    base_sl, base_tp = 1.2, 2.5
    for sig in ['accel_300_long', 'bb_bounce', 'mover+', 'exhaustion']:
        for atr in [0.3, 0.7, 1.2]:
            regime = classify_volatility(atr)
            sl_mult = get_sl_multiplier_v2(atr, sig)
            tp_mult = get_tp_multiplier_v2(atr, sig)
            adj_sl = base_sl * sl_mult
            adj_tp = base_tp * tp_mult
            print(f"  {sig:20s} | {regime:8s} | SL: {adj_sl:.2f}% | TP: {adj_tp:.2f}%")
    
    print("\n=== Test Complete ===")
