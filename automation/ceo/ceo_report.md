## CEO Report — 2026-08-15 (latest run)

### Diagnosis
24h 56T -$0.32 (50.0% WR — FLAT). 48h 125T -$1.06 (50.4% WR). R:R improved to 0.70:1 (avg win 0.48% vs avg loss -0.69%) — up from 0.35:1. Today 26T -$0.08. 4 open $0 flat. NEUTRAL regime. Best 7d: r2-trend-long2 17T +$0.19 64.7%, bb_bounce+ 21T +$0.21 61.9%, bb-bounce-short,hzscore- 18T +$0.14 61.1%. ATR_SL still dominates losses (44T/48h -$3.60). PM_TRAIL improving (Aug 15 avg 0.06% vs Aug 14 avg 0.27%).

### Root Cause
coin_tracker_hot generates 2-4 signals/cycle but ZERO become trades. Root cause: `COIN_TRACKER_HOT_MIN_COMPOSITE=50` too tight. BTC (accumulation BULL, comp=50.5) fails health check (warm, momentum=55<70). IMX (hot, comp=57.6) has price=0.0 data bug. ZK (comp=48.9), CAKE (comp=49.6) both filtered. Signal starvation persists (26T today vs 100T Aug 12) — eval windows helping R:R but not volume.

### Fix Applied
LOWERED `COIN_TRACKER_HOT_MIN_COMPOSITE` 50→45. Unblocks ZK (comp=48.9, warm/momentum=73) and CAKE (comp=49.6, warm/momentum=74) immediately. IMX price=0.0 bug flagged for separate investigation. Eval windows active (TRAIL_ACT 0.40%, PM_TRAIL_DIST 0.60%, ATR_TP_K_MULT 2.5, PM_TRAIL race fix, SIGNAL_FILTER_SPEED_MIN 30) — closing ~Aug 17.

### Verification
Monitor 48h: ct-hot signals/day (should ↑ from 0), ct-hot WR (must >50%), R:R (should ↑ from 0.70:1 toward 0.75:1+), daily trades (must ↑ from 26T). Eval windows closing ~Aug 17 — if R:R still inverted after eval, escalate. IMX price bug needs fix (data quality issue blocking hot setup signal).

---

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
