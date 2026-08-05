# pnl_utils.py — Centralized PnL Module (2026-05-20)

Created `/root/.hermes/scripts/pnl_utils.py` as single source of truth for all PnL math across Hermes trading system.

## Module Location
`/root/.hermes/scripts/pnl_utils.py`

## Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `compute_live_pnl(entry, current, direction)` | Live unleveraged % from entry/current prices | position_manager.py:2158, hl-sync-guardian.py:1488, profit_monster.py |
| `compute_pnl_usdt(pnl_pct, calc_notional)` | % → signed USDT | General |
| `compute_close_pnl(entry, exit, direction, calc_notional)` | Close-time PnL + fee estimation | hl-sync-guardian.py:2523, position_manager.py:926 |
| `compute_hl_pnl_pct(unrealized_pnl, position_value)` | From HL unrealized + position value | position_manager.py:2201 |
| `apply_pnl_ground_truth(...)` | Use HL realized when available | Guardian close path |
| `pnl_sanity_check(...)` / `zero_suspicious_pnl(...)` | Corruption guard | All write paths |

**Direction type:** `str` (accepts `'LONG'` / `'SHORT'`, not `Literal` — call sites pass string vars)

**calc_notional rule:** `hl_notional_usdt if is not None else amount_usdt` — 0.0 is falsy, must use explicit `is not None`

## Bug Fixed: `unrealized_pnl != 0` Guard

**File:** `hl-sync-guardian.py` `sync_pnl_from_hype()` (line ~1475)

**Problem:** `if unrealized_pnl != 0:` skipped ALL updates (including `current_price`) for breakeven positions. Breakeven positions had stale `current_price` for the entire session.

**Fix:** Removed guard — PnL update now unconditional. `pnl_usdt` from HL's `unrealized_pnl` is already 0 at breakeven, so the guard added no value.

**Pattern:** Always update `current_price` regardless of PnL being zero.

## Files Updated to Use pnl_utils

| File | Sites Updated |
|------|---------------|
| `hl-sync-guardian.py` | `sync_pnl_from_hype()` (1475, 1488), `_close_paper_trade_db()` (2523) |
| `position_manager.py` | `refresh_current_prices()` no-HL branch (2158), HL branch (2201) |
| `profit_monster.py` | `filter_profitiable_positions()` — local import inside function |

## Local Import Pattern (profit_monster.py)

To avoid circular dependency at module load, profit_monster.py uses local import inside `filter_profitiable_positions()`:
```python
from pnl_utils import compute_live_pnl
```
Not a module-level import.

## Key PnL Formula

All PnL is "unleveraged" = raw market return %:
```python
if direction == 'LONG':
    pnl_pct = ((current - entry) / entry) * 100
else:
    pnl_pct = ((entry - current) / entry) * 100
pnl_usdt = pnl_pct/100 * calc_notional  # signed: + profit, - loss
```

HL `hype_pnl_usdt` (from fills) is ground truth — used at close, not stored on open positions.