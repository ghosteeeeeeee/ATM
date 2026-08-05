# Guardian Orphan Triple-Bug — June 12, 2026

## Symptoms
Same-day duplicate orphans for ADA, MET, GALA. Each produces:
- Multiple HL close executions (2-4 per token)
- Multiple guardian_orphan DB trades
- Multiple `close_position_hl` calls, some failing with 429

## Three Bugs Fixed

### Bug 1 — `_check_hard_stops` Missing `_CLOSED_HL_COINS.add()`
**File**: `hl-sync-guardian.py` line ~3147
**Before**: `_CLOSED_HL_COINS.add(coin)` — no `.upper()`, plain string
**After**: `_CLOSED_HL_COINS.add(coin.upper())`
**Impact**: `_sweep_blocklist_trades` runs AFTER `_check_hard_stops` and checks `_CLOSED_HL_COINS` to skip tokens. Without `.upper()`, plain string doesn't match uppercase tokens in the set → `_sweep_blocklist_trades` sees token as still open → fires `_attempt_flip_position` → new orphan created.

### Bug 2 — Stale-Marker Cleanup Doesn't Clear Pending Retry
**File**: `hl-sync-guardian.py` lines ~3646-3652
**Problem**: When a closing marker is cleared as "stale" (token no longer in HL), the `_PENDING_RETRY_FILE` state is NOT cleared. Next cycle re-loads pending retry and attempts `close_position_hl` on non-existent position → 429 → cycle repeats.
**Fix**: Stale-marker cleanup now also calls `_clear_pending_retry([tok])` when clearing a stale marker.

### Bug 3 — Pending Retry Doesn't Check HL Positions Before `close_position_hl`
**File**: `hl-sync-guardian.py` lines ~4217-4237
**Problem**: `_load_pending_retry()` returns tokens whose HL closes failed last cycle. But the pending retry block runs BEFORE `hl_pos` is fetched (it's in the pre-cycle section before `while True`). Without checking if token is still in HL, it fires `close_position_hl` on a non-existent position → rate-limited → same token stays in pending retry forever.
**Fix**: Inline `get_open_hype_positions_curl()` call to check HL state. Split into `pending_in_hl` (retry) and `pending_gone` (just clear retry state).

## Pattern Summary
```
Market close fails (429) 
  → _CLOSED_HL_COINS.discard(token) 
  → pending_retry saved to file
  → next cycle: stale marker cleared (token not in HL) 
  → orphan re-created in same cycle (Bug 2)
  OR: pending retry fires close_position_hl on non-existent position (Bug 3)
  OR: _sweep_blocklist_trades re-triggers due to missing _CLOSED_HL_COINS (Bug 1)
```

## All `_CLOSED_HL_COINS.add()` Sites (must all use `.upper()`)
```
1198:  _CLOSED_HL_COINS.add(coin.upper())  ← reconcile dup_row path
1268:  _CLOSED_HL_COINS.add(coin.upper())  ← reconcile orphan creation path  
3147:  _CLOSED_HL_COINS.add(coin.upper())  ← _check_hard_stops [FIXED this session]
3706:  _CLOSED_HL_COINS.add(coin.upper())  ← Step 6 orphan close
```

## Verification
```bash
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py && echo "Syntax OK"
grep -n "_CLOSED_HL_COINS.add(" /root/.hermes/scripts/hl-sync-guardian.py
```
