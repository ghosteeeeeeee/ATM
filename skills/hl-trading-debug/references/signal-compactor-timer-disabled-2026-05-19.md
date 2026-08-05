# Signal Compactor Timer Disabled — Hot-Set Stays Empty
**Date:** 2026-05-19
**Status:** Root cause found, fix pending

## Symptom

AXS:LONG entered hot-set at 14:35-14:38 (cycle 29881-29883) with `rs-s1944,zscore-pump+`, score=0.00.
Next cycle (29884+): hot-set is empty. AXS never reaches decider_run → never becomes a live trade.
`decider_run` logs: `🧊 [HOT-SET] hotset.json is empty — no signals survived compaction` every cycle.

signal_compactor.timer is DISABLED: `systemctl list-units` shows `hermes-signal-compactor.timer   inactive (dead)`

## Root Cause

`/etc/systemd/system/hermes-signal-compactor.timer` exists but is not active.

```
$ systemctl list-units | grep signal-compactor
hermes-signal-compactor.timer   inactive (dead)
```

Pipeline.timer (hermes-pipeline.timer) runs every 1 min and calls `run_pipeline.py` which includes `signal_compactor` in `STEPS_EVERY_MIN`. But signal_compactor.py appears to run without producing signals — or produces empty results when the timer is dead.

## Diagnostic

Check timer status:
```bash
systemctl status hermes-signal-compactor.timer
systemctl list-timers | grep signal-compactor
```

Check hot-set:
```bash
cat /var/www/hermes/data/hotset.json | python3 -m json.tool
```

Check pipeline log for signal_compactor output:
```bash
grep -a "signal_compactor" /root/.hermes/logs/pipeline.log | tail -20
grep -a "COMPACTOR\|compactor\|HOT-SET" /root/.hermes/logs/pipeline.log | tail -20
```

## Fix

Re-enable and start the timer:
```bash
systemctl enable hermes-signal-compactor.timer
systemctl start hermes-signal-compactor.timer
systemctl status hermes-signal-compactor.timer
```

Verify hot-set starts filling:
```bash
watch -n 5 'cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Tokens: {len(d)}\")"' 2>/dev/null || cat /var/www/hermes/data/hotset.json
```

## AXS Disappeared Because

1. signal_compactor.timer was disabled → signal_compactor not running on its own schedule
2. pipeline.timer calls signal_compactor via run_pipeline.py but signal_compactor was producing empty results (or timer state affects its behavior)
3. AXS entered hot-set at 14:35 (confirmed in pipeline.log)
4. Hot-set went empty at 14:39 (cycle 29882 → 29884, PRESERVE-EMPTY logged but entries disappeared anyway)
5. decider_run at 14:44+ saw empty hot-set → no execution

## Related Issue

Ghost trades (ADA/UNI) opened during the window when signal_compactor was dead AND live_trading was briefly enabled (14:52-14:54). AXS was blocked from live trading because hot-set was empty (signal_compactor dead) AND live_trading was disabled (False in hermes_constants).

## Lesson

`signal-compactor.timer` being inactive explains why hot-set stays empty even though pipeline.timer is running. The systemd timer is the orchestrator — if it's dead, signal_compactor may not fire correctly even when called from run_pipeline.py.