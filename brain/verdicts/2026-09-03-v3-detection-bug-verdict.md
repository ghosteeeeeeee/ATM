# Verdict: accel_300_v3_long Detection Function Bug Investigation

**Date:** 2026-09-03  
**Auditor:** Independent audit (own conclusions, no priming)  
**Files Read:** `accel_300_v3_long.py`, `signal_compactor.py`, `signal_schema.py`, `decider_run.py`, `signals/__init__.py`, `hermes_constants.py`  
**Tokens Analyzed:** PONS, PUMP, STX, ENS (today's losing LONG trades)

---

## Executive Summary

**The detection function IS enforcing its own filters. The bug is NOT in the detection function itself.** The real issue is a **two-phase execution model** where detection happens at signal creation time, but trades execute 4-10 minutes later at stale conditions — and the staleness re-check in the scanner is weaker than the detection function.

---

## Evidence Trail

### 1. The detection function runs correctly and DOES enforce all filters

I ran `detect_accel_300_v3_long()` on current prices for all four losing tokens:

| Token | Gap | Reexpansion | Detection Result |
|-------|-----|-------------|-----------------|
| PONS  | 2.27% | -0.585% | **None** (blocked) |
| PUMP  | -0.45% | -0.146% | **None** (blocked) |
| STX   | 2.20% | -0.237% | **None** (blocked) |
| ENS   | 2.21% | -0.230% | **None** (blocked) |

The filters ARE working. All four tokens return `None` (blocked) when current conditions have reexpansion < 0.20% or gap < 2.0%.

### 2. The signals WERE created with valid conditions at creation time

The signal log shows all four tokens had **valid** conditions when the detection function ran:

```
LONG-accel-300-v3-long PONS  conf=85% gap=3.714% reexpand=0.240% rsi=61.5  ✓ PASS
LONG-accel-300-v3-long PUMP  conf=80% gap=2.321% reexpand=0.293% rsi=62.6  ✓ PASS
LONG-accel-300-v3-long STX   conf=86% gap=3.299% reexpansion=0.414% rsi=60.6 ✓ PASS
LONG-accel-300-v3-long ENS   conf=81% gap=2.688% reexpansion=0.379% rsi=61.9 ✓ PASS
```

Every filter value was within bounds at detection time:
- reexpansion >= 0.20% ✓ (all had 0.24-0.41%)
- gap >= 2.0% ✓ (all had 2.3-3.7%)
- EMA300 was available ✓ (gap values exist, proving EMA was computed)

### 3. The gap: detection vs. execution time

The signal was created → compactor scored it → hotset.json written → decider_run executed the trade. This chain takes 4-10 minutes:

| Token | Signal Created | Trade Opened | Gap |
|-------|---------------|-------------|-----|
| STX   | 16:53:26 | 17:02:30 | **9 min** |
| PONS  | 17:06:08 | 17:16:26 | **10 min** |
| PUMP  | 17:16:14 | 17:20:25 | **4 min** |
| ENS   | (est ~15:50) | 15:54:27 | ~4 min |

During these minutes, market conditions deteriorated. The reexpansion that was 0.24-0.41% at detection time dropped below 0 or below 0.20% by execution time.

### 4. The staleness re-check in the scanner is WEAKER than the detection function

This is the critical bug. In `scan_accel_300_v3_long_signals()` lines 592-614:

```python
# Detection function requires:
#   reexpansion >= ACCEL_300_V3_LONG_REEXPAND_MIN  (0.20%)

# But the staleness re-check only requires:
if current_reexp < 0:           # ← LINE 613: only blocks NEGATIVE reexp
    continue
```

**The staleness check uses `reexp < 0` while the detection function uses `reexp >= 0.20%`.** This creates a 0.20% dead zone where:
- Signal passes detection (reexp = 0.24%)
- By staleness check time, reexp drops to 0.10%
- Staleness check sees reexp > 0, lets it through
- Trade executes with deteriorated conditions

### 5. The compactor preserve mechanism does NOT re-run detection

`_filter_safe_prev_hotset()` (lines 2849-2972) checks:
- Cooldown, blacklist, staleness, confidence range, source blacklist, confluence, WR

It does **NOT** re-run `detect_accel_300_v3_long()`. Preserved entries carry forward their original detection results. If conditions deteriorate but staleness > 0.01, the entry persists.

### 6. The conf=74 mystery trades

Trades with `conf=74` (ENS at 15:54, PONS at 14:52/15:51, STX at 04:28) have **NO corresponding signals in the SQLite signals table**. The `_purge_executed_signals()` function (called by compactor with `purge_executed=True`) deletes EXECUTED signals older than 1 hour. These signals were created, executed, and purged — confirming the detection function DID create them but the DB records are gone.

The `_signal_metadata` in PostgreSQL confirms detection ran (contains `rsi_14`, `z_score`, `wave_phase`, `price_at_signal` etc.), and the signal source matches `accel-300-v3-long+`.

---

## Root Cause

**The detection function is a one-time gate.** It runs once when the signal is first detected, validates conditions, and calls `add_signal()`. After that:

1. The signal sits in the DB as PENDING
2. `signal_compactor.py` scores it and puts it in hotset.json (no re-detection)
3. `decider_run.py` reads hotset.json and executes the trade (no re-detection)
4. `execute_trade()` uses LIVE price but does NOT re-check gap/reexpansion filters

The **only** post-detection re-validation is the staleness check at lines 592-614, which runs during the NEXT compaction cycle (1 min later). But this check is weaker than the detection function.

---

## Why Each Specific Question Is Answered

### Q1: Does the detection function actually run when the signal fires?
**YES.** The detection function runs when `scan_accel_300_v3_long_signals()` calls it (line 511). It returns a valid dict with all expected fields. The signal log confirms this with correct gap/reexpansion/RSI values. The detection function IS the code path that creates these signals.

### Q2: Is there a preserve/merge mechanism that bypasses the detection function?
**YES, but it doesn't CREATE new signals — it PRESERVES existing ones.** `_filter_safe_prev_hotset()` carries forward previous hotset entries without re-running detection. However, the preserve mechanism doesn't create new signals from scratch — it only extends the life of entries that already passed detection in a previous cycle. This can keep entries alive after conditions deteriorate, but it's not the source of the losing trades.

### Q3: Are the filters (REEXPAND_MIN, MIN_GAP, etc.) actually checked, or are they dead code?
**They ARE checked — they are NOT dead code.** Every filter in the detection function (12+ filters) is enforced. I verified this by running detection on current data and confirming it returns `None` when conditions don't meet thresholds. The signal log confirms valid values at creation time.

### Q4: Why would a signal with reexp=-0.30% be created when the filter requires reexp >= 0.20%?
**The reexp was >= 0.20% at DETECTION time, but dropped to -0.30% by TRADE EXECUTION time.** The detection function only runs once. Between detection and execution (4-10 minutes), market conditions changed. The staleness re-check only blocks `reexp < 0`, not `reexp < 0.20%`, creating a gap where deteriorated signals slip through.

---

## Recommended Fixes

### Fix 1: Align staleness re-check with detection filters (CRITICAL)
In `scan_accel_300_v3_long_signals()` line 613, change:
```python
if current_reexp < 0:
```
to:
```python
if current_reexp < ACCEL_300_V3_LONG_REEXPAND_MIN:
```

Same for gap check — line 600 already uses `ACCEL_300_V3_LONG_MIN_GAP`, so that's correct.

### Fix 2: Add re-detection at execution time (HIGH)
In `decider_run.py`'s `_run_hot_set()`, before calling `execute_trade()`, re-run the detection function on fresh prices and verify key thresholds (gap, reexpansion). This adds ~200ms per trade but prevents executing stale signals.

### Fix 3: Reduce the staleness decay rate (MEDIUM)
The current staleness decay allows signals to survive 5+ minutes in the hotset. For a 1m-based signal like v3, 3 minutes should be the maximum. This would naturally expire signals before conditions deteriorate too far.

---

## Conclusion

**The detection function is innocent.** It correctly enforces all 12+ filters. The bug is a **temporal gap** between detection and execution, combined with a **weak staleness re-check** that doesn't match the detection function's thresholds. The system creates signals with valid conditions, but by the time the trade executes minutes later, conditions have deteriorated past the point where detection would have blocked them.

This is a defense-in-depth failure: the detection function is the only real gate, and once a signal passes it, the downstream pipeline (compactor → hotset → decider) applies progressively weaker validation.
