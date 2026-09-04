# Stale Signal Zombie Loop Investigation — 2026-09-04

## Executive Summary

**Root Cause: SECOND zombie loop** — different from the original `created_at=CURRENT_TIMESTAMP` merge UPDATE bug (fixed in `e0af8d75`). This new loop is caused by the interaction between:
1. `PRESERVE-APPROVED-UPSERT` creating APPROVED rows with `created_at=CURRENT_TIMESTAMP`
2. The compactor's SQL query picking up these fresh APPROVED rows
3. The `entry_origin_ts` resetting to `time.time()` when the preserved entry drops and re-enters from DB

**Effect:** Signals survive indefinitely through a cycle of: DB → hotset → preserve → UPSERT → DB → hotset → preserve → ...

## The Zombie Cycle

```
T+0min:   Signal created (PENDING, created_at=NOW)
T+1min:   Compactor: DB picks up → hotset_final. Preserve: prev exists → PASS
          PRESERVE-APPROVED-UPSERT creates APPROVED (created_at=NOW)
T+5min:   Preserve staleness=0.0 → DROPPED
          But DB query: APPROVED row created_at=T+4min (< 10min) → still picked up
          No prev_entry → entry_origin_ts = T+5min (FRESH!) → staleness=1.0
T+6min:   Preserve picks up from hotset.json (staleness=0.8 → PASS)
          PRESERVE-APPROVED-UPSERT creates new APPROVED (created_at=NOW)
T+10min:  DB query picks up APPROVED from T+9min (< 10min)
          No prev_entry → entry_origin_ts = T+10min (FRESH again!)
          ...cycle repeats indefinitely
```

## Evidence

### ICP:LONG ema300-dip — 18-hour survival
- First entered hotset: `2026-09-03 03:15:01` (conf=86.0, score=129.18)
- Executed: `2026-09-03 21:37:15` (conf=99, ema300-dip)
- **18 hours 22 minutes** in the system
- 208 ema300-dip executions on Sep 3 alone
- 228 total ema300-dip executions across Sep 3-4

### HYPE:LONG — 15 executions
### ATOM:LONG — 12 executions  
### LTC:LONG — 10 executions

## Bug #1: PRESERVE-APPROVED-UPSERT refreshes created_at

**File:** `signal_compactor.py` line 2267-2274
```python
INSERT INTO signals (..., created_at, updated_at)
VALUES (..., CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
```

When a preserved entry wins the merge, a NEW APPROVED row is created with `created_at=CURRENT_TIMESTAMP`. This makes the signal appear "fresh" to the compactor's SQL query:
```sql
WHERE created_at > datetime('now', '-10 minutes')
```

## Bug #2: entry_origin_ts resets on re-entry

**File:** `signal_compactor.py` line 1806-1813
```python
if prev_entry:
    entry_origin_ts = prev_entry.get('entry_origin_ts')
else:
    entry_origin_ts = time.time()  # ← RESETS TO NOW
```

When the preserved entry drops (staleness=0) and the DB path re-adds it, there's no `prev_entry` in the hotset, so `entry_origin_ts` resets to `time.time()`. This resets staleness to 1.0.

## Bug #3: created_at NOT returned by get_approved_signals()

**File:** `signal_schema.py` line 2626-2664

The SQL SELECT does not include `created_at`:
```sql
SELECT id, token, direction, COUNT(*), MAX(confidence), ...
-- created_at is NOT selected
```

**File:** `decider_run.py` line 2728
```python
signal_created_at = sig.get('created_at')  # Returns None!
```

The staleness check at line 2725-2743 (`SIGNAL_STALENESS_MAX_AGE_MIN = 5`) is **completely disabled** because `created_at` is not in the signal dict.

## Bug #4: Accel-300 staleness check uses missing field

**File:** `decider_run.py` line 3045-3054
```python
_entry_origin = sig.get('entry_origin_ts') or 0  # Returns 0!
if not _entry_origin and sig.get('created_at'):   # Also None!
    ...
_hotset_age_min = (time.time() - _entry_origin) / 60.0  # = 0
```

The accel-300 staleness re-check (max 10 min) is also disabled for the same reason.

## Why the Original Fix Wasn't Enough

The original zombie loop fix (`e0af8d75`) removed `created_at=CURRENT_TIMESTAMP` from the merge UPDATE in `signal_schema.py`. This stopped the merge from refreshing `created_at`.

But `PRESERVE-APPROVED-UPSERT` is a DIFFERENT code path in `signal_compactor.py` that creates NEW APPROVED rows with `created_at=CURRENT_TIMESTAMP`. This is the second zombie loop.

## Fixes Required

### Fix 1: Stop PRESERVE-APPROVED-UPSERT from refreshing created_at
```python
# signal_compactor.py line 2267-2274
# BEFORE:
INSERT INTO signals (..., created_at, updated_at)
VALUES (..., CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)

# AFTER:
INSERT INTO signals (..., created_at, updated_at)
VALUES (..., ?, CURRENT_TIMESTAMP)  # Use original creation time from entry
```

Pass the original `entry_origin_ts` as `created_at` instead of `CURRENT_TIMESTAMP`.

### Fix 2: Add created_at to get_approved_signals()
```python
# signal_schema.py line 2626
# Add created_at to the SELECT:
SELECT id, token, direction, MAX(created_at) as created_at, ...
```

### Fix 3: Add staleness check to ALL signal types in decider_run
The current staleness check at line 2725-2743 only works if `created_at` is present. After Fix 2, it will work for all signals.

### Fix 4: Add maximum hotset lifetime
Add a hard limit on how long a signal can stay in the hotset (e.g., 30 minutes max). This is defense-in-depth.

## Verification

After fixes, verify:
1. New signals survive max ~5 min (non-fav) or ~8 min (fav) in hotset
2. No signal executes more than once per detection event
3. `created_at` in APPROVED signals reflects original detection time, not UPSERT time
4. The staleness check in decider_run blocks signals older than `SIGNAL_STALENESS_MAX_AGE_MIN`
