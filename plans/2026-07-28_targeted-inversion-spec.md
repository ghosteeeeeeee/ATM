# Spec: Targeted Signal Inversion Gate

**Date:** 2026-07-28
**Status:** READY TO IMPLEMENT
**File:** `decider_run.py`, `hermes_constants.py`

---

## Problem

With 29% WR, certain signal sources are **consistently wrong** — they lose more often than random chance. The system has 143 trades from `inv-accel-300` LONG signals with only 29% WR. If those signals had been inverted to SHORT, the WR would have been ~71%.

### Signal Performance Data (200 trades)

| Signal | Trades | WR | Total PnL | Verdict |
|--------|--------|-----|-----------|---------|
| `accel-300-` SHORT | 16 | **62%** | **+2.25%** | KEEP — best signal |
| `inv-accel-300+` LONG | 77 | 29% | **-3.59%** | **INVERT** |
| `inv-accel-300-` SHORT | 66 | 23% | **-6.17%** | **INVERT** |
| `accel-300+` LONG | 9 | 22% | **-1.53%** | **INVERT** |
| `sqx+` LONG | 7 | 0% | **-2.23%** | DISABLED (already off) |

### Why Full Inversion Doesn't Work

There's an existing `_FLIP_SIGNALS = False` in `decider_run.py:42`. It was tested — WR dropped to **13.8%** (worse). Full inversion flips R:R too:

| Metric | Current | If All Inverted |
|--------|---------|-----------------|
| WR | 29% | ~71% (theoretical) |
| Avg Win | +0.49% | becomes -0.49% |
| Avg Loss | -0.29% | becomes +0.29% |
| R:R | 1.68x | **0.59x** (inverted) |
| Profit Factor | 0.58 | 0.58 (unchanged) |

Inverting good signals (`accel-300-` at 62% WR) would destroy the only profitable signal.

### Why Targeted Inversion Works

Only invert signals that are **statistically proven losers** (>=5 trades, <35% WR). Keep signals that work (`accel-300-` at 62% WR). This preserves the good R:R while fixing the bad entries.

---

## Solution

Add a per-signal inversion dict to `hermes_constants.py`. Before each trade execution in `decider_run.py`, check if the signal source is in the inversion dict and flip direction.

---

## Implementation Details

### 1. New Constants in `hermes_constants.py`

```python
# ── Targeted Signal Inversion ──────────────────────────────────────────────────
# Invert direction for specific signals that are statistically proven losers.
# Each entry: source_prefix → True (always invert) or a callable (conditional).
# Does NOT affect signals not in this dict.
#
# Data basis: 200 closed trades, 2026-07-28 analysis.
# inv-accel-300+ LONG: 29% WR, -3.59% total → flip to SHORT
# inv-accel-300- SHORT: 23% WR, -6.17% total → flip to LONG
# accel-300+ LONG: 22% WR, -1.53% total → flip to SHORT
#
# CONCERN: Inverting inv-accel-300- (SHORT→LONG) means we'd be going LONG on
# a signal that fires when price is BELOW EMA300 and falling. That's catching
# a falling knife. Only do this if the data supports it — the 23% WR suggests
# the SHORT direction is wrong, but LONG might not be right either.
# RECOMMENDATION: Start with inv-accel-300+ and accel-300+ only. Monitor.
SIGNAL_INVERSION_ENABLED = True   # Master toggle

SIGNAL_INVERSION_MAP = {
    # source_prefix: True = always invert
    'inv-accel-300+': True,    # 77 trades, 29% WR → flip LONG→SHORT
    'accel-300+':     True,    # 9 trades, 22% WR → flip LONG→SHORT
    # DO NOT invert these:
    # 'accel-300-':   False,   # 16 trades, 62% WR — KEEP, this is our best signal
    # 'sqx+':         False,   # Already disabled via SQUEEZE_CROSS_ENABLED=False
    # 'sqx-':         False,   # 10 trades, 40% WR — borderline, don't invert yet
}
```

### 2. Changes to `decider_run.py`

Replace the existing `_FLIP_SIGNALS` block (line 1990-1996) with targeted inversion:

```python
# ── Targeted Signal Inversion ─────────────────────────────────────────
# Invert direction for specific signals that are statistically proven losers.
# Replaces the old _FLIP_SIGNALS global flip (WR 13.8% — worse).
flipped_direction = None
if SIGNAL_INVERSION_ENABLED:
    for prefix, should_invert in SIGNAL_INVERSION_MAP.items():
        if should_invert and source and source.startswith(prefix):
            flipped_direction = 'SHORT' if direction == 'LONG' else 'LONG'
            log(f'  [INVERT] {token} {source}: {direction} → {flipped_direction} (WR<35% signal)')
            direction = flipped_direction
            break
elif _FLIP_SIGNALS:
    # Legacy global flip (disabled)
    flipped_direction = 'SHORT' if direction == 'LONG' else 'LONG'
    log(f'  [FLIP] {token} {direction} → {flipped_direction} (legacy)')
    direction = flipped_direction
```

Also apply to delayed entries (line 488-491):

```python
# ── Targeted Inversion for delayed entries ──────────────────────────
if SIGNAL_INVERSION_ENABLED:
    for prefix, should_invert in SIGNAL_INVERSION_MAP.items():
        if should_invert and source and source.startswith(prefix):
            direction = 'SHORT' if direction == 'LONG' else 'LONG'
            entry['direction'] = direction
            break
elif _FLIP_SIGNALS:
    direction = 'SHORT' if direction == 'LONG' else 'LONG'
    entry['direction'] = direction
```

### 3. Import in `decider_run.py`

Add to imports at top of file:

```python
from hermes_constants import (
    # ... existing imports ...
    SIGNAL_INVERSION_ENABLED,
    SIGNAL_INVERSION_MAP,
)
```

### 4. Source Matching Logic

The `source` field in hotset.json looks like:
- `inv-accel-300+` (standalone)
- `inv-accel-300+,tl_break_long` (combo)
- `accel-300+` (standalone)
- `accel-300-,sqx-28,tl_break_short` (combo)

The matching uses `source.startswith(prefix)`:
- `'inv-accel-300+'.startswith('inv-accel-300+')` → True ✓
- `'inv-accel-300+,tl_break_long'.startswith('inv-accel-300+')` → True ✓
- `'accel-300-,sqx-28'.startswith('accel-300+')` → False ✓ (doesn't match accel-300-)

This correctly handles both standalone and combo signals.

### 5. Logging and Audit Trail

Every inversion is logged with:
- Token, original direction, flipped direction, source, reason

The `flipped` parameter is already passed to `execute_trade()`:
```python
success, msg = execute_trade(
    ...,
    flipped=bool(flipped_direction),
    ...
)
```

The `flipped` flag is stored in the trade record for post-analysis.

---

## Data Flow

```
hotset.json entry
    ↓
source = "inv-accel-300+" or "inv-accel-300+,tl_break_long"
direction = "LONG"
    ↓
SIGNAL_INVERSION_MAP check:
  'inv-accel-300+' in source? → YES
  should_invert = True
    ↓
direction flipped: LONG → SHORT
    ↓
execute_trade(token, direction="SHORT", ..., flipped=True)
    ↓
Trade placed as SHORT instead of LONG
```

---

## Config Toggles

| Constant | Default | Purpose |
|----------|---------|---------|
| `SIGNAL_INVERSION_ENABLED` | `True` | Master toggle |
| `SIGNAL_INVERSION_MAP` | `{'inv-accel-300+': True, 'accel-300+': True}` | Which signals to invert |
| `_FLIP_SIGNALS` | `False` | Legacy global flip (kept for reference) |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Inversion makes things worse | Set `SIGNAL_INVERSION_ENABLED = False` instantly |
| Inverted signal also loses | Monitor — if inverted WR < 40%, remove from map |
| Combo signals miscounted | `startswith()` handles combos correctly |
| Backtest doesn't match live | Source format may differ — verify with `hotset.json` |
| `accel-300-` accidentally inverted | `accel-300-` doesn't start with `accel-300+` — safe |

---

## Expected Impact

| Scenario | WR | PnL Impact |
|----------|-----|------------|
| Current (no inversion) | 29% | -$0.81 |
| Invert `inv-accel-300+` only | 35-40% | +$2-4 |
| Invert `inv-accel-300+` + `accel-300+` | 38-42% | +$3-5 |
| If inverted signals also lose (worst case) | 25-28% | -$2-3 |

**Conservative estimate**: 29% → 38% WR (+9% improvement)

---

## Testing Plan

1. **Dry run first**: Set `SIGNAL_INVERSION_ENABLED = True` but log only (don't execute). Run 24h. Check what would have been inverted.
2. **Paper mode**: Enable inversion in paper mode. Compare paper WR to live WR.
3. **A/B test**: Run inversion ON for 48h, compare to previous 48h baseline.
4. **Monitor inverted trades**: Track WR of inverted trades separately. If < 40%, the inversion isn't working.

---

## Open Questions

1. **Should we also invert `inv-accel-300-` SHORT (23% WR, -6.17%)?**
   - Pro: Lowest WR of any signal with meaningful volume
   - Con: Inverting SHORT→LONG means catching falling knives (price below EMA300)
   - Recommendation: Start WITHOUT this. The -6.17% is the biggest drag, but inversion may not fix it.

2. **Should combo signals be inverted?**
   - `inv-accel-300+,tl_break_long` has 25% WR — should it be inverted?
   - Current logic: YES (starts with `inv-accel-300+`)
   - Alternative: Only invert standalone signals, not combos
   - Recommendation: Invert combos too — the prefix match handles this correctly.

3. **Minimum trade count for inversion?**
   - `accel-300+` has only 9 trades — is that enough data?
   - Recommendation: Keep at 5+ trades (current threshold). 9 is enough for 22% WR.
