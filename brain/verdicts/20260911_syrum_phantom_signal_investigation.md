# 🔍 SYRUP Phantom Signal Investigation — Sep 10, 2026

**Investigator:** Hermes Trading System  
**Date:** Sep 11, 2026  
**Trade:** #15196 — SYRUP SHORT  
**Status:** CLOSED (SL hit, -$0.14)

---

## Executive Summary

The SYRUP SHORT trade #15196 was executed legitimately through the pipeline, but the triggering signal (ID 1608289) has been **purged from the SQLite signals database** by the normal `_purge_executed_signals` cleanup mechanism. This is **not a phantom trade** — it was a real signal that was created, executed, and cleaned up per design. The mystery stems from a gap in the signal ID sequence and the NULL `signal_created_at` field.

**Root Cause:** Normal signal lifecycle — create → approve → execute → purge.  
**Confidence Mismatch:** The 99% confidence was **calculated** by `get_approved_signals()` (base 78% + diversity bonus + hot bonus), not the raw signal confidence.  
**signal_created_at NULL:** The `decider_run.py` code never passes `--signal-created-at` to `brain.py` — this is a known limitation affecting 90.8% of all trades.

---

## FINDINGS

### FINDING 1: Signal 1608289 Was Purged After Execution (NOT Phantom)

**EVIDENCE:**
```
Signal ID Gap in SQLite:
  ID 1608288: NEAR SHORT rs-r31 conf=84.8 created=2026-09-10 12:40:13
  [ID 1608289: MISSING — gap in sequence]
  ID 1608290: BLUR SHORT pump-chain- conf=88.0 created=2026-09-10 12:42:05
```

The pipeline log at 12:48:22 shows:
```
1828684: → mark_signal_executed(token=SYRUP, direction=SHORT, signal_id=1608289) — atomic claim
1828694: → ENTERED: SYRUP SHORT (trade #15196)
```

**The signal WAS in the database at execution time** but was purged by `_purge_executed_signals()` which deletes `decision='EXECUTED'` signals older than 1 hour. This is normal behavior — the signal lived its full lifecycle and was cleaned up.

**SIGNIFICANCE:** This is NOT a data integrity bug. The signal existed, was executed, and was purged per design. The ID gap is expected behavior.

---

### FINDING 2: The Signal Was Created by signals_runner, Approved via PENDING-APPROVE-BYPASS

**EVIDENCE:**
Pipeline log at 12:40:17 shows:
```
Signal accel_300_v4_short: 1  ← signals_runner detected 1 accel signal
```

Pipeline log at 12:41:03 shows:
```
1826639: ➡️  [PENDING-APPROVE-BYPASS] SYRUP:SHORT backtested standalone (accel-300-v4-short-) allowed at pending approve
```

The signal was:
1. **Created** by `signals_runner.py` as PENDING at ~12:40:13 (ID 1608289)
2. **Approved** by `signal_compactor.py` at 12:41:03 via `PENDING-APPROVE-BYPASS`
3. **Executed** by `decider_run.py` at 12:48:22 (trade #15196 opened)
4. **Purged** by `_purge_executed_signals()` after ~1 hour

**SIGNIFICANCE:** The signal followed the standard pipeline path. The `ACCEL_300_STANDALONE_BYPASS_ENABLED` flag allowed single-source execution without requiring 2+ confluence sources.

---

### FINDING 3: Confidence 99% Was Calculated, Not Raw

**EVIDENCE:**

The PostgreSQL trade record shows `confidence=99.00`. This value is calculated in `get_approved_signals()` (signal_schema.py line 2987):

```python
final_conf = min(99, base + diversity_bonus + hot_bonus)
d['final_confidence'] = round(final_conf, 1)
```

Where:
- `base` = max(effective_confidence, confidence) from DB = **78.0** (the raw signal confidence)
- `diversity_bonus` = min(20, num_types × 5) = min(20, 1 × 5) = **5** (single type: accel-300-v4-short-)
- `hot_bonus` = min(20, hot_rounds × 5)

For the final_confidence to reach 99:
- `78 + 5 + hot_bonus ≥ 99` → `hot_bonus ≥ 16` → `hot_rounds ≥ 4`

This means there were **other APPROVED signals for SYRUP SHORT** with `survival_rounds ≥ 4` at execution time. The `get_approved_signals` query uses `MAX(survival_rounds)` across ALL APPROVED signals for the same token+direction, not just the newly created one.

**Log confirmation:**
```
1828672: [DECIDER-LOOP] #1 SYRUP SHORT conf=99 hotset=YES src=accel-300-v4-short-
```

**SIGNIFICANCE:** The confidence mismatch (83% raw vs 99% in trade) is explained by the scoring formula. The raw signal confidence was 78%, but the approved signal scoring added diversity and hot-set bonuses, capping at 99%.

---

### FINDING 4: signal_created_at Is NULL Due to Missing CLI Flag

**EVIDENCE:**

PostgreSQL query shows:
```sql
SELECT COUNT(*) FROM trades WHERE signal_created_at IS NOT NULL;  -- 448
SELECT COUNT(*) FROM trades;  -- 4872
-- 90.8% of trades have NULL signal_created_at
```

In `decider_run.py`, the `execute_trade()` function (line 1546) accepts many signal-related parameters but **does NOT pass `--signal-created-at`** to `brain.py`:

```python
cmd = [sys.executable, BRAIN_CMD, 'trade', 'add',
       token, cmd_side, str(_trade_size), str(round(price, 6)),
       ...
       '--signal', _signal_for_trade,
       '--confidence', str(round(confidence, 1)),
       # NOTE: --signal-created-at is NOT passed here!
       ]
```

The `signal_created_at` field exists in `brain.py` (line 348, 658) but is never populated by `decider_run.py`.

**SIGNIFICANCE:** This is a **known limitation**, not a bug specific to this trade. The `signal_created_at` field is only populated for trades opened via specific legacy paths (HL copy trading, guardian inserts). The standard pipeline execution path never passes this parameter.

---

### FINDING 5: STANDALONE_BYPASS Enabled Single-Source Execution

**EVIDENCE:**

Pipeline log shows repeated bypasses:
```
1826589: ✅ [CONFLUENCE-GATE-PASS] SYRUP SHORT: {accel-300-v4-short-} (backtested standalone signal (accel-300-v4-short-))
1826616: ➡️  [HOTSET-FINAL-BYPASS] SYRUP:SHORT backtested standalone (accel-300-v4-short-) allowed at final guard
1826639: ➡️  [PENDING-APPROVE-BYPASS] SYRUP:SHORT backtested standalone (accel-300-v4-short-) allowed at pending approve
1826646: 🛡️  [SAFETY-FILTER-BYPASS] SYRUP:SHORT backtested standalone (accel-300-v4-short-) allowed at safety filter
```

The `STANDALONE_BYPASS_SIGNALS` list in `hermes_constants.py` includes `accel-300-v4-short-`, allowing it to execute with a single signal source instead of requiring 2+ confluence sources.

**SIGNIFICANCE:** The signal was allowed through all gates via the standalone bypass mechanism. This is by design for backtested signals with proven track records.

---

### FINDING 6: The Trade Was Stale But Still Executed

**EVIDENCE:**

Pipeline log at 12:48:22:
```
1828673: ⏰ [STALE-WARN] SYRUP SHORT: signal 8.1min old (max 5min) — conditions will be verified
```

The signal was created at ~12:40:13 and executed at 12:48:22 — **8.1 minutes old**. The staleness warning was logged but the trade was still executed because:

1. The `SIGNAL_STALENESS_MAX_AGE_MIN` hard block was **removed** on 2026-09-04 (see decider_run.py line 2940-2946)
2. Condition-based checks (ACCEL-V2-STALE, VOLATILITY GATE, price drift) verify validity at execution time
3. The signal passed all condition checks despite being stale

**SIGNIFICANCE:** The stale signal was allowed to execute because the system trusts condition-based validation over time-based expiry. This is a deliberate design decision documented in the codebase.

---

### FINDING 7: No Race Condition Detected

**EVIDENCE:**

The execution flow was sequential:
1. 12:40:13 — Signal created (ID 1608289)
2. 12:41:03 — Signal approved via PENDING-APPROVE-BYPASS
3. 12:41:03-12:48:02 — Signal survived in hotset through multiple compaction cycles
4. 12:48:02 — Signal entered hotset top-10 (SYRUP(r12 sc=159))
5. 12:48:22 — decider_run executed the trade

The `BUG-26 fix` (atomic claim via `mark_signal_executed`) prevented double-execution. The log confirms:
```
1828684: → mark_signal_executed(token=SYRUP, direction=SHORT, signal_id=1608289) — atomic claim
1828687: ✔ PostgreSQL duplicate check passed: no open trade for SYRUP SHORT
1828694: → ENTERED: SYRUP SHORT (trade #15196)
```

**SIGNIFICANCE:** No race condition. The signal was properly claimed before the trade was opened.

---

### FINDING 8: No Compactor Merger Created Confidence 99

**EVIDENCE:**

The signal_compactor does NOT merge multiple signals into one with inflated confidence. The `final_confidence: 99` is calculated in `get_approved_signals()` using the formula:
```python
final_conf = min(99, base + diversity_bonus + hot_bonus)
```

The compactor's role is:
1. Score signals using `_score_signal()` (line 917)
2. Write hotset.json with `final_confidence: conf` (the score)
3. NOT to inflate confidence

The score for SYRUP was `123.54` at 12:41:03 (from `_score_signal()`), but this is different from the `final_confidence: 99` in the trade record. The trade's confidence comes from `get_approved_signals()`, not from the hotset score.

**SIGNIFICANCE:** The confidence 99 is a calculated value, not evidence of signal merging or manipulation.

---

## Conclusion

| Mystery | Explanation |
|---------|-------------|
| Signal not found in DB | **Purged** by `_purge_executed_signals()` after execution (normal lifecycle) |
| Confidence 99 vs 78/83 | **Calculated** by `get_approved_signals()`: base 78% + diversity 5% + hot bonus ≥16% = 99% |
| signal_created_at NULL | **Known limitation**: `decider_run.py` never passes `--signal-created-at` to `brain.py` |
| Different signal source | **Same source** (accel-300-v4-short-): raw confidence was 78%, calculated final was 99% |
| Race condition | **None detected**: atomic claim via `BUG-26 fix` prevented double-execution |

## Recommendations

1. **LOW PRIORITY:** Pass `--signal-created-at` from `decider_run.py` to `brain.py` to populate this field for all trades. This would improve audit trail completeness.

2. **MEDIUM PRIORITY:** Consider adding a `signal_id` column to the PostgreSQL trades table to permanently link trades to their source signals, even after SQLite purging.

3. **NO ACTION NEEDED:** The current behavior is correct — signals are created, executed, and purged per design. The investigation confirms data integrity is intact.

---

*Investigation completed: 2026-09-11*
*Files examined: pipeline.log, signal_schema.py, decider_run.py, signal_compactor.py, brain.py, signals SQLite DB, PostgreSQL brain DB*
