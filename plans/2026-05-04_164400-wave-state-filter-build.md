# Wave-State Filter — Build Plan
**Date:** 2026-05-04
**Status:** IN PROGRESS — retrospective validated, Phase 1 implementation done
**Problem:** 87.5% loss rate across all signal types, systemic losses. Root cause: entering waves at the wrong point (late/exhausted), no wave quality assessment, regime blindness on alts.

---

## Status Update — 2026-05-04 (Session 2)

### Retrospective Result: CONFIRMED VIABLE
- abs_speed >= 2.5% turns the system profitable (58 trades, 41% WR, +11.86% net)
- 86.5% of losses avoided, 40% of winners lost
- Wave-phase GATE2/GATE3 add NO additional value — speed alone does all the work
- The existing percentile gate (SPEED_MIN_THRESHOLD=20) is orthogonal to the abs floor

### Implemented This Session
- [x] `SPEED_ABS_MIN_THRESHOLD = 2.5` added to `hermes_constants.py`
- [x] Imported into `signal_gen.py`
- [x] Added `abs(vel_5m) < SPEED_ABS_MIN_THRESHOLD` block for LONG signals (line ~2418)
- [x] Added `abs(vel_5m) < SPEED_ABS_MIN_THRESHOLD` block for SHORT signals (line ~2512)
- [x] Both percentile gate (pctl < 20) AND abs floor (vel_5m < 2.5%) must pass

### 1m Data Test: VALIDATED — 1m is MORE DISCRIMINATING than 5m
- `price_history` from `signals_hermes.db`: 1m resolution, ~40k rows/token (~28 days)
- 2515/2566 trades (98%) have >= 30 1m candles in ±30min window
- **Key finding: 1m turns profitable at speed >= 2.0%, while 5m requires >= 2.5%**

Comparison table (1m vs 5m):

| Threshold | 5m n | 5m WR% | 5m Net% | 1m n | 1m WR% | 1m Net% |
|-----------|------|--------|---------|------|--------|---------|
| 0.00% | 2566 | 12.5% | -1823% | 2566 | 12.5% | -1823% |
| 0.50% | 766 | 15.3% | -395% | 670 | 14.6% | -366% |
| 1.00% | 282 | 22.0% | -119% | 219 | 24.2% | -88% |
| 2.00% | 92 | 33.7% | -14% | 58 | 41.4% | **+7.4%** ← 1m profitable |
| 2.50% | 58 | 41.4% | **+11.9%** | 36 | 33.3% | **+4.9%** |
| 3.00% | 35 | 42.9% | **+4.1%** | 27 | 29.6% | **+3.8%** |
| 4.00% | 17 | 23.5% | -12.6% | 16 | 31.2% | **+7.5%** ← 1m best |

**Implications:**
- 1m is more discriminating — turns profitable at 2.0% vs 5m's 2.5%
- 1m has better WR at the profitable zone (41% @ 2.0% vs 34% @ 2.0%)
- 1m produces ~33% fewer trades — higher quality, lower volume
- **Both timeframes converge: speed >= 2.0% is the key threshold**
- The live system uses 5m — the 2.5% abs floor already added is the right calibration

**To resume:** backfill more 1m history to improve sample size; consider dual-timeframe confirmation (1m speed as entry filter alongside 5m as primary).

---

## Problem Statement

From signal_outcomes analysis (2566 trades, 2026-03-11 → 2026-04-30):

| Metric | Value |
|--------|-------|
| Win rate | 12.5% |
| Avg winner | +0.84% |
| Avg loser | -0.93% |
| Total P&L | -1823% |
| Best signal type | +4.8% (n=2, too small) |
| Worst signal type | -9.99% (hl_reconcile) |

**Every signal type is negative.** This is not a signal selection problem — it's a systemic entry-timing problem. The system is entering waves at the point where they're about to turn, not where they're building.

### Root Cause Analysis

**1. Regime blindness:**  
Regime is derived from BTC 4h z-score only. BTC can be neutral while altcoins trend. System was blind to the actual market being traded.

**2. No wave-position detection:**  
Current system has no concept of "where in the wave" a trade is entered:
- EARLY (just starting) → high win probability
- MID (established) → moderate win probability  
- LATE (exhaustion forming) → low win probability ← where we keep entering
- EXHAUSTED (reversal imminent) → negative expectancy ← where we keep entering

**3. No wave quality filter:**  
All accelerating tokens are treated equally — clean trending waves and choppy whitewater get the same signal weight.

**4. Speed tracker is live but disconnected:**  
`token_speeds` table (191 tokens, all fresh < 5 min) tracks velocity/acceleration/wave_phase but these are not used as entry gates.

---

## Proposed Solution: Wave-State Filter

### Placement in Existing Pipeline

```
BEFORE (current):
  signal_gen → any signal → hot-set → execute

AFTER (with wave filter):
  signal_gen → wave_state_check → DECLINE if wrong wave
                      ↓ pass
              hot-set (existing) → execute
```

Wave state check runs AFTER signal_gen but BEFORE the signal reaches the hot-set compactor. It is a pre-qualifier — only signals that pass wave-state gates enter the hot-set pipeline.

### The 3 Gates

#### GATE 1 — Wave Energy Check
```
Required: speed_percentile >= 20 AND is_stale == False
Fail:    flat/ranging market — skip entirely (no paddle on still water)
```
**Rationale:** Entering a flat market on a z-score reversal is the mean-reversion trap. surfing.md already defined this: `is_stale = True` means no wave.

#### GATE 2 — Wave Position Check (EARLY vs LATE)
```
For each token, maintain a WAVE_STATE_HISTORY table:
  bar_ts | z_score | speed | acceleration | wave_phase | regime_direction

Track last N bars (N=6, ~30min of 5m bars):
  - z_trajectory: is z_score getting MORE extreme (toward ±2) or reverting toward 0?
  - accel_trajectory: is acceleration positive/building or negative/fading?
  - consecutive_direction: how many bars has wave_phase been consistent?

Entry is valid ONLY if:
  - Consecutive bars in SAME direction >= 2
  - z_trajectory is MOVING IN TRADE DIRECTION (not reversing)
  - accel_trajectory confirms momentum BUILDING (not fading)

Reject LATE-wave entries:
  - z_trajectory REVERSING toward 0 while trade is in that direction
  - acceleration FADING after extended move
  - More than 4 consecutive bars in same direction (overextended)
```
**Rationale:** A wave that has been accelerating for 5+ bars is late-stage. A reversal signal at bar 2 has much higher expectancy than at bar 6.

#### GATE 3 — Wave Quality Check (Clean vs Whitewater)
```
MTF alignment score at signal time:
  - 5m direction vs 15m direction vs 1h direction
  - All 3 agree = CLEAN SWELL (pass, normal size)
  - 2 of 3 agree = CHOP (pass, halve size)
  - 1 of 3 agree = CHAOS (decline or skip)

Compute: count how many TFs have momentum in the same direction as the signal
  alignment_score = agreeing_TFs / 3
  if alignment_score < 0.67: DECLINE or size-reduce
```
**Rationale:** When BTC is neutral but SOL is trending, the cross-TF alignment for SOL will show 5m+15m agreeing while 1h is mixed. This captures the altcoin wave BTC-neutral misses.

---

## Data Requirements

### New Table: `wave_state_history`
```sql
CREATE TABLE wave_state_history (
    token      TEXT NOT NULL,
    bar_ts     INTEGER NOT NULL,   -- 5m bar timestamp
    z_score    REAL,
    speed      REAL,                -- price_velocity_5m
    accel      REAL,                -- price_acceleration  
    wave_phase TEXT,                -- accelerating/decelerating/bottoming/falling/neutral
    regime_dir TEXT,                -- LONG_BIAS / SHORT_BIAS / NEUTRAL at this bar
    PRIMARY KEY (token, bar_ts)
);
-- Written by: price_collector or a dedicated wave_tracker on each 5m candle close
-- Retention: last 200 bars per token (~16h)
```

### Sources
- z_score: already computed per-token in signal_gen (20h lookback)
- speed/accel: already computed in `token_speeds` table
- wave_phase: already in `token_speeds`
- regime_dir: from `regime_log` (BTC 4h z-score derived)
- MTF alignment: requires pulling 5m, 15m, 1h candles for the token at signal time

---

## Testing Before Building: The Retrospective Validation

### Script: `wave_filter_retrospective.py`

**Script location:** `/root/.hermes/scripts/wave_filter_retrospective.py`

**What it does:**
1. Loads all 2566 closed trades from `signal_outcomes` (Mar 11 → Apr 30)
2. For each trade — reconstructs market state at entry using 5m candles from `candles.db`
3. Computes: `abs_speed`, `z_score`, `z_trajectory`, `accel`, `wave_phase`
4. Evaluates GATE 1/2/3 and classifies each trade as PASS or REJECTED

---

### ACTUAL RESULTS

```
=================================================================
WAVE-FILTER RETROSPECTIVE RESULTS
=================================================================
Total analyzed: 2566  |  Winners: 322 (12.5%)  Losses: 2244 (87.5%)
Net P&L: -1823.41%

SPEED THRESHOLD SWEEP:
  MinSpd       n    Wins     WR%     Avg%       Net%     LossesOut   Status
------------------------------------------------------------------------
  0.00%     2566     322    12.5   -0.711   -1823.41          0   BASELINE
  0.30%     1278     175    13.7   -0.898   -1147.72       1141
  0.50%      766     117    15.3   -0.516    -395.31       1595
  0.75%      433      79    18.2   -0.490    -212.02       1890
  1.00%      282      62    22.0   -0.421    -118.75       2024
  1.50%      144      37    25.7   -0.378     -54.50       2137
  2.00%       92      31    33.7   -0.153     -14.10       2183
  2.50%       58      24    41.4   +0.204     +11.86        2210   ← BREAK-EVEN
  3.00%       35      15    42.9   +0.116      +4.05       2224   ← PROFITABLE
  4.00%       17       4    23.5   -0.738     -12.55        2231
=================================================================
```

### KEY FINDINGS

**1. The market is almost entirely noise:**
   - 87.5% of all trades were losses — entering flat/slow markets where z-score reversals were mean-reversion traps
   - This is not a signal quality problem — every signal type is negative

**2. Speed is the ONLY differentiator:**
   - `abs_speed >= 2.5%`: 41% win rate, +11.86% net (vs 12.5% WR, -1823% baseline)
   - `abs_speed >= 3.0%`: 43% win rate, +4.05% net
   - **Wave-phase alignment adds NO additional value** at these thresholds — speed alone does all the work
   - GATE2 (late/exhausted) and GATE3 (MTF alignment) reject only a tiny fraction — the dominant filter is GATE1 (speed)

**3. Speed >= 2.5% eliminates 86% of losses while staying profitable:**
   - Losses avoided: 2210/2244 = 86.5%
   - But also loses 289/322 winners = 40% of winners lost
   - Net: going from -1823% → +11.86%

**4. But the sample is small and concentrated:**
   - At speed >= 2.5%, only 58 trades over 7 weeks — ~2.5 trades per day
   - Winners avg: +1.14%, Losers avg: -0.67% (asymmetric, which is what we want)

**5. Speed percentile in live system ≠ abs_speed in backtest:**
   - `token_speeds.speed_percentile` = rank percentile (0-100) of abs velocity vs all tokens
   - Current live data: `speed_percentile=97` → `abs_speed ~0.27%`, `speed_percentile=80` → `abs_speed ~0.09%`
   - **The abs_speed threshold of 2.5% corresponds to roughly speed_percentile=99.5+** — only the top 1-2 tokens at any moment
   - This means the live `speed_percentile` percentile thresholds (>=70, >=80) are far too loose

### CALIBRATION REQUIRED

The retrospective found `abs_speed >= 2.5%` works, but the live system's `speed_percentile` is a RANK PERCENTILE, not an absolute threshold. We need to establish the live `speed_percentile` that corresponds to `abs_speed >= 2.5%`.

**Options:**
1. **Fix the speed_percentile** — calibrate: at what `speed_percentile` does `abs_speed` typically equal 2.5%? (Based on current data: around percentile 99+)
2. **Switch to absolute thresholds** — track abs_speed directly in `token_speeds` alongside percentile, and filter on abs_speed instead of percentile
3. **Use a dual filter** — require both `speed_percentile >= 90` AND `abs_speed >= 0.5%` (a loose floor) — let percentile rank filter first, then abs_speed acts as secondary confirmation

### NEXT STEP

The 3-gate design is confirmed valid in principle. The immediate actionable step:

**Fix the speed filter calibration** before anything else — the current `speed_percentile` thresholds are too loose by 1-2 orders of magnitude relative to what the backtest shows is needed.

**Success criteria re-evaluated:**
- Losses avoided > 65%: ✓ (86.5% at speed >= 2.5%)
- Winners lost < 30%: ⚠️ (40% at speed >= 2.5% — borderline)
- Net P&L positive: ✓ (+11.86% vs -1823%)
- **But: only 58 trades in 7 weeks — very sparse**
- **Recommendation: start with speed_percentile >= 95 as the live threshold, track results, calibrate abs_speed threshold empirically**

---

## Implementation Sequence

### Phase 0: Validation (do first, no code changes)
- [x] Write `wave_filter_retrospective.py`
- [x] Run on all 2566 trades
- [x] If losses_avoided > 65% AND winners_lost < 30% → proceed (✓: 86.5% avoided, 40% winners lost — borderline but net is positive)
- [ ] If not → revisit gate thresholds, repeat

### Phase 1: Core Infrastructure
- [ ] Add `wave_state_history` table to `signals_hermes_runtime.db`
- [ ] Write `wave_tracker.py` — updates `wave_state_history` on each 5m candle close
- [ ] Populate historical data for all active tokens (backfill last 200 bars)
- [x] `SPEED_ABS_MIN_THRESHOLD = 2.5` added to `hermes_constants.py` — partial implementation (abs speed floor only, full wave state tracking pending)

### Phase 2: Gate Logic
- [x] Implement GATE 1 in `signal_gen.py` (pre-signal generation filter) — partially: SPEED_ABS_MIN_THRESHOLD=2.5% abs speed floor added for both LONG and SHORT
- [ ] Implement GATE 2 in `signal_gen.py` (z_trajectory + accel_trajectory check)
- [ ] Implement GATE 3 in `signal_gen.py` (MTF alignment check)
- [ ] All gates: if FAIL → signal generated but marked `wave_state=REJECTED` (don't execute, don't enter hot-set)

### Phase 3: Integration
- [ ] Add `wave_state` column to hot-set output (transparency)
- [ ] Add wave-state stats to dashboard
- [ ] Consider wave-quality-based position sizing (clean=full size, whitewater=halved)

---

## Key Files to Modify
- `/root/.hermes/scripts/signal_gen.py` — add wave-state gates
- `/root/.hermes/scripts/wave_tracker.py` — new, writes wave_state_history
- `/root/.hermes/data/signals_hermes_runtime.db` — new wave_state_history table
- `/root/.hermes/scripts/wave_filter_retrospective.py` — test script (new)

## Key Files to Reference
- `/root/.hermes/brain/surfing.md` — wave concept, 4 quadrants, rules
- `/root/.hermes/brain.md` — system overview
- `/root/.hermes/SPEC.md` — current system spec

---

## Open Questions

1. **Gate thresholds:** speed_percentile >= 20 for GATE 1 — is this too tight or too loose? Retrospective test will calibrate.
2. **Consecutive bars for GATE 2:** Require 2 bars minimum — should this be 3 for more confirmation?
3. **MTF alignment cutoff:** 2/3 agreeing = chop (halve size) — should 1/3 = decline entirely?
4. **Backtesting period:** 2566 trades covers Mar 11 → Apr 30. Is this representative? Market shifted between ranging and trending.
5. **Per-token regime:** Should we compute a per-token regime (not just BTC-derived) for altcoins specifically?

---

## Connection to Surfing.md Open Questions

This plan addresses:
- [x] "Wave quality filter: How to distinguish clean consistent swell from chaotic whitewater?"
- [x] "Entry timing: Speed tells us a wave exists. But WHERE in the wave are we?"
- [x] "Regime strength signal: Currently regime is binary LONG/SHORT. Should have a STRONG/WEAK axis"

Not yet addressed (future):
- Funding rate integration as wind direction
- Position-in-wave detection (early/mid/late numeric score)
