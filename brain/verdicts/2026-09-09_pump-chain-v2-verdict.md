# Independent Audit Verdict: Pump-Chain V2 Spec

**Auditor:** Hermes independent auditor (fresh-eyes, no priming)
**Date:** 2026-09-09
**Files read:** pump-chain-v2-spec.md, pump_flow_signal.py, pump_flow_engine.py
**Data queried:** signals_hermes_runtime.db (73 pump trades), signals_hermes.db (price_history)
**Method:** Independent backtest from scratch — SQL queries, velocity computation, filter application

---

## Summary Table

| Claim | Verdict | Confidence |
|-------|---------|------------|
| Baseline: 73 trades, 42W/31L, 57.5% WR, PnL +0.504 | **AGREE** | HIGH |
| Plan's LONG/SHORT breakdown (27W/13L + 3W/3L) | **DISAGREE** — only covers pump-chain+/- (46 trades), not all 73 | HIGH |
| Claim 1: tok30m filter → 80.4% WR, +1.541 PnL | **PARTIAL** — WR ~80% correct, but PnL is +3.360 not +1.541 | HIGH |
| Claim 2: V2 combined → 86.5% WR, +1.386, PF 2.44 | **PARTIAL** — actually 93.5% WR, +3.489, PF 27.63 (better than claimed) | HIGH |
| Claim 3: SHORT filter catches all 4 SHORT losers | **AGREE** | HIGH |
| Claim 4: Only 1 LONG loser (NEO) remains | **DISAGREE** — 2 LONG losers remain: CHIP and NEO | HIGH |
| Claim 5: V2 saves 6 more winners, catches 1 more loser | **DISAGREE** — saves 4 more winners, catches 3 more losers | HIGH |

---

## Detailed Findings

### 0. Baseline Verification

**Plan claims:** 42W/31L = 57.5% WR, PnL = +0.504
**My backtest:** 42W/31L = 57.5% WR, PnL = +0.504

**Verdict: AGREE**

The overall baseline is exactly correct.

---

### 1. Plan's LONG/SHORT Breakdown (Section 1)

**Plan claims:**
- pump-chain+ (LONG): 27W / 13L = 67.5% WR, PnL = -0.403
- pump-chain- (SHORT): 3W / 3L = 50% WR, PnL = -0.636

**My query:**
- `pump-chain+` signal_type: 40 LONG, 27W/13L, PnL = -0.403 ✓
- `pump-chain-` signal_type: 6 SHORT, 3W/3L, PnL = -0.636 ✓
- But these are only 46 of the 73 trades!

**The other 27 trades:**
- `pump-catcher+`: 20 LONG, 8W/12L, PnL = -0.17
- `pump_chain`: 1 LONG + 2 SHORT, 2W/1L, PnL = +1.442
- Mixed signal types: 4 LONG, 2W/2L, PnL = +0.27

**Full breakdown:**
- ALL LONG (65 trades): 38W/27L, WR=58.5%, PnL=+1.272
- ALL SHORT (8 trades): 4W/4L, WR=50.0%, PnL=-0.768

**Verdict: MISLEADING** — The plan presents pump-chain+/- breakdown as if it's the full picture, but 37% of trades come from other signal types. The plan should have been explicit about this subset.

---

### 2. Velocity Distribution Analysis (Section 2)

**Plan claims:**
- Winners avg tok30m: +0.862%, positive: 86%
- Losers avg tok30m: -0.441%, positive: 29%

**My computation:**
- Winners avg tok30m: +0.956%, positive: 93%
- Losers avg tok30m: -0.399%, positive: 32%

**Verdict: PARTIAL** — The DIRECTION is correct (tok30m is a strong discriminator), but the exact percentages differ. The actual separator power is even stronger than claimed (93% vs 86% for winners).

---

### 3. Claim 1: Token 30m Velocity Filter

**Plan claims:** Block LONG when tok30m < 0% → 46 trades, 80.4% WR, PnL +1.541, PF 2.23, blocked 27 (5W/22L)

**My backtest:**
- 50 trades pass (40W/10L), WR=80.0%, PnL=+3.360, PF=3.62
- 23 blocked (2W/21L)

**Verdict: PARTIAL**
- WR improvement direction is correct (~80%)
- But PnL is +3.360, NOT +1.541 (the plan's number is 55% lower)
- Number of blocked trades differs: 23 vs claimed 27
- Number of blocked winners differs: 2 vs claimed 5
- The filter is actually MORE effective than the plan claims

---

### 4. Claim 2: Combined V2 Filters

**Plan claims (Section 4):**
- V1: 32 trades, 81.2% WR, PnL +0.717, PF 1.72, blocked 41 (16W/25L)
- V2: 37 trades, 86.5% WR, PnL +1.386, PF 2.44, blocked 36 (10W/26L)

**My backtest:**
- V1: 31 trades, 83.9% WR, PnL +1.387, PF 3.20, blocked 42 (16W/26L)
- V2: 31 trades, 93.5% WR, PnL +3.489, PF 27.63, blocked 42 (13W/29L)

**Verdict: PARTIAL**
- V1 and V2 direction is correct (V2 is better than V1)
- But the exact numbers diverge significantly
- V2 is actually MUCH better than claimed (93.5% vs 86.5% WR, PF 27.63 vs 2.44)
- The plan appears to have used different velocity values or a different data snapshot

---

### 5. Claim 3: SHORT Velocity Filter Catches All 4 SHORT Losers

**My verification:**
- ICP SHORT (2 entries): tok30m=+1.314% and +0.521% — both > 0% ✓
- BIGTIME SHORT: tok30m=+0.934% — > 0% ✓
- KAS SHORT: tok30m=+1.468% — > 0% ✓

All 4 SHORT losers have positive tok30m velocity. Both tok30m>0% and tok5m>0% filters catch all 4.

**Caveat:** The filter also blocks 3 SHORT winners (APT, ADA, CAKE) who had positive velocity.

**Verdict: AGREE**

---

### 6. Claim 4: Only 1 LONG Loser (NEO) Remains After V2

**My backtest:** 2 LONG losers pass V2:
1. **NEO** — pnl=-0.102, tok30m=+1.538%, tok5m=+0.541%, btc1h=+0.329%
2. **CHIP** — pnl=-0.029, tok30m=+0.227%, tok5m=+0.021%, btc1h=+0.567%

CHIP passes V2 because its tok30m velocity is +0.227% (barely positive). The plan missed this trade.

**Note:** CHIP's tok30m=+0.227% is a borderline case. If the plan used slightly different velocity values (which it did — see velocity discrepancy analysis), CHIP could have been computed as negative, making it appear to be blocked. This is likely how the error occurred.

**Verdict: DISAGREE** — 2 LONG losers remain, not 1

---

### 7. Claim 5: V2 Saves 6 More Winners, Catches 1 More Loser

**My backtest:**
- Trades saved by V2 (blocked by V1, allowed by V2): 4 trades, ALL winners (DOT, IMX, AIXBT, GRASS)
- Trades extra caught by V2 (allowed by V1, blocked by V2): 4 trades (1W: CASHCAT +0.223, 3L: AIXBT -0.318, ENA -0.035, IMX -0.147)
- Net: +3 winners saved, +3 losers caught

**Plan claims:** +6 winners saved, +1 loser caught

**Verdict: DISAGREE** — saves 4 more winners (not 6), catches 3 more losers (not 1)

---

## Velocity Data Discrepancy Analysis

The plan's velocity values systematically differ from my calculations:

| Trade | Plan's tok30m | My tok30m | Diff |
|-------|--------------|-----------|------|
| NEO LONG | +1.311% | +1.538% | -0.227% |
| APT SHORT | 5m=+1.152% | 5m=+1.012% | +0.140% |
| ICP SHORT | 5m=+0.296% | 5m=+0.279% | +0.017% |
| KAS SHORT | 5m=+1.224% | 5m=+1.046% | +0.178% |
| ICP SHORT (2nd) | 5m=+0.592% | 5m=+0.199% | +0.393% |

**Root cause:** The plan likely computed velocities at a different point in time, when the price_history table had different data. The price collector runs periodically, so the available price points vary. My backtest uses `timestamp <= entry_ts` (correct historical lookback), while the plan may have used a different window.

**Impact:** The discrepancies are small but can affect borderline cases (like CHIP with tok30m=+0.227%).

---

## Edge Cases & Risks

### 1. Missing Data
- **0/73 trades** have missing velocity data — no issue here

### 2. CHIP Borderline Case
- CHIP (LONG loser, pnl=-0.029) passes V2 with tok30m=+0.227%
- This is very close to the 0% threshold
- A small change in velocity computation could flip this trade
- **Risk:** In live trading, velocity values at detection time may differ from historical lookback, causing similar borderline cases

### 3. SHORT Filter Collateral Damage
- The SHORT velocity filter (tok30m > 0%) blocks 3 SHORT winners (APT +0.007, ADA +0.052, CAKE +0.018)
- These are small wins (total +0.077 USDT) but still lost opportunity
- Net benefit is positive (catches 4 losers totaling -0.859 vs blocks 3 winners totaling +0.077)

### 4. Velocity at Detection vs Execution
- The v2 filters check velocity at signal detection time
- If conditions change between detection and execution, trades can pass filters that should block them
- This is already documented in AGENTS.md

---

## Conclusion

The plan's DIRECTION is correct: the V2 filters (tok30m < 0%, tightened tok5m, SHORT velocity) significantly improve win rate and PnL. The core insight — that token 30m velocity is the strongest discriminator between winners and losers — is validated by the data.

However, the specific numbers in the plan are unreliable due to:
1. Velocity data discrepancies (different computation methods or data snapshots)
2. Misleading LONG/SHORT breakdown (only covers pump-chain+/-, not all 73 trades)
3. Missed borderline cases (CHIP passes V2)
4. Incorrect claims about the number of winners saved and losers caught

**The V2 filters should be implemented, but with corrected numbers:**
- Expected WR: ~90%+ (better than claimed 86.5%)
- Expected PnL improvement: substantial (plan's +1.386 is conservative)
- Remaining LONG losers: 2 (CHIP + NEO), not just 1
- SHORT filter catches all 4 losers but also blocks 3 small winners

**Recommendation:** Proceed with V2 implementation using the CORRECTED backtest numbers from this audit, not the plan's numbers. Run the backtest again after implementation to verify.
