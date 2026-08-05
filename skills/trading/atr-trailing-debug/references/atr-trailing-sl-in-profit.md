---
name: atr-trailing-sl-in-profit
description: ATR trailing SL in-profit fast-lock fix for Hermes position_manager — when a trade moves into profit, use a fixed % trailing stop instead of ATR-based, so the SL trails tight under price.
tags: [trading, atr, trailing-sl, position-manager, hermes]
---

# ATR Trailing SL — In-Profit Fast Lock

## Context
When a trade moves into profit, the ATR-based SL (which uses `k × atr_pct`) is often **larger** than the minimum floor percentage. This means `max(sl_pct, MIN_SL_PCT)` returns `sl_pct` — the floor never binds, and the SL stays wider than intended.

For T's trading philosophy ("first candle against us we're out, book profit fast"), the trailing SL needs to be **tight underneath price** when in profit — not ATR-relative.

## The Gotcha
```python
# WRONG: floor never triggers because sl_pct > MIN_SL_PCT
atr_pct = atr / entry  # e.g., ETH: 3.97/2314 = 0.00172 = 0.172%
sl_pct = k * atr_pct   # = 0.172%
sl_min_pct = 0.0005     # 0.05%
effective_sl_pct = max(sl_pct, sl_min_pct)  # = 0.172% — ATR wins, floor useless!
```

## The Fix
When in profit, use a **fixed percentage trailing stop** that ignores ATR entirely:
```python
if direction == "LONG":
    in_profit = ref_price > entry
    if in_profit:
        effective_sl_pct = 0.0005  # Fixed 0.05% — locks right under price
    else:
        effective_sl_pct = max(sl_pct, 0.002)  # ATR-based with 0.20% floor
    new_sl = round(ref_price * (1 - effective_sl_pct), 8)
```

## Constants (hermes_constants.py)
```python
ATR_SL_MIN_PROFIT = 0.0005  # 0.05% — fixed trailing when in profit
ATR_SL_MIN_ACCEL = 0.002    # 0.20% — protection floor when at/below entry
```

## position_manager.py — import
```python
from hermes_constants import (
    ...
    ATR_SL_MIN_ACCEL, ATR_TP_MIN_ACCEL, ATR_SL_MIN_PROFIT,  # must include ATR_SL_MIN_PROFIT
    ...
)
```

## The Gotcha (Trial & Error)
**Attempt 1 — `max(sl_pct, MIN_SL_PCT)` doesn't help when ATR > floor:**
```python
# ETH: atr_pct = 0.17%, ATR-based sl_pct = 0.17%, floor = 0.20%
# max(0.00172, 0.002) = 0.002 → floor wins → SL = ref × 0.998 (still too wide)
```

**Attempt 2 — `max(0.0005, sl_pct)` still doesn't help:**
```python
# max(0.0005, 0.00172) = 0.00172 → ATR still wins!
# The floor must be used AS the effective_sl_pct, not as a max() argument.
```

**Correct approach — hardcode the in-profit value:**
```python
if in_profit:
    effective_sl_pct = ATR_SL_MIN_PROFIT  # 0.0005 — IGNORES ATR, fixed 0.05%
else:
    effective_sl_pct = max(sl_pct, ATR_SL_MIN_ACCEL)  # ATR-based with 0.20% floor
```

## SHOR T TP Bug — Critical (Discovered 2026-04-25, UNI SHORT #7777)
**`_update_position_sl_tp` uses `entry_price` for SHORT TP instead of `ref_price`.**

In `position_manager.py` `_update_position_sl_tp` (~line 1665):
```python
if direction == "LONG":
    new_tp = round(ref_price * (1 - new_tp_pct), 8)   # ✓ correct — uses current/ref price
elif direction == "SHORT":
    new_tp = round(entry_price * (1 - new_tp_pct), 8)  # ✗ BUG — uses ENTRY, never trails!
```

For SHORT, TP is computed from `entry_price` — it never moves even if price falls. This is the inverse of the LONG problem.

**Impact on UNI SHORT #7777:**
- Entry: $3.2557, current: $3.2572 (SHORT underwater)
- TP computed as: entry × (1 - 0.005) = $3.2394
- Since TP is locked at entry-based price, the trailing TP logic for SHORT is dead code
- TP only moves when `entry_price` changes (never) — so the TP never improves

**Fix:** Change SHORT TP to use `ref_price`:
```python
elif direction == "SHORT":
    new_tp = round(ref_price * (1 - new_tp_pct), 8)  # Same as LONG — use current price
```

## Behavior
| Scenario | SL % | Notes |
|----------|------|-------|
| LONG: price above entry | 0.05% fixed | Locks profit fast, trails under price |
| LONG: price at/below entry | ATR-based (min 0.20%) | Protection mode |
| SHORT: price below entry | 0.05% fixed | Locks profit fast |
| SHORT: price at/above entry | ATR-based (min 0.20%) | Protection mode |
| SHORT: TP update | ✗ entry_price bug | TP locked at entry — never trails |

## Additional Bugs Found (2026-04-26 Session)

**Bug: `continue` at line 2178 blocked peak tracking entirely**
```python
# BEFORE (broken): the `continue` inside `if hl_data:` skipped peak tracking
if hl_data:
    ...
    continue  # ← THIS made the entire peak tracking block unreachable!
    new_high = max(existing_high, cur_price)  # never runs
    new_low = min(existing_low, cur_price)   # never runs

# FIX: move `continue` to the `else` branch
if hl_data:
    ...  # PnL and peak tracking logic
else:
    continue  # no HL data — skip this position
```

**Bug: SHORT lowest_price never updated — `new_low = existing_low`**
```python
# BEFORE (broken): SHORT branch never tracked new lows
if direction == "SHORT":
    new_high = max(existing_high, cur_price)
    new_low = existing_low   # ← BUG: never changes! lowest_price stays at entry forever
elif direction == "LONG":
    new_high = existing_high
    new_low = min(existing_low, cur_price)  # ← LONG correctly tracks new lows

# FIX: SHORT must also use min() to track its profit trough
if direction == "SHORT":
    new_high = max(existing_high, cur_price)
    new_low = min(existing_low, cur_price)  # ← track new lows for SHORT
```

**Bug: Initial SHORT TP uses raw `tp_pct` instead of `effective_tp_pct` (line 1688)**
```python
# Trailing TP path (line 1679) — CORRECT:
tp_at_ref = round(ref_price * (1 - effective_tp_pct), 8)  # floor enforced

# Initial TP path (line 1688) — BUG: uses raw tp_pct, no floor enforcement
new_tp = round(ref_price * (1 - tp_pct), 8)  # ← missing effective_tp_pct!
# For ATOM: tp_pct = 0.0032, effective_tp_pct = 0.0050 (floor binds)
# → initial SHORT TP would be 2.0205 × (1-0.0032) = 2.0140 instead of 2.0104
# FIX: new_tp = round(ref_price * (1 - effective_tp_pct), 8)

# Full trailing SHORT TP block:
if current_tp > 0:
    tp_at_ref = round(ref_price * (1 - effective_tp_pct), 8)
    if tp_at_ref >= current_tp:
        new_tp = current_tp; needs_tp = False   # loosen blocked
    else:
        new_tp = tp_at_ref; needs_tp = True      # tighten accepted
else:
    new_tp = round(ref_price * (1 - effective_tp_pct), 8)  # ← use effective_tp_pct
    needs_tp = True
```

**Hardcoded value to fix: `ATR_UPDATE_THRESHOLD_PCT = 0.0015` at line 79**
Not sourced from `hermes_constants.py`. Only affects HL push gating (not DB persistence), so not critical — but should be moved to constants for consistency.

## ETH Example
- Entry: 2314.0, ATR(14): 3.97 (0.17%)
- ATR-based sl_pct = 0.17% → SL = $3.97 below peak (too wide)
- Fixed 0.05% in profit → SL = $1.16 below peak (tight, locks profit)
- Peak at 2317.80 → SL = 2316.64, profit locked = **$1.32 USDT**
