# accel-300 Condition 2 Bug: abs(gap) Stripped Sign for SHORT

## Date: 2026-05-14

## The Bug

**File:** `/root/.hermes/scripts/signals/accel_300.py`, line 222-224 (Condition 2)

**Symptom:** CHIP:SHORT fires when price is ABOVE EMA300. CHIP at bar 374: gap_now=+0.2486% (positive = above EMA), but accel_300 fires SHORT anyway. Price was +0.25% above EMA — not a SHORT setup — yet signal fired and closed at loss twice within 3 minutes.

**Root Cause:** `abs(gap_now)` strips the sign, making positive gaps pass Condition 2 for SHORT signals.

```python
# BEFORE (BUG — abs strips sign):
if abs(gap_now) < min_gap:
    # For CHIP: abs(+0.2486) = 0.2486 >= 0.20 → passes → fires SHORT
    # But CHIP was ABOVE EMA — shouldn't SHORT
    continue
```

**Why it passed silently:** In a bear market, most coins are below EMA. So `abs()` rarely caused false SHORTs — the sign happened to be negative for almost all coins. CHIP was a rare above-EMA case where `abs()` created a false signal.

## The Fix

Replace `abs()` with direction-specific signed comparison:

```python
# AFTER (SIGNED — direction-aware):
if direction == 'LONG':
    # gap_now positive = above EMA, too small = reject
    if gap_now < min_gap:
        continue
elif direction == 'SHORT':
    # gap_now must be negative = below EMA to be SHORT-eligible
    # positive gap (above EMA) correctly rejects: 0.25 > -0.20 = False → pass through
    if gap_now > -min_gap:
        continue
```

For CHIP: `gap_now=+0.2486`, `direction='SHORT'`, `min_gap=0.20` → `0.2486 > -0.20` = True → **rejected** ✓

## History — Why abs() Was Added (2026-05-13)

An earlier bug caused ALL SHORT signals to be rejected (`gap_now < MIN_GAP_PCT` with negative gap always `True`). The fix added `abs()` to require magnitude >= 0.20 regardless of sign. This correctly fixed the original problem but introduced the new bug: positive gaps now pass for SHORT.

**Timeline:**
- 2026-05-13: Added `abs()` to fix "all SHORTs rejected" → SHORT signals started firing
- 2026-05-14: Found CHIP fires incorrectly with positive gap → removed `abs()`, added signed checks

## Verification

```python
# CHIP before fix: fires SHORT (wrong)
# CHIP after fix: returns None (correct)

# UNITS of CHIP gap (below EMA, should SHORT):
# gap_now=-0.25%, direction='SHORT', min_gap=0.20
# -0.25 > -0.20 = False → passes Condition 2 → fires SHORT ✓
```

## Key Lesson

**abs() is wrong for bidirectional signals where direction implies sign.** Use explicit signed comparison:
- LONG: `gap_now < min_gap` (positive but too small = reject)
- SHORT: `gap_now > -min_gap` (positive = above EMA = reject for SHORT)

abs() is appropriate for magnitude-only checks (e.g., ATR thresholds, volatility filters) — not for directional gap checks where the sign carries semantic meaning.

## Related

- `references/accel-300-timing-fix-2026-05-10.md` — earlier accel-300 fixes
- `references/instant-reopen-cooldown-gap-2026-05-14.md` — CHIP/LAYER instant reopen root cause
- `references/last-30-losers-2026-05-13.md` — accel-300 trade analysis (23.3% winrate, abs bug contributed)