# Independent Audit Verdict: Zombie Signal Loop Analysis

**Auditor:** DeepSeek Harness (independent, fresh-eyes)
**Date:** 2026-09-04
**Files examined:** signal_compactor.py, decider_run.py, signal_schema.py, hermes_constants.py, pipeline.log
**DB queries:** SQLite signals_hermes_runtime.db (direct queries)

---

## Signal Lifecycle Summary

```
signal_gen.py → DB (PENDING) → signal_compactor.py → DB (APPROVED) → hotset.json → decider_run.py → execute
                                                     ↓
                                          _filter_safe_prev_hotset (staleness decay)
                                                     ↓
                                          PRESERVE-APPROVED-UPSERT (DB upsert)
                                                     ↓
                                          cleanup_stale_approved (1h expiry)
```

---

## Claim 1: SECOND zombie loop caused by PRESERVE-APPROVED-UPSERT refreshing created_at

**Verdict: AGREE (with nuance)**
**Confidence: HIGH**

### Evidence

The PRESERVE-APPROVED-UPSERT mechanism (signal_compactor.py lines 2267-2285) INSERTs a **new** APPROVED row with `created_at = CURRENT_TIMESTAMP` when a preserved entry wins the merge and no existing APPROVED row is found:

```python
# Line 2267-2274
_cur.execute("""
    INSERT INTO signals (
        token, direction, signal_type, source, confidence,
        decision, executed, z_score, survival_rounds,
        hot_cycle_count, combo_key, price, signal_metadata,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, 'APPROVED', 0, ?, ?, 1, ?, ?, ?,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
""")
```

The zombie loop mechanism:

1. **T=0:** Signal enters hotset → entry_origin_ts = T=0, staleness = 1.0
2. **T=1-5min:** Preserved via `_filter_safe_prev_hotset`, staleness decays at rate 0.2 (non-favorites)
3. **T=5min:** staleness = max(0, 1 - 5*0.2) = 0 → entry dropped from preserve path (line 2892-2893)
4. **T=5-10min:** Compactor DB query (line 1162: `created_at > datetime('now', '-10 minutes')`) picks up the fresh APPROVED row → re-adds to hotset with **new** entry_origin_ts = time.time() (line 1813) → **staleness RESET to 1.0**
5. Meanwhile, `cleanup_stale_approved(hours=1)` (decider_run.py line 2486) marks old APPROVED rows as EXPIRED
6. Next compaction: PRESERVE-APPROVED-UPSERT finds no APPROVED row (expired) → INSERTs new one → cycle repeats

**Key:** The entry never dies because:
- PRESERVE-APPROVED-UPSERT keeps creating fresh APPROVED rows
- Compactor DB query (10-min window) picks them up and re-adds to hotset
- entry_origin_ts resets on each re-entry via the DB path (line 1813: `entry_origin_ts = time.time()`)

**Nuance:** The claim says "refreshing created_at" — technically it's creating a NEW row, not updating created_at on an existing row. The UPDATE path (line 2256-2265) does NOT touch created_at. But the effect is the same: a fresh `created_at` appears in the DB every cycle.

---

## Claim 2: Compactor SQL query picks up fresh APPROVED rows, re-entering them into hotset

**Verdict: AGREE**
**Confidence: HIGH**

### Evidence

The compactor's main query (signal_compactor.py lines 1139-1170):

```sql
SELECT token, direction, MAX(signal_type), MAX(confidence), ...
FROM signals
WHERE decision IN ('PENDING', 'APPROVED')
  AND executed = 0
  AND created_at > datetime('now', '-10 minutes')  -- LINE 1162
  AND confidence >= 60
  AND token NOT LIKE '@%'
  AND combo_key IS NOT NULL
GROUP BY combo_key
```

The `created_at > datetime('now', '-10 minutes')` clause picks up any APPROVED signal with a fresh timestamp. PRESERVE-APPROVED-UPSERT creates rows with `CURRENT_TIMESTAMP`, which is always within the 10-minute window.

**Confirmed via log:** The ICP:LONG ema300-dip signal appears in compactor HOTSET-FINAL-ADD entries every 1-2 minutes throughout Sep 3 (54,242 log lines matching "ema300-dip" on Sep 3 alone).

---

## Claim 3: When preserved entry drops (staleness=0) and DB path re-adds it, entry_origin_ts resets to time.time()

**Verdict: AGREE**
**Confidence: HIGH**

### Evidence

signal_compactor.py lines 1806-1813:

```python
if prev_entry:
    prev_origin_ts = prev_entry.get('entry_origin_ts')
    if isinstance(prev_origin_ts, (int, float)) and prev_origin_ts > 0:
        entry_origin_ts = prev_origin_ts  # preserved from previous cycle
    else:
        entry_origin_ts = time.time()     # reset
else:
    entry_origin_ts = time.time()         # NEW entry → reset
```

When the entry drops from hotset (staleness=0 → filtered by `_filter_safe_prev_hotset` at line 2892-2893), the next compactor cycle sees `prev_entry = None` and sets `entry_origin_ts = time.time()`. This resets the staleness timer, creating an effectively immortal signal.

---

## Claim 4: created_at is NOT returned by get_approved_signals(), disabling staleness check at decider_run line 2728

**Verdict: AGREE**
**Confidence: HIGH**

### Evidence

signal_schema.py `get_approved_signals()` SQL (lines 2627-2665):

```sql
SELECT id, token, direction,
       COUNT(*) as count,
       MAX(COALESCE(effective_confidence, confidence)) as max_conf,
       MIN(COALESCE(effective_confidence, confidence)) as min_conf,
       GROUP_CONCAT(DISTINCT signal_type) as types,
       MAX(source) as source,
       MAX(price) as price,
       MAX(leverage) as leverage,
       MAX(COALESCE(...)) as hot_rounds,
       MAX(COALESCE(...)) as learned_sl_multiplier,
       (...) as signal_metadata
FROM signals
WHERE decision='APPROVED' AND executed=0
  AND created_at > datetime('now','-'||?||' hours')
```

**`created_at` is NOT in the SELECT clause.** The result dict `d = dict(r)` (line 2669) does not contain `created_at`.

decider_run.py line 2728:
```python
signal_created_at = sig.get('created_at')  # Returns None
if signal_created_at:                        # False — block skipped
    ...staleness check...
```

**The staleness check is DEAD CODE** for signals going through `get_approved_signals()`.

---

## Claim 5: accel-300 staleness check at line 3045 is also disabled

**Verdict: PARTIAL (technically correct but moot for ICP:LONG)**
**Confidence: MEDIUM**

### Evidence

decider_run.py lines 3040-3054:

```python
_is_accel_v2 = 'accel-300-v2' in (source or '')
_is_accel_v2_long = 'accel-300-v2-long' in (source or '')
_is_accel_v2_long_5m = 'accel-300-v2-long-5m' in (source or '')
_is_accel_v3_short = 'accel-300-v3-short' in (source or '')
if _is_accel_v2 or _is_accel_v2_long or _is_accel_v2_long_5m or _is_accel_v3_short:
    _entry_origin = sig.get('entry_origin_ts') or 0       # None → 0
    if not _entry_origin and sig.get('created_at'):        # created_at also None
        ...
    _hotset_age_min = (time.time() - _entry_origin) / 60.0 if _entry_origin else 0
    # _hotset_age_min = 0 → check never triggers
```

**Analysis:**
- `entry_origin_ts` is NOT in the signal dict from `get_approved_signals()` → returns None → defaults to 0
- `created_at` is also NOT in the signal dict → fallback fails
- `_entry_origin` stays 0, `_hotset_age_min` = 0, check never triggers

**However:** This check only applies to accel-300 signals (source contains 'accel-300-v2' or 'accel-300-v3-short'). ICP:LONG with source='ema300-dip' does NOT match any of these conditions. So this check is irrelevant for the ICP:LONG zombie. It IS relevant for other accel-300 zombie signals.

---

## Claim 6: 208 ema300-dip executions happened on Sep 3, with tokens like HYPE executed 15 times

**Verdict: PARTIAL (correct direction, wrong numbers)**
**Confidence: HIGH**

### Evidence

My count from pipeline.log:
- **212** ema300-dip EXEC lines on Sep 3 (not 208 — close but off by 4)
- **54,242** total ema300-dip log lines on Sep 3 (hotset entries, preserves, writes, etc.)

Token breakdown (ema300-dip executions on Sep 3):
| Token | Executions |
|-------|-----------|
| ATOM LONG | 23 |
| HYPE LONG | 18 (not 15) |
| LTC LONG | 14 |
| USUAL LONG | 12 |
| LDO LONG | 12 |
| PONS LONG | 10 |
| CRV LONG | 10 |
| ICP LONG | 2 |
| ... | ... |
| **Total** | **212** |

**Note:** These are EXEC log lines, not necessarily unique executed trades (some may be duplicate log entries). The actual unique executed trades may be fewer.

---

## Claim 7: ICP:LONG survived 18 hours in the system

**Verdict: AGREE**
**Confidence: HIGH**

### Evidence

From pipeline.log:
- **First appearance:** 2026-09-03 03:15:01 (HOTSET-FINAL-ADD for ICP:LONG ema300-dip)
- **Execution:** 2026-09-03 21:37:15 (EXEC: ICP LONG @ $2.544250)
- **Duration:** 18 hours 22 minutes

The signal cycled through the hotset for 18+ hours before executing. During this time:
- 11 PRESERVE-APPROVED-UPSERT rows were created in the DB (all now EXPIRED)
- The signal was preserved in hotset via the `_filter_safe_prev_hotset` mechanism
- entry_origin_ts was carried forward, but staleness decayed and was reset multiple times via the compactor DB query path

---

## Additional Findings

### A. Signal 1593791 does not exist in the DB

The execution log at 21:37:15 references `signal_id=1593791`, but this ID does not exist in the `signals` table or `signal_history`. This is because `_purge_executed_signals(hours=1)` (signal_compactor.py line 2750-2848) deletes EXECUTED signals after 1 hour. The signal was created, executed, and purged — all within the normal lifecycle.

### B. PRESERVE-APPROVED-UPSERT is MASSIVELY active

The log contains **1,893** PRESERVE-APPROVED-UPSERT entries across the entire log span. This mechanism fires on nearly every compaction cycle for every preserved entry that lacks an existing APPROVED row. This is the primary driver of the zombie loop.

### C. The 10-minute compactor window is too wide

The compactor SQL `created_at > datetime('now', '-10 minutes')` allows signals up to 10 minutes old. Since PRESERVE-APPROVED-UPSERT creates fresh APPROVED rows every cycle, there's always a row within this window. A tighter window (e.g., 2-3 minutes) would break the cycle.

### D. entry_origin_ts reset is the root cause

The fundamental flaw is at signal_compactor.py line 1813: when an entry drops from hotset and is re-added via the DB path, `entry_origin_ts = time.time()` resets the staleness timer. This means a signal can live forever as long as:
1. PRESERVE-APPROVED-UPSERT keeps creating APPROVED rows
2. Compactor DB query keeps re-adding the entry to hotset

### E. Cleanup mechanisms are insufficient

- `cleanup_stale_approved(hours=1)` marks APPROVED signals as EXPIRED after 1 hour
- But PRESERVE-APPROVED-UPSERT immediately creates a new APPROVED row
- The compactor DB query picks up the new row and re-adds to hotset
- The cycle is unbroken

---

## Summary Table

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | Second zombie loop from PRESERVE-APPROVED-UPSERT | **AGREE** | HIGH |
| 2 | Compactor SQL picks up fresh APPROVED rows | **AGREE** | HIGH |
| 3 | entry_origin_ts resets on re-entry | **AGREE** | HIGH |
| 4 | created_at NOT returned by get_approved_signals | **AGREE** | HIGH |
| 5 | accel-300 staleness check disabled | **PARTIAL** | MEDIUM |
| 6 | 208 ema300-dip executions, HYPE 15x | **PARTIAL** | HIGH |
| 7 | ICP:LONG survived 18 hours | **AGREE** | HIGH |

---

## Root Cause Chain

```
PRESERVE-APPROVED-UPSERT creates APPROVED row (CURRENT_TIMESTAMP)
    → Compactor DB query picks it up (10-min window)
        → Re-adds to hotset with entry_origin_ts = time.time() (RESET)
            → Staleness starts at 1.0 again
                → After 5 min, staleness = 0, drops from preserve
                    → But PRESERVE-APPROVED-UPSERT has already created new APPROVED row
                        → Compactor DB query picks it up again
                            → INFINITE ZOMBIE LOOP
```

**The two independent kill mechanisms that should break this loop but don't:**
1. `cleanup_stale_approved(hours=1)` — expires the APPROVED row, but PRESERVE-APPROVED-UPSERT recreates it
2. Staleness decay to 0 — drops entry from preserve, but compactor DB query re-adds it with reset entry_origin_ts

**To break the loop, you need to fix BOTH:**
1. PRESERVE-APPROVED-UPSERT should NOT create new APPROVED rows when the entry's staleness is low (e.g., < 0.3)
2. OR: The compactor DB query should NOT pick up signals that were created by PRESERVE-APPROVED-UPSERT (e.g., check for a `preserved` flag)
3. OR: entry_origin_ts should NOT reset when re-entering via the DB path (carry it in the DB row)
