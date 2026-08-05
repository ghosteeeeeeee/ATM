# Signal run() Wrapper & Per-Direction Flags — Session 2026-05-12

## Bug: 15 Signal Modules Silently Skipped by signals_runner

**Root cause:** `signals_runner._run_signal()` does a fresh `__import__('signals.{name}')` then
looks for `mod.run` directly — it does NOT use the registry. All 15 modules lacked `run()`
wrappers → `getattr(mod, 'run', None)` returned `None` → signals silently died with zero output.

**Pattern discovered:**
```python
# signals_runner._run_signal ~line 40:
mod = __import__(f'signals.{module_name}', fromlist=['run'])
fn = getattr(mod, 'run', None)
if fn is None: return None  # ← signal silently skipped
return fn(prices) or fn()
```

The registry (`signals/__init__.py`) only sets `enabled` at startup — it is NOT consulted at runtime.
Every signal module needs a `run()` wrapper at module level (not inside `if __name__` block).

## All 15 Modules Fixed — `run()` Wrapper Pattern

```python
# signals/<name>.py — at bottom of file, BEFORE `if __name__` block
def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    from signals.<name> import scan_<name>_signals
    result = scan_<name>_signals(prices_dict)
    # Normalize return
    if isinstance(result, int): return result
    elif isinstance(result, tuple): return result[0]  # (count, tokens_set)
    elif isinstance(result, list): return len(result)
    return 0
```

**Modules fixed:** ma_cross, atr_compression, trend_purity, hh_hl, macd_accel, ema9_sma20,
volume_hl, ma300_candle_confirm, r2_trend, r2_rev, gap_300, macd_1m, ema20_50, exhaustion, guppy

## ma300_candle_confirm — Special Case (Import Failure)

The scan function lives in the PARENT directory (`ma300_candle_confirm_signals.py`), not in
`signals/`. The wrapper MUST re-export it:

```python
# signals/ma300_candle_confirm.py — BEFORE run() function
from ma300_candle_confirm_signals import scan_ma300_candle_signals
```

Without this, runtime ImportError: cannot import name 'scan_ma300_candle_signals' from 'signals.ma300_candle_confirm'.

## Bug: MA_CROSS_PLUS_ENABLED Was Ignored

`ma_cross.run()` was calling `scan_ma_cross_signals()` which checked `MA_CROSS_ENABLED` (top-level)
but NOT `MA_CROSS_PLUS_ENABLED` or `MA_CROSS_MINUS_ENABLED`. Result: golden cross LONG signals
fired even though `MA_CROSS_PLUS_ENABLED = False`.

**Pattern:** Single-flag signals (no +/- split) that emit both directions need per-direction checks
inside their scan function, not just at the top level.

## All 26 Per-Direction Flags Now in hermes_constants (2026-05-12)

```
ATR_COMPRESSION_PLUS_ENABLED   = True
ATR_COMPRESSION_MINUS_ENABLED  = True
EMA9_SMA20_PLUS_ENABLED        = True
EMA9_SMA20_MINUS_ENABLED       = True
EXHAUSTION_PLUS_ENABLED        = True
EXHAUSTION_MINUS_ENABLED       = True
GUPPY_PLUS_ENABLED             = False
GUPPY_MINUS_ENABLED            = False
HH_HL_PLUS_ENABLED            = True
HH_HL_MINUS_ENABLED           = True
MA300_CANDLE_PLUS_ENABLED     = True
MA300_CANDLE_MINUS_ENABLED   = True
MACD_ACCEL_PLUS_ENABLED       = True
MACD_ACCEL_MINUS_ENABLED      = True
R2_REV_PLUS_ENABLED           = False
R2_REV_MINUS_ENABLED          = False
R2_TREND_PLUS_ENABLED         = False
R2_TREND_MINUS_ENABLED        = True
TREND_PURITY_PLUS_ENABLED    = True
TREND_PURITY_MINUS_ENABLED   = True
VOLUME_HL_PLUS_ENABLED        = True
VOLUME_HL_MINUS_ENABLED       = True
EMA20_50_PLUS_ENABLED         = True
EMA20_50_MINUS_ENABLED        = True
MACD_1M_PLUS_ENABLED          = True
MACD_1M_MINUS_ENABLED         = True
```

Previously missing: `EMA20_50_ENABLED` (was no flag), `MACD_1M_ENABLED` (was no flag).
Both now have PLUS/MINUS variants too.

## Per-Direction Kill-Switch Pattern for Loop-Based Signals

For signals that loop over `for direction in ['LONG', 'SHORT']`:

```python
for direction in ['LONG', 'SHORT']:
    # ── Per-direction kill-switch ─────────────────────────────────────────
    from hermes_constants import <NAME>_PLUS_ENABLED, <NAME>_MINUS_ENABLED
    if direction == 'LONG' and not <NAME>_PLUS_ENABLED:
        continue
    if direction == 'SHORT' and not <NAME>_MINUS_ENABLED:
        continue
    sig = detect_signal(...)
```

For signals that return a signal dict with `direction` already set:

```python
if sig is None:
    continue
# ── Per-direction kill-switch ─────────────────────────────────────────
from hermes_constants import <NAME>_PLUS_ENABLED, <NAME>_MINUS_ENABLED
if sig['direction'] == 'LONG' and not <NAME>_PLUS_ENABLED:
    continue
if sig['direction'] == 'SHORT' and not <NAME>_MINUS_ENABLED:
    continue
sid = add_signal(...)
```

## Verifying All Signals Compile and Run

```bash
cd /root/.hermes/scripts
python3 -m py_compile \
  signals/__init__.py hermes_constants.py \
  signals/ma_cross.py signals/gap_300.py signals/ma_cross_5m.py \
  signals/atr_compression.py signals/ema9_sma20.py \
  signals/exhaustion.py signals/guppy.py signals/hh_hl.py \
  signals/macd_accel.py signals/r2_rev.py signals/r2_trend.py \
  signals/trend_purity.py signals/volume_hl.py \
  signals/ma300_candle_confirm.py signals/ema20_50.py signals/macd_1m.py \
  ma300_candle_confirm_signals.py \
  && echo "All compile OK"

# Test run() on each
python3 << 'EOF'
import sys; sys.path.insert(0,'.')
from signals import SIGNAL_REGISTRY
ok, fail = [], []
for e in SIGNAL_REGISTRY:
    mod = __import__(f'signals.{e["name"]}', fromlist=['run'])
    r = getattr(mod, 'run', None)
    if r: ok.append(e['name'])
    else: fail.append(e['name'])
print(f"run() available: {len(ok)}/{len(SIGNAL_REGISTRY)}")
if fail: print(f"  MISSING: {fail}")
EOF
```

## Testing Per-Direction Kill-Switch

```python
import hermes_constants as hc
hc.MA_CROSS_PLUS_ENABLED = False
hc.MA_CROSS_MINUS_ENABLED = True

from signals import ma_cross
result = ma_cross.run()
# Result should be 0 if all signals were LONG
# LONG signals blocked, SHORT signals pass
```