## CEO Report — 2026-08-11 00:15 UTC

### Diagnosis

Verified DB: 24h 69T -$0.22 (43.5% WR — red, 2nd consecutive red after 15+ green). 12h 34T -$0.39 (38.2% WR — rough). 6h 14T -$0.34 (21.4% WR — very rough, post-SL-widening window). 7d 370T +$0.46 (51.9% WR — positive, trajectory intact). 4d 231T +$1.01 (51.9% WR — solid).

LONG 24h: 53T -$0.31 (39.6% WR — bleeding today, unusual). SHORT 24h: 16T +$0.09 (56.3% WR — profitable). 7d LONG: 233T +$1.57 (53.6% WR — strong). 7d SHORT: 137T -$1.11 (48.9% WR — legacy aging).

Stars7d all profitable: bb_bounce+,range_finder+ LONG 53T +$0.71 (58.5%), bb_bounce+,hzscore+ LONG 29T +$0.29 (51.7%), bb-bounce-short,hzscore- SHORT 16T +$0.17 (62.5%). Stars24h rough: bb_bounce+,hzscore+ LONG 23T -$0.05 (47.8% WR), bb_bounce+,range_finder+ LONG 8T -$0.12 (37.5% WR).

Cost drivers48h: atr_sl_hit 37T -$1.67, cut-loser-CL-trail 26T -$0.98. 6h: atr_sl_hit 8T -$0.31 (SL widening not yet effective — only2.5h old).

### Root Cause

Market NEUTRAL (105/106 tokens), mean-reversion entries (bb_bounce, hzscore) getting chopped in sideways price action. LONG bleeding at 39.6% WR today while SHORT is profitable (56.3%) — unusual inversion indicating choppy conditions favor quick exits over reversals. SL widening deployed at 22:00 has not had enough time to show effect (2.5h). 7d trajectory remains positive at 51.9% WR.

### Fix Applied

**No trading changes.** SL widening (ATR_SL_MIN 0.5%→1.2%, TRAILING_DISTANCE 0.30%→0.60%, CL_TRAIL_ACTIVATE -0.5→-1.0) deployed at 22:00. Monitor 24h: if 6h WR stays <30%, investigate SL width vs ATR of current regime. If24h stays red for 12+ more hours, consider reverting SLMIN/SLMAX to 0.8%/1.8%.

### Verification

7d remains positive (+$0.46). Stars intact on 7d. Pipeline healthy. 3 open positions. No phantoms. No action needed — let SL widening evaluation window complete (24h from 22:00 = 22:00 Aug 11).
