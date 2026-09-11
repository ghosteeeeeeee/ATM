#!/usr/bin/env python3
"""
Signal Registry — scripts/signals/__init__.py

Active signals only. Dead signals pruned 2026-08-27 (ponytail audit).
Registry: 65 → 15 entries. Flags preserved in hermes_constants.py.
2026-08-28: Removed bb_bounce (NEVER_REENABLED) and atr_spike (NEVER_REENABLED).
"""

from __future__ import annotations

# ── Import enabled flags for active signals ───────────────────────────────────
from hermes_constants import (
    HZSCORE_ENABLED, HZSCORE_PLUS_ENABLED, HZSCORE_MINUS_ENABLED,
    RS_ENABLED, RS_PLUS_ENABLED, RS_MINUS_ENABLED,
    R2_TREND_SHORT_ENABLED, R2_TREND_LONG_ENABLED,
    BB_BOUNCE_SHORT_ENABLED, BB_BOUNCE_LONG_ENABLED, BB_BOUNCE_V2_LONG_ENABLED,
    RETURN_EXHAUSTION_SHORT_ENABLED,
    ENGULFING_ENABLED, ENGULFING_PLUS_ENABLED, ENGULFING_MINUS_ENABLED,
    CONTINUATION_ENABLED, CONTINUATION_PLUS_ENABLED,
    SPIKE_EXHAUSTION_SHORT_ENABLED, SPIKE_EXHAUSTION_SHORT_MINUS_ENABLED,
    LIQUIDATION_HUNT_ENABLED, LIQUIDATION_HUNT_PLUS_ENABLED, LIQUIDATION_HUNT_MINUS_ENABLED,
    MACD_DIVERGENCE_ENABLED, MACD_DIVERGENCE_PLUS_ENABLED, MACD_DIVERGENCE_MINUS_ENABLED,
    CHAIN_FIRE_ENABLED, CHAIN_FIRE_PLUS_ENABLED, CHAIN_FIRE_MINUS_ENABLED,
    SIGNAL_CONFLUENCE_ENABLED, SIGNAL_CONFLUENCE_PLUS_ENABLED, SIGNAL_CONFLUENCE_MINUS_ENABLED,
    ACCEL_300_V2_ENABLED, ACCEL_300_V2_LONG_ENABLED, ACCEL_300_V2_LONG_5M_ENABLED, INVERSE_ACCEL_300_V2_ENABLED,
    ACCEL_300_V3_LONG_ENABLED,
    ACCEL_300_V3_SHORT_ENABLED,
    ACCEL_300_V4_SHORT_ENABLED,
    ICHIMOKU_ENABLED,
    VOLUME_BREAKOUT_ENABLED,
    RANGE_REVERSION_ENABLED,
    RANGE_REVERSION_PLUS_ENABLED, RANGE_REVERSION_MINUS_ENABLED,
    COILED_SPRING_ENABLED, COILED_SPRING_PLUS_ENABLED, COILED_SPRING_MINUS_ENABLED,
    COILED_SPRING_TRIGGER_LONG_ENABLED, COILED_SPRING_TRIGGER_LONG_PLUS_ENABLED,
    BTC_WAVE_DETECTOR_ENABLED,
    PUMP_FLOW_ENABLED,
    OPEN_SKIES_ENABLED, OPEN_SKIES_PLUS_ENABLED, OPEN_SKIES_MINUS_ENABLED,
    NEUTRAL_SNIPER_ENABLED, NEUTRAL_SNIPER_PLUS_ENABLED, NEUTRAL_SNIPER_MINUS_ENABLED,
    SLOW_GRIND_LONG_ENABLED,
    PULLBACK_ENTRY_ENABLED, PULLBACK_ENTRY_PLUS_ENABLED, PULLBACK_ENTRY_MINUS_ENABLED,
    CONTINUUM_SCORE_ENABLED, CONTINUUM_SCORE_LONG_ENABLED, CONTINUUM_SCORE_SHORT_ENABLED,
    SMA20_DIP_ENABLED, SMA20_DIP_PLUS_ENABLED, SMA20_DIP_MINUS_ENABLED,
    GRIND_BREAKOUT_ENABLED, GRIND_BREAKOUT_PLUS_ENABLED, GRIND_BREAKOUT_MINUS_ENABLED,
    SQUEEZE_REVERSAL_ENABLED, SQUEEZE_REVERSAL_PLUS_ENABLED, SQUEEZE_REVERSAL_MINUS_ENABLED,
    RESISTANCE_BREAK_ENABLED, RESISTANCE_BREAK_PLUS_ENABLED, RESISTANCE_BREAK_MINUS_ENABLED,
    MOVER_ENABLED, MOVER_PLUS_ENABLED, MOVER_MINUS_ENABLED,
    BTC_PUMP_RIDER_ENABLED,
    BREAKOUT_LONG_ENABLED, BREAKOUT_LONG_PLUS_ENABLED, BREAKOUT_LONG_MINUS_ENABLED,
    WARRIOR_SR_CONFIRM_ENABLED, WARRIOR_SR_CONFIRM_PLUS_ENABLED, WARRIOR_SR_CONFIRM_MINUS_ENABLED,
    BREAKOUT_PULLBACK_ENABLED, BREAKOUT_PULLBACK_PLUS_ENABLED, BREAKOUT_PULLBACK_MINUS_ENABLED,
    VOLUME_CLIMAX_ENABLED, VOLUME_CLIMAX_PLUS_ENABLED, VOLUME_CLIMAX_MINUS_ENABLED,
    HH_HL_ENABLED,
    EMA300_BREAKTHROUGH_ENABLED,
    EMA300_BREAKTHROUGH_PLUS_ENABLED,
    EMA300_BREAKTHROUGH_MINUS_ENABLED,
)


# ── Import run() functions from active signal scripts ─────────────────────────

try:
    from signals.hzscore import run as _hzscore_run
except Exception:
    _hzscore_run = None

try:
    from signals.rs import scan_rs_signals as _rs_run
except Exception:
    _rs_run = None

try:
    from signals.r2_trend_short import run as _r2_trend_short_run
except Exception:
    _r2_trend_short_run = None

try:
    from signals.r2_trend_long import run as _r2_trend_long_run
except Exception:
    _r2_trend_long_run = None

try:
    from signals.r2_trend_v2_long import run as _r2_trend_v2_long_run
except Exception:
    _r2_trend_v2_long_run = None

try:
    from signals.ema300_dip_long import run as _ema300_dip_long_run
except Exception:
    _ema300_dip_long_run = None

try:
    from signals.ema300_dip_short import run as _ema300_dip_short_run
except Exception:
    _ema300_dip_short_run = None

try:
    from signals.bb_bounce_short import run as _bb_bounce_short_run
except Exception:
    _bb_bounce_short_run = None

try:
    from signals.bb_bounce_long import run as _bb_bounce_long_run
except Exception:
    _bb_bounce_long_run = None

try:
    from signals.bb_bounce_v2_long import run as _bb_bounce_v2_long_run
except Exception:
    _bb_bounce_v2_long_run = None

try:
    from signals.bb_bounce_v2_short import run as _bb_bounce_v2_short_run
except Exception:
    _bb_bounce_v2_short_run = None

try:
    from signals.return_exhaustion_short import run as _return_exhaustion_short_run
except Exception:
    _return_exhaustion_short_run = None

try:
    from signals.engulfing import run as _engulfing_run
except Exception:
    _engulfing_run = None

try:
    from signals.continuation import run as _continuation_run
except Exception:
    _continuation_run = None

try:
    from signals.spike_exhaustion_short import run as _spike_exhaustion_short_run
except Exception:
    _spike_exhaustion_short_run = None

try:
    from signals.liquidation_hunt import run as _liquidation_hunt_run
except Exception:
    _liquidation_hunt_run = None

try:
    from signals.macd_divergence import run as _macd_divergence_run
except Exception:
    _macd_divergence_run = None

try:
    from signals.chain_fire import run as _chain_fire_run
except Exception:
    _chain_fire_run = None

try:
    from signals.slow_grind_short import run as _slow_grind_short_run
except Exception:
    _slow_grind_short_run = None

try:
    from signals.slow_grind_long import run as _slow_grind_long_run
except Exception:
    _slow_grind_long_run = None

try:
    from signals.signal_confluence import run as _signal_confluence_run
except Exception:
    _signal_confluence_run = None

try:
    from signals.accel_300_v2_short import scan_accel_300_v2_short_signals as _accel_300_v2_short_run
except Exception:
    _accel_300_v2_short_run = None

try:
    from signals.accel_300_v2_long import scan_accel_300_v2_long_signals as _accel_300_v2_long_run
except Exception:
    _accel_300_v2_long_run = None

try:
    from signals.accel_300_v2_long_5m import scan_accel_300_v2_long_5m_signals as _accel_300_v2_long_5m_run
except Exception:
    _accel_300_v2_long_5m_run = None

try:
    from signals.accel_300_v3_long import scan_accel_300_v3_long_signals as _accel_300_v3_long_run
except Exception:
    _accel_300_v3_long_run = None

try:
    from signals.accel_300_v3_short import scan_accel_300_v3_short_signals as _accel_300_v3_short_run
except Exception:
    _accel_300_v3_short_run = None

try:
    from signals.accel_300_v4_short import scan_accel_300_v4_short_signals as _accel_300_v4_short_run
except Exception:
    _accel_300_v4_short_run = None

try:
    from signals.inverse_accel_300_v2 import scan_inverse_accel_300_v2_signals as _inverse_accel_300_v2_run
except Exception:
    _inverse_accel_300_v2_run = None

try:
    from signals.ichimoku_cloud import run as _ichimoku_run
except Exception:
    _ichimoku_run = None

try:
    from signals.volume_breakout import run as _volume_breakout_run
except Exception:
    _volume_breakout_run = None

try:
    from signals.range_reversion_long import scan_range_reversion_long_signals as _range_reversion_long_run
except Exception:
    _range_reversion_long_run = None

try:
    from signals.range_reversion_short import scan_range_reversion_short_signals as _range_reversion_short_run
except Exception:
    _range_reversion_short_run = None

try:
    from signals.coiled_spring import run as _coiled_spring_run
except Exception:
    _coiled_spring_run = None

try:
    from signals.coiled_spring_trigger import run as _coiled_spring_trigger_run
except Exception:
    _coiled_spring_trigger_run = None

try:
    from signals.btc_wave_detector import run as _btc_wave_detector_run
except Exception:
    _btc_wave_detector_run = None

try:
    from signals.pump_flow_signal import run as _pump_flow_signal_run
except Exception:
    _pump_flow_signal_run = None

try:
    from signals.btc_pump_rider import run as _btc_pump_rider_run
except Exception:
    _btc_pump_rider_run = None

try:
    from signals.open_skies import run as _open_skies_run
except Exception:
    _open_skies_run = None

try:
    from signals.pullback_entry import run as _pullback_entry_run
except Exception:
    _pullback_entry_run = None

try:
    from signals.doji_top import run as _doji_top_run
except Exception:
    _doji_top_run = None

try:
    from signals.doji_bottom import run as _doji_bottom_run
except Exception:
    _doji_bottom_run = None

try:
    from signals.continuum_score import run as _continuum_score_run
except Exception:
    _continuum_score_run = None

try:
    from signals.continuum_oscillator import run as _continuum_oscillator_run
except Exception:
    _continuum_oscillator_run = None

try:
    from signals.continuum_trend import run as _continuum_trend_run
except Exception:
    _continuum_trend_run = None

try:
    from signals.neutral_sniper import run as _neutral_sniper_run
except Exception:
    _neutral_sniper_run = None

try:
    from signals.sma20_dip import run as _sma20_dip_run
except Exception:
    _sma20_dip_run = None

try:
    from signals.grind_breakout import run as _grind_breakout_run
except Exception:
    _grind_breakout_run = None

try:
    from signals.squeeze_reversal import run as _squeeze_reversal_run
except Exception:
    _squeeze_reversal_run = None

try:
    from signals.resistance_break import run as _resistance_break_run
except Exception:
    _resistance_break_run = None

try:
    from signals.mover import run as _mover_run
except Exception:
    _mover_run = None

try:
    from signals.breakout_long import run as _breakout_long_run
except Exception:
    _breakout_long_run = None

try:
    from signals.warrior_sr_confirm import run as _warrior_sr_confirm_run
except Exception:
    _warrior_sr_confirm_run = None

try:
    from signals.breakout_pullback import run as _breakout_pullback_run
except Exception:
    _breakout_pullback_run = None

try:
    from signals.volume_climax import run as _volume_climax_run
except Exception:
    _volume_climax_run = None

try:
    from signals.hh_hl import run as _hh_hl_run
except Exception:
    _hh_hl_run = None

try:
    from signals.trend_purity import run as _trend_purity_run
except Exception:
    _trend_purity_run = None

try:
    from signals.ema300_breakthrough import run as _ema300_breakthrough_run
except Exception:
    _ema300_breakthrough_run = None


# ── Signal Registry ───────────────────────────────────────────────────────────
# Each entry: {'name': '<name>', 'enabled': <flag>, 'run': <callable>}
# Directional variants (plus/minus) are handled inside each signal's run()
# based on their *_PLUS_ENABLED / *_MINUS_ENABLED flags.

SIGNAL_REGISTRY: list[dict] = [
    {'name': 'hzscore',                  'enabled': 'HZSCORE_ENABLED',              'run': _hzscore_run},
    {'name': 'rs',                       'enabled': 'RS_ENABLED',                   'run': _rs_run},
    {'name': 'r2_trend_short',           'enabled': 'R2_TREND_SHORT_ENABLED',       'run': _r2_trend_short_run},
    {'name': 'r2_trend_long',            'enabled': 'R2_TREND_LONG_ENABLED',        'run': _r2_trend_long_run},
    {'name': 'r2_trend_v2_long',         'enabled': 'R2_TREND_V2_LONG_ENABLED',     'run': _r2_trend_v2_long_run},
    {'name': 'ema300_dip_long',          'enabled': 'EMA300_DIP_LONG_ENABLED',      'run': _ema300_dip_long_run},
    {'name': 'ema300_dip_short',         'enabled': 'EMA300_DIP_SHORT_ENABLED',     'run': _ema300_dip_short_run},
    {'name': 'bb_bounce_short',          'enabled': 'BB_BOUNCE_SHORT_ENABLED',      'run': _bb_bounce_short_run},
    {'name': 'bb_bounce_long',           'enabled': 'BB_BOUNCE_LONG_ENABLED',       'run': _bb_bounce_long_run},
    {'name': 'bb_bounce_v2_long',        'enabled': 'BB_BOUNCE_V2_LONG_ENABLED',    'run': _bb_bounce_v2_long_run},
    {'name': 'bb_bounce_v2_short',       'enabled': 'BB_BOUNCE_V2_SHORT_ENABLED',   'run': _bb_bounce_v2_short_run},
    {'name': 'return_exhaustion_short',  'enabled': 'RETURN_EXHAUSTION_SHORT_ENABLED', 'run': _return_exhaustion_short_run},
    {'name': 'engulfing',                'enabled': 'ENGULFING_ENABLED',            'run': _engulfing_run},
    {'name': 'continuation',             'enabled': 'CONTINUATION_ENABLED',         'run': _continuation_run},
    {'name': 'spike_exhaustion_short',   'enabled': 'SPIKE_EXHAUSTION_SHORT_ENABLED', 'run': _spike_exhaustion_short_run},
    {'name': 'liquidation_hunt',         'enabled': 'LIQUIDATION_HUNT_ENABLED',     'run': _liquidation_hunt_run},
    {'name': 'macd_divergence',          'enabled': 'MACD_DIVERGENCE_ENABLED',      'run': _macd_divergence_run},
    {'name': 'chain_fire',               'enabled': 'CHAIN_FIRE_ENABLED',           'run': _chain_fire_run},
    {'name': 'slow_grind_short',         'enabled': 'SLOW_GRIND_SHORT_ENABLED',     'run': _slow_grind_short_run},
    {'name': 'slow_grind_long',          'enabled': 'SLOW_GRIND_LONG_ENABLED',      'run': _slow_grind_long_run},
    {'name': 'signal_confluence',        'enabled': 'SIGNAL_CONFLUENCE_ENABLED',    'run': _signal_confluence_run},
    {'name': 'accel_300_v2_short',       'enabled': ACCEL_300_V2_ENABLED,           'run': _accel_300_v2_short_run},
    {'name': 'accel_300_v2_long',        'enabled': ACCEL_300_V2_LONG_ENABLED,      'run': _accel_300_v2_long_run},
    {'name': 'accel_300_v2_long_5m',     'enabled': ACCEL_300_V2_LONG_5M_ENABLED,   'run': _accel_300_v2_long_5m_run},
    {'name': 'accel_300_v3_long',        'enabled': ACCEL_300_V3_LONG_ENABLED,      'run': _accel_300_v3_long_run},
    {'name': 'accel_300_v3_short',       'enabled': ACCEL_300_V3_SHORT_ENABLED,     'run': _accel_300_v3_short_run},
    {'name': 'accel_300_v4_short',       'enabled': ACCEL_300_V4_SHORT_ENABLED,     'run': _accel_300_v4_short_run},
    {'name': 'inverse_accel_300_v2',     'enabled': INVERSE_ACCEL_300_V2_ENABLED,   'run': _inverse_accel_300_v2_run},
    {'name': 'ichimoku_cloud',           'enabled': ICHIMOKU_ENABLED,              'run': _ichimoku_run},
    {'name': 'volume_breakout',           'enabled': 'VOLUME_BREAKOUT_ENABLED',     'run': _volume_breakout_run},
    {'name': 'range_reversion_long',       'enabled': 'RANGE_REVERSION_PLUS_ENABLED',  'run': _range_reversion_long_run},
    {'name': 'range_reversion_short',      'enabled': 'RANGE_REVERSION_MINUS_ENABLED', 'run': _range_reversion_short_run},
    {'name': 'coiled_spring',             'enabled': 'COILED_SPRING_ENABLED',         'run': _coiled_spring_run},
    {'name': 'coiled_spring_trigger',     'enabled': 'COILED_SPRING_TRIGGER_LONG_ENABLED', 'run': _coiled_spring_trigger_run},
    {'name': 'btc_wave_detector',         'enabled': 'BTC_WAVE_DETECTOR_ENABLED',     'run': _btc_wave_detector_run},
    {'name': 'pump_flow_signal',          'enabled': 'PUMP_FLOW_ENABLED',             'run': _pump_flow_signal_run},
    {'name': 'btc_pump_rider',            'enabled': 'BTC_PUMP_RIDER_ENABLED',        'run': _btc_pump_rider_run},
    {'name': 'open_skies',                'enabled': 'OPEN_SKIES_ENABLED',            'run': _open_skies_run},
    {'name': 'neutral_sniper',            'enabled': 'NEUTRAL_SNIPER_ENABLED',        'run': _neutral_sniper_run},
    {'name': 'pullback_entry',            'enabled': 'PULLBACK_ENTRY_ENABLED',        'run': _pullback_entry_run},
    {'name': 'grind_breakout',            'enabled': 'GRIND_BREAKOUT_ENABLED',        'run': _grind_breakout_run},
    {'name': 'squeeze_reversal',          'enabled': 'SQUEEZE_REVERSAL_ENABLED',      'run': _squeeze_reversal_run},
    {'name': 'doji_top',                  'enabled': 'DOJI_TOP_ENABLED',              'run': _doji_top_run},
    {'name': 'doji_bottom',               'enabled': 'DOJI_TOP_ENABLED',              'run': _doji_bottom_run},
    {'name': 'continuum_score',           'enabled': 'CONTINUUM_SCORE_ENABLED',       'run': _continuum_score_run},
    {'name': 'continuum_oscillator',      'enabled': 'CONTINUUM_OSC_ENABLED',         'run': _continuum_oscillator_run},
    {'name': 'continuum_trend',           'enabled': 'CONTINUUM_TREND_ENABLED',       'run': _continuum_trend_run},
    {'name': 'sma20_dip',                'enabled': 'SMA20_DIP_ENABLED',            'run': _sma20_dip_run},
    {'name': 'resistance_break',         'enabled': 'RESISTANCE_BREAK_ENABLED',     'run': _resistance_break_run},
    {'name': 'mover',                    'enabled': 'MOVER_ENABLED',               'run': _mover_run},
    {'name': 'breakout_long',            'enabled': 'BREAKOUT_LONG_ENABLED',       'run': _breakout_long_run},
    {'name': 'warrior_sr_confirm',       'enabled': 'WARRIOR_SR_CONFIRM_ENABLED',  'run': _warrior_sr_confirm_run},
    {'name': 'breakout_pullback',        'enabled': 'BREAKOUT_PULLBACK_ENABLED',   'run': _breakout_pullback_run},
    {'name': 'volume_climax',            'enabled': 'VOLUME_CLIMAX_ENABLED',       'run': _volume_climax_run},
    {'name': 'hh_hl',                    'enabled': 'HH_HL_ENABLED',              'run': _hh_hl_run},
    {'name': 'trend_purity',             'enabled': 'TREND_PURITY_ENABLED',        'run': _trend_purity_run},
    {'name': 'ema300_breakthrough',       'enabled': 'EMA300_BREAKTHROUGH_ENABLED', 'run': _ema300_breakthrough_run},
]


# ── Registry Accessors ─────────────────────────────────────────────────────────

# Slow signals — scan 191 tokens and take >60s. Run on a 5-min cadence.
# pump_flow_signal removed — runs every minute to match state file update cadence
_SLOW_SIGNALS = {'macd_divergence', 'signal_confluence', 'ichimoku_cloud'}


def _resolve_enabled(entry):
    """Resolve 'enabled' to bool: if string, look up in hermes_constants; otherwise return as-is."""
    import hermes_constants as hc
    enabled = entry['enabled']
    if isinstance(enabled, str):
        return getattr(hc, enabled, False)
    return enabled


def get_registered_signals():
    """Return only the signals where enabled=True and run is not None."""
    return [s for s in SIGNAL_REGISTRY if _resolve_enabled(s) and s['run'] is not None]


def get_fast_signals():
    """Fast signals — run every minute."""
    return [s for s in get_registered_signals() if s['name'] not in _SLOW_SIGNALS]


def get_slow_signals():
    """Slow signals — run every 5 minutes."""
    return [s for s in get_registered_signals() if s['name'] in _SLOW_SIGNALS]


def register_signal(name: str, run_fn, enabled=True):
    """Dynamically register a signal at runtime."""
    global SIGNAL_REGISTRY
    SIGNAL_REGISTRY = [s for s in SIGNAL_REGISTRY if s['name'] != name]
    SIGNAL_REGISTRY.append({'name': name, 'enabled': enabled, 'run': run_fn})


def _run_signal(args):
    """Run a single signal."""
    sig_name, fn_name = args
    try:
        import sys
        sys.path.insert(0, '/root/.hermes/scripts')
        try:
            mod = __import__(sig_name, fromlist=[fn_name])
        except ImportError:
            mod = __import__(f'signals.{sig_name}', fromlist=[fn_name])
        fn = getattr(mod, fn_name, None)
        if fn is None:
            return sig_name, None
        if fn.__code__.co_argcount == 0:
            return sig_name, fn()
        from signal_schema import get_all_latest_prices
        prices = get_all_latest_prices()
        return sig_name, fn(prices)
    except Exception as e:
        return sig_name, f'ERROR: {e}'


def run_all_signals(signal_list=None):
    """Run all enabled signals using ThreadPoolExecutor."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    signals_to_run = signal_list if signal_list is not None else get_registered_signals()

    work = [
        (signal['name'], signal['run'].__name__)
        for signal in signals_to_run
        if signal.get('run') is not None
    ]

    results = {}

    with ThreadPoolExecutor(max_workers=21) as executor:
        futures = {executor.submit(_run_signal, w): w[0] for w in work}
        for future in as_completed(futures):
            sig_name = futures[future]
            try:
                name, result = future.result()
                results[name] = result
            except Exception as e:
                results[sig_name] = f'ERROR: {e}'

    return results
