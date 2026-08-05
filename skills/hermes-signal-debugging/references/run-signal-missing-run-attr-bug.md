# Bug: _run_signal looks for `run` attr — most signal modules only have `scan_*`

## Symptom
Pipeline log shows signal names listed but with 0 counts. Only `accel_300` and `rs` produce signals. 15 other signal modules (ma_cross, hh_hl, macd_accel, trend_purity, etc.) are completely silent despite having working `scan_*` functions.

## Root Cause
`signals/__init__.py` — `_run_signal()` at lines ~261-285:

```python
mod = __import__(f'signals.{module_name}', fromlist=['run'])
fn = getattr(mod, 'run', None)   # ← BUG: looks for 'run' attr
```

Many signal modules export only `scan_*` functions (e.g., `ma_cross` exports `scan_ma_cross_signals`, NOT `run`). When `getattr(mod, 'run', None)` finds no `run`, it silently returns no signal.

The `SIGNAL_REGISTRY` correctly maps each signal name to its `scan_*` or `run()` entrypoint and stores it as `entry['run']`. But `_run_signal` bypasses the registry entirely — it re-imports the module fresh and looks for a `run` attribute that doesn't exist on most modules.

## Affected Modules (have `scan_*` but NO `run()`)
These 15 modules are registered and will NEVER fire via signals_runner:
- atr_compression
- trend_purity
- ma_cross ← SHORT-capable, T requested this specifically
- r2_trend ← SHORT-capable
- volume_hl
- exhaustion ← SHORT-capable
- hh_hl ← SHORT-capable, T requested this specifically
- macd_accel ← SHORT-capable, T requested this specifically
- ma300_candle_confirm
- ema9_sma20 ← SHORT-capable
- gap_300
- guppy
- r2_rev
- macd_1m
- ema20_50

## Modules that DO have `run()` (7 fire correctly)
- accel_300, rs, vel_hermes, ma_cross_5m, pct_hermes, hzscore, hmacd, mtf_momentum, momentum, phase_accel, fast_momentum, counter_flip, tl_break

## The Fix
`_run_signal` should use the registry's already-resolved function instead of re-importing:

```python
# OLD (broken):
mod = __import__(f'signals.{module_name}', fromlist=['run'])
fn = getattr(mod, 'run', None)

# NEW (correct):
# The registry entry already has the correct callable as entry['run']
# Pass it in or access it directly from the registry
```

Or alternatively, add a `run()` wrapper to each signal module that calls its `scan_*` function.

## Verification
```bash
cd /root/.hermes/scripts
python3 -c "
from signals import SIGNAL_REGISTRY
for e in SIGNAL_REGISTRY:
    fn = e['run']
    has_run = hasattr(fn, '__name__') and fn.__name__ == 'run' or callable(fn)
    # Actually just check the function name
    print(f\"{e['name']}: {fn.__name__}\")
"
```

## See Also
- `signals/__init__.py` — `_run_signal` lines 261-285, `SIGNAL_REGISTRY` lines 200-321
- `signals_runner.py` — calls `run_all_signals()` which calls `_run_signal`