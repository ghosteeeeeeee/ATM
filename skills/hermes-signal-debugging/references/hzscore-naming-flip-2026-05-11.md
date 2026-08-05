# hzscore+ / hzscore- Naming Fix (2026-05-11)

## What Was Wrong

The `hzscore.py` source label was inverted from the actual signal direction:
- `hzscore+` → fired SHORT
- `hzscore-` → fired LONG

This is backwards from standard convention where `+` typically means Long and `-` means Short.

## The Fix

**File:** `/root/.hermes/scripts/signals/hzscore.py`, line 118

**Before:**
```python
hz_dir_char = '-' if local_dir == 'LONG' else '+'
```

**After:**
```python
hz_dir_char = '+' if local_dir == 'LONG' else '-'
```

**Also updated the docstring (line 10):**
```python
# Before: hz_dir_char: '-' for LONG, '+' for SHORT.
# After:  hz_dir_char: '+' for LONG, '-' for SHORT.
```

## Result After Fix

| local_dir | hz_dir_char | source label | Action |
|-----------|-------------|--------------|--------|
| LONG | `+` | `hzscore+` | fires LONG ✓ (label matches action) |
| SHORT | `-` | `hzscore-` | fires SHORT ✓ (label matches action) |

## Important: Actual Logic Was NOT Changed

The fix only changed the **source label** written to the DB (`source='hzscore+'` vs `'hzscore-'`). The **signal action** (which direction fires for a given z-score) was not changed.

- z > 0 (price above mean) → still fires **SHORT**
- z < 0 (price below mean) → still fires **LONG**

Old trades in trades.json will still show the old inverted labels (e.g., a trade with `signal=hzscore+` that was SHORT was created before the fix). New signals will have correct labels.

## T's Exact Request

> "previously hzscore+ was short, I want hzscore- to be short now and hzscore+ to be for long"

T meant: "I want hzscore- to be SHORT and hzscore+ to be LONG" — he wanted the naming to match convention. The fix achieves this.

## If T Actually Wants Logic Flipped (Action, Not Label)

If T means he wants `hzscore+` to fire LONG and `hzscore-` to fire SHORT (the actual signal direction swapped), change lines 102-104:

```python
# Current (z > 0 = SHORT, z < 0 = LONG):
local_dir = 'SHORT' if bullish_tfs >= 2 else ('LONG' if bearish_tfs >= 2 else None)

# To flip: z > 0 = LONG, z < 0 = SHORT:
local_dir = 'LONG' if bullish_tfs >= 2 else ('SHORT' if bearish_tfs >= 2 else None)
```

## Verification

```bash
grep "hz_dir_char" /root/.hermes/scripts/signals/hzscore.py
# Should show: hz_dir_char = '+' if local_dir == 'LONG' else '-'
```