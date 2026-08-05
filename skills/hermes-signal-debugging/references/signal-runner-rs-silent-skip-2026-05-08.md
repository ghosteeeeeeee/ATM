# RS Signal Silent Skip — 2026-05-08

## Root Cause: Missing `run()` Entry Point

`signals/rs.py` only exports `scan_rs_signals()` — no `run()` function.
`signals/__init__._run_signal()` dispatches via `getattr(mod, 'run', None)` → finds nothing → returns `(sig_name, None)` silently every cycle.

RS was **registered and enabled** (`RS_ENABLED=True` in registry) but always silently skipped. Pipeline log shows no error, no warning — completely invisible.

## Diagnosis

```python
# One-liner check — run from /root/.hermes/scripts
python3 -c "import sys; sys.path.insert(0,'.'); mod=__import__('signals.rs',fromlist=['run']); print('has run:', hasattr(mod,'run'))"
# False → broken, signal silently skipped every cycle

# Full registry check
python3 -c "
import sys; sys.path.insert(0,'.')
from signals import SIGNAL_REGISTRY, _resolve_enabled
for e in SIGNAL_REGISTRY:
    print(f\"{'ON ' if _resolve_enabled(e) else 'OFF'} {e['name']:25s} run={'YES' if e.get('run') else 'NONE'}\")
"
# rs → ON, run=NONE → silently broken
```

## The Fix

`signals/rs.py` needs a `run()` wrapper:

```python
def run(prices_dict=None):
    """Entry point for signals_runner — called by _run_signal() via getattr(mod, 'run')."""
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices() if prices_dict is None else prices_dict
    added, tokens = scan_rs_signals(prices)
    return added
```

## Also: CONFLUENCE_REQUIRED Kill-Switch Removed

During this session, the `CONFLUENCE_REQUIRED=False → pass` branch was removed entirely.
Confluence is now binary: **2+ signal types = PASS, 1 signal type = BLOCKED**. No kill-switch.

Before:
```python
if unique_signal_types >= 2: pass_gate = True
elif CONFLUENCE_REQUIRED and unique_signal_types == 1: pass_gate = False  # block
else: pass_gate = True  # CONFLUENCE_REQUIRED=False bypass
```

After:
```python
if unique_signal_types >= 2: pass_gate = True
else: pass_gate = False  # always block single-source
```

**User's explicit rule**: single-source signals never pass, period.

## Diagnostic: Why is only one signal type appearing?

If hot-set shows only `accel_300_long` with zero RS or pct-hermes:

1. `python3 -c "import sys; sys.path.insert(0,'.'); mod=__import__('signals.rs',fromlist=['run']); print('rs run:', hasattr(mod,'run'))"` → False = missing run()
2. `grep "PCT_HERMES_PLUS_ENABLED" hermes_constants.py` → False = flag disabled, signal won't fire
3. Check pipeline log for `DEBUG add_signal BLOCKED: ... PCT_HERMES_PLUS_ENABLED=False`
4. Check DB: `SELECT signal_type, COUNT(*) FROM signals WHERE created_at>datetime('now','-1h') GROUP BY signal_type`