# Guardian Orphan Closing Bug — 2026-05-08

## Summary
Decider_run opens positions on Hyperliquid via `brain.py trade add` → `mirror_open()`. Guardian runs parallel reconciliation cycles and finds the new HL positions BEFORE `brain.py` has written PostgreSQL records. Guardian's orphan-closing logic (hardcoded `trade_id IN (3000000, 5000000)` check) finds no matching DB record, treats the new position as an orphan, and closes it immediately.

Result: All 13 tokens that traded on HL (EIGEN, ATOM, ADA, CAKE, DYM, 2Z, APEX, LINK, MORPHO, BSV, MON, TIA, UMA, etc.) show 8-33 second open-close lifetimes on Hyperliquid with $0 PnL. No PostgreSQL records exist for any of them.

## Root Cause Chain

```
decider_run:execute_trade()
  → subprocess.run(['brain.py', 'trade', 'add', ...])
    → brain.py add_trade()
      → mirror_open() on HL  ← HL position opens here
      → PostgreSQL INSERT    ← runs AFTER HL confirm, but guardian runs parallel

guardian: reconcile() [runs every ~30s]
  → get_open_hype_positions()  ← sees new HL position
  → queries PostgreSQL for id IN (3000000, 5000000)  ← finds nothing
  → ORPHAN GUARD continue at line 1145-1148  ← OLD path: skips cleanly
  OR (new block lines 3638-3678): ← NEW path: creates record then closes
  → _close_orphan_paper_trade_by_id()  ← closes HL position
  → _clear_closing_marker()  ← only if close_ok=True
```

## The New Orphan Block (Uncommitted, lines 3638-3678)

The uncommitted diff added a new `else:` block at lines 3638-3678 that:
1. Creates a guardian_orphan_insert record with `trade_id = lev * 1000000`
2. Calls `_close_orphan_paper_trade_by_id()` which searches by `id` (auto-increment), not `trade_id` — structural mismatch
3. Conditionally clears the closing marker only if `close_ok=True`

But the **ORPHAN GUARD** at line 1145-1148 (`continue`) already skips before reaching this block. The new block is **dead code** — it only triggers if a position reaches Step 6 orphan detection without going through the reconcile path.

## Why 48 Markers Have `trade_id: null`

All 48 entries in `guardian-closing-markers.json` have `trade_id: null`. The orphan INSERT uses `trade_id = lev * 1000000`. Either:
1. The INSERT failed entirely (no record created), but `_save_closing_marker()` already ran
2. A different code path created the markers without a trade_id

The `trade_id: null` suggests the markers were created by `_save_closing_marker()` WITHOUT the subsequent INSERT running successfully.

## Evidence

- **PostgreSQL trades table**: only 2 rows — PURR (id=8780, trade_id=3000000) and XLM (id=8774, trade_id=5000000). Both are closed guardian orphans. No records for EIGEN, ATOM, ADA, CAKE, DYM, etc.
- **HL fill data** (user-provided): 13 tokens opened and closed in 8-33 second intervals at 17:08-17:30 on May 8
- **pipeline.log**: No entries for May 8 17:08-17:30 — pipeline wasn't running during incident window
- **guardian-closing-markers.json**: 48 stale entries (May 6–May 8 20:22), all with `trade_id: null`
- **systemd journalctl** (18:03): "SKIP: ADA — guardian closing in progress (race guard)" — decider_run IS checking closing markers and blocking tokens

## Fix

1. **Clear `guardian-closing-markers.json`** — delete all 48 stale entries to unblock tokens
2. **Remove the orphan creation block** (lines 3638-3678 in uncommitted diff) — it's dead code that creates phantom records
3. **Ensure brain.py PostgreSQL INSERT happens BEFORE `mirror_open()` returns** — or add the PostgreSQL record before the HL position is visible to the guardian's next reconcile cycle
4. **Verify `_clear_closing_marker()` is called on ALL exit paths** — including exceptions

## Diagnostic SQL

```sql
-- Check all guardian orphan records (trade_id 3000000/5000000)
SELECT id, token, direction, status, entry_price, exit_price, trade_id, close_reason, is_guardian_close
FROM trades WHERE trade_id IN (3000000, 5000000);

-- Check if any trades have trade_id set (should only be the 2 orphans)
SELECT token, trade_id, status FROM trades WHERE trade_id IS NOT NULL;

-- Check trades with guardian close
SELECT token, status, entry_time, close_time, is_guardian_close, close_reason
FROM trades WHERE is_guardian_close = True ORDER BY entry_time DESC;
```