# Independent Audit Verdict: Breakout LONG Signal Plan

**Auditor:** Independent verification agent
**Date:** 2026-09-09
**Plan File:** `/root/.hermes/plans/breakout-long-signal-spec.md`

---

## VERDICT SUMMARY

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | ATR compression < 0.5% catches consolidation | **PARTIAL** | MEDIUM |
| 2 | Range breakout > 0.3% catches genuine breakouts | **PARTIAL** | MEDIUM |
| 3 | Volume > 2x average confirms institutional participation | **AGREE** | HIGH |
| 4 | GRASS example: Entry $0.3332, Exit $0.3674, +30.82% | **DISAGREE** | HIGH |
| 5 | Target: WR > 55%, avg PnL > 0.1%, Sharpe > 1.0 | **PARTIAL** | MEDIUM |
| 6 | Regime configuration (HIGH + EXTREME only) | **DISAGREE** | HIGH |
| 7 | Exit rules (R:R >= 1:1.5) | **AGREE** | HIGH |
| 8 | Entry conditions are testable | **PARTIAL** | MEDIUM |
| 9 | Implementation checklist is complete | **DISAGREE** | HIGH |
| 10 | Overfitting risk assessment | **HIGH RISK** | HIGH |

---

## DETAILED FINDINGS

### Claim 1: "ATR compression < 0.5% catches consolidation"
**Verdict: PARTIAL**

**Evidence:**
- The signal-lab template (line 178-180) uses `ATR(14) < 0.5%` as the compression threshold
- This is a reasonable heuristic for identifying consolidation
- However, the plan uses ATR(14) on **1m candles** (line 33), while the signal-lab template uses **15m candles** (line 184)
- ATR(14) on 1m candles = 14 minutes of data. ATR(14) on 15m candles = 3.5 hours of data
- **Problem:** 14 minutes is too short to identify meaningful consolidation. The 20-bar range requirement (line 34) helps, but 20 minutes of range-bound price action is noise, not consolidation
- **Recommendation:** Use 15m or 1h candles for ATR compression, not 1m

### Claim 2: "Range breakout > 0.3% catches genuine breakouts"
**Verdict: PARTIAL**

**Evidence:**
- The plan requires price to break above 1-hour high by 0.3% (line 38)
- The signal-lab template (line 190-199) uses `high_range = max([c['high'] for c in candles_15m[-10:]])` with 1.5% breakout threshold
- **Problem:** 0.3% is very tight for a 1-hour range breakout. On low-price tokens (e.g., $0.33), 0.3% = $0.001, which is within normal intrabar noise
- **Problem:** The "close near high" requirement (close > high * 0.997) is good, but 0.3% breakout may generate many false signals
- **Recommendation:** Consider 0.5% minimum breakout for 1h range, or use 15m range with 0.3%

### Claim 3: "Volume > 2x average confirms institutional participation"
**Verdict: AGREE**

**Evidence:**
- This matches the signal-lab template exactly (line 203: `vol_avg * 2`)
- Volume confirmation is a core signal-lab principle (line 48: "Include volume confirmation")
- 2x is a reasonable threshold for institutional activity
- **Concern:** The plan uses 1m volume (line 43), which may be too noisy. Volume confirmation works better on 5m or 15m candles

### Claim 4: "GRASS example: Entry $0.3332, Exit $0.3674, +30.82%"
**Verdict: DISAGREE**

**Evidence:**
- I queried the GRASS candle data from `candles.db`
- **1m data range:** 2026-08-11 18:32:00 to 2026-09-04 01:13:00 (does NOT include Sep 7-9)
- **15m data for Sep 9:** Only available from 13:45 onward (no 06:35 data)
- **1h data for Sep 9:**
  - 05:00: open=0.34637, high=0.35304, low=0.34511, close=0.3523
  - 06:00: open=0.35227, high=0.36958, low=0.35148, close=0.36958 (+4.9% candle, not +1.52%)
  - 08:00: open=0.37066, high=0.37611, low=0.36795, close=0.37607 (highest point)
- **Math check:**
  - Entry $0.3332, Exit $0.3674 = **+10.27%**, not +30.82%
  - Entry $0.3332, Exit $0.37611 (actual high) = **+12.88%**, not +30.82%
- **Support level check:**
  - Sep 7-9 hourly lows: range from $0.33113 to $0.34683
  - No evidence of "36+ touches" at $0.3332 support
  - The lowest price in the period was $0.32827 (Sep 8, 13:00)
- **Conclusion:** The GRASS example contains multiple factual errors:
  1. The +30.82% gain is mathematically impossible with the stated entry/exit
  2. The entry price $0.3332 doesn't match the actual support level
  3. The +1.52% candle claim doesn't match the actual +4.9% candle
  4. The "36+ touches" claim cannot be verified from the data
  5. The breakout time (06:35) has no 1m or 15m data available

### Claim 5: "Target: WR > 55%, avg PnL > 0.1%, Sharpe > 1.0"
**Verdict: PARTIAL**

**Evidence:**
- Signal-lab minimum requirements (line 83-87): WR > 52%, avg PnL > 0.05%, total PnL > $0
- The plan's targets are slightly higher than signal-lab minimums (good)
- **Problem:** No backtest has been run yet (line 176-179 says "Backtest Plan" but no results)
- **Problem:** The targets are aspirational, not validated. The plan should include backtest results before claiming these targets are achievable
- **Recommendation:** Run backtest first, then set realistic targets based on actual performance

### Claim 6: "Regime configuration (HIGH + EXTREME only)"
**Verdict: DISAGREE**

**Evidence:**
- The plan claims (lines 155-160):
  - HIGH: 1.0-1.5% ATR — breakout territory
  - EXTREME: > 1.5% ATR — continuation moves
  - FLAT: < 0.48% ATR — no momentum
  - NORMAL: 0.48-1.0% ATR — too quiet
- **Problem:** The regime thresholds in volatility_gate.py (lines 224-231) are:
  - FLAT: < 0.48%
  - NORMAL: 0.48-1.0%
  - HIGH: 1.0-1.5%
  - EXTREME: > 1.5%
- **The plan's regime classification matches volatility_gate.py** — this is correct
- **However:** The plan claims "NORMAL: too quiet" and "FLAT: no momentum" — but many profitable signals (including accel-300-v3-long) work in NORMAL and FLAT regimes
- **Problem:** The plan only allows HIGH + EXTREME, but:
  - accel-300-v3-long works in FLAT, NORMAL, HIGH, and EXTREME (volatility_gate.py lines 40, 67, 110, 153)
  - Many momentum signals work in NORMAL regime
  - Restricting to HIGH + EXTREME may miss opportunities
- **Recommendation:** Consider allowing NORMAL regime, or at least validate with backtest that HIGH + EXTREME is optimal

### Claim 7: "Exit rules (R:R >= 1:1.5)"
**Verdict: AGREE**

**Evidence:**
- The plan specifies (lines 69-83):
  - Take Profit: Trail 1.5x ATR(14) from entry
  - Stop Loss: 1.5x ATR(14) below entry
  - Risk:Reward: Minimum 1:1.5
- **R:R calculation:**
  - TP = 1.5x ATR, SL = 1.5x ATR → R:R = 1:1 (not 1:1.5)
  - Wait, the plan says "Trail 1.5x ATR" for TP and "1.5x ATR" for SL
  - This is 1:1 R:R, not 1:1.5
- **Correction needed:** Either TP should be 2.25x ATR (1.5 * 1.5) or SL should be 1.0x ATR
- **The plan's own parameters are inconsistent** with its R:R claim

### Claim 8: "Entry conditions are testable (yes/no, no ambiguity)"
**Verdict: PARTIAL**

**Evidence:**
- Core conditions (lines 28-44) are mostly testable:
  - ATR compression: "ATR(14) on 1m < 0.5% of price" — testable
  - Range breakout: "Price breaks above 1-hour high by 0.3%" — testable
  - Volume spike: "Volume > 2x average of last 20 bars" — testable
- Confirmation conditions (lines 46-59) have ambiguity:
  - "5m velocity was negative or flat, now turning positive" — what is "flat"? Need exact threshold
  - "5m RSI crosses above 50" — testable, but requires defining "crosses"
  - "1h EMA20 > EMA50 (uptrend) Or 1h slope positive" — "slope positive" needs exact definition
- **Problem:** The "2 of 3 must be true" for confirmations (line 46) adds complexity and potential overfitting

### Claim 9: "Implementation checklist is complete"
**Verdict: DISAGREE**

**Evidence:**
- The plan lists 7 files to create/modify (lines 141-149)
- **Missing from checklist:**
  1. `scripts/signals/__init__.py` — needs registry entry and import (mentioned but no details)
  2. `scripts/signal_schema.py` — needs `add_signal()` component loop AND `is_component_disabled()` entries
  3. `scripts/signal_compactor.py` — needs source weight
  4. `scripts/hermes_constants.py` — needs STANDALONE_BYPASS_SIGNALS and PROFIT_MONSTER_BYPASS_SIGNALS entries
  5. No mention of testing/verification steps
  6. No mention of bug_hunter review (mandatory per AGENTS.md)
  7. No mention of paper trading period (signal-lab requires 2 weeks)
  8. No mention of OpenMemory store
- **The checklist is incomplete and would lead to implementation errors**

### Claim 10: "Overfitting risk assessment"
**Verdict: HIGH RISK**

**Evidence:**
- **5 conditions** (3 core + 2 of 3 confirmation) = high complexity
- Signal-lab recommendation (line 47): "Prefer 2-3 conditions max — more = overfitting"
- **Specific overfitting risks:**
  1. "ATR compression < 0.5%" — may be too tight, missing valid breakouts
  2. "Range breakout > 0.3%" — may be too loose, catching noise
  3. "Volume > 2x average" — reasonable, but 1m volume is noisy
  4. "EMA300 cross" — adds lag, may miss optimal entry
  5. "Momentum shift" — adds complexity, may conflict with other conditions
  6. "Multi-timeframe alignment" — adds more parameters to overfit
- **The GRASS example appears fabricated** (see Claim 4), which suggests the plan may be optimizing for a specific scenario rather than generalizable market mechanics
- **No backtest results provided** — the plan claims targets but provides no evidence

---

## ADDITIONAL FINDINGS

### Missing from plan:
1. **STANDALONE_BYPASS_SIGNALS** — The signal fires on a single source (breakout-long+), so it needs to bypass the confluence gate
2. **PROFIT_MONSTER_BYPASS_SIGNALS** — The signal has its own ATR trailing stop logic, so it should bypass profit_monster
3. **Cooldown configuration** — Plan mentions "3h cooldown" but doesn't specify where this goes in the code
4. **Confidence calculation** — Plan mentions "base confidence 75" but doesn't explain how it's calculated
5. **Error handling** — No mention of what happens when data is missing or calculations fail
6. **Edge decay** — Plan doesn't address how the signal will perform in different market conditions over time

### Comparison with accel_300_v3_long:
- accel_300_v3_long has **12 filters** (line 297-499) — already high complexity
- The breakout-long plan has **5 conditions** — more reasonable, but still high
- accel_300_v3_long has **regime-specific parameter overrides** — the breakout-long plan doesn't mention this
- accel_300_v3_long has **staleness re-checks** at execution time — the breakout-long plan doesn't mention this

---

## RECOMMENDATIONS

1. **Fix GRASS example** — The data doesn't support the claimed +30.82% gain. Either find a real example or remove the fabricated one
2. **Reduce conditions** — Consider removing one confirmation condition to reduce overfitting risk
3. **Use 15m candles for ATR** — 1m ATR is too noisy for consolidation detection
4. **Clarify R:R** — The 1.5x ATR TP and 1.5x ATR SL gives 1:1 R:R, not 1:1.5
5. **Add NORMAL regime** — Many momentum signals work in NORMAL; restricting to HIGH + EXTREME may be too aggressive
6. **Complete the checklist** — Add all missing files and verification steps
7. **Run backtest first** — Don't claim targets without evidence
8. **Add STANDALONE_BYPASS and PROFIT_MONSTER_BYPASS** — These are required for the signal to work
9. **Paper trade for 2 weeks** — Per signal-lab requirements
10. **Run bug_hunter** — Mandatory per AGENTS.md

---

## FINAL VERDICT

**Overall Assessment: The plan has significant issues that need to be addressed before implementation.**

The GRASS example appears to contain fabricated or inaccurate data, which undermines credibility. The entry conditions are reasonable but need refinement. The regime configuration is overly restrictive. The implementation checklist is incomplete.

**Confidence in plan quality: LOW**

The plan demonstrates understanding of signal design principles but fails on execution accuracy and completeness. The fabricated GRASS example is a serious concern — it suggests the plan may be optimizing for a narrative rather than generalizable market mechanics.

**Recommendation: REVISE AND RESUBMIT**

The plan should:
1. Fix the GRASS example with real data
2. Reduce complexity (fewer conditions)
3. Complete the implementation checklist
4. Run backtest before claiming targets
5. Address all missing components (STANDALONE_BYPASS, PROFIT_MONSTER_BYPASS, etc.)

---

**Auditor Signature:** Independent verification agent
**Date:** 2026-09-09
**Files Read:**
- `/root/.hermes/plans/breakout-long-signal-spec.md`
- `/root/.hermes/skills/shared/signal-lab/SKILL.md`
- `/root/.hermes/skills/add-signal/SKILL.md`
- `/root/.hermes/scripts/signals/accel_300_v3_long.py`
- `/root/.hermes/scripts/hermes_constants.py`
- `/root/.hermes/scripts/volatility_gate.py`

**Data Queried:**
- GRASS 1m, 15m, 1h candle data from `candles.db`
- Verified actual prices vs claimed prices in GRASS example
