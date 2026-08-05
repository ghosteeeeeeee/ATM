# Standalone Executor Killswitch Pattern — Updated 2026-05-16

## Problem (2026-05-15)

`zscore_pump_hunter.py` and `pump_hunter.py` are standalone trade executors that run independently of the signal pipeline. They have their own position tracking, SL/TP logic, and trade execution — completely separate from `signal_compactor` → `hot-set` → `guardian` flow.

After a reboot, their systemd timers auto-resume. No global killswitch existed.

## Fix Applied — 2026-05-16 (flag split for GHOST TRADES)

**hermes_constants.py** — two separate killswitch systems:

```python
# Old standalone executor (deprecated, disabled via flag)
ZSCORE_PUMP_ENABLED        = False  # controls zscore_pump_hunter.py ONLY

# New pipeline-integrated signal (signals/zscore_pump.py)
ZSCORE_PUMP_NEW_ENABLED    = True   # master kill-switch for signals/zscore_pump.py
ZSCORE_PUMP_PLUS_ENABLED   = True   # LONG directional
ZSCORE_PUMP_MINUS_ENABLED  = True   # SHORT directional
```

**zscore_pump_hunter.py** (old standalone) — uses its own isolated flag:
```python
from hermes_constants import ZSCORE_PUMP_ENABLED
if not ZSCORE_PUMP_ENABLED:
    log("ZSCORE_PUMP_ENABLED=False — block zscore_pump from firing", "OFF")
    return
```

**signals/zscore_pump.py** (new pipeline) — uses its own flags:
```python
from hermes_constants import (
    ZSCORE_PUMP_NEW_ENABLED,   # master gate
    ZSCORE_PUMP_PLUS_ENABLED,  # LONG gate
    ZSCORE_PUMP_MINUS_ENABLED, # SHORT gate
)
if not ZSCORE_PUMP_NEW_ENABLED:
    return 0
```

**signals/__init__.py** — registry MUST use the NEW flag:
```python
ZSCORE_PUMP_NEW_ENABLED, ZSCORE_PUMP_PLUS_ENABLED, ZSCORE_PUMP_MINUS_ENABLED,
# ...
{'name': 'zscore_pump', 'enabled': ZSCORE_PUMP_NEW_ENABLED, 'run': _zscore_pump_run},
```

**CRITICAL BUG FOUND (2026-05-16)**: Registry entry incorrectly used `ZSCORE_PUMP_ENABLED` (old standalone flag=`False`), silently disabling the new pipeline signal. Fixed by updating to `ZSCORE_PUMP_NEW_ENABLED`.

## CRITICAL BUG TO AVOID

When splitting an old standalone signal into a new pipeline-integrated signal:
- **DO NOT** reuse the old standalone's flag name in the new signal's registry
- The old standalone flag is `=False` (disabled) — any registry/import that picks it up silently disables the new signal
- Always create a new flag name (e.g., `_NEW` suffix) for the new pipeline signal's master kill-switch
- Audit `signals/__init__.py` registry entries whenever adding new master/directional flag pairs — the registry is the most commonly missed update

## Pattern for Future Standalone-to-Pipeline Migrations

1. Add `*_NEW_ENABLED` flag (master) + `*_PLUS_ENABLED` / `*_MINUS_ENABLED` (directional) to `hermes_constants.py`
2. Set old standalone's flag to `False` (disabled)
3. Update old standalone to import its own flag only
4. Update new signal to import the NEW flag only
5. Update `signals/__init__.py` imports AND registry entry to use the new flag
6. Verify: `grep -n "ZSCORE_PUMP" files` — new signal file must NOT contain the old flag name

## Files Involved

- `/root/.hermes/scripts/hermes_constants.py` — killswitch flags (LEGACY vs NEW separated)
- `/root/.hermes/scripts/zscore_pump_hunter.py` — old standalone executor (uses `ZSCORE_PUMP_ENABLED`)
- `/root/.hermes/scripts/signals/zscore_pump.py` — new pipeline signal (uses `ZSCORE_PUMP_NEW_ENABLED`)
- `/root/.hermes/scripts/signals/__init__.py` — registry (must use `ZSCORE_PUMP_NEW_ENABLED`)
- `/var/www/hermes/data/zscore-pump.json` — position track file (0 open, closed history)
- `/var/www/hermes/data/hotset.json` — hot-set (new signal goes through this)
- `/var/www/hermes/data/signals_hermes_runtime.db` — signal DB (new signal writes here)