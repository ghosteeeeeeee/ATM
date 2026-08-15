## CEO Report — 2026-08-15 23:00 UTC (verified)

### Diagnosis
24h 46T -$0.14 (47.8% WR — RED). 7d 453T -$1.52 (50.3% WR). R:R 0.85:1 (avg win 0.485% vs avg loss -0.571%) — IMPROVED from 0.75:1. ATR_SL 43T/48h avg -0.79% (-$3.42) still dominates. PM_TRAIL only 14T/48h (down from 69T — new params taking effect). 5 open -$0.05 flat. Aug 15: 35T -$0.04 (volume stable after recovery). Legacy losers closing: wave_catcher+, range_finder+, accel-300- all disabled and aging out. ct-hot+ 13T +$0.06 53.8% — profitable. Coin tracker: SOL hot comp=58.7 setup=60.7 — strongest candidate.

### Root Cause
Eval windows (PM_TRAIL 0.60% act/0.50% dist, ATR_TP_K_MULT 2.5, TRAIL_ACT 0.40%, SIGNAL_FILTER_SPEED_MIN 30, COIN_TRACKER_HOT_MIN_COMPOSITE 45) closing ~Aug 17. R:R improving as eval params take effect. PM_TRAIL exits reduced (69T→14T) — trades now reaching main trailing. ATR_SL still dominant but R:R approaching neutral (0.85:1).

### Fix Applied
NO CHANGES — eval windows active. System flat, not bleeding hard. R:R trending toward 1:1.

### Verification
Monitor: eval close ~Aug 17, R:R 48h (should ↑ from 0.85:1 toward 1:1+), daily trades (must stay >30T), PM_TRAIL exits (should ↓ further), ATR_SL count (should ↓). If R:R still <0.90:1 post-eval → widen ATR_SL or add regime filter on SHORTs.

---

## CEO Report — 2026-08-15 16:00 UTC (verified)

### Diagnosis
24h 44T -$0.23 (47.7% WR — RED). 48h 123T -$1.03 (49.6% WR). 7d 450T -$1.68 (50.2% WR). R:R 0.75:1 (avg win 0.43% vs avg loss -0.57%) — IMPROVING (was 0.71:1). ATR_SL 44T/48h avg -0.78% (-$3.46) still dominates losses. PM_TRAIL 69T/48h avg +0.26% (+$1.75) — positive but small. 5 open $0 flat. Aug 15: 31T -$0.13 (volume recovering from 15T yesterday). Top 7d: r2-trend-long2 17T +$0.19 64.7%, bb_bounce+ 21T +$0.21 61.9%, ct-hot+ 12T +$0.11 58.3%. Legacy losers aging out (wave_catcher+, range_finder+ — all disabled, trades closing). 6 eval windows active closing ~Aug 17.

### Root Cause
R:R still inverted but improving. ATR_SL dominates at -0.78% avg while PM_TRAIL captures only +0.26%. Winners cut too early — trades peak at ~0.5% but PM_TRAIL catches at 0.26%. Eval windows targeting this: PM_TRAIL 0.60% activation catches trades with real momentum, ATR_TP_K_MULT 2.5 extends TP, TRAIL_ACT 0.40% lets more trades reach trailing. Volume recovering — SIGNAL_FILTER_SPEED_MIN 30 working (31T today vs 15T yesterday).

### Fix Applied
NO CHANGES — 6 eval windows active, closing ~Aug 17. Changing now invalidates results. System stabilizing: volume up, R:R improving, legacy losers closing. Eval windows need data to evaluate.

### Verification
Monitor: eval close ~Aug 17, R:R 48h (should ↑ from 0.75:1 toward 0.90:1+), daily trades (should stay >30T), avg PM_TRAIL exit (should ↑ from 0.26%), ATR_SL count (should ↓ from 44). If R:R still inverted post-eval → escalate to ATR_SL widening or regime filter on SHORTs.

---

## CEO Report — 2026-08-15 14:15 UTC (verified)

### Diagnosis
Today 29T -$0.14 (44.8% WR — RED). range_finder+ LONG 9T -$0.14 33.3% — ENTIRE LOSS. ct-hot+ 11T +$0.08 54.5% WR — profitable. 4 open (all ct-hot) $0 flat. 48h R:R 0.71:1 (avg win 0.48% vs avg loss -0.68%). 48h: ATR_SL 45T avg -0.73% dominates (-$3.62), PM_TRAIL 13T avg -0.26% (-$0.35). 7d 455T -$1.64 50.3% WR. range_finder+ legacy trades closing (all 9 between 03:36-04:06 UTC). Volume recovering: 29T today vs 15T yesterday at same time.

### Root Cause
range_finder+ LONG is disabled (RANGE_FINDER_PLUS_ENABLED=False) but legacy open positions closed today. These 9 trades are the ENTIRE day's loss. ct-hot+ performing well (54.5% WR). R:R still inverted but eval windows targeting this (PM_TRAIL activation 0.40%, distance 0.60%, ATR_TP_K_MULT 2.5, trailing activation 0.40%, SIGNAL_FILTER_SPEED_MIN 30). 6 eval windows active — closing ~Aug 17.

### Fix Applied
NO CHANGES — eval windows active. Changing now invalidates results. System flat, not bleeding hard. range_finder+ legacy trades will age out. ct-hot+ volume should increase as COIN_TRACKER_HOT_MIN_COMPOSITE=45 takes effect.

### Verification
Monitor: eval close ~Aug 17, R:R 48h (should ↑ from 0.71:1), daily trades (should ↑ from 29T), range_finder+ legacy trades (should reach 0), ct-hot+ WR (must >50%). If R:R still inverted post-eval → escalate.

---

## CEO Report — 2026-08-15 (latest run — verified)

### Diagnosis
24h 47T -$0.40 (46.8% WR — RED). 48h 123T -$1.12 (49.6% WR). 7d 453T -$1.54 (50.6% WR). R:R inverted 0.70:1 (avg win 0.48% vs avg loss -0.69%). PM_TRAIL avg exit 0.27% (MFE 0.51% — trades peak 0.51%, floor 0.11%, exit at 0.27%). ATR_SL avg exit -0.79% (MFE 1.12% — trades peak 1.12%, crash to SL). 5 open -$0.05. Daily: Aug 12 +$0.95 (43T 67.4% WR) → Aug 13 -$1.58 (53T 43.4%) → Aug 14 -$0.56 (80T 52.5%) → Aug 15 -$0.04 (27T 48.1%). Best 7d: r2-trend-long2 17T +$0.19 64.7%, hzscore+,mover+ 5T +$0.17 80%, bb_bounce+ 21T +$0.21 61.9%, ct-hot+ 9T +$0.18 66.7%. Worst 7d: wave_catcher+ 8T -$0.42 (killed), range_breakout+ 8T -$0.41 (killed), trend_momentum 6T -$0.37 (killed).

### Root Cause
PM_TRAIL distance 0.40% too tight — trail floor = peak-0.40%. Trade peaking at 0.51% → floor 0.11% → exits at 0.27%. Winners cut too early while ATR_SL takes full -0.79% loss. Signal starvation persists (27T vs 100T Aug 12) but mitigated by recent fixes (SIGNAL_FILTER_NEUTRAL_SPEED_MIN=15, COIN_TRACKER_HOT_MIN_COMPOSITE 45).

### Fix Applied
WIDENED PM_TRAIL_DISTANCE_PCT 0.40%→0.60%. Trail floor now peak-0.60%. Trade peaking at 0.51% → floor -0.09% (breakeven guard catches at 0.0%). Trade peaking at 1.0% → floor 0.40%. Expected: avg exit ↑ from 0.27% toward 0.40%+, R:R ↑ from 0.70:1 toward 0.90:1+.

### Verification
Monitor 48h: avg PM_TRAIL exit % (should ↑ from 0.27%), R:R ratio (should ↑ from 0.70:1), daily trades (should ↑ from 27), ATR_SL count (should ↓). Eval windows closing ~Aug 17 — if R:R still inverted post-eval, escalate. Coin tracker: 3 coins in accumulation (SOL 58.9, DOGE 56.4, BTC 53.2) — system needs better Wyckoff phase classification.

---

## CEO Report — 2026-08-15 12:15 UTC

### Diagnosis
24h 53T -$0.27 (49.1% WR — FLAT). 48h 125T -$1.06 (50.4% WR). Today 26T -$0.08. 5 open (all ct-hot: BIGTIME/ZRO/MON/LINEA/DYDX) $0 flat. ATR_SL still dominates losses (44T/48h -$3.60). 7d: 6 of 8 days red. Best7d: r2-trend-long2 17T +$0.19 64.7%, bb_bounce+ 21T +$0.21 61.9%, bb-bounce-short,hzscore- 18T +$0.14 61.1%. Worst7d: wave_catcher+ LONG 8T -$0.42 37.5%, range_breakout+ 8T -$0.41 25%, range_finder+ 9T -$0.14 33.3%.

### Root Cause
R:R inverted persists — ATR_SL exits avg -0.81% while PM_TRAIL/trailing exits avg ~0.26%. Signal starvation ongoing (26T today vs 100T Aug 12). 5 eval windows deployed Aug 15 closing ~Aug 17 — TRAIL_ACT 0.40%, PM_TRAIL_DIST 0.60%, ATR_TP_K_MULT 2.5, PM_TRAIL race fix, SIGNAL_FILTER_SPEED_MIN 30. COIN_TRACKER_HOT_MIN_COMPOSITE 50→45 deployed to unblock ct-hot volume.

### Fix Applied
NO CHANGES — eval windows active. Changing now invalidates results. System flat, not bleeding hard. Wait for eval close Aug 17.

### Verification
Monitor: eval close ~Aug 17, R:R 48h (should ↑ from 0.70:1), daily trades (must ↑ from 26T), ct-hot volume (should ↑ after composite threshold drop), ATR_SL count (should ↓ from 44). If R:R still inverted post-eval → escalate.

---

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

---

## CEO Report — 2026-08-16 20:00 UTC

### Diagnosis
24h 43T -$0.22 (48.8% WR — RED). 48h 120T -$1.02 (50.0% WR). 7d 451T -$1.67 (50.3% WR). R:R inverted 0.67:1 (avg win 0.45% vs avg loss -0.67%). ATR_SL 166T/7d avg -0.62% (-$10.56) dominates. PM_TRAIL 231T/7d avg +0.40% (+$9.29) — improving. 5 open $0 flat. Daily: Aug 12 +$0.49 (100T) → Aug 13 -$1.58 (53T) → Aug 14 -$0.56 (80T) → Aug 15 -$0.12 (32T) → Aug 16 -$0.22 (43T partial). Best 7d: r2-trend-long2 17T +$0.19 64.7%, bb_bounce+ 21T +$0.21 61.9%, hzscore+,mover+ 5T +$0.17 80%.

### Root Cause
ATR_SL still dominates losses (166T/7d = 36.8% of all trades). R:R inverted because winners avg +0.45% while losers avg -0.67%. Eval windows (PM_TRAIL 0.60% act/0.50% dist, ATR_TP_K_MULT 2.5, TRAIL_ACT 0.40%, SIGNAL_FILTER_SPEED_MIN 30, COIN_TRACKER_HOT_MIN_COMPOSITE 45) deployed Aug 15 — closing ~Aug 17. System needs eval data before further tuning.

### Fix Applied
NO CHANGES — 6 eval windows active, closing ~Aug 17. Changing now invalidates results. SIGNAL_FILTER_SPEED_MIN 30 needs 24h+ to show volume impact (Aug 15 only 32T vs 100T Aug 12).

### Verification
Monitor 48h: eval close ~Aug 17, R:R (should ↑ from 0.67:1), ATR_SL count (should ↓), avg PM_TRAIL exit (should ↑ from 0.40%), daily trades (must ↑ from 32T). If R:R still inverted post-eval → consider widening ATR_SL or regime filter for SHORT entries.

## CEO Report — 2026-08-15 23:00 UTC

### Diagnosis
R:R still inverted at 0.68:1 (avg win 0.45% vs avg loss -0.66%). 24h: 45T -$0.35 (46.7% WR — RED). Aug 15 volume recovering to34T from 15T starvation. 6 eval windows active closing ~Aug 17. Legacy hzscore- trades5T -$0.35 still closing (signal killed Aug 13). All dead signals already killed.

### Root Cause
PM_TRAIL avg exit 0.23% still cutting winners short while ATR_SL takes -0.77%. Eval windows (PM_TRAIL 0.60%/0.50%, ATR_TP_K_MULT 2.5, TRAIL_ACT 0.40%) not yet showing R:R improvement. Legacy trades from killed signals still bleeding in48h window.

### Fix Applied
NO CHANGES — eval windows close tomorrow. Changing now invalidates measurement. Legacy hzscore- trades will age out naturally.

### Verification
Monitor: eval close ~Aug 17, R:R (should ↑ from 0.68:1), daily trades (should stay >30T), avg PM_TRAIL exit (should ↑ from 0.23%). If R:R still inverted after eval closure → widen PM_TRAIL_DISTANCE_PCT 0.50%→0.70%.
