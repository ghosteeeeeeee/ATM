# PnL Discrepancy: HL vs Local DB (2026-05-18)

## Symptom
Profits appear **inflated**, losses appear **deflated** in local DB vs HL.

## Root Cause
DB `amount_usdt` defaults to **$50** everywhere, but actual HL position size is 7% of withdrawable (~$7-$20 on a ~$100 account). Every PnL formula uses:

```
pnl_usdt = amount_usdt × |pnl_pct| / 100
```

Since `amount_usdt` is inflated 3-7x, all PnL values are wrong proportionally.

**Example — 10% move:**
- HL actual: ~$7 × 10% = **$0.70**
- DB shows: $50 × 10% = **$5.00** (7x inflation)

Losses are *deflated* in the same proportion: need a bigger move to register the same $ amount.

## The 3 PnL Columns (which to trust)

| Column | Set by | Trust |
|--------|--------|-------|
| `pnl_usdt` | Local calc with $50 default | WRONG — use only for legacy/migration |
| `hype_pnl_usdt` | brain.py signal-based calc | WRONG — same $50 problem |
| `hype_realized_pnl_usdt` | Guardian post-HL-fill | CORRECT — HL ground truth |

## Files with Hardcoded `$50` Default

All should be replaced with `DEFAULT_TRADE_SIZE_USDT` from `hermes_constants`:

```
position_manager.py:881         — close_paper_position PnL math
brain.py:597                     — close_trade PnL math
hl-sync-guardian.py:2524,2658,2666 — guardian close
cascade_flip.py:140,275          — flip helpers
hl-paper-sync.py:187,206         — paper sync
hermes-trades-api.py:297         — API returns
close_position.py:71             — close script
backfill_hl_pnl.py:99            — backfill
backfill_orphan_hl_prices.py:143 — backfill
```

## Planned Fix (NOT YET IMPLEMENTED — 2026-05-18)

### Step A — hermes_constants: add 2 constants
```python
DEFAULT_TRADE_SIZE_USDT = 50.0   # local DB signal-level default
HL_MIN_NOTIONAL_USDT     = 10.0  # HL minimum (currently in hyperliquid_exchange.py)
```

### Step B — DB schema: add 1 new column
```sql
ALTER TABLE trades ADD COLUMN hl_notional_usdt REAL;
```
`amount_usdt` stays as signal-level intent (backward compatible). New `hl_notional_usdt` carries actual HL notional for PnL math.

### Step C1 — hyperliquid_exchange.py: enhance `mirror_open()` return
After `mirror_get_entry_fill()`, include:
```python
"total_sz":     entry_info.get("total_sz"),   # actual coin units from HL fills
"notional_usdt": size_usdt,                   # actual USDT size sent to HL
```

### Step C2 — brain.py: write actual HL notional at INSERT
- Read `notional_usdt` from `mirror_open()` result → write to `hl_notional_usdt` column
- `amount_usdt` stays as passed (signal-level, NULL→$50 default)
- `pnl_usdt`/`pnl_pct` still init to 0 at open (filled at close)

### Step C3 — All close functions: PnL hierarchy (priority order)
1. `hype_realized_pnl_usdt` from HL fill polling → use directly
2. `hl_notional_usdt` available → `pnl = hl_notional × price_change_pct`
3. Fall back to `amount_usdt` ($50 constant) — **only for pre-migration legacy trades**

### Step D — Replace all 12 hardcoded `50`/`50.0` with constant import

## What This Preserves (Don't Break)
- `amount_usdt` still = signal-level intent for all existing queries/displays
- Local ATR/SL/TP math uses `stop_loss`/`target` price columns — unaffected
- All existing close paths still work, just with better PnL when HL data available
- Existing open trades fall back gracefully via `amount_usdt`

## Open Decision
Should existing open trades be backfilled with `hl_notional_usdt`? Can query HL fills per open trade's entry time to compute actual notional. **Decision pending from T.**