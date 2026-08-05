# hl-sync-guardian Audit — June 12, 2026

## Files Audited
- `/root/.hermes/scripts/hl-sync-guardian.py` — 4,226 lines after fixes

## Bugs Found & Fixed

### Bug 1 (P1) — Unreachable dead code after `continue`
**Lines:** 3101-3116 (removed)
**File:** hl-sync-guardian.py
**Issue:** After `if direction_changed: ... continue` at line 3100, a full ATR/SL/TP recompute block was unreachable. It referenced `real_atr` which was only defined in the `else` branch below — NameError if reached.
**Fix:** Deleted lines 3101-3116.

### Bug 2 (P2) — Return tuple not unpacked in pending retry path
**Line:** 4198
**File:** hl-sync-guardian.py
**Issue:** `_poll_hl_fills_for_close()` returns `(wavg, pnl)` tuple. Call site passed it as scalar to `_close_orphan_paper_trade_by_id()` and formatted with `.6f` → TypeError.
**Fix:**
```python
# Before:
hl_exit = _poll_hl_fills_for_close(token, close_start_ms)
# After:
hl_exit_px, realized_pnl = _poll_hl_fills_for_close(token, close_start_ms)
```

### Bug 3 (P2) — Duplicate guard SELECT missing direction filter
**Lines:** 1176-1205
**File:** hl-sync-guardian.py
**Issue:** SELECT had no direction filter, UPDATE used orphan HL coin's direction instead of matched paper trade's direction. Could corrupt opposite-direction records.
**Fix:** SELECT now fetches `direction` from matched row; UPDATE and `_mark_hl_reconciled` use `existing_direction`.

### Bug 4 (P2) — `f.get('dir')` not defensive against None
**Lines:** 519, 893, 914, 2600
**File:** hl-sync-guardian.py
**Issue:** `str(f.get('dir', ''))` silently passes if dir=None (str(None)='None', 'Open' in 'None'=False — safe but implicit).
**Fix:** `str(f.get('dir') or '')` — explicit None coercion.

### Bug 5 (P3) — False positive (no code change)
**File:** hl-sync-guardian.py
**Issue:** Subagent claimed `_poll_open_fill_once` was called outside `if dup_row` block. Verified: it IS inside the block. False positive from line-number miscounting.

## Prior Fixes (already in file before this audit)
- range(3) → range(6) for fill polling timeouts (lines ~932, ~982)
- `_close_paper_trade_db` atomic single UPDATE
- `add_orphan_trade` sets is_guardian_close=TRUE, guardian_closed=TRUE
- Duplicate guard SELECT before orphan creation
- `_clear_pending_retry` split into locked/unlocked versions
- `_record_loss_cooldown` moved outside try block

## Not Fixed (out of scope this session)
- analyze-trades: AAVE @ 15:40, AVNT @ 13:44/14:14 backfill still pending

## Subagent Performance
- Batch 1 (lines 1-2130): completed in 206s, found 5 bugs
- Batch 2 (lines 2131-4240): timed out at 600s — main session audited remaining range
- Lesson: split hl-sync-guardian into max 2 batches, audit any timeout remainder in main session
