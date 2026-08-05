# PnL Sync Implementation (2026-05-18)

## What Was Fixed

5 bugs + 2 audit catches across 12 files. Full plan at `/root/.hermes/plans/pnl-sync-plan.md`.

## The Core Problem

HL position size ≈ $7–$10 (7% of withdrawable). DB `amount_usdt` defaulted to $50 everywhere. PnL was 5–7× wrong:

```
WRONG:  pnl_usdt = $50 × leverage × price_change_pct
RIGHT: pnl_usdt = $7  × leverage × price_change_pct  (or whatever HL actually filled)
```

## Solution Architecture

### New column: `hl_notional_usdt` (REAL, nullable)
- Written at trade open via `mirror_open()` return dict
- Read at close for accurate PnL
- `amount_usdt` stays signal-level intent (backward compat for all existing queries/displays)

### `calc_notional` pattern (used everywhere)
```python
calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt
```
Actual HL notional when available; falls back to signal-level $50.

### PnL hierarchy at close
| Tier | Source | When used |
|------|--------|-----------|
| 1 | `hype_realized_pnl_usdt / calc_notional × 100` | HL confirmed fills — MOST TRUSTED |
| 2 | `calc_notional × price_change_pct` | No HL fills yet — accurate for actual notional |
| 3 | `amount_usdt × price_change_pct` | Legacy fallback —inflated/deflated |

## Bugs Fixed

| # | File | Line | Bug |
|---|------|------|-----|
| 1 | position_manager.py | 904 | Fee calc used `amount_usdt × leverage` → inflated fees ~7x. Fixed to `calc_notional × leverage`. |
| 2 | hl-sync-guardian.py | 749 | `add_orphan_trade()` INSERT missing `hl_notional_usdt` → orphan trades always fell back to $50. Fixed. |
| 3 | hl-sync-guardian.py | 2666 | `_close_orphan_paper_trade_by_id()` didn't read `hl_notional_usdt`. Fixed. |
| 4 | hl-sync-guardian.py | 1401 | Cascade flip INSERT missing `hl_notional_usdt`. Fixed. |
| 5 | backfill_orphan_hl_prices.py | 147 | Backfill PnL used `amount_usdt` not `calc_notional`. Fixed. |
| 6 | position_manager.py | 1096 | Hardcoded `50` fallback — replaced with `DEFAULT_TRADE_SIZE_USDT` + div/zero guard. |
| 7 | hermes-trades-api.py | 313 | Hardcoded `50.0` fallback — replaced with `DEFAULT_TRADE_SIZE_USDT`. |

## Files Modified

```
hermes_constants.py          — DEFAULT_TRADE_SIZE_USDT, HL_MIN_NOTIONAL_USDT
brain.py                     — add_trade() INSERT hl_notional_usdt; close_trade() PnL hierarchy
position_manager.py          — close_paper_position() PnL hierarchy + fee fix
hl-sync-guardian.py          — orphan INSERT/close, cascade flip INSERT, _execute_mirror_close
hyperliquid_exchange.py      — mirror_open() returns notional_usdt
cascade_flip.py              — 4 hardcoded 50s → DEFAULT_TRADE_SIZE_USDT
hl-paper-sync.py             — 2 hardcoded 50s → DEFAULT_TRADE_SIZE_USDT
close_position.py            — 1 hardcoded 50 → DEFAULT_TRADE_SIZE_USDT
hermes-trades-api.py         — 1 hardcoded 50 → DEFAULT_TRADE_SIZE_USDT + import fix
backfill_hl_pnl.py           — 1 hardcoded 50 → DEFAULT_TRADE_SIZE_USDT
backfill_orphan_hl_prices.py — calc_notional for backfill PnL
```

## Files That Compile Clean (syntax verified)
```
brain.py ✓
position_manager.py ✓
hl-sync-guardian.py ✓
hermes-trades-api.py ✓
backfill_orphan_hl_prices.py ✓
backfill_hl_pnl.py ✓
close_position.py ✓
```

## Audit Findings (from ai-engineer subagent)

- All 3 close paths (brain.py, position_manager.py, hl-sync-guardian.py) correctly SELECT `hl_notional_usdt`
- `calc_notional` pattern correct in all locations
- PnL uses `calc_notional` in all tier branches
- Fee calculation (position_manager.py:907) now uses `calc_notional × leverage` ✓
- Division-by-zero guards in place: `entry_price > 0`, `calc_notional > 0`, `if amt else 0`
- `DEFAULT_TRADE_SIZE_USDT` imported in all modified files
- Variable scoping clean — no premature use of `calc_notional`
- SQL parameterization correct — no injection risk

## Known Limitations

1. **Pre-existing trades** (opened before 2026-05-18): `hl_notional_usdt = NULL`, fall back to $50, PnL inflated. No backfill — user confirmed.
2. **Cascade flip notional**: cascade flip INSERT uses paper trade size × current price as `hl_notional_usdt` (estimated, not actual fill). `place_order()` doesn't return fill details. Separate refactor needed to capture actual fill notional from HL response.
3. **close_position.py** (standalone manual close script): uses `amount_usdt` only — separate fix needed (tracked separately).
4. **Theoretical division-by-zero edge case**: `hl-sync-guardian.py:2561` and `:2682` use `calc_notional` as divisor. If `calc_notional = 0` (both `hl_notional_usdt` and `amount_usdt` NULL/0) AND `DEFAULT_TRADE_SIZE_USDT = 0`, would ZeroDivisionError. Won't happen in practice since `DEFAULT_TRADE_SIZE_USDT = 50.0`.

## Guardian Restart

After code changes, guardian must be restarted:
```
sudo systemctl restart hermes-hl-sync-guardian
```
Confirmed running: PID 1362510, 4min uptime post-restart (2026-05-18 18:51 UTC).