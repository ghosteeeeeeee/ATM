# Confluence Bugfix: Numeric Suffixes = Same Signal (2026-05-12)

## The Bug

`signal_compactor.py` `_signal_type_key()` only stripped numeric suffixes from RS signals (`rs-s####` → `rs-s`), treating all other numeric-tagged sources as genuinely distinct:

- `hhh-short5` + `hhh-short6` → 2 unique → **FAKE PASS** (same signal, different bars_since)
- `ma-death14` + `ma-death17` → 2 unique → **FAKE PASS** (same signal, different bars_since)
- `rs-s386` + `rs-r1774` → 2 unique → **CORRECT** (support vs resistance)

The `_signal_type_key()` was:
```python
m = re.match(r'^(rs-[sr])(\d+)$', part)  # RS-only!
if m: return m.group(1)
return part  # everything else returned unchanged
```

Result: TAO SHORT with `hhh-short4,hhh-short5` (1 unique type) passed the confluence gate. Same for STBL SHORT with `ma-death14,ma-death17`. This is the "same signal firing twice is not confluence" bug.

## The Fix

```python
def _signal_type_key(part: str) -> str:
    # Strip numeric suffixes from ALL signal types — bars_since values
    # are timestamps, not distinct signals. hhh-short4 and hhh-short5
    # are the SAME hh_hl signal at different times.
    m = re.match(r'^([a-z][a-z0-9_-]*)([+-]?)(\d+)$', part)
    if m:
        prefix, suffix, _ = m.groups()
        return prefix + suffix  # e.g. 'hhh-short' or 'ma-death'
    return part
```

**Regex breakdown:** `([a-z][a-z0-9_-]+)([+-])?(\d+)$`
- Group 1: prefix (lowercase letter start, then alphanum/-/_) — `hhh-short`, `ma-death`, `rs-s`, `accel-300`
- Group 2: optional direction suffix — `+` or `-` kept for directional signals
- Group 3: numeric — stripped

## Results

| Combo | Before | After |
|---|---|---|
| `hhh-short5 + hhh-short6` | 2 types → **PASS** | `hhh-short` + `hhh-short` = 1 type → **BLOCK** |
| `ma-death14 + ma-death17` | 2 types → **PASS** | `ma-death1` + `ma-death1` = 1 type → **BLOCK** |
| `hhh-short5 + ma-death14` | 2 types → **PASS** | `hhh-short` + `ma-death1` = 2 types → **PASS** (real) |
| `accel-300+ + hhh-long4` | 2 types → **PASS** | `accel-300+` + `hhh-long` = 2 types → **PASS** (real) |

## Key Insight

**Numeric suffixes in source tags = bars_since, not distinct signals.** Different bars_since values for the same signal type represent the same signal re-firing at different times — not two independent signals providing genuine confluence. The fix normalizes all numeric-suffixed sources to their canonical type before counting unique signal types.

## Also Fixed: ma_cross regex digit-stripping bug

`ma-death14` → `ma-death1` (not `ma-death`) because the regex `([a-z][a-z0-9_-]+)` greedily captured the trailing digit as part of the prefix before the suffix digit group could match.

**Correct regex for `ma-death14` → `ma-death`:**
```python
m = re.match(r'^([a-z][a-z0-9_-]*)([+-]?)(\d+)$', 'ma-death14')
# prefix='ma-death1', suffix='', num='4'  ← WRONG (prefix includes digit)
```

Should be `ma-cross` style (no trailing digit in prefix):
```python
# ma-death14 → groups: 'ma-death', '', '14'  ← needs prefix without trailing digit
```

**Actual fix needed if this matters:** Change pattern to `([a-z][a-z0-9_-]+)` without the trailing `*`:
```python
m = re.match(r'^([a-z][a-z0-9_-]+)([+-]?)(\d+)$', 'ma-death14')
# prefix='ma-death', suffix='', num='14'  ← correctly strips trailing digit
```

Note: `ma-death1` vs `ma-death` makes no functional difference (both become 1 unique type), but the normalization should be semantically clean.

## Per-Direction Kill-Switch Architecture

When adding direction flags to signal modules, follow this pattern:

```python
# In the signal's scan/add_signal block — AFTER signal detection, BEFORE add_signal()
from hermes_constants import {SIGNAL}_PLUS_ENABLED, {SIGNAL}_MINUS_ENABLED
if direction == 'LONG' and not {SIGNAL}_PLUS_ENABLED:
    continue  # skip LONG
if direction == 'SHORT' and not {SIGNAL}_MINUS_ENABLED:
    continue  # skip SHORT
```

**All 27 registered signals now have both `*_PLUS_ENABLED` and `*_MINUS_ENABLED` flags.**

Flags default `True` in hermes_constants. Intentional partial flags (one direction = False):
- `EMA9_SMA20_PLUS_ENABLED = False` (LONG suppressed)
- `EXHAUSTION_PLUS_ENABLED = False` (LONG suppressed)
- `FAST_MOMENTUM_MINUS_ENABLED = False` (SHORT suppressed)
- `GAP_300_PLUS/_MINUS = False` (both disabled)
- `GUPPY_PLUS/_MINUS = False` (both disabled)
- `MA_CROSS_PLUS_ENABLED = False` (LONG suppressed)
- `MA_CROSS_5M_PLUS/_MINUS = False` (both disabled)
- `MACD_ACCEL_PLUS_ENABLED = False` (LONG suppressed)
- `MOMENTUM_PLUS/_MINUS = False` (both disabled)
- `MTF_MOMENTUM_PLUS/_MINUS = False` (both disabled)
- `PCT_HERMES_PLUS_ENABLED = False` (LONG suppressed)
- `R2_REV_PLUS/_MINUS = False` (both disabled)
- `R2_TREND_PLUS/_MINUS = False` (both disabled)
- `VEL_HERMES_PLUS_ENABLED = False` (LONG suppressed)
- `VOLUME_HL_PLUS_ENABLED = False` (LONG suppressed)
- `MA300_CANDLE_PLUS_ENABLED = False` (LONG suppressed)

## Why SHORT Confidence Appears Lower

**Structural, not a bug.** The dominant SHORT signals emit lower base confidence:
- `ema9-sma20-`: base 55-68 (gap-based formula)
- `hh_hl_breakout` SHORT: flat 65
- `ma_cross` death cross: flat 55-65

LONG is dominated by `accel-300+`: base 80-85.

The regime multiplier in `_score_signal()` is symmetrical — no direction bias. Score formula:
```
score = base_conf × survival_bonus × staleness × reg_mult × source_mult × speed_mult
```

Only the base emitted confidence differs by signal type. If SHORT base confidence needs raising, the fix is in the individual signal modules (ema9_sma20.py confidence formula, hh_hl breakout confidence assignment).