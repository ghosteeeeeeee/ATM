# Single-Source APPROVED Bypass — Root Cause

## Symptom
Confluence gate is WORKING (logs show single-source blocked at CONFLUENCE-GATE-BLOCK), but single-source signals still reach `decision=APPROVED` in DB and open as trades.

## Root Cause: Merge Step Re-Approves Prev_Hotset
signal_compactor.py has two paths:
1. **Fresh DB path** — confluence gate at lines 545-555 correctly blocks single-source
2. **Merge/preserve step** (lines 938-964) — `_filter_safe_prev_hotset()` re-approves entries from previous hot-set WITHOUT re-running confluence check

### The Leak at Line 1335
```python
# _filter_safe_prev_hotset():
if src == 'breakout':
    pass  # ← PROBLEM: breakout bypass lets single-source through
elif len(source_parts) < 2:
    continue  # ← blocks single-source (except breakout)
```
BUT: entries created BEFORE the confluence patch (07:46 today) already had `decision=APPROVED` in DB. They get preserved and re-approved in merge step.

## Key Evidence
- Confluence gate working: 13:38-13:44 logs show NEAR LONG blocked (`only 1 unique types {accel-300+}`)
- But NEAR opened at 12:43 — before confluence patch was deployed or before its effect
- Current hot-set (fresh, 0.4 min old): ALL entries have 2+ unique types ✓
- DB APPROVED (13:35-13:37): ENS LONG (1-part), NIL SHORT (1-part) ← LEAK STILL ACTIVE
- These leaked because `_filter_safe_prev_hotset` preserved them from prev_hotset

## The Fix
1. Remove `breakout` bypass at line 1333-1334 in signal_compactor.py
2. Force-clear single-source APPROVED entries from DB after patch deployment:
   ```sql
   UPDATE signals SET decision='PENDING' 
   WHERE decision='APPROVED' AND source NOT LIKE '%,%';
   ```
3. Or: add confluence re-check in merge step at line 958

## Prev_Hotset Is Loaded From
`hotset.json` (written at end of each compaction cycle, read as `prev_hotset` at start of next).

## Diagnostic Query
```python
# Check which APPROVED entries are single-source
import sqlite3, re
DB = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT token, direction, source, created_at FROM signals "
    "WHERE decision='APPROVED' ORDER BY created_at DESC"
).fetchall()
for r in rows:
    parts = r[2].split(',')
    types = set()
    for p in parts:
        m = re.match(r'^([a-z][a-z0-9_-]*)([+-]?)(\d+)$', p)
        types.add(m.group(1)+m.group(2) if m else p)
    if len(types) == 1:
        print(f"SINGLE-SOURCE: {r[0]} {r[1]} src={r[2]}")
conn.close()
```

## Regime Filtering Is Disabled
decider_run.py:1698-1708 — counter-trend trap guard **commented out 2026-05-11** because 100-bar 1m LR was too noisy. To re-enable, uncomment but use confidence threshold > 30.
