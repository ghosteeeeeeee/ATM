# ATR Issues — Disable HL Close Orders, Beef Up Internal ATR Tracking

## Goal

Disable the broken HL close-order placement (`_execute_atr_bulk_updates`) and make the internal ATR TP/SL hit detection + self-close pipeline bulletproof. The system already has all the pieces — this is hardening and bug fixing.

---

## Current State

### What's Already Disabled (Good)
- `ATR_HL_ORDERS_ENABLED = False` at line 73 of `position_manager.py`
- `_execute_atr_bulk_updates()` exists but is never called — kill switch is off

### The Working Internal Pipeline (Keep Intact)
```
check_and_manage_positions()  [line 1827]
  ├── _collect_atr_updates()   [line 1278] — compute fresh ATR SL/TP per position
  ├── _persist_atr_levels()   [line 1422] — write to brain DB
  ├── check_atr_tp_sl_hits()  [line  360] — detect if price crossed DB levels
  └── close_paper_position()   [line  841] — close DB + mirror_close() to HL
```

### The Broken Part
`mirror_close()` (the market-close path in `close_paper_position`) is unreliable for the close-order use case — orders won't fill at meaningful prices, creating gap risk and poor fills.

### What We Want Instead
Internal ATR hit detection drives ALL exits. HL gets a market close via `mirror_close()` as a simple market order — no trigger orders.

---

## Step-by-Step Plan

### Step 1: Disable HL ATR Order Push Completely
**File:** `/root/.hermes/scripts/position_manager.py`

Two things are already done, but verify and document:

1. Line 73: Confirm `ATR_HL_ORDERS_ENABLED = False`
2. Lines 1862-1863: The `_execute_atr_bulk_updates()` call is guarded by the flag — no code change needed, just confirm
3. Add a kill-switch comment explaining why it's disabled

```python
# KILL SWITCH: HL trigger-order placement for ATR SL/TP is DISABLED.
# The internal ATR pipeline (_collect_atr_updates → _persist_atr_levels →
# check_atr_tp_sl_hits → close_paper_position) handles ATR exits via market mirror.
# _execute_atr_bulk_updates() is broken for close-order use cases.
```

### Step 2: Audit `_collect_atr_updates()` — ATR Threshold Bug
**File:** `/root/.hermes/scripts/position_manager.py` (lines 1278–1419)

**Bug:** Delta threshold check (line 1395-1400) only fires when `needs_sl/needs_tp` is True from the trailing logic. But the trailing logic can set `needs_sl=True` even when the delta is tiny (because it already passed the `new_sl > current_sl` check for LONG). The real threshold logic is correct but the logging at line 1367 shows what was *computed*, not whether it actually passed the threshold. 

**Fix:** Make the debug print show `needs_sl/needs_tp` and whether it passed the delta threshold, so we can monitor this in production.

### Step 3: Audit `check_atr_tp_sl_hits()` — The Core Hit Detector
**File:** `/root/.hermes/scripts/position_manager.py` (lines 360–428)

**Problem 1:** Requires **both** SL and TP to be set in DB to fire (`if not sl or not tp: continue` at line 402). If a position has only SL or only TP, it will never be closed on ATR hit.

**Fix:** Make SL-only or TP-only positions still eligible for hit detection. Only require the relevant level:
- For `atr_sl_hit`: require SL only
- For `atr_tp_hit`: require TP only

**Problem 2:** Uses `stop_loss` and `target` from the `pos` dict passed in — which comes from `refresh_current_prices()`. If the refresh doesn't have the DB-written ATR values (race condition or stale cache), hits won't detect.

**Fix:** `check_atr_tp_sl_hits()` should read directly from the DB, not trust the `pos` dict's SL/TP. Add a direct DB lookup for each trade_id.

### Step 4: Add Direct DB Read in `check_atr_tp_sl_hits()`
**File:** `/root/.hermes/scripts/position_manager.py`

Refactor `check_atr_tp_sl_hits()` to optionally accept a `db_conn` and read the current SL/TP directly from DB for each trade, bypassing any stale in-memory values:

```python
def check_atr_tp_sl_hits(open_positions: List[Dict], db_conn=None) -> List[Dict]:
    # ... existing logic ...
    # After fetching row from pos dict, overwrite sl/tp with live DB values
    if db_conn:
        cur.execute("SELECT stop_loss, target FROM trades WHERE id = %s AND status = 'open'",
                    (trade_id,))
        db_row = cur.fetchone()
        if db_row:
            sl = float(db_row['stop_loss']) if db_row['stop_loss'] else sl
            tp = float(db_row['target']) if db_row['target'] else tp
```

### Step 5: Harden `close_paper_position()` ATR Cleanup
**File:** `/root/.hermes/scripts/position_manager.py` (lines 967–977)

The ATR cleanup calls `cancel_all_open_orders(hype_token)` which cancels ALL open orders for that token. This is overly broad — it could cancel SL/TP orders for OTHER open positions on the same token.

**Fix:** Only cancel the specific stale orders for this trade_id. The `_execute_atr_bulk_updates()` logic that matches by trigger price proximity is correct — steal that logic for the cleanup path.

```python
# Cancel only the specific SL/TP orders for this position
# Match by token + trigger price matching old SL/TP ± tolerance
```

### Step 6: Ensure `mirror_close()` Is the Only HL Interaction
**File:** `/root/.hermes/scripts/position_manager.py`

`close_paper_position()` already calls `mirror_close()` for HL market close (line 980). This is the correct behavior — a simple market order that will fill at market price. This should stay.

Confirm that `mirror_close()` handles both LONG (sell to close) and SHORT (buy to close) correctly and verify the `hype_coin()` mapping is correct for all tokens in the current portfolio.

### Step 7: Add Health Monitoring / Logging
**Files:** `position_manager.py`, `trading.md`

Add structured logging so we can detect if the pipeline is silently failing:

```
[ATR] IMX LONG: computed SL=0.1449 TP=0.1492 — passed threshold, written to DB
[ATR] IMX LONG: hit detection — price=0.1435 <= SL=0.1449 → CLOSING
[Position Manager] Closed trade 123 (atr_sl_hit)
[ATR CLEANUP] Cancelled 1 stale order for IMX
[Position Manager] HYPE mirror_close SUCCESS: IMX
```

All of these already exist at various points — confirm they're all firing correctly.

### Step 8: End-to-End Test
**Script:** `/root/.hermes/scripts/atr_dry_run.py`

Run the dry-run to verify `_collect_atr_updates()` works for all open positions, then simulate hit detection by patching a price slightly below SL for one position and confirming the hit fires.

---

## Files Likely to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/position_manager.py` | Steps 1, 2, 3, 4, 5, 6, 7 |
| `/root/.hermes/brain/trading.md` | Step 7 monitoring |

---

## Tests / Validation

1. **Unit test:** Patch a position's `current_price` below its SL in the DB, call `check_atr_tp_sl_hits()`, verify it returns the hit
2. **Unit test:** Patch a position with only SL (no TP), verify SL hit still fires  
3. **Dry run:** Run `python3 atr_dry_run.py` — should output per-position ATR levels for all 10 open positions
4. **Manual inspection:** Check the Streamlit dashboard (`/signals`) to confirm position SL/TP values match what's in the DB

---

## Risks & Tradeoffs

- **Risk:** Changing `check_atr_tp_sl_hits()` to read from DB directly could slow down the pipeline (one extra DB query per position per cycle). **Mitigation:** Read all at once with a `WHERE id IN (...)` query.
- **Tradeoff:** The ATR cleanup (Step 5) currently cancels ALL orders for a token. Fixing it to cancel only the specific orders reduces blast radius but is more complex. **Mitigation:** Use the existing trigger-price-matching logic from `_execute_atr_bulk_updates()`.
- **Open Question:** Does `mirror_close()` reliably fill on HL for both LONG and SHORT? Need to verify with T.

---

## Open Questions for T

1. Is `mirror_close()` working reliably for both LONG and SHORT? The market close should fill at market — is it?
2. Are there specific tokens where the ATR levels feel wrong (SL too tight or too loose)?
3. Should we also disable `ATR_HL_ORDERS_ENABLED` entirely in the config, or just leave the `= False` default?
