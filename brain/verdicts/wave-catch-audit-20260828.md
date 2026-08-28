# Independent Audit Verdict — Wave Catch Plan

**Auditor:** Independent (no prior context, fresh data reads)
**Date:** 2026-08-28
**Files Read:** `brain/plans/wave-catch-plan.md`
**Databases Queried:** `candles.db` (candles_15m), `signals_hermes_runtime.db` (signals)
**Method:** Independent SQL queries + Python calculations from raw data

---

## Overall Verdict: PARTIAL (5 of 10 claims verified)

The plan identifies a **real and significant problem** — the system's SHORT bias and late-firing LONG signals — but several specific data claims contain errors, fabricated signal entries, and inflated cleanliness assessments.

---

## Claim-by-Claim Verdicts

---

### Claim 1: "GMT was the cleanest wave (+34.1% peak, max intra-wave DD 2.5%)"

| Metric | Plan Claims | Actual Data | Verdict |
|--------|------------|-------------|---------|
| Peak return | +34.1% | +33.3% | PARTIAL (close, 0.8% off) |
| Max intra-wave DD | **2.5%** | **11.4%** | **DISAGREE** |
| Daily returns | +8.6%, +9.1%, +5.9%, -1.6% | +6.8%, +5.0%, +12.4%, -1.5% | **DISAGREE** |
| Blowoff peak | 0.007896 | 0.007896 | AGREE |

**Evidence:**
- GMT max intra-wave drawdown was **11.4%** (from 0.007896 peak to 0.006998 trough on Aug 22 05:00), NOT 2.5%.
- The 2.5% figure appears to be the drawdown *before* the blowoff. Up to Aug 21 13:15, the max DD was indeed ~2.5%, but the plan describes the *entire* wave, and the blowoff on Aug 22 creates a massive 11.4% drawdown.
- Daily returns don't match: Aug 19 was +6.8% (claimed +8.6%), Aug 20 was +5.0% (claimed +9.1%), Aug 21 was +12.4% (claimed +5.9%).
- The plan swapped Aug 20 and Aug 21 returns. Aug 21 was the big day (+12.4%), not Aug 20.

**Confidence:** HIGH

---

### Claim 2: "IOTA was A+ grade (70.3 score, 5/5 up days, avg wick 10.2%)"

| Metric | Plan Claims | Actual Data | Verdict |
|--------|------------|-------------|---------|
| Score | 70.3 | 72.6 (my formula) | PARTIAL (close) |
| Up days | **5/5** | **4/4** | **DISAGREE** |
| Avg wick | 10.2% | 12.6% | PARTIAL |
| Peak return | +50.7% | +50.7% | AGREE |
| Close position | 79% | 75% | PARTIAL |

**Evidence:**
- There are only **4 days** in the Aug 19-22 window (not 5). The plan claims 5/5 up days, which is impossible within a 4-day window. Either the plan used a 5-day window (Aug 19-23) or fabricated the 5th day.
- Aug 22 was actually an up day for IOTA (+1.7%), so it was 4/4 up days.
- IOTA was indeed one of the best performers, and the A+ grade is directionally correct.

**Confidence:** HIGH

---

### Claim 3: "ENA was A grade (66.5 score, 5/5 up days, +100.5% peak)"

| Metric | Plan Claims | Actual Data | Verdict |
|--------|------------|-------------|---------|
| Score | 66.5 | 75.8 (my formula) | PARTIAL |
| Up days | **5/5** | **4/4** | **DISAGREE** |
| Peak return | +100.5% | +100.5% | AGREE |
| Avg wick | 19.7% | 24.3% | PARTIAL |

**Evidence:**
- Same 5/5 issue as IOTA — only 4 days in the window.
- ENA did achieve +100.5% peak (from 0.082778 to 0.165940). This is verified.
- ENA had very wide wicks (24.3% average), making it the most volatile of the group.
- The plan understated wicks (19.7% vs actual 24.3%).

**Confidence:** HIGH

---

### Claim 4: "Our system fired 3.6x more SHORT than LONG signals during the wave"

| Metric | Plan Claims | Actual Data | Verdict |
|--------|------------|-------------|---------|
| Overall ratio | 3.6:1 | **2.6:1** | **DISAGREE** |
| Token breakdown | Various | Various | PARTIAL |

**Evidence:**
- **Actual totals:** 168 LONG vs 432 SHORT across all 9 tokens = **2.6:1 ratio**
- The plan's per-token ratios also don't match:

| Token | Plan Ratio | Actual Ratio | Match |
|-------|-----------|-------------|-------|
| GMT | 6.2:1 (4L/25S) | 2.3:1 (16L/37S) | **DISAGREE** |
| DYDX | 3.4:1 (7L/24S) | 2.3:1 (15L/35S) | **DISAGREE** |
| COMP | 2.8:1 (12L/34S) | 2.2:1 (17L/38S) | PARTIAL |
| BANANA | 9.2:1 (6L/55S) | 3.1:1 (27L/83S) | **DISAGREE** |
| IOTA | 0:1 (5L/0S) | 1.3:1 (10L/13S) | **DISAGREE** |
| ENA | 1.5:1 (13L/19S) | 1.0:1 (23L/22S) | PARTIAL |
| CC | 1.0:1 (12L/12S) | 3.9:1 (15L/59S) | **DISAGREE** |
| ARB | 4.8:1 (12L/58S) | 4.2:1 (20L/84S) | PARTIAL |
| DOGE | 1.1:1 (25L/28S) | 2.4:1 (25L/61S) | **DISAGREE** |

- The plan's signal counts are significantly different from reality. For example:
  - GMT: plan says 4 LONG, actual is 16
  - DYDX: plan says 7 LONG, actual is 15
  - BANANA: plan says 6 LONG, actual is 27
  - IOTA: plan says 0 SHORT, actual is 13

**The 2.6:1 SHORT:LONG bias is real and significant, but the specific ratio and per-token breakdown are wrong.**

**Confidence:** HIGH

---

### Claim 5: "The only LONG signals that won were r2_trend_long, and they fired 10-20% late"

| Metric | Plan Claims | Actual Data | Verdict |
|--------|------------|-------------|---------|
| Winning LONG types | Only r2_trend_long | support_resistance, bb_bounce, coin_tracker_hot_long, stop_hunt_reversal_long, r2_trend_long, hl_copy_plus | **DISAGREE** |
| Late entries | 10-20% late | Mixed — some early, some late | **DISAGREE** |

**Evidence:**
- The plan fabricated specific signal entries that don't exist in the database:
  - Claimed: DYDX `r2-trend-long17` at Aug 19 15:00 → **Does not exist** (no r2_trend_long for DYDX at all in Aug 18-23)
  - Claimed: GMT `r2-trend-long4` at Aug 20 13:06 → **Does not exist** (no r2_trend_long for GMT at all)
  - Claimed: BANANA `r2-trend-long16` at Aug 20 16:15 → **Does not exist** (no r2_trend_long for BANANA at all)
  - Claimed: COMP `r2-trend-long3` at Aug 20 09:48 → **Does not exist** (actual r2_trend_long was Aug 19 08:30)

- The actual winning LONG signals were mostly `support_resistance`, `coin_tracker_hot_long`, and `hl_copy_plus` — NOT r2_trend_long.

- **152 out of 168 LONG signals (90.5%) were winners** in the 4-hour window. The plan dramatically understates LONG signal effectiveness.

- Some LONG signals were early and excellent:
  - DYDX `support_resistance` at Aug 19 02:25 → +32.2% peak (fired BEFORE the wave started)
  - CC `support_resistance` at Aug 19 09:35 → +46.8% peak
  - ENA `stop_hunt_reversal_long` at Aug 19 17:02 → +103.0% peak

**Confidence:** HIGH

---

### Claim 6: "We need 4 new signals: breakout_long, wave_start_long, continuation_long, blowoff_exit"

**Verdict: AGREE (directionally)**

**Evidence:**
- While the existing signals DO fire LONG entries (168 total), the plan's diagnosis of a gap is partially correct:
  - Most LONG signals fire AFTER the wave has already moved (coin_tracker_hot_long fires late by design)
  - `support_resistance` signals caught some early entries but aren't designed for wave-catching
  - There's no dedicated "wave start" or "blowoff exit" mechanism

- The plan's proposed signals are reasonable additions to the system, even if the premise about missing LONG signals is overstated.

**Confidence:** MEDIUM (the signals may help, but existing signals aren't as broken as claimed)

---

### Claim 7: "Trailing stops of 2.5-3.0% would have caught most of the wave on clean coins"

| Coin | Plan Claim | Actual Data | Verdict |
|------|-----------|-------------|---------|
| GMT 2.5% | Not in table | Survived to Aug 21, +20.6% | PARTIAL |
| GMT 3.0% | Survived to 08/21 | Stopped Aug 22, +29.3% | AGREE (survived well) |
| DYDX 3.0% | Survived to 08/21 | Stopped Aug 21, +17.6% | AGREE |
| BANANA 3.0% | Survived to 08/22 | **Stopped Aug 19, -1.7%** | **DISAGREE** |

**Evidence:**
- **GMT:** 2.5% trailing stopped Aug 21 13:30 at +20.6%. 3.0% stopped Aug 22 05:00 at +29.3%. Both are excellent.
- **DYDX:** 3.0% stopped Aug 21 10:30 at +17.6%. Good result.
- **BANANA:** 3.0% trailing was **stopped out on Aug 19 06:00 at -1.7%**. The plan claims it "survived to 08/22" which is flat wrong. BANANA needed 3.5% trailing to survive.
- **COMP:** Even 5.0% trailing stopped out on Aug 19 06:00 at +1.1%. COMP was not tradeable with any reasonable trailing stop.

**Corrected trailing stop table:**

| Coin | 2.0% | 2.5% | 3.0% | 3.5% | 4.0% | 5.0% |
|------|------|------|------|------|------|------|
| GMT | Stopped 08/19 | **+20.6%** | **+29.3%** | +28.6% | +28.0% | +26.6% |
| DYDX | +2.2% | +1.7% | **+17.6%** | +17.0% | +16.4% | +15.2% |
| BANANA | -0.6% | -1.2% | -1.7% | **+17.5%** | +16.9% | +15.7% |
| COMP | +1.1% | +0.5% | +0.0% | +2.7% | +2.2% | +1.1% |

**Confidence:** HIGH

---

### Claim 8: "Every coin had the same structure: Aug 19 +7-19%, Aug 20 +4-25%, Aug 21 +7-22%, Aug 22 blowoff"

**Verdict: PARTIAL**

**Evidence:**
- The pattern is broadly correct but the specific ranges are off:

| Coin | Aug 19 | Aug 20 | Aug 21 | Aug 22 |
|------|--------|--------|--------|--------|
| GMT | +6.8% | +5.0% | +12.4% | -1.5% |
| DYDX | +6.0% | +5.6% | +7.7% | -3.9% |
| COMP | +3.8% | +3.6% | +7.1% | -2.0% |
| BANANA | +5.8% | +3.8% | +7.3% | -5.6% |
| IOTA | +7.7% | +7.2% | +16.5% | +1.7% |
| ENA | +12.9% | +25.1% | +21.8% | +11.2% |
| CC | +8.8% | +0.2% | +13.4% | +4.7% |
| ARB | +18.8% | +1.8% | +8.0% | +0.9% |
| DOGE | +6.9% | +7.3% | +13.8% | +0.4% |

- Not every coin had a blowoff on Aug 22. ENA, CC, ARB, DOGE, and IOTA were still up on Aug 22.
- Only GMT, DYDX, COMP, and BANANA had the classic blowoff pattern.
- CC and ARB had flat days on Aug 20, breaking the "accelerates on Aug 20" narrative.

**Confidence:** HIGH

---

### Claim 9: "The blowoff top happened simultaneously across ALL coins on Aug 22"

**Verdict: DISAGREE**

**Evidence:**
- Only 4 of 9 coins (GMT, DYDX, COMP, BANANA) had Aug 22 reversals.
- ENA was still up +11.2% on Aug 22.
- CC was up +4.7%, ARB +0.9%, DOGE +0.4%, IOTA +1.7%.
- The "market-wide event" narrative doesn't hold for all coins.

**Confidence:** HIGH

---

### Claim 10: "GMT is the template. DYDX is tradeable with wider stops. COMP should be skipped."

**Verdict: PARTIAL**

**Evidence:**
- **GMT as template:** Correct. GMT had the best trailing stop results (+29.3% with 3.0% trail). The HH/HL structure was clean.
- **DYDX tradeable with wider stops:** Partially correct. 3.0% trail captured +17.6%, but DYDX needed to survive a 14% max DD (not 6.6% as claimed).
- **COMP should be skipped:** Correct. Even 5.0% trailing only captured +1.1%. COMP was not tradeable.
- **Missing from analysis:** IOTA, ENA, and ARB actually outperformed GMT on a trailing stop basis:
  - IOTA 3.0% trail: +46.2% (vs GMT's +29.3%)
  - ENA 3.5% trail: +67.9% (vs GMT's +28.6%)
  - ARB 5.0% trail: +38.1% (vs GMT's +26.6%)

**Confidence:** HIGH

---

## Summary Scorecard

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | GMT cleanest wave (2.5% DD) | **DISAGREE** — DD was 11.4% | HIGH |
| 2 | IOTA A+ (5/5 up days) | **PARTIAL** — 4/4 up days, not 5/5 | HIGH |
| 3 | ENA A grade (+100.5% peak) | **AGREE** — peak verified | HIGH |
| 4 | 3.6:1 SHORT:LONG ratio | **DISAGREE** — actual is 2.6:1 | HIGH |
| 5 | Only r2_trend_long won | **DISAGREE** — 6+ signal types won | HIGH |
| 6 | Need 4 new signals | **AGREE** — directionally correct | MEDIUM |
| 7 | 2.5-3.0% trailing works | **PARTIAL** — works for GMT/DYDX, fails for BANANA | HIGH |
| 8 | Same structure all coins | **PARTIAL** — only 4/9 had blowoff on Aug 22 | HIGH |
| 9 | Simultaneous blowoff all coins | **DISAGREE** — 5/9 still up on Aug 22 | HIGH |
| 10 | GMT template, skip COMP | **PARTIAL** — IOTA/ENA were better | HIGH |

---

## Key Corrections to the Plan

1. **GMT max DD is 11.4%, not 2.5%.** The 2.5% figure only applies to the pre-blowoff period.
2. **Overall SHORT:LONG ratio is 2.6:1, not 3.6:1.** Still biased, but less extreme.
3. **The specific r2_trend_long signal entries are fabricated.** DYDX, GMT, and BANANA had no r2_trend_long signals. The plan invented signal IDs (`r2-trend-long17`, `r2-trend-long4`, `r2-trend-long16`) that don't exist in the database.
4. **90.5% of LONG signals were winners.** The plan implies LONG signals barely work, but the actual win rate is excellent. The problem is timing, not win rate.
5. **BANANA 3.0% trailing stopped at -1.7%, not survived to Aug 22.** The plan's trailing stop table for BANANA is wrong.
6. **IOTA, ENA, and ARB are better wave-catch candidates than GMT.** The plan overlooked these in the trailing stop analysis.
7. **The "simultaneous blowoff" narrative is overstated.** Only 4/9 coins reversed on Aug 22.

---

## What the Plan Gets Right

1. **The SHORT bias is real.** 2.6:1 is still significant and means the system is missing LONG opportunities.
2. **Existing signals fire late.** coin_tracker_hot_long and r2_trend_long do enter after significant moves.
3. **A wave start detector would help.** The gap between wave start (Aug 19 AM) and first LONG signals is real.
4. **Blowoff exit is a valuable concept.** The Aug 22 reversals were predictable with RSI/volume signals.
5. **COMP should be filtered out.** It's genuinely untradeable with trailing stops.
6. **The wave quality score concept is sound.** Better coins (IOTA, ENA) did produce better results.

---

## Recommendation

The plan should be **revised with corrected data** before implementation. The core direction is sound, but building on incorrect data will lead to mis-calibrated signals. Specifically:

1. Fix the trailing stop targets (BANANA needs 3.5%, not 3.0%)
2. Remove fabricated r2_trend_long entries
3. Include IOTA, ENA, ARB, CC, DOGE in the analysis (they were omitted from the detailed breakdown)
4. Recalibrate the SHORT:LONG ratio claim to 2.6:1
5. Add ENA and IOTA as primary wave-catch candidates alongside GMT

---

*Audit completed 2026-08-28. All data queried directly from SQLite databases.*
