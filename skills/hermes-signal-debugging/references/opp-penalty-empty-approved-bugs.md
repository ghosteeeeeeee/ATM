# OPP Penalty Debug Findings — 2026-05-21

## The Bug: OPP Penalty Invisible Despite OPP Signals Existing

### Symptom
- OPP signals ARE present in the DB (e.g., ICP SHORT conf=69.7%, rs-r267 source)
- OPP penalty should fire — ICP SHORT penalizes ICP LONG by 30% (floor 65%)
- BUT: `⚠️ [OPP-PENALTY]` log entries are **ZERO** in today's pipeline.log
- Result: signals that should be penalized score full confidence → flood top-10 → push legitimate signals out

### Root Cause: OPP Query Sees EXPIRED Signals

**Location:** signal_compactor.py line ~356 `_get_opposing_penalty()`

**Query:**
```python
opp_signals = cur.execute("""
    SELECT token, direction, confidence, source, created_at
    FROM signals
    WHERE decision IN ('PENDING','APPROVED')
    AND created_at > datetime('now', '-5 minutes')
    AND confidence >= 60
""", ...).fetchall()
```

**The problem:** OPP signals (e.g., ICP SHORT id=1015202 at 02:43:09) are marked EXPIRED by the next compaction cycle. When `_get_opposing_penalty()` runs, it queries `decision IN ('PENDING','APPROVED')` — the OPP signal is already `EXPIRED` → invisible → returns penalty=1.0 (no penalty).

**Timing:** Compaction runs at :36. OPP signal created at 02:43:09. By next compaction at 02:44:36, OPP signal has been expired via `UPDATE signals SET decision='EXPIRED' WHERE decision='APPROVED' AND created_at < datetime('now', '-5 minutes')`.

### Diagnostic

```bash
# 1. Check OPP signals in DB (ignore decision state)
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT id, token, direction, decision, confidence, source, created_at FROM signals \
   WHERE source LIKE '%zscore-pump-%' ORDER BY created_at DESC LIMIT 20;"

# 2. Check OPP query result — PENDING/APPROVED only (may show 0 despite OPP signal existing)
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT id, token, direction, decision, confidence, source, created_at FROM signals \
   WHERE decision IN ('PENDING','APPROVED') \
   AND created_at > datetime('now', '-5 minutes') \
   AND confidence >= 60;"

# 3. Compare: if OPP signals exist but OPP query returns 0 → timing issue (signal expired before query)
# OPP signal created at T, compaction expires it at T+~90s, OPP query at T+90s+ finds nothing

# 4. Check OPP-PENALTY log entries (should be many if OPP signals firing correctly)
grep -c "OPP-PENALTY" /var/www/hermes/logs/pipeline.log
# 0 = broken (signal expired before OPP query ran)
# N > 0 = working (count should roughly match OPP signal frequency)
```

### The OPP Penalty Formula

```python
opp_source_count = len([s for s in all_opp_signals if s['source'] != src])
penalty_mult = max(0.65, 1.0 - (opp_source_count * 0.30))
# 1 OPP source → 0.70 (30% penalty)
# 2 OPP sources → 0.40 (60% penalty) — but floored at 0.65
# 3 OPP sources → floor 0.65
```

**Critical note:** OPP penalty reduces score but does NOT block signals at the confluence gate. A signal with OPP penalty can still enter top-10 and be approved. Only the confluence gate (2+ sources) blocks at line 1081.

### OPP Signals vs. Counter-Regime Signals

These are DIFFERENT:
- **OPP signals** — same token, opposite direction, within 5-min window → score penalty
- **Counter-regime** — token direction opposes market regime → direction filter in decider_run

---

## Zero APPROVED Signals Ever in DB

### Symptom
```sql
SELECT COUNT(*) FROM signals WHERE decision='APPROVED';
→ 0 (ZERO across entire database history)
```

Yet 88 signals are EXECUTED today.

### Root Cause: PENDING → EXECUTED Direct Path

The signal lifecycle is NOT what the docs describe:

**Expected:** PENDING → APPROVED → EXECUTED
**Actual:** PENDING → EXECUTED (direct, bypassing APPROVED)

OR:

**Actual:** PENDING → EXPIRED (compaction expiry, confluence gate, staleness)

### Why This Matters

`decider_run` watches for `decision='APPROVED' AND executed=0` at line ~1520. Since NO signals ever have this state, the execution gate appears to not fire — but it does fire for PENDING→EXECUTED via `_run_hot_set()` at lines 1012-1019.

### Verification Query

```sql
-- Check actual decision state distribution for recent signals
SELECT decision, COUNT(*) as cnt
FROM signals
WHERE created_at > datetime('now', '-1 hour')
GROUP BY decision
ORDER BY cnt DESC;

-- Check EXECUTED signals — did they pass through APPROVED?
SELECT id, token, direction, decision, executed, created_at, updated_at
FROM signals
WHERE decision='EXECUTED'
ORDER BY created_at DESC
LIMIT 10;
-- If updated_at - created_at < 2 minutes → direct PENDING→EXECUTED path (no APPROVED state)
```

### Related: Preservation Bug

**Location:** signal_compactor.py lines ~1000-1012

When preserving previous hot-set entries to `hotset.json`, the code writes to `hotset_final` (which becomes hotset.json) WITHOUT updating the DB. The signal stays PENDING or EXPIRED in the DB.

`decider_run`'s `_run_hot_set()` at lines 1012-1019 writes APPROVED for tokens in hot-set, but only for PENDING signals. Preserved entries that are already EXPIRED don't get revived to APPROVED.

**Fix direction:** Either signal_compactor must write APPROVED for preserved entries, OR decider_run's `_run_hot_set()` must handle EXPIRED→APPROVED revival for hot-set tokens.

---

## Empty approved_ids SQL Bug

**Location:** signal_compactor.py lines ~1179-1197

```python
if approved_ids:
    cur.execute("""
        UPDATE signals SET decision='EXPIRED', expired_at=CURRENT_TIMESTAMP
        WHERE decision='APPROVED' AND id NOT IN ({})
        AND executed=0 AND created_at < datetime('now', '-5 minutes')
    """, ...)
```

**Problem:** When `approved_ids=[]` (top-10 didn't include any previously-APPROVED signals), the `NOT IN ()` subquery is syntactically valid in SQLite but semantically **always TRUE** — `NOT IN (empty)` returns TRUE for all rows, so ALL APPROVED signals get expired regardless of whether they were in the current top-10.

**Mitigation:** OPP signals were already EXPIRED before this query ran (timing issue above), so the impact is minimal. But if OPP timing is fixed, this bug would prematurely expire OPP signals that should survive another cycle.