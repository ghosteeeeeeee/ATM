# Signal Module Audit Pattern

Multi-pass audit pattern for verifying all signal modules have working `run()` wrappers and correct import paths. Run after any batch modification to signal files.

## When to Use

- After adding `run()` wrappers to multiple signal modules
- After moving or refactoring signal scan functions
- When investigating "signal X never fires" reports

## Audit Command

```bash
cd /root/.hermes/scripts
python3 -c "
import sys; sys.path.insert(0,'.')
MODULES = ['ma_cross', 'atr_compression', 'hh_hl', 'macd_accel', 'ema9_sma20',
    'ma300_candle_confirm', 'r2_trend', 'r2_rev', 'gap_300', 'macd_1m',
    'ema20_50', 'exhaustion', 'guppy', 'volume_hl', 'trend_purity']
for mod_name in MODULES:
    try:
        mod = __import__(f'signals.{mod_name}', fromlist=['run'])
        r = mod.run(None)
        print(f'OK   {mod_name:22s} → {type(r).__name__}: {str(r)[:60]}')
    except Exception as e:
        print(f'FAIL {mod_name:22s} → {e}')
" 2>&1 | grep -vE \"^  \[MACD|^  DEBUG|DEBUG add_signal|stale price\"
```

## Known Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| `NameError: name 'scan_xxx' is not defined` | Import path wrong — scan function is in parent dir, not `signals/` | `from ma300_candle_confirm_signals import scan_ma300_candle_signals` (no `signals.` prefix) |
| `NameError: name 'DRY_RUN' is assigned to before global declaration` | `global DRY_RUN` appears before the assignment in the same function | Remove the `global DRY_RUN` line — variable is already module-level |
| File truncated to ~10 lines | Used `write_file()` instead of `patch()` on an existing file | Restore from backup or re-create the file with full content |

## Dual-Path Import Pattern

Some signals have a split structure — a slim `signals/` wrapper file + a parent-dir scanner module with the actual logic:

```
/root/.hermes/scripts/
  ma300_candle_confirm_signals.py   ← 269 lines, has scan_ma300_candle_signals()
  signals/
    ma300_candle_confirm.py         ← 10 lines, run() wrapper that calls parent
```

The wrapper MUST import from parent:
```python
from ma300_candle_confirm_signals import scan_ma300_candle_signals
```

## Verification After Fix

Always run the audit command again after patching. A successful fix shows `OK` with the correct return type (int, tuple, list). Any `FAIL` means the module is still broken.