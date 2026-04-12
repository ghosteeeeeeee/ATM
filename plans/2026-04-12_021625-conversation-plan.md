# Plan: Pipeline Reliability — Circuit Breaker, Health Monitoring, Watchdog

**Date:** 2026-04-12
**Status:** Planning only — not executed

---

## Goal

Add three layers of operational resilience to the Hermes trading pipeline so failures are caught, contained, and visible — not silent.

---

## Current Context

- Live trading is ON (`hype_live_trading.json`)
- Pipeline runs every 10 min via `decider-run.py` + `signal_gen.py` + `guardian.py`
- Errors currently log to `trading.log` and `errors.log` but:
  - No circuit-breaker halts a failing step mid-pipeline
  - No visibility into whether signals *should have* fired but didn't
  - No heartbeat to alert when a scheduled step never ran

---

## Task 3: Circuit-Breaker + Error Tracing (ERR Breadcrumbs)

### Problem
When a pipeline step throws an error, execution continues and the failure is only visible in logs. No way to know which step failed, how far the pipeline got, or whether downstream steps ran with bad state.

### Approach
1. Add `ERR breadcrumbs` — a `pipeline_steps.json` log written by each step at entry/exit
2. Each step writes: `{step: "signal_gen", status: "START|FAIL|SUCCESS", ts: "...", error: "..."}`
3. On any uncaught exception in a cron cycle, dump the breadcrumb trail to `errors.log`
4. Add a circuit-breaker flag in `brain/pipeline_state.json`: if any step fails 3 consecutive cycles, mark that step as `DEGRADED` and skip it for 1 cycle before retrying

### Files likely to change
- `scripts/signal_gen.py` — add breadcrumb at top/bottom of `run()`
- `scripts/ai_decider.py` — add breadcrumb at top/bottom of `run_llm_compaction()` and `decide_signals_batch()`
- `scripts/guardian.py` — add breadcrumb at top/bottom of guardian loop
- `scripts/decider-run.py` — add breadcrumb for overall orchestration
- `brain/pipeline_state.json` — new file for circuit-breaker state

### Tests
- Kill `signal_gen` mid-run, confirm breadcrumb shows FAIL and next cycle skips signal_gen
- Confirm `errors.log` contains breadcrumb trail after a deliberate exception

---

## Task 4: Signal-Level Health Monitoring

### Problem
System can silently fail to generate signals for tokens that should have triggered — e.g., RSI drops below 30 but no `rsi-confluence` signal appears. No baseline to compare "what should have fired" vs "what actually fired".

### Approach
1. Define "expectation rules" — conditions that should produce signals:
   - RSI crosses below 30 → expect `rsi-confluence` LONG signal within 5 min
   - RSI crosses above 70 → expect `rsi-confluence` SHORT signal within 5 min
   - MACD histogram crosses zero → expect `mtf_macd` signal within 5 min
   - Z-score crosses ±2.5 → expect momentum signal within 5 min
2. After each `signal_gen` run, compare fired signals against expected signals
3. Log `SIGNAL_GAP: expected=[...], got=[...]` when gap detected
4. After 3 consecutive gap cycles, raise an alert to `trading.log` + optionally Telegram

### Files likely to change
- `scripts/signal_gen.py` — add expectation tracking state to `__init__` or module-level dict
- `brain/signal_expectations.json` — new file (persisted across cycles)

### Tests
- Artificially suppress RSI signal generation, confirm gap is detected and reported

---

## Task 5: WATCHDOG Heartbeat — Alert When Pipeline Steps Don't Run

### Problem
If a cron job fails to fire, or a step exits early without logging, there's no alert. The system can go silent and no one knows.

### Approach
1. Each pipeline step writes a heartbeat timestamp to `brain/heartbeat.json`:
   ```json
   {
     "signal_gen": "2026-04-12T02:15:00Z",
     "ai_decider": "2026-04-12T02:15:03Z",
     "guardian": "2026-04-12T02:15:08Z",
     "decider_run": "2026-04-12T02:15:00Z"
   }
   ```
2. A new `scripts/watchdog.py` runs every 5 min via cron
3. It reads `heartbeat.json` and checks each step's last run time
4. If any step hasn't run in > 2x its expected interval (e.g., `signal_gen` > 20 min), fire:
   - A `WATCHDOG_ALERT` to `errors.log`
   - A Telegram message to T
   - Optionally restart the missing step's cron

### Files likely to change
- `scripts/watchdog.py` — new file
- `scripts/signal_gen.py` — add heartbeat write at end of `run()`
- `scripts/ai_decider.py` — add heartbeat write at end of compaction cycle
- `scripts/guardian.py` — add heartbeat write each loop iteration
- `brain/heartbeat.json` — new file
- systemd: add `hermes-watchdog.timer` (every 5 min)

### Tests
- Stop `signal_gen` cron for 30 min, confirm watchdog fires alert
- Confirm Telegram message received (if configured)

---

## Risks & Tradeoffs

- **Heartbeat spam:** If steps run frequently, a single late cycle could trigger false watchdog alerts. Mitigate: use 2x interval threshold, not 1x.
- **Signal gap false positives:** During low-volatility periods, no signals may be expected. Only alert on 3 consecutive gap cycles.
- **Circuit-breaker skip:** Skipping a step 1 cycle means a potential missed trade. Circuit-breaker should log prominently so T can manually override.
- **Pipeline state file corruption:** If `pipeline_state.json` gets corrupted, the circuit-breaker could permanently disable a step. Add a try/except with fallback to re-enable on startup.

---

## Open Questions

1. Should watchdog alerts go to Telegram directly, or route through an existing alert channel (e.g., the gateway)?
2. Should circuit-breaker automatically disable a step for 1 cycle, or just log a warning and let T decide?
3. Is there an existing notification system (Telegram bot, Discord webhook) already configured for alerts?
