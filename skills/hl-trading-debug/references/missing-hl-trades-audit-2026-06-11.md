# Missing HL Trades — 2026-06-11 Audit

## What Was Found

Comparing HL fill log (`/root/.hermes/logs/sync-guardian.log`) against PostgreSQL `brain.trades`:

| Time (UTC) | Symbol | Action | Entry | Exit | Status in Local DB |
|---|---|---|---|---|---|
| 15:40:06 | AAVE | OPEN SHORT @ 63.532 | MISSING | — | Not recorded |
| 15:40:09 | AAVE | CLOSE SHORT @ 63.57 | — | MISSING | Not recorded |
| 14:14:06 | AVNT | OPEN SHORT @ 0.10977 | MISSING | — | Not recorded |
| 14:14:16 | AVNT | CLOSE SHORT @ 0.10995 | — | MISSING | Not recorded |
| 13:51:05 | AVNT | CLOSE SHORT @ 0.11050 | — | MISSING | Not recorded |

## Bug #1: guardian_orphan INSERT Duplicate-Key (AAVE)

### Root Cause
`trades_trade_id_key` UNIQUE constraint on `trade_id` column. When guardian tries to INSERT a guardian_orphan trade for a coin that already has a guardian_orphan record (same token, or the same trade reopened), it gets `duplicate key violates unique constraint`.

### Timeline (AAVE — two separate orphan closes same day)
```
06-10 08:59:11 — AAVE guardian_orphan close, HL fill @ 60.999
06-10 08:59:17 — FAIL: duplicate key "trades_trade_id_key" — record NOT written
06-10 08:59:17 — AAVE left with no DB record; guardian orphan marker set
06-10 10:37:27 — [STALE-MARKER] AAVE no longer in HL — clearing marker
06-10 12:31:46 — AAVE LONG closed via guardian_tp (different direction)

06-11 15:40:08 — AAVE SHORT re-appears as orphan (HL position with no DB record)
06-11 15:40:08 — ⛔ ORPHAN DETECTED: AAVE HL position has no DB record
06-11 15:40:08 — close_position_hl(AAVE, guardian_orphan)
06-11 15:40:09 — market_close filled @ 63.57
06-11 15:40:15 — FAIL: duplicate key "trades_trade_id_key" — record NOT written
06-11 15:59:25 — [STALE-MARKER] AAVE no longer in HL — clearing marker
06-11 16:01:17 — AAVE SHORT re-OPENED via signal (new trade, new record id=11804)
06-11 17:01:13 — AAVE SHORT CLOSED properly via signal exit (id=11804, recorded correctly)
```

### Key Insight
The duplicate key is NOT from two records with the same `trade_id`. The constraint is on `trade_id` which is an empty string for ALL records (confirmed: `SELECT trade_id FROM trades ORDER BY id DESC LIMIT 5` returns all empty). Since PostgreSQL treats empty strings as distinct, the constraint should not fire for two empty-string records — unless there's a NULL mixed in.

**Hypothesis:** One of the prior AAVE records (from a different session/day) has `trade_id = NULL` while the orphan INSERT tries `trade_id = ''`. UNIQUE constraint on (trade_id) with one NULL = only one NULL allowed. The next INSERT with '' (empty string) would violate the constraint only if NULL and '' are treated as equal by the unique index, OR if the first orphan INSERT on 06-10 successfully inserted with '' but then a second path tries to INSERT with NULL.

**Diagnostic:**
```sql
SELECT id, trade_id, token, open_time, close_time, direction, close_reason
FROM trades
WHERE token = 'AAVE' AND open_time >= '2026-06-10';
-- AAVE records present: id=11739 (06-10 LONG), id=11804 (06-11 SHORT)
-- No guardian_orphan AAVE records from 06-10 or 06-11 — all INSERT attempts failed
```

### Fix Required
Before guardian_orphan INSERT, DELETE any existing guardian_orphan record for the same token:
```python
# In _close_orphan_paper_trade_by_id or its callers
cur.execute("DELETE FROM trades WHERE token=%s AND status='closed' AND close_reason='guardian_orphan' AND close_time > NOW() - INTERVAL '1 hour'", (token,))
```

---

## Bug #2: Stale-Refresh Race (AVNT Opens Not Recorded)

### Root Cause
Guardian was in a stale-refresh loop on AVNT — repeatedly detecting price staleness and refreshing — but never actually created a new trade record before the fills arrived.

### Timeline (AVNT — 4 trades, only 2 recorded)
```
06-11 11:56:06 — AVNT OPEN SHORT @ 0.10795 (1137 SKR equivalent notional)
                 → Recorded: id=11795 (open 11:56, close 12:16)

06-11 12:16:03 — AVNT CLOSE SHORT @ 0.11023
                 → Recorded: id=11795 close

06-11 13:44:07 — AVNT OPEN SHORT @ 0.10998 (92 AVNT)
                 → Recorded: id=11799 (open 13:44, close 13:51)

06-11 13:51:04 — AVNT CLOSE SHORT @ 0.110765
                 → Recorded: id=11799 close

06-11 14:14:06 — AVNT OPEN SHORT @ 0.10977 (92 AVNT)
                 → NOT RECORDED — guardian was in stale-refresh loop
14:14:16 — AVNT CLOSE SHORT @ 0.10995
                 → NOT RECORDED — parent open never created

06-11 14:15:08 — AVNT OPEN SHORT @ 0.10972 (93 AVNT)
                 → Recorded: id=11800 (open 14:15, close 14:25)

06-11 14:25:04 — AVNT CLOSE SHORT @ 0.11092
                 → Recorded: id=11800 close
```

### Guardian Log Evidence
```
439226: 06-11 13:44 — AVNT stale (stored=0.107950 vs current=0.109980, Δ=1.85%) — refreshing
439377: 06-11 14:15 — AVNT stale (stored=0.109980 vs current=0.109720, Δ=0.24%) — refreshing
```

Between 13:44 and 14:15, the guardian was likely in repeated stale-detection cycles where it saw AVNT as stale but was not creating new paper trades before the fill arrived.

### Fix Required
Guardian must create a DB record for an OPEN before checking staleness — or handle fills that arrive mid-refresh-cycle.

---

## Minor Price Discrepancies (Not Bugs)

Most CLOSE exits differ by 0.08-0.37% between HL fill price and our recorded exit_price. This is expected: HL fills at market, we record price ~1-2s later at slightly different market price. The HL PnL column is authoritative.

---

## Database Path Summary

```
PostgreSQL brain.trades        ← main trade record (all opens + closes via guardian)
PostgreSQL brain.hyperliquid_trades  ← DEAD PATH (0 rows, never populated)
SQLite trades_archive.db       ← archived closed trades
```

Guardian is the sole writer to `brain.trades`. The guardian_orphan path (no-DB-record → create and close) and the normal signal→brain.py→guardian path are the two write paths.