# pnl_utils Centralization — 2026-05-20

Created `/root/.hermes/scripts/pnl_utils.py` to centralize all P&L math replacing inline calculations across 5 files.

## Functions

```python
compute_live_pnl(entry_price, current_price, direction)  # → float pnl_pct (unleveraged)
compute_pnl_usdt(pnl_pct, amount_usdt)                   # → float signed USDT
compute_close_pnl(entry, exit, direction, amount_usdt)    # → (pnl_pct, pnl_usdt, net_pnl)
compute_hl_pnl_pct(unrealized_pnl, position_value)        # → float pnl_pct
apply_pnl_ground_truth(row, hl_data)                      # → (pnl_pct, pnl_usdt, hl_pnl_pct)
pnl_sanity_check(pnl_pct)                                 # → bool
zero_suspicious_pnl(pnl_pct, threshold=0.001)             # → float
```

## Direction Type Hint

`compute_live_pnl` accepts `str` (not `Direction` enum) — callers pass `"LONG"`/`"SHORT"` strings. This is intentional flexibility, not a bug.

## Files Updated

| File | Change |
|------|--------|
| `position_manager.py` | `compute_live_pnl` (×3: refresh path, HL-authoritative path, check_and_manage_positions loop) + `compute_hl_pnl_pct` + `compute_close_pnl` |
| `profit_monster.py` | `compute_live_pnl` in `filter_profitable_positions` |
| `hl-sync-guardian.py` | `compute_close_pnl` in `_close_paper_trade_db`, `compute_live_pnl` in `sync_pnl_from_hype`. Fixed stale-price skip on `unrealized_pnl == 0` |
| `cascade_flip.py` | `compute_close_pnl` in `_close_paper_position`, `compute_pnl_usdt` for cascade close |
| `brain.py` | `compute_close_pnl` fallback in `close_trade` (replaces leveraged `calc_notional * lev` formula with unleveraged PnL) |

## Bug Fixed in hl-sync-guardian.py

`sync_pnl_from_hype()` had `if unrealized_pnl != 0:` wrapping the entire PnL + price update block. Breakeven positions (`unrealized_pnl == 0`) had stale `current_price` written to DB for the entire next cycle. Removed the guard — now always writes price + PnL regardless.

## Bug Fixed in brain.py close_trade

When HL has no fill data, the fallback used:
```python
calc_notional * lev  # ← leveraged formula
```
But `compute_close_pnl` returns unleveraged `pnl_pct`. The primary HL branch uses `hype_pnl_usdt / calc_notional * 100` for consistency. Replaced with `compute_close_pnl` and derived `hype_pnl_pct` the same way.

## Files NOT Changed (correctly excluded)

- `hyperliquid_exchange.py` — raw API passthrough, no computation
- `hype-sync.py` — calls `brain.close_trade` which uses pnl_utils
- `backtest_*.py`, `wave_backtest.py` — offline analysis, own P&L math acceptable

## Verification

```bash
python3 -m py_compile pnl_utils.py position_manager.py profit_monster.py hl-sync-guardian.py cascade_flip.py brain.py
# ALL CLEAN
```

After patching, run:
```bash
grep -rn "LONG.*SHORT\|pnl_pct.*=.*current\|entry.*\*.*100" /root/.hermes/scripts/*.py \
  | grep -v __pycache__ | grep -v pnl_utils | grep -v backtest
# should return nothing
```