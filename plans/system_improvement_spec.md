# Hermes System Improvement Spec

## Problem Statement
Hermes has 35 signals (30 disabled), 35 automations, but no feedback loop, no self-improvement, and no observability. The system generates signals, executes trades, but doesn't learn from outcomes. Every parameter change is manual. Kill switch bugs took 13+ analyses to find.

## Guiding Principle (from Matt Pocock)
> "Build loops into your systems. The harness matters more than the model."

## What We're Building

### 1. Signal Decay Detector (Auto-Disable)
**File:** `scripts/signal_decay_detector.py`
**Timer:** Every 6 hours

Automatically detects when a signal type's WR drops below threshold and disables it.

**Logic:**
- Query signal_outcomes for each signal type (24h, dedup)
- If WR < 30% AND trades >= 5 → flag for disable
- If WR < 20% AND trades >= 3 → immediate disable
- Write disable action to `automation/decay_log.md`
- Send alert via OpenMemory

**Output:** Auto-disables signals without CEO intervention.

### 2. Parameter Auto-Tuner
**File:** `scripts/param_auto_tuner.py`
**Timer:** Every 12 hours

Automatically adjusts SL/TP/trailing based on recent MFE/MAE data.

**Logic:**
- Query last 50 trades for MFE/MAE distribution
- If avg MAE > avg MFE → SL too tight (widen)
- If avg MFE > 2x avg SL → TP too loose (tighten)
- If whipsaw rate > 40% → trailing too tight (widen)
- Apply changes with safety bounds (max 10% change per cycle)
- Log all changes to `automation/tuner_log.md`

**Safety:** Never changes more than 2 parameters per cycle. Never changes by more than 10%. Rolls back if WR drops after change.

### 3. Observability Dashboard
**File:** `scripts/obs_dashboard.py`
**Timer:** Every 5 minutes (background)

Writes real-time metrics to `var/www/hermes/data/obs_metrics.json`.

**Metrics:**
- Trades today / win rate / PnL
- Active signals count / hotset size
- Pipeline health (last run time, errors)
- Token speeds distribution
- Signal type performance (24h)

**Output:** JSON file that can be served by nginx for a simple dashboard.

### 4. Automated Rollback
**File:** `scripts/auto_rollback.py`
**Timer:** After each param_auto_tuner run

Compares performance before/after parameter change. Reverts if degraded.

**Logic:**
- Store parameter snapshot before change
- After 6 hours, compare WR before/after
- If WR dropped by > 5% → revert to snapshot
- Log rollback to `automation/rollback_log.md`

### 5. Error Pattern Analyzer
**File:** `scripts/error_analyzer.py`
**Timer:** Every hour

Scans pipeline logs for recurring errors and alerts on patterns.

**Logic:**
- Parse last hour of pipeline logs
- Count error types
- If same error > 3 times → alert
- If new error type appears → alert
- Store error patterns in `data/error_patterns.json`

## Implementation Order

1. **Signal Decay Detector** — Highest impact. Stops bleeding from decaying signals.
2. **Observability Dashboard** — Quick win. Gives visibility into system state.
3. **Parameter Auto-Tuner** — Medium impact. Automates what CEO does manually.
4. **Error Pattern Analyzer** — Quick win. Catches issues faster.
5. **Automated Rollback** — Safety net for auto-tuner.

## Files to Create
```
scripts/signal_decay_detector.py
scripts/param_auto_tuner.py
scripts/obs_dashboard.py
scripts/auto_rollback.py
scripts/error_analyzer.py
automation/signal_decay_detector_prompt.md
automation/param_auto_tuner_prompt.md
```

## Systemd Timers to Add
```
hermes-signal-decay-detector.timer (6h)
hermes-param-auto-tuner.timer (12h)
hermes-obs-dashboard.timer (5min)
hermes-error-analyzer.timer (1h)
```

## Success Metrics
- Signal decay detected within 6 hours (vs 13+ analyses before)
- Parameter changes are data-driven (not gut feeling)
- System health visible in real-time
- Errors caught within 1 hour (vs next-day CEO review)
- Zero manual parameter tuning needed for routine adjustments
