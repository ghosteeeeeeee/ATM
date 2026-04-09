# ATR Issues Continued #2 — Plan
**Date:** 2026-04-09 21:35 UTC
**Status:** PLANNING ONLY — no execution

---

## Goal

Disable the broken HL close-order functionality (which cannot place meaningful limit/market closes on HL) and harden the internal ATR TP/SL tracking system so that Hermes closes positions internally when ATR-based SL/TP triggers fire, without relying on HL orders.

---

## Current Context

### What's broken
The system cannot reliably place CLOSE orders on Hyperliquid in a meaningful way. `mirror_close()` works (market close) but limit close orders and the `_execute_atr_bulk_updates()` SL/TP update path have issues. The `close_position` → `mirror_close` path uses market orders only — no limit close.

### What already works
- **`_collect_atr_updates()`** in `position_manager.py` (lines 1182–1320): Computes ATR-based SL/TP for all open positions, deduplicates tokens, fetches fresh ATR per cycle, applies trailing-only-tighten logic
- **`_execute_atr_bulk_updates()`** in `position_manager.py` (lines 1323–1441): Pushes updated SL/TP to HL via cancel + re-place (for existing position management)
- **`should_cut_loser()`** in `position_manager.py` (lines 311–351): Checks live price vs SL price in DB
- **`check_stale_position()`** in `position_manager.py` (lines 354–432): Speed-based stale detection
- **`_pm_get_atr()`** / **`_force_fresh_atr()`** in `position_manager.py` (lines 1013–1179): ATR fetching from HL 15m candles
- **`check_cascade_flip()`**: Cascade flip detection

### What needs to be made bulletproof
1. **ATR TP/SL hit detection** — every pipeline cycle, check if current price has crossed the DB SL or TP level for any open position
2. **Internal close execution** — when ATR SL or TP is hit, call `close_paper_position()` to close internally (DB) + mirror to HL via `mirror_close()` (market)
3. **Stop relying on HL SL/TP trigger orders** — the HL trigger orders are unreliable as the execution path; Hermes should self-close based on its own ATR levels and treat HL mirror as best-effort
4. **Stale order cleanup** — cancel stale HL SL/TP orders for positions that were already closed internally

---

## Proposed Approach

### Phase 1: Audit and disable HL SL/TP order placement for closes

**Files:** `position_manager.py`, `hyperliquid_exchange.py`

- Find any code path that calls `_execute_atr_bulk_updates()` and deprecates/flags it as non-functional for close triggers
- Add a kill-switch flag (e.g., `ATR_HL_ORDERS_ENABLED = False`) to disable pushing SL/TP orders to HL
- The `cancel_bulk_orders` and `place_bulk_orders` paths remain usable for other purposes but the ATR close-order path is disabled

### Phase 2: Implement internal ATR TP/SL hit detection

**File:** `position_manager.py` — new function `check_atr_tp_sl_hits()`

```python
def check_atr_tp_sl_hits(open_positions: List[Dict]) -> List[Dict]:
    """
    Check every open position for ATR TP/SL hit.
    Returns list of positions where:
      - LONG: current_price <= stop_loss  → SL hit
      - LONG: current_price >= target     → TP hit
      - SHORT: current_price >= stop_loss → SL hit
      - SHORT: current_price <= target    → TP hit
    
    Reads current_price from the position dict (refreshed by refresh_current_prices()).
    """
```

Called in the main position loop before any other close logic.

### Phase 3: Wire ATR hit detection into close pipeline

**File:** `position_manager.py` — integrate `check_atr_tp_sl_hits()` into `check_and_manage_positions()`

In the main per-position loop (around line 600–800 where `should_cut_loser` is called):
1. First, check ATR TP/SL hits via `check_atr_tp_sl_hits()`
2. If hit → call `close_paper_position()` with reason `atr_sl_hit` or `atr_tp_hit`
3. Continue with existing stale/cut-loser checks as fallback

### Phase 4: Harden the ATR computation pipeline

1. **`_force_fresh_atr()`**: Ensure it handles:
   - HL API rate limit errors gracefully (don't crash the pipeline)
   - Tokens with no candle data (return None, skip the position)
   - Add logging so failures are visible in pipeline output

2. **`_collect_atr_updates()`**: 
   - Ensure the 0.3% delta threshold (`ATR_UPDATE_THRESHOLD_PCT`) is correct
   - Skip cascade-flip positions (already done — verify)
   - Ensure trailing logic (only tighten, never loosen) is working

3. **`refresh_current_prices()`**: Verify current prices are being refreshed every cycle for all open positions. This is the reference price for ATR hit detection.

### Phase 5: Cleanup stale HL orders for closed positions

When `close_paper_position()` is called for an ATR hit:
1. After internal close, attempt to cancel any HL SL/TP orders for that token via `cancel_all_open_orders(token)` — best-effort, don't block if it fails
2. This prevents orphaned HL trigger orders from firing after the position is already closed

---

## Step-by-Step Plan

| Step | Action | Files | Notes |
|------|--------|-------|-------|
| 1 | Add kill switch `ATR_HL_ORDERS_ENABLED = False` | `position_manager.py` | Disables `_execute_atr_bulk_updates()` call path |
| 2 | Add `check_atr_tp_sl_hits()` function | `position_manager.py` | Internal ATR TP/SL hit detection |
| 3 | Wire `check_atr_tp_sl_hits()` into `check_and_manage_positions()` loop | `position_manager.py` | Before stale/cut-loser checks |
| 4 | Add best-effort HL order cleanup after ATR hit close | `position_manager.py` | `cancel_all_open_orders()` in `close_paper_position()` |
| 5 | Harden `_force_fresh_atr()` error handling | `position_manager.py` | Add try/except with logging |
| 6 | Add `atr_sl_hit` / `atr_tp_hit` to `close_reasons` tracking | `position_manager.py` | New close reasons for analytics |
| 7 | Update `trading.md` with new architecture | `brain/trading.md` | Document the ATR self-close system |
| 8 | Test: dry-run `check_atr_tp_sl_hits()` on current positions | `position_manager.py` | Verify hit detection logic |

---

## Files Likely to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/position_manager.py` | Core changes: kill switch, new `check_atr_tp_sl_hits()`, wiring, HL cleanup |
| `/root/.hermes/brain/trading.md` | Document new ATR close architecture |

---

## Tests / Validation

1. **Dry-run test**: Run `check_atr_tp_sl_hits()` against current open positions — should return empty list (no hits) or report any positions that are suspiciously close to SL/TP
2. **Simulate a hit**: Manually set a position's `current_price` to trigger SL or TP and verify it would be returned by `check_atr_tp_sl_hits()`
3. **Pipeline integration check**: Confirm `check_atr_tp_sl_hits()` is called every pipeline cycle in `check_and_manage_positions()`
4. **No HL orders placed**: With kill switch off, `_execute_atr_bulk_updates()` should not be called from the main loop

---

## Risks / Tradeoffs

- **Risk**: If `current_price` in DB is stale, ATR hit detection may fire incorrectly or miss actual hits. Mitigation: `refresh_current_prices()` must run every cycle (it does — called in `check_and_manage_positions()`)
- **Risk**: Closing via `mirror_close()` (market order) may not be the same as a limit close. Mitigation: market close is actually what we want for TP hits (we want out now). For SL hits, market close is acceptable as it's a worst-case protection.
- **Tradeoff**: Disabling HL SL/TP orders means we lose the "free" HL-side SL/TP protection. If Hermes crashes or the pipeline stops, positions won't auto-close on HL until the next run. Mitigation: `hl-sync-guardian.py` still runs every 60s and can reconcile.
- **Open Question**: Should we try to keep the `_execute_atr_bulk_updates()` path alive but only for TP/SL *updating* (not for close triggers)? If yes, keep the function but disable its close-order behavior and only use it for trail-tightening. The task says "disable that functionality" — confirm this means fully disable or just disable the close-order use.

---

## Open Questions

1. **Confirm scope of "disable"**: Does "disable that functionality" mean fully remove the HL close-order code path, or just stop calling it for ATR hits? (Currently reading as fully disable.)
2. **HL mirror as best-effort**: With internal ATR hit detection, `mirror_close()` to HL is still called — but it's a market close, not a limit. Is that acceptable for TP/SL hits?
3. **Existing open HL SL/TP orders**: There may be existing SL/TP trigger orders on HL from previous runs. Should a cleanup run be done on startup to cancel all existing HL SL/TP orders for tokens with open positions?
