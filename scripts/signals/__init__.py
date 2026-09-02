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
    BB_BOUNCE_SHORT_ENABLED, BB_BOUNCE_LONG_ENABLED,
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
    ICHIMOKU_ENABLED,
    VOLUME_BREAKOUT_ENABLED,
    RANGE_REVERSION_ENABLED,
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
    from signals.bb_bounce_short import run as _bb_bounce_short_run
except Exception:
    _bb_bounce_short_run = None

try:
    from signals.bb_bounce_long import run as _bb_bounce_long_run
except Exception:
    _bb_bounce_long_run = None

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
    from signals.range_reversion import run as _range_reversion_run
except Exception:
    _range_reversion_run = None


# ── Signal Registry ───────────────────────────────────────────────────────────
# Each entry: {'name': '<name>', 'enabled': <flag>, 'run': <callable>}
# Directional variants (plus/minus) are handled inside each signal's run()
# based on their *_PLUS_ENABLED / *_MINUS_ENABLED flags.

SIGNAL_REGISTRY: list[dict] = [
    {'name': 'hzscore',                  'enabled': 'HZSCORE_ENABLED',              'run': _hzscore_run},
    {'name': 'rs',                       'enabled': 'RS_ENABLED',                   'run': _rs_run},
    {'name': 'r2_trend_short',           'enabled': 'R2_TREND_SHORT_ENABLED',       'run': _r2_trend_short_run},
    {'name': 'r2_trend_long',            'enabled': 'R2_TREND_LONG_ENABLED',        'run': _r2_trend_long_run},
    {'name': 'bb_bounce_short',          'enabled': 'BB_BOUNCE_SHORT_ENABLED',      'run': _bb_bounce_short_run},
    {'name': 'bb_bounce_long',           'enabled': 'BB_BOUNCE_LONG_ENABLED',       'run': _bb_bounce_long_run},
    {'name': 'return_exhaustion_short',  'enabled': 'RETURN_EXHAUSTION_SHORT_ENABLED', 'run': _return_exhaustion_short_run},
    {'name': 'engulfing',                'enabled': 'ENGULFING_ENABLED',            'run': _engulfing_run},
    {'name': 'continuation',             'enabled': 'CONTINUATION_ENABLED',         'run': _continuation_run},
    {'name': 'spike_exhaustion_short',   'enabled': 'SPIKE_EXHAUSTION_SHORT_ENABLED', 'run': _spike_exhaustion_short_run},
    {'name': 'liquidation_hunt',         'enabled': 'LIQUIDATION_HUNT_ENABLED',     'run': _liquidation_hunt_run},
    {'name': 'macd_divergence',          'enabled': 'MACD_DIVERGENCE_ENABLED',      'run': _macd_divergence_run},
    {'name': 'chain_fire',               'enabled': 'CHAIN_FIRE_ENABLED',           'run': _chain_fire_run},
    {'name': 'signal_confluence',        'enabled': 'SIGNAL_CONFLUENCE_ENABLED',    'run': _signal_confluence_run},
    {'name': 'accel_300_v2_short',       'enabled': ACCEL_300_V2_ENABLED,           'run': _accel_300_v2_short_run},
    {'name': 'accel_300_v2_long',        'enabled': ACCEL_300_V2_LONG_ENABLED,      'run': _accel_300_v2_long_run},
    {'name': 'accel_300_v2_long_5m',     'enabled': ACCEL_300_V2_LONG_5M_ENABLED,   'run': _accel_300_v2_long_5m_run},
    {'name': 'accel_300_v3_long',        'enabled': ACCEL_300_V3_LONG_ENABLED,      'run': _accel_300_v3_long_run},
    {'name': 'accel_300_v3_short',       'enabled': ACCEL_300_V3_SHORT_ENABLED,     'run': _accel_300_v3_short_run},
    {'name': 'inverse_accel_300_v2',     'enabled': INVERSE_ACCEL_300_V2_ENABLED,   'run': _inverse_accel_300_v2_run},
    {'name': 'ichimoku_cloud',           'enabled': ICHIMOKU_ENABLED,              'run': _ichimoku_run},
    {'name': 'volume_breakout',           'enabled': 'VOLUME_BREAKOUT_ENABLED',     'run': _volume_breakout_run},
    {'name': 'range_reversion',           'enabled': 'RANGE_REVERSION_ENABLED',     'run': _range_reversion_run},
]


# ── Registry Accessors ─────────────────────────────────────────────────────────

# Slow signals — scan 191 tokens and take >60s. Run on a 5-min cadence.
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
