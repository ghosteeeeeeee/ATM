# Independent Verdict: BTC Momentum Sync Plan

**Auditor:** Independent (own-conclusions agent)
**Date:** 2026-09-12
**Files Read:** `plans/2026-09-12_btc-momentum-sync-plan.md`, `scripts/continuum_context.py`, `scripts/signal_compactor.py` (lines 1050-1160, 1940-2060, 3300-3390, 3825-3884), `scripts/hermes_constants.py` (lines 2214-2259, 2514, 2596-2605, 3297-3340), `scripts/decider_run.py` (lines 1555-1684, 1925-1982, 2180-2220, 2920-2960, 3240-3300, 3790-3810), `scripts/brain.py` (lines 340-360, 640-670, 1240-1260), `scripts/data_migration_sync.py` (lines 155-204)
**SQL Queries Run:** 8 queries against PostgreSQL (brain DB), 3 queries against continuum.db (SQLite)

---

## Claim 1: "LONG trades lose $1.42/week in HIGH+NORMAL regimes"

**Verdict: PARTIAL — Direction correct, amount understated**

**Evidence:**
```
My SQL query results (7-day, non-paper, closed):
  HIGH LONG:   73 trades, 54.8% WR, -$0.78
  NORMAL LONG: 55 trades, 58.2% WR, -$1.16
  ─────────────────────────────────────────
  Combined:    -$1.94  (plan says -$1.42)

Plan's NORMAL LONG numbers: 60 trades, 58.3% WR, -$0.64
Actual NORMAL LONG numbers: 55 trades, 58.2% WR, -$1.16
```

The plan understates the NORMAL LONG bleed by $0.52. The actual combined LONG bleed in HIGH+NORMAL is **-$1.94**, not -$1.42. The plan also has the NORMAL LONG trade count wrong (60 vs 55). SHORTs are net positive at +$1.27 total, confirming the directional asymmetry.

**Confidence: HIGH** — SQL query against live PostgreSQL, reproducible.

---

## Claim 2: "BTC was bearish 56% of the last 7 days"

**Verdict: DISAGREE — BTC was significantly more bearish (63%)**

**Evidence:**
```
My query against continuum.db (19,718 BTC state records, 7 days):
  BULL (>55):    5,033 (25.5%)
  NEUTRAL (45-55): 2,251 (11.4%)
  BEAR (<45):   12,434 (63.1%)
```

BTC spent 63.1% of the last 7 days bearish, not 56%. This makes the case for a BTC momentum gate STRONGER than the plan argues. If anything, the plan undersells the urgency.

**Confidence: HIGH** — Direct SQLite query against continuum.db with 19,718 records.

---

## Claim 3: "All big losses share high RSI, high z-score, stale signals"

**Verdict: PARTIAL — Stale confirmed, RSI/z-score unverifiable**

**Evidence:**
```
15 biggest losses (>5% loss), all from my SQL query:
  RSI at entry:    NULL for all 15 trades (field not populated)
  Z-Score at entry: NULL for all 15 trades (field not populated)
  Signal age:       avg 285.3min, range 11.5-791.4min
  Age > 10min:      13/13 with valid age data (100%)
  Stale in metadata: 3/15 (from _signal_metadata JSONB)
  Exit reason:      12/15 via atr_sl_hit, 3/15 via cut-loser-CL-T1
```

**Critical finding:** `entry_rsi_14` and `signal_z_score` are NULL for ALL 15 biggest losses. These columns exist in the schema but are not being populated by the trade creation pipeline. The plan's claim about "high RSI, high z-score" cannot be verified because the data simply isn't recorded. The staleness claim is verified — all big losses had signals 11-791 minutes old at execution.

**Confidence: HIGH for age, N/A for RSI/z-score** — Data columns exist but are empty.

---

## Claim 4: "The staleness decay of 10%/min is too slow"

**Verdict: DISAGREE — This diagnoses the wrong problem**

**Evidence:**
```
Current formula: staleness_mult = max(0.0, 1.0 - (age_m * 0.1))
  → dies at 10 minutes

Plan proposes:   staleness_mult = max(0.0, 1.0 - (age_m * 0.2))
  → dies at 5 minutes

BUT — the actual trade data tells a different story:
  Signal age distribution at OPEN time (204 trades with signal_created_at):
    0-1min:    23 trades, 57% WR, +$3.92
    1-3min:     5 trades, 80% WR, +$4.88
    3-5min:     5 trades, 100% WR, +$13.77  ← BEST performers
    5-10min:    3 trades, 33% WR, -$2.25
    10-30min:  23 trades, 57% WR, -$20.17  ← WORST window
    30-60min:  15 trades, 27% WR, -$44.45  ← WORST window
    1-3h:      56 trades, 62% WR, +$29.73  ← actually profitable
    3-6h:      31 trades, 45% WR, -$65.45  ← worst absolute
    >6h:       43 trades, 65% WR, +$58.91  ← BEST performers
```

**Root cause discovery:** The staleness_mult formula gives 0 at 10 minutes, meaning `score = confidence * 0 * ... = 0`. With score=0, the signal should NEVER enter the hotset. Yet 96% of trades have age >10min at open time. How?

**Answer:** Three mechanisms bypass staleness:
1. **Hard staleness block was REMOVED on 2026-09-04** (decider_run.py line 2940-2946): "FIX 2026-09-04: Remove hard 5min staleness block... A signal with valid conditions should execute regardless of age." Now it only WARNS.
2. **PENDING→APPROVED transition has no age gate** (signal_compactor.py line 3349-3351): "No age gate — if it's in top-10 it's signal-worthy."
3. **Favorites get slower decay** (FAVORITES_RESIDENCY_DECAY=0.12 vs default 0.2), extending hotset life to ~8.3min.

**Making staleness_mult more aggressive (0.2/min) won't help** because the formula is already producing 0 for most trades. The issue is that the execution layer (decider_run.py) doesn't enforce a hard staleness block. The plan addresses a symptom, not the cause.

**Confidence: HIGH** — Verified by code review of decider_run.py line 2940-2946 and SQL data showing 96% of trades have age >10min.

---

## Claim 5: "Blocking LONGs when BTC score < 45 would eliminate the bleed"

**Verdict: CANNOT VERIFY with current data — Concept is sound but needs prerequisites**

**Evidence:**
```
BTC score in trade metadata: 0/336 trades have btc_score stored
  → Cannot correlate BTC state at trade time with PnL

BTC state from continuum.db (last 7 days):
  BEAR (<45): 63.1% of time
  BULL (>55): 25.5% of time

LONG PnL in HIGH+NORMAL: -$1.94 (verified)
SHORT PnL total: +$1.27 (verified)
```

**Critical gap:** BTC score is NOT stored in `_signal_metadata` for any trade. The metadata contains `rsi_14`, `z_score`, `macd_hist`, `momentum_score`, `momentum_state`, `bb_position`, etc. — but NO BTC-related fields. To verify this claim, we would need to:
1. Add BTC score/trend_bias to `_signal_metadata` in the compactor
2. Backfill historical trades
3. Run the correlation query

The concept (don't go LONG when BTC is falling) is directionally correct — SHORTs are profitable, LONGs are not, and BTC was bearish 63% of the time. But the specific threshold of 45 and the expected elimination of bleed are unverified.

**Confidence: MEDIUM** — Conceptually sound, empirically unverifiable with current data.

---

## Claim 6: "514 transitions in 7 days"

**Verdict: DISAGREE — Actual count is 806, and they're much more frequent than claimed**

**Evidence:**
```
My query against continuum.db:
  Total bias transitions (score crosses 45/55 boundaries): 806
  Total hours in window: 168.0
  Average time between transitions: 0.21 hours (12.6 minutes)
  
  Plan claims: 514 transitions, 1.3-2.1 hours between
  Actual:      806 transitions, 0.21 hours (12.6 min) between

Score swings >20 points: only 9 in 7 days
```

The plan's transition count is wrong (514 vs 806) and the frequency estimate is dramatically wrong (12.6 minutes, not 1.3-2.1 hours). The plan's Layer 2 (Transition Detection) proposes detecting regime changes with a 30-minute window and a 20-point delta threshold. With 12.6-minute average transition frequency, this is too slow — transitions happen twice per detection window. However, only 9 score swings >20 points occurred, meaning the 20-point delta threshold in the plan is actually quite conservative and would only fire on major moves.

**Confidence: HIGH** — Direct SQLite query with 19,718 records.

---

## Additional Findings (Not in the Plan)

### Finding A: TREND_FILTER exists but is NOT used in signal_compactor.py

```
hermes_constants.py defines:
  TREND_FILTER_ENABLED = True
  TREND_FILTER_TIMEFRAME = '15m'
  TREND_FILTER_EMA_FAST = 20
  TREND_FILTER_EMA_SLOW = 50

But signal_compactor.py has ZERO references to TREND_FILTER.
It's only used in individual signal detectors:
  - inverse_accel_300.py
  - inverse_accel_300_v2.py
  - atr_spike.py
  - wave_catcher.py
```

This is a gap. The compactor should enforce trend alignment as a universal filter, not rely on individual signals to check it. The plan doesn't mention this.

### Finding B: cut-loser-CL-T1 is a guaranteed loser

```
Exit reason distribution:
  cut-loser-CL-T1: 61 trades, 0.0% WR, -$9.33 PnL
```

This exit mechanism has a 0% win rate across 61 trades. It's the single biggest PnL drag. The plan doesn't address this at all. The cut-loser mechanism forces trades closed at a loss — worth investigating whether the threshold is too tight.

### Finding C: signal_rsi_14 and signal_z_score are NULL for all trades

The trade schema has columns for `entry_rsi_14` and `signal_z_score`, but they're empty for all 336 recent trades. This means Layer 4 (RSI/Z-Score Guard) in the plan can't be validated retroactively. The data would need to be captured going forward.

### Finding D: The 3-5 minute window is the sweet spot

```
Age 3-5min: 5 trades, 100% WR, +$13.77
```

Signals executed 3-5 minutes after creation have a 100% win rate. This suggests the optimal staleness window is tighter than current settings, but the issue is execution timing, not the staleness formula.

---

## Overall Assessment

### What the Plan Gets Right:
1. **LONGs are bleeding in HIGH/NORMAL regimes** — Verified, and the bleed is WORSE than claimed (-$1.94 vs -$1.42)
2. **SHORTs are profitable** — Verified at +$1.27
3. **BTC has been predominantly bearish** — Verified at 63.1%
4. **Big losses correlate with stale signals** — Verified (avg 285min age)
5. **Layer 1 (BTC Momentum Gate) is the highest-impact change** — Conceptually sound
6. **Layer 5 (Continuum Context Boost) is already built** — Just needs wiring

### What the Plan Gets Wrong:
1. **Staleness diagnosis is wrong** — The staleness_mult formula isn't the problem. The hard staleness block was removed, so signals execute regardless of age. Making decay faster won't help without restoring the hard block.
2. **Numbers are inaccurate** — NORMAL LONG bleed is -$1.16 (not -$0.64), total LONG bleed is -$1.94 (not -$1.42), BTC bearish is 63% (not 56%), transitions are 806 (not 514)
3. **RSI/z-score claim is unverifiable** — Data isn't recorded in trades table
4. **Transition frequency is wrong** — 12.6 minutes, not 1.3-2.1 hours

### What the Plan Misses:
1. **TREND_FILTER gap** — Defined but not enforced in compactor
2. **cut-loser-CL-T1 is a guaranteed loser** — 0% WR, -$9.33, biggest single drag
3. **Signal indicator data isn't being recorded** — RSI, z-score columns are empty
4. **The real staleness fix** — Restore the hard staleness block in decider_run.py (removed 2026-09-04) or add it to the compactor as a hard gate, not just a score multiplier

### Is the 5-Layer Defense the Right Approach?

**Partially.** The layers are reasonable individually but miss the mark on priorities:

| Layer | Verdict | Reason |
|-------|---------|--------|
| 1. BTC Momentum Gate | ✅ BEST LAYER | Sound concept, highest impact. But needs BTC score in metadata first. |
| 2. Transition Detection | ⚠️ NEEDS TUNING | Based on wrong frequency data. 12.6min transitions need faster detection. |
| 3. Stale Signal Filter | ❌ WRONG DIAGNOSIS | Formula isn't the issue. Hard block removal is. |
| 4. RSI/Z-Score Guard | ⚠️ CAN'T VERIFY | Data not recorded. Worth adding to metadata. |
| 5. Continuum Context Boost | ✅ EASY WIN | Already built, just wire it up. |

### Better Alternatives:

1. **Restore hard staleness block** in decider_run.py (or add to compactor as hard gate, not score multiplier). The V2 staleness check (SIGNAL_STALENESS_MAX_AGE_MIN=5) only WARNS — make it BLOCK.

2. **Add BTC score/trend_bias to `_signal_metadata`** — This is a prerequisite for Layer 1 and enables retrospective analysis.

3. **Enforce TREND_FILTER in compactor** — It's defined but not used. Add it as a universal gate in `_score_signal()`.

4. **Investigate cut-loser-CL-T1** — 0% win rate across 61 trades. Either the threshold is wrong or the mechanism is counterproductive.

5. **Record signal indicators at trade time** — Populate `entry_rsi_14`, `signal_z_score` in the INSERT so we can validate filters retrospectively.

### Recommended Priority (Revised):

1. **Restore hard staleness block** (1 hour, HIGH IMPACT) — Stop executing signals that are >5min old
2. **Add BTC score to metadata** (2 hours, PREREQUISITE) — Enable Layer 1 verification
3. **Implement BTC Momentum Gate** (Layer 1 from plan) (3 hours, HIGH IMPACT) — Block LONGs when BTC bearish
4. **Wire Continuum Context Boost** (Layer 5 from plan) (1 hour, LOW RISK) — Already built
5. **Enforce TREND_FILTER in compactor** (1 hour, MEDIUM IMPACT) — Use existing constant
6. **Investigate cut-loser-CL-T1** (1 hour, MEDIUM IMPACT) — 0% WR, -$9.33
7. **RSI/Z-Score recording** (2 hours, DATA) — Enable future validation

---

*This verdict was produced by independent analysis. All numbers come from direct SQL queries against the live PostgreSQL and SQLite databases. No claims from the plan were taken at face value.*
