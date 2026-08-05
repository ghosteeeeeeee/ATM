# accel_300 Gap Expansion Fix — 2026-05-14

## Problem

AAVE SHORT signal appeared in hot-set even though price had crossed BACK above EMA. The signal was written when AAVE was below EMA, but by the time the guardian ran, price was above EMA and the SHORT direction was wrong.

Root cause: accel_300 fires when price crosses below EMA and gap is growing. But when price is bouncing right around the EMA (gap near 0%), it can cross back and forth, generating signals that are immediately stale.

**AAVE example:**
- Price crossed below EMA at ~95.7 (gap ≈ 0%)
- Signal wrote SHORT with gap_now ≈ -0.15%
- Price bounced back ABOVE EMA to 96.88 (gap = +0.82%)
- hot-set now has a SHORT signal that's directionally opposite to current price

## Solution: Gap Expansion Check (Condition 4c)

Price must be meaningfully farther from EMA than it was at the cross bar. This ensures the move is a clean trend, not bouncing near EMA.

**Logic added to `detect_accel_300()`** (after condition 4a — gap growth):

```python
# ── Condition 4c: GAP EXPANSION — price must be farther from EMA than at cross ─
if cross_bar is not None and gap_pcts[cross_bar] is not None:
    gap_at_cross = gap_pcts[cross_bar]
    if direction == 'LONG':
        if gap_now < gap_at_cross + MIN_GAP_EXPANSION:
            continue
    else:  # SHORT
        if gap_now > gap_at_cross - MIN_GAP_EXPANSION:
            continue
```

**hermes_constants.py addition:**
```python
ACCEL_300_MIN_GAP_EXPANSION = 0.10  # price must be 0.10%+ farther from EMA than at cross
```

## Implementation Notes

1. **cross_bar** is found by scanning for the bar where price crossed EMA (closes[j] vs ema300[j] direction flip). Already computed earlier in the function (lines 269-280).

2. **Direction-specific MIN_GAP_PCT**: accel_300 now uses `MIN_GAP_PCT_LONG` / `MIN_GAP_PCT_SHORT` from hermes_constants instead of a single local `MIN_GAP_PCT = 0.20`. Imported at top of file.

3. **Confidence formula fix**: Uses `abs(sig['gap_pct'])` with direction-specific `min_gap` to avoid sign issues for SHORT signals.

## Verification

```bash
# AAVE should return None (crossed back above EMA)
python3 -c "
import sys; sys.argv.append('--dry')
from signals import accel_300 as a
prices = a._get_1m_prices('AAVE', 710)
print(a.detect_accel_300(prices, 'AAVE'))
"
# Expected: None

# DOGE should still fire (clean trend, expansion 1.14%)
python3 -c "
import sys; sys.argv.append('--dry')
from signals import accel_300 as a
prices = a._get_1m_prices('DOGE', 710)
print(a.detect_accel_300(prices, 'DOGE'))
"
# Expected: {'direction': 'LONG', ...}
```

## Tokens that PASS the new expansion check (2026-05-14 sample)

| Token | Dir | gap_now | gap_at_cross | expansion |
|-------|-----|---------|--------------|-----------|
| DOGE | LONG | 1.21% | 0.07% | 1.14% |
| SAGA | SHORT | -1.70% | -0.81% | 0.90% |
| ALGO | LONG | 0.90% | 0.13% | 0.77% |
| GOAT | LONG | 0.78% | 0.04% | 0.74% |

Tokens like VVV (no recent cross), AAVE (crossed back), stay blocked.