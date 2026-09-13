# SL Memory S/R System — Independent Audit Verdict

**Auditor:** Independent (no priming, fresh read)
**Date:** $(date -Iseconds)
**Files Read:** sl-memory-sr-system.md, signal_compactor.py, volatility_gate_v2.py, hermes_constants.py, position_manager.py, decider_run.py, risk_reward_engine.py
**Data Analyzed:** PostgreSQL brain DB — 744 atr_sl_hit trades, 30-day window

---

## VERDICT 1: Death Zones Are Real

**Claim:** Previous SL hits cluster at specific price levels ("death zones"), creating structural S/R.

**Verdict: AGREE**

**Evidence:**
- 744 ATR SL hits in 30 days (52.7% of all 1,411 closed trades — dominant exit)
- **94 zones** with ≥2 hits across **60 tokens**
- **18.6% re-hit rate** at 0.5% tolerance (110/592 subsequent hits land within 0.5% of a prior SL)
- **50.7% re-hit rate** at 2% tolerance — half of all subsequent SL hits land near a prior hit
- **63 structural re-hit pairs** where entry prices differ by >1% but SLs converge within 0.5% — proves this is NOT mechanical (same ATR → same SL), the market STRUCTURALLY reverses at these levels

**Worst offenders:**
| Token | Zone Re-hits | Total SL Hits | Notes |
|-------|-------------|---------------|-------|
| HYPE | 17 | 28 | SL zone at ~76.51 hit from entries at 74.14, 76.98, 77.04 |
| CRV | 10 | 15 | |
| AVNT | 10 | 13 | |
| SOL | 8 | 13 | |
| GRASS | 5 | 12 | Zone at ~0.367 hit from entries at 0.333 and 0.371 (10% divergence) |

**Confidence: HIGH**

---

## VERDICT 2: Integration Points Exist in Codebase

**Claim:** Spec integrates with RR engine, signal_compactor, position_manager, and decider_run.

**Verdict: AGREE**

**Evidence:**
- ✅ `risk_reward_engine.py` exists (1,178 lines) — evaluates structural R:R, has S/R map builder
- ✅ `signal_compactor.py` exists (4,233 lines) — has SOURCE_WEIGHTS, CONFLUENCE_ENABLED, scoring pipeline
- ✅ `position_manager.py` `get_trade_params()` (line 2008) — computes SL via ATR, returns `stop_loss` and `target`
- ✅ `decider_run.py` reads hotset, calls `get_trade_params`, places trades
- ✅ `volatility_gate_v2.py` — regime classification exists, used by compactor
- ✅ `sl_memory` table does NOT exist yet (verified) — Phase 1 is needed

**Confidence: HIGH**

---

## VERDICT 3: Spec Correctly Identifies the Problem Pattern

**Claim:** "We keep placing stops at the same levels where we keep getting killed."

**Verdict: AGREE**

**Evidence:**
- HYPE: SL zone at ~76.51 gets hit repeatedly from entries spanning 74-77 (3.9% entry divergence)
- ETH: SL zone at ~2516 hit from entries at 2401 and 2499 (4.1% divergence)
- BTC: SL zone at ~78550 hit from entries at 74987 and 79291 (5.7% divergence)
- GRASS: SL zone at ~0.367 hit from entries at 0.333 and 0.371 (10.2% divergence)
- These are NOT identical setups — different entry prices, different ATR — but the same structural level kills the trade

**Confidence: HIGH**

---

## VERDICT 4: ATR SL Calculation Matches Spec's Description

**Claim:** ATR SL = entry ± (ATR × multiplier), currently doesn't account for death zones.

**Verdict: AGREE**

**Evidence from `position_manager.py` (lines 2023-2052):**
```python
atr = _pm_get_atr(token)
atr_pct = atr / price
k = ATR_K_INITIAL  # 1.2
atr_sl_pct = (k * atr) / price
effective_sl_pct = max(atr_sl_pct, ATR_SL_MIN_INIT)  # floor at 1.2%
effective_sl_pct = min(effective_sl_pct, ATR_SL_MAX_INIT)  # cap at 1.5%
stop_loss = price * (1 - effective_sl_pct)  # LONG
```

**From `hermes_constants.py`:**
- `ATR_K_INITIAL = 1.2` (initial SL)
- `ATR_SL_MIN_INIT = 0.012` (1.2% floor)
- `ATR_SL_MAX_INIT = 0.015` (1.5% cap)

**No death zone check exists** anywhere in the SL computation chain. Zero references to `death_zone` or `sl_memory` in the codebase.

**Confidence: HIGH**

---

## VERDICT 5: Spec's Implementation Has Critical Flaws

**Claim:** `calculate_smart_sl()` can move SL below death zones to avoid stop-outs.

**Verdict: DISAGREE (the implementation as written won't work)**

**Evidence — 5 critical issues:**

### Issue 1: ATR Trailing Defeats the Smart SL
- **67.9% of SL hits have SL ≈ exit price** (within 0.2%) — meaning the SL *trailed* into the kill zone
- **92.1% of SL-hit trades saw price go UP first** — ATR trailing moved SL toward the reversal level
- If you set initial SL wider (below death zone), ATR trailing will move it back UP toward the zone as price rises. The trailed SL ends up in the same death zone regardless of initial placement.
- **The spec treats SL as static, but it's dynamic.** This is the fundamental flaw.

### Issue 2: Narrow SL Band
- `ATR_SL_MIN_INIT = 1.2%`, `ATR_SL_MAX_INIT = 1.5%` — only **0.3% of room** to adjust
- 53.8% of SL hits already have SL distance < 1.0% (below the floor) — the trailing pushed SL tighter than the initial band
- Moving SL from 1.2% to 1.5% to avoid a zone is a 25% increase in risk per trade — changes R:R dramatically

### Issue 3: Python Bug in Spec Code
```python
# Line 130 of spec:
lowest_zone = min(z for z in death_zones)  # BUG: min() on Zone objects without key
# Should be:
lowest_zone = min(death_zones, key=lambda z: z.center)
```

### Issue 4: entry_atr_14 is 90.7% NULL
- Only 69/744 SL hits have `entry_atr_14` populated
- The spec's `regime_weight` scoring depends on ATR at entry — most data points won't have it
- The spec's `atr_at_entry` column in `sl_memory` would be NULL for ~90% of records

### Issue 5: `stop_loss` at Close ≠ Initial SL
- `stop_loss` column reflects the TRAILED level at close, not the initial placement
- For 56% of trades, the final `stop_loss` differs from `exit_price` by >0.2% — confirming trailing moved the SL
- The spec's `sl_price` in `sl_memory` would record the trailed exit level, not the level that was initially placed

**Confidence: HIGH**

---

## VERDICT 6: SL Proximity Scoring (Entry Filter) Is Partially Valid

**Claim:** Adding SL proximity score to signal_compactor would filter bad entries.

**Verdict: PARTIAL**

**Evidence FOR:**
- 63 structural re-hit pairs prove that entering near known death zones is dangerous
- A proximity score could reduce entries where the projected SL (even after trailing) would land in a high-density zone
- The compactor already has 15+ scoring dimensions — adding one more is architecturally clean

**Evidence AGAINST:**
- Since SL trails dynamically, the "proposed SL" at entry time won't be the final SL at exit
- The spec calculates `proposed_sl = entry - (atr * DEFAULT_ATR_MULT)` — but the actual SL at death will be higher (trailed up)
- A better approach: check if current price is near a death zone (price approaching the zone), not whether the initial SL would land there

**Confidence: MEDIUM**

---

## VERDICT 7: Position Manager Pre-Trade Check Is Partially Valid

**Claim:** `pre_trade_sl_check()` can catch death zone proximity before trade entry.

**Verdict: PARTIAL**

**Evidence FOR:**
- The `get_trade_params()` function (line 2008) is the exact integration point — SL is computed here
- Adding a zone check between SL computation and return would be clean
- 76 tokens have ≥3 SL hits — enough data for meaningful zones

**Evidence AGAINST:**
- Same trailing problem — the initial SL check doesn't predict where trailing will end up
- The spec's 0.5% proximity threshold is arbitrary and doesn't account for ATR magnitude
- The spec doesn't address what happens when the check fails — skip the trade? Widen SL? The R:R implications aren't analyzed

**Confidence: MEDIUM**

---

## VERDICT 8: Regime Weighting Has Data Support

**Claim:** EXTREME regime SL hits should count 1.5x (volatility magnifies them).

**Verdict: AGREE (partially)**

**Evidence:**
| Regime | SL Hits | % of Total | Avg SL Dist | Avg PnL |
|--------|---------|-----------|-------------|---------|
| EXTREME | 286 | 38.4% | 1.51% | -0.37% |
| NORMAL | 238 | 32.0% | 1.06% | -0.50% |
| HIGH | 219 | 29.4% | 1.10% | -0.74% |

- EXTREME has the most SL hits AND the widest SL distances — supports 1.5x weighting
- But HIGH actually has the worst avg PnL (-0.74%) — should also be weighted up
- The spec only weights EXTREME, not HIGH

**Confidence: MEDIUM**

---

## VERDICT 9: Edge Cases Are Mostly Addressed

**Claim:** Spec handles few data points, zone overlap, stale zones, regime changes, multi-token, over-filtering.

**Verdict: MOSTLY AGREE**

**Evidence:**
- ✅ Minimum 2 hits to form a zone — reasonable
- ✅ Per-token zones — correct (SOL ≠ BONK)
- ✅ 2% proximity check limit — prevents over-filtering
- ✅ Exponential decay for stale zones — sound approach
- ⚠️ Zone overlap (LONG SL = SHORT SL at same price) — spec says "different directions, no conflict" — this is correct but the generated column `zone_type` uses `RESISTANCE`/`SUPPORT` labels that could confuse debugging
- ❌ Missing: no handling for thin-liquidity tokens where 1 SL hit could represent a flash crash, not a real zone

**Confidence: HIGH**

---

## OVERALL VERDICT

### The Phenomenon: AGREE
Death zones are real and statistically significant. 50.7% re-hit rate at 2% tolerance across 744 trades is not noise. The 63 structural re-hit pairs (different entries, same SL level) prove this is market structure, not mechanical coincidence.

### The Solution: DISAGREE (as specified)
The spec treats SL as a static value computed at entry. In reality, ATR trailing moves SL continuously — 67.9% of SL hits have the trailed SL within 0.2% of exit price. The "smart SL" that avoids death zones at entry time will have its SL trailed back into the zone as price rises.

### What Would Work Instead:
1. **Zone-aware entry filtering** (not SL placement): "Is current price approaching a death zone? Skip the trade if price is within X ATR of a zone." This prevents entering BEFORE the zone, not after.
2. **Zone-aware exit timing**: "Price is approaching a known death zone — tighten trailing or exit early." This uses zones as exit signals, not entry filters.
3. **Zone-aware position sizing**: "Zone ahead → smaller position" — reduces exposure without changing SL width.
4. **Record INITIAL SL** (not trailed) in sl_memory — this gives true placement zones. Add `initial_sl` column to sl_memory.
5. **Extend SL_MIN/SL_MAX band** — 0.3% is too narrow for meaningful adjustment. Consider 1.0%-2.0%.

### Bottom Line
The spec correctly diagnoses the disease (death zones kill trades repeatedly) but prescribes the wrong treatment (adjust static SL placement). The real treatment is zone-aware ENTRY and EXIT logic, not zone-aware SL placement. The data is clear: once you enter, trailing will move your SL into the zone regardless.

---

## Recommendations

1. **Do NOT implement `calculate_smart_sl()` as written** — it won't survive ATR trailing
2. **DO implement zone awareness in entry filtering** — check if price is approaching a death zone before entering
3. **DO implement zone-aware exit logic** — tighten PM_TRAIL or exit when price approaches a zone
4. **DO create sl_memory table** with `initial_sl` column (not just `sl_price` which gets trailed)
5. **DO backtest first** — measure how many of the 744 SL hits would have been avoided by entry filtering vs SL adjustment
6. **Fix the Python bug** on spec line 130 (`min()` without key)
7. **Address the data gap** — only 9.3% of SL hits have `entry_atr_14`; need to populate this going forward

**Overall Rating: PARTIAL (35% implementable as-is, 65% needs rethinking)**
