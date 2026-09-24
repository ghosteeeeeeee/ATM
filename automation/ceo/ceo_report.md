## CEO Report — 2026-09-24 ~13:50 UTC

### Diagnosis
24h: 39T 33.3%WR -$2.18 (worsened from -$0.61 at 11:30 UTC). 7d: 220T 42.7%WR -$2.51. 14d: 453T 47.5%WR -$4.08. System degrading. All NEUTRAL. 2 open.

**SHORT RSI <50 is the #1 bleed.** 14d: 103T/218 SHORT trades have RSI <50 — 42.7%WR **-$3.69**. The upgrade_implementer lowered SHORT_RSI_FLOOR from 50→40 today, opening the40-50 bleeding band. 59 trades in40-50 band = 40.7%WR -$2.39.

**Today's losses:** pump-chain- SHORT 15T -$0.92 (NEUTRAL cold streak), mover+ LONG 3T -$0.61 (killed), others minor. Total -$2.39 today.

### Fix Applied
**SHORT_RSI_FLOOR 40→50.** Commit 9441fe6e. Blocks entire RSI <50 SHORT band (103T/14d -$3.69). NULL detection RSI preserved (36T 52.8%WR +$0.49). Expected +$0.50-1.00/7d.

### Verification
Need 24-48h to measure. Previous floor=50 was working (0 pullback-entry- SHORT trades while active). Current floor=40 allowed bleeding band through. Should see immediate reduction in SHORT losses.

### Remaining Issues
1. **CL-T1:** 17T/7d 0%WR -$1.83. Fire windows widened (2,3)→(4,6) today — monitoring.
2. **pump-chain- SHORT NEUTRAL:** 74T/14d 51.4%WR -$0.08 (breakeven). Cold streak today.
3. **atr_sl_hit dominates:** 142T/7d -$3.15. ATR_SL 1.3-1.5% too tight for NEUTRAL chop.
4. **SIGNAL DIVERSITY:** Only pump-chain+ LONG and volume-breakout-long+ pass NEUTRAL confluence.
