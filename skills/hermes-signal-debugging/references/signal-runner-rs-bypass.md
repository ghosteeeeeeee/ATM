# Signal Runner — _run_signal Registry Bypass Bug

## Bug Summary

**Root cause (2026-05-12)**: `_run_signal()` in `signals/__init__.py` (lines ~275-276) reimports each signal module looking for a `run` attribute, but 15 of 28 signal modules only have `scan_*` functions — no `run` attribute exists. The result is `None` returned silently, and those signal types produce zero output.

## Affected Modules

### Have `run()` function (work correctly)
```
accel_300, rs, vel_hermes, pct_hermes, hzscore, hmacd,
mtf_momentum, mtf_macd, momentum, fast_momentum, phase_accel,
ma_cross_5m, counter_flip, tl_break, guppy, macd_1m, r2_rev, ema20_50, gap_300
```

### Have ONLY `scan_*` functions (silent — blocked by _run_signal bug)
```
ma_cross, atr_compression, trend_purity, hh_hl, macd_accel,
ema9_sma20, volume_hl, ma300_candle_confirm, exhaustion
```

Note: Some of these may also have `run()` — this list reflects what was found 2026-05-12.

## The Bug in Code

```python
# signals/__init__.py — _run_signal() ~line 275
def _run_signal(module_name: str, signal_name: str, prices_dict: dict) -> Optional[List[dict]]:
    mod = __import__(f'signals.{module_name}', fromlist=['run'])
    fn = getattr(mod, 'run', None)   # ← finds None for scan_*-only modules!
    if fn is None:
        return None  # silent no-op
    return fn(prices_dict)
```

## The Fix

The `SIGNAL_REGISTRY` already stores the correct `scan_*` function as the `run` entry:

```python
# SIGNAL_REGISTRY['ma_cross']['run'] = scan_ma_cross_signals ✓
# But _run_signal reimports the module instead of using the registry
```

Fix: replace the `__import__` + `getattr` pattern with a direct call to `entry['run']` from `SIGNAL_REGISTRY`.

## Why It Went Unnoticed

- `accel_300`, `rs`, and `vel_hermes` are the loudest signals and happened to have `run()` functions
- The 10+ silent signal types (ma_cross, hh_hl, macd_accel, trend_purity, etc.) returned nothing silently
- No error was raised — the function just returned `None`

## How to Verify

```bash
cd /root/.hermes/scripts
python3 -c "
import sys; sys.path.insert(0, '.')
from signals import SIGNAL_REGISTRY

# Check which modules have run() vs only scan_*()
has_run = []
scan_only = []
for entry in SIGNAL_REGISTRY:
    name = entry['name']
    mod = __import__(f'signals.{name}', fromlist=['run'])
    if hasattr(mod, 'run'):
        has_run.append(name)
    else:
        scan_only.append(name)

print('Modules with run():', has_run)
print('Modules scan-*-only (SILENT):', scan_only)
"
```

## Impact

- 10+ enabled signal types produce zero output
- Only 3 signal types actually fire via `signals_runner`: accel_300, rs, vel_hermes
- This is why ma_cross, hh_hl, atr_compression, trend_purity, and others appear "broken" despite correct logic