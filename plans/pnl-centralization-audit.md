# PnL Centralization Audit Plan
**Date:** 2026-05-20
**Goal:** Centralize all P&L calculations into a single `pnl_utils.py` module, replacing 6+ scattered inline calculations across live trading scripts.

---

## Problem

P&L calculations were duplicated across 5+ trading scripts with inconsistent formulas:
- Some used leverage multipliers inline (`calc_notional * lev`)
- Some computed leveraged `pnl_pct` (amplified by leverage) instead of raw market return
- `hl-sync-guardian.py` had a bug where `unrealized_pnl == 0` (breakeven) caused the entire price update to be skipped — leaving `current_price` stale for breakeven positions
- `brain.py` fallback path used `calc_notional * lev` which doubled leverage

---

## Changes Made

### 1. Created `/root/.hermes/scripts/pnl_utils.py`

Single source of truth for all P&L math. Exports:

| Function | Purpose |
|----------|---------|
| `compute_live_pnl(entry_price, current_price, direction)` | Direction-aware live PnL % (unleveraged, entry-based). Accepts `Direction` enum or `str` ('LONG'/'SHORT'). |
| `compute_pnl_usdt(pnl_pct, amount_usdt)` | Converts unleveraged PnL % to USDT using notional amount. |
| `compute_close_pnl(entry_price, exit_price, direction, amount_usdt)` | Closed position PnL % + USDT + net (after fees). Fee-inclusive via `notional * 0.00045 * 2`. |
| `compute_hl_pnl_pct(hl_unrealized, position_value)` | Converts Hyperliquid `unrealizedPnl` to unleveraged `pnl_pct`. |
| `apply_pnl_ground_truth(pos, hl_unrealized, hl_entry, hl_size, curr_price)` | Applies HL ground truth to a position dict (updates pnl_pct, pnl_usdt, current_price, peaks). |
| `pnl_sanity_check(pnl_pct, pnl_usdt)` / `zero_suspicious_pnl(pnl_pct, pnl_usdt)` | Guard against bad data. |

**Key convention:** `pnl_pct` is ALWAYS unleveraged (raw market return), never amplified by leverage.

---

### 2. Updated `profit_monster.py`

**File:** `/root/.hermes/scripts/profit_monster.py`

**Change:** `filter_profitable_positions` — replaced hand-rolled LONG/SHORT if/else PnL with `compute_live_pnl`.

```python
# BEFORE (inline LONG/SHORT):
if direction == "LONG":
    live_pnl = ((pos["current_price"] - pos["entry_price"]) / pos["entry_price"]) * 100
else:
    live_pnl = ((pos["entry_price"] - pos["current_price"]) / pos["entry_price"]) * 100

# AFTER:
live_pnl = compute_live_pnl(pos["entry_price"], pos["current_price"], pos["direction"])
```

Also added local import to avoid circular dependency at module load:
```python
from pnl_utils import compute_live_pnl   # local import to avoid circular dependency at module load
```

---

### 3. Updated `hl-sync-guardian.py`

**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

**Change 1 — `sync_pnl_from_hype`:**
- Removed `if unrealized_pnl != 0:` guard. This was a bug — it skipped ALL updates (price + PnL) for breakeven positions, leaving `current_price` stale.
- Now always writes `current_price` and `pnl_pct` regardless of unrealized value.
- Uses `compute_live_pnl(entry_price_hl, curr_price_hl, direction)` for `pnl_pct`.
- Uses HL `unrealizedPnl` directly for `pnl_usdt` (authoritative USDT value).
- Stale trade rotation and cut-loser logic preserved outside the update block.

**Change 2 — `_close_paper_trade_db`:**
- Replaced inline LONG/SHORT PnL with `compute_close_pnl(float(entry_price), exit_price, direction, amount_usdt)`.
- Returns `pnl_pct, pnl_usdt, _` (ignores net since fees already handled in cascade_flip context).

**Import added:**
```python
from pnl_utils import compute_close_pnl
```

---

### 4. Updated `position_manager.py`

**File:** `/root/.hermes/scripts/position_manager.py`

**Change 1 — `refresh_current_prices` (line 2159):**
- Replaced inline LONG/SHORT `pnl_pct` with `compute_live_pnl(_ep, cur_price, direction)`.

**Change 2 — `refresh_current_prices` HL-authoritative path (line 2201):**
- Replaced `unrealized_pnl / position_value * 100` with `compute_hl_pnl_pct(hl_unrealized, position_value)`.

**Change 3 — `check_and_manage_positions` loop (line 2391):**
- Replaced second inline LONG/SHORT PnL with `compute_live_pnl(entry, cur, direction)`.

**Import updated:**
```python
from pnl_utils import compute_live_pnl, compute_hl_pnl_pct, compute_pnl_usdt, compute_close_pnl, Direction
```

---

### 5. Updated `cascade_flip.py`

**File:** `/root/.hermes/scripts/cascade_flip.py`

**Change 1 — `_close_paper_position`:**
- Replaced inline LONG/SHORT + `pnl_usdt_val = round(live_pnl / 100 * amount_usdt, 4)` with:
```python
pnl_pct, pnl_usdt_val, net_pnl = compute_close_pnl(entry_price, current_price, direction, amount_usdt)
```

**Change 2 — `execute_cascade_flip`:**
- Replaced `close_pnl_usdt = round(live_pnl / 100 * old_amount, 4)` with:
```python
close_pnl_usdt = compute_pnl_usdt(live_pnl, old_amount)
```

**Import added:**
```python
from pnl_utils import compute_close_pnl
```

---

### 6. Updated `brain.py`

**File:** `/root/.hermes/scripts/brain.py`

**Change — `close_trade` fallback path:**
- Replaced inline leveraged formula `((exit - entry) * calc_notional * lev / entry)` with:
```python
pnl_pct, hype_pnl_usdt, _ = compute_close_pnl(float(entry_price or 1), float(exit_price), direction, calc_notional)
```
- **Bug fixed:** Old formula used `calc_notional * lev` which doubled leverage (calc_notional already includes leverage). `compute_close_pnl` correctly multiplies unleveraged `pnl_pct` by `calc_notional` only.

**Import added:**
```python
from pnl_utils import compute_close_pnl
```

---

## Key Decisions

1. **`pnl_pct` is always unleveraged** — raw market return `((current - entry) / entry) * 100`, not amplified by leverage. Makes it comparable across all leverage levels and consistent with `_close_paper_trade_db`.

2. **`pnl_usdt` uses `calc_notional`** (actual HL notional when available, else `amount_usdt`) — not `amount_usdt` alone. Matches how HL computes `unrealizedPnl`.

3. **Direction accepts both `Direction` enum and `str`** — `compute_live_pnl` and `compute_close_pnl` accept `Direction | str` to avoid casting errors from DB rows (which return strings like `'LONG'`) and `hl-sync-guardian.py` (which sometimes passes strings).

4. **Breakeven positions still update price** — `sync_pnl_from_hype` now always writes `current_price` and `pnl_pct` even when `unrealized_pnl == 0`. Previously these positions went stale.

5. **`cascade_flip.py` fee handling preserved** — `compute_close_pnl` returns `net_pnl = pnl_usdt_val - fee_total` (includes both entry and exit taker fees `notional * 0.00045 * 2`). The existing cascade_flip code already had fee calculation inline; it now passes through `compute_close_pnl`.

---

## What Was NOT Changed (Correctly Excluded)

| File | Reason |
|------|--------|
| `hyperliquid_exchange.py` | Purely passes through HL's raw `unrealizedPnl` / `closed_pnl` — no computation |
| `hype-paper-sync.py` | Calls `brain.close_trade` which now uses pnl_utils |
| `backtest_*.py` files | Offline analysis, different context |
| `wave_backtest.py` | Research script, not live trading |
| `ai_decider.py:2151` | Distance calculations (not P&L) |
| `breakout_engine.py:323` | Reward percentage (not live trading) |

---

## Verification

All 5 modified files pass `python3 -m py_compile` with zero errors:

```
pnl_utils.py          ✓
position_manager.py  ✓
profit_monster.py     ✓
hl-sync-guardian.py   ✓
cascade_flip.py      ✓
brain.py              ✓
```

Grep scan for remaining inline PnL patterns in live trading scripts: **zero results**.

---

## Files Modified/Created Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `/root/.hermes/scripts/pnl_utils.py` | Created | ~200 |
| `/root/.hermes/scripts/profit_monster.py` | Modified | ~4 |
| `/root/.hermes/scripts/hl-sync-guardian.py` | Modified | ~8 |
| `/root/.hermes/scripts/position_manager.py` | Modified | ~4 |
| `/root/.hermes/scripts/cascade_flip.py` | Modified | ~4 |
| `/root/.hermes/scripts/brain.py` | Modified | ~4 |