## CEO Report — 2026-08-15 (23:30 UTC)

### Diagnosis
System flat, eval windows holding. Verified DB: 24h 51T +$0.11 (49.0% WR), 7d ~456T +$0.11 (flat). R:R by exit type: PM_TRAIL avg +0.283% vs ATR_SL avg -0.763% = 0.37:1 (inverted). ATR_SL 46T/48h avg -0.763% (-$3.52) dominates losses. PM_TRAIL 69T/48h avg +0.283% (+$1.99) — eval window changes holding. 5 open -$0.09 flat. Volume 51T (stable, up from 15T starvation low). Auto_1hr stable, no changes needed.

### Root Cause
R:R structural: PM_TRAIL captures 37% of ATR_SL magnitude. Trades peak ~1% MFE before dying at SL. Eval windows (PM_TRAIL act 0.60%/dist 0.60%, TRAIL_ACT 0.40%, ATR_K 2.5, SIGNAL_FILTER 30, COIN_TRACKER_HOT 45) deployed Aug 15, closing ~Aug 17. range_finder+ legacy 9T 33.3% WR -$0.14 (all closed, aging out). Legacy losers: wave_catcher+ 8T 37.5% -$0.42, range_breakout+ 8T 25% -$0.41, trend_momentum 6T 16.7% -$0.37 (all disabled, closing).

### Fix Applied
NO CHANGES — eval windows close ~Aug 17. PM_TRAIL +0.283% avg confirms eval working (was -0.26% before changes). System flat (49% WR +$0.11). Changing now invalidates results.

### Verification
24h +$0.11 (49.0% WR) — flat. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.16. R:R 0.37:1 by exit type (needs 1:1+). Volume 51T stable. 5 stars7d intact: return_exhaustion_long 3T 100% +$0.39, hzscore+,mover+ 5T 80% +$0.17, r2-trend-long2 17T 64.7% +$0.19, bb_bounce+ 21T 61.9% +$0.21, ct-hot+ 16T 56.3% +$0.16.

### Next Actions
1. **Aug 17:** Evaluate all 6 windows. Key metrics: PM_TRAIL avg exit (should hold >0.25%), ATR_SL count (should ↓), R:R (should ↑ from 0.37:1)
2. **Post-eval:** If R:R still <0.5:1, consider ATR_SL widen or PM_TRAIL further loosening
3. **Monitor:** ct-hot+ (must >55% WR), return_exhaustion_long (must >80% WR)
4. **Legacy:** range_finder+, wave_catcher+, range_breakout+ all closing — no action needed
