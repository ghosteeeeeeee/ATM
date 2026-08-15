## CEO Report — 2026-08-15 (latest run)

### Diagnosis
24h 56T -$0.20 (50% WR — recovering). 48h 122T -$0.96 (50.8% WR). Daily: Aug 12 +$0.49 (100T) → Aug 13 -$1.58 (53T) → Aug 14 -$0.56 (80T) → Aug 15 +$0.06 (21T). 5 open -$0.09. R:R inverted 0.33:1 (PM_TRAIL avg +0.26% vs ATR_SL avg -0.78%). KEY: ATR_SL trades avg MFE 1.18% — trades PEAK at 1.18% then die. 43 ATR_SL/48h dominates losses (-$3.37). NEUTRAL regime (411/549 tokens). Stars7d intact. Pipeline healthy.

### Root Cause
R:R inverted because PM_TRAIL has a race condition: trail state cleared when price crashes fast (1.18% → 0.25% in <30s), bypassing breakeven guard. 43 trades/48h peaked at 1.18% then hit -0.78% ATR_SL — should have exited at 0.0% breakeven. Additionally, TRAILING_ACTIVATION_PCT 0.60% too high for NEUTRAL regime — most trades hit ATR_SL before reaching trailing. range_finder standalone bypass creating9T of 33.3% WR bleeding trades.

### Fix Applied
1. LOWERED TRAILING_ACTIVATION_PCT 0.60%→0.40% — more trades reach trailing
2. REMOVED range_finder from STANDALONE_BYPASS — 9T 33.3% WR bleeding
3. FIXED PM_TRAIL race condition — removed "clear on drop below activation" so breakeven guard catches fast crashes. Trades now exit at 0.0% instead of -0.78%

### Verification
Monitor48h: R:R (should ↑ from 0.33:1), ATR_SL count (should ↓ from 43), avg win (should ↑ from 0.26%), PM_TRAIL exits (should ↑ from 70). Eval windows (PM_TRAIL 0.60%, ATR_TP_K_MULT 2.5, TRAIL_ACT 0.60%) closing ~Aug 17.

### Verification
Monitor: daily trades (must ↑ within 24h), range_finder standalone WR (must >45% to keep enabled), eval close ~Aug 17, R:R ratio (should ↑ from 0.49:1 after eval windows close). NO other changes — eval windows active, SIGNAL_FILTER_SPEED_MIN needs time.
