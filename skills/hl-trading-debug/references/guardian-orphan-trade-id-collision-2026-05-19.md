# Guardian Orphan INSERT Trade ID Collision Bug (2026-05-19)

## Bug: Ghost Trades Opening on HL with No Local DB Counterpart

**Root cause:** `hl-sync-guardian.py` orphan INSERT (line 3759) uses `int(lev * 1000000)` as `trade_id`. Every coin with same leverage hits the same ID across different days → duplicate key constraint violation → INSERT silently fails → no DB record → no closing marker cleared → guardian re-detects orphan next cycle → closes again → repeats.

**Collision table:**
| Leverage | trade_id | Coins that hit it |
|----------|----------|-------------------|
| 5x | 5000000 | ONDO, ADA, ZEN, MANY others |
| 3x | 3000000 | CHIP |
| 1x | 1000000 | (future) |

**Affected tokens:** ONDO, STRK, 0G, ADA, MON — all guardian-closed orphans with no DB record.

**Fix:** Change orphan INSERT to use `NULL` for trade_id (orphan trades never went to HL, no reconciliation needed), or query `MAX(id)+1` from DB. Do NOT use `int(lev * 1000000)` — it's a collision hazard.

## Diagnostic Query

```python
import psycopg2
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT id, token, trade_id, status, guardian_reason, open_time 
    FROM trades 
    WHERE guardian_reason='guardian_orphan' 
    ORDER BY open_time DESC
""")
for r in cur.fetchall():
    print(r)
# Find stale entries with trade_id in HL orphan range (1000000-9000000)
```

## The Four Ghost Trade Paths

1. **brain.py INSERT fails** → HL has position, DB doesn't → orphan detected → guardian closes
2. **guardian orphan INSERT fails** → no DB record created → closing marker not cleared → orphan re-detected next cycle → re-closes
3. **decider_run opens via brain.py** → `mirror_open` succeeds → DB INSERT fails (e.g. NOW() placeholder mismatch) → position stays on HL → orphan
4. **Stale orphan markers** → `_load_closing_markers()` corruption → same orphan closes repeatedly

**This session's ghost trades (ONDO, STRK, 0G at 14:52):** Path #2 — guardian orphan INSERT was failing due to trade_id collision, so no DB record was created, closing marker was set but never cleared, and the same orphan was re-closed every cycle.

## Fix Required

In `hl-sync-guardian.py` line ~3759:
```python
# OLD (collision-prone):
int(lev * 1000000)  # trade_id from HL leverage encoding

# FIX (use NULL or fresh DB ID):
NULL  # orphan trades never went to HL — no trade_id needed
# OR: cur_orphan.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM trades")
```

Also: clear the stale orphan records (ZEN id=9895, trade_id=5000000; CHIP id=9891, trade_id=3000000) to unblock future orphans.

## Constants Still Not Imported

`DEFAULT_TRADE_SIZE_USDT` (=$50) and `HL_MIN_NOTIONAL_USDT` (=$11) are defined in `hermes_constants.py` but **zero imports found** in any .py file. Hardcoded `$50` and `$11` still scattered throughout codebase. This is a separate tracking issue from the ghost trade bug.