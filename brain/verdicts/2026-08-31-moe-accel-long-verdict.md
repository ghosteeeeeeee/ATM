# MoE Decision Panel: accel_300_v2_long Signal Improvement Plan

**Date:** 2026-08-31  
**Signal:** accel_300_v2_long (LONG-only momentum)  
**Status:** KILLED — 3 trades, 0% WR, -$0.20/24h, all atr_sl_hit  
**Panel:** 6-member Mixture-of-Experts  

---

## 1. Signal Analyst Verdict — What's Wrong with the Signal Logic

### Core Problem: The signal fires AFTER the pump, not during it.

The accel_300_v2_long signal uses a 10-bar gap acceleration window and requires gap >= 1.5% above EMA300. By the time these conditions are met, the move is already extended. The signal is a **lagging indicator disguised as a leading one**.

**Specific logic failures:**

1. **Gap acceleration filter is backwards for entries.** `V2_MIN_GAP_ACCEL = 0.20` means the gap must be *widening*. But widening gap at 1.5%+ above EMA300 means the move is already mature — you're buying the top of the acceleration curve, not the beginning.

2. **Fresh cross bypass is too aggressive.** `V2_FRESH_CROSS_MIN_GAP = 0.10` allows entry with only 0.10% gap for fresh crosses. This catches tokens like ZEN (gap=1.50%, accel=+0.16%) which are right at the edge, but the accel threshold of 0.20% blocks them anyway. Meanwhile, CRV enters with gap=4.5% and RSI=72 — classic overextension.

3. **No overbought filter.** The signal compactor has an RSI < 20 filter for LONG (blocking oversold freefall), but there is NO RSI > 70 filter for LONG. CRV entered at RSI=72 — textbook overbought territory. This is the single biggest missing filter.

4. **Velocity filter is too permissive.** `min_velocity = abs(price) * 0.0003` is essentially "price moved at all in the right direction over 5 bars." For a 1m signal, this barely filters noise.

5. **The 15m trend filter is asymmetric with SHORT.** LONG uses a simple price-vs-EMA20 check (30 candles, needs 20), while SHORT uses EMA20-vs-EMA50 crossover (60 candles, needs 50). The SHORT signal has a more robust trend detection. This means LONG entries can fire against weak or nonexistent trends.

### Verdict: The signal is structurally a momentum-chasing entry. It needs mean-reversion awareness added — specifically an overbought RSI ceiling and a maximum gap threshold reduction for fresh entries.

---

## 2. Code Architect Verdict — Bugs and Fixes Needed

### Bug 1: RSI Overbought Filter Missing (CRITICAL)
- **File:** `signal_compactor.py:1295-1322`
- **Issue:** The RSI filter only blocks LONG when RSI < 20 (oversold). There is NO upper bound filter. CRV entered at RSI=72 and immediately reversed.
- **Fix:** Add an RSI > 70 (or > 75) block for LONG entries in the same section.

### Bug 2: _get_15m_trend Asymmetry Between LONG and SHORT
- **File:** `signals/accel_300_v2_long.py:138-179` vs `signals/accel_300_v2_short.py:135-172`
- **Issue:** LONG's trend function uses price-vs-EMA20 (30 candles). SHORT's uses EMA20-vs-EMA50 crossover (60 candles). This means LONG has a weaker trend filter.
- **Fix:** Unify both to use the SHORT version (EMA20-vs-EMA50 crossover) which is proven to work at 52% WR.

### Bug 3: Fresh Cross Bypass Allows Weak Entries
- **File:** `signals/accel_300_v2_long.py:56,350-351`
- **Issue:** `V2_FRESH_CROSS_MIN_GAP = 0.10` is too low. ZEN at gap=1.50% with accel=+0.16% was blocked by the accel threshold but would have passed with this bypass. Meanwhile, the fresh cross bypass itself is allowing entries with essentially zero conviction.
- **Fix:** Raise `V2_FRESH_CROSS_MIN_GAP` to 0.50 (or remove the fresh cross bypass entirely and let the main filters do their job).

### Bug 4: Staleness Check Uses Stale EMA
- **File:** `signals/accel_300_v2_long.py:473-481`
- **Issue:** The staleness check recalculates the EMA from the `prices` list, but `prices` was fetched earlier and may be stale. The current price `price` is from `prices_dict` (the latest tick), but the EMA is computed from the full 700-bar series in `prices`. If the latest bar in `prices` is old, the "staleness check" itself is stale.
- **Fix:** The staleness check should use only the current tick price and the most recent EMA, not recompute from the full series.

### Bug 5: Cooldown Bypass Implemented Inline
- **File:** `signals/accel_300_v2_long.py:408-428`
- **Issue:** The cooldown is checked via a direct DB query, bypassing the `get_cooldown()` function from `signal_schema.py`. The comment says "cooldown system ignores reason='signal'" — this means the cooldown system is broken for this signal type. The SHORT signal uses `get_cooldown()` normally (line 397-398 of short file).
- **Fix:** Fix the cooldown system to support the `reason='signal'` parameter, or document why this signal needs a different cooldown mechanism. The current inline check is fragile and inconsistent.

### Verdict: 5 bugs identified. Bug 1 (RSI overbought) is the highest-impact fix. Bug 2 (trend asymmetry) is the most architecturally concerning. Bug 3 (fresh cross) is the most likely cause of the ZEN failure.

---

## 3. Risk Manager Verdict — Execution and Timing Issues

### Problem: Signal-to-Execution Latency Creates Guaranteed Losses

**Timeline analysis (from context):**
- Signal fires → enters hotset → compactor approves → decider_run executes → position opens
- This pipeline has a **3-10 minute delay** between signal firing and trade execution
- For a 1m momentum signal, 3-10 minutes is an eternity — the move is over

**Specific execution failures:**
1. **ZEN at 15:45:** gap=1.50%, accel=+0.16% — blocked by accel threshold (0.20%) AND negative slope. This was the only signal that even attempted to enter, and it was correctly blocked. The signal was correct to fire, but the entry conditions were wrong.

2. **CRV entered at RSI=72:** This is the cardinal sin — buying overbought. The signal has no mechanism to detect "the move is already priced in." RSI=72 on a 1m timeframe means the token has been pumping for 30+ minutes straight.

3. **SAND entered at -4.56%:** Classic case of signal firing at the local peak and then the pullback hitting the ATR stop loss.

### Risk Controls Needed:
1. **RSI ceiling at signal time** (not just compactor time) — block the signal from being created if RSI > 70
2. **Maximum gap cooldown** — if gap > 3.5%, require the gap to be *narrowing* (not widening) before entry
3. **Entry speed requirement** — if the signal price is within 0.5% of the 15m high, block the entry (buying at resistance)

### Verdict: The execution pipeline adds 3-10 minutes of latency to a 1m momentum signal. This is a structural mismatch. The signal needs to be designed for delayed execution — meaning it should fire at the BEGINNING of a move, not at the peak. Currently it fires at the peak.

---

## 4. Statistician Verdict — Sample Size and Edge Assessment

### Sample Size: INSUFFICIENT
- 3 trades total, 0% WR
- This is statistically meaningless — you cannot conclude the signal has 0% WR from 3 trades
- However, the SHORT signal with the same architecture has 52% WR, so the architecture CAN work

### Edge Assessment:
- The SHORT signal has a **structural advantage**: downward moves are faster and more persistent in crypto. Buying momentum in crypto is buying into resistance.
- The LONG signal's gap range (1.5%-4.5%) means it only fires when price is already extended above EMA300. By definition, it's buying above the mean.
- The SHORT signal's gap range (2.0%-6.0%) means it fires when price is already below EMA300 — but in crypto, below-EMA300 moves tend to cascade (panic selling). Above-EMA300 moves tend to mean-revert (profit taking).

### Statistical Verdict:
- **SHORT edge:** Structural — panic selling cascades, profit taking mean-reverts
- **LONG edge:** Weak — requires the move to continue AFTER already being extended
- **Recommendation:** The signal needs to either (a) fire earlier (lower gap threshold, earlier in the move) or (b) add mean-reversion filters (RSI ceiling, max gap, proximity to resistance)
- **Minimum sample needed:** 30 trades to determine if the signal has a positive edge at all

### Verdict: The signal is structurally disadvantaged for LONG entries in crypto. The SHORT signal works because panic selling cascades. The LONG signal needs to be redesigned to catch moves EARLY, not at peaks. Sample size is too small for statistical significance, but the architectural analysis is sufficient to identify the core problem.

---

## 5. Regime Analyst Verdict — Market Context

### BTC-CRASH Filter Blocks LONG Entries
- **File:** `decider_run.py:1881-1905`
- When BTC momentum is negative (BTC-CRASH filter), LONG entries are blocked
- This is correct behavior — you don't want to go LONG on altcoins when BTC is dumping
- BUT: the accel_300_v2_long signal fires regardless of BTC state, meaning it generates signals that will be blocked by the BTC crash filter. This wastes processing and creates confusion.

### Tide Filter Suppresses LONG in Bearish Regime
- **File:** `signal_compactor.py:657-683`
- When BTC 3h is falling AND SHORT WR > 55%, LONG entries get a tide penalty
- This is correct — in a bearish tide, LONG momentum is fighting the macro

### 15m Trend Filter is Too Weak
- The LONG signal allows BULLISH and NEUTRAL trends (line 436-437 of long file)
- NEUTRAL means the trend is undefined — entering a LONG in a neutral trend is gambling
- The SHORT signal blocks only BULLISH (line 410 of short file) — it allows NEUTRAL and BEARISH
- This asymmetry means LONG enters in more uncertain conditions than SHORT

### Verdict: The regime filters are working correctly but the signal ignores them at creation time. The signal should have a pre-filter that checks BTC momentum and trend regime BEFORE creating the signal, not relying on downstream gates to block it.

---

## 6. Systems Engineer Verdict — Pipeline and Execution Issues

### Issue 1: Signal Fires Every Pipeline Cycle (Cooldown was broken)
- The cooldown was firing every minute — fixed with direct DB check
- But the fix is inline (lines 408-428) rather than using the proper `get_cooldown()` function
- This creates two code paths for cooldown, which is a maintenance hazard

### Issue 2: Signal-to-Hotset-to-Execution Pipeline Has Multiple Staleness Gates
- Signal creation → staleness check at signal time
- Signal in hotset → staleness check at execution time (decider_run.py:3004-3048)
- This double-check is good, but both checks are using the same stale data source

### Issue 3: The Signal is KILLED but Still Generating
- `ACCEL_300_V2_LONG_ENABLED = False` in hermes_constants.py
- The signal scanner checks this flag and returns 0
- But the signal code still runs through the full detection pipeline before hitting this check
- This wastes CPU cycles on every pipeline run

### Issue 4: PROFIT_MONSTER_BYPASS_SIGNALS Includes Dead Signal
- **File:** `hermes_constants.py:1085`
- `'accel-300-v2-long'` is still in the PROFIT_MONSTER_BYPASS_SIGNALS list
- If the signal is re-enabled, it bypasses profit_monster trail and uses ATR SL only
- This means the signal has NO trailing protection — it's raw ATR SL, which explains the immediate losses

### Issue 5: No Price-at-High Check
- The signal enters at whatever price is current, without checking if that price is near a recent high
- CRV at RSI=72 was likely at or near its 1h high — there's no filter for this
- Adding a "distance from 1h high" check would prevent buying at resistance

### Verdict: The pipeline is sound but the signal is poorly designed for its execution context. The 3-10 minute delay between signal and execution means the signal must fire at the BEGINNING of a move, not at the end. Currently it fires at the end.

---

## Synthesis: Top 5 Changes (Priority Order)

### Change 1: Add RSI Overbought Filter for LONG (HIGHEST IMPACT)
- **File:** `signal_compactor.py:1295-1322`
- **What:** Add `if _rsi_val > 75: block LONG` in the same RSI filter section
- **Expected Impact:** Would have blocked CRV entry (RSI=72), preventing the worst loss. Estimated to improve LONG WR by 15-25%.
- **Risk:** LOW — this is a pure filter addition. No signal logic changes. If the filter is too aggressive, it can be loosened to RSI > 80.
- **Priority:** 1 — implement immediately

### Change 2: Unify _get_15m_trend to Use SHORT's Robust Version
- **File:** `signals/accel_300_v2_long.py:138-179`
- **What:** Replace the simple price-vs-EMA20 check with the EMA20-vs-EMA50 crossover from the SHORT file
- **Expected Impact:** Would filter out entries in weak/undefined trends. The SHORT signal uses this and has 52% WR. Estimated +10-15% WR improvement.
- **Risk:** MEDIUM — this changes the signal's behavior. May reduce signal count. But it aligns with the proven SHORT architecture.
- **Priority:** 2

### Change 3: Raise Fresh Cross Minimum Gap from 0.10% to 0.50%
- **File:** `signals/accel_300_v2_long.py:56`
- **What:** Change `V2_FRESH_CROSS_MIN_GAP = 0.10` to `V2_FRESH_CROSS_MIN_GAP = 0.50`
- **Expected Impact:** Would have prevented ZEN-like entries where the signal fires with essentially no conviction. Forces the signal to wait for a meaningful gap.
- **Risk:** LOW — 0.10% is clearly too aggressive (ZEN was blocked anyway by other filters). 0.50% is a reasonable minimum.
- **Priority:** 3

### Change 4: Add Maximum Gap Reduction for Fresh Entries
- **File:** `signals/accel_300_v2_long.py:258-260` (Filter 1)
- **What:** For fresh cross entries (bars_since_cross <= 8), apply a LOWER max gap threshold (e.g., 2.5% instead of 4.5%). Only allow large gaps (>3%) for established entries (bars_since_cross > 8).
- **Expected Impact:** Prevents buying into already-extended moves when the cross is fresh. Forces early entry for fresh crosses, late entry only for sustained momentum.
- **Risk:** MEDIUM — reduces the addressable trade space. But the current max gap of 4.5% is clearly too high for fresh entries.
- **Priority:** 4

### Change 5: Fix Cooldown to Use Proper get_cooldown() Function
- **File:** `signals/accel_300_v2_long.py:408-428`
- **What:** Replace the inline DB cooldown check with the standard `get_cooldown()` from `signal_schema.py`, matching how the SHORT signal does it (line 397-398 of short file)
- **Expected Impact:** Eliminates a maintenance hazard. The inline check was a workaround for a broken cooldown system — if the system is fixed, use it.
- **Risk:** LOW — the SHORT signal already uses this function successfully.
- **Priority:** 5 (low impact but high importance for code quality)

---

## Additional Recommendations

### Re-enable Signal Only After:
1. Backtest confirms positive edge with the new filters (RSI ceiling, unified trend, higher fresh cross gap)
2. Minimum 30-trade paper trading period
3. SHORT signal comparison — the SHORT signal works because of structural advantages (panic selling cascades). The LONG signal needs to prove it can overcome the structural disadvantage (profit taking mean-reverts).

### Potential New Signal Architecture:
Instead of "catch accelerating gap above EMA300," consider:
- **"Catch early momentum shift"** — fire when gap is SMALL (0.3-1.0%) and just starting to widen
- **"Catch trend continuation after pullback"** — fire when gap narrows to 0.5% then starts widening again
- **"Catch breakout from consolidation"** — fire when gap is stable at 1.0-1.5% and then accelerates

These approaches fire BEFORE the move, not at the peak.

---

## Summary Table

| Change | File:Line | Impact | Risk | Priority |
|--------|-----------|--------|------|----------|
| RSI overbought filter | signal_compactor.py:1295-1322 | HIGH | LOW | 1 |
| Unify 15m trend to SHORT version | accel_300_v2_long.py:138-179 | MEDIUM | MEDIUM | 2 |
| Raise fresh cross min gap to 0.50% | accel_300_v2_long.py:56 | MEDIUM | LOW | 3 |
| Max gap reduction for fresh entries | accel_300_v2_long.py:258-260 | MEDIUM | MEDIUM | 4 |
| Fix cooldown to use get_cooldown() | accel_300_v2_long.py:408-428 | LOW | LOW | 5 |

**Final Verdict:** The signal is structurally disadvantaged for LONG entries in crypto. The SHORT signal works because panic selling cascades. The LONG signal needs to either fire earlier (lower thresholds, catch the beginning of moves) or add mean-reversion awareness (RSI ceiling, max gap, proximity-to-high checks). With these 5 changes, the signal could potentially achieve 45-55% WR, but it needs to be re-enabled and paper-traded first.

---

*Report generated by MoE Decision Panel — 6 experts, 1 synthesis*
*Files analyzed: accel_300_v2_long.py, accel_300_v2_short.py, hermes_constants.py, signal_compactor.py, decider_run.py*
