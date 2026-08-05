# accel-300 Short Signal Audit — 2026-05-31

## Session Summary

T asked ai-engineer subagent to audit `accel_300.py` for:
- SHORT signal logic bugs (negative value handling)
- Wrong-bar-index final-verify (Pattern 7)

## Subagent Findings vs Main Session Verification

| Bug | Subagent Claim | Main Session Verdict | Status |
|-----|---------------|---------------------|--------|
| Line 320 SHORT expansion `>` wrong, should be `<` | HIGH | **FALSE POSITIVE** — `>` is correct | REVERTED |
| Lines 326-340 final-verify checks n-2 not i | MEDIUM | **CONFIRMED BUG** — Pattern 7 | PATCHED |

---

## Bug 1: SHORT Expansion Check — FALSE POSITIVE (reverted)

**Subagent claim:** `if gap_now > gap_at_cross - MIN_GAP_EXPANSION` uses wrong operator for SHORT.
Should be `<`.

**Why subagent was wrong:**
- `gap_at_cross` for SHORT is NEGATIVE (e.g., -0.20)
- `MIN_GAP_EXPANSION = 0.10` (positive)
- `threshold = gap_at_cross - MIN_GAP_EXPANSION = -0.30`

The `>` operator correctly means:
- `gap_now=-0.25 > -0.30` → True → **block** (only 0.05% expansion, insufficient) ✓
- `gap_now=-0.35 > -0.30` → False → **pass** (0.15% expansion, sufficient) ✓

With `<` (subagent's proposed fix):
- `gap_now=-0.25 < -0.30` → False → **pass** (weak expansion, wrong) ✗
- `gap_now=-0.35 < -0.30` → True → **block** (strong expansion, wrong) ✗

**Rule:** When subagent claims inequality direction is wrong for a directional signal,
trace the actual sign values through both branches. The subagent did not account for
the negative sign of SHORT gap values when evaluating `>` vs `<`.

**Pattern:** This is a subagent false positive — sign-blind inequality analysis.

---

## Bug 2: Final-Verify Checks Wrong Bar — CONFIRMED (patched)

**Subagent claim:** Lines 326-340 check `len(closes)-2` (newest bar n-2) instead of
detection bar `i` (Pattern 7).

**Confirmed:** Old code blocked valid signals when:
- Signal detected at i=695 (gap growing, valid)
- Bar n-2=698 reversed to gap=-0.02 → signal blocked

**Fix applied:**
```python
# BEFORE:
current_bar_idx = len(closes) - 2
if current_bar_idx != i:
    if direction == 'LONG' and not (closes[current_bar_idx] > ema300[current_bar_idx]):

# AFTER:
if i >= len(closes) - 1:
    continue
if direction == 'LONG' and not (closes[i] > ema300[i]):
```

When `i == n-2`, behavior preserved. When `i < n-2` (signal on older bar), now correctly verifies detection bar.

---

## What Was Verified Correct (no change needed)

| Check | Lines | Value |
|-------|-------|-------|
| SHORT min gap `gap_now > -min_gap` | 228-231 | Correct — `-0.25 > -0.20` is False, passes |
| avg_gap_growth SHORT formula `gap_then - gap_now` | 258-261 | Correct — `-0.15 - (-0.25) = +0.10` (accelerating down) |
| delta comparison for SHORT `delta_last >= delta_prev` | 307-310 | Correct — sign-aware for negative gaps |
| Confidence formula `abs(gap_pct)` threshold | 455-457 | Correct — uses abs() for gap magnitude |

---

## Key Lessons

1. **Subagent's Bug 1 was sign-blind:** claimed `>` was wrong without tracing through
   concrete negative values. The `>` operator correctly blocks weak SHORT expansions.

2. **Always re-verify subagent bug claims with concrete values in main session before
   applying patches.** Particularly for directional signals with negative values.

3. **Bug 2 was real Pattern 7 issue:** fixed correctly, behavior preserved when i=n-2.

## Constants at time of audit

```
MIN_GAP_PCT_LONG = 0.20
MIN_GAP_PCT_SHORT = 0.20
ACCEL_300_MIN_GAP_GROWTH = 0.03
ACCEL_300_MIN_GAP_EXPANSION = 0.10
ACCEL_300_PERSISTENCE_BARS = 3
```