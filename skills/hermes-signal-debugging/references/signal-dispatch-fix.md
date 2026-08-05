# Signal Dispatch Bug — `_run_signal` hardcoded 'run'

**Date:** 2026-05-16  
**Symptom:** New pipeline signals (zscore_pump, ema_angle) returned 0 signals through the pipeline runner but worked fine when called manually.

## Root Cause

In `signals/__init__.py`, the `_run_signal` function always looked for a method named `'run'`:

```python
def _run_signal(sig_name, module_name):
    mod = importlib.import_module(f'signals.{module_name}')
    return getattr(mod, 'run', None)()  # ← hardcoded 'run'!
```

Meanwhile, `name_to_module` dict correctly mapped signal names to function names:
```python
name_to_module = {
    'zscore_pump': 'scan_zscore_pump_signals',
    'ema_angle': 'ema_angle_run',
    ...
}
```

But `_run_signal` never read it — so all signals whose entry point wasn't literally `run()` silently returned `None`.

## Fix

Change `_run_signal` to accept the actual function name as the second argument (`fn_name`), and change the work list to pass `signal['run'].__name__`:

```python
# signals/__init__.py — _run_signal
def _run_signal(sig_name, fn_name):
    mod = importlib.import_module(f'signals.{sig_name}')
    return getattr(mod, fn_name)()  # ← use fn_name, not hardcoded 'run'

# run_all_signals — work list
work_list = [(sig_name, signal['run'].__name__) for sig_name, signal in SIGNAL_REGISTRY.items()]
```

## Pattern for Adding New Signals

When adding a new signal to the pipeline:

1. The signal module must have an entry point function (e.g., `scan_zscore_pump_signals`, `ema_angle_run`)
2. Add to `SIGNAL_REGISTRY` in `signals/__init__.py`
3. **Critical:** If the function name is NOT `run`, you MUST add it to `name_to_module`:
   ```python
   name_to_module = {
       'zscore_pump': 'scan_zscore_pump_signals',   # fn_name, not module_name
       'ema_angle': 'ema_angle_run',
       'accel_300': 'scan_accel_300_signals',
       ...
   }
   ```
4. `_run_signal` passes `fn_name` via `signal['run'].__name__` which is the function's actual string name

## Verification

Run the signal standalone and via the pipeline, compare counts:
```bash
cd /root/.hermes/scripts
python3 -c "
import sys; sys.path.insert(0, '.')
from signals import scan_zscore_pump_signals
prices = get_price_dict()  # your price data source
print(scan_zscore_pump_signals(prices))
"
```

If standalone returns N signals but pipeline returns 0 — check `_run_signal` dispatch.

## Related Triggers in hermes-signal-debugging

- "pipeline signals returning None — dispatcher not reading name_to_module dict"
- "signals work manually but not through pipeline — check _run_signal hardcoded 'run'"
- "new signal not firing in pipeline but works standalone — _run_signal fn_name bug"