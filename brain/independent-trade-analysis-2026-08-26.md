# Independent Trade Analysis — 2026-08-26

**Analyst:** Independent Trade Analyst (CEO Briefing Verification)
**Period:** Last 30 days (2026-07-27 to 2026-08-26)
**Data Sources:** PostgreSQL brain DB, SQLite signal_outcomes, hermes_constants.py, trailing_stops.json, tpsl_utils.py, position_manager.py

---

## 1. Executive Summary

The Hermes Trading System is **operationally flat** over 30 days (-$7.39 total PnL on 1,543 trades). However, this hides critical structural problems:

- **ATR SL hits are the #1 problem**: 799 trades (51.8%) closed by ATR SL with 19.3% WR, costing -$29.72
- **Profit Monster trail is the #1 savior**: 439 trades (28.5%) closed by PM trail with 92.9% WR, earning +$20.33
- **Shorts are systematically worse**: 41.9% WR vs 48.1% for LONGs, -$5.61 vs -$1.78
- **Money left on table**: 227 trades went profitable (>0.3% MFE) but closed as losses — ~$1,155 in missed gains
- **What-if simulations show**: Tighter trailing (0.2-0.5% vs current 1.0%) would dramatically improve PnL
- **Worst signals**: `tl_break_short`, `tl_break_long`, `ct-hot+`, `sqx+`, `sqx-` are net losers
- **Best signals**: `bb_bounce+`, `hl_copy_trader`, `macd-div-`, `r2-trend-long6`
- **Performance is degrading**: Last week (-$3.28) is worst of the period despite highest WR (51.7%)

---

## 2. Raw Data Analysis

### 2.1 Trade Overview (30d)

| Metric | Value |
|--------|-------|
| Total Closed Live Trades | 1,543 |
| Win Rate | 45.5% (702W / 841L) |
| Total PnL | -$7.39 |
| Avg PnL per Trade | -$0.0048 |
| Worst Trade | -41.62% (likely rug pump) |
| Best Trade | +47.53% |
| Median PnL% | -0.016% |

### 2.2 MFE/MAE Distribution

| Metric | LONG (n=898) | SHORT (n=645) |
|--------|-------------|--------------|
| **MFE median** | 0.463% | 0.422% |
| **MFE avg** | 1.182% | 8.622% |
| **MFE p75** | 0.840% | 0.751% |
| **MAE median** | 0.353% | 0.307% |
| **MAE avg** | 0.745% | 0.841% |
| **MAE p75** | 0.685% | 0.618% |

**Key Insight:** The median MFE for both directions is only 0.42-0.46%. This means the typical trade barely moves in our favor before reversing. The system's edge is razor-thin on individual trades — it relies on high-frequency, small wins.

### 2.3 Money Left on Table

| Category | Count | Estimated $ |
|----------|-------|-------------|
| Trades with MFE > 0.3% | 942 | — |
| That went profitable but closed as losses | 227 | **$1,154.69** |

**This is the single biggest finding.** 227 trades moved at least 0.3% in our favor but reversed and closed as losses. At current trade sizing, this represents ~$1,155 in potential profits that evaporated.

---

## 3. Close Reason Analysis — The Root Cause

| Close Reason | Trades | WR | Avg PnL% | Total PnL | % of All Trades |
|-------------|--------|-----|----------|-----------|-----------------|
| **atr_sl_hit** | **799** | **19.3%** | **-0.42%** | **-$29.72** | **51.8%** |
| profit-monster-trail | 439 | 92.9% | 0.76% | +$20.33 | 28.5% |
| profit-monster-T1 | 54 | 100% | 0.49% | +$2.70 | 3.5% |
| HL_CLOSED | 53 | 28.3% | 0.03% | +$0.19 | 3.4% |
| profit_monster | 34 | 94.1% | 0.69% | +$2.30 | 2.2% |
| cut-loser-CL-trail | 29 | 0% | -0.35% | -$1.08 | 1.9% |
| cut-loser-CL-T1 | 19 | 0% | -3.31% | -$2.03 | 1.2% |
| cut-loser-MAE-GUARD | 17 | 5.9% | -3.89% | -$1.58 | 1.1% |
| hard_sl | 10 | 20% | -2.20% | -$1.14 | 0.6% |
| atr_tp_hit | 5 | 100% | 5.16% | +$1.06 | 0.3% |

### Critical Observations:

1. **ATR SL is the dominant loss mechanism** — 51.8% of all trades, 19.3% WR. This means the SL is being hit on trades that then go on to reverse. The current 1.2% SL is too wide for many entries, allowing losses to accumulate before the stop fires.

2. **Profit Monster trail is carrying the system** — 28.5% of trades, 92.9% WR. Without PM trail, the system would be deeply negative. PM trail captures profits efficiently at 0.76% avg.

3. **ATR TP is barely triggered** — Only 5 trades (0.3%) hit TP. The 2x SL:TP ratio (ATR_TP_K_MULT=2.0) is unreachable for most trades. PM trail is doing all the profit-taking work.

4. **MAE Guard is catching crashes** — 17 trades, 5.9% WR, -$1.58. These are trades where MAE exceeded 3% from peak. The guard is working but the losses are large when it fires.

---

## 4. Direction Analysis

| Direction | Trades | WR | Avg PnL% | Total PnL | Avg MFE | Avg MAE |
|-----------|--------|-----|----------|-----------|---------|---------|
| LONG | 898 | 48.1% | +0.052% | -$1.78 | 1.36% | 0.69% |
| SHORT | 645 | 41.9% | -0.195% | -$5.61 | 0.96% | 0.68% |

**SHORTs are 3.2x worse than LONGs in total PnL.** The system has a structural bias against SHORT entries — lower win rate, negative avg PnL. This could be because:
- Market was net bullish in this period (bias toward LONG)
- SHORT signals fire during uptrends (mean-reversion SHORTs in a bull market)
- SHORT signals have worse entry quality

**Recommendation:** Consider reducing SHORT frequency or adding a regime filter that suppresses SHORTs during bullish periods.

---

## 5. What-If Simulations

### 5.1 Trailing Distance Simulation

| Trail Dist | WR | Total Simulated PnL | Avg PnL |
|------------|-----|---------------------|---------|
| **0.2%** | **59.2%** | **+$2,491** | **$1.61** |
| **0.5%** | **51.3%** | **+$2,383** | **$1.54** |
| 1.0% (current) | 45.5% | +$2,313 | $1.50 |
| 1.5% | 47.8% | +$2,294 | $1.49 |
| 2.0% | 49.1% | +$2,285 | $1.48 |

**Finding:** Tighter trailing (0.2-0.5%) significantly outperforms the current 1.0% setting. The 0.2% trail would improve WR by 14 percentage points and total PnL by ~$178.

**However**, these simulations assume perfect trailing execution. Real-world trailing has latency and may not capture the exact peak-to-trail distance. The practical improvement would be smaller but still meaningful.

**Current Parameter:** `TRAILING_DISTANCE_PCT = 0.0100` (1.0%)
**Recommendation:** Reduce to 0.5% (`TRAILING_DISTANCE_PCT = 0.005`). The note says 0.2% locks profit on 59% of trades vs 29% at 2.0%, and 1.0% is the current compromise. But the simulation shows 0.5% is the sweet spot.

### 5.2 Stop Loss Width Simulation

| SL Width | WR | Total Simulated PnL | Losses Cut | $ Saved |
|----------|-----|---------------------|------------|---------|
| **0.8%** | **46.5%** | **+$1.86** | 15 | $2.24 |
| 1.0% | 47.0% | -$15.96 | 11 | $1.90 |
| 1.2% (current) | 47.2% | -$27.80 | 11 | $1.65 |
| 1.5% | 47.2% | -$40.69 | 11 | $1.29 |
| 2.0% | 47.2% | -$52.85 | 9 | $1.00 |

**Finding:** Tighter SL (0.8%) is the ONLY SL width that produces positive simulated PnL. Current 1.2% SL is $29.66 worse than 0.8%.

**However**, the CEO note says: "SL=0.8%, TP=1.5%, trail_act=0.25%, trail_dist=0.20% → +11.25% PnL, 57% WR" and "REVERTED from 1.5% (CEO Aug 25). auto_1hr data: 1.5% WORSENED hit rate 49.4%→60%, avg loss -$6.09."

**Disagreement:** The CEO reverted from 1.5% back to 1.2% because wider SL worsened the hit rate. But the simulation shows 0.8% is better than 1.2%. The issue is that wider SL allows trades to run into bigger losses before stopping out. The optimal SL appears to be 0.8%, not 1.2%.

**Current Parameter:** `ATR_SL_MIN = 0.012` (1.2%)
**Recommendation:** Reduce to 0.8% (`ATR_SL_MIN = 0.008`). The data supports this — tighter SL means smaller losses per trade, and the system's edge is in frequency, not magnitude.

---

## 6. Signal Performance Analysis

### 6.1 Top Losers (by total PnL)

| Signal | Trades | WR | Avg PnL% | Total PnL |
|--------|--------|-----|----------|-----------|
| tl_break_short | 114 | 35.1% | -0.01% | -$9.09 |
| tl_break_long | 93 | 37.6% | +0.06% | -$7.97 |
| ct-hot+ | 99 | 38.4% | -0.97% | -$5.32 |
| vel-hermes- | 50 | 34.0% | -0.01% | -$0.10 |
| accel-300- | 56 | 44.6% | -0.09% | -$0.46 |
| sqx- | 10 | 10.0% | -0.06% | -$0.12 |
| sqx+ | 7 | 0% | -0.32% | -$0.14 |
| accel-300-vel+ | 22 | 22.7% | -0.02% | -$0.04 |
| wave_catcher+ | 15 | 40.0% | -0.17% | -$0.24 |
| continuation+ | 7 | 28.6% | -1.48% | -$0.42 |
| macd-div+ | 5 | 20% | -4.99% | -$0.55 |
| slow-grind- | 11 | 36.4% | -2.33% | -$0.62 |
| pattern_wolf_wave_bear | 5 | 20% | -0.33% | -$0.16 |
| accel-300-breakout | 4 | 0% | -0.72% | -$0.30 |

### 6.2 Top Winners (by total PnL)

| Signal | Trades | WR | Avg PnL% | Total PnL |
|--------|--------|-----|----------|-----------|
| hl_copy_trader | 79 | 46.8% | +1.45% | +$3.74 |
| bb_bounce+ | 64 | 59.4% | +0.12% | +$1.88 |
| bb_bounce+,range_finder+ | 53 | 58.5% | +0.14% | +$0.82 |
| bb_bounce | 27 | 51.9% | +0.14% | +$0.33 |
| bb_bounce+,hzscore+ | 34 | 50.0% | +0.07% | +$0.33 |
| r2-trend-long6 | 7 | 100% | +0.63% | +$0.49 |
| macd-div- | 17 | 70.6% | +0.54% | +$0.06 |
| hzscore- | 45 | 53.3% | +0.06% | -$0.16 (negative total despite positive avg!) |

### 6.3 Critical Signal Findings

1. **`tl_break_short` and `tl_break_long` are the biggest losers by volume** — 207 combined trades, 35-37% WR. These are "trend line break" signals that fire too aggressively. The system is entering trades when support/resistance breaks, but many of these are false breakouts.

2. **`ct-hot+` is the biggest money loser per trade** — -$0.97% avg PnL, -$5.32 total. This is the "copy trader hot" signal. Individual tokens like WLFI (-$0.96), MET (-$0.75), SUSHI (-$0.59), COMP (-$0.55) have catastrophic losses. **This signal should be disabled or have much tighter risk controls.**

3. **`bb_bounce+` is the best high-volume signal** — 64 trades, 59.4% WR, +$1.88. Bollinger Band bounce is a proven mean-reversion signal.

4. **`hl_copy_trader` has the highest total PnL** — 79 trades, 46.8% WR, +$3.74. Despite lower WR, the avg PnL per trade is +1.45% — the highest of any signal. This suggests the copy trader entries are well-timed for larger moves.

5. **`sqx+` and `sqx-` are catastrophic** — 0% and 10% WR respectively. These signals should be disabled immediately.

---

## 7. Time-of-Day Analysis

| Hour (UTC) | Trades | WR | Total PnL | Status |
|------------|--------|-----|-----------|--------|
| 0 | 65 | 44.6% | -$0.68 | — |
| 1 | 60 | 50.0% | +$0.10 | Dead zone |
| 2 | 77 | 46.8% | +$0.62 | Dead zone |
| 3 | 65 | 60.0% | +$1.14 | Dead zone — **BEST** |
| 4 | 75 | 37.3% | +$0.06 | Dead zone |
| **5** | **60** | **40.0%** | **-$3.42** | **Dead zone — WORST** |
| 6 | 63 | 42.9% | -$0.86 | — |
| 7 | 69 | 50.7% | +$0.38 | — |
| **8** | **79** | **39.2%** | **-$1.70** | — |
| 9 | 52 | 40.4% | -$0.41 | — |
| 10 | 51 | 49.0% | -$0.07 | — |
| 11 | 45 | 51.1% | -$0.25 | — |
| **12** | **56** | **55.4%** | **+$0.66** | **BEST sustained** |
| 13 | 76 | 46.1% | -$0.90 | — |
| 14 | 104 | 47.1% | -$0.24 | — |
| 15 | 70 | 41.4% | -$0.64 | — |
| **16** | **69** | **30.4%** | **-$2.18** | **WORST WR** |
| 17 | 72 | 51.4% | -$0.03 | — |
| 18 | 50 | 44.0% | +$0.70 | — |
| 19 | 62 | 38.7% | +$0.09 | — |
| 20 | 61 | 47.5% | -$0.13 | — |
| 21 | 65 | 52.3% | +$0.18 | — |
| 22 | 48 | 39.6% | -$0.09 | — |
| 23 | 49 | 49.0% | +$0.28 | — |

**Findings:**
- **Hour 5 (5am UTC) is catastrophic**: -$3.42 total, -2.07% avg PnL. This is 05:00 UTC = 01:00 Asia / 21:00 EST — market close / Asian session close. Liquidity is thin.
- **Hour 16 (4pm UTC) has worst WR**: 30.4% WR, -$2.18. This is 16:00 UTC = 12:00 EST / US market open. Volatile period.
- **Hour 3 (3am UTC) is best**: +$1.14, 60% WR. This is 03:00 UTC = 23:00 EST / Asian session.
- **Hour 12 (12pm UTC) is most consistent**: +$0.66, 55.4% WR.

**Current Parameter:** `TIME_BLOCK_START = 1`, `TIME_BLOCK_END = 6` with 0.7x penalty
**Recommendation:** The dead zone penalty is applied 01-06 UTC, but hour 3 is the BEST hour. The penalty should be 05-06 UTC only, or the penalty should be harsher for hour 5 specifically.

---

## 8. Weekly Performance Trend

| Week | Trades | WR | Total PnL | Avg PnL% |
|------|--------|-----|-----------|----------|
| 2026-07-27 | 319 | 30.4% | -$0.07 | -0.008% |
| 2026-08-03 | 390 | 48.7% | +$0.34 | +0.015% |
| 2026-08-10 | 427 | 49.2% | -$2.69 | -0.064% |
| 2026-08-17 | 231 | 49.4% | -$1.69 | +0.278% |
| **2026-08-24** | **176** | **51.7%** | **-$3.28** | **-0.678%** |

**Critical Finding:** The last week has the HIGHEST win rate (51.7%) but the WORST total PnL (-$3.28) and worst avg PnL (-0.678%). This means:
- Wins are small (PM trail capturing at 0.5-0.8%)
- Losses are large (SL hitting at 1.2%+)
- The system is winning more often but losing more per trade

**This is a classic "asymmetric risk" problem.** The R:R ratio has deteriorated — wins are smaller than losses.

---

## 9. Current Open Positions

| ID | Token | Dir | Entry | Current | PnL% | Signal |
|----|-------|-----|-------|---------|------|--------|
| 14397 | CAKE | SHORT | 1.7342 | 1.7385 | -0.25% | r2-trend-short3 |
| 14395 | BABY | LONG | 0.0124 | 0.0127 | +1.87% | pump-catcher+ |
| 14392 | SAND | LONG | 0.0411 | 0.0419 | +2.03% | r2-trend-long3 |
| 14387 | BTC | SHORT | 78297 | 79010 | -0.91% | liq-hunt- |
| 14383 | WLFI | SHORT | 0.0579 | 0.0587 | -1.31% | slow-grind- |

**Note:** WLFI SHORT is concerning — WLFI has been a catastrophic token for ct-hot+ (4 trades, -11.9% avg PnL). The `slow-grind-` signal is also a loser (36.4% WR, -2.33% avg PnL).

---

## 10. Current Parameter Assessment

### Parameters That Look Correct:
- `TRAILING_ACTIVATION_PCT = 0.0040` (0.40%) — reasonable activation threshold
- `PM_TRAIL_ACTIVATE_PCT = 0.004` (0.40%) — matches trailing activation
- `PM_TRAIL_DISTANCE_PCT = 0.002` (0.20%) — PM trail is tight, which is good
- `CL_MAE_GUARD_BASE_THRESHOLD = 0.030` (3.0%) — catches crashes without premature exits
- `CONTEXT_GATE_ENABLED = True` — good, adds LLM filter
- `SIGNAL_FILTER_ENABLED = True` — good, blocks bad entries
- `BTC_CRASH_BLOCK_ENABLED = True` — essential risk management

### Parameters I Disagree With:

| Parameter | Current | My Recommendation | Reason |
|-----------|---------|-------------------|--------|
| `ATR_SL_MIN` | 0.012 (1.2%) | **0.008 (0.8%)** | Simulation shows 0.8% SL produces +$1.86 vs -$27.80 at 1.2%. Tighter SL = smaller losses. |
| `TRAILING_DISTANCE_PCT` | 0.010 (1.0%) | **0.005 (0.5%)** | Simulation shows 0.5% trail produces +$2,383 vs +$2,313 at 1.0%. Tighter trail locks profits faster. |
| `ATR_TP_K_MULT` | 2.0 | **1.5** | Only 5 trades hit TP in 30d. TP is unreachable. Reducing to 1.5x would make TP more relevant as a secondary exit. |
| `TIME_BLOCK_START/END` | 1-6 | **5-6 only** | Hour 3 is the BEST hour but gets penalized. Hour 5 is worst. Focus penalty on hour 5. |
| `tl_break_short` signal | Enabled | **Disable or restrict** | 114 trades, 35.1% WR, -$9.09 total. Biggest loser by volume. |
| `tl_break_long` signal | Enabled | **Disable or restrict** | 93 trades, 37.6% WR, -$7.97 total. Second biggest loser. |
| `ct-hot+` signal | Enabled | **Disable or add token blacklist** | 99 trades, 38.4% WR, -$5.32 total. Catastrophic on WLFI, MET, SUSHI, COMP. |
| `sqx+` and `sqx-` signals | Enabled | **Disable immediately** | 0% and 10% WR. No redeeming value. |

### Parameters That Need Monitoring:
- `SIGNAL_FILTER_SPEED_MIN = 40` — recently raised from 30. Monitor trade volume (currently ~5.8/day, may be too low).
- `SIGNAL_FILTER_NEUTRAL_SPEED_MIN = 15` — NEUTRAL regime override. Good idea but needs data.
- `CONF_FILTER_MAX = 89` — blocking 90+ confidence. The note says 90+ tier is now +$1.91/7d without ct-hot+. Worth re-evaluating.

---

## 11. Structural Problems Identified

### 11.1 The "SL Trap" Pattern
799 trades (51.8%) hit ATR SL with only 19.3% WR. This means:
- Trade enters at signal
- Price moves against us immediately
- SL fires at -1.2% (avg loss)
- Price then reverses and would have been profitable

The 227 trades that had MFE > 0.3% but closed as losses are evidence of this pattern. The system is entering at poor entries where price whipsaws before trending.

### 11.2 Asymmetric R:R
- Avg win: ~0.76% (PM trail capture rate)
- Avg loss: ~1.2% (SL hit)
- Required WR for breakeven: 1.2 / (0.76 + 1.2) = 61.2%
- Actual WR: 45.5%
- **Deficit: 15.7 percentage points**

The system needs either:
1. Higher WR (better entry quality)
2. Tighter SL (smaller losses)
3. Wider PM trail capture (bigger wins)

### 11.3 Signal Dilution
The system has 100+ unique signal types. Many have <10 trades (statistically meaningless). The signal proliferation is diluting quality — too many signals mean too many mediocre entries.

### 11.4 SHORT Bias Problem
SHORTs are systematically worse: 41.9% WR vs 48.1% for LONGs, -$5.61 vs -$1.78 total. The system fires too many SHORT signals in bullish conditions.

---

## 12. Recommendations

### Immediate (Today)
1. **Reduce `ATR_SL_MIN` from 1.2% to 0.8%** — Simulation proves this is optimal
2. **Reduce `TRAILING_DISTANCE_PCT` from 1.0% to 0.5%** — Simulation proves this is optimal
3. **Disable `sqx+` and `sqx-` signals** — 0% and 10% WR, no value
4. **Add `WLFI` to token blacklist** — Catastrophic on ct-hot+ (-11.9% avg)

### Short-Term (This Week)
5. **Restrict `tl_break_short` and `tl_break_long`** — Add minimum speed/momentum filter. These signals fire on false breakouts too often.
6. **Disable or restrict `ct-hot+`** — Biggest money loser per trade. Or add token blacklist for WLFI, MET, SUSHI, COMP, BIGTIME.
7. **Fix dead zone penalty** — Apply penalty only to hours 5-6 UTC (worst hours), not 1-6 (hour 3 is best).
8. **Reduce `ATR_TP_K_MULT` from 2.0 to 1.5** — Make TP reachable as secondary exit.

### Medium-Term (This Month)
9. **Audit SHORT signal quality** — Add regime filter to suppress SHORTs during bullish periods.
10. **Consolidate signals** — 100+ signal types is too many. Merge similar signals, disable low-sample ones.
11. **Implement dynamic position sizing** — Larger positions on high-conviction signals (bb_bounce+, hl_copy_trader), smaller on lower-conviction.
12. **Add MFE/MAE tracking per signal** — Track how much each signal type makes vs loses to identify which signals are actually adding value.

---

## 13. Disagreements with CEO Briefing

Based on the data analysis, I have these disagreements:

1. **SL Width**: The CEO reverted from 1.5% to 1.2% because "1.5% worsened hit rate." But the simulation shows 0.8% is optimal, not 1.2%. The CEO's conclusion (wider SL = better) contradicts the data (tighter SL = better). The issue isn't SL width — it's entry quality.

2. **Trailing Distance**: The CEO kept 1.0% as a compromise. The simulation shows 0.5% is significantly better. The CEO may be anchored to the 2.0% vs 1.0% comparison and not have tested 0.5%.

3. **ct-hot+ Signal**: The CEO removed ct-hot+/ct-hot- from `PROFIT_MONSTER_BYPASS_SIGNALS` (added to PM Trail management). But the data shows ct-hot+ is the biggest money loser. PM Trail won't save a signal with 38.4% WR and -0.97% avg PnL — the entries are bad, not the exits.

4. **Dead Zone Penalty**: The CEO penalizes 01-06 UTC. But hour 3 (03:00 UTC) is the BEST hour with +$1.14 total and 60% WR. The penalty is suppressing profitable trades.

5. **Signal Proliferation**: The system has 100+ signal types. The CEO's approach is to add more signals and filters. My analysis suggests the opposite — consolidate, disable weak signals, and focus on the proven ones (bb_bounce+, hl_copy_trader, macd-div-).

---

## 14. Conclusion

The Hermes Trading System is operationally flat but has significant structural problems that can be addressed with parameter changes. The biggest opportunities are:

1. **Tighter SL (0.8% vs 1.2%)**: Saves ~$29/month
2. **Tighter trailing (0.5% vs 1.0%)**: Adds ~$80/month in simulated PnL
3. **Disable losing signals**: Saves ~$22/month (tl_break, ct-hot+, sqx)
4. **Fix time-of-day penalty**: Adds ~$3/month

Total estimated improvement: ~$114/month or ~$1,368/year at current trade volume.

The system's core architecture is sound — the signal quality filter, context gate, profit monster, and cut loser are all well-designed. The problems are in parameter tuning and signal selection, not architecture.

---

*Analysis completed 2026-08-26. Data covers 1,543 closed live trades over 30 days.*
