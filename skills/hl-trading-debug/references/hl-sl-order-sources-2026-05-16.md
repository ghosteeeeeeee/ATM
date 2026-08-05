# HL SL Order Sources — Who Places Stop Loss Orders on Hyperliquid

**Date:** 2026-05-16  
**Finding:** Systematic audit of all code paths that place SL orders on HL.

---

## SL Placement Sources (ranked by likelihood)

### 1. `brain.py` lines 541-543 — PRIMARY SOURCE (active)

**Every new HL position gets SL + TP placed at entry.**

```python
from hyperliquid_exchange import place_sl as hl_place_sl, place_tp as hl_place_tp
sl_result = hl_place_sl(hype_token, direction, float(stop_loss), float(sz))
tp_result = hl_place_tp(hype_token, direction, float(target), float(sz))
```

Called inside `add_trade()` after `mirror_open()` succeeds and DB INSERT commits.

**SL value:** computed via `compute_atr_sl_price()` from tpsl_utils, stored as `stop_loss` column at entry.

**Trigger:** any successful `mirror_open` → `add_trade` sequence.

---

### 2. `position_manager._execute_atr_bulk_updates()` — DISABLED

```python
# position_manager.py line 89
ATR_HL_ORDERS_ENABLED = False  # Kill switch — SL/TP managed locally by guardian
```

When enabled, this pushes trailing SL updates to HL every pipeline cycle. Currently **disabled** — all SL/TP managed internally via `check_atr_tp_sl_hits()` in position_manager.

---

### 3. `cascade_flip.py` lines 412-415 — DISABLED

```python
from hyperliquid_exchange import place_sl as hl_place_sl, place_tp as hl_place_tp
sl_result = hl_place_sl(hl_token, opposite_dir, sl_val, float(trade_sz))
tp_result = hl_place_tp(hl_token, opposite_dir, tp_val, float(trade_sz))
```

Places SL/TP on the NEW direction after a cascade flip. `CASCADE_FLIP_ENABLED = False` per memory — **disabled**.

---

### 4. `pump_hunter.py` — conditional

Has its own `place_sl()` / `place_tp()` calls. Only fires when pump signals fire. Not a systemic source of random SL losses.

---

### 5. `hl-sync-guardian.py` — NEVER CALLED

Functions exist but are **not invoked** in the main reconciliation loop:
- `_place_or_replace_tp()` (line 3332) — defined but no callers
- `replace_sl()` / `replace_tp()` — imported at line 192 but not used in reconciliation

Guardian reads SL/TP from DB but does not push them to HL.

---

## HL Order Types — What These SL Orders Look Like

```
5/16/2026 - 01:09:09  Stop Market  2Z  Close Short  [Reduce Only]
111  111              Market       Market  Yes  Price above 0.092749  --  Cancel
```

- **Trigger:** "Price above" → SHORT SL (price rises = bad for SHORT, triggers close)
- **Reduce Only:** HL closes the SHORT position, cannot open new long
- **Cancel All:** TP and SL are linked — triggering one cancels the other
- **Order type:** `Stop Market` = trigger order, `isMarket=True` executes as market order

---

## Diagnostic: Which Code Path Placed a Specific Order?

1. **Get HL open trigger orders:**
   ```python
   from hyperliquid_exchange import get_exchange, MAIN_ACCOUNT_ADDRESS
   exchange = get_exchange()
   orders = exchange.info.open_orders(MAIN_ACCOUNT_ADDRESS)
   # Look for oid, coin, triggerPx, tpsl type
   ```

2. **Cross-reference with PostgreSQL trades:**
   ```sql
   SELECT token, direction, entry_price, stop_loss, created_at 
   FROM trades 
   WHERE token IN ('2Z', 'LINEA') 
   ORDER BY created_at DESC LIMIT 5;
   ```

3. **Calculate expected SL from entry:**
   - 2Z entry price × (1 + ATR_SL_MIN_INIT) → compare to 0.092749
   - LINEA entry price × (1 + ATR_SL_MIN_INIT) → compare to 0.00366

4. **Match time:** orders placed at 00:28 (LINEA) and 01:09 (2Z) → check brain.py logs around those timestamps

---

## Key Architecture Points

| Path | Enabled | Effect |
|------|---------|--------|
| `brain.py` SL at entry | YES | Every new HL position gets SL/TP on entry |
| `position_manager` trailing SL | NO (`ATR_HL_ORDERS_ENABLED=False`) | Managed internally, no HL orders |
| `cascade_flip` new-direction SL | NO (`CASCADE_FLIP_ENABLED=False`) | Disabled |
| `hl-sync-guardian` TP/SL sync | NO | Guardian reads DB, doesn't push to HL |
| `pump_hunter` SL | Conditional | Only on pump signals |

**Conclusion:** SL orders on HL come from `brain.py` at entry. If SL is being placed and causing losses, the issue is either:
1. SL placed too wide (ATR params)
2. SL placed at wrong price for direction (bug in `stop_loss` computation at entry)
3. Position不应该 have been opened (signal quality issue)