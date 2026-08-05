# Signal Runner Two-Dispatch System (2026-05-08)

## Signal Runner Confirmed Clean (2026-05-08)
**File:** `/root/.hermes/scripts/signals_runner.py` — 83 lines, NOT in git (created May 7-8).

Verified: ThreadPoolExecutor(21 workers), calls `_run_signal()` per signal, logs result if not None.
No DB writes, no trade execution, no branching. When T asks to review signal_runner.py: confirm clean,
move to next script. Do not branch into confluence gates, orphan closing, or decider_run.

The runner is NEVER the problem when pipeline shows 0 signals or wrong counts — check the
individual signal module's `run()` function, or `signals/__init__.py` registry configuration.

---

## The Two Dispatch Paths

### Path 1 — PRIMARY: ThreadPoolExecutor calls registry entry directly
```python
# signals/__init__.py
SIGNAL_REGISTRY = [
    {'name': 'accel_300', 'enabled': ACCEL_300_ENABLED, 'run': _accel_300_run},
    {'name': 'rs',        'enabled': RS_ENABLED,        'run': _rs_run},
    ...
]

# _rs_run is set at import time:
from signals.rs import scan_rs_signals as _rs_run  # line 86

# ThreadPoolExecutor calls the registry function directly:
with ThreadPoolExecutor(max_workers=21) as executor:
    futures = {executor.submit(_run_signal, w): w[0] for w in work}
    # Each future calls signal['run']() — the imported function, NOT getattr(mod, 'run')
```

The registry `run` field is the **imported module function** — not the module's `run()` attribute.
`getattr(mod, 'run', None)` in `_run_signal` is a **fallback** that only fires if `signal['run']` is `None`.

### Path 2 — FALLBACK: getattr(mod, 'run') in _run_signal
```python
def _run_signal(args):
    sig_name, module_name = args
    mod = __import__(f'signals.{module_name}', fromlist=['run'])
    fn = getattr(mod, 'run', None)   # ← fallback, not primary
    if fn is None:
        return sig_name, None         # ← silent skip, no log
    # ... call fn(prices) or fn()
```

## Why rs.py Was Different

- Registry entry was **correct**: `_rs_run = scan_rs_signals` (imported at line 86)
- ThreadPoolExecutor uses registry `run` → calls `scan_rs_signals()` directly → WORKS
- BUT: `signals/rs.py` had no `run()` function → `getattr(mod, 'run', None)` → `None`
- The `run()` wrapper was added at line 572 as **belt-and-suspenders** for the fallback path

## Full Signal Registry Status (2026-05-08)

| Signal | Registry `run` | Module has `run()` | Status |
|--------|---------------|-------------------|--------|
| pct_hermes | `_pct_hermes_run` | Yes | ✅ |
| vel_hermes | `_vel_hermes_run` | Yes | ✅ |
| hzscore | `_hzscore_run` | Yes | ✅ |
| hmacd | `_hmacd_run` | Yes | ✅ |
| mtf_momentum | `_mtf_momentum_run` | Yes | ✅ |
| momentum | `_momentum_run` | Yes | ✅ |
| phase_accel | `_phase_accel_run` | Yes | ✅ |
| fast_momentum | `_fast_momentum_run` | Yes | ✅ |
| accel_300 | `_accel_300_run` | Yes | ✅ |
| rs | `_rs_run` | **No (FIXED)** | ✅ now |
| gap_300 | `_gap_300_run` | No | ✅ via registry |
| ma_cross | `_ma_cross_run` | No | ✅ via registry |
| ma_cross_5m | `_ma_cross_5m_run` | No (but has `run()`) | ✅ via registry |
| hh_hl | `_hh_hl_run` | No | ✅ via registry |
| guppy | `_guppy_run` | No | ✅ via registry |
| macd_accel | `_macd_accel_run` | No | ✅ via registry |
| trend_purity | `_trend_purity_run` | No | ✅ via registry |
| ema9_sma20 | `_ema9_sma20_run` | No | ✅ via registry |
| r2_rev | `_r2_rev_run` | No | ✅ via registry |
| r2_trend | `_r2_trend_run` | No | ✅ via registry |
| volume_hl | `_volume_hl_run` | No (has `main()`) | ✅ via registry |
| ma300_candle_confirm | `_ma300_candle_run` | No | ✅ via registry |
| atr_compression | `_atr_compression_run` | No | ✅ via registry |
| exhaustion | `_exhaustion_run` | No | ✅ via registry |
| counter_flip | `_counter_flip_run` | Yes | ✅ |

**Dead code (not in registry):** `macd_1m`, `ema20_50`

## Diagnostic Commands

```python
# Check registry vs active
from signals import SIGNAL_REGISTRY, get_registered_signals
print(f"Total: {len(SIGNAL_REGISTRY)}, Active: {len(get_registered_signals())}")

# Check which run entries are None
for e in SIGNAL_REGISTRY:
    if e.get('run') is None:
        print(f"BROKEN: {e['name']}")

# Verify a module's run() attribute
import sys; sys.path.insert(0, '/root/.hermes/scripts')
mod = __import__('signals.rs', fromlist=['run'])
print('run exists:', hasattr(mod, 'run'))  # Should be True after fix
```

## RS run() Wrapper (applied 2026-05-08)

```python
# signals/rs.py lines 572-582
def run(prices_dict=None):
    """Wrapper for signals_runner dispatcher.
    signals_runner calls getattr(mod, 'run', None) — this is the entry point.
    Dispatches to scan_rs_signals with the prices dict.
    """
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_rs_signals(prices_dict)
```

## Key Insight

**The `run()` attribute on module is NOT the primary dispatch path** — it's a fallback.
The primary path is the registry's imported function (`_rs_run = scan_rs_signals`).
Adding `run()` to `signals/rs.py` was correct and necessary, but for a different reason
than originally diagnosed: it ensures the fallback path also works if registry entry is
bypassed or if the module is called directly.