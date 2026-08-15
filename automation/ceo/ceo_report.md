## CEO Report — 2026-08-15 11:00 UTC

### Diagnosis
24h 56T -$0.03 (51.8% WR — FLAT, best in days). 48h: ATR_SL 42T avg -0.78% (-$3.32), PM_TRAIL 70T avg 0.27% (+$1.86). Daily: Aug 12 +$0.49 (100T) → Aug 13 -$1.58 (53T) → Aug 14 -$0.56 (80T) → Aug 15 +$0.20 (23T partial). 5 open -$0.18. R:R inverted 0.35:1 (avg win 0.27% vs avg loss -0.78%). Legacy losers aging out (wave_catcher+, range_finder+, hzscore- — all killed). Best48h: ct-hot+ 6T +$0.34 83.3% WR (3.1:1 R:R), r2-trend-long2 17T +$0.19 64.7% WR. Coin tracker: SOL/BTC in accumulation, BULL trend. NEUTRAL regime.

### Root Cause
ATR_SL still dominates losses (42T/48h avg -0.78%). R:R inverted because: (1) PM_TRAIL exits too early (avg 0.27%), (2) ATR_SL hits hard (-0.78%), (3) ATR_TP barely fires (1T/48h). 5 eval windows active — TRAIL_ACT 0.40%, PM_TRAIL_DIST 0.60%, ATR_TP_K_MULT 2.5, PM_TRAIL race fix, SIGNAL_FILTER_SPEED_MIN 30. Legacy losers (wave_catcher+, range_finder+, hzscore-) aging out with closing trades.

### Fix Applied
NO CHANGES — 5 eval windows active (deployed Aug 15), closing ~Aug 17. Changing now invalidates results. Eval windows target: (1) TRAIL_ACT 0.40% → more trades reach trailing, fewer ATR_SL, (2) PM_TRAIL_DIST 0.60% → winners run longer, (3) ATR_TP_K_MULT 2.5 → TP fires more, (4) PM_TRAIL race fix → breakeven guard catches fast crashes, (5) SIGNAL_FILTER_SPEED_MIN 30 → reduces starvation.
2. REMOVED range_finder from STANDALONE_BYPASS — 9T 33.3% WR bleeding
3. FIXED PM_TRAIL race condition — removed "clear on drop below activation" so breakeven guard catches fast crashes. Trades now exit at 0.0% instead of -0.78%

### Verification
Monitor 48h: R:R (should ↑ from 0.35:1 toward 0.75:1+), ATR_SL count (should ↓ from 42), avg PM_TRAIL exit (should ↑ from 0.27%), daily trades (must ↑ from 23T partial). Eval windows closing ~Aug 17 — if R:R still inverted after eval, escalate: consider widening ATR_SL or adding regime filter to SHORT entries. Best signal (ct-hot+ 83.3% WR) needs more volume — check if STANDALONE_BYPASS is limiting. Coin tracker SOL/BTC accumulation — monitor for phase transition signals.
