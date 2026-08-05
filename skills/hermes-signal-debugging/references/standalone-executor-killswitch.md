# Standalone Executor Killswitch Pattern

## Problem (2026-05-15)

`zscore_pump_hunter.py` and `pump_hunter.py` are standalone trade executors that run independently of the signal pipeline. They have their own position tracking, SL/TP logic, and trade execution — completely separate from `signal_compactor` → `hot-set` → `guardian` flow.

After a reboot, their systemd timers (`hermes-zscore-pump-hunter.timer`, `hermes-pump-hunter.timer`) auto-resume. The executors check their own internal state but there was NO global killswitch — so even if you disabled something in `hermes_constants`, the standalone executors would still fire.

## Root Cause

- Both executors import from `hermes_constants` (SHORT_BLACKLIST, etc.) but had NO master kill flag
- Timer services resume on boot automatically
- `zscore_pump` had closed 76 positions in the track file — it was actively trading post-reboot, not "just started working"

## Fix Applied

**hermes_constants.py** — added standalone executor killswitches:

```python
# ── Standalone Executor Killswitches ───────────────────────────────────────────
# pump_hunter and zscore_pump are standalone executors — they manage their own
# positions and bypass the signal pipeline. Killswitches here prevent them from
# firing if enabled/disabled state gets out of sync after reboot.
PUMP_HUNTER_ENABLED        = False  # set False to block pump_hunter from firing
ZSCORE_PUMP_ENABLED        = False  # set False to block zscore_pump from firing
```

**zscore_pump_hunter.py** — added check at top of `scan_and_fire()`:

```python
def scan_and_fire():
    from hermes_constants import ZSCORE_PUMP_ENABLED
    if not ZSCORE_PUMP_ENABLED:
        log("ZSCORE_PUMP_ENABLED=False — block zscore_pump from firing", "OFF")
        return
```

**pump_hunter.py** — same pattern at top of `scan_and_fire()`:

```python
def scan_and_fire():
    from hermes_constants import PUMP_HUNTER_ENABLED
    if not PUMP_HUNTER_ENABLED:
        log("PUMP_HUNTER_ENABLED=False — block pump_hunter from firing", "OFF")
        return
```

## Pattern for Future Standalone Executors

When adding a new standalone executor that bypasses the pipeline:

1. Add `*_ENABLED` flag to `hermes_constants.py` in the Standalone Executor Killswitches section
2. Import and check at the top of the main scan function
3. Log an "OFF" message when blocked so log shows the killswitch fired
4. Default to `False` until explicitly validated

## Files Involved

- `/root/.hermes/scripts/hermes_constants.py` — killswitch flags
- `/root/.hermes/scripts/zscore_pump_hunter.py` — standalone executor
- `/root/.hermes/scripts/pump_hunter.py` — standalone executor
- `/var/www/hermes/data/zscore-pump.json` — position track file (76 closed, 0 open)
- `/var/www/hermes/data/pump-hunter.json` — position track file

## Related Systemd Services

```
hermes-zscore-pump-hunter.timer  — every 1 min, activates hermes-zscore-pump-hunter.service
hermes-pump-hunter.timer         — every 1 min, activates hermes-pump-hunter.service
```

Both timers run even when the executor is killswitched off — the check happens inside the executor, not at the timer level.