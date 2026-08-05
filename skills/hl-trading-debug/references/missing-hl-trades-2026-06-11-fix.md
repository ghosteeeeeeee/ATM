# Missing HL Trades — 2026-06-11 Audit & Fix

## Trades Missing from Local DB (PostgreSQL brain.trades)

| HL Time (UTC) | Symbol | Action | HL Price | HL Size | Missing Because |
|---|---|---|---|---|---|
| 15:40:06 | AAVE | OPEN SHORT | 63.532 | 0.16 | `signal_gen` never created paper trade; guardian orphan INSERT failed silently |
| 15:40:09 | AAVE | CLOSE SHORT | 63.57 | 0.16 | Guardian closed HL @63.57 ✓ but INSERT duplicate-key → except block silent death |
| 13:44:06 | AVNT | OPEN SHORT | 0.10977 | 92 | Guardian in stale-refresh loop on old LONG record; never created new SHORT paper trade |
| 13:51:05 | AVNT | CLOSE SHORT | 0.11050 | 92 | Parent open not recorded |
| 14:14:06 | AVNT | OPEN SHORT | 0.10972 | 92 | Same stale-refresh loop; new position not created |
| 14:14:16 | AVNT | CLOSE SHORT | 0.10995 | 92 | Parent open not recorded |

All other HL trades on 2026-06-11 matched a local DB record.

---

## Root Cause #1 — Guardian Path B Orphan INSERT Silent Death

### Two Orphan Handling Paths

**Path A** (`add_orphan_trade` at ~line 745):
```sql
INSERT INTO trades (...) SELECT ..., WHERE NOT EXISTS (SELECT 1 FROM trades WHERE token=%s AND ...)
RETURNING id
```
- Race: two cycles both pass WHERE NOT EXISTS, one INSERT wins, other gets `fetchone()==None`
- Handler: checks `if row is None: return None` → caller uses existing record → **correct**

**Path B** (orphan close fallback at ~line 3717 — the "no DB record found" path):
```sql
INSERT INTO trades (...) VALUES (...)
RETURNING id
```
- Race: second cycle hits `trades_trade_id_key` UNIQUE violation
- Handler (BEFORE FIX): `except Exception as e: log(...FAIL); _t.sleep(3)` → **silent death**
- HL close already happened → no record created AND no record closed → **leaked**

### What Actually Collides on `trade_id`

`trade_id` is NOT the PostgreSQL `id` (which uses `trades_id_seq`). `trade_id` is a manual integer with UNIQUE constraint `trades_trade_id_key`. The INSERT at line ~3728 writes:
```python
int(lev * 1000000)  # e.g., lev=5 → 5000000
```
This collides when two cycles both try to create a guardian_orphan for the same token+leverage combination.

**BUT**: there are only 2 records in the entire DB with non-null trade_id (id=10214 ASTER=5000000, id=10281 PURR=3000000). The real collision is **between concurrent guardian cycles racing on the same orphan**, not legacy data.

### PostgreSQL Behavior

`INSERT ... RETURNING id` where the INSERT is blocked by a UNIQUE constraint on a non-id column:
- The INSERT does NOT silently skip
- It raises the constraint violation
- The entire transaction may be affected depending on isolation level
- `fetchone()` never runs → no result → except block fires

### Fix Applied (2026-06-11)

```sql
INSERT INTO trades (...) VALUES (...)
ON CONFLICT (trade_id) DO NOTHING
RETURNING id
```

Three-branch logic after `fetchone()`:
1. **Result != None** → INSERT won, we created the record → close it
2. **Result == None** → INSERT skipped (another cycle won) → find existing record → close it
3. **Genuine gap** (no record found in branch 2) → insert with `nextval('trades_id_seq')` as trade_id → close it

File: `/root/.hermes/scripts/hl-sync-guardian.py` ~line 3717

---

## Root Cause #2 — Stale Record Direction Mismatch

### The Sequence

1. AVNT LONG opened 2026-06-11 11:56:06 @ 0.10795, closed 12:16:03 @ 0.11063
2. Guardian tracked this as a self_close record: `{coin:'AVNT', direction:'LONG', entry_px:0.10795, ...}`
3. AVNT SHORT opened 13:44:07 @ 0.10998 — new HL position, **no DB record yet**
4. `_check_hard_stops` ran → looked up self_close record for AVNT → found stale LONG record
5. Stale check: `entry_delta = abs(0.10795 - 0.10998) / 0.10998 = 1.85% > 0.1%` → stale detected
6. **BUG**: recalculated SL/TP using `direction='SHORT'` (new HL direction) but stored it in the **same LONG self_close record**
7. Guardian never created a paper trade for 13:44 SHORT open
8. Same pattern repeated at 14:14 (SHORT open @ 0.10972, guardian in loop, record not created)

### Why the Self-Close Record Wasn't Cleared

The AVNT LONG self_close record was used to track SL/TP for that specific position. When the LONG closed at 12:16, there was nothing to trigger a self_close record deletion. The record persisted with its stale `direction='LONG'`.

### Fix Applied (2026-06-11)

```python
stored_direction = record.get('direction', '')
direction_changed = (
    stored_direction and
    stored_direction.upper() != direction.upper()
)
if entry_delta > 0.001 or direction_changed:
    # invalidate and recalculate from scratch
```

File: `/root/.hermes/scripts/hl-sync-guardian.py` ~line 3017

---

## Key PostgreSQL Queries Used

```sql
-- Check for non-null trade_ids
SELECT id, token, trade_id, open_time FROM trades WHERE trade_id IS NOT NULL AND trade_id > 0;

-- Check trades by token over date range
SELECT id, token, trade_id, leverage, open_time, close_time, status, signal_reason, guardian_reason
FROM trades WHERE token IN ('AAVE','AVNT') AND open_time >= '2026-06-10 00:00:00' ORDER BY open_time;

-- Confirm constraint definition
SELECT conname, contype, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'trades'::regclass AND conname = 'trades_trade_id_key';

-- Confirm id sequence
SELECT column_name, column_default FROM information_schema.columns
WHERE table_name='trades' AND column_name='id';
```

---

## Verification

Both fixes applied and syntax-checked:
```bash
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py
# Syntax OK
```

Guardian must be restarted to pick up the fixes.
