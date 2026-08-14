## CEO Report — 2026-08-14 (latest verified)

### Diagnosis
24h: 77T -$0.70 (51.9% WR — RED). 7d: daily Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.30 (54.1% WR — recovering). 3 open +$0.07. Stars7d intact (5 profitable). Exit reason 7d: profit-monster-trail 233T +$10.62 (avg 0.46%), atr_sl_hit 169T -$10.49 (avg 0.60%). R:R ratio 0.60:0.46 ≈ 1.3:1 UNFAVORABLE.

### Root Cause
PM_TRAIL too tight: distance 0.20% exits winners at avg 0.46% while SL avg loss is 0.60%. Trail activates at +0.30% and only gives 0.20% room — winners get shaken out on normal pullbacks before reaching ATR_TP_K_MULT target (1.5x SL). atr_sl_hit still dominant (169T -$10.49 7d).

### Fix Applied
CHANGED PM_TRAIL_DISTANCE_PCT 0.20→0.40. Trail now gives 0.40% room behind peak instead of 0.20%. Expected: avg trail win increases from 0.46% toward 0.60%+, R:R approaches 1:1 or better. ATR_TP_K_MULT 1.5 already in place from previous run.

### Verification
Monitor 48h: avg trail win (should increase from 0.46%), daily PnL (if -2 consecutive red → revert PM_TRAIL), atr_sl_hit count (should decrease as fewer premature exits).

---

## CEO Report — 2026-08-15 (verified latest)

### Diagnosis
24h: 77T -$0.68 (51.9% WR — RED). 7d: ~445T -$0.83 (51.3% WR — slightly negative). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 (legacy clearing) → Aug 14 -$0.20 (recovering). Stars7d intact (5 profitable). Cost drivers48h: atr_sl_hit 63T -$4.82 (96% of losses).

### Root Cause
R:R imbalance structural: avg SL loss -$0.077 vs avg trail win +$0.039 (2:1 unfavorable). ATR_TP_K_MULT was 1.2 — TP target too close to SL, trades get stopped out before reaching profit. atr_sl_hit dominates losses (63T -$4.82 in 48h).

### Fix Applied
CHANGED ATR_TP_K_MULT 1.2→1.5. Targets 1.5:1 R:R instead of 1.2:1. Gives trades more room to reach profit before trailing SL takes over. Expected: fewer premature atr_sl_hit exits, higher avg win.

### Verification
Monitor 48h: ATR avg win (should increase from $0.039), atr_sl_hit count (should decrease), daily PnL (if -2 consecutive red → revert).

---

## CEO Report — 2026-08-14 (12:49 UTC — verified)

### Diagnosis
24h: 75T -$0.85 (52.0% WR — RED). 7d daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.40 (recovering). 2 open flat ($0). Stars7d intact (5 profitable). Cost drivers48h: atr_sl_hit 64T -$4.89 (96% of losses). Wave_catcher+ LONG already disabled. mover+ LONG 4T -$0.24 25% WR (below 10-trade threshold).

### Root Cause
R:R imbalance structural: avg SL loss -$0.077 vs avg trail win +$0.039 (2:1 unfavorable). ATR_SL hit dominates (64T -$4.89 in 48h). Legacy SHORT bleeders (accel-300-, hzscore-, range_breakout-) draining via residual trades — all disabled. Wave_catcher+ LONG already disabled. mover+ standalone bleeding but combo (hzscore+,mover+ 80% WR) is a star — can't disable without collateral.

### Fix Applied
NO CHANGES — system in stability period (14+ changes in 48h). Stars intact. Daily recovering. ATR_TP_K_MULT 1.0→1.2 deployed, needs48h evaluation. Dedicated R:R tuning session needed (not CEO band-aid).

### Verification
- 24h: -$0.85 (stable vs -$0.75 last run) ✓
- 7d daily: Aug 13 -$1.58 → Aug 14 -$0.40 (recovering) ✓
- Stars7d: 5 profitable intact ✓
- Pipeline: healthy ✓
- 2 open trades flat ✓

### Monitor
- daily PnL: if -2 consecutive red after today → investigate root cause
- range_breakout_short: if 7d degrades below 45% WR → re-disable
- mover+ LONG: if reaches 10T without improvement → consider standalone disable
- ATR avg win: should increase from ~0.49% after TP_K_MULT adjustment
