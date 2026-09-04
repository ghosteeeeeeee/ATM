# Independent Verdict: spike_exhaustion_short Improvement Plan
**Auditor:** Independent Agent (own conclusions, no priming)
**Date:** 2026-09-03
**Files reviewed:** spike_exhaustion_short.py, hermes_constants.py (lines 2307-2316), improvement plan
**Data analyzed:** signals_hermes_runtime.db (signal_outcomes, signals, momentum_cache), candles.db (candles_1m, candles_5m)

---

## Summary

**REJECT the proposed changes.** The plan is built on incorrect premises, inaccurate data analysis, and code that would degrade signal quality. The root problem is not the threshold — it's that the signal NEVER EXECUTES.

---

## Claim 1: "Current signal misses CASHCAT events because spike threshold is too high (2.5% vs actual 0.65-2.22%)"

### Verdict: DISAGREE
### Confidence: HIGH

**Evidence:**

1. **The signal ALREADY fires for CASHCAT.** 29 spike_exhaustion_short signals were generated for CASHCAT between Aug 14-26 with the current 2.5% threshold. The signal does NOT "miss" events — it detects them and writes them to the signals table.

2. **The claimed spike percentages are inaccurate.** I recomputed spikes for the three claimed events using the actual candle data:
   - 15:49 (Aug 12): Plan claims +0.65%. My computation: +0.769%. **Close but inaccurate.**
   - 18:25 (Aug 12): Plan claims +1.16%. My computation: +0.492%. **Off by 2.4x.**
   - 16:15 (Aug 12): Plan claims +2.22%. My computation: +0.000%. **Completely wrong — no spike exists at this time.**

3. **The real problem is execution, not detection.** All 86 spike_exhaustion_short signals across all tokens resulted in:
   - 72 EXPIRED (approved but not executed within timeout)
   - 14 SKIPPED (blocked by compactor/context gate)
   - **0 EXECUTED** — this signal has NEVER produced a trade.

4. **Lowering the threshold would not help.** The signal already fires. The bottleneck is downstream (compactor scoring, context gate filtering, position limits).

---

## Claim 2: "Reducing threshold to 1.5% would catch these events"

### Verdict: DISAGREE — actively harmful
### Confidence: HIGH

**Evidence from simulation on 6,621 CASHCAT candles with volume>0:**

| Configuration | Signals | Avg Spike | Price Drops at All | Drop>0.5% | Adverse>1% |
|---|---|---|---|---|---|
| **Current 2.5%/stall3** | 78 | 3.615% | 91.0% | 69.2% | 61.5% |
| Proposed 1.5%/stall1 | 322 | 2.540% | 96.3% | 76.7% | 65.5% |
| Proposed 1.5%/stall3 | 234 | 2.460% | 94.9% | 74.8% | 63.7% |

**Key finding:** The proposed 1.5%/stall1 produces **4x more signals** but with **worse adverse excursion** (65.5% vs 61.5%). With the 1.2% SL, 59.7% of entries would hit the stop loss before any profit. The current 2.5% threshold actually has BETTER signal quality.

**Rate limiting issue:** With stall=1, CASHCAT would generate up to 69 signals on a single day (Aug 17), far exceeding the 2h cooldown cap of 12/day/token. Most of these would be redundant noise.

---

## Claim 3: "Reducing stall from 3 to 1 candle would enable faster entry"

### Verdict: DISAGREE — reduces quality
### Confidence: HIGH

**Evidence:**
- Stall=3 ensures the spike has actually exhausted before entry. Stall=1 fires while momentum may still be rising.
- With stall=1, 59.7% of entries experience >1% adverse excursion within 30 minutes (would be stopped out at 1.2% SL).
- The current stall=3 already works: 91% of entries see some price drop, 69.2% see >0.5% drop.
- The plan's own backtest table shows: Event 15:49 PASS stall, Event 18:25 PASS stall, Event 16:15 PASS stall. The stall wasn't the problem for these events.

---

## Claim 4: "Adding RSI > 70 confirmation would filter non-overbought entries"

### Verdict: PARTIAL — concept is sound, implementation is incomplete
### Confidence: MEDIUM

**Evidence:**
- **RSI IS available** in `momentum_cache` table (column `rsi_14`, type REAL) for most tokens. Example: ETH=52.4, SOL=68.99.
- **However, CASHCAT has only 1 row** in momentum_cache with `rsi_14="quiet"` (a string, not a number). This token has no numeric RSI.
- The plan does not implement RSI computation — it assumes RSI exists. A fallback or calculation from raw candles would be needed.
- The plan does not implement Bollinger Bands either — `upper_bb` is referenced in the code but never computed. There's no BB table in either database.
- **The concept is valid**: RSI > 70 + BB band break is a standard overbought reversal pattern. But the plan doesn't implement it correctly.

---

## Bugs Found in Proposed Code

### Bug 1: Missing indicator calculations (CRITICAL)
The plan's code references `upper_bb` and `rsi` but these are never computed:
```python
if current_price >= upper_bb and rsi > SPIKE_EXHAUSTION_SHORT_RSI_MIN:
```
There is no Bollinger Bands calculation in the signal file, no BB data in either database, and no import for computing it. This code would raise a `NameError`.

### Bug 2: Hardcoded constant (MINOR)
The plan's code snippet hardcodes `0.015` instead of using the constant:
```python
if best_spike >= 0.015:  # 1.5% instead of 2.5%
```
This violates the codebase convention: "No hardcoded constants — all thresholds MUST go in hermes_constants.py."

### Bug 3: Dual entry path (DESIGN FLAW)
The plan creates two separate code paths:
1. BB band break + RSI > 70 (new path)
2. Spike detection (existing path, modified threshold)

These run independently. The BB+RSI path could fire even when the spike detection fails, creating inconsistent behavior. The conditions should be integrated, not parallel.

### Bug 4: Config table inconsistency
The plan's backtest table for "Proposed signal" uses different columns than "Current signal," making comparison misleading. The proposed table adds RSI and BB Break columns but removes Stall and Red columns.

---

## Edge Cases and Risks Missed

### Risk 1: Synthetic candle distortion
CASHCAT candles frequently have `O=H=L=C` (tick data with no intrabar movement). This creates:
- Spike values that are technically correct but meaningless (e.g., 168% spike on Aug 22 — clearly a data artifact)
- False "red candle" detection when tick data alternates between two prices
- The signal was designed for normal candles with intrabar range, not tick-synthetic data

### Risk 2: CASHCAT is in PENALTY_TOKENS
CASHCAT has a 0.7x score multiplier (penalty). Even if the signal fires perfectly, the compactor deprioritizes it. This is a separate issue from the signal's detection logic.

### Risk 3: 0% execution rate is the real problem
86 signals across 20 tokens, 0 trades. The plan doesn't investigate WHY signals aren't executing. Potential causes:
- Signal confidence (80-88%) isn't competitive enough in the compactor
- Position slots are filled by other signals first
- Context gate blocks the signals
- Speed/velocity filters reject the tokens

### Risk 4: Signal frequency explosion
CASHCAT generates 29 signals in 13 days with current settings. With 1.5%/stall1, it would generate ~322 (projected). The system has position limits (MAX_OPEN_POSITIONS=5, MAX_TOTAL_POSITIONS=10) and cooldowns that would reject most, but the increased frequency wastes computation and clutters the signals table.

### Risk 5: No follow-through validation
The plan claims these are "missed opportunities" but provides no evidence that the proposed entries would be profitable. My simulation shows 59.7% adverse excursion with stall=1, meaning most entries would be stopped out.

---

## Recommendation

**DO NOT deploy the proposed changes.** Instead:

1. **Investigate the execution bottleneck.** Why do 86 signals produce 0 trades? Check the compactor scoring, context gate, and position limits. This is the real problem.

2. **If threshold changes are desired, use 2.0%/stall3** — this is a more conservative middle ground that increases signals moderately (126 vs 78 for CASHCAT) without the quality degradation of 1.5%/stall1.

3. **BB band + RSI implementation needs proper engineering:**
   - Compute BB from 20-period SMA + 2σ on 1m or 5m candles
   - Compute RSI from momentum_cache or calculate from candles
   - Integrate as an alternative entry path with proper backtesting
   - Don't add unimplemented features to the plan

4. **Add data quality checks.** CASHCAT's synthetic candles (O=H=L=C) can produce wild spike values. Add a minimum candle range check (e.g., require H-L > 0.1% to avoid tick noise).

5. **Consider disabling spike_exhaustion_short entirely** until the execution problem is solved. It consumes signal table space and pipeline cycles for 0 return.

---

## Files Referenced
- `/root/.hermes/scripts/signals/spike_exhaustion_short.py` — current signal (186 lines)
- `/root/.hermes/scripts/hermes_constants.py` — lines 2307-2316 (11 constants)
- `/root/.hermes/brain/plans/2026-09-03_spike_exhaustion_short_improvement.md` — proposed plan (156 lines)
- `/root/.hermes/data/signals_hermes_runtime.db` — signals, signal_outcomes, momentum_cache tables
- `/root/.hermes/data/candles.db` — candles_1m, candles_5m tables
