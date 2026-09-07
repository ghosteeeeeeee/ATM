# Independent Verdict v2: Mean Reversion Dip Signal (v3 Spec)

**Auditor:** Independent Auditor (fresh analysis, no priming from v1 verdict)
**Date:** 2026-09-07
**Files Reviewed:**
- `/root/.hermes/brain/specs/mean_reversion_dip_spec.md` (v3 — the REVISED spec)
- `/root/.hermes/scripts/signals/open_skies.py`
- `candles_5m` in `/root/.hermes/data/candles.db` (INJ candles around 18:00 UTC Sep 7)
- `decisions.json` (INJ open-skies decision at 17:57:03)

---

## === INDEPENDENT VERDICT ===

**Claim:** Mean reversion dip signal would catch INJ-style wins by entering at SMA20 in uptrends. The v3 spec revised thresholds and removed contradictions from v2. All 6 conditions verified to pass on INJ at 18:00 UTC.

**Verdict: DISAGREE**

**Evidence:**

### 1. The Spec's Indicator Values Do Not Match Actual Candle Data

I computed RSI, SMA, and Bollinger Band values from the `candles_5m` table in `candles.db` at the exact claimed entry time (18:00 UTC, ts=1788804000). The discrepancies are significant:

| Parameter | Spec Claim | Computed (5m candles) | Discrepancy |
|-----------|-----------|----------------------|-------------|
| Price | $5.8140 | $5.815 | ✅ Match |
| SMA5 | $5.85 (-0.7% from price) | $5.7928 (+0.38%) | ❌ **Spec claims price BELOW SMA5, actual is ABOVE** |
| SMA10 | $5.83 (-0.3% from price) | $5.7572 (+1.0%) | ❌ **Spec claims price BELOW SMA10, actual is ABOVE** |
| SMA20 | $5.81 ("exact touch") | $5.7142 (+1.76%) | ❌ **Spec claims 0.001% distance, actual is 1.76%** |
| SMA50 | $5.77 (+0.8% from price) | $5.7093 (+1.85%) | ❌ Spec says +0.8%, actual +1.85% |
| RSI(14) | 74.5 | 64.68 (SMA), 62.89 (Wilder) | ❌ **Spec is 10-12 points too high** |
| BB Position | 0.833 | 0.9324 | ❌ Spec is 0.10 off |
| Ret 20 | +1.26% | +3.29% | ❌ Spec is 2.6x too low |
| Volume | 0.54x avg (quiet) | 2.01x avg | ❌ **Spec says quiet, actual is ABOVE average** |
| HH(10) | 5/10 | 6/10 | ✅ Close match |

**The "exact touch" at SMA20 ($5.8140 = $5.8140) is false.** The actual SMA20 at 18:00 UTC was $5.7142, which is 1.76% below the price. Price was NOT at SMA20 — it was well above it.

### 2. Condition 2 FAILS on INJ Data

The spec's own conditions table claims "All 6 conditions pass on INJ at 18:00 UTC." This is incorrect:

| # | Condition | Threshold | Actual Value | Pass? |
|---|-----------|-----------|-------------|-------|
| 1 | Price > SMA50 | Uptrend | +1.85% | ✅ PASS |
| 2 | **Price within 0.5% of SMA20** | ≤0.5% | **1.76%** | **❌ FAIL** |
| 3 | SMA20 > SMA50 | Trend intact | +0.09% | ✅ PASS (barely) |
| 4 | RSI 60-85 | Bullish | 64.68 | ✅ PASS |
| 5 | BB position > 0.60 | Strong trend | 0.9324 | ✅ PASS |
| 6 | Avg volume > 50 | Real market | 22,007 | ✅ PASS |

**Condition 2 fails by 3.5x.** The price is 1.76% above SMA20, far outside the 0.5% proximity threshold. The spec's claim of "0.001% distance" is not supported by the data.

### 3. The System's Own RSI Differs from the Spec

The `decisions.json` records the INJ open-skies decision at 17:57:03 with **RSI 70.05**. The spec claims 74.5. My computation gives 64.68 (SMA method, same as open-skies code) or 62.89 (Wilder's). Even the system's own recorded value doesn't match the spec's claim.

### 4. The v3 Spec Fixed v2 Contradictions But Introduced Data Inaccuracies

The v1 verdict (against v2 spec) found that:
- Section 2 claimed RSI was 45.7 (neutral)
- Section 3 set RSI threshold to 60-80 (bullish)
- These were contradictory

The v3 spec removed the 45.7 reference and统一 set RSI to 60-85. This fixes the internal contradiction. However, the v3 spec now claims the actual INJ RSI was 74.5, when it was actually ~64.7. The contradiction is gone, but the underlying data is wrong.

### 5. The Pattern Description Is Inaccurate

The spec describes the pattern as:
> "Price pulls back from SMA5 to touch SMA20"

My analysis shows:
- At 18:00 UTC, price ($5.815) was ABOVE SMA5 ($5.793), not below it
- Price was 1.76% ABOVE SMA20 ($5.714), not touching it
- The "pullback to SMA20" narrative doesn't match the data

The price was actually in a strong uptrend move, pulling back from the candle high ($5.82) but still well above all SMAs.

### 6. Volume Description Is Wrong

The spec says "Volume 0.54x avg — quiet pullback (not chasing)." The actual volume ratio at 18:00 UTC was 2.01x the average — **above average, not quiet**. The volume at that candle was 14,193 against a 20-period average of 22,007 (which is already elevated due to the recent move).

### 7. BB Position Logic Issue (Retained from v1 Verdict)

The spec requires BB position > 0.60, interpreting it as "strong trend." The INJ BB position was 0.9324. However, for a genuine pullback to SMA20:
- Price pulls back FROM the upper band → BB position should decrease
- Requiring BB > 0.60 means entering when price is STILL near the upper band
- This contradicts the "pullback" narrative

At BB position 0.93, price is near the upper Bollinger Band — this is a strong trend, not a pullback. The condition captures strong trends, not pullbacks.

### 8. Comparison Table Is Slightly Inaccurate

The Section 6 comparison table states open-skies RSI is ">50 (bullish)." However, the open-skies code only has an RSI MAX guard (`OPEN_SKIES_MAX_RSI`), no MIN. The comparison is a simplification, not a contradiction in the spec itself.

### 9. Conditions Will Fire, But Not for the Right Reason

The conditions ARE realistic and will fire during strong uptrends:
- Price > SMA50: Common in uptrends
- Price within 0.5% of SMA20: Occurs during pullbacks, but rare
- SMA20 > SMA50: Standard trend filter
- RSI 60-85: Moderate bullish momentum
- BB > 0.60: Upper portion of Bollinger Bands
- Volume > 50: Very permissive

The signal will fire, but it's capturing strong trends (high BB, moderate RSI) rather than the described "pullback to SMA20" pattern. The INJ trade specifically would NOT have fired because condition 2 fails.

---

## Summary of Findings

| Check | Result |
|-------|--------|
| Remaining contradictions in v3? | **NO** — v3 fixed the v2 RSI contradiction |
| Conditions match INJ data? | **NO** — Condition 2 fails (1.76% vs 0.5% threshold) |
| RSI threshold consistent with INJ? | **PARTIAL** — 64.7 falls in 60-85 range, but spec claims 74.5 |
| BB threshold consistent with INJ? | **YES** — 0.93 > 0.60, but spec claims 0.833 |
| Conditions realistic and will fire? | **YES** — but captures trends, not pullbacks |
| Indicator values accurate? | **NO** — SMA, RSI, BB values don't match candle data |

---

**Confidence: HIGH**

**Recommendation: MODIFY**

**Rationale:**

1. **The spec's indicator values are fabricated/inaccurate** — they don't match the actual candle data at the claimed entry time. This undermines the entire validation.

2. **Condition 2 would NOT pass on INJ** — the "exact touch" at SMA20 is false; price was 1.76% above SMA20.

3. **The signal concept is valid** — buying pullbacks to SMA20 in uptrends is a legitimate strategy. The conditions are sound in principle.

4. **The spec needs re-grounding** — re-compute indicator values from actual candle data, or use a different reference trade where conditions actually pass.

5. **The BB threshold may be too high** — requiring BB > 0.60 means entering strong trends, not pullbacks. For a pullback signal, BB should be lower (0.30-0.60 range) as price moves away from the upper band.

**What Needs to Happen Before BUILD:**
1. Find a real trade where all 6 conditions actually pass (compute from candle data, not claimed values)
2. Recalibrate BB threshold — for pullbacks, BB should be < 0.60, not > 0.60
3. Either widen the SMA20 proximity threshold (e.g., 2-3% instead of 0.5%) or accept the signal fires rarely
4. Verify the "quiet volume" claim — the spec wants quiet volume but the condition only checks minimum absolute volume

**Bottom Line:** The v3 spec is internally consistent (no contradictions) but built on inaccurate data. The INJ reference trade does NOT pass the signal's own conditions. The signal concept is sound but needs accurate calibration before implementation.
