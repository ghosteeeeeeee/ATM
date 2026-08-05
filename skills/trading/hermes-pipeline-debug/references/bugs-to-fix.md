# bugs-to-fix.md

**Location:** `/root/.hermes/brain/bugs-to-fix.md`

Canonical tracking file for confirmed bugs that need fixing but aren't urgent enough to fix right now.

## Active Items

### BUG-2026-05-17-001 — Price data freshness: timestamp ordering bug (HIGH)
**Reported:** 2026-05-16, root cause confirmed 2026-05-17
**File:** `price_collector.py` line ~549 (fix applied)
**Problem:** `prices.json["updated"]` was written at collection START, before the ~90s candle aggregation phase. smoke_test reads age as `time.time() - updated`, so during aggregation the file always showed 90-180s age even though prices were fresh from HL allMids.

**Actual data flow (BEFORE fix):**
1. `fetch_all_prices()` → HL allMids call (~0.1s)
2. `save_prices()` → writes `prices.json` with `updated = time.time()` ← TOO EARLY
3. `_aggregate_tf()` x4 → scans 25.5M rows over ~90s
4. `_seed_universe_candles()` → Binance candles

**Fix applied:** Second `save_prices()` call added AFTER aggregation completes (line ~549), BEFORE `_seed_universe_candles()`. `prices.json["updated"]` now reflects end-of-collection time.

**Key insight:** signal_gen reads from `latest_prices` SQLite table (fresh, updated every ~3.4min), NOT `prices.json`. The staleness only affected smoke_test monitoring — actual trading data was never stale.

**Verification:**
```bash
python3 -c "import json,time; d=json.load(open('/root/.hermes/data/prices.json')); print(f'Age: {time.time()-d[\"updated\"]:.0f}s')"
# Should show <60s after price_collector completes
```
**Status:** Fix deployed 2026-05-17 — verify at next price_collector run (~3-4min cycle)

---

### BUG-2026-05-16-002 — smoke_test no_flapping threshold too low (LOW)
**Reported:** 2026-05-16
**File:** `smoke_test.py` → `check_no_flapping()`
**Problem:** Threshold `> 55` always triggers on a healthy pipeline (1 cycle/min = 60 cycles). Not actual flapping — threshold is wrong.
**Fix:** Change `> 55` to `> 65`. Also distinguish between "many normal cycles" and "actual restarts/crashes."
**Status:** Pending

---

### BUG-2026-05-16-003 — smoke_test pipeline_not_stuck: auto-clear orphaned locks (LOW)
**Reported:** 2026-05-16
**File:** `smoke_test.py` → `check_pipeline_not_stuck()`
**Problem:** When `/tmp/hermes-pipeline.lock` exists with no holder process (orphaned lock), smoke_test reports FAIL. But the pipeline is running fine — the lock is just leftover cruft.
**Fix:** In `check_pipeline_not_stuck()`, if lock exists but `holders` is empty AND age > 600s, auto-delete the lock instead of reporting FAIL:
```python
if not holders and age > 600:
    lock.unlink()
    return True, "orphaned lock cleared"
```
**Status:** Pending — requires smoke_test.py modification

---

### BUG-2026-05-17-004 — Lock fd not closed → stale lock recurrence (MEDIUM)
**Reported:** 2026-05-17
**File:** `run_pipeline.py` line 176 (fix applied)
**Problem:** `os.close(lock_fd)` was added to release fcntl advisory lock immediately after acquisition. However, lock is going stale again post-fix — possible manual invocation bypassing the fix, or a second code path acquiring the lock without closing.
**Symptom:** Lock mtime=16:33, no holder process, fix code confirmed at line 176.
**Fix applied:** `os.close(lock_fd)` right after successful `fcntl.flock()` + comment about fork behavior.
**Still investigating:** Lock keeps reappearing as stale despite fix. Check for manual `python3 run_pipeline.py` invocations or second lock acquisition path.
**Status:** Fix deployed, monitoring for recurrence