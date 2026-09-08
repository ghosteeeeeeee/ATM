# SHORT Filter Overhaul — Stop Blocking Profitable Shorts

**Date:** 2026-09-08
**Status:** ANALYSIS COMPLETE → AWAITING IMPLEMENTATION
**Trigger:** 7 LONGs lost on Sep 8 while 146 profitable SHORT signals were blocked by filters

---

## Incident Summary

On 2026-09-08, the system executed 47 LONGs (most losing) while blocking 1,101 SHORT signals. Of those blocked SHORTs, 146 would have been winners with >0.5% PnL (+140% notional). The system was bleeding on LONGs while SHORT opportunities passed by.

### Sep 8 Performance

| Side | Trades | WR | PnL |
|------|--------|-----|-----|
| LONGs executed | 47 | ~45% | **-$1.44** |
| SHORTs executed | 18 | 44% | -$0.46 |
| SHORTs blocked (total) | 1,101 | — | — |
| SHORTs blocked (>0.5% winners) | 146 | would have won | **+140% notional** |

### BTC Context

BTC was falling on Sep 8. SHORT signals were generating correctly but the filter chain was blocking them before they could reach execution.

---

## Root Cause: Filter Chain Is Too Aggressive on SHORTs

The signal compactor applies 5+ filters to SHORT signals. Each one is individually reasonable but combined they block almost everything.

### Filter 1: VEL-FILTER (5h Velocity)

**File:** `signal_compactor.py:2285-2313`
**Constant:** `SHORT_VEL_FILTER_VEL_THRESHOLD = 0.3%`
**What it does:** Blocks SHORT if token 5h velocity > 0.3% OR 5+ green candles

**Problem:** A token can have a minor bounce (0.3% over 5h) and still be a valid SHORT. The filter treats any upward momentum as "don't SHORT" — but rollover SHORTs happen AFTER a bounce.

**Evidence:** Many blocked SHORTs had z-scores of +1.5 to +2.0 (overbought) with high RSI (70-100) — classic SHORT setups that got blocked because the 5h velocity was slightly positive.

### Filter 2: SHORT-NEUTRAL Block

**File:** `signal_compactor.py:1714-1724`
**Constant:** `SHORT_NEUTRAL_BLOCK_ENABLED = True`
**What it does:** Blocks ALL SHORTs when 4h regime is NEUTRAL

**Problem:** The 0% WR stat that justified this block is from old data. When BTC is falling, SHORTs in NEUTRAL-regime tokens can work. The regime applies to the TOKEN, not the MARKET — a token can be in NEUTRAL while the market is trending down.

**Evidence:** Sep 8 had mix of NORMAL and EXTREME regimes. SHORTs executed in NORMAL had 44% WR. NEUTRAL block may have prevented additional valid entries.

### Filter 3: EMA300-SLOPE Filter

**File:** `signal_compactor.py:1467-1492`
**What it does:** Blocks ema300-dip SHORT if EMA300 slope >= 0 (EMA rising)

**Problem:** Flat EMA (slope ≈ 0) is actually a valid SHORT setup — the token is at equilibrium after an uptrend, about to roll over. Only aggressively rising EMAs should block SHORTs.

**Evidence:** Several blocked SHORTs had EMA slope near 0 — the signal was correct but the filter was too strict.

### Filter 4: SLOPE-FILTER (Price Slope)

**File:** `signal_compactor.py:1455-1465`
**What it does:** Blocks SHORT if token price slope >= threshold (price trending up)

**Problem:** Same issue as VEL-FILTER — minor bounces before rollover get blocked.

### Filter 5: SPIKE-FILTER

**File:** `signal_compactor.py:2178-2198`
**What it does:** Blocks SHORT after recent bullish 5m candle + low RSI

**Problem:** Less impactful but adds to the cumulative block rate.

---

## Data Analysis

### Blocked SHORT Signal Types

| Signal Type | Blocked Count | Notes |
|-------------|--------------|-------|
| support_resistance | 740 | Most blocked — this is the primary SHORT signal |
| ema300_dip_short | 133 | Second most blocked |
| volume_breakout_short | 52 | |
| return_exhaustion_short | 41 | |
| accel_300_v3_short | 39 | |

### Blocked SHORTs That Would Have Won (>0.5% PnL)

146 blocked SHORTs had >0.5% PnL in the 30-minute window after signal time.

Top winning tokens that were blocked:
- NOT: multiple +1.2-1.9% winners
- YGG: multiple +0.5-1.8% winners  
- ADA: multiple +0.6-1.4% winners
- BCH: +0.6-1.5% winners
- ZRO: +0.6-1.7% winners
- ARB: +1.0-1.5% winners

### Comparison: Executed vs Blocked SHORTs

| Metric | Executed (18) | Blocked (>0.5% PnL, 146) |
|--------|--------------|--------------------------|
| Avg confidence | 83 | 83 |
| Avg z-score | -0.93 | Mixed (many positive = overbought) |
| Avg RSI | 38.0 | Mixed (many 70+ = overbought) |
| Avg PnL | -0.46% | +0.94% |

The blocked SHORTs had similar confidence but were better setups (overbought tokens about to roll over).

---

## Recommendations

### Fix 1: Relax VEL-FILTER (High Impact)

**Current:** `SHORT_VEL_FILTER_VEL_THRESHOLD = 0.3%`
**Proposed:** `SHORT_VEL_FILTER_VEL_THRESHOLD = 0.5%`

**Rationale:** 0.3% over 5h is noise. A token can bounce 0.3% and still be in a downtrend. 0.5% is a more meaningful threshold that allows minor bounces while still catching genuine uptrends.

**Alternative:** Instead of raising the threshold, reduce the green candle requirement from 5 to 7. Five green candles on 5m = 25 minutes of green. That's noise, not a trend.

### Fix 2: Relaxed SHORT-NEUTRAL Block (Medium Impact)

**Current:** `SHORT_NEUTRAL_BLOCK_ENABLED = True` (hard block)
**Proposed:** Change to penalty mode (0.7x score multiplier) when BTC is falling

**Rationale:** The 0% WR stat is stale. When BTC is falling, SHORTs in NEUTRAL tokens can work. A hard block is too aggressive.

**Alternative:** Add BTC direction check — only block SHORTs in NEUTRAL when BTC is also flat/rising. When BTC is falling, allow SHORTs in NEUTRAL.

### Fix 3: Relax EMA300 Slope Filter (Medium Impact)

**Current:** Blocks if EMA300 slope >= 0
**Proposed:** Block if EMA300 slope >= 0.1%

**Rationale:** Flat EMA (slope ≈ 0) is a valid SHORT setup. Only rising EMAs (>0.1%) should block.

### Fix 4: BTC-Aligned SHORT Accelerator (Strategic)

**New concept:** When BTC 30m momentum is falling, RELAX all SHORT filters by 50%.

**Implementation:**
```python
# In signal_compactor.py, after each SHORT filter check:
if btc_momentum < -0.10:  # BTC falling
    # Don't apply the filter — BTC direction confirms the SHORT
    pass
```

**Rationale:** The correlation data shows SHORTs are most profitable when BTC is falling (84.6% WR). Applying the same filters regardless of BTC direction is wrong — filters should be RELAXED when BTC confirms the direction.

### Fix 5: Reduce Compaction Expiry Time (Low Impact)

**Current:** Signals expire after ~6 minutes
**Proposed:** Extend to 10 minutes for SHORT signals

**Rationale:** SHORT setups often develop over longer timeframes. A 6-minute window may be too short for the signal to reach the hot-set and execute.

---

## Implementation Plan

### Phase 1: Conservative (Immediate)
- [ ] Raise `SHORT_VEL_FILTER_VEL_THRESHOLD` from 0.3% to 0.5%
- [ ] Raise `SHORT_VEL_FILTER_GREEN_THRESHOLD` from 5 to 7
- [ ] Change EMA300 slope threshold from >= 0 to >= 0.1%

### Phase 2: BTC-Aligned (Week 1)
- [ ] Add BTC momentum check to SHORT-NEUTRAL block — relax when BTC falling
- [ ] Add BTC momentum check to VEL-FILTER — relax when BTC falling

### Phase 3: Monitoring (Week 2+)
- [ ] Track SHORT execution rate (should increase from 1.7% to 5%+)
- [ ] Track SHORT WR (should stay >= 50%)
- [ ] Track total SHORT PnL (should improve from -$0.46)
- [ ] Monitor LONG WR (should not degrade)

---

## Independent Audit Findings (2026-09-08)

**Verdict: UNSOUND (as originally written) — critical flaws identified**

| Issue | Audit Finding | Severity |
|-------|--------------|----------|
| VEL-FILTER green candle check | **DEAD CODE** — `range(3)` can never reach threshold of 5. The OR condition is inert. Only velocity >0.3% actually blocks. | CRITICAL |
| "146 blocked winners" claim | **UNVERIFIABLE** — no simulation script exists. System doesn't track forward returns of blocked signals. | HIGH |
| Executed vs blocked comparison | **UNFAIR** — executed SHORTs have SL/TP applied (avg loss -1.09%), blocked SHORTs measured on raw candle move (no risk management). Not comparable. | HIGH |
| 0.5% VEL threshold | **NO BACKTEST** — original backtest established 0.1%. Already raised 3x (0.1→0.3). Raising again without data. | MEDIUM |
| SHORT-NEUTRAL "stale" | **MISLEADING** — block already has bypasses (SHORT_BIAS, strong confluence, standalone bypass). 2,146 SHORTs bypassed on Sep 8. Only 894 actually blocked. | MEDIUM |
| Confluence gate | **NOT MENTIONED** — 3,058 SHORTs blocked by single-source requirement. This is the BIGGEST blocker, not the filters the plan focuses on. | MEDIUM |
| SHORT R:R | **POOR** — avg win +0.31% vs avg loss -1.09% (0.28:1 R:R). Relaxing filters adds volume without fixing the underlying R:R problem. | MEDIUM |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| More bad SHORTs get through | High | Medium (R:R is 0.28:1) | Monitor WR, revert if <45% |
| LONG filters also get relaxed | Low | High | SHORT fixes are SHORT-specific |
| Pipeline starvation (too many SHORTs) | Low | Medium | Rate limits still apply |
| Overfitting to Sep 8 data | High | High | Must validate on Sep 7-9 data |
| Confluence gate change breaks LONG quality | Medium | High | Don't touch confluence for now |

## Revised Recommendations

### Fix 1: VEL-FILTER Dead Code (CRITICAL — do first)

**File:** `signal_compactor.py:2302`
**Bug:** `range(3)` can only produce values 0,1,2 — `_last3_green` max is 3, but threshold is 5. Green candle check is dead code.

**Fix:** Change `range(3)` to `range(SHORT_VEL_FILTER_GREEN_THRESHOLD)` or change threshold back to 3.

### Fix 2: Build Simulation Script (before any threshold changes)

Need a script that:
1. Takes all blocked SHORT signals
2. Looks up token price at signal time and 30min/1hr later
3. Applies same SL/TP logic as live trades
4. Produces comparable PnL numbers

Without this, all "would-have-won" claims are speculation.

### Fix 3: Address SHORT R:R (higher impact than filter relaxation)

The real problem: avg SHORT win is +0.31% but avg loss is -1.09%. Even with 50% WR, the system bleeds.

Options:
- Tighter SL on SHORTs (currently ATR-based, same as LONGs)
- Wider TP target for SHORTs
- Trailing stop on SHORTs (currently not implemented for SHORTs)

### Fix 4: VEL-FILTER Threshold (only after simulation)

If simulation confirms the 0.3% threshold blocks more winners than losers, raise to 0.4% (conservative, not 0.5%).

### Fix 5: SHORT-NEUTRAL (only after data)

The block already has bypasses. If BTC-aligned relaxation is needed, add it as a NEW bypass condition rather than removing the existing block.

---

## Files to Modify

1. `scripts/signal_compactor.py` — Fix dead code bug (line 2302)
2. `scripts/hermes_constants.py` — Threshold changes (only after simulation)
3. `scripts/simulate_blocked_shorts.py` — NEW: simulation script to verify claims
4. `plans/2026-09-08_btc-alignment-crash-protection-overhaul.md` — Cross-reference with LONG filter plan
