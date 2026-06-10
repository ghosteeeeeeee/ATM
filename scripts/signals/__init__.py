#!/usr/bin/env python3
"""
Signal Registry — scripts/signals/__init__.py

New architecture: ALL signal generators live here as individual scripts in scripts/signals/.
This __init__.py wires them into a registry that run_pipeline.py consumes.

Each signal script exports a run() function (or equivalent). The registry handles
enabled/disabled state via hermes_constants flags.
"""

from __future__ import annotations

# ── Import all *_ENABLED flags from hermes_constants ─────────────────────────
from hermes_constants import (
    PCT_HERMES_ENABLED, PCT_HERMES_PLUS_ENABLED, PCT_HERMES_MINUS_ENABLED,
    VEL_HERMES_ENABLED, VEL_HERMES_PLUS_ENABLED, VEL_HERMES_MINUS_ENABLED,
    HZSCORE_ENABLED, HZSCORE_PLUS_ENABLED, HZSCORE_MINUS_ENABLED,
    HMACD_ENABLED, HMACD_PLUS_ENABLED, HMACD_MINUS_ENABLED,
    MOMENTUM_ENABLED, MOMENTUM_PLUS_ENABLED, MOMENTUM_MINUS_ENABLED,
    MTF_MOMENTUM_ENABLED, MTF_MOMENTUM_PLUS_ENABLED, MTF_MOMENTUM_MINUS_ENABLED,
    PHASE_ACCEL_ENABLED, PHASE_ACCEL_PLUS_ENABLED, PHASE_ACCEL_MINUS_ENABLED,
    FAST_MOMENTUM_ENABLED, FAST_MOMENTUM_PLUS_ENABLED, FAST_MOMENTUM_MINUS_ENABLED,
    ACCEL_300_ENABLED,
    EMA_ANGLE_ENABLED, EMA_ANGLE_PLUS_ENABLED, EMA_ANGLE_MINUS_ENABLED,
    RS_ENABLED, GAP_300_ENABLED, GAP_300_PLUS_ENABLED, GAP_300_MINUS_ENABLED,
    MA_CROSS_ENABLED, MA_CROSS_PLUS_ENABLED, MA_CROSS_MINUS_ENABLED,
    MA_CROSS_5M_ENABLED, MA_CROSS_5M_PLUS_ENABLED, MA_CROSS_5M_MINUS_ENABLED,
    HH_HL_ENABLED, GUPPY_ENABLED, MACD_ACCEL_ENABLED,
    TREND_PURITY_ENABLED, EMA9_SMA20_ENABLED,
    R2_REV_ENABLED, R2_TREND_ENABLED,
    VOLUME_HL_ENABLED, MA300_CANDLE_ENABLED,
    ATR_COMPRESSION_ENABLED, EXHAUSTION_ENABLED, COUNTER_FLIP_ENABLED,
    # Per-direction flags for signals without their own +/- killswitch
    ATR_COMPRESSION_PLUS_ENABLED, ATR_COMPRESSION_MINUS_ENABLED,
    EMA9_SMA20_PLUS_ENABLED, EMA9_SMA20_MINUS_ENABLED,
    EXHAUSTION_PLUS_ENABLED, EXHAUSTION_MINUS_ENABLED,
    GUPPY_PLUS_ENABLED, GUPPY_MINUS_ENABLED,
    HH_HL_PLUS_ENABLED, HH_HL_MINUS_ENABLED,
    MA300_CANDLE_PLUS_ENABLED, MA300_CANDLE_MINUS_ENABLED,
    MACD_ACCEL_PLUS_ENABLED, MACD_ACCEL_MINUS_ENABLED,
    R2_REV_PLUS_ENABLED, R2_REV_MINUS_ENABLED,
    R2_TREND_PLUS_ENABLED, R2_TREND_MINUS_ENABLED,
    TREND_PURITY_PLUS_ENABLED, TREND_PURITY_MINUS_ENABLED,
    VOLUME_HL_PLUS_ENABLED, VOLUME_HL_MINUS_ENABLED,
    EMA20_50_PLUS_ENABLED, EMA20_50_MINUS_ENABLED,
    MACD_1M_PLUS_ENABLED, MACD_1M_MINUS_ENABLED,
    TL_BREAK_ENABLED,
    ZSCORE_PUMP_NEW_ENABLED, ZSCORE_PUMP_PLUS_ENABLED, ZSCORE_PUMP_MINUS_ENABLED,
    MTP_ZSCORE_ENABLED, MTP_ZSCORE_PLUS_ENABLED, MTP_ZSCORE_MINUS_ENABLED,
)


# ── Import real run() functions from each signal script ──────────────────────
# Each signal script has its own run() or equivalent entry point.
# We import them here and wire into the registry.

try:
    from signals.pct_hermes import run as _pct_hermes_run
except Exception:
    _pct_hermes_run = None

try:
    from signals.vel_hermes import run as _vel_hermes_run
except Exception:
    _vel_hermes_run = None

try:
    from signals.zscore_rising import run as _zscore_rising_run
except Exception:
    _zscore_rising_run = None

try:
    from signals.hzscore import run as _hzscore_run
except Exception:
    _hzscore_run = None

try:
    from signals.hmacd import run as _hmacd_run
except Exception:
    _hmacd_run = None

try:
    from signals.mtf_macd import run as _mtf_macd_run
except Exception:
    _mtf_macd_run = None

try:
    from signals.mtf_momentum import run as _mtf_momentum_run
except Exception:
    _mtf_momentum_run = None

try:
    from signals.momentum import run as _momentum_run
except Exception:
    _momentum_run = None

try:
    from signals.phase_accel import run as _phase_accel_run
except Exception:
    _phase_accel_run = None

try:
    from signals.fast_momentum import run as _fast_momentum_run
except Exception:
    _fast_momentum_run = None

try:
    from signals.accel_300 import scan_accel_300_signals as _accel_300_run
except Exception:
    _accel_300_run = None

try:
    from signals.ema_angle import scan_ema_angle_signals as _ema_angle_run
except Exception:
    _ema_angle_run = None

try:
    from signals.rs import scan_rs_signals as _rs_run
except Exception:
    _rs_run = None

try:
    from signals.gap_300 import scan_gap300_signals as _gap_300_run
except Exception:
    _gap_300_run = None

try:
    from signals.ma_cross import scan_ma_cross_signals as _ma_cross_run
except Exception:
    _ma_cross_run = None

try:
    from signals.ma_cross_5m import scan_ma_cross_5m_signals as _ma_cross_5m_run
except Exception:
    _ma_cross_5m_run = None

try:
    from signals.hh_hl import scan_hh_hl_signals as _hh_hl_run
except Exception:
    _hh_hl_run = None

try:
    from signals.guppy import scan_all_tokens as _guppy_run
except Exception:
    _guppy_run = None

try:
    from signals.macd_accel import scan_macd_accel_signals as _macd_accel_run
except Exception:
    _macd_accel_run = None

try:
    from signals.trend_purity import scan as _trend_purity_run
except Exception:
    _trend_purity_run = None

try:
    from signals.ema9_sma20 import scan_ema9_sma20_signals as _ema9_sma20_run
except Exception:
    _ema9_sma20_run = None

try:
    from signals.r2_rev import scan_r2_rev_5m_signals as _r2_rev_run
except Exception:
    _r2_rev_run = None

try:
    from signals.r2_trend import scan_r2_trend_signals as _r2_trend_run
except Exception:
    _r2_trend_run = None

try:
    from signals.volume_hl import main as _volume_hl_run
except Exception:
    _volume_hl_run = None

try:
    from signals.ma300_candle_confirm import scan_ma300_candle_signals as _ma300_candle_run
except Exception:
    _ma300_candle_run = None

try:
    from signals.atr_compression import scan_atr_compression_signals as _atr_compression_run
except Exception:
    _atr_compression_run = None

try:
    from signals.exhaustion import scan as _exhaustion_run
except Exception:
    _exhaustion_run = None

try:
    from signals.counter_flip import run as _counter_flip_run
except Exception:
    _counter_flip_run = None

try:
    from signals.tl_break import scan_tl_break_signals as _tl_break_run
except Exception:
    _tl_break_run = None

try:
    from signals.zscore_pump import scan_zscore_pump_signals as _zscore_pump_run
except Exception:
    _zscore_pump_run = None

try:
    from signals.mtp_zscore import scan_mtp_zscore_signals as _mtp_zscore_run
except Exception:
    _mtp_zscore_run = None


# ── Signal Registry ───────────────────────────────────────────────────────────
# Each entry: {'name': '<name>', 'enabled': <flag>, 'run': <callable>}
# NOTE: directional variants (plus/minus) are handled inside each signal's run()
# based on their *_PLUS_ENABLED / *_MINUS_ENABLED flags.

# ── Signal Registry ───────────────────────────────────────────────────────────
# Each entry: {'name': '<name>', 'enabled': <flag>, 'run': <callable>}
# NOTE: directional variants (plus/minus) are handled inside each signal's run()
# based on their *_PLUS_ENABLED / *_MINUS_ENABLED flags.

# For signals with *_ENABLED flags, 'enabled' stores the flag NAME (string),
# resolved at access time via _resolve_enabled(). Others store bool directly.

SIGNAL_REGISTRY: list[dict] = [
    {'name': 'pct_hermes',          'enabled': 'PCT_HERMES_ENABLED',         'run': _pct_hermes_run},
    {'name': 'vel_hermes',           'enabled': 'VEL_HERMES_ENABLED',         'run': _vel_hermes_run},
    {'name': 'zscore_rising',        'enabled': 'ZSCORE_RISING_ENABLED',      'run': _zscore_rising_run},
    {'name': 'hzscore',              'enabled': 'HZSCORE_ENABLED',            'run': _hzscore_run},
    {'name': 'hmacd',                'enabled': 'HMACD_ENABLED',              'run': _hmacd_run},
    {'name': 'hmacd_mtf',             'enabled': 'HMACD_ENABLED',              'run': _mtf_macd_run},
    {'name': 'mtf_momentum',          'enabled': 'MTF_MOMENTUM_ENABLED',       'run': _mtf_momentum_run},
    {'name': 'momentum',             'enabled': 'MOMENTUM_ENABLED',          'run': _momentum_run},
    {'name': 'phase_accel',          'enabled': 'PHASE_ACCEL_ENABLED',        'run': _phase_accel_run},
    {'name': 'fast_momentum',        'enabled': 'FAST_MOMENTUM_ENABLED',      'run': _fast_momentum_run},
    # These use their *_ENABLED boolean directly
    {'name': 'accel_300',            'enabled': ACCEL_300_ENABLED,           'run': _accel_300_run},
    {'name': 'ema_angle',            'enabled': EMA_ANGLE_ENABLED,            'run': _ema_angle_run},
    {'name': 'rs',                   'enabled': RS_ENABLED,                   'run': _rs_run},
    {'name': 'gap_300',              'enabled': GAP_300_ENABLED,             'run': _gap_300_run},
    {'name': 'ma_cross',             'enabled': MA_CROSS_ENABLED,            'run': _ma_cross_run},
    {'name': 'ma_cross_5m',          'enabled': MA_CROSS_5M_ENABLED,         'run': _ma_cross_5m_run},
    {'name': 'hh_hl',                'enabled': HH_HL_ENABLED,               'run': _hh_hl_run},
    {'name': 'guppy',                'enabled': GUPPY_ENABLED,               'run': _guppy_run},
    {'name': 'macd_accel',           'enabled': MACD_ACCEL_ENABLED,          'run': _macd_accel_run},
    {'name': 'trend_purity',         'enabled': TREND_PURITY_ENABLED,        'run': _trend_purity_run},
    {'name': 'ema9_sma20',           'enabled': EMA9_SMA20_ENABLED,         'run': _ema9_sma20_run},
    {'name': 'r2_rev',               'enabled': R2_REV_ENABLED,             'run': _r2_rev_run},
    {'name': 'r2_trend',             'enabled': R2_TREND_ENABLED,           'run': _r2_trend_run},
    {'name': 'volume_hl',            'enabled': VOLUME_HL_ENABLED,           'run': _volume_hl_run},
    {'name': 'ma300_candle_confirm', 'enabled': MA300_CANDLE_ENABLED,        'run': _ma300_candle_run},
    {'name': 'atr_compression',      'enabled': ATR_COMPRESSION_ENABLED,     'run': _atr_compression_run},
    {'name': 'exhaustion',           'enabled': EXHAUSTION_ENABLED,          'run': _exhaustion_run},
    {'name': 'counter_flip',         'enabled': COUNTER_FLIP_ENABLED,      'run': _counter_flip_run},
    {'name': 'tl_break',             'enabled': TL_BREAK_ENABLED,          'run': _tl_break_run},
    {'name': 'zscore_pump',         'enabled': ZSCORE_PUMP_NEW_ENABLED,       'run': _zscore_pump_run},
    {'name': 'mtp_zscore',          'enabled': MTP_ZSCORE_ENABLED,             'run': _mtp_zscore_run},
]


# ── Registry Accessors ─────────────────────────────────────────────────────────

# Slow signals — scan 191 tokens and take >60s. Run separately on a 5-min cadence.
# All other signals are fast (<10s each).
_SLOW_SIGNALS = {'momentum', 'mtf_momentum'}


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
    """Dynamically register a signal at runtime. Useful for plugin-style injection.
    Pass enabled=<flag_name_str> to defer to hermes_constants at access time."""
    global SIGNAL_REGISTRY
    SIGNAL_REGISTRY = [s for s in SIGNAL_REGISTRY if s['name'] != name]
    SIGNAL_REGISTRY.append({'name': name, 'enabled': enabled, 'run': run_fn})


def _run_signal(args):
    """Run a single signal. Threads share the LRU cache with the caller,
    so pct_hermes/vel_hermes/phase_accel benefit from cached get_price_history
    calls made by earlier signals in the same batch.

    NOTE: cache warming is only guaranteed if pct_hermes runs BEFORE the other
    cache-dependent signals. Since ThreadPool uses as_completed() (not submission order),
    we submit cache-warming signals FIRST and let them fill the cache before the
    remaining signals start pulling from it.
    """
    sig_name, fn_name = args
    try:
        import sys
        sys.path.insert(0, '/root/.hermes/scripts')
        # Use the signal name itself as module name
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
    """
    Run all enabled signals using ThreadPoolExecutor.

    Key optimization: threads share the LRU cache for get_price_history() and
    other expensive functions. When pct_hermes runs first and populates the
    cache with 191 tokens of price history, vel_hermes and phase_accel
    that run next get cache hits on every token — eliminating redundant
    SQLite reads and CPU computation.

    The 3 slow signals (pct_hermes ~20s, vel_hermes ~14s, phase_accel ~20s)
    now run sequentially in threads but cache is warm for the 2nd and 3rd,
    reducing total from ~56s (sequential) to ~20s (first fills cache, others hit it).
    Fast signals (~3-5s each) run in parallel and complete quickly.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    signals_to_run = signal_list if signal_list is not None else get_registered_signals()

    # Build (name, module_name) work items
    name_to_module = {
        'pct_hermes': 'run', 'vel_hermes': 'run',
        'hzscore': 'run', 'hmacd': 'run',
        'phase_accel': 'run', 'fast_momentum': 'run',
        'accel_300': 'scan_accel_300_signals', 'ema_angle': 'scan_ema_angle_signals',
        'rs': 'scan_rs_signals',
        'ma_cross': 'scan_ma_cross_signals', 'ma_cross_5m': 'scan_ma_cross_5m_signals',
        'hh_hl': 'scan_hh_hl_signals', 'guppy': 'scan_all_tokens',
        'macd_accel': 'scan_macd_accel_signals', 'trend_purity': 'scan',
        'ema9_sma20': 'scan_ema9_sma20_signals', 'r2_rev': 'run', 'r2_trend': 'run',
        'volume_hl': 'run', 'ma300_candle_confirm': 'run',
        'atr_compression': 'run',
        'exhaustion': 'run', 'counter_flip': 'run',
        'tl_break': 'run', 'zscore_pump': 'scan_zscore_pump_signals',
        'mtp_zscore': 'scan_mtp_zscore_signals',
    }
    work = [
        (signal['name'], signal['run'].__name__)
        for signal in signals_to_run
        if signal.get('run') is not None
    ]

    results = {}

    # ThreadPoolExecutor: threads share LRU cache (unlike ProcessPoolExecutor).
    # 21 threads — the GIL means CPU-bound work doesn't fully parallelize,
    # but I/O (SQLite) interleaves and the shared LRU cache eliminates
    # redundant computation for pct_hermes/vel_hermes/phase_accel.
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
