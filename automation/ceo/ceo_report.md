## CEO Report — 2026-08-15 (verified)

### Diagnosis
24h: 79T -$0.97 (49.4% WR — RED, 3rd consecutive red day). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.46 → Aug 15 -$0.97 (worsening). 0 open. R:R inverted: avg win 0.507% vs avg loss -0.743% (0.68:1). ATR_SL hit 61T -$4.87 in 48h (dominant cost). wave_catcher+ LONG 6T -$0.34 33.3% WR (below 10T threshold). mover+ LONG 7T -$0.15 28.6% WR (below 10T). Stars7d intact (5 profitable).

### Root Cause
ATR_TP_K_MULT 1.5 too tight — winners capped at 0.51% while SL takes 0.74%. 3rd red day confirms fix insufficient. wave_catcher+ and mover+ below 10-trade disable threshold.

### Fix Applied
BUMPED ATR_TP_K_MULT 1.5→2.0. Expected: avg win increases from 0.51% toward 0.74%+, R:R improves to ~1:1. 48h eval window starts now.

### Verification
Monitor: daily PnL (if -2 more red → investigate deeper), R:R ratio (48h), wave_catcher+ LONG (if hits 10T without improvement → disable), mover+ LONG (same).

---

## CEO Report — 2026-08-14 15:20 UTC (verified)

### Diagnosis
24h: 80T -$0.93 (50.0% WR — RED). 7d: 451T -$0.74 (51.7% WR — slightly negative). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.46 (67T, 52.2%). 2 open $0 flat. ATR fix eval ~26h: avg win 0.51% (up from 0.44%), avg loss 0.74%, R:R 0.69:1 (improving but still inverted). Exit reasons: atr_sl_hit 32T -$2.65 (96% of losses), profit-monster-trail 45T +$1.46 (avg 0.34%). Stars7d intact: bb_bounce+,range_finder+ 52T +$0.70 57.7%, bb_bounce+ 21T +$0.21 61.9%.

### Root Cause
R:R structural: avg win 0.51% vs avg loss 0.74% — trailing exits too early (0.34% avg), ATR SL too wide (0.82% avg). wave_catcher+ LONG already disabled. Accel-300- (35T -$0.31) and hzscore- (16T -$0.17) legacy SHORTs still draining 7d but clearing.

### Fix Applied
NO CHANGES — ATR_TP_K_MULT 1.5 eval window ~26h old. Changing now invalidates measurement. If Aug 15 also red → bump ATR_TP_K_MULT 1.5→2.0 (expected avg win 0.68%, R:R ~0.92:1).

### Verification
Monitor: daily PnL (if 3rd consecutive red → ATR_TP_K_MULT 2.0), avg trail win (should reach 0.55%+ by 48h), disk (82% — if hits 85% → cleanup).

---

## CEO Report — 2026-08-15 (verified)

### Diagnosis
24h: 79T -$0.62 (53.2% WR — RED). 7d: 438T -$0.30 (51.3% WR — stable). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.25 (recovering). 4 open $0 flat. R:R inverted: avg win 0.44% vs avg loss 0.77% (0.57:1). ATR_TP_K_MULT 1.5 and PM_TRAIL 0.40 deployed, evaluation window active.

### Root Cause
R:R structural: stop losses avg -$0.077 vs trailing profits avg +$0.039. Even 53% WR can't overcome 0.57:1 ratio. ATR fix should increase TP target, PM_TRAIL widening should let winners run longer.

### Fix Applied
NO CHANGES — stability period. ATR_TP_K_MULT 1.5 and PM_TRAIL_DISTANCE_PCT 0.40 in 48h evaluation window. Changing params during eval invalidates results.

### Verification
Monitor 48h: avg trail win (should increase from 0.44% toward 0.77%+), daily PnL (if -2 consecutive red → investigate), atr_sl_hit count (should decrease). Secondary: phantom trades (128x), stale prices (17 tokens), disk at 82%.

---

## CEO Report — 2026-08-15 (latest verified)

### Diagnosis
24h: 80T -$0.65 (52.5% WR — RED). 7d: 445T +$0.38 (53.0% WR — barely positive). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.25 (recovering). 2 open flat. Both LONG (-$0.41 56.1% WR) and SHORT (-$0.24 43.5% WR) negative 24h. Biggest bleeder: wave_catcher+ LONG 6T -$0.34 33.3% WR. R:R structural: avg SL -$0.080 vs avg trail +$0.034 (0.43:1 inverted). ATR_TP_K_MULT 1.5 deployed, needs 48h eval.

### Root Cause
1. wave_catcher+ LONG consistently worst performer — 6T -$0.34 33.3% WR 24h, negative across all timeframes. Base WAVE_CATCHER_ENABLED still fires LONG despite PLUS variant killed.
2. R:R inverted: stop losses avg -$0.080, trailing profits avg +$0.034. Even 52.5% WR can't overcome 0.43:1 ratio.

### Fix Applied
DISABLED WAVE_CATCHER_ENABLED (was True). wave_catcher+ LONG is worst active signal. SHORT profitable but base flag fires both directions. No R:R param changes during stability period (ATR_TP_K_MULT 1.5 eval window active).

### Verification
Monitor 24h: daily PnL (should improve ~$0.06/day from wave_catcher+ kill), R:R ratio (ATR_TP_K_MULT eval closes in ~24h), SHORT7d (legacy clearing, should improve).

---

## CEO Report — 2026-08-14 (latest verified)

### Diagnosis
24h: 77T -$0.70 (51.9% WR — RED). 7d: daily Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.30 (54.1% WR — recovering). 3 open +$0.07. Stars7d intact (5 profitable). Exit reason 7d: profit-monster-trail 233T +$10.62 (avg 0.46%), atr_sl_hit 169T -$10.49 (avg 0.60%). R:R ratio 0.60:0.46 ≈ 1.3:1 UNFAVORABLE.

### Root Cause
PM_TRAIL too tight: distance 0.20% exits winners at avg 0.46% while SL avg loss is 0.60%. Trail activates at +0.30% and only gives 0.20% room — winners get shaken out on normal pullbacks before reaching ATR_TP_K_MULT target (1.5x SL). atr_sl_hit still dominant (169T -$10.49 7d).

### Fix Applied
CHANGED PM_TRAIL_DISTANCE_PCT 0.20→0.40. Trail now gives 0.40% room behind peak instead of 0.20%. Expected: avg trail win increases from 0.46% toward 0.60%+, R:R approaches 1:1 or better. ATR_TP_K_MULT 1.5 already in place from previous run.

### Verification
Monitor 48h: avg trail win (should increase from 0.46%), daily PnL (if -2 consecutive red → revert PM_TRAIL), atr_sl_hit count (should decrease as fewer premature exits).