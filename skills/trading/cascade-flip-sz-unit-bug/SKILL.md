---
name: cascade-flip-sz-unit-bug
description: "Cascade flip order fails for dust tokens — sz was dollars not coin quantity. Root cause + 2-bug fix for cascade_flip() in position_manager.py. Min position floor $11 notional (T approved, 2026-04-20)."
tags:
  - hyperliquid
  - cascade-flip
  - position-manager
  - dust-token
  - order-sizing
created: 2026-04-20
---

# Cascade Flip — SZ Unit Bug

## Context
When cascade flip triggers in `position_manager.cascade_flip()`, it must place a market order to open the new position in the opposite direction. A bug caused this order to fail for low-price ("dust") tokens.

## Root Cause: Two Bugs

### Bug 1: sz is coin quantity, not dollar notional (PRIMARY)

**What happened:** `cascade_flip` passed `sz=old_amount` (e.g., $50) to `place_order()`. For a token like MEME at ~$0.0006, this meant 50 COINS = $0.03, below HL's $10 minimum order value.

**The fix:** Convert from dollar notional to coin quantity:
```python
leverage_val = max(1, old_leverage)  # fetched from old trade's leverage column
sz_coins = (old_amount * leverage_val) / current_price if current_price > 0 else old_amount

# HL requires >= $10; enforce minimum with $11 floor (T approved $11, 2026-04-20)
min_order_value = 11.0
min_sz_coins = min_order_value / current_price if current_price > 0 else 0
if sz_coins < min_sz_coins:
    sz_coins = min_sz_coins
```

### Bug 2: ok.get('size') returns None (SECONDARY)

**What happened:** `place_order()` wraps HL's response as `{"success": True, "result": {...}}`. The `ok.get('size')` call in the success block returned `None`, so it fell back to `old_amount` (dollars), corrupting `insert_post_flip_trade`'s `amount_usdt` parameter.

**The fix:** Use `sz_coins` directly since that was the actual quantity sent to HL:
```python
trade_sz = sz_coins  # instead of: ok.get('size') or old_amount
```

## Verification Steps

1. **Schema check** — leverage column must be fetched from the old trade:
   ```sql
   SELECT amount_usdt, leverage FROM trades WHERE id=%s
   ```
   (Column 7 = amount_usdt, Column 30 = leverage in brain DB)

2. **Log verification** — After fix, cascade flip log should show:
   ```
   [CASCADE FLIP] ✅ MEME SHORT entered @ $0.0006...
   [CASCADE FLIP] ✅ Post-flip DB entry created: trade_id=N atr_managed=TRUE
   ```

3. **Before fix**, the error was:
   ```
   [CASCADE FLIP] ⚠️ MEME SHORT entry failed: Order must have minimum value of $10. asset=75
   ```

## Affected Tokens
Any token where `notional_usdt / price < dust_threshold` would fail. MEME ($0.0006), ZETA, ASTER, and similar dust tokens most at risk.

## Files
- `/root/.hermes/scripts/position_manager.py` — `cascade_flip()` function (lines ~2898-3060)
- `place_order()` in `hyperliquid_exchange.py` — wraps HL response as `{"success": True, "result": ...}`
