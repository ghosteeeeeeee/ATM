# Plan: Pipeline Reliability — Circuit Breaker, Health Monitoring, Watchdog

**Date:** 2026-04-12
**Status:** Planning only — not executed
**Updated:** After confirming existing infrastructure

---

## Goal

Add three layers of operational resilience to the Hermes trading pipeline so failures are caught, contained, and visible — not silent.

---

## What Already Exists

| Feature | Exists | Where |
|---|---|---|
| Pipeline heartbeat | ✅ | `pipeline_heartbeat.json` — `signal_gen`, `ai_decider`, `decider_run`, `position_manager` all write to it |
| Heartbeat staleness check | ✅ | `wasp.py` — warns if heartbeat > 15 min old |
| Circuit-breaker (signal types) | ✅ | `ai_decider.py` — disables signal sources after 10 consecutive failures |
| ERR breadcrumbs | ❌ | Not implemented |
| Signal-gap monitoring | ❌ | Not implemented |
| Watchdog Telegram alerts | ❌ | Not implemented |
| Watchdog auto-restart | ❌ | Not implemented |

---

## Task 3: ERR Breadcrumbs — Log Each Pipeline Step Entry/Exit per Cycle

### Problem
When a pipeline step throws an error, the exception logs to `errors.log` but there's no structured record of: (a) which step was running, (b) what state it was in, (c) whether subsequent steps ran with stale/bad state.

### Approach
1. Create `brain/pipeline_steps.json` — a per-cycle step log
2. Each step, at entry, writes: `{step: "signal_gen", event: "START", ts: "..."}`
3. Each step, at successful exit, overwrites with: `{step: "signal_gen", event: "SUCCESS", ts: "..."}`
4. On any uncaught exception mid-cycle, the last-write-wins entries remain visible — showing exactly which step failed
5. On pipeline startup in `decider-run.py`, check if `pipeline_steps.json` has any `FAIL` events still present from a previous cycle → if so, log them to `errors.log` and clear them (prevents stale breadcrumbs from being confused with current cycle)

### Where to add breadcrumbs
| File | Step name | Where |
|---|---|---|
| `scripts/signal_gen.py` | `signal_gen` | top of `run()`, bottom of `run()` |
| `scripts/ai_decider.py` | `ai_decider` | top of `run_llm_compaction()`, bottom of `run_llm_compaction()` |
| `scripts/ai_decider.py` | `ai_decider_batch` | top of `decide_signals_batch()`, bottom |
| `scripts/hl-sync-guardian.py` | `guardian` | top of guardian loop, bottom each iteration |
| `scripts/decider_run.py` | `decider_run` | top/bottom of `main()` |

### Files to change
- `scripts/signal_gen.py` — add `_log_step()` calls
- `scripts/ai_decider.py` — add `_log_step()` calls
- `scripts/hl-sync-guardian.py` — add `_log_step()` calls
- `scripts/decider_run.py` — add `_log_step()` calls
- `brain/pipeline_steps.json` — created automatically (add to `.gitignore`)

### Validation
```
# Test: kill signal_gen mid-run, confirm pipeline_steps.json shows FAIL
# Expected: pipeline_steps.json contains event:FAIL for signal_gen after kill
```

---

## Task 4: Signal-Level Health Monitoring (Signal-Gap Detection)

### Problem
System can silently fail to generate signals for tokens that should have triggered — no baseline to compare "expected" vs "actual".

### Approach
1. Define "expectation rules" — conditions that should produce signals:
   - RSI crosses below 30 → expect `rsi-confluence` LONG signal within 5 min
   - RSI crosses above 70 → expect `rsi-confluence` SHORT signal within 5 min
   - MACD histogram crosses zero → expect `mtf_macd` signal within 5 min
   - Z-score crosses ±2.5 → expect momentum signal within 5 min
2. After each `signal_gen` run, compare fired signals against expected signals
3. Log `SIGNAL_GAP: expected=[...], got=[...]` when gap detected
4. After 3 consecutive gap cycles, raise a CRITICAL alert to `errors.log`

### Files to change
- `scripts/signal_gen.py` — add `_check_signal_gaps()` called at end of `run()`
- `brain/signal_expectations.json` — new file (persisted state: last_triggered conditions + gap counts)

### Tests
- Suppress RSI signal generation artificially, confirm gap is detected after 3 cycles

---

## Task 5: Watchdog Heartbeat — Alert When Steps Don't Run

### What exists
- `pipeline_heartbeat.json` — all steps write timestamps
- `wasp.py` — checks heartbeat is < 15 min old, logs WARNING

### What is missing
- No Telegram/Discord alert when a step is missing
- No auto-restart of the missing step's cron
- No check for individual step staleness (WASP only checks the whole file age)

### Approach
1. Extend `wasp.py`'s `check_pipeline()` to also alert on individual step staleness:
   - `signal_gen` > 15 min → ERROR (should run every 10 min)
   - `ai_decider` > 15 min → ERROR
   - `guardian` > 5 min → ERROR (runs every 60s)
2. Add Telegram notification from WASP (check `auth.json` for Telegram creds)
3. Document how to add auto-restart as a future enhancement (not implementing now)

### Files to change
- `scripts/wasp.py` — enhance `check_pipeline()` with per-step thresholds and Telegram alert
- `scripts/signal_gen.py` — `decider_run` heartbeat is currently the one that's stale (02:02 vs 02:12) — investigate why `decider_run` hasn't updated since 02:02

### Immediate flag
```
Current heartbeat shows decider_run: 2026-04-12T02:02:12Z (10 min stale)
All other steps updated at 02:12. decider_run may not be running its 10-min cycle.
```

---

## Task 5b: Investigate decider_run heartbeat staleness (02:02 vs 02:12)

**Current state:** `decider_run` heartbeat is 10 minutes behind all other steps.

### Files to check
- `scripts/decider_run.py` — `_update_decider_heartbeat()` at line 334
- systemd timer: `hermes-decider-run.timer` — is it still active?

---

## Risks & Tradeoffs

- **Breadcrumb state pollution:** If a step crashes, its FAIL entry stays in `pipeline_steps.json` until next successful run. This is fine — it serves as a crash witness. Just need to clear on startup.
- **Signal-gap false positives:** Low-volatility periods have no signals expected. Use 3-cycle consecutive gap before alerting.
- **Telegram spam:** If heartbeat alerts fire on every late cycle, T will mute them. Use > 2× interval as threshold, not > 1×.
- **decider_run investigation:** If the heartbeat staleness is a systemd timer issue, fixing it is critical — it means `decider_run` hasn't orchestrated anything for 10+ min.

---

## Open Questions

1. Should watchdog alerts go to Telegram directly, or route through the gateway notification system?
2. Should circuit-breaker automatically disable a step for 1 cycle, or just log and let T decide?
3. What Telegram bot/token is configured in `auth.json` — is there an existing alert channel?
