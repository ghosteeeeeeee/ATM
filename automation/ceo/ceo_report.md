## CEO Report — 2026-08-12 23:45 UTC

### Diagnosis
24h: 35T -$0.29 (42.9% WR — RED). 7d: 380T +$0.45 (51.8% WR — barely positive). Daily declining: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.23. Hotset 1 token (ADA LONG continuation+). Market NEUTRAL, macro gate REDUCE. System idle (6 open, 0 new trades in hours).

### Root Cause
Market regime: NEUTRAL 107/107 = no directional conviction. Macro gate REDUCE = correct behavior. Hotset nearly empty = compaction filtering low-conviction signals. Not a signal breakdown — cold streak on bb_bounce+,hzscore+ (16.7% WR 24h, but 48.5% WR 7d intact).

### Fix Applied
NO CHANGES. 7d positive, stars intact, trailing 0.60% deployed 27h. System idle by design. Overreacting destabilizes.

### Verification
Monitor: bb_bounce+,hzscore+ 7d WR. If drops <45% → escalate to disable. Disk84% — approaching WARN.

---

## CEO Report — 2026-08-12 21:30 UTC

### Decision: TRAILING_DISTANCE_PCT stays at 0.60%

Options evaluated:
- (A) Reduce to 0.30% — would re-introduce the problem we just fixed (locked in 0.15% profits, stopped on pullbacks)
- (B) Keep at 0.60% — low-ATR tokens get tight trailing stops, inherent to their volatility profile
- (C) ATR-scaled trailing — optimal but adds code complexity for 2-3 outlier tokens

**Chose B.** The trailing distance is a global parameter; optimizing it for ADA (0.35% ATR) and ASTER (0.17% ATR) degrades the typical token. If low-ATR tokens are a problem, the fix is an ATR minimum filter (skip tokens with ATR < 0.5%), not changing the trailing distance.

The tpsl_utils.py `if`→`elif` bug fix will self-correct on next position_manager cycle — no action needed.

---

## CEO Report — 2026-08-12 20:15 UTC

### Diagnosis
24h: 31T -$0.38 (41.9% WR — RED). 7d: 379T +$0.30 (51.7% WR — barely positive). Daily declining: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.32. System idle (7 open, hotset empty, NEUTRAL regime). Live trading ON.

### Root Cause
TRAILING_DISTANCE_PCT was 0.20% (set by CEO Aug 11 19:20). ATR_SL_MIN is 1.0%. With trailing distance 0.20%, trades locked in 0.15% profit on any 0.35% move, then stopped out on normal pullbacks. ATR_SL floor (1.0%) never activated — trailing exited first at tiny gains/losses. atr_sl_hit still dominant cost driver ($1.73 in 48h).

### Fix Applied
TRAILING_DISTANCE_PCT: 0.20% → 0.60%. Trade flow now:
- Entry at $1.00, SL at $0.99 (1.0% floor)
- Price hits $1.0035 → trailing activates, SL = $0.9975 (below entry, breathing room)
- Price hits $1.01 → trailing SL = $1.0040 (locks +0.40%)
- Pullback to $1.0040 → exits at +0.40%

Commit 4da383f.

### Verification
Monitor 24h: if atr_sl_hit >40% of exits → revert trailing to 0.30%. If WR improves to >45% → confirm fix working.

### Stars 7d (intact)
- bb_bounce+,range_finder+ LONG 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT 17T +$0.12 58.8%
- hzscore+,mover+ LONG 5T +$0.17 80%

### Action Items
- [ ] Monitor 24h: trailing distance 0.60% effect
- [ ] Monitor: hotset refill (currently empty, NEUTRAL regime)
- [ ] Monitor: 7 open positions (mostly hzscore+ LONG)
