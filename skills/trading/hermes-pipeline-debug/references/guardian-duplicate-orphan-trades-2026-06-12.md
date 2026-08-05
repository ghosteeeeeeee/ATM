# Guardian Duplicate Orphan Trades — 5 Compounding Bugs (2026-06-12)

## The Symptom

ADA, MET, and other tokens get duplicate open/close pairs in HL:
```
ADA Open Long @ 0.17271 → Close Long @ 0.17256  (14:57)
ADA Open Long @ 0.17212 → Close Long @ 0.17214  (14:58)
ADA Open Long @ 0.17215 → Close Long @ 0.17204  (15:04)
```
3 open/close pairs in 7 minutes. PostgreSQL has only 1 record (the first open).
Each HL close triggers a new orphan paper trade creation in the next cycle.

## Root Cause — 5 Compounding Bugs

### Bug A — Pending retry never cleared on Step 6 success

**File:** `hl-sync-guardian.py` Step 6 (lines ~3758, ~3819, ~3839)
**Severity:** Critical

When Step 6 (`_sync_orphan_hl_positions`) successfully closed an orphan paper trade,
`_clear_pending_retry([coin.upper()])` was never called. The token stayed in
`_PENDING_RETRY_FILE`. Next cycle loaded it in Step 5 (pending retry path) and fired
a SECOND `close_position_hl` call on the already-closed HL position → created a new
orphan → next cycle's Step 6 closed that → cycle repeats.

**Fix:** Add `_clear_pending_retry([coin.upper()])` to ALL THREE Step 6 success branches:
1. "existing orphan record found" path (line ~3839)
2. "INSERT succeeded, close it" path (line ~3819)
3. "INSERT skipped (race), close existing" path (line ~3759)

### Bug B — Step 6 failure path incorrectly saved to pending retry

**File:** `hl-sync-guardian.py` lines ~1291-1304 (reconcile_hype_to_paper orphan path)
**Severity:** High

When `market_close` failed in the reconcile_hype_to_paper orphan path (internal orphan),
it called `_save_pending_retry([coin])`. But Step 6 also owns orphan closes. The
pending retry path and Step 6 would both fire on the same token in the same cycle —
duplicate closes.

**Fix:** Remove `_save_pending_retry` from reconcile_hype_to_paper's orphan path entirely.
Step 6 (`_sync_orphan_hl_positions`) handles all orphan HL closes and manages its own
retry state via `_CLOSED_HL_COINS`.

### Bug C — Pending retry path ran before current orphan set was built

**File:** `hl-sync-guardian.py` Step 5 (pending retry) vs Step 6 (orphan close)
**Severity:** High

Step 5 (pending retry) runs at lines ~4223-4292. Step 6 (orphan close) builds its
`orphans` set and runs later. A token could be in BOTH `pending_in_hl` AND `orphans`.
Both paths fire on the same token in the same cycle.

**Fix:** In pending retry loop, check `if token.upper() in _CLOSED_HL_COINS` before
calling `close_position_hl`. If already in `_CLOSED_HL_COINS`, skip (Step 6 owns it).

### Bug D — `_check_hard_stops` didn't add to `_CLOSED_HL_COINS`

**File:** `hl-sync-guardian.py` `_check_hard_stops` success branch (line ~1756)
**Severity:** Medium

When `_check_hard_stops` successfully closed a trade via HL, it didn't add the
token to `_CLOSED_HL_COINS`. So `_check_and_close_breached_trades` (Step 11) saw
the token as UNPROTECTABLE and closed it again — creating a duplicate orphan.

**Fix:** Add `_CLOSED_HL_COINS.add(token.upper())` after successful HL close in
`_check_hard_stops`.

### Bug E — Pending retry used stale mid price for exit

**File:** `hl-sync-guardian.py` pending retry path (line ~4256)
**Severity:** Medium

The pending retry path used `curr_price` (mid estimate from `hype_cache.get_allMids()`)
as the exit price for `_close_orphan_paper_trade_by_id`. Mid ≠ actual HL fill price.

**Fix:** Use `hl_exit = _poll_hl_fills_for_close(token, int(curr_price))` instead.

---

## Guardian Orphan State Machine

Tokens flow through these states across cycles:

```
Token appears in HL but not in DB
    → reconcile_hype_to_paper creates orphan paper trade
    → Step 6: close_position_hl(token)
        → success: _clear_pending_retry + _clear_closing_marker
        → failure: DON'T save to pending_retry (Step 6 self-manages)
    → Token in _CLOSED_HL_COINS for rest of cycle

Next cycle:
    → Token NOT in HL (closed last cycle)
    → Token NOT in orphans (gone from HL)
    → Token NOT in pending retry (cleared on Step 6 success)
    → Done
```

**Key invariants:**
- `_CLOSED_HL_COINS`: cleared every cycle at line ~3591, rebuilt by Step 6 and `_check_hard_stops`
- `_PENDING_RETRY_FILE`: written only when `market_close` fails AND the path is NOT Step 6
- Step 6: ONLY orphan close path that should fire for tokens in `_CLOSED_HL_COINS`
- Pending retry: ONLY fires for tokens NOT in `_CLOSED_HL_COINS`

---

## Verification After Fix

```bash
# Syntax check
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py && echo "Syntax OK"

# All close_position calls should use CLOSE_SLIPPAGE
grep -n "close_position(token\|close_position(coin" /root/.hermes/scripts/hl-sync-guardian.py
# Expected: no output (all calls should have slippage=CLOSE_SLIPPAGE)

# All orphan close success branches should clear pending retry
grep -n "_clear_pending_retry" /root/.hermes/scripts/hl-sync-guardian.py
# Expected: 3 calls in Step 6 + 1 in pending retry skip path

# _check_hard_stops should add to _CLOSED_HL_COINS
grep -n "_CLOSED_HL_COINS.add" /root/.hermes/scripts/hl-sync-guardian.py
# Expected: at least 2 (Step 6 + _check_hard_stops)
```
