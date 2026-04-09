# ATR + TP/SL Cleanup Plan

## Goal
Fix the duplicate close-position orders on Hyperliquid and streamline the TP/SL lifecycle so:
1. All stale HL TP/SL orders are removed before fresh ones are placed
2. Fresh TP/SL comes from the current ATR multipliers in the DB
3. One authoritative system manages TP/SL on HL — not two competing scripts

---

## Context / Assumptions

### Current Architecture (Problem)
Two scripts write TP/SL to HL:

| Script | TP/SL Role | Runs |
|---|---|---|
| `batch_tpsl_rewrite.py` | Computes ATR SL/TP, writes to DB, does NOT place on HL (guardian-managed coins only) | Every 1 min (`hermes-atr-sl-updater.timer`) |
| `hl-sync-guardian.py` (`reconcile_tp_sl`) | Reads DB SL/TP, places/updates on HL if move is "favorable" | Every 1 min (pipeline) |

**Problem 1 — Guardian's "favorable move" gate blocks fresh ATR-based SL/TP:**
- `reconcile_tp_sl` only moves TP/SL if it improves in the favorable direction
- `batch_tpsl_rewrite` writes new ATR-based SL/TP to DB every minute
- If market moves against position, the "favorable" gate prevents updating to new (correct) ATR levels
- Result: HL has stale TP/SL; DB has correct ATR-based TP/SL — out of sync

**Problem 2 — No atomic cancel-then-place in `reconcile_tp_sl`:**
- `replace_sl` / `replace_tp` try to MODIFY existing orders
- They call `_find_open_trigger_order` which looks in a 55-second cached open_orders list
- On race conditions: old order not yet removed from cache → modify call succeeds on stale OID → ghost order
- No place where we explicitly CANCEL all existing TP/SL before placing new ones

**Problem 3 — Duplicate close_position calls:**
- `close_position` in `hyperliquid_exchange.py` (the market-close helper) is called from ≥5 places in guardian
- Deduplication set `_CLOSED_THIS_CYCLE` is persisted to disk (good for crash-restart) but not threadsafe
- If two guardian cycles overlap (timer overlap, or fast re-run), the same trade_id can get `close_position` called twice before the dedup set is saved

**Problem 4 — Two different ATR multiplier tables:**
- `decider_run.py` `_compute_dynamic_sl` / `_compute_dynamic_tp` — used by `decider_run` and `hl-sync-guardian`
- `position_manager.py` `_pm_atr_multiplier` — different k values, used by `position_manager`
- `batch_tpsl_rewrite.py` `compute_sl_tp` — THIRD different k table
- Three sources of truth for the same ATR math → inconsistent SL/TP levels

---

## Proposed Approach

### Phase 1: Audit and unify ATR multiplier tables
Consolidate all ATR k-multiplier logic into one place (`decider_run.py` exports `_compute_dynamic_sl` / `_compute_dynamic_tp`). Patch `position_manager.py` and `batch_tpsl_rewrite.py` to import from there instead of their own copies.

### Phase 2: Implement atomic cancel-then-place in `hl-sync-guardian`
Add a `clean_tpsl_orders(coin)` helper that:
1. Fetches ALL open trigger orders for the coin from HL (fresh API, not cache)
2. Cancels ALL TP and SL orders found (by OID + CLOID)
3. Waits for confirmation
4. Returns the list of cancelled orders

Patch `reconcile_tp_sl` to call `clean_tpsl_orders` BEFORE computing and placing new TP/SL.

### Phase 3: Fix duplicate close_position race in `hl-sync-guardian`
1. Add file-based lock: `_close_lock_<token>.lock` created before `close_position_hl`, deleted after
2. Add `_CLOSED_THIS_CYCLE` update BEFORE the actual HL call (not after)
3. Make `_save_closed_set()` called inside the try block before `close_position_hl`

### Phase 4: Ensure `batch_tpsl_rewrite` and `hl-sync-guardian` don't conflict
- `batch_tpsl_rewrite`: compute-only for ALL coins (not just guardian-managed). Keep writing to DB.
- `hl-sync-guardian` `reconcile_tp_sl`: the sole writer to HL
- OR: disable `batch_tpsl_rewrite` entirely if `reconcile_tp_sl` is the authoritative system

---

## Step-by-Step Plan

### Step 1: Unify ATR multipliers
**File: `/root/.hermes/scripts/decider_run.py`**
- Export `_atr_multiplier` and `_compute_dynamic_sl` / `_compute_dynamic_tp` at module level
- Ensure all k values (SL: 1.5/2.0/2.5, TP: 4.5/6.0/7.5) are defined here once

**File: `/root/.hermes/scripts/position_manager.py`**
- Replace `_pm_atr_multiplier` with `from decider_run import _atr_multiplier`
- Replace calls to `_pm_atr_multiplier` with `_atr_multiplier(token, atr_pct)`
- Keep local `_atr_multiplier` only if import fails (graceful degradation)

**File: `/root/.hermes/scripts/batch_tpsl_rewrite.py`**
- Replace `compute_sl_tp` with import from `decider_run`: `_compute_dynamic_sl` / `_compute_dynamic_tp`
- Pass `atr` (absolute) and `atr_pct` (percentage) correctly

**File: `/root/.hermes/scripts/hl-sync-guardian.py`**
- Already uses `decider_run._compute_dynamic_sl` / `_compute_dynamic_tp` — confirm no changes needed here

### Step 2: Add atomic clean_tpsl_orders helper
**File: `/root/.hermes/scripts/hyperliquid_exchange.py`**
- Add `clean_all_tpsl_orders(coin: str) -> dict` that:
  1. Calls `get_all_hl_orders()` (uncached) and filters to trigger orders for the coin
  2. Cancels each by OID + CLOID
  3. Returns `{'cancelled': [oids], 'errors': [...]}`
- Add `_exchange_rate_limit()` calls before each cancel (1s delay between cancels)

**File: `/root/.hermes/scripts/hl-sync-guardian.py`**
- In `reconcile_tp_sl`, before computing new SL/TP:
  ```python
  clean_result = clean_all_tpsl_orders(coin)
  if clean_result['cancelled']:
      log(f'  🗑️ {coin} cancelled {len(clean_result["cancelled"])} stale orders')
      time.sleep(2)  # let HL process cancellations
  ```

### Step 3: Fix duplicate close race
**File: `/root/.hermes/scripts/hl-sync-guardian.py`**
- Around `close_position_hl` (line ~388):
  1. Create `/tmp/hermes-close-lock-{token}.lock` (原子性)
  2. Check if trade already in `_CLOSED_THIS_CYCLE` before proceeding
  3. Add to `_CLOSED_THIS_CYCLE` and save to disk BEFORE calling `close_position_hl`
  4. After HL returns, delete lock file in `finally:` block
- Also check `_save_closed_set()` is called BEFORE the HL API call, not after

### Step 4: Resolve batch_tpsl_rewrite vs guardian conflict
Pick one approach:

**Option A (Preferred):** Keep `batch_tpsl_rewrite` as compute-only (it already is for guardian-managed coins). Make `hl-sync-guardian` the sole TP/SL writer to HL. Remove any redundant cancel/place from `batch_tpsl_rewrite`.

**Option B:** If `batch_tpsl_rewrite` is more reliable, disable `reconcile_tp_sl` in guardian and let batch_tpsl_rewrite do full cancel+place cycle.

Recommendation: **Option A** — `hl-sync-guardian` is already in the pipeline and has the breach detection safety net.

### Step 5: Verify
1. Run `python3 /root/.hermes/scripts/smoke_test.py --critical` — all checks pass
2. Check HL open orders for a test token — should be exactly 1 TP + 1 SL (no ghosts)
3. Check `smoke_heal.log` — no duplicate close attempts
4. Check `wasp.log` — no TP/SL warnings for missing orders

---

## Files Likely to Change

| File | Change |
|---|---|
| `/root/.hermes/scripts/decider_run.py` | Export `_atr_multiplier` at module level; add docstrings to existing functions |
| `/root/.hermes/scripts/position_manager.py` | Import `_atr_multiplier` from decider_run; remove local duplicate |
| `/root/.hermes/scripts/batch_tpsl_rewrite.py` | Replace `compute_sl_tp` with decider_run imports; keep DB-write-only behavior for guardian-managed coins |
| `/root/.hermes/scripts/hyperliquid_exchange.py` | Add `clean_all_tpsl_orders()` helper |
| `/root/.hermes/scripts/hl-sync-guardian.py` | Call `clean_all_tpsl_orders` before TP/SL reconcile; fix close_position race with file locks + pre-save dedup set |

## Risks / Tradeoffs

- **Risk:** Changing ATR multiplier imports mid-session could briefly change SL/TP levels for live positions → small PnL impact
- **Mitigation:** Changes to multiplier logic only affect future TP/SL recalculations, not existing placed orders (unless cancel-then-place fires)
- **Risk:** File locks on `close_position_hl` could cause hangs if lock not released → use `fcntl.flock` with timeout (30s)
- **Open Question:** Should `batch_tpsl_rewrite` be disabled entirely once `clean_tpsl_orders` is deployed in guardian? (It may be redundant.)
- **Open Question:** PAXG/AAVE/MORPHO/ASTER cannot have HL TP/SL at all — should these be handled by `self_close_watcher` only, with no attempt to place on HL?

## Validation / Test Plan

1. Run in dry-run mode first: `python3 batch_tpsl_rewrite.py --dry-run`
2. Check `wasp.log` after deploying — should show "X stale orders cancelled"
3. Monitor HL open orders via `get_all_hl_orders()` — should never have >2 trigger orders per token
4. After deployment, watch `smoke_heal.log` for 24h — no "duplicate close" entries
