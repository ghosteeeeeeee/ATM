# Stale Signal Fix — Gap Expansion Check (2026-05-14)

## Trigger

"AAVE SHORT stale in hot-set — price bounced back above EMA"

## Problem

AAVE SHORT signal appeared in hot-set even though price had recrossed ABOVE EMA by execution time. The signal wrote when AAVE was below EMA, but by guardian run time price was back above EMA — wrong direction.

Root cause: accel_300 fires when price crosses below EMA and gap is growing, but when price bounces near EMA (gap near 0%), it can cross back and forth, generating signals that are immediately stale.

## Solution: Gap Expansion Condition 4c

Price must be meaningfully farther from EMA than at the cross bar. Clean trend, not bouncing.

**Logic added to `detect_accel_300()`** (after Condition 4a — gap growth):

```python
# ── Condition 4c: GAP EXPANSION ─────────────────────────────────────────────
if cross_bar is not None and gap_pcts[cross_bar] is not None:
    gap_at_cross = gap_pcts[cross_bar]
    if direction == 'LONG':
        if gap_now < gap_at_cross + MIN_GAP_EXPANSION:
            continue
    else:  # SHORT
        if gap_now > gap_at_cross - MIN_GAP_EXPANSION:
            continue
```

**hermes_constants.py:**
```python
ACCEL_300_MIN_GAP_EXPANSION = 0.10  # price must be 0.10%+ farther from EMA than at cross
```

## Key Implementation Details

1. **cross_bar** — already computed earlier (lines ~269-280), find the bar where price first crossed EMA within the LOOKBACK window
2. **MIN_GAP_PCT** — now uses `MIN_GAP_PCT_LONG` / `MIN_GAP_PCT_SHORT` from hermes_constants (not a local constant)
3. **Confidence formula** — uses `abs(sig['gap_pct'])` with direction-specific min_gap

## Verification

```python
# AAVE returns None (crossed back above EMA)
# DOGE fires with 1.14% expansion (clean trend)
```

## Related

- Bug #14 in new-signal-implementation: Persistence + Gap-Growth Catches Peaks
- references/accel-300-gap-expansion-fix.md (full detail)