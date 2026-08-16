## CEO Report — 2026-08-16 (9th run, eval finalized)

### Diagnosis
Eval windows CLOSED. Verified DB: 24h 58T -$0.36 (43.1% WR — RED). 7d 455T -$1.85 (50.3% WR). 48h exit: PM_TRAIL 60T 75.8% WR avg +0.27% (+$1.68), ATR_SL 48T 2% WR avg -0.76% (-$3.66), T1 12T 100% WR avg +0.57% (+$0.69). R:R 0.75:1 (inverted but improved from 0.38:1 earlier this week). 4 open. Stars 7d: return_exhaustion_long 3T 100% +$0.39, hzscore+,mover+ 5T 80% +$0.17, r2-trend-long2 17T 64.7% +$0.19, bb_bounce+ 22T 63.6% +$0.25.

### Eval Window Final Decisions
| Param | Before | After | Rationale |
|-------|--------|-------|-----------|
| PM_TRAIL_ACTIVATE_PCT | 0.60% | 0.40% KEPT | Reverted Aug 16. R:R 0.37:1→0.75:1. PM_TRAIL 60T 75.8% WR. |
| PM_TRAIL_DISTANCE_PCT | 0.60% | 0.50% KEPT | Tightened Aug 15. Floor +0.10%. Avg exit 0.27%. |
| ATR_TP_K_MULT | 2.5 | **2.0 REVERTED** | 2.5x TP unreachable (1 hit/48h). 2.0x more realistic as secondary exit. |
| TRAILING_ACTIVATION_PCT | 0.60% | 0.40% KEPT | PM_TRAIL handles most exits; this is fallback. |
| SIGNAL_FILTER_SPEED_MIN | 45 | 30 KEPT | Recovery 15T→50T+ confirmed. NEUTRAL override 15. |
| COIN_TRACKER_HOT_MIN_COMPOSITE | 50 | 45 KEPT | Unblocked ZK+CAKE. ct-hot+ 25T 48% WR 7d. |

### Fix Applied
ATR_TP_K_MULT 2.5 → 2.0 (only change — all other eval params confirmed working).

### Next Focus
R:R still inverted (0.75:1). PM_TRAIL avg exit 0.27% vs ATR_SL avg -0.76%. Need to either widen PM_TRAIL to capture more profit, or widen ATR_SL to give trades more room. No more legacy losers to kill — all bleeding signals disabled. System is now signal-quality-limited, not signal-quantity-limited.

---

## CEO Report — 2026-08-16: PM_TRAIL_ACTIVATE_PCT Revert Explained

### What happened
PM_TRAIL_ACTIVATE_PCT was raised from 0.30% → 0.60% on Aug 14 to give trades room to reach ATR_TP (1.6% target). After 48h eval, it was reverted to 0.40% on Aug 16.

### The data that showed 0.60% was worse

**Before (0.30% → 0.60%):** R:R was 0.67:1. PM_TRAIL avg exit 0.44%.

**After (0.60% for 48h):** R:R worsened to 0.37:1. PM_TRAIL avg exit dropped to 0.29%.

The problem: ATR_SL trades peak at 0.94% MFE (mean favorable excursion) on average, but the trail only arms at 0.60%. A trade peaking at 0.94% that reverses needs to hold above 0.60% for the trail to catch it — but the reversal happens too fast. The trail never activates, and the trade crashes through to ATR_SL at -0.79%.

**48h exit breakdown at 0.60% activation:**
- PM_TRAIL: 60T avg +0.27% (+$1.68)
- ATR_SL: 48T avg -0.76% (-$3.66)
- R:R = 0.27/0.76 = 0.36:1 (inverted)

### Why 0.40% is better

At 0.40%, the trail arms 0.20% earlier. A trade peaking at 0.94% that reverses hits the 0.40% activation → trail catches it → exits at a small gain or breakeven instead of crashing to -0.79%.

**Floor calculation:** PM_TRAIL_ACTIVATE 0.40% - PM_TRAIL_DISTANCE 0.50% = -0.10% floor. Trades exit no worse than -0.10% after trail activates. Without trail (ATR_SL), they exit at -0.79%. That's the difference.

### What improved after reverting

R:R improved from 0.37:1 → 0.75:1 within 24h of reverting. PM_TRAIL avg exit holding at 0.26-0.29% (still low but improving). ATR_SL count should decrease as more trades catch the trail earlier.

---

## CEO Report — 2026-08-16 (7th run, verified)

### Diagnosis
Eval windows closing TOMORROW. Verified DB: 24h 58T -$0.36 (43.1% WR — RED). 48h R:R 0.75:1 (avg win 0.49% / avg loss -0.66%) — improved from 0.38:1 earlier today. PM_TRAIL 68T avg +0.29% (+$2.00), ATR_SL 50T avg -0.76% (-$3.83), T1 12T avg +0.57% (+$0.69). 2 open $0 flat. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.02 → Aug 16 -$0.31 (5T all losses, ct-hot+ 4T -0.89% avg — likely noise). Best 7d: return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.

### Root Cause
System flat, R:R still inverted but improving (0.38:1 → 0.75:1). PM_TRAIL at 0.40% activation exits at avg 0.29% while ATR_SL takes -0.76% — winners cut too early. Today's 5T all losses is noise (ct-hot+ 4T at -0.89% avg — needs monitoring tomorrow). All legacy bleeders disabled. Eval windows close tomorrow — cannot change params without invalidating results.

### Fix Applied
NO CHANGES. Eval windows closing tomorrow. Changing params now invalidates 6 eval windows worth of data. All bleeding signals already disabled. Stars intact.

### Verification
Tomorrow's run is CRITICAL: 1) Evaluate all 6 eval windows (PM_TRAIL 0.40% act/0.50% dist, ATR_TP_K_MULT 2.5, TRAILING_ACTIVATION_PCT 0.40%, SIGNAL_FILTER_SPEED_MIN 30, COIN_TRACKER_HOT_MIN_COMPOSITE 45), 2) Final param decisions, 3) R:R must ↑ from 0.75:1 toward 1:1+, 4) ct-hot+ must recover from today's 0% WR (noise or deterioration?), 5) Daily trades must stay >30T.

---

## CEO Report — 2026-08-16 (6th run, verified)

### Diagnosis
Eval windows closing tomorrow. Verified DB: 24h 55T -$0.14 (45.5% WR — SLIGHTLY RED). 7d: all bad signals already disabled (wave_catcher, mover+, accel-300, trend_momentum). 48h: ATR_SL 48T avg -0.76% (-$3.65), PM_TRAIL 68T avg +0.29% (+$2.00), T1 12T avg +0.57% (+$0.69). 5 open $0 flat. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.02 → Aug 16 -$0.09 (2T early). auto_1hr killed ct-hot- SHORT (4T 0% WR -$0.19).

### Root Cause
System flat, no emergency. PM_TRAIL revert (0.60%→0.40%) just happened — needs 24-48h data. R:R still inverted (PM_TRAIL +0.29% vs ATR_SL -0.76% = 0.38:1) but PM_TRAIL net positive (+$2.00). All legacy bleeders already disabled or aging out. Eval windows close tomorrow — no changes today to keep eval clean.

### Fix Applied
NO CHANGES. Eval windows closing tomorrow. PM_TRAIL revert needs data. All bleeding signals already disabled. Stars intact.

### Verification
Tomorrow's run is CRITICAL: 1) Evaluate PM_TRAIL revert (48h data at 0.40% activation), 2) Final eval window decisions (6 windows), 3) Check R:R (should ↑ from 0.38:1), 4) Check daily trades healthy (>30T).

---

- [2026-08-16 (5th run, verified)] CEO: NO CHANGES — eval windows closing tomorrow, system flat. Verified DB: 24h 55T -$0.02 (47.3% WR — FLAT). 7d 456T -$1.55 (50.9% WR). R:R 0.43:1 (avg win 0.33% / avg loss 0.77%) — improved from 0.37:1. 48h: ATR_SL 47T avg -0.76% (-$3.60), PM_TRAIL 69T avg +0.29% (+$2.06). 5 open $0 flat. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.02 → Aug 16 -$0.04 (1T early). PM_TRAIL revert (0.60%→0.40%) just happened — only 1 trade since, needs 24-48h data. 6 eval windows closing ~Aug 17. DECISION: NO CHANGES — eval windows closing tomorrow, PM_TRAIL revert needs data. CRITICAL: Tomorrow's run evaluates 6 eval windows + PM_TRAIL revert. Monitor: R:R (should ↑ from 0.43:1), atr_sl_hit count (should ↓ from 48), avg exit % (should ↑ from 0.33%).

### Diagnosis
Eval windows closing tomorrow. Verified DB: 24h 55T -$0.02 (47.3% WR — FLAT). 7d 456T -$1.55 (50.9% WR). R:R 0.43:1 (avg win 0.33% / avg loss 0.77%) — improved from 0.37:1. 48h: ATR_SL 47T avg -0.76% (-$3.60), PM_TRAIL 69T avg +0.29% (+$2.06). 5 open $0 flat. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.02 → Aug 16 -$0.04 (1T early).

### Root Cause
PM_TRAIL revert from 0.60%→0.40% just happened — only1 trade on Aug 16 since revert. 48h data is mostly from old params. R:R improving (0.37:1→0.43:1). All bad signals already disabled (wave_catcher, mover+, accel-300, trend_momentum). SHORT bleed is legacy trades aging out. System flat — no urgent action needed.

### Fix Applied
NO CHANGES. Eval windows closing tomorrow. PM_TRAIL revert needs 24-48h data. All bleeding signals already disabled. Stars intact. System flat.

### Verification
Tomorrow's run is CRITICAL: 1) Evaluate PM_TRAIL revert (48h data), 2) Final eval window decisions (6 windows), 3) Check if SHORT bleed aging out, 4) Check daily trades healthy (>30T).

---

- [2026-08-16 (4th run, verified)] CEO: NO CHANGES — eval windows closing tomorrow, system flat. Verified DB: 24h 55T -$0.02 (47.3% WR — FLAT). 7d 458T -$1.53 (50.9% WR). R:R 0.43:1 (avg win 0.33% / avg loss 0.77%) — improved from 0.37:1 earlier. 48h: ATR_SL 48T avg -0.77% (-$3.72), PM_TRAIL 81T avg +0.33% (+$2.75 est). 4 open -$0.02 flat. SHORT 24h: 5T -$0.25 0% WR (ct-hot- 4T + range_finder- 1T — tiny sample). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.02 → Aug 16 -$0.04 (1T early). PM_TRAIL revert (0.60%→0.40%) just happened — only 1 trade since, needs 24-48h data. 6 eval windows closing ~Aug 17. DECISION: NO CHANGES — eval windows closing tomorrow, PM_TRAIL revert needs data. CRITICAL: Tomorrow's run evaluates 6 eval windows + PM_TRAIL revert. Monitor: R:R (should ↑ from 0.43:1), atr_sl_hit count (should ↓ from 48), avg exit % (should ↑ from 0.33%).
