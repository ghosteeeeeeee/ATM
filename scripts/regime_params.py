#!/usr/bin/env python3
"""
regime_params.py — Regime-aware parameter overrides for signals.

Different volatility regimes (FLAT/NORMAL/HIGH/EXTREME) need different
signal parameters. This module provides a central registry of overrides
and a helper to merge them with defaults.

Usage in signal files:
    from regime_params import get_regime_params
    overrides = get_regime_params(token, 'accel_300_v3_long')
    min_gap = overrides.get('MIN_GAP', ACCEL_300_V3_LONG_MIN_GAP)

These overrides are EDUCATED GUESSSES from the regime-aware-signal-params-spec.
Must be validated via backtest before trusting. Normal regime uses defaults (no override).
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Override Registry ─────────────────────────────────────────────────────────
# Keys: signal_name → volatility_regime → {short_param_name: value}
# Empty dict for a regime = use hermes_constants defaults.

REGIME_PARAMS = {
    'accel_300_v3_long': {
        'FLAT': {
            'MIN_GAP': 1.5,          # default 2.0 — lower bar in quiet markets
            'MAX_GAP': 5.0,          # default 6.0 — less extension in flat
            'MIN_PULLBACK': 0.25,    # default 0.35 — smaller pullbacks meaningful
            'REEXPAND_MIN': 0.12,    # default 0.20 — gentler bounce confirmation
            'RSI_MAX': 65,           # default 68 — slightly tighter
            'CHASE_MOVE_MAX': 1.5,   # default 2.0 — less noise tolerance
            'COOLDOWN_BARS': 15,     # default 20 — more opportunities in quiet
            'VOLUME_MULT': 1.0,      # default 1.1 — volume less critical
        },
        'NORMAL': {},  # use defaults
        'HIGH': {
            'MIN_GAP': 2.5,          # default 2.0 — need stronger trend
            'MAX_GAP': 7.0,          # default 6.0 — allow more extension
            'MIN_PULLBACK': 0.45,    # default 0.35 — clearer pullback required
            'REEXPAND_MIN': 0.28,    # default 0.20 — stronger bounce confirmation
            'RSI_MAX': 72,           # default 68 — more room in volatile markets
            'CHASE_MOVE_MAX': 3.0,   # default 2.0 — more noise tolerance
            'GREEN_CAP': 2,          # default 3 — less chasing in volatile
            'COOLDOWN_BARS': 25,     # default 20 — longer cooldown
            'VOLUME_MULT': 1.2,      # default 1.1 — volume more important
        },
        'EXTREME': {
            'MIN_GAP': 3.0,          # default 2.0 — only strong trends
            'MAX_GAP': 8.0,          # default 6.0 — extreme extension OK
            'MIN_PULLBACK': 0.55,    # default 0.35 — very clear pullback required
            'REEXPAND_MIN': 0.35,    # default 0.20 — strong bounce confirmation
            'RSI_MAX': 70,           # default 68 — moderate room
            'CHASE_MOVE_MAX': 4.0,   # default 2.0 — extreme noise
            'GREEN_CAP': 2,          # default 3 — don't chase in storms
            'COOLDOWN_BARS': 30,     # default 20 — long cooldown
            'VOLUME_MULT': 1.3,      # default 1.1 — volume critical
            'CONF_BASE': 48,         # default 55 — lower base confidence
        },
    },
    'accel_300_v3_short': {
        'FLAT': {
            'MIN_GAP': 0.8,          # default 1.0 — lower bar
            'MAX_GAP': 5.0,          # default 6.0
            'CHASE_DROP_MAX': 1.5,   # default 2.0
            'COOLDOWN_BARS': 12,     # default 15
        },
        'NORMAL': {},
        'HIGH': {
            'MIN_GAP': 1.5,          # default 1.0 — stronger trend needed
            'MAX_GAP': 7.0,          # default 6.0
            'CHASE_DROP_MAX': 3.0,   # default 2.0 — more noise
            'COOLDOWN_BARS': 20,     # default 15
            'VOLUME_MULT': 1.2,      # default 1.1
        },
        'EXTREME': {
            'MIN_GAP': 2.0,          # default 1.0 — strong trend only
            'MAX_GAP': 8.0,          # default 6.0
            'CHASE_DROP_MAX': 4.0,   # default 2.0 — extreme noise
            'COOLDOWN_BARS': 25,     # default 15
            'VOLUME_MULT': 1.3,      # default 1.1
            'CONF_BASE': 52,         # default 62 — lower base confidence
        },
    },
}


def get_regime_params(token, signal_name):
    """Get regime-specific parameter overrides for this token.

    Returns dict of override key-value pairs. Empty dict = use defaults.
    Keys use short names (MIN_GAP, RSI_MAX, etc.) matching hermes_constants
    names without the signal prefix.

    Falls back to NORMAL (no overrides) if:
      - token has no ATR data
      - signal has no overrides defined
      - volatility_gate import fails
    """
    try:
        from volatility_gate import get_atr_pct, classify_volatility
        atr_pct = get_atr_pct(token)
        regime = classify_volatility(atr_pct) if atr_pct is not None else 'NORMAL'
    except Exception:
        regime = 'NORMAL'

    signal_overrides = REGIME_PARAMS.get(signal_name, {})
    return signal_overrides.get(regime, {})


def get_regime(token):
    """Get the current volatility regime for a token (for logging/storage)."""
    try:
        from volatility_gate import get_atr_pct, classify_volatility
        atr_pct = get_atr_pct(token)
        return classify_volatility(atr_pct) if atr_pct is not None else 'NORMAL'
    except Exception:
        return 'NORMAL'


# ── Short-name → full constant name mapping (for signal file integration) ─────

PARAM_MAP_LONG = {
    'MIN_GAP': 'ACCEL_300_V3_LONG_MIN_GAP',
    'MAX_GAP': 'ACCEL_300_V3_LONG_MAX_GAP',
    'MIN_PULLBACK': 'ACCEL_300_V3_LONG_MIN_PULLBACK',
    'MAX_PULLBACK': 'ACCEL_300_V3_LONG_MAX_PULLBACK',
    'REEXPAND_MIN': 'ACCEL_300_V3_LONG_REEXPAND_MIN',
    'RSI_MAX': 'ACCEL_300_V3_LONG_RSI_MAX',
    'RSI_MIN': 'ACCEL_300_V3_LONG_RSI_MIN',
    'CHASE_MOVE_MAX': 'ACCEL_300_V3_LONG_CHASE_MOVE_MAX',
    'GREEN_CAP': 'ACCEL_300_V3_LONG_GREEN_CAP',
    'COOLDOWN_BARS': 'ACCEL_300_V3_LONG_COOLDOWN_BARS',
    'VOLUME_MULT': 'ACCEL_300_V3_LONG_VOLUME_MULT',
    'CONF_BASE': 'ACCEL_300_V3_LONG_CONF_BASE',
    'MIN_VELOCITY': 'ACCEL_300_V3_LONG_MIN_VELOCITY',
    'SLOPE_WINDOW': 'ACCEL_300_V3_LONG_SLOPE_WINDOW',
    'MIN_SLOPE_PCT': 'ACCEL_300_V3_LONG_MIN_SLOPE_PCT',
    'PERSISTENCE_BARS': 'ACCEL_300_V3_LONG_PERSISTENCE_BARS',
}

PARAM_MAP_SHORT = {
    'MIN_GAP': 'ACCEL_300_V3_SHORT_MIN_GAP',
    'MAX_GAP': 'ACCEL_300_V3_SHORT_MAX_GAP',
    'MIN_GAP_ACCEL': 'ACCEL_300_V3_SHORT_MIN_GAP_ACCEL',
    'CHASE_DROP_MAX': 'ACCEL_300_V3_SHORT_CHASE_DROP_MAX',
    'COOLDOWN_BARS': 'ACCEL_300_V3_SHORT_COOLDOWN_BARS',
    'VOLUME_MULT': 'ACCEL_300_V3_SHORT_VOLUME_MULT',
    'CONF_BASE': 'ACCEL_300_V3_SHORT_CONF_BASE',
}


def apply_overrides(defaults_dict, overrides, param_map):
    """Merge regime overrides into a defaults dict.

    Args:
        defaults_dict: dict of {full_constant_name: current_value}
        overrides: dict of {short_name: new_value} from get_regime_params()
        param_map: dict mapping short_name → full_constant_name

    Returns:
        New dict with overrides applied (original unchanged).
    """
    result = dict(defaults_dict)
    for short_key, value in overrides.items():
        full_key = param_map.get(short_key)
        if full_key and full_key in result:
            result[full_key] = value
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', default='BTC')
    parser.add_argument('--signal', default='accel_300_v3_long')
    args = parser.parse_args()

    overrides = get_regime_params(args.token, args.signal)
    regime = get_regime(args.token)
    print(f"Token: {args.token} | Regime: {regime} | Signal: {args.signal}")
    if overrides:
        print(f"Overrides: {overrides}")
    else:
        print("No overrides (using defaults)")
