# SHORT Wrong-Side Check — Inverted Comparison (2026-05-18)

## Bug

TPSL trailing gate patch (2026-05-18) applied a WRONG-SIDE check to force-write SL when the stored SL is on the loss side of current price. The SHORT comparison was INVERTED.

## Root Cause

**For SHORT trades:**
- In loss: `current_price < entry_price` → price went UP against the SHORT
- SL must be ABOVE current price to protect: `SL > current_price` (numerically higher)
- Wrong-side condition: `current_sl > current_price` → SL is numerically above current → in loss territory
- **PATCH USED**: `current_sl < current_price` ← OPPOSITE → never fires for losing SHORTs

**For LONG trades:**
- In loss: `current_price < entry_price` → price went DOWN against the LONG
- SL must be BELOW current price to protect: `SL < current_price` (numerically lower)
- Wrong-side condition: `current_sl < current_price` → SL is numerically below current → in loss territory
- **PATCH USED**: `current_sl < current_price` ← CORRECT

## Worked Example — SKY SHORT

```
entry        = 0.068845
current      = 0.069600 (price rose = losing for SHORT)
lowest_price = 0.068697
get_trade_params SL (fallback) = 0.070700 = current * 1.015
TPSL SL (correct) = lowest * 1.007 = 0.069178

current_sl = 0.070700, current_price = 0.069600
Correct wrong_side check: current_sl(0.070700) > current_price(0.069600) = TRUE → force write
Patched wrong_side check: current_sl(0.070700) < current_price(0.069600) = FALSE → blocked
```

## Fix

In `tpsl_utils.py` trailing gate (around line 430):

```python
# WRONG (applied 2026-05-18):
current_on_wrong_side = (current_sl < current_price) if current_price > 0 else False

# CORRECT:
current_on_wrong_side = (current_sl > current_price) if current_price > 0 else False
```

For SHORT: `current_sl > current_price` means SL is numerically above current price — in loss territory for SHORT.

## Diagnostic

```python
# SKY SHORT trace
current_sl = 0.070700
current    = 0.069600
direction  = 'SHORT'

# WRONG check (what was patched):
current_on_wrong_side = (current_sl < current_price)
# = (0.070700 < 0.069600) = False  ← never triggers

# CORRECT check:
current_on_wrong_side = (current_sl > current_price)
# = (0.070700 > 0.069600) = True   ← triggers force-write
```

## Pattern

| Direction | Loss Zone | Wrong-Side Condition | Patched (Wrong) | Correct |
|-----------|-----------|---------------------|-----------------|---------|
| SHORT | `current_price > entry` (price rose) | `SL > current_price` | `SL < current_price` | `SL > current_price` |
| LONG | `current_price < entry` (price fell) | `SL < current_price` | `SL < current_price` ✓ | `SL < current_price` ✓ |

## Impact

Without correct wrong-side force-write, the trailing gate blocks ALL updates when:
- SHORT: `current_sl > current_price` (loss zone) AND `new_sl < current_sl` (would tighten)
- LONG: `current_sl < current_price` (loss zone) AND `new_sl > current_sl` (would tighten)

For established trades where `get_trade_params()` pre-wrote a fallback SL at entry that happens to be in the loss zone, the TPSL engine can never overwrite it — the position is permanently stuck with the wrong baseline.

## Related

- Pattern 11b (`references/persist-debug-2026-05-18.md`): `_persist_atr_levels()` not writing to DB for SHORT trades — the trailing gate blocks `needs_sl=True` for SKY/UNI/XMR
- Pattern 8 (`references/trailing-gate-needs-sl-debug-2026-05-17.md`): generic trailing gate blocking valid tighten
