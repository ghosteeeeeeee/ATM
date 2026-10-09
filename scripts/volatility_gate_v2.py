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
        'squeeze-reversal+', 'squeeze-reversal-',  # BB squeeze → mean-reversion breakout
        'grind-breakout+', 'grind-breakout-',  # steady grind + late breakout
        'continuum+', 'continuum-',  # continuum score extreme signals — contrarian, works in range-bound
        'continuum-mom+', 'continuum-mom-',  # continuum momentum zone-transition — regime-agnostic
        'continuum-osc+', 'continuum-osc-',  # continuum oscillator cadence — regime-agnostic
        'continuum-trend+', 'continuum-trend-',  # continuum trendline alignment — regime-agnostic
        'oversold-bounce+',  # oversold bounce LONG — mean reversion at extreme oversold
        'ai-trader', 'ai-trader+', 'ai-trader-',  # AI-driven signal — context-aware, works in all regimes
    },
    'NORMAL': {
        'pump-catcher+', 'pump-catcher-',
        'pump-chain', 'pump-chain+', 'pump-chain-',  # chain correlation momentum (hyphen variant)
        'pump_chain', 'pump_chain+', 'pump_chain-',  # chain correlation momentum (underscore variant — actual DB values)
        'pump-chain-v5',  # V5 with velocity + continuum oscillator filters
        'pump-chain-v6+', 'pump-chain-v6-',  # V6 — NORMAL is profitable SHORT habitat (spec rev1 §6.3)
        'bb_bounce', 'bb_bounce+',
        'bb_bounce+,range_finder+', 'bb_bounce+,hzscore+',
        'bb-bounce-short,hzscore-',
        'bb-bounce-short',
        'tl_break', 'tl_break_long', 'tl_break_short',
        'trend_momentum_near_sma',
        'hzscore', 'range_finder', 'range_breakout',
        'accel-300', 'accel-300-',
        'range_breakout+', 'range_breakout_short',
        'r2-trend-short',  # R² downtrend SHORT — works in all regimes
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
        'squeeze-reversal+', 'squeeze-reversal-',  # BB squeeze → mean-reversion breakout
        'grind-breakout+', 'grind-breakout-',  # steady grind + late breakout
        'hh-hl', 'hh-hl+', 'hh-hl-',  # Structure Sniper — trend-following breakout, best in NORMAL
        'ema300-breakthrough+', 'ema300-breakthrough-',  # EMA300 breakout — 15m, trend continuation/reversal
        'trend_purity+', 'trend_purity-',  # trend following — fires in NORMAL (primary regime)
        'continuum+', 'continuum-',  # continuum score extreme signals — regime-agnostic
        'continuum-mom+', 'continuum-mom-',  # continuum momentum zone-transition — regime-agnostic
        'continuum-osc+', 'continuum-osc-',  # continuum oscillator cadence — regime-agnostic
        'continuum-trend+', 'continuum-trend-',  # continuum trendline alignment — regime-agnostic
        'mtf-regime-trend+', 'mtf-regime-trend-',  # multi-timeframe regime trend — added 2026-10-04: sync with v1 NORMAL
        'hmacd-mtf', 'hmacd_mtf', 'hmacd_mtf-+', 'hmacd-mtf-+',  # multi-timeframe MACD — added 2026-10-09: CAKE/ETH LONG blocked
        'volume-breakout-long+',  # volume-confirmed breakout LONG — added 2026-10-09: sync with v1
        'volume-breakout-short-', 'volume_breakout_short',  # volume-confirmed breakout SHORT — added 2026-10-09: BANANA SHORT blocked
        'btc-pump-rider+',  # BTC breakout → alt lagging LONG — added 2026-10-09: sync with v1
        'r2v2-long', 'r2v2-long3',  # R² trend v2 — added 2026-10-09: IOTA LONG blocked
        'bb-bounce-v2-long+', 'bb_bounce_v2_long',  # BB bounce v2 LONG — added 2026-10-09: APT LONG blocked
        'doji-bottom-long', 'doji-top', 'doji-top-short',  # doji patterns — added 2026-10-09: LTC LONG blocked
        'continuum-ma+', 'continuum-ma-',  # continuum MA crossover — momentum confirmation
        'oversold-bounce+',  # oversold bounce LONG — mean reversion at extreme oversold
        'ai-trader', 'ai-trader+', 'ai-trader-',  # AI-driven signal — context-aware, works in all regimes
    },
    'HIGH': {
        'pump-catcher+', 'pump-catcher-',
        'pump-chain', 'pump-chain+', 'pump-chain-',  # chain correlation momentum (hyphen variant)
        'pump_chain', 'pump_chain+', 'pump_chain-',  # chain correlation momentum (underscore variant — actual DB values)
        'pump-chain-v5',  # V5 with velocity + continuum oscillator filters
        'pump-chain-v6+',  # V6 LONG only — HIGH kept (gate-applied HIGH kept 14T 57.1% +$0.92); SHORT HIGH is the bleed regime (spec rev1 §6.3)
        'bb_bounce', 'bb_bounce+',
        'bb_bounce+,range_finder+', 'bb_bounce+,hzscore+',
        'tl_break', 'tl_break_long', 'tl_break_short',
        'accel-300-vel',
        'continuation', 'continuation+',
        'hzscore', 'range_finder',
        'accel-300', 'accel-300-',
        'range_breakout+', 'range_breakout_short',
        'wave_catcher', 'wave_catcher+', 'wave_catcher-',
        'r2-trend-long', 'r2-trend-short',  # R² trend detectors — LONG only in HIGH (74.1% WR)
        'r2v2-long', 'r2v2-long3',  # R² trend v2 — added 2026-10-09: IOTA LONG blocked
        'hmacd-mtf', 'hmacd_mtf', 'hmacd_mtf-+', 'hmacd-mtf-+',  # multi-timeframe MACD — added 2026-10-09
        'volume-breakout-long+',  # volume-confirmed breakout LONG — added 2026-10-09: sync with v1
        'volume-breakout-short-', 'volume_breakout_short',  # volume-confirmed breakout SHORT — added 2026-10-09
        'bb-bounce-v2-long+', 'bb_bounce_v2_long',  # BB bounce v2 LONG — added 2026-10-09
        'doji-bottom-long', 'doji-top', 'doji-top-short',  # doji patterns — added 2026-10-09
        'btc-pump-rider+',  # BTC breakout → alt lagging LONG — added 2026-10-09: sync with v1
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
        'squeeze-reversal+', 'squeeze-reversal-',  # BB squeeze → mean-reversion breakout
        'grind-breakout+', 'grind-breakout-',  # steady grind + late breakout
        'hh-hl', 'hh-hl+', 'hh-hl-',  # Structure Sniper — trend-following breakout, works in HIGH
        'ema300-breakthrough+', 'ema300-breakthrough-',  # EMA300 breakout — strong moves confirm through EMA
        # trend_purity+ REMOVED from HIGH — 33.3% WR, -$0.50 (3 trades). Wins in EXTREME (57.1%).

        'continuum+', 'continuum-',  # continuum score extreme signals — regime-agnostic
        'continuum-mom+', 'continuum-mom-',  # continuum momentum zone-transition — regime-agnostic
        'continuum-osc+', 'continuum-osc-',  # continuum oscillator cadence — regime-agnostic
        'continuum-trend+', 'continuum-trend-',  # continuum trendline alignment — regime-agnostic
        'mtf-regime-trend+', 'mtf-regime-trend-',  # multi-timeframe regime trend — added 2026-10-04: sync with v1 HIGH
        'oversold-bounce+',  # oversold bounce LONG — mean reversion at extreme oversold
        'ai-trader', 'ai-trader+', 'ai-trader-',  # AI-driven signal — context-aware, works in all regimes
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
        'pump-chain', 'pump-chain+',  # chain correlation LONG — EXTREME edge (57% WR)
        'pump_chain', 'pump_chain+',  # underscore LONG variant
        'pump-chain-v5',  # V5 — LONG killed, SHORT regime-routed via VOL_PHASE_MULTS (EXTREME Pump_Flow=0.0)
        'pump-chain-v6+', 'pump-chain-v6-',  # V6 — EXTREME carries the PnL (spec rev1 §6.3)
        # pump-chain- SHORT removed 2026-10-01 — EXTREME Pump_Flow=0.0 hard block; REGIME_SIGNALS was stale dead path
        'squeeze-reversal+', 'squeeze-reversal-',  # BB squeeze → mean-reversion breakout — works in storms
        'grind-breakout+', 'grind-breakout-',  # steady grind + late breakout — works in storms
        'ema300-breakthrough+', 'ema300-breakthrough-',  # EMA300 breakout — strong momentum confirms through EMA
        'continuum+', 'continuum-',  # continuum score extreme signals — regime-agnostic
        'continuum-mom+', 'continuum-mom-',  # continuum momentum zone-transition — regime-agnostic
        'continuum-osc+', 'continuum-osc-',  # continuum oscillator cadence — regime-agnostic
        'continuum-trend+', 'continuum-trend-',  # continuum trendline alignment — regime-agnostic
        'mtf-regime-trend+', 'mtf-regime-trend-',  # multi-timeframe regime trend — added 2026-10-04: sync with v1 EXTREME
        'r2v2-long', 'r2v2-long3',  # R² trend v2 — added 2026-10-09: LDO LONG blocked in EXTREME
        'hmacd-mtf', 'hmacd_mtf', 'hmacd_mtf-+', 'hmacd-mtf-+',  # multi-timeframe MACD — added 2026-10-09
        'volume_breakout+', 'volume_breakout-',  # volume-confirmed breakout — wins in EXTREME (67% WR)
        'volume-breakout-long+',  # volume-confirmed breakout LONG (hyphen variant) — added 2026-10-09: sync with v1
        'volume-breakout-short-', 'volume_breakout_short',  # volume-confirmed breakout SHORT — added 2026-10-09: BANANA SHORT blocked
        'bb-bounce-v2-long+', 'bb_bounce_v2_long',  # BB bounce v2 LONG — added 2026-10-09: APT LONG blocked in EXTREME
        'doji-bottom-long', 'doji-top', 'doji-top-short',  # doji patterns — added 2026-10-09
        'trend_purity+', 'trend_purity-',  # trend following — penalized in EXTREME via VOL_PHASE_MULTS (0.15x)
        'oversold-bounce+',  # oversold bounce LONG — mean reversion at extreme oversold
        'accel-300-breakout',  # ATR breakout signal — works solo, added 2026-09-23 (bug hunt: was killing PONS SHORT)
        'ai-trader', 'ai-trader+', 'ai-trader-',  # AI-driven signal — context-aware, works in all regimes
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
        'Pattern': 1.3,         # Structure Sniper thrives in trend building
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
        'Mover': 0.0,           # BLOCKED — mover+ LONG 4/7 wins EXTREME but -$0.48 lifetime. 1.2x insufficient. signal_reporter 2026-09-23
        'HL_Copy': 1.1,         # Follow smart money
        'Continuation': 1.1,    # Ride the wave
        'Bollinger': 0.4,       # Don't fade storms
        'Trendline': 0.5,       # Structural breaks unreliable
        'Exhaustion': 0.3,      # Storms don't exhaust
        'Coiled_Spring': 0.0,   # BLOCKED — 40% WR in EXTREME, only trade NORMAL
        'Accelerate': 0.0,      # BLOCKED — accel_300_v3_long 37% WR in EXTREME, wins in HIGH/NORMAL
        'EMA300_Dip': 0.0,      # BLOCKED — ema300_dip 25% WR in EXTREME, wins in HIGH/NORMAL
        'Support_Resistance': 0.0,  # BLOCKED — rs is mean-reversion, only works in NORMAL (2026-09-25)
        'Pullback_Entry_Long': 0.0,  # BLOCKED — pullback_entry+ 0% WR in EXTREME, wins in HIGH
        'Pullback_Entry': 1.0,  # OK — pullback-entry- 68% WR +$1.46 lifetime EXTREME, 64% WR +$0.43/7d. Updated 2026-09-18
        'Oversold_Bounce': 1.0,  # OK — oversold bounce LONG, mean reversion works in EXTREME (oversold = extreme)
        'Pattern': 0.3,              # PENALIZED — Structure Sniper unreliable in storms, fires on noise
        'Trend_Purity': 0.15,        # PENALIZED — trend_purity+ LONG 40% WR in EXTREME, -$0.72/7d. 0.3x insufficient (2026-09-13 brain_auditor)
        'Pump_Flow': 0.0,      # BLOCKED — pump-chain- SHORT 51.9% WR -$0.20 EXTREME (54T). Wins in NORMAL (83.3% WR). signal_reporter 2026-09-24
        'Slow_Grind': 0.0,     # BLOCKED — slow_grind 20% WR -$0.58 EXTREME (5T). Wins in NORMAL. 2026-10-01
        'Open_Skies': 0.0,     # BLOCKED — open-skies+ 25% WR -$0.46 EXTREME (4T). No winning regime. 2026-10-01
        'SMA20_Dip': 0.0,      # BLOCKED — sma20_dip 57% WR -$0.02 EXTREME (7T). Marginal. 2026-10-01
    },
    # NORMAL volatility: block signals that lose here but win in EXTREME/HIGH
    ('NORMAL', '*'): {
        'Pullback_Entry': 0.0,        # BLOCKED — pullback-entry- 0/3 (0%) -$0.37 in NORMAL 24h. All-time 48.3% WR -$0.03. 2026-09-17
        'Oversold_Bounce': 1.0,  # OK — oversold bounce LONG, mean reversion works in NORMAL
        'R2_Structural': 0.2,         # HEAVILY PENALIZED — rr-struct+ LONG 5T 40%WR -$0.49 in NORMAL (24h). Wins in HIGH (87.5% WR). Tightened from 0.5 2026-09-14
        # Open_Skies REMOVED 2026-09-12 — was 55.6% WR +$1.06 total, NORMAL was primary regime
        'Engulfing': 0.0,             # BLOCKED — engulfing 50% WR in NORMAL, wins in HIGH
        # Pump_Flow REMOVED from NORMAL block — pump-chain- SHORT 83.3% WR +$0.13 NORMAL (6T). Block was for pump-chain+ LONG only. signal_reporter 2026-09-24
        'Grind_Trend': 0.0,           # BLOCKED — grind-trend+ LONG 0%WR -$0.30 in NORMAL (5T). Wins in HIGH (57.1% WR). 2026-09-19
        'Momentum': 0.0,              # BLOCKED — momentum LONG 38.5%WR -$0.99/7d in NORMAL. Wins in EXTREME/HIGH. 2026-09-21
        'Volume': 0.0,                # BLOCKED — volume-breakout-long+ 62.5%WR -$0.05 in NORMAL (8T/30d). 0 winners 7d NORMAL. Wins in EXTREME (75%WR +$1.46). 2026-09-21
    },
    # HIGH volatility: block signals that lose here but win in EXTREME/NORMAL
    ('HIGH', '*'): {
        'Coiled_Spring': 0.0,    # BLOCKED — coiled_spring 33% WR in HIGH, wins in NORMAL
        'Trendline': 0.3,        # PENALIZED — tl_break 33% WR in HIGH, wins in NORMAL
        # Pullback_Entry REMOVED from HIGH — all-time 53.1% WR +$0.44 in HIGH (49T). Block was stale from bad 24h snapshot. signal_reporter 2026-09-19
        'Oversold_Bounce': 1.0,  # OK — oversold bounce LONG, mean reversion works in HIGH
        'R2_Structural': 0.0,    # BLOCKED — rr-struct- 4T 25%WR -$0.41 in HIGH, wins in NORMAL. Key fixed 2026-09-13 (was R2_Structural, already matched but value stands)
        'Bollinger': 0.0,        # BLOCKED — bb_bounce 50% WR in HIGH, wins in EXTREME/NORMAL
        # Accelerate REMOVED 2026-09-12 — SHORT needs HIGH regime access, EXTREME already blocked
        'Volume_Breakout': 0.0,  # BLOCKED — volume_breakout 33% WR in HIGH, wins in EXTREME
        'Breakout': 0.0,         # BLOCKED — breakout_long 33% WR in HIGH, wins in EXTREME
        'Pump_Flow': 0.5,        # PENALIZED 2026-09-22 — HIGH pump-chain+ 37% WR, pump-chain- 48% WR. Bare pump_chain 76.9% WR though.
        'Trend_Purity': 0.0,    # BLOCKED — trend_purity+ 33.3% WR in HIGH (3T, -$0.50), wins in EXTREME (57.1%)
        'Support_Resistance': 0.0,  # BLOCKED — rs mean-reversion, only works in NORMAL (2026-09-25)
    },
}


# ── Per-Signal-Type Overrides ────────────────────────────────────────────────
# FAMILY-level blocks (above) are too coarse. When a specific signal variant
# (e.g. accel_300_v3_long) loses in a regime, the ENTIRE family gets blocked —
# killing winning variants (e.g. accel_300_short) in the same family.
# This dict overrides family-level blocks for SPECIFIC signal types.
# Key: (vol_regime, signal_type_substring) → multiplier
# The signal_type is checked with 'in' matching (substring), so 'accel_300_short'
# matches 'accel_300_short', 'accel_300_short+', etc.
# FIRST MATCH WINS — order from most specific to least specific.
SIGNAL_TYPE_OVERRIDES = {
    # ── Pump-Chain V6 explicit overrides (spec rev1 §6.3, re-audit note #4) ──
    # MUST be first (FIRST MATCH WINS): the generic ('NORMAL','pump-chain-'):1.2 and
    # bare 'pump-chain' entries substring-match 'pump-chain-v6±' — v6 LONG would
    # inherit the SHORT-side NORMAL boost and v6 would inherit bare-form penalties.
    ('NORMAL', 'pump-chain-v6+'): 1.0,    # LONG neutral — do NOT inherit SHORT boost
    ('NORMAL', 'pump-chain-v6-'): 1.2,    # SHORT keeps NORMAL habitat boost (same as pump-chain-)
    ('HIGH', 'pump-chain-v6+'): 1.0,      # LONG neutral in HIGH
    ('EXTREME', 'pump-chain-v6+'): 1.0,   # LONG neutral in EXTREME
    ('EXTREME', 'pump-chain-v6-'): 1.0,   # SHORT neutral in EXTREME (floors block oversold)
    # ── EXTREME regime: per-signal overrides of family-level blocks ──
    # ORDER MATTERS: most specific first (FIRST MATCH WINS via substring)
    ('EXTREME', 'accel_300_v3_long'): 0.0,     # BLOCKED — 37% WR in EXTREME, confirmed loser
    ('EXTREME', 'accel_300_v3_short'): 1.0,     # OK — structural breakout SHORT works in EXTREME
    ('EXTREME', 'accel_300_short'): 1.0,         # OK — star SHORT signal, needs EXTREME access
    ('EXTREME', 'accel_300_long'): 0.5,          # PENALIZED — accel_300_long less reliable in EXTREME
    ('EXTREME', 'ema300_dip_long'): 0.0,         # BLOCKED — 25% WR in EXTREME
    ('EXTREME', 'ema300_dip_short'): 1.0,        # OK — ema300_dip_short structural SHORT
    ('EXTREME', 'ema300_breakthrough_short'): 1.0,  # OK — structural SHORT works in EXTREME
    ('EXTREME', 'ema300_breakthrough_long'): 0.0,   # BLOCKED — same as ema300_dip_long family
    ('EXTREME', 'coiled_spring'): 0.0,           # BLOCKED — 40% WR, only trade NORMAL
    ('EXTREME', 'mover_long'): 0.5,              # PENALIZED 2026-09-22 — 50% WR but -$0.93 (8T)
    ('EXTREME', 'mover_short'): 0.5,             # PENALIZED 2026-09-22 — 55.6% WR but -$0.46 (9T)
    ('EXTREME', 'pump_chain-'): 1.0,             # REVERTED 2026-10-08 brain_auditor — dampen 0.5 was over-correction. 14d EXTREME meta-RSI>=45: 41T +$1.09 (50-55 band 14T 64.3%WR +$0.81 BEST cell). The 7d EXTREME bleed (−$0.23/33.3%) was pre-floor RSI<45 trades — now blocked by SHORT_RSI_HARD_FLOOR=45 + PUMP_CHAIN_SHORT_RSI_MIN=45. HIGH stays blocked via PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED.
    ('EXTREME', 'pump_chain+'): 1.0,             # OK 2026-09-22 — 45.8% WR, +$1.19 (48T, profitable)
    ('EXTREME', 'support_resistance'): 0.5,      # PENALIZED — rs mean-reversion reduced in EXTREME
    # ── EXTREME: bare-form fallbacks (after specific forms, FIRST MATCH WINS) ──
    # These catch signal types like 'ema300_breakthrough+', 'pump-chain-', etc.
    # that don't match the specific _long/_short overrides above.
    ('EXTREME', 'ema300_breakthrough'): 1.0,     # OK — bare form fallback for ema300_breakthrough+
    ('EXTREME', 'ema300_dip'): 1.0,              # OK — bare form fallback (specific _long/_short above take priority)
    ('EXTREME', 'mover-_short'): 0.5,            # PENALIZED 2026-09-22 — same as mover_short
    ('EXTREME', 'mover'): 0.5,                   # PENALIZED — bare form fallback (same family as mover+) (coin_tracker_hot variants below)
    ('EXTREME', 'coin_tracker_hot_long'): 0.0,    # BLOCKED — same as mover_long (Mover family)
    ('EXTREME', 'coin_tracker_hot_short'): 0.0,   # BLOCKED — same as mover_short (Mover family)
    ('EXTREME', 'coin_tracker_hot'): 1.0,         # OK — bare coin_tracker_hot fallback
    ('EXTREME', 'pump_chain'): 1.0,              # OK 2026-09-22 — bare form 63.6% WR, +$1.35 (22T)
    ('EXTREME', 'pump-chain+'): 1.0,             # OK 2026-09-22 — 45.8% WR, +$1.19 (48T)
    ('EXTREME', 'pump-chain-'): 1.0,             # REVERTED 2026-10-08 brain_auditor — hyphen variant, same as underscore. 14d EXTREME meta-RSI>=45: 41T +$1.09. Floors already block RSI<45 oversold.
    ('EXTREME', 'pump-chain'): 1.0,              # OK — bare form fallback (63.6% WR, +$1.35 in EXTREME)
    ('EXTREME', 'pump-catcher'): 0.5,            # PENALIZED — pump-catcher family in EXTREME
    ('EXTREME', 'bb-squeeze'): 0.0,              # BLOCKED 2026-10-02 — 12T 50%WR -$0.15 EXTREME. HIGH 63.6%WR +$0.14 kept. signal_reporter
    ('EXTREME', 'mtf-regime-trend-'): 0.0,       # BLOCKED CEO 2026-10-06 — EXTREME 30d 2T 0%WR -$0.23. SHORT model A: EXTREME habitat only profitable with RSI>=40; this signal's oversold leaks make EXTREME a bleed zone.
    ('EXTREME', 'mtf_regime_trend_short'): 0.0,  # underscore form
    ('EXTREME', 'mtf-regime-trend+'): 0.0,       # BLOCKED — signal already disabled (MTF_REGIME_TREND_PLUS_ENABLED=False); gate defense-in-depth
    ('EXTREME', 'mtf_regime_trend_long'): 0.0,   # underscore form
    # ── NORMAL regime: per-signal overrides ──
    # 30d data (2026-10-01): NORMAL LONG -$2.39, NORMAL SHORT -$2.16. Bleed zone.
    # Entries use BOTH underscore and hyphen forms — substring matching means
    # 'pullback_entry-' does NOT match 'pullback-entry-' (underscore ≠ hyphen).
    ('NORMAL', 'pullback_entry-'): 0.0,          # BLOCKED — pullback-entry- SHORT 0% WR in NORMAL (legacy underscore form)
    ('NORMAL', 'pullback-entry-'): 0.5,          # PENALIZED — 30d NORMAL: 32T -$0.62. HIGH: 58T +$0.43. Route by regime.
    ('NORMAL', 'pullback_entry+'): 0.5,          # PENALIZED — pullback-entry+ LONG less reliable in NORMAL
    ('NORMAL', 'pullback-entry+'): 0.3,          # PENALIZED — 30d: 6T 17%WR -$0.57. Structurally weak LONG variant.
    ('NORMAL', 'volume_breakout_short'): 1.0,    # OK — volume-breakout-short can work in NORMAL
    ('NORMAL', 'pump_chain+'): 1.0,              # RE-ENABLED 2026-10-07 CEO — every pump is a LONG
    ('NORMAL', 'pump-chain+'): 1.0,              # RE-ENABLED 2026-10-07 CEO — hyphen variant
    ('NORMAL', 'pump_chain-'): 1.2,              # BOOST 1.0→1.2 2026-10-08 brain_auditor — NORMAL profitable SHORT habitat. Boost winning side; EXTREME reverted to 1.0 same day (RSI>=45 pays); HIGH blocked in compactor. Small-n boost, not a filter.
    ('NORMAL', 'pump-chain-'): 1.2,              # hyphen form — same boost (runtime signal_type is 'pump-chain')
    ('NORMAL', 'pump_chain'): 0.5,               # PENALIZED 2026-09-22 — 66.7% WR but -$0.27 (6T)
    ('NORMAL', 'pump-chain'): 0.5,               # PENALIZED — bare form fallback
    ('NORMAL', 'bb-bounce-v3-long'): 0.0,        # BLOCKED 2026-10-04 signal_reporter — NORMAL 15T 46.7%WR -$0.43. Wins HIGH 5T 60%WR +$0.08. Overrides family Bollinger NORMAL=1.3 boost (wrong for v3).
    ('NORMAL', 'bb_bounce_v3_long'): 0.0,        # underscore form (signal_type in signals DB)
    ('NORMAL', 'mtf-regime-trend-'): 0.0,        # BLOCKED CEO 2026-10-06 — NORMAL 30d 2T 50%WR -$0.25; 7d overall SHORT bleeding. Habitat kept in HIGH.
    ('NORMAL', 'mtf_regime_trend_short'): 0.0,   # underscore form
    ('NORMAL', 'trend-ride'): 0.0,               # BLOCKED 2026-10-06 signal_reporter — backtest NORMAL 79T 45.6%WR -$1.38 no edge; 24h 7T 42.9%WR -$0.18. EXTREME habitat kept (58.6%WR +$5.69).
    ('NORMAL', 'trend_ride'): 0.0,               # underscore form (signal_type 'trend_ride_long')
    # ── NORMAL: bleeding signals (30d cross-tab) ──
    ('NORMAL', 'ema300_dip_short'): 0.3,         # PENALIZED — 30d NORMAL: 12T -$0.84. Bleeds BOTH regimes.
    ('NORMAL', 'ema300_dip'): 0.3,               # PENALIZED — 30d NORMAL: 27T -$0.55. 64% WR but exits bleed (atr_sl_hit -$1.18, cut-loser -$1.07).
    ('NORMAL', 'coiled_spring'): 0.3,            # PENALIZED — 30d NORMAL: 7T -$0.11. 43% WR overall.
    ('NORMAL', 'sma20_dip'): 0.3,                # PENALIZED — 30d NORMAL: 5T -$0.35. 42% WR overall.
    ('NORMAL', 'sma20-dip'): 0.3,                # PENALIZED — hyphen variant
    ('NORMAL', 'slow_grind'): 0.3,               # PENALIZED — 30d: 15T 40%WR -$0.80. Both regimes bleed.
    ('NORMAL', 'r2_trend_long'): 0.3,            # PENALIZED — 30d NORMAL: 4T -$0.18. 36% WR overall.
    ('NORMAL', 'r2-trend-long'): 0.3,            # PENALIZED — hyphen variant
    ('NORMAL', 'trend_purity+'): 0.3,            # PENALIZED — 30d: 11T 36%WR -$0.90. Structurally weak.
    ('NORMAL', 'trend_purity'): 0.3,             # PENALIZED — bare form fallback
    ('NORMAL', 'range_reversion'): 0.3,          # PENALIZED — 30d: 6T 17%WR -$0.62. Structurally weak.
    ('NORMAL', 'range-reversion'): 0.3,          # PENALIZED — hyphen variant
    # NOTE: ('NORMAL','ema300_dip_long') removed — dead-by-theft (bare 'ema300_dip' matches first, same 0.3 value)
    # ── NORMAL: wrong-variant signals — REMOVED 2026-10-01 ──
    # ('NORMAL','bb-bounce-v2-long+'), ('NORMAL','open-skies+'), ('NORMAL','rr-struct-v2+')
    # were removed: bb_bounce_v2_long.py emits source='bb-bounce-v2-long+' and open_skies.py
    # emits source='open-skies+' — the WINNERS' own source strings. The DB 'loser' rows are
    # older trades recorded in source form (trades.signal switched formats ~2026-09-11);
    # winner and loser share signal_type AND source, so these keys cannot discriminate
    # and with source-matching enabled they would penalize the winners (caught by test:
    # bb_bounce_v2_long NORMAL returned 0.3 instead of None). rr-struct-v2+ kept out too —
    # RR_STRUCTURAL_V2_LONG_ENABLED=False means it can't fire anyway.
    # ── HIGH regime: per-signal overrides ──
    ('HIGH', 'accel_300_short'): 1.0,            # OK — accel_300_short SHORT works in HIGH
    ('HIGH', 'mover+'): 0.5,                     # PENALIZED 2026-09-22 — 54.5% WR but -$0.07 (11T)
    ('HIGH', 'mover-'): 1.0,                     # OK 2026-09-22 — 66.7% WR, +$0.26 (3T)
    ('HIGH', 'pump_chain+'): 1.0,                # RE-ENABLED 2026-10-07 CEO — every pump is a LONG
    ('HIGH', 'pump-chain+'): 1.0,                # RE-ENABLED 2026-10-07 CEO — hyphen variant
    ('HIGH', 'pump_chain-'): 1.0,                # Gate shows 1.0 but PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True (brain_auditor 2026-10-07) hard-blocks in signal_compactor.py:2901 + decider_run.py:1656. Gate value is fallback only. Comment was stale (said False). HIGH 30d 27T 44.4%WR -$0.42.
    ('HIGH', 'pump-chain-'): 1.0,                # hyphen variant — same as underscore
    ('HIGH', 'pump_chain'): 1.0,                 # OK 2026-09-22 — bare form 76.9% WR (13T) in HIGH
    ('HIGH', 'pump-chain'): 1.0,                 # OK — bare form fallback
    ('HIGH', 'bb-bounce-v3-long'): 1.0,          # OK 2026-10-04 signal_reporter — HIGH 5T 60%WR +$0.08 (7d 4T 75%WR +$0.10). Overrides family Bollinger HIGH=0.0 block (stale v1/v2 data).
    ('HIGH', 'bb_bounce_v3_long'): 1.0,          # underscore form
    ('HIGH', 'mtf-regime-trend-'): 0.0,          # BLOCKED CEO 2026-10-06 — HIGH 30d 7T 42.9%WR -$0.34 (queue evidence). Fresh n=1 +$0.06 is noise. EXTREME also blocked below.
    ('HIGH', 'mtf_regime_trend_short'): 0.0,     # underscore form
    ('HIGH', 'accel-300-'): 0.0,                # BLOCKED 2026-10-01 — accel-300- SHORT HIGH 0%WR -$0.31 (4T). NORMAL 75%WR. signal_reporter
    ('HIGH', 'accel-300'): 0.0,                 # BLOCKED — bare form fallback for accel-300- (substring match)
    ('HIGH', 'trend-ride'): 0.0,                # BLOCKED 2026-10-06 signal_reporter — backtest HIGH 91T 51.6%WR -$2.38 no edge; 24h 7T 42.9%WR -$0.18. EXTREME 58.6%WR kept via Momentum family (no EXTREME block).
    ('HIGH', 'trend_ride'): 0.0,                # underscore form (signal_type 'trend_ride_long' in trades DB)
    ('HIGH', 'support_resistance'): 0.3,         # PENALIZED — rs mean-reversion reduced in HIGH
    ('HIGH', 'pullback_entry-'): 1.0,            # OK — pullback-entry- SHORT 53.4% WR in HIGH (legacy underscore form)
    ('HIGH', 'pullback-entry-'): 1.0,            # OK — 30d HIGH: 58T +$0.43. Works in HIGH, bleeds NORMAL.
    # ── HIGH: bleeding signals (30d cross-tab) ──
    ('HIGH', 'ema300_dip_short'): 0.3,           # PENALIZED — 30d HIGH: 12T -$0.64. Bleeds BOTH regimes.
    ('HIGH', 'ema300_dip'): 0.5,                 # PENALIZED — 30d HIGH: 28T -$0.17. Bleeds less than NORMAL.
    ('HIGH', 'coiled_spring'): 0.3,              # PENALIZED — 30d HIGH: 6T -$0.23. 43% WR overall.
    ('HIGH', 'sma20_dip'): 0.3,                  # PENALIZED — 30d HIGH: 7T -$0.36. 42% WR overall.
    ('HIGH', 'sma20-dip'): 0.3,                  # PENALIZED — hyphen variant
    ('HIGH', 'slow_grind'): 0.3,                 # PENALIZED — 30d HIGH: 7T -$0.24. 40% WR overall.
    # HIGH wrong-variant keys removed 2026-10-01 — same reason as NORMAL (share source with winners).
}


def _get_signal_type_mult(signal_type, regime, source=None):
    """Check per-signal-type overrides. Returns multiplier or None if no override.
    Matches against BOTH signal_type (underscore form, e.g. 'open_skies_long') AND
    source (hyphen+/- form, e.g. 'open-skies+'). This is critical: the signals DB
    stores signal_type as underscore+_long/_short, but some override keys are written
    in source form. Without source matching, those keys are dead code (2026-10-01 fix)."""
    if not signal_type and not source:
        return None
    st_lower = (signal_type or '').lower()
    src_lower = (source or '').lower()
    for (ov_regime, ov_signal), mult in SIGNAL_TYPE_OVERRIDES.items():
        if ov_regime != regime:
            continue
        if ov_signal in st_lower or (src_lower and ov_signal in src_lower):
            return mult
    return None


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


def get_atr_ratio(token='BTC'):
    """Compute current ATR(14) / average ATR ratio for BTC.
    
    Returns float > 1.0 when expanding, < 1.0 when compressing.
    Uses candles_1h for both current and average.
    """
    conn = None
    try:
        conn = sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close
            FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), 520))  # 500 avg + 20 current
        rows = cur.fetchall()
        if len(rows) < 100:
            return None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()

    candles = list(reversed(rows))

    # Compute TR for all candles
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i][1], candles[i][2], candles[i-1][3]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    if len(trs) < 500:
        return None

    # Current ATR = last 14 bars
    current_atr = sum(trs[-14:]) / 14
    # Average ATR = previous 500 bars (excluding current 14)
    avg_atr = sum(trs[-514:-14]) / 500

    if avg_atr <= 0:
        return None

    return current_atr / avg_atr


def get_btc_trend():
    """Get BTC 30m trend direction from momentum_cache.
    
    Returns: 'RISING', 'FALLING', or 'FLAT'
    """
    conn = None
    try:
        conn = sqlite3.connect(f'{HERMES_DATA}/signals_hermes_runtime.db', timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT velocity FROM momentum_cache WHERE token='BTC'")
        row = cur.fetchone()
        conn.close()
        if row and row[0] is not None:
            vel = float(row[0])
            if vel > 0.15:
                return 'RISING'
            elif vel < -0.15:
                return 'FALLING'
            return 'FLAT'
    except Exception:
        pass
    return 'FLAT'


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
    """Get combined multiplier from volatility regime + market phase.
    
    FIX: Check wildcard FIRST for 0.0 blocks, then specific keys for overrides.
    This prevents blocked signals from leaking through specific (regime, phase) combos.
    """
    # Step 1: Check wildcard (regime, '*') for hard blocks (0.0 multipliers)
    wildcard_key = (regime, '*')
    if wildcard_key in VOL_PHASE_MULTS:
        wildcard_mult = VOL_PHASE_MULTS[wildcard_key].get(family, None)
        if wildcard_mult is not None and wildcard_mult == 0.0:
            return 0.0  # Hard block — never overridden by specific keys
    
    # Step 2: Check specific (regime, phase) combination
    key = (regime, phase)
    if key in VOL_PHASE_MULTS:
        return VOL_PHASE_MULTS[key].get(family, 1.0)
    
    # Step 3: Check wildcard (regime, '*') for non-zero multipliers
    if wildcard_key in VOL_PHASE_MULTS:
        return VOL_PHASE_MULTS[wildcard_key].get(family, 1.0)
    
    # No specific multiplier — use phase-only multiplier
    if _CLUSTERING_ENABLED:
        try:
            return get_phase_mult(family, phase)
        except Exception:
            pass
    
    return 1.0


def get_combined_multiplier(signal_type, regime, phase, source=None):
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
    
    # 0. Per-signal-type override (highest priority — replaces family-level blocks)
    # Overrides vol-phase (step 1), lifecycle (step 2), and inverse (step 3) multipliers.
    # ATR ratio boost (step 4) still applies — it's about BTC trend, not signal family.
    signal_mult = _get_signal_type_mult(signal_type, regime, source=source)
    if signal_mult is not None:
        mult *= signal_mult
        # Skip steps 1-3 (family/phase/lifecycle/inverse) — per-signal override replaces them
        # Jump to step 4 (ATR ratio boost) below
    else:
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
    
    # 4. ATR ratio + BTC trend boost (2026-09-11)
    # Boosts direction-aligned expansion trades (83% WR for SHORT in falling expansion)
    from hermes_constants import (
        VOL_GATE_ATR_RATIO_EXPANSION,
        VOL_GATE_EXPANSION_SHORT_FALLING_BOOST,
        VOL_GATE_EXPANSION_LONG_RISING_BOOST,
    )
    try:
        atr_ratio = get_atr_ratio('BTC')
        if atr_ratio is not None and atr_ratio > VOL_GATE_ATR_RATIO_EXPANSION:
            btc_trend = get_btc_trend()
            # Determine signal direction from signal_type suffix
            _is_short = signal_type.endswith('-') or '_short' in signal_type.lower()
            _is_long = signal_type.endswith('+') or '_long' in signal_type.lower()
            
            if btc_trend == 'FALLING' and _is_short:
                mult *= VOL_GATE_EXPANSION_SHORT_FALLING_BOOST  # 1.2x for SHORT in falling expansion
            elif btc_trend == 'RISING' and _is_long:
                mult *= VOL_GATE_EXPANSION_LONG_RISING_BOOST    # 1.1x for LONG in rising expansion
    except Exception:
        pass
    
    # Clamp to reasonable range (prevent extreme multipliers from crushing scores)
    # 0.0 = hard block (regime ban), preserve it; floor everything else at 0.3
    if mult == 0.0:
        return 0.0
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
                # Direction-preserving suffix match (sync with v1 fix 2026-10-09)
                suffix = part[-1] if part[-1] in '+-' else ''
                if suffix and (base + suffix) in regime_sigs:
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
        
        # Hard block: 0.0 multiplier = signal is banned in this regime
        # Fixes bug where VOL_PHASE_MULTS 0.0 was clamped to 0.3 and ignored
        if combined_mult == 0.0:
            return ('SKIP', f'regime_block: {signal} banned in {regime} (mult=0.0)')
        
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
