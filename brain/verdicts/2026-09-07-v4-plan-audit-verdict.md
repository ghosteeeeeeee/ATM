# Independent Audit Verdict: Accel-300 V4 Killer Signal Plan

**Auditor:** Independent auditor (own-conclusions)
**Date:** 2026-09-07
**Data sources read:** `accel300_all_trades_analyzed.json` (204 trades), `accel300_short_detailed.json` (139 trades), `hermes_constants.py`, `decider_run.py`, `accel_300_v3_short.py`, plan file

---

## CRITICAL ISSUE: Data Source Mismatch

The plan claims regime breakdown from **294 trades** (EXTREME:116, HIGH:89, NORMAL:76, FLAT:13), but the JSON file `accel300_all_trades_analyzed.json` contains only **204 trades** (140 SHORT + 64 LONG), with regime counts of EXTREME:94, HIGH:65, NORMAL:36, FLAT:9 (for all directions) or EXTREME:47, HIGH:52, NORMAL:34, FLAT:7 (SHORT only).

**This means the plan was built on a different/larger dataset that is not provided for verification.** The 95 "missing" trades lack metadata (z, rsi, regime, pre15_move). This is a fundamental audit gap — I can only verify claims against the 204-trade file that was provided, and many of the plan's specific numbers (116, 89, 76, 13) cannot be independently confirmed.

---

## Claim 1: Block EXTREME + FLAT Regimes

**Verdict: PARTIAL**
**Confidence: MEDIUM**

**What was claimed:** "Removes 51W/65L (EXTREME) + 3W/6L (FLAT) → leaves 83W/43L = 66% WR baseline"

**Evidence from data:**
- In the 204-trade file, SHORT trades: EXTREME has 22W/25L (46.8%), FLAT has 2W/5L (28.6%)
- Combined EXTREME+FLAT removal: blocks 24W/30L = removing 54 trades
- After removal: 50W/36L = 58.1% WR (not 66% as claimed)
- **PnL is misleading:** EXTREME SHORT has +$1.28 PnL in this data (profitable!). Blocking it would HURT PnL

**Problem:** The plan says EXTREME has "44% WR, -$1.69 PnL" but this file shows 46.8% WR, +$1.28 PnL. The plan used a different dataset. In this data, EXTREME is actually net profitable for SHORT — blocking it removes a +$1.28 contributor.

**Assessment:** Regime blocking is directionally reasonable (EXTREME has lower WR than HIGH), but the PnL direction is WRONG in the plan. EXTREME is not the "biggest loser" in this data.

---

## Claim 2: z>0 Filter in HIGH Regime → 79% WR

**Verdict: AGREE (but even better than claimed)**
**Confidence: MEDIUM**

**What was claimed:** "catches 21L, blocks 15W → 79% WR (23W/6L)"

**Evidence from data:**
- HIGH regime SHORT trades: 52 total (32W/20L = 61.5% WR)
- z <= 0 (ALLOW): 24 trades → **23W/1L = 95.8% WR** (PnL: +$15.98)
- z > 0 (BLOCK): 28 trades → 9W/19L (PnL avoided: -$11.79)

**The filter works BETTER than claimed** — 95.8% WR vs claimed 79%. However, the claim of "23W/6L" doesn't match this data at all (it's 23W/1L). The plan was using different numbers.

**Statistical significance: 24 trades is below the 30-trade threshold.** The 95.8% WR is based on a very small sample. One additional loss would drop it to 92%.

**Overfitting risk: MEDIUM.** The z>0 boundary is clean (z is a continuous metric, and the threshold is logical — SHORT should be below EMA), but the sample is tiny.

---

## Claim 3: pre15>0 Filter in NORMAL Regime → 100% WR

**Verdict: DISAGREE (massive overfitting risk)**
**Confidence: HIGH**

**What was claimed:** "catches ALL 16 losses → 15W/0L = 100% WR"

**Evidence from data:**
- NORMAL regime SHORT trades: 34 total (18W/16L = 52.9% WR)
- pre15 <= 0 (ALLOW): 14 trades → **14W/0L = 100% WR** (PnL: +$6.32)
- pre15 > 0 (BLOCK): 20 trades → 4W/16L (PnL avoided: -$13.63)

The 100% WR is confirmed on this data, BUT:

**CRITICAL OVERFITTING EVIDENCE:**

1. **Sample size is only 14 trades.** This is nowhere near enough for statistical significance. A 100% WR on 14 trades has a 95% confidence interval of [77%, 100%] — meaning the TRUE win rate could be as low as 77%.

2. **Razor-thin boundary at zero.** One trade (INJ, pre15=+0.027%) is barely above the 0% cutoff. At 0.05% threshold, a loss appears (93.8% WR). At 0.15% threshold, WR drops to 84.2%.

3. **Boundary sensitivity table:**
   | Threshold | Blocked | Kept | WR |
   |-----------|---------|------|-----|
   | > 0.00% | 20 | 14 | 100.0% |
   | > 0.05% | 18 | 16 | 93.8% |
   | > 0.10% | 18 | 16 | 93.8% |
   | > 0.15% | 15 | 19 | 84.2% |
   | > 0.20% | 14 | 20 | 85.0% |
   | > 0.25% | 13 | 21 | 81.0% |
   | > 0.30% | 12 | 22 | 77.3% |

   Moving the boundary by 0.05% changes the result from 100% to 93.8%. This is classic overfitting — the filter is fitting noise, not signal.

4. **Economic logic is weak.** "Price was rising 15 min before SHORT entry" blocking ALL trades is too aggressive. Some of these are valid counter-trend entries. The 4 wins blocked (FIL +0.22, HBAR +0.30, ME +0.23, LTC +0.07) are real money left on the table.

5. **The plan itself acknowledges this is suspicious:** "100% WR is almost certainly overfitting. Expect 10-20% degradation." This is honest, but even with 20% degradation, the plan projects 86% WR on 15 trades — still unrealistic with n=14.

**Assessment: This filter is the biggest overfitting risk in the plan. The 100% WR is a mirage on tiny samples.**

---

## Claim 4: RSI > 50 Safety Filter

**Verdict: PARTIAL (direction reversed from what plan says)**
**Confidence: MEDIUM**

**What was claimed:** "Catches ~55 losses, blocks ~27 wins" — implying RSI > 50 is BAD for SHORT (which makes sense: overbought = price might keep rising = SHORT loses).

**Evidence from data:**
After regime + z>0 + pre15>0 filters, there are 38 trades (37W/1L).
- RSI <= 50 (ALLOW): 29 trades → **29W/0L = 100% WR**
- RSI > 50 (BLOCK): 9 trades → **8W/1L** (blocks $+2.43 of winners)

**Problem:** The RSI > 50 filter is **blocking winners** (8 wins vs 1 loss caught). It's **negative** in this data — it removes $+2.43 of profit while only catching $-0.99 of losses. The remaining loss (INJ, RSI=58.6) IS caught by the filter, but at a net cost.

**However:** The RSI > 50 filter makes economic sense as a safety net — overbought SHORT entries ARE riskier. The negative result in this sample may be noise. On a larger sample, it could be positive.

**Assessment:** The filter is directionally sound but shows negative results in this data. The plan's claim of "catches ~55 losses" is based on the full 299-trade dataset, not the 204-trade subset.

---

## Claim 5: Fix RSI Calculation (Wilder Smoothing)

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**
- The signal detection code (`accel_300_v3_short.py`) uses Wilder smoothing RSI (lines 143-158):
  ```python
  avg_gain = (avg_gain * (period - 1) + gains[i]) / period
  avg_loss = (avg_loss * (period - 1) + losses[i]) / period
  ```
- The plan correctly identifies that the signals table stores a different RSI calculation
- The ENA example is valid: table RSI=21.2 (<25, caught) vs Wilder RSI=27.2 (>25, passes) — a real discrepancy
- Wilder smoothing is the standard RSI calculation (as used by TradingView, etc.)

**Assessment:** This is a legitimate bug fix, not overfitting. RSI should be consistent everywhere.

---

## Claim 6: Projected Performance → 86% WR

**Verdict: DISAGREE**
**Confidence: HIGH**

**What was claimed:** "Optimistic: 86% WR (38W/6L), Realistic: 81% WR"

**Evidence:**
- On the 204-trade file, after ALL filters: 29W/0L = 100% WR (PnL: +$19.87)
- BUT this is 29 trades from 140 SHORT trades — **79% of trades are filtered out**
- The "86% WR" projection assumed specific trade counts (38W/6L) that don't match this data
- More importantly: **filtering out 79% of trades is extreme overfitting**

**The real question:** How many trades per day would this produce?
- 140 SHORT trades over ~27 days (Aug 12 to Sep 7) = ~5.2 trades/day
- After filtering: ~29 trades over 27 days = ~1.1 trades/day
- That's 1 trade per day on average — may be too few for the system to be meaningful

**Assessment:** The projected WR is based on different data and likely inflated. The realistic outcome is probably 75-85% WR on very few trades, with high variance due to small samples.

---

## Implementation Order Assessment

**Verdict: PARTIAL**

The plan proposes:
1. Fix RSI calculation ✅ (legitimate bug fix)
2. Add regime filter ✅ (directionally sound, but EXTREME is actually profitable in this data)
3. Add z>0 filter ✅ (works well, high confidence)
4. Add pre15>0 filter ❌ (massive overfitting risk, tiny sample)
5. Add RSI>50 safety filter ⚠️ (negative in this data, but directionally sound)
6. Test 7 days ✅ (essential before going live)

**Problem with order:** Steps 3+4 are regime-specific filters that need different data sources to validate properly. The plan should prioritize steps 1+2+3 (which are solid) and RESEARCH step 4 more carefully before implementing.

---

## Summary of Overfitting Risks

| Risk | Severity | Evidence |
|------|----------|----------|
| pre15>0 at exact 0% boundary | **HIGH** | 0.05% threshold change drops WR from 100% to 93.8% |
| n=14 for NORMAL filter | **HIGH** | Need ≥30 for statistical significance |
| n=24 for HIGH filter | **MEDIUM** | Close to threshold but still below |
| 79% trade filtering rate | **HIGH** | Only 21% of trades survive all filters |
| RSI>50 blocks 8W/1L | **MEDIUM** | Net negative in this sample |
| Data source mismatch | **HIGH** | Plan's regime numbers (294 trades) don't match provided data (204 trades) |

---

## FINAL VERDICT

**Overall Plan Assessment: HIGH RISK — NEEDS MORE DATA BEFORE IMPLEMENTATION**

The plan has legitimate insights:
- z>0 is a genuinely good SHORT filter in HIGH regime
- RSI calculation fix is a real bug
- Regime-based filtering is directionally sound

But critical problems exist:
- The pre15>0 filter is classic overfitting on a tiny sample
- The 86% WR projection is almost certainly inflated
- The data source used for the plan's regime analysis is not available for verification
- Only 29 trades would survive all filters — too few for reliable statistics

**Recommendation:** Implement steps 1-3 (RSI fix, regime block, z>0 filter) which are solid. DEFER step 4 (pre15>0) until more data is collected. Steps 5+6 can be evaluated after the first 3 are live.

---

## Files Verified
- `/root/.hermes/plans/accel300-v4-killer-signal.md` — plan file
- `/root/.hermes/data/accel300_all_trades_analyzed.json` — 204 trades with metadata
- `/root/.hermes/data/accel300_short_detailed.json` — 139 SHORT trades with candle data
- `/root/.hermes/scripts/hermes_constants.py` — current constants (lines 1-796)
- `/root/.hermes/scripts/decider_run.py` — current filter logic (lines 1-1142)
- `/root/.hermes/scripts/signals/accel_300_v3_short.py` — signal detection (623 lines)
