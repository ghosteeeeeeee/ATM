# RS Signal — Bounce Threshold Fix (2026-05-09)

## Problem: _BOUNCE_THRESH_ATR=0.20 was unreachable for most tokens

### Root Cause

`_BOUNCE_THRESH_ATR = 0.20` means price must be within `0.20 * ATR(14)` of a level to count as a "touch" for bounce confirmation.

For low-ATR tokens this is impossibly tight:
```
Token    ATR%         Thresh(% of price)   0.15% fallback    Ratio
ADA      0.024%       0.0048%              0.15%             31x tighter
ANIME    0.023%       0.0045%              0.15%             33x tighter
```

For ANIME (price ~$0.005), the bounce threshold was `0.00000023` — price noise is larger. For ADA, it was `0.000013` — also noise-level. Every token showed `bounce=False` because price never got within the threshold of the level across 6 candles.

### The Fix

Raised `_BOUNCE_THRESH_ATR` from `0.20` to `1.00` — 5x more forgiving, still strict:
```python
_BOUNCE_THRESH_ATR = 1.00  # was 0.20
RS_PROXIMITY_K     = 1.00  # was 1.20 (fires closer to level = earlier entry)
RS_MIN_TOUCHES     = 8     # was 5 (stronger structural levels only)
```

### Effect

| Metric | Before | After |
|--------|--------|-------|
| Signals firing | 11 | 8 |
| bounce=True | 0% | BIGTIME first to achieve |
| Signal quality | weak, late | tighter, earlier |

### Lesson

ATR-based thresholds must be validated against low-ATR tokens. A threshold of `0.20 * ATR` that seems reasonable for BTC (ATR ~0.5%) becomes `0.10%` — still workable. For tokens with ATR of `0.024%`, it becomes `0.0048%` — noise. Always compute the absolute threshold value in price terms for a representative low-ATR token before setting an ATR multiplier.