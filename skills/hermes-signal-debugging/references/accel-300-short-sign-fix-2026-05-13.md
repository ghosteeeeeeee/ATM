# accel-300 SIGN BUG + PATCH ACCIDENT — 2026-05-13

## Bug: SHORT gap_growth Formula Inverted

**File:** `/root/.hermes/scripts/signals/accel_300.py`, line 249

### The Problem

For SHORT signals, `gap_pct` is **negative** (price below EMA). The code used the same formula for both directions:

```python
avg_gap_growth = gap_now - gap_then  # WRONG for SHORT
```

For SHORT, this produces **backwards logic**:
- Price **accelerating down** (more below EMA): `gap_now=-0.369`, `gap_then=-0.280` → growth = `-0.089` → **REJECTED**
- Price **bouncing up** (less below EMA): `gap_now=-0.280`, `gap_then=-0.369` → growth = `+0.089` → **FIRED**

So the old code fired on bounces and rejected genuine accelerations — **exactly backwards for SHORT**.

### Real Examples from May 12 signals.log

| Token | gap_now | gap_then (implied) | Old growth | Old fires? | Actual price action |
|-------|---------|-------------------|-----------|-----------|-------------------|
| FIL SHORT | -0.280% | -0.369% | +0.089% | ✓ FIRE | Bounced from -0.369% to -0.280% — recovering, not falling |
| ATOM SHORT | -0.716% | -0.803% | +0.087% | ✓ FIRE | Bounced from -0.803% to -0.716% — recovering |
| ZK SHORT | -0.207% | -0.276% | +0.069% | ✓ FIRE | Bounce, trade lost -0.43% |

### The Fix

```python
# CORRECTED — sign-flip for SHORT direction
if direction == 'LONG':
    avg_gap_growth = gap_now - gap_then  # gap growing = accelerating up
else:
    avg_gap_growth = gap_then - gap_now  # flip for SHORT: gap becoming MORE negative = accelerating down
```

For SHORT, `gap_then - gap_now` gives:
- **Positive** when price falls further below EMA (accelerating down = correct signal)
- **Negative** when price bounces toward EMA (recovering = correctly rejected)

### Lines 298-301 Are CORRECT — Do NOT Change

The marginal acceleration check for bars > 3:

```python
delta_last  = gap_pcts[i] - gap_pcts[gap_1_idx]
delta_prev  = gap_pcts[gap_1_idx] - gap_pcts[gap_2_idx]
if direction == 'LONG' and delta_last <= delta_prev: continue  # reject decelerating LONG
if direction == 'SHORT' and delta_last >= delta_prev: continue  # reject decelerating SHORT
```

This is **correct**:
- SHORT bouncing (delta_last = +0.060, delta_prev = +0.040): `0.060 >= 0.040` → `True` → **correctly rejected**
- SHORT accelerating down (delta_last = -0.089, delta_prev = -0.060): `-0.089 >= -0.060` → `False` → **correctly fires**
- LONG decelerating (delta_last = +0.040, delta_prev = +0.060): `0.040 <= 0.060` → `True` → **correctly rejected**
- LONG accelerating (delta_last = +0.060, delta_prev = +0.040): `0.060 <= 0.040` → `False` → **correctly fires**

The prior reference `accel-300-marginal-acceleration-bug-2026-05-13.md` incorrectly claimed this was inverted. It is NOT inverted.

---

## Patch Accident: Deleted gap_then Assignment

**File:** `/root/.hermes/scripts/signals/accel_300.py`

When applying the sign-fix patch, the `gap_then = gap_pcts[gap_then_idx]` assignment was accidentally deleted from the code, causing:

```
NameError: name 'gap_then' is not defined
```

This crashed `detect_accel_300()` for ALL tokens, producing **zero signals** after the fix — appearing as if the fix broke the signal system entirely.

### The Lesson

When inserting an if/else block around a variable that was previously assigned inline (above or below the block), **always explicitly restore the assignment statement inside each branch or before the branches**. The refactoring accidentally consumed the standalone assignment line.

### Correct Patch Structure

```python
gap_then_idx = i - PERSISTENCE_BARS
if gap_then_idx < 0 or gap_pcts[gap_then_idx] is None:
    continue

gap_then = gap_pcts[gap_then_idx]  # ← MUST be before the if/else
if direction == 'LONG':
    avg_gap_growth = gap_now - gap_then
else:
    avg_gap_growth = gap_then - gap_now  # flip for SHORT
```

---

## Verification After Fix

```bash
cd /root/.hermes/scripts && python3 -c "
import sqlite3, sys
sys.path.insert(0, '.')
from signals.accel_300 import detect_accel_300, _get_1m_prices

for token in ['SKY', 'ZEN', 'SUI', 'NEAR', 'FIL', 'FET', 'ZK', 'AVAX']:
    prices = _get_1m_prices(token, lookback=700)
    if not prices:
        print(f'{token}: no data')
        continue
    sig = detect_accel_300(token, prices)
    if sig:
        print(f'{token}: SIGNAL -> {sig[\"direction\"]} gap={sig[\"gap_pct\"]:.3f}% growth={sig[\"gap_growth\"]:.3f}% bars={sig[\"bars_since_cross\"]}')
    else:
        print(f'{token}: no signal')
"
```

Expected output (signals now firing correctly):
```
SKY: SIGNAL -> SHORT gap=-0.335% growth=0.158% bars=9
NEAR: SIGNAL -> SHORT gap=-0.317% growth=0.291% bars=2
FET: SIGNAL -> LONG gap=0.253% growth=0.117% bars=6
AVAX: SIGNAL -> SHORT gap=-0.275% growth=0.128% bars=2
```

---

## Related Files

- `signals/accel_300.py` line 249 (sign fix) and lines 298-301 (marginal acceleration — correct)
- `references/accel-300-marginal-gap-misfires-2026-05-13.md` — related: MIN_GAP_PCT too low, bars 6-10 late entries
- `references/accel-300-abs-gap-bug.md` — prior bug: abs() missing for SHORT gap check
- `references/last-30-losers-2026-05-13.md` — trade outcomes driven by this bug
