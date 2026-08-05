# Guardian Orphan PnL Fix — 2026-05-20

## Root Cause Summary

Guardian orphan closes used $50 placeholder for `amount_usdt` and had no `hl_notional_usdt` column — causing ~5x PnL inflation for actual ~$10 HL positions. 7 bugs total across 3 files.

## Bug Map

| # | File | Line | Bug | Fix |
|---|------|------|-----|-----|
| 1 | brain.py | 637 | `calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt` — 0.0 is falsy | `if hl_notional_usdt is not None` |
| 2 | brain.py | 640 | `amount_usdt = float(amount_usdt or DEFAULT_TRADE_SIZE_USDT)` — 0.0 falsy | `if amount_usdt is not None else DEFAULT_TRADE_SIZE_USDT` |
| 3 | position_manager.py | 883 | same 0.0 falsy for `amount_usdt` and `hl_notional_usdt` | explicit `is not None` |
| 4 | position_manager.py | 1096 | same in HL backfill path | explicit `is not None` |
| 5 | hl-sync-guardian.py | 696 | `get_db_open_trades()` pipe parser `parts[5]` falsy | `parts[5] is not None and parts[5] != ""` |
| 6 | hl-sync-guardian.py | 2610,2694,2696 | `_close_orphan_paper_trade_by_id` amount_usdt + calc_notional falsy | `is not None` + `amount_usdt_override` kwarg |
| 7 | hl-sync-guardian.py | 3659-3680 | guardian_orphan INSERT: no `hl_notional_usdt` col, hardcoded 50.0 | add col, compute `abs(sz×entry_px)` |

## Guardian Orphan Close — 4 Call Sites

All 4 call sites to `_close_orphan_paper_trade_by_id` now pass `amount_usdt_override`:

1. **sync() DB-record orphan close** (line ~3637): `sz × entry_px` from `hl_pos.get(coin, {})` → `amount_usdt_override=hl_notional_override`
2. **sync() no-DB-record orphan INSERT+close** (line ~3680): `hl_notional = abs(sz * entry_px_raw)` → both `amount_usdt` and `hl_notional_usdt` VALUES
3. **orphan detection path** (line ~1215): `pos_data` lookup → `_hl_notional = abs(_sz * _ep)` → `amount_usdt_override=_hl_notional`
4. **pending retry** (line ~4093): `amount_usdt_override=None` (no HL data available, uses DB lookup)

## `_close_orphan_paper_trade_by_id` Function Signature Change

```python
# BEFORE
def _close_orphan_paper_trade_by_id(trade_id, token, direction, entry_px, lev, reason):
    amount_usdt = DEFAULT_TRADE_SIZE_USDT  # hardcoded fallback

# AFTER
def _close_orphan_paper_trade_by_id(trade_id, token, direction, entry_px, lev, reason,
                                     amount_usdt_override=None):
    if amount_usdt_override is not None:
        amount_usdt = amount_usdt_override
        _debug_log(f"PnL TIER-2: using HL_notional_override=${amount_usdt_override}")
    else:
        # DB lookup fallback
        amount_usdt = DEFAULT_TRADE_SIZE_USDT
```

## PnL Tiered Hierarchy (close_trade in brain.py)

- **Tier 1**: `hype_realized_pnl_usdt` from HL API (ground truth, guardian-written)
- **Tier 2**: `hl_notional_usdt × price_change_pct` (used when Tier 1 unavailable)
- **Tier 3**: `amount_usdt × price_change_pct` (last resort, inflated ~5x)

Guardian orphan fixes ensure `hl_notional_usdt` is now populated with real HL notional for all new guardian-created trades.

## patch replace_all Warning

Using `replace_all=True` on hl-sync-guardian.py created DUPLICATE CODE BLOCKS at lines 1261 and 3733 — the file became corrupted. 

**Lesson**: Never use `replace_all=True` on large files (>1000 lines). Always do targeted single-location patches. If a patch fails or corrupts, revert with `git checkout -- scripts/hl-sync-guardian.py` and re-apply as separate targeted patches.

## Verified Compile Clean

```
brain.py ✓
hl-sync-guardian.py ✓
decider_run.py ✓
signal_compactor.py ✓
position_manager.py ✓
```
