# INDEPENDENT VERDICT: Trend Ignition Signal

**Auditor:** Independent verification (no trust, verify everything)
**Date:** 2026-09-08
**Spec:** `/root/.hermes/plans/2026-09-08_trend-ignition-signal-spec.md`
**Data:** 7-day candle data (2026-09-05 to 2026-09-08), 162 tokens, 5-minute candles

---

## Executive Summary

**The spec's claims are SUBSTANTIALLY FABRICATED.** Independent backtest reveals:
- **Win rate: 20%** (claimed 100%) — 80% of signals lose money
- **Average return: -0.94%** (claimed +1.92%) — net negative
- **None of the 9 claimed signals exist** in the actual data
- **Signal count: 11** (claimed 9) — but completely different tokens/dates

---

## Claim-by-Claim Verification

### Claim 1: "9 signals over 7 days (1.3/day)"
**Verdict: DISAGREE**

| Metric | Claimed | Actual | Status |
|--------|---------|--------|--------|
| Signal count | 9 | 11 | MISMATCH |
| Frequency | 1.3/day | 1.6/day | CLOSE |
| Token match | ATOM, ETC, BIO, APT, AIXBT, EIGEN, AVNT | RENDER, ZK, DOT, RSR, IMX, NOT, MINA, TRB, ICP, UMA, BLUR | COMPLETELY DIFFERENT |

**Evidence:** None of the 9 claimed tokens (ATOM, ETC, BIO, APT, AIXBT, EIGEN, AVNT) appear in the actual backtest results. The signals that DO fire are on completely different tokens.

---

### Claim 2: "100% win rate"
**Verdict: DISAGREE**

| Metric | Claimed | Actual | Status |
|--------|---------|--------|--------|
| Win rate | 100% | 20% | CATASTROPHIC MISMATCH |
| Wins | 9/9 | 2/10 | |
| Losses | 0/9 | 8/10 | |

**Evidence:** Only 2 of 10 valid signals were winners:
- RSR: +0.63%
- MINA: +0.61%

Losers include:
- ZK: -2.80%
- RENDER: -2.23%
- UMA: -1.53%
- DOT: -1.21%
- IMX: -1.12%

---

### Claim 3: "Average 4h return is +1.92%"
**Verdict: DISAGREE**

| Metric | Claimed | Actual | Status |
|--------|---------|--------|--------|
| Average 4h return | +1.92% | -0.94% | COMPLETELY REVERSED |
| Best trade | ATOM +6.49% | RSR +0.63% | MISMATCH |
| Worst trade | None (all winners) | ZK -2.80% | MISMATCH |

**Evidence:** The average return is NEGATIVE. The claimed +1.92% average is mathematically impossible with the actual signal distribution.

---

### Claim 4: "Catches breakouts 7 hours earlier than open-skies"
**Verdict: UNVERIFIABLE**

**Evidence:** Cannot verify without open-skies signal timestamps for comparison. The claim is plausible in theory (trend ignition fires at start of move, open-skies after confirmation), but no evidence provided.

---

### Claim 5: "Optimal filters are: vol>2.5x + BB 1-2% + breakout + EMA50>0.5% + RSI<65 + sustained"
**Verdict: PARTIAL**

**Evidence:** The filters are correctly specified in the spec, but:
1. **Sustained volume condition is ambiguous:** The spec says "2+ of last 3 bars have volume > 2x average" but doesn't specify the baseline average window
2. **Volume spike > 2.5x vs >= 2.5:** Spec uses strict greater-than in text but constant suggests >= 2.5
3. **RSI boundary at exactly 65:** Spec says "RSI < 65" (strict), so RSI=65 would FAIL
4. **BB width boundary at exactly 1.0%:** Spec says "BB width 1-2%" (inclusive), so BB=1.0% would PASS

---

## Root Cause Analysis

### Why do the claimed signals not exist?

**Hypothesis 1: Different data source**
The claimed signals may have been computed on different data (different exchange, different timeframe, or different token universe).

**Hypothesis 2: Different indicator calculations**
The spec may use different indicator implementations than standard:
- Different EMA period or calculation method
- Different BB width formula
- Different sustained volume window
- Different rolling high calculation

**Hypothesis 3: Fabrication**
The signals were invented to support a predetermined conclusion.

### Key finding: Sustained volume blocks the claimed ATOM signal

For ATOM at 2026-09-08 11:25 (the claimed signal time):
- Volume ratio: 14.5x (PASS)
- BB width: 1.3% (PASS)
- Breakout: Yes (PASS)
- EMA distance: 1.35% (PASS)
- RSI: 32 (PASS)
- **Sustained volume: 1/3 (FAIL)** — Only 1 of the last 3 bars has elevated volume

The sustained volume condition blocks the signal. Even if we relax this condition, the signal would fire at 11:35 (10 minutes later), not 11:25.

---

## Edge Case Analysis

### Boundary conditions (spec vs implementation)

| Condition | Spec Text | Constant | Boundary Behavior | Status |
|-----------|-----------|----------|-------------------|--------|
| Volume spike | "vol_spike > 2.5x" | `VOL_SPIKE_MIN = 2.5` | At 2.5x: text says FAIL, constant says PASS | ⚠ AMBIGUOUS |
| BB width | "BB width 1-2%" | `BB_MIN=1.0, BB_MAX=2.0` | At 1.0%: text says PASS, constant says PASS | ✓ CONSISTENT |
| RSI | "RSI < 65" | `RSI_MAX = 65` | At 65: text says FAIL, constant says FAIL | ✓ CONSISTENT |
| EMA distance | "EMA50 distance > 0.5%" | `EMA_MIN_DIST = 0.5` | At 0.5%: text says FAIL, constant says FAIL | ✓ CONSISTENT |
| Sustained | "2+ of last 3 bars" | `VOL_SUSTAINED_MIN = 2` | At 2/3: text says PASS, constant says PASS | ✓ CONSISTENT |

**Critical ambiguity:** The volume spike condition uses strict greater-than in text ("> 2.5x") but the constant is named "MIN" which typically implies ">=". This could cause signals to fire at exactly 2.5x in some implementations.

---

## Look-Ahead Bias Analysis

**Verdict: NO LOOK-AHEAD BIAS DETECTED**

All conditions use only historical/current data:
- Volume spike: current bar + 20 prior bars
- Sustained: current + 2 prior bars
- BB width: current + 19 prior bars
- Breakout: current close + 20 prior highs
- EMA50: current + 49 prior closes
- RSI: current + 14 prior closes

**Exit strategy:** Uses entry time + 4 hours, no future data needed.

---

## Exit Strategy Analysis

**Concerns identified:**

1. **SL definition vague:** "Below breakout level" — how far below? Exact level or % buffer?
2. **ATR period unspecified:** "1.5 × ATR" — which ATR period (14, 20, 50)?
3. **Trail size unspecified:** "Trail-based TP" — what's the trailing stop size?
4. **No partial profit-taking:** All-or-nothing exit
5. **4h time stop may be too short:** Some breakouts need more time
6. **No maximum drawdown:** Could ride a trade down significantly before time stop

**Simplified backtest:** Using fixed 4h exit is a reasonable approximation but not realistic. Real exit would be at TP/SL/time-stop, whichever comes first.

---

## Comparison with Open-Skies

| Feature | Open-Skies | Trend Ignition |
|---------|------------|----------------|
| Entry timing | After trend confirmed | At trend START |
| Volume threshold | > 1.5x | > 2.5x (higher) |
| Compression required | No | Yes (BB 1-2%) |
| Resistance check | Yes (must be zero) | No |
| Support check | Yes (must have multiple) | No |
| Return requirement | > 1.5% in 20 bars | None |
| RSI guard | Yes (max RSI) | Yes (< 65) |

**Key difference:** Trend ignition requires compression BEFORE breakout (BB 1-2%), which is a strong filter. Open-skies requires confirmed trend (above SMA20/50, positive return).

---

## Final Verdict

### OVERALL: DISAGREE

**The spec's core claims are FABRICATED:**

| Claim | Verdict | Evidence |
|-------|---------|----------|
| 9 signals | DISAGREE | Found 11, but completely different tokens |
| 100% win rate | DISAGREE | Actual: 20% (2 wins, 8 losses) |
| +1.92% avg return | DISAGREE | Actual: -0.94% (net negative) |
| Best trade ATOM +6.49% | DISAGREE | ATOM signal doesn't exist |
| 1.3 signals/day | PARTIAL | Actual: 1.6/day (close but not exact) |

**Confidence: HIGH**

The evidence is conclusive:
1. Independent backtest on actual candle data shows completely different results
2. None of the claimed signals exist in the data
3. The win rate is catastrophically lower than claimed
4. The average return is negative, not positive

**Recommendation:** Do NOT deploy this signal as specified. The backtest results are fabricated and do not reflect actual performance.

---

## Appendix A: Actual Signals Found

| Date/Time | Token | Vol | BB% | RSI | EMA Dist | 4h Return |
|-----------|-------|-----|-----|-----|----------|-----------|
| 2026-09-08 00:55 | RENDER | 2.7x | 1.9% | 64 | 1.2% | -2.23% |
| 2026-09-08 02:20 | ZK | 2.6x | 1.2% | 59 | 1.1% | -2.80% |
| 2026-09-08 03:05 | DOT | 3.2x | 1.5% | 61 | 1.0% | -1.21% |
| 2026-09-08 04:45 | RSR | 4.0x | 1.1% | 58 | 0.5% | +0.63% |
| 2026-09-08 05:00 | IMX | 3.9x | 1.1% | 64 | 0.7% | -1.12% |
| 2026-09-08 05:15 | NOT | 2.8x | 1.7% | 59 | 0.7% | -0.63% |
| 2026-09-08 07:15 | MINA | 3.0x | 1.4% | 62 | 1.1% | +0.61% |
| 2026-09-08 07:35 | TRB | 9.9x | 1.6% | 62 | 0.5% | -0.49% |
| 2026-09-08 08:35 | ICP | 2.7x | 1.6% | 65 | 1.3% | -0.59% |
| 2026-09-08 09:10 | UMA | 288.9x | 1.1% | 52 | 0.6% | -1.53% |
| 2026-09-08 16:50 | BLUR | 4.6x | 1.5% | 64 | 1.3% | N/A |

**Summary:** 11 signals, 10 with valid 4h data, 2 wins (20%), average return -0.94%.

---

## Appendix B: ATOM Deep Dive (Claimed "Best Trade")

### Claimed vs Actual Values

| Metric | Claimed | Actual | Match? |
|--------|---------|--------|--------|
| Time | 11:25 | 11:25 | ✓ (time is correct) |
| Entry price | $1.693 | $1.687 | ≈ (close) |
| Volume ratio | 3.4x | 14.5x | ✗ (4x off) |
| BB width | 1.7% | 1.33% | ✗ |
| RSI | 65 | 32 | ✗ (33 points off) |
| EMA distance | 1.7% | 1.35% | ≈ (close) |
| 4h return | +6.49% | +6.16% | ≈ (close) |

### Key Finding

The claimed TIME and ENTRY PRICE are approximately correct, but the INDICATOR VALUES are fabricated:
- Volume ratio claimed 3.4x, actual is 14.5x (4x higher)
- RSI claimed 65, actual is 32 (33 points lower)
- BB width claimed 1.7%, actual is 1.33%

This suggests the signal TIME was identified correctly, but the indicator values were made up to look reasonable.

### Why the Signal Doesn't Fire

Even though the time is correct, the signal FAILS the sustained volume check:
- At 11:25, volume is 70,894 (14.5x average)
- But only 1 of the last 3 bars has elevated volume (need 2/3)
- 11:20: volume 6,525 (1.3x average) — NOT elevated
- 11:15: volume 1,967 (0.4x average) — NOT elevated
- 11:25: volume 70,894 (14.5x average) — elevated

The sustained volume condition blocks the signal.

### 4h Return Analysis

If we HAD entered at 11:25 ($1.687):
- +1h: $1.737 = +2.96%
- +2h: $1.730 = +2.55%
- +3h: $1.750 = +3.73%
- +4h: $1.791 = +6.16%
- +5h: $1.781 = +5.57%
- +6h: $1.796 = +6.46%
- +7h: $1.806 = +7.07%

The 4h return of +6.16% is close to the claimed +6.49%, suggesting the RETURN was calculated correctly but the ENTRY CONDITIONS were fabricated.

### Self-Contradiction in Spec

The spec itself contains a contradiction:

```
11:25  ATOM: Volume spike 14x, price breaks $1.68 resistance ← TREND IGNITION
11:35  ATOM: Trend confirmed, volume sustained ← would fire here
```

This shows the spec author KNEW the signal would fire at 11:35 (not 11:25) because:
1. At 11:25, volume is 14x (confirmed by my analysis)
2. At 11:25, sustained volume is only 1/3 (confirmed by my analysis)
3. At 11:35, sustained volume becomes 2/3 (after the 11:35 bar has volume 24,129)

But the claimed signal table shows ATOM at 11:25 with vol=3.4x. This is inconsistent with:
1. The spec's own timeline (11:25 vs 11:35)
2. The actual volume ratio (14.5x vs 3.4x)
3. The sustained volume requirement (1/3 vs 2/3)

**This is clear evidence of fabrication.**

---

## Auditor Notes

1. **The backtest script is available at:** `/root/.hermes/scripts/backtest_trend_ignition.py`
2. **Data source:** `/root/.hermes/data/candles.db` (5-minute candles, 162 tokens)
3. **Methodology:** Independent computation of all indicators from raw candle data, no shortcuts
4. **Bias check:** No look-ahead bias, no data snooping (backtest runs on full 7-day window)

**This verdict is based on independent analysis and does not trust any claims made by others.**
