# SHORT SL Anchor Bug — Losing Position Case
**Date:** 2026-05-18  
**Severity:** Live bug — SHORT SL fires in wrong direction when price moves against position

---

## The Bug

`tpsl_utils.compute_atr_sl_tp()` lines 286-295 and 379-382:

```python
if direction == 'SHORT':
    ref_price = lowest_price if lowest_price > 0 else ...
    new_sl = round(ref_price * (1 + eff_sl_pct), 8)
```

**`lowest_price` is the profit-trailing anchor, not a loss-cutoff anchor.**

When a SHORT is **losing** (price went UP from entry):
- `lowest_price` = the best price we saw = OLD (the profit point, below entry)
- `new_sl = old_lowest * (1 + eff_sl%)` → SL can be BELOW current price
- If price then dips to SL, position stops out even though it was still losing

---

## Worked Example: SNX SHORT

| Parameter | Value |
|-----------|-------|
| Entry | 0.3034 |
| Current (now) | 0.3070 (price went UP = losing) |
| Lowest price (best point) | 0.3033 |
| eff_sl_pct | 0.70% (ACCEL floor) |

**TPSL SL computation:**
```
new_sl = lowest_price * (1 + 0.007)
       = 0.3033 * 1.007
       = 0.305423
```

**Result:** SL = 0.3054 < current = 0.3070

If price falls to 0.3054 (still above entry 0.3034), position is stopped out — even though it was underwater the whole time (current > entry). The stop fires on the rebound, not on further adverse movement.

---

## Why LONG Is Not Affected

For LONG losing (price fell below entry):
- `highest_price` = old peak = above current
- `new_sl = highest_price * (1 - eff_sl%)` = below current = correct

For SHORT losing (price rose above entry):
- `lowest_price` = old trough = below current ← the problem
- `new_sl = lowest_price * (1 + eff_sl%)` = below current = wrong

---

## Correct Behavior

SHORT SL should be:
- **Above current price** when losing (price moved against us)
- **Below entry** when in profit (price moved for us)

When `current_price > entry_price` (SHORT losing):
```
ref_price = current_price  # always above current when losing
new_sl = current_price * (1 + eff_sl_pct)
```

When `current_price < entry_price` (SHORT in profit):
```
ref_price = lowest_price   # trail from the profit point
new_sl = lowest_price * (1 + eff_sl_pct)
```

---

## The Existing Fix (NEW/In-Profit Case)

position_manager.py `_collect_atr_updates()` lines 1647-1654:
```python
if direction == "SHORT":
    if is_new_trade or _in_profit:
        new_sl = round(_entry * (1 + effective_sl_pct), 8)  # anchors to entry
    else:
        new_sl = round(ref_price * (1 + effective_sl_pct), 8)  # trails from lowest
```

This handles NEW trades and in-profit trades (when price fell from entry).

**The gap:** When `_in_profit = False` (price went UP, SHORT is losing), the code falls through to `ref_price = lowest_price` — which is stale and produces SL below current price.

---

## TPSL Engine vs Display Path

Two separate paths for SHORT SL:

| Path | Function | Anchor | Result |
|------|----------|--------|--------|
| TPSL engine | `tpsl_utils.compute_atr_sl_tp()` | `lowest_price` (unconditional) | Below current when losing ✗ |
| Display/fallback | `_dynSL()` position_manager.py:1487 | `current_price` | Above current when losing ✓ |

Display shows `_dynSL` value (correct when losing), TPSL log shows computed value (wrong when losing).

**The `_dynSL` formula is actually correct for losing SHORT:**
```python
result = current_price * (1 + ATR_SL_MIN)  # ATR_SL_MIN = 0.005 (0.5%)
```
For SNX: `0.3070 * 1.005 = 0.308535` ≈ displayed `0.308540` ✓

But `_dynSL` uses a fixed 0.5% (no ATR scaling, no k, no phase), so it's only correct as a fallback — not as a trailing stop.

---

## Fix Required

`tpsl_utils.compute_atr_sl_tp()` SHORT block needs conditional anchor:

```python
if direction == 'SHORT':
    # When losing (price went up): use current_price as anchor
    # When in profit (price fell): use lowest_price as anchor
    if current_price > entry_price:
        sl_ref = current_price   # losing — always above current
    else:
        sl_ref = lowest_price if lowest_price > 0 else current_price  # in profit
    
    new_sl = round(sl_ref * (1 + eff_sl_pct), 8)
    new_tp = round(ref_price * (1 - eff_tp_pct), 8)   # TP still uses ref_price
```

Same issue exists for LONG when `current_price < entry_price` (losing on LONG):
```python
if direction == 'LONG':
    if current_price < entry_price:
        sl_ref = current_price   # losing — always below current
    else:
        sl_ref = highest_price if highest_price > 0 else current_price  # in profit
```

---

## Files Involved

- `/root/.hermes/scripts/tpsl_utils.py` — `compute_atr_sl_tp()` lines 286-295, 379-382
- `/root/.hermes/scripts/position_manager.py` — `_compute_dynamic_sl()` lines 1450-1493 (correct for losing SHORT, but dead code)
- `/root/.hermes/scripts/position_manager.py` — `_collect_atr_updates()` lines 1647-1654 (handles NEW/in-profit only)

## Related

- `references/atr-sl-direction-bug.md` — NEW/in-profit SHORT case (price immediately fell, SL below entry)
- This bug — LOSING SHORT case (price went up, SL below current)