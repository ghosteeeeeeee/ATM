# Signal Module `run()` Wrapper Pattern

## The Problem

`s信号_runner._run_signal()` uses this pattern:
```python
mod = __import__(f'signals.{module_name}', fromlist=['run'])
fn = getattr(mod, 'run', None)  # ← requires run() attribute on module
```

It does **NOT** use the registry's stored `scan_*` reference — it re-imports the module fresh and looks for a `run` attribute. Without it, the signal silently returns `None` and produces nothing.

**Symptom:** Only signals with actual `run()` functions on their modules fire (accel_300, rs, vel_hermes). 15 other signals appear enabled in the registry but produce zero signals.

**Root cause confirmed 2026-05-12:** signal_gen called `scan_*` directly — `signals_runner` (the canonical runner since 2026-05-06) wraps with `run()`.

## The Fix

Add this wrapper at the end of any signal module:

```python
def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    result = scan_<signal>_signals(prices_dict)
    return len(result) if isinstance(result, list) else result
```

## Return value conventions

| Signal module type | `run()` returns |
|---|---|
| Returns list of dicts (ma_cross, hh_hl, r2_trend) | `len(result)` |
| Returns `Tuple[int, set]` (atr_compression, macd_accel) | `result[0]` |
| Returns `Tuple[int, list]` (rs, ma300_candle_confirm) | `len(result[1])` or `result[0]` |
| Returns bare int (exhaustion, trend_purity) | `result` |

## Modules that needed the wrapper (fixed 2026-05-12)

```
ma_cross, atr_compression, trend_purity, hh_hl, macd_accel,
ema9_sma20, volume_hl, ma300_candle_confirm, r2_trend,
r2_rev, gap_300, macd_1m, ema20_50, exhaustion, guppy
```

## Verification command

```bash
cd /root/.hermes/scripts
python3 -c "
import sys; sys.path.insert(0,'.')
from signals import SIGNAL_REGISTRY
for e in SIGNAL_REGISTRY:
    m = e['name'].replace('-','_').replace('+','plus').replace('-','minus')
    try:
        mod = __import__(f'signals.{m}', fromlist=['run'])
        print(f'  {\"✓\" if hasattr(mod,\"run\") else \"✗\"} {e[\"name\"]}')
    except: print(f'  ? {e[\"name\"]}')
"
```

## Pitfall: SyntaxError "name assigned before global declaration"

When adding `run()` wrapper before an existing `if __name__ == '__main__':` block that uses `global DRY_RUN`, Python evaluates the global declaration at parse time. The `run()` function (added earlier) may confuse Python's resolution.

**Fix:** Move `import argparse` and any `args = parser.parse_args()` calls **before** the `global DRY_RUN` line. Or remove `global DRY_RUN` entirely if DRY_RUN is module-level and only set, never read within the block.