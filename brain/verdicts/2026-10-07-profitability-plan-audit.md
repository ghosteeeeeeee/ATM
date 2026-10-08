# Independent Audit: Profitability Fix Plan (2026-10-07)

**Auditor:** Independent verifier (fresh analysis, no reliance on plan author's work)
**Date:** 2026-10-07
**Plan under review:** `/root/.hermes/plans/profitability-fix-plan-2026-10-07.md`
**Data sources queried:** PostgreSQL brain DB (5,614 trades), candles.db (5m/1h), continuum.db, signals_hermes_runtime.db

---

## Executive Summary

The plan identifies a real problem (system losing money, entry timing issues) but contains **significant factual errors** in its supporting data. Two of five key claims are wrong, one is partially wrong, and two are directionally correct but contain stale/incorrect specifics. The Priority 1 recommendation (move-done velocity filter) is **actively harmful** based on independent backtesting — it blocks the trades that win. Priority 2 (widen CUT_LOSER_PNL) is directionally sound but the plan works from stale numbers.

| Claim | Verdict |
|-------|---------|
| 1. Winners before dump, losers after | **PARTIAL** — pattern holds for some trades but plan cherry-picked 5 of 16 and mischaracterized LDO |
| 2. Velocity filter +3.5%/+4.0% WR | **DISAGREE** — numbers not reproducible; filter hurts at every threshold tested |
| 3. 505 SHORT signals expired via SHORT-CONTINUUM | **PARTIAL** — phenomenon real, number not reproducible, causal attribution unverifiable |
| 4. Hard max loss -0.20% but exits at +0.28%–1.11% | **AGREE** — confirmed, but CUT_LOSER_PNL already changed to -1.50 |
| 5. Only 12.6% continuum coverage | **PARTIAL** — concern valid, but specific numbers (12.6%, Sep 4–21, 5,235) all wrong |

| Recommendation | Verdict |
|----------------|---------|
| Priority 1: Move-done filter (0.5% 5m) | **DISAGREE** — backtest shows it reduces WR; filter direction is backwards |
| Priority 2: CUT_LOSER_PNL → -2.50 | **PARTIAL** — direction supported, but value is aggressive and premise is stale |
| Priority 3: Grind detection | **AGREE** (conceptual — no data to verify yet) |
| Priority 4: Backfill continuum DB | **AGREE** — coverage gap is real |

---

## Claim 1: "Winners entered BEFORE the dump, losers entered AFTER the dump was over"

**Verdict: PARTIAL**

### What the plan claims
A table of 5 pump-chain trades from "last 3 days" showing APT/LTC as winners (entered during dump) and IO/LDO/INJ as losers (entered after dump).

### What I found

The plan says "Traced price action for all pump-chain trades (last 3 days)" — there are actually **16 pump-chain trades** opened Oct 4–7, not 5. The plan cherry-picked 5.

I traced price action for all 16 using candles.db 5m data:

| Token | Dir | PnL% | 30m Before | 5m Vel | 60m After | Pattern |
|-------|-----|------|------------|--------|-----------|---------|
| IMX | LONG | +2.07 | +0.60% | +0.05% | +0.22% | Winner: entered during pump |
| GMT | LONG | +1.36 | +0.22% | -0.11% | +1.33% | Winner: flat entry, continued up |
| HBAR | SHORT | +2.46 | -0.65% | +0.35% | -0.26% | Winner: entered during dump |
| LTC | SHORT | **-5.57** | -0.45% | -0.22% | +0.65% | **Loser: after dump, bounced** ✅ |
| DOGE | SHORT | +3.59 | -0.25% | -0.11% | -0.15% | Winner: flat, continued down |
| IO | SHORT | **-3.15** | -1.44% | -0.47% | +0.88% | **Loser: after dump, bounced** ✅ |
| LTC | SHORT | +13.64 | -0.03% | +0.30% | -0.36% | Winner: flat, continued down |
| APT | SHORT | +23.89 | -0.68% | +0.00% | -4.75% | Winner: entered during dump ✅ |
| INJ | SHORT | **-1.43** | +0.33% | +0.13% | +1.09% | **Loser: wrong direction** ✅ |
| IMX | LONG | **-1.67** | +0.63% | +0.23% | +0.45% | Price went WITH trade, but hard_max_loss fired |
| ADA | SHORT | **-1.42** | +0.12% | +0.19% | -0.78% | Price went WITH trade (down), but hard_max_loss fired |
| LDO | SHORT | **-1.61** | -0.71% | -0.05% | **-0.80%** | Price CONTINUED DOWN — hard_max_loss fired prematurely |
| LDO | LONG | **-3.15** | -0.55% | -0.81% | +0.00% | Mixed; entered after dump |
| GRASS | SHORT | -0.00 | -0.39% | +0.26% | +0.60% | Loser: after dump, bounced |
| FIL | SHORT | **-2.70** | -0.34% | -0.29% | +0.18% | Loser: after dump, slightly bounced |
| APT | SHORT | **-0.47** | -1.05% | -0.11% | -0.40% | Price went WITH trade, but hard_sl fired |

### Key findings

1. **The pattern holds for IO, LTC(-5.57), FIL, GRASS** — these entered after the dump and price bounced against them. ✅

2. **LDO SHORT is mischaracterized by the plan.** The plan says "LDO -1.6% | -1.09% (already dumped) | -0.67% (bounced)". My candle data shows 60min after entry price was **-0.80%** (continued DOWN, in the SHORT's favor). The trade lost because hard_max_loss exited it at -0.29% price move before the move completed. **This is evidence FOR the hard_max_loss being too tight, NOT against entry timing.**

3. **Four "losers" show favorable post-entry price action** — IMX LONG (+0.45% after), ADA SHORT (-0.78% after), LDO SHORT (-0.80% after), APT SHORT (-0.40% after). All four lost to hard_max_loss/hard_sl firing prematurely. **The real problem for these trades is the stop, not the entry.**

4. **The plan omits HBAR +2.46% and DOGE +3.59%** — winners that entered during/flat before the move, consistent with the pattern but not shown.

### Bottom line
The "winners before, losers after" narrative is **partially supported** — it explains IO, LTC(-5.57), FIL, and GRASS. But it **misses the bigger issue**: several losers were actually good entries killed by premature hard_max_loss exits. The plan's focus on entry timing may be addressing a secondary problem while the primary bleed (hard_max_loss: 0% WR, 66 trades, -$9.04) goes unaddressed by Priority 1.

---

## Claim 2: "Velocity filters help marginally: 30m at 3.0% gives +3.5% WR, 5m at 0.5% gives +4.0% WR"

**Verdict: DISAGREE**

### What the plan claims
| Filter | Threshold | Allowed WR | Improvement |
|--------|-----------|------------|-------------|
| None (baseline) | — | 48.0% | — |
| 30m velocity | 3.0% | 51.5% | +3.5% |
| 5m velocity | 0.5% | 52.0% | +4.0% |

### What I found — independent backtest

I computed 5m and 30m velocity at entry for all 289 pump-chain trades using candles.db, then tested move-done filters at multiple thresholds.

**Baseline (all 289 pump-chain trades):** 155W / 134L = **53.6% WR** — NOT 48.0%.
The closest subset to 48% is pump-chain+ (LONG only) at 47.9%, but the plan doesn't specify this.

**5m velocity move-done filter** (block SHORT if v5 < -thr, block LONG if v5 > thr):

| Threshold | Trades Kept | Wins | Losses | WR | Δ vs baseline |
|-----------|------------|------|--------|-----|---------------|
| 0.3% | 66 | 32 | 34 | 48.5% | **-5.1pp** |
| **0.5%** | **76** | **38** | **38** | **50.0%** | **-3.6pp** |
| 0.7% | 77 | 39 | 38 | 50.6% | -3.0pp |
| 1.0% | 80 | 41 | 39 | 51.2% | -2.4pp |

Only 80/289 trades have 5m candle data — the filter can only be evaluated on 28% of trades.

**30m velocity move-done filter:**

| Threshold | Trades Kept | Wins | Losses | WR | Δ vs baseline |
|-----------|------------|------|--------|-----|---------------|
| 1.0% | 186 | 95 | 91 | 51.1% | -2.6pp |
| 2.0% | 247 | 126 | 121 | 51.0% | -2.6pp |
| **3.0%** | **266** | **139** | **127** | **52.1%** | **-1.4pp** |
| 5.0% | 272 | 141 | 131 | 51.8% | -1.8pp |

**The move-done filter REDUCES win rate at every threshold tested.** The plan's claimed improvements (+3.5pp and +4.0pp) are in the opposite direction of what the data shows.

### Why the filter hurts

I tested the **opposite** filter — requiring token to already be moving in the signal direction at entry ("allow-only"):

| Min 5m velocity (in signal direction) | Trades | Wins | Losses | WR | Δ |
|---------------------------------------|--------|------|--------|-----|---|
| 0.0% (any momentum) | 32 | 21 | 11 | **65.6%** | +12.0pp |
| 0.1% | 27 | 20 | 7 | **74.1%** | +20.4pp |
| 0.2% | 19 | 12 | 7 | 63.2% | +9.5pp |

**Trades where the token is ALREADY moving in the signal direction at entry have 65–75% WR**, vs 53.6% baseline. The move-done filter blocks exactly these trades. The filter direction is backwards.

(Sample sizes are small — 4 to 32 trades — so these numbers are suggestive, not conclusive. But the direction is consistent across every threshold.)

### Code reality check

The plan's code snippet proposes `PUMP_FLOW_MOVE_DONE_THRESHOLD = 0.5` on 5m velocity. The **actual implemented code** uses `PUMP_FLOW_MOVE_DONE_THRESHOLD = 3.0` on **30m** velocity (`pump_flow_signal.py:334-340`, `hermes_constants.py:3859`). The plan's snippet doesn't match what's in the codebase.

### Where might 48% baseline come from?
- pump-chain+ (LONG) only: 47.9% — closest match
- Last 7 days (Sep 30+): 46.3%
- Last 3 days (Oct 4+): 37.5%
- None of these subsets reproduce the claimed +3.5pp or +4.0pp improvements

### Bottom line
**The velocity filter numbers are not reproducible from the trade data.** The move-done approach reduces WR because it blocks momentum trades, which are the winners. If anything, the data suggests a momentum-REQUIREMENT filter (only trade when token is already moving in signal direction) could help — but needs validation on larger samples.

---

## Claim 3: "505 pump-chain SHORT signals expired due to SHORT-CONTINUUM filter"

**Verdict: PARTIAL**

### What the plan claims
505 pump-chain SHORT signals expired in 24h, root cause SHORT-CONTINUUM filter (BTC score > 40 blocks SHORTs).

### What I found

**Runtime DB (signals_hermes_runtime.db) expired pump-chain SHORT signals by day:**

| Date | Expired pump-chain SHORTs |
|------|--------------------------|
| Sep 28 | 187 |
| Sep 29 | 455 |
| Sep 30 | 481 |
| Oct 1 | 469 |
| Oct 2 | 441 |
| Oct 3 | 296 |
| Oct 4 | 209 |
| **Oct 5** | **790** |
| Oct 6 | 439 |
| Oct 7 | 325 |

**I cannot reproduce 505 from any single day.** The closest single-day numbers are 790 (Oct 5) or 439 (Oct 6). The number 505 might come from a specific 24h window that spans two calendar days, or a different counting method.

**Causal attribution to SHORT-CONTINUUM is unverifiable:**
- Zero signals have "continuum" in `rejection_reason` or `decision_reason`
- The SHORT-CONTINUUM filter in `signal_compactor.py:2822-2873` blocks via `continue` — it skips the signal during compaction without recording a rejection reason
- Expired signals expire for many reasons (staleness, compaction rounds, TTL). Not all expiries are caused by SHORT-CONTINUUM.

**However, the phenomenon is directionally real:**
- On Oct 5 (24h before the fix), 790 pump-chain SHORTs expired
- Of those with btc_score in metadata: 373 (47.2%) had btc_score > 40
- At the old threshold (SHORT_CONTINUUM_SCORE_MAX=40), these would have been blocked by SHORT-CONTINUUM
- After the fix (raised to 60 on Oct 6), Oct 7 still had 325 expiries — but we can't attribute the reduction to the fix vs. natural variation

**Note:** The fix (40→60) is already applied per `hermes_constants.py:1353`. The plan describes it as done.

### Bottom line
The concern is valid — hundreds of pump-chain SHORTs were expiring daily, and a substantial fraction had btc_score > 40. But the specific number (505) is not reproducible, and the causal chain (SHORT-CONTINUUM → expiry) cannot be verified from the data because the filter doesn't record rejection reasons.

---

## Claim 4: "Hard max loss fires at -0.20% price move (5x leverage) but actual exits at +0.28% to +1.11%"

**Verdict: AGREE** (with an important caveat)

### What the plan claims
Hard max loss threshold at 5x leverage is -0.20% price move, but actual exit price moves range from +0.28% to +1.11%.

### What I found

**Code confirms the mechanism** (`position_manager.py:3395-3406`):
```
HARD_MAX_LOSS_PCT = CUT_LOSER_PNL / leverage
```
At CUT_LOSER_PNL=-1.00, lev=5: threshold = -0.20% price move. ✅

**⚠️ CAVEAT: CUT_LOSER_PNL is already -1.50, not -1.00.** Changed on Oct 7 by brain_auditor (`hermes_constants.py:707`). Current threshold at 5x is **-0.30%**, not -0.20%. The plan's table is stale.

**My analysis of all 66 hard_max_loss exits:**

| Leverage | n | Actual price moves at exit | Mean | Median |
|----------|---|---------------------------|------|--------|
| 5x | 38 | +0.28% to +3.18% | +0.72% | +0.77% |
| 3x | 28 | +0.33% to +1.20% | +0.71% | +0.70% |

For pump-chain-specific hard_max_loss exits, the range +0.28% (INJ) to +1.11% (LTC) matches the plan. ✅

**exit_conditions field confirms slippage:**
- LDO SHORT: `hard_max_loss_pct=-0.29%,lev=5.0,thresh=-0.20%` — actual 0.29% vs threshold 0.20%
- FIL SHORT: `hard_max_loss_pct=-0.48%,lev=5.0,thresh=-0.20%` — actual 0.48% vs threshold 0.20%
- IO SHORT (3x): price moved +1.05% against trade before exit

**Hard_max_loss cohort stats:**
- 66 total exits, **0% WR** (0 wins), total bleed **-$9.04**
- Last 7 days: 64 trades, 0 wins, -$8.60
- **86.4% had MFE > 0** — were in profit at some point before the stop fired
- Pump-chain subset: 22 trades, 0 wins, -$2.82

### Bottom line
The claim is correct: the hard max loss threshold is much tighter than where exits actually happen, due to polling latency and slippage. The exit_conditions field provides direct evidence. However, the plan's table uses stale CUT_LOSER_PNL=-1.00; the current value is -1.50. The broader finding — hard_max_loss is the #1 bleed source with 0% WR — is well-supported.

---

## Claim 5: "Only 12.6% of trades have BTC continuum data"

**Verdict: PARTIAL**

### What the plan claims
660/5,235 trades = 12.6% have BTC continuum data matched. Continuum.db covers Sep 4–21 only (17 days).

### What I found

**Continuum.db actual coverage:**
- `continuum_states` table: **Aug 12 – Oct 7** (56 days, 129,285 rows, BTC only, 1m timeframe)
- `continuum_states_backfill` table: Aug 12 – Sep 3 (33,092 rows)
- The plan's "Sep 4–21 (17 days)" claim is **wrong** — the DB covers 56 days, not 17

**Trade counts:**
- Total trades in PostgreSQL: **5,614** (not 5,235 — plan used a stale count)
- Trades within continuum.db date range (Aug 12 – Oct 7): **2,277 (40.6%)** — not 12.6%
- Trades with `signal_z_score` not null: **3,514 (62.6%)**

**Z-score coverage by month (the real gap):**

| Month | Total | With z_score | Coverage |
|-------|-------|-------------|----------|
| May | 536 | 536 | 100% |
| Jun | 1,551 | 1,551 | 100% |
| Jul | 703 | 639 | 90.9% |
| Aug | 1,567 | 761 | 48.6% |
| **Sep** | **1,053** | **0** | **0%** |
| Oct | 202 | 27 | 13.4% |

**The real problem:** z_score data stopped being recorded in September (0% coverage). The continuum.db has BTC data for Aug 12 – Oct 7, but the trades from September have no z_score in their signal_metadata. May–Aug 11 trades have no continuum.db data at all.

**The 660/5,235 = 12.6% figure is not reproducible** from any query I ran. The denominator (5,235) doesn't match current totals, and the numerator (660) doesn't match any obvious subset.

### What IS true
- Continuum.db does NOT cover the full trading history (May 20 – Aug 11 = ~84 days missing)
- September trades have 0% z_score coverage — oscillator-based filters can't be validated on them
- The underlying concern (insufficient continuum data for oscillator filter validation) is **valid**

### Bottom line
The specific numbers are wrong (12.6%, Sep 4–21, 5,235), but the concern about insufficient continuum coverage is legitimate. The actual gap is: (a) May 20 – Aug 11 has no continuum.db data, and (b) September trades have no z_score recorded. A backfill would help but the plan should use correct numbers.

---

## Question 6: Is the move-done filter threshold (0.5% 5m) well-chosen?

**Verdict: NO — DISAGREE with the approach entirely**

The threshold choice is secondary to the fundamental problem: **the filter direction is backwards.**

My backtest shows:
- Blocking trades where token already moved in signal direction (move-done) **reduces WR** at every threshold: 0.3% → -5.1pp, 0.5% → -3.6pp, 1.0% → -2.4pp
- Requiring trades where token is already moving in signal direction (momentum-requirement) **increases WR**: 0.0% → +12.0pp, 0.1% → +20.4pp (small samples)

The plan's intuition — "token already moved, move likely over" — is contradicted by the data. In pump-chain trades, momentum at entry is a **positive** predictor of success, not negative. The 0.5% threshold is irrelevant if the filter itself is harmful.

Additionally, the actual code implements a **30m** filter at **3.0%**, not a 5m filter at 0.5% as the plan proposes. The plan's code snippet doesn't match the codebase.

**Recommendation:** Do not deploy the move-done filter. If pursuing velocity-based filters, test a momentum-REQUIREMENT filter (only trade when token velocity is already in signal direction) on a larger sample first.

---

## Question 7: Is CUT_LOSER_PNL -2.50 reasonable?

**Verdict: PARTIAL — direction is supported, but the value is aggressive and the plan's premise is stale**

### Current state
- CUT_LOSER_PNL is already **-1.50** (changed from -1.00 on Oct 7 by brain_auditor)
- The plan proposes -2.50, framed as "from -1.00" — **stale premise**
- At -1.50, lev=5: HARD_MAX_LOSS_PCT = -0.30% price move (not -0.20% as plan states)

### Evidence supporting widening
- hard_max_loss cohort: **0% WR** (0/66), -$9.04 bleed, #1 loss source
- **86.4% had MFE > 0** — trades were in profit before stop fired
- trail_family exits: 120 trades, 87.5% WR, +$9.47 — the winning exit mechanism needs room
- The constant's own comment: "Widen gives trail ~50% more room. Cannot block winners (HML only fires on losers)."

### Evidence against going to -2.50
- The cohort is 0% WR — **none of the 66 trades recovered**, even though 86.4% were in profit at some point. Widening gives more room, but these trades show no winners even with MFE>0.
- At -2.50 with lev=5: threshold = -0.50% price move. A single bad trade loses 2.5% of account. With 16 pump-chain trades in 3 days, that's meaningful tail risk.
- The current -1.50 already provides 50% more room than -1.00. Going to -2.50 is a 67% increase from current.
- **The real question is entry quality**: if 86.4% of hard_max_loss trades were in profit at some point but all ended as losers, the problem may be that these are bad trades that briefly go green, not good trades that need more room.

### What would be more reasonable
- **Monitor the current -1.50 for 48–72 hours** before going further. The change was made today (Oct 7); there's no post-change data yet.
- If hard_max_loss frequency doesn't drop, consider -2.00 as an intermediate step rather than jumping to -2.50.
- Pair any widening with an MFE-based filter: if a trade hits hard_max_loss but had MFE > +0.5%, that's a different failure mode than a trade that never went green.

---

## Additional Findings (beyond plan scope)

### Finding A: The plan's "last 3 days" table is incomplete
**Severity: Medium.** The plan shows 5 trades but says "all pump-chain trades (last 3 days)." There are 16. The omitted 11 trades include 2 winners (HBAR +2.46%, DOGE +3.59%) and several losers where hard_max_loss — not entry timing — was the proximate cause. This cherry-picking biases the analysis toward the plan's narrative.

### Finding B: hard_max_loss is a bigger problem than entry timing
**Severity: High.** The plan's Priority 1 addresses entry timing, but the data shows:
- hard_max_loss: 66 trades, **0% WR**, -$9.04
- Of 16 pump-chain trades in last 3 days, **8 exited via hard_max_loss** (50%)
- At least 4 of those 8 had favorable post-entry price action — they would have been profitable if held
- The plan's Priority 2 (widen CUT_LOSER_PNL) addresses this, but it's listed as Priority 2 behind the harmful Priority 1

**Recommendation:** Prioritize the hard_max_loss fix over the move-done filter.

### Finding C: 5m candle data coverage is sparse
**Severity: Medium.** Only 80/289 pump-chain trades (27.7%) have 5m candle data in candles.db. Any 5m-velocity-based filter can only be backtested on ~28% of trades. The plan doesn't mention this limitation. If pursuing velocity filters, first ensure 5m candle coverage is sufficient.

### Finding D: Plan's code snippet doesn't match codebase
**Severity: Low.** The plan proposes `PUMP_FLOW_MOVE_DONE_THRESHOLD = 0.5` on 5m velocity. The codebase has `PUMP_FLOW_MOVE_DONE_THRESHOLD = 3.0` on 30m velocity. Either the plan is proposing a change from the current implementation, or it's describing something different than what's deployed. This should be clarified before any code changes.

### Finding E: Continuum.db coverage claim is wrong
**Severity: Low.** Plan says "Sep 4–21 (17 days)." Actual: Aug 12 – Oct 7 (56 days). The backfill table covers Aug 12 – Sep 3. The plan author may have queried the wrong table or an outdated snapshot. The underlying concern (coverage gap for May–Aug) is still valid.

---

## Verdict Summary

| # | Claim | Verdict | Key evidence |
|---|-------|---------|--------------|
| 1 | Winners before dump, losers after | **PARTIAL** | Pattern holds for IO/LTC(-5.57)/FIL/GRASS, but LDO is mischaracterized (price continued down) and 4 losers were killed by premature stops, not bad timing |
| 2 | Velocity +3.5%/+4.0% WR | **DISAGREE** | Baseline is 53.6% not 48%; move-done filter reduces WR at every threshold (-1.4pp to -5.1pp); momentum trades are winners |
| 3 | 505 SHORTs expired via SHORT-CONTINUUM | **PARTIAL** | 209–790/day expired, 47% had btc_score>40; but 505 not reproducible and causal chain unverifiable |
| 4 | Hard max loss -0.20% vs exits +0.28%–1.11% | **AGREE** | exit_conditions confirms; 66 exits, 0% WR, -$9.04; but CUT_LOSER_PNL already -1.50 |
| 5 | 12.6% continuum coverage | **PARTIAL** | Continuum.db covers Aug 12–Oct 7 (not Sep 4–21); z_score 0% in Sep; but 12.6%/5,235 not reproducible |

| # | Recommendation | Verdict | Action |
|---|---------------|---------|--------|
| P1 | Move-done filter (0.5% 5m) | **DISAGREE** | Do not deploy. Filter direction is backwards; blocks winning momentum trades. |
| P2 | CUT_LOSER_PNL → -2.50 | **PARTIAL** | Direction supported (0% WR cohort needs room), but monitor current -1.50 first; consider -2.00 as intermediate. Premise is stale (already -1.50). |
| P3 | Grind detection | **AGREE** | Sound concept; no data to verify yet. Reasonable long-term investment. |
| P4 | Backfill continuum DB | **AGREE** | Coverage gap is real (May–Aug 11 missing, Sep z_score=0%). Use correct numbers (not 12.6%/Sep 4–21). |

---

## Recommended Priority Order (revised)

1. **Fix hard_max_loss first** — it's the #1 bleed (0% WR, -$9.04, 50% of recent pump-chain exits). Monitor current -1.50; widen further only if frequency doesn't drop.
2. **Do NOT deploy the move-done filter** — it hurts. If pursuing velocity filters, test momentum-REQUIREMENT (opposite direction) on larger samples.
3. **Backfill continuum DB** with correct target dates (May 20 – present, not Sep 4–21).
4. **Grind detection** as long-term project — concept is sound.
5. **Re-run the plan's analysis** with correct baselines (53.6% not 48%), all 16 recent trades (not 5), and current constant values (-1.50 not -1.00).

---

*Audit methodology: All numbers computed from live databases via independent SQL queries and Python analysis. No figures taken from the plan without verification. Velocity backtests computed from candles.db 5m data joined to PostgreSQL trade entries. Price action traced from candles.db for all 16 pump-chain trades opened Oct 4–7.*
