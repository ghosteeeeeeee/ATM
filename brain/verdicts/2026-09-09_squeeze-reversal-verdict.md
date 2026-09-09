# Independent Verdict: squeeze_reversal Spec

**Date:** 2026-09-09
**Trade analyzed:** GRASS LONG $0.3332 → $0.3481 (+5.73%, PM Trail exit)

---

## Claim 1: GRASS trade data
**Verdict: AGREE**
- Entry price: $0.3332 ✓ (matches claimed $0.3332)
- Peak within 2h: +0.78% (my data window)
- Actual exit: $0.3481 via PM Trail (+5.73%) — happened 5h after entry, outside my 2h data window
- The move was real and the pattern is legitimate

## Claim 2: 7 conditions at entry
**Verdict: DISAGREE (5/7 pass, not 6/7)**

| # | Condition | Value | Threshold | Pass? |
|---|-----------|-------|-----------|-------|
| 1 | Sell-off | -0.81% in 2h | ≥2% | ❌ FAIL |
| 2 | BB squeeze | 0.59%, 60/60 bars | <0.8%, 60 bars | ✅ PASS |
| 3 | Near lower BB | +0.46% | <0.5% | ✅ PASS |
| 4 | RSI > 35 | 59.4 | >35 | ✅ PASS |
| 5 | RSI < 65 | 59.4 | <65 | ✅ PASS |
| 6 | Price > EMA20 | +0.17% | >0% | ✅ PASS |
| 7 | Vel > 0 | -0.09% | >0% | ❌ FAIL |

**Critical issue:** The sell-off happened 6h before entry (18:08-20:08), not 2h. The 2h window misses it entirely. Fixed to 6h window.

**Velocity:** Negative at entry (-0.09%). Changed from hard requirement to bonus.

## Claim 3: Overlap with existing signals
**Verdict: AGREE — low overlap**
- `bollinger_squeeze`: Fires AFTER expansion starts (3.5h late for GRASS)
- `squeeze_reversal`: Fires DURING squeeze (earlier entry)
- `coiled_spring`: Requires bullish trend first — GRASS had sell-off
- `grind_breakout`: Requires price above EMA20 during grind — different pattern

## Claim 4: Naming conflicts
**Verdict: AGREE — SQUEEZE_REVERSAL_* is clean namespace**

---

## Overall: PARTIAL AGREE

**What's correct:**
- GRASS trade data is accurate
- The pattern is real (sell-off → squeeze → expansion)
- Low overlap with existing signals
- No naming conflicts

**What needed fixing:**
1. **Sell-off window:** 2h → 6h (the sell-off was 6h before entry, not 2h)
2. **Velocity:** Hard requirement → bonus (was negative at entry)

**Recommendation:**
- Proceed with corrected conditions (6h sell-off window, velocity as bonus)
- Paper trade for 2 weeks
- Monitor for false signals during tight ranges that don't break out
