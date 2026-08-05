# Bug: Preserve Path — JSON Written, DB Not Updated → No Execution

**Date:** 2026-05-21
**Severity:** SEV2 — pipeline running, no trades opening, financial opportunity cost
**Status:** Open / Fix pending

## Summary

Signals in `hotset.json` via the preserve path are NOT reaching live trades. The hot-set has entries, but nothing executes. Root cause: `signal_compactor` preserve path writes to `hotset.json` but does NOT upsert an `APPROVED` row in `signals_hermes_runtime.db`. `decider_run`'s execution gate calls `get_approved_signals()` which queries `WHERE decision='APPROVED'` — returns **zero rows** → early return → no trades.

## Root Cause

### Signal Flow (normal APPROVED path)
```
add_signal() → PENDING in DB
  ↓
signal_compactor: PENDING→APPROVED (confluence gate passes)
  ↓ writes
hotset.json (entry has APPROVED DB row)
  ↓
decider_run: get_approved_signals() → finds APPROVED row → executes
```

### Signal Flow (preserve path — BROKEN)
```
signal_compactor: PENDING→APPROVED blocked (confluence gate fails)
  ↓ (preserve path kicks in for entries that were previously multi-source)
hotset.json written with preserved entry
  ↓ BUT
No APPROVED row written to DB (preserve path skips DB upsert)
  ↓
decider_run: get_approved_signals() → returns [] → return 0,0 at line 1510
  ↓
No execution, even though hotset.json has entries
```

### Why the PENDING-APPROVE-BLOCK also fires

The `PENDING-APPROVE-BLOCK` fires on **individual PENDING rows one-by-one**, checking `source` of each new row. A 2-source preserved combo in `hotset.json` doesn't protect a new single-source PENDING row for the same token+direction from being blocked. The preserve path's multi-source combo and the PENDING row's single-source are checked independently.

Example for ASTER:LONG:
1. Prior cycle: ASTER:LONG with `source='rs-s126,zscore-pump+'` → APPROVED → traded → executed=1
2. New cycle: zscore-pump+ fires alone → creates PENDING row with `source='zscore-pump+'` (single source)
3. PENDING-APPROVE-BLOCK fires: `🔒 [PENDING-APPROVE-BLOCK] ASTER LONG single-source blocked from APPROVE`
4. Preserve path writes `ASTER:LONG src='rs-s126,zscore-pump+'` to hotset.json (from prior cycle's data)
5. BUT: no new APPROVED row exists in DB for this cycle
6. decider_run → `get_approved_signals()` → 0 rows → nothing executes

## Two Categories of hotset.json Entries

| Category | Source | Has APPROVED DB row | decider_run executes? |
|----------|--------|---------------------|------------------------|
| 1 — DB path | entries_from_db (passed confluence) | YES | YES |
| 2 — Preserve path | preserve_prev_hotset | **NO** | **NO** |

Category 2 entries look valid in `hotset.json` (correct source, z_score, etc.) but have no DB presence → invisible to decider_run's execution query.

## Diagnostic Query

```python
# Check what's actually in hotset.json vs what's in APPROVED DB
import sqlite3, json
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()

with open('/var/www/hermes/data/hotset.json') as f:
    hs = json.load(f)

hot_tokens = {f"{e['token']}:{e['direction']}" for e in hs.get('hotset', [])}

c.execute("""
    SELECT token, direction, decision, source, executed
    FROM signals
    WHERE decision='APPROVED' AND executed=0
    ORDER BY created_at DESC
""")
approved_rows = c.fetchall()

print(f"hotset.json entries: {len(hs.get('hotset', []))}")
print(f"APPROVED+unexecuted DB rows: {len(approved_rows)}")
print(f"Overlap: {sum(1 for r in approved_rows if f\"{r[0]}:{r[1]}\" in hot_tokens)}")

# Check for Category 2 entries (in hotset but not APPROVED)
for e in hs.get('hotset', []):
    key = f"{e['token']}:{e['direction']}"
    c.execute("""
        SELECT decision, source FROM signals
        WHERE token=? AND direction=? AND executed=0
        ORDER BY created_at DESC LIMIT 1
    """, (e['token'], e['direction']))
    db_row = c.fetchone()
    in_db = key in {f"{r[0]}:{r[1]}" for r in approved_rows}
    print(f"  {key}: hotset=YES db_approved={'YES' if in_db else 'NO (preserve path)'} db_row={db_row}")
conn.close()
```

Expected: all hotset.json entries should have `db_approved=YES`. If any show `NO (preserve path)`, that entry is stranded.

## The Fix

When `signal_compactor` preserves a `prev_hotset` entry to `hotset.json` (Step 12 / `_filter_safe_prev_hotset` or merge step), it must ALSO upsert an APPROVED row in the DB for that token+direction.

**Location:** `signal_compactor.py` around the preserve/merge step (~lines 938-964 and/or `_filter_safe_prev_hotset`)

**Fix pattern:**
```python
# After writing entry to hotset.json (preserve path), also upsert DB:
upsert_approved = """
    UPDATE signals
    SET decision='APPROVED', updated_at=CURRENT_TIMESTAMP
    WHERE token=? AND direction=? AND decision='PENDING';
    INSERT OR IGNORE INTO signals (token, direction, decision, source, created_at, updated_at)
    VALUES (?, ?, 'APPROVED', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
"""
cursor.execute(upsert_approved, (token, direction, token, direction, source))
```

**Alternative (cleaner):** Add a `hot_cycle_count` increment to the existing APPROVED row via UPDATE if one exists, or INSERT if not. The key is: if an entry is being preserved to `hotset.json`, it MUST have a corresponding APPROVED row in the DB or decider_run will never see it.

## Why This Wasn't Caught Earlier

1. The preserve path was added in 2026-04-16 (`_run_hot_set is READ-ONLY` note in decider_run)
2. Before the confluence gate (2026-05-12), most signals naturally had 2+ sources and passed PENDING→APPROVED normally → Category 1 path was sufficient
3. After confluence gate (2026-05-12), many signals are blocked at PENDING→APPROVED → preserve path is needed more often
4. But the preserve path was implemented without the DB upsert, making it useless for execution
5. The PENDING-APPROVE-BLOCK compound with the missing DB upsert creates a double-block: PENDING can't become APPROVED, and preserve can't execute without it

## Related Bugs in Skill

- PENDING-APPROVE-BLOCK (signal_compactor.py:1047) — blocks single-source PENDING rows from APPROVED
- Merge step bypass of confluence (2026-05-12, fixed)
- `_filter_safe_prev_hotset` missing open-position check (2026-05-12, fixed)