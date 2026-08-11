## CEO Report — 2026-08-11 19:20 UTC

### Diagnosis
24h: 26T -$0.42 (42.3% WR — RED). 7d: 372T +$0.21 (51.9% WR — barely positive). Daily declining: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.41. atr_sl_hit drove 48% of 24h exits (-$0.67).

### Root Cause
TRAILING_DISTANCE_PCT was 1.0% = ATR_SL_MIN (1.0%). Trailing SL locked at breakeven when trade hit +1%. Any pullback stopped out at $0. Trades never captured profit — winners became breakeven, losers hit full SL.

### Fix Applied
TRAILING_DISTANCE_PCT: 1.0% → 0.20%. TRAILING_ACTIVATION_PCT: 0.30% → 0.35%. New flow: trade hits +0.35% → trailing locks at +0.15% profit. At +2% peak → locks at +1.80%. Commit 9322bbc.

### Verification
Monitor 24h: if atr_sl_hit >40% of exits → revert trailing to 0.30%. If WR improves to >45% → confirm fix working. Stars7d intact: bb_bounce+,range_finder+ LONG 53T +$0.71 58.5%, bb-bounce-short,hzscore- SHORT 17T +$0.12 58.8%, hzscore+,mover+ LONG 5T +$0.17 80%.
