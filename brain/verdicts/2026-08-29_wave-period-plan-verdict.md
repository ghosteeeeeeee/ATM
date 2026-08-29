# Independent Verdict: Wave Period Analysis Plan

**Auditor:** Independent verification agent
**Date:** 2026-08-29
**Files reviewed:**
- `/root/.hermes/plans/2026-08-29_wave-period-analysis-plan.md`
- `/root/.hermes/brain/wave_pattern_buckets.md`
- `/root/.hermes/scripts/wave_period_detector.py`
- `/root/.hermes/scripts/wave_classifier.py`

**Method:** Read all files from scratch, ran scripts on live candle DB, tested alternative parameters, verified claims against actual data.

---

## CRITICAL BUG FOUND

### `find_peaks_troughs()` uses `>=` for peaks and `<=` for troughs with `elif`

```python
# Lines 61-68 of wave_period_detector.py
if all(prices[i] >= prices[i-j] for j in range(1, window+1)) and \
   all(prices[i] >= prices[i+j] for j in range(1, window+1)):
    extrema.append((i, prices[i], 'peak'))
elif all(prices[i] <= prices[i-j] for j in range(1, window+1)) and \
     all(prices[i] <= prices[i+j] for j in range(1, window+1)):
    extrema.append((i, prices[i], 'trough'))
```

**Problem:** `>=` means flat regions (where `price[i] == price[i±j]`) are always classified as peaks, never troughs, because the `if` branch catches them first via `elif`. This creates a massive peak bias for tokens with flat close prices.

**Evidence:** 6 tokens have 35-44% flat close-price transitions (ZRO: 39.6%, ARB: 43.7%, HYPE: 40.5%, WLD: 40.6%, TURBO: 39.1%, FET: 35.2%). These tokens show peak-to-trough ratios of 4.9:1 to 7.4:1, whereas tokens with <1% flat transitions (BTC, ETH, SOL) show ~1:1 ratios.

**Impact:** When using strict inequality (`>`, `<`), ALL 6 "HIGH_FREQ_OSCILLATOR" tokens flip to MEDIUM_FREQ_TREND. The fast_pct drops from 72-78% to 1-7%. **The entire HIGH_FREQ_OSCILLATOR bucket is an artifact of this bug.**

---

## CLAIM-BY-CLAIM VERDICT

### Claim 1: ZRO is HIGH_FREQ_OSCILLATOR with 78% of waves in 1-2h bucket

**Verdict: DISAGREE**

| Metric | Original (buggy) | Strict inequality (correct) |
|--------|-------------------|-----------------------------|
| Fast_pct (1-2h) | 78.4% | 6.2% |
| Peaks | 313 | ~40 |
| Troughs | 45 | ~41 |
| Peak/trough ratio | 7.0:1 | 1.0:1 |
| Classification | HIGH_FREQ_OSCILLATOR | MEDIUM_FREQ_TREND |

The 78.4% fast_pct is entirely caused by the peak-detection bug. ZRO has 39.6% flat close-price transitions. With correct detection, ZRO's dominant period is 2-8h (67.5%), making it MEDIUM_FREQ_TREND like BTC.

**Confidence: HIGH** — Reproducible with both `>=` and `>` operators.

---

### Claim 2: BTC/ETH/SOL are MEDIUM_FREQ_TREND with 40-50% of waves in 4-8h

**Verdict: PARTIAL**

| Token | 4-8h actual | 2-8h actual (code's medium_pct) | Claim says |
|-------|-------------|----------------------------------|------------|
| BTC | 46.5% | 83.1% | "40-50%" — correct for 4-8h |
| ETH | 44.3% | 77.2% | "40-50%" — correct for 4-8h |
| SOL | 43.5% | 81.0% | "40-50%" — correct for 4-8h |

The 40-50% claim for the 4-8h bucket specifically is **approximately correct** (actual: 43-47%). However, the MEDIUM_FREQ_TREND bucket documentation says "Dominant period: 4-8 hours (60%+ of all waves)" — this is misleading. The classifier checks `medium_pct` which counts 2-8h (not 4-8h). The 60%+ threshold applies to the 2-8h combo, not 4-8h alone.

Additionally, BTC and SOL have 1817h (75-day) data gaps in the candle DB, which inflates their CV from ~0.6 to ~8.9. After gap filtering, their CV drops to realistic levels (0.55, 0.60).

**Confidence: MEDIUM** — The 4-8h numbers are roughly right, but the bucket description is misleading.

---

### Claim 3: 5 buckets capture all token wave patterns

**Verdict: DISAGREE**

With the bug fixed (strict inequality), the classification collapses:

| Bucket | With bug | Without bug |
|--------|----------|-------------|
| HIGH_FREQ_OSCILLATOR | 6 tokens | **0 tokens** |
| MEDIUM_FREQ_TREND | 10 tokens | **19 tokens** |
| BIMODAL | 2 tokens | **0 tokens** |
| CHAOTIC | 1 token | 1 token (WIF) |
| TRANSITIONAL | 1 token | 0 tokens |

The 5-bucket system only exists because of the extrema detection bug. Without it, there is essentially 1 bucket (MEDIUM_FREQ_TREND) plus 1 outlier (WIF/CHAOTIC).

Additionally, the code contains a 6th bucket (`LOW_FREQ_SWINGER` at line 55 of wave_classifier.py) that is NOT documented in `wave_pattern_buckets.md`. It never triggers with current data but represents a documentation/code inconsistency.

**Confidence: HIGH** — Verified with strict inequality on all 20 tokens.

---

### Claim 4: Window=3 is reasonable for extrema detection

**Verdict: DISAGREE**

Window sensitivity analysis shows classification instability:

| Token | Window=2 | Window=3 | Window=4 | Window=5 |
|-------|----------|----------|----------|----------|
| ZRO | HIGH_FREQ | HIGH_FREQ | HIGH_FREQ | HIGH_FREQ |
| BTC | MED_FREQ | MED_FREQ | MED_FREQ | **CHAOTIC** |
| ETH | MED_FREQ | MED_FREQ | MED_FREQ | **TRANSITIONAL** |
| SOL | MED_FREQ | MED_FREQ | MED_FREQ | **CHAOTIC** |
| WIF | **BIMODAL** | CHAOTIC | CHAOTIC | CHAOTIC |
| LINK | BIMODAL | BIMODAL | BIMODAL | **TRANSITIONAL** |

BTC, ETH, and SOL flip to CHAOTIC/TRANSITIONAL at window=5. WIF flips from BIMODAL to CHAOTIC between window=2 and window=3. The classifications are not robust to window choice.

Furthermore, the plan itself lists this as an "uncertain decision" (Decision #1) and proposes validation, but the validation was never completed. The plan says "Different windows produce very different period counts" — this is confirmed and is worse than acknowledged.

**Confidence: HIGH** — Window sensitivity directly tested.

---

### Claim 5: Wave pattern can predict trade outcomes

**Verdict: UNVERIFIED**

No backtest results are presented in any of the reviewed files. The plan describes Phase 2 Step 3 ("Backtest Wave Strategies Per Bucket") and Phase 3 ("Integration") as future work. The claim that "Wave pattern can predict trade outcomes" is aspirational, not evidence-based.

**Confidence: N/A** — No evidence to evaluate.

---

## ADDITIONAL FINDINGS

### Data Gap Contamination

10 of 20 tokens have significant data gaps in the candle DB:

| Token | Gap Duration | Impact |
|-------|-------------|--------|
| BTC | 1817h (75 days) | CV inflated from 0.55 to 8.92 |
| SOL | 1817h (75 days) | CV inflated from 0.60 to 8.89 |
| WIF | 1963h (82 days) | CV inflated, CHAOTIC classification |
| TRUMP | 1928h total | Multiple gaps |
| DOGE | 1874h (78 days) | CV inflated |
| SUI | 1963h (82 days) | CV inflated |
| KAS | 1704h (71 days) | CV inflated |
| ONDO | 507h (21 days) | Moderate impact |
| AAVE | 198h (8 days) | Minor impact |
| FET | 48h (2 days) | Minor impact |

The `calculate_wave_periods()` function uses raw timestamp differences, so a data gap of 1817 hours becomes a single "wave period" of 1817h. This massively distorts mean, std, and CV statistics.

After gap filtering (>48h periods removed), WIF changes from CHAOTIC to TRANSITIONAL, and BTC/SOL CV drops from ~9 to ~0.6.

### Amplitude Classification Changes with Bug Fix

With strict inequality, the previously LOW_AMP tokens (ZRO, ARB, HYPE, WLD, TURBO, FET) change amplitude class because the period count drops dramatically (from ~350 to ~80 periods), and the remaining periods have larger amplitudes:

| Token | Amp (buggy) | Amp (strict) |
|-------|-------------|--------------|
| ZRO | 0.97% LOW_AMP | ~2.5% HIGH_AMP |
| ARB | 0.60% LOW_AMP | ~2.5% HIGH_AMP |
| HYPE | 0.57% LOW_AMP | ~1.8% MED_AMP |
| WLD | 0.78% LOW_AMP | ~2.5% HIGH_AMP |
| TURBO | 0.80% LOW_AMP | ~2.5% HIGH_AMP |
| FET | 0.79% LOW_AMP | ~2.3% MED_AMP |

The flat-price periods were dragging average amplitude down artificially.

---

## SUMMARY TABLE

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | ZRO is HIGH_FREQ_OSCILLATOR (78% fast) | **DISAGREE** — artifact of `>=` bug | HIGH |
| 2 | BTC/ETH/SOL are MEDIUM_FREQ_TREND (40-50% 4-8h) | **PARTIAL** — 4-8h~44% correct, but bucket doc says 60%+ which is wrong | MEDIUM |
| 3 | 5 buckets capture all patterns | **DISAGREE** — collapses to 1 bucket without bug | HIGH |
| 4 | Window=3 is reasonable | **DISAGREE** — classifications unstable across windows | HIGH |
| 5 | Wave pattern predicts trade outcomes | **UNVERIFIED** — no backtest data | N/A |

---

## REQUIRED FIXES BEFORE INTEGRATION

### Fix 1: Extrema Detection (CRITICAL)
```python
# Change from:
if all(prices[i] >= prices[i-j] ...):
    ... 'peak'
elif all(prices[i] <= prices[i-j] ...):
    ... 'trough'

# To:
if all(prices[i] > prices[i-j] ...) and all(prices[i] > prices[i+j] ...):
    ... 'peak'
elif all(prices[i] < prices[i-j] ...) and all(prices[i] < prices[i+j] ...):
    ... 'trough'
```

### Fix 2: Data Gap Handling (HIGH)
Filter out or interpolate periods > 48h that span candle data gaps before analysis.

### Fix 3: Documentation Alignment (MEDIUM)
- wave_pattern_buckets.md says "4-8 hours (60%+)" but code checks "2-8 hours (>60%)"
- Remove or document the 6th bucket (LOW_FREQ_SWINGER) in wave_classifier.py

### Fix 4: Window Validation (MEDIUM)
Complete the proposed window sensitivity analysis before locking in window=3.

---

## BOTTOM LINE

**The wave period analysis framework has the right structure and intent, but the core extrema detection algorithm has a bug that invalidates the HIGH_FREQ_OSCILLATOR classification and the 5-bucket system.** The "choppy ZRO trades" observation may still be real, but the wave period analysis does not support the conclusion that ZRO is fundamentally different from BTC/ETH/SOL. The flat-price bias in low-liquidity tokens creates an illusion of high-frequency oscillation.

Fix the bug, re-run the analysis, and the real patterns will emerge. The 5-bucket system may collapse to 2-3 meaningful buckets (MEDIUM_FREQ_TREND, CHAOTIC, and possibly BIMODAL for some tokens).

---

*This verdict was generated by independent analysis. All claims were tested against live data from the candle DB using the actual scripts.*
