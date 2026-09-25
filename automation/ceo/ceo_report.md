## CEO Report — 2026-09-25 ~05:00 UTC

### Diagnosis
24h: 28T 32.1%WR -$2.52. 7d: 217T 44.2%WR -$1.57. 14d: 442T 47.1%WR -$4.91. System quiet — 1 open (BTC LONG). Most signals blocked by NEUTRAL confluence gate.

### Bleeding Points (verified)
- pullback-entry- SHORT: 26T 34.6%WR -$1.82/7d — losing across ALL regimes (EXTREME -$0.68, NORMAL -$0.52, HIGH -$0.90). 30d 52.1%WR +$0.35 — cold streak, not systemic.
- pump-chain- SHORT: 33T 45.5%WR -$0.93/7d. EXTREME 46T 50%WR -$0.67/14d (whipsaw). 30d 54.4%WR +$0.29.
- atr_sl_hit dominant exit: 17 trades/48h -$3.21. avg loss -5.05%.

### Fix Applied
**1 CODE FIX:** volume_spike recording bug. btc_crash_filter.py computes volume_spike ratio but decider_run.py never injected it into _signal_metadata. Chase filter blind to volume quality for 7+ days. Added 3 lines at decider_run.py:4187 — inject _crash_signal.volume_spike into _exec_meta. Expected +$0.30-0.80/7d.

### Verification
CL-T1 disable verified: 0 cut-loser-CL-T1 trades in11h since disable. LONG_RSI_SWEET_SPOT_BOOST deployed but no LONG trades yet (market SHORT-heavy). Pipeline healthy, 1 open position, all timers firing.

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
