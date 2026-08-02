# ZSCORE-PUMP & RS Signal Quality Improvement Plan
**Date:** 2026-05-24  
**Status:** DRAFT — awaiting T approval  
**Source:** brain.trades (PostgreSQL) + signals_hermes_runtime.db (SQLite) — last 24h

---

## 1. Executive Summary

Analyzed 83 closed trades (46 LONG, 38 SHORT) from the last 24h. Win rate is 43%
across both directions — not great. The goal was to find what separates big winners
from losers and tune the zscore-pump + resistance/support signal parameters accordingly.

**Overall 24h stats:**
| Direction | Trades | Win Rate | Avg %  | Net PnL | Avg Duration |
|-----------|--------|----------|--------|---------|--------------|
| LONG      | 46     | 45.7%    | +0.18% | +$0.87  | 64 min        |
| SHORT     | 38     | 42.1%    | -0.03% | -$0.10  | 67 min        |

---

## 2. Verified Findings (Independent Audit)

> ⚠️ A subagent independently re-ran all queries. Findings that differ from initial
> report are marked with **[CORRECTED]**.

### 2a. Big Winners (27 trades, avg +1.37%, avg 81 min hold) [CORRECTED: was 26]

- **All exited via profit-monster** (TP hit) — except 1 atr_sl_hit, 1 HARD_SL_CLOSE_FAILED
- **Avg confidence: 93.7** (high but not 98 exclusively)
- **All signals are COMBO (RS + zscore)** — [CORRECTED] initial report incorrectly
  stated many were single-source zscore
- **No pure single-source zscore-pump signals exist in the trade dataset** — every
  signal includes RS component (e.g., `rs-s624,zscore-pump+`, `rs-r76,zscore-pump-`)
- Top winner: ME LONG `rs-s624,zscore-pump+` at +4.27%, 49 min — combo signal
- Second best: GRIFFAIN SHORT `rs-r76,zscore-pump-` at +1.87%, 0.5 min (fast TP)

### 2b. Big Losers (32 trades, avg -0.98%, avg 54 min hold)

- **31/32 exited via atr_sl_hit** — quick reversals caught by SL
- **1/32 exited via guardian_sl** (rs-r184 SHORT -0.91%)
- **Avg confidence: 94** — same as winners (high confidence doesn't predict outcome)
- **All are also COMBO signals** — [CORRECTED] not single-source
- Fastest loser: rs-r188 SHORT closed in **0.05 min** (3 seconds!) — combo signal
- Many losers held for 40-180 min before reversing through SL

### 2c. Extreme Z-Score Signals (|z| > 3.0)

888 signals with |z| > 3.0 fired in the 24h window. Cross-referencing with trade outcomes:

| Token | Dir | z_score | Trade Result | close_reason |
|-------|-----|---------|--------------|--------------|
| IP    | SHORT | -6.712 | **+1.25% WIN** | profit-monster |
| BLUR  | SHORT | -6.161 | **+1.69% WIN** | profit-monster |
| VINE  | SHORT | -5.619 | Mixed        | — |
| VINE  | LONG  | 6.915  | Mixed        | — |

**[CORRECTED]** Initial report said IP/BLUR extreme z shorts were losers. They were
winners. The extreme z signals are not inherently losers — some win, some lose.

### 2d. Close Reason Breakdown

| close_reason       | count | avg_pnl_pct | total_pnl |
|--------------------|-------|-------------|-----------|
| profit-monster     | 31    | +1.12%      | +$3.71    |
| HARD_SL_CLOSE_FAILED | 1  | +1.87%      | +$0.21    |
| guardian_sl        | 1     | -0.91%      | -$0.10    |
| atr_sl_hit         | 51    | -0.60%      | -$3.21    |

**Key insight:** TP hits are 4x more profitable per trade than SL hits. The challenge
is not signal direction — it's getting stop-loss placement right so winners can run
without getting stopped out prematurely.

---

## 3. Root Cause Analysis

### What the data actually shows:

1. **All signals are combo (RS + zscore)** — there is no "pure zscore without RS" in
   the trade set. So the original "single-source zscore = losing" hypothesis is
   **not supported** by the data.

2. **High confidence (94 avg) doesn't predict winners vs losers** — both groups
   have similar confidence scores. Confidence alone is not a filter.

3. **Extreme z (|z| > 4) does NOT reliably predict loss** — IP SHORT at z=-6.71 won.
   BLUR SHORT at z=-6.16 won. The z-score magnitude alone is not a reversal indicator.

4. **Duration asymmetry is the key differentiator:**
   - Winners: avg 81 min (more time to develop)
   - Losers: avg 54 min (faster failure)
   - This suggests SL placement is too tight relative to signal validity window

5. **Profit-monster exits beat ATR SL exits** — when the system hits TP (1.12% avg)
   vs getting stopped out (-0.60% avg), the difference is huge. Better SL placement
   (wider for high-conviction entries) would let winners run longer.

---

## 4. Proposed Parameter Changes

All changes go in `/root/.hermes/scripts/hermes_constants.py`.

### 4a. SL Distance Multiplier for High-Confidence Combo Entries

**Problem:** SL is too tight for combo signals. Winners get stopped out prematurely.

**Current state:** `sl_distance = 0.015` (1.5%) hard-coded in decider_run for RS
signals. But ATR-based SL in position_manager uses `k_sl * atr_14`. The issue is
the base ATR multiplier may be too tight for high-conviction entries.

**Fix in hermes_constants.py:**
```python
# For RS+zscore COMBO signals (high conviction), widen the ATR-based SL slightly
# to give winning trades room to develop
RS_COMBO_SL_MULTIPLIER = 1.2   # NEW: multiply ATR SL by 1.2x for combo signals
                               #   → wider SL = longer winning trade survival
```

> **Note:** This may require changes in `position_manager.py` and/or `decider_run.py`
> to read and apply this multiplier. T must approve before implementing.

### 4b. Z-Score Cap for Extreme Entries (|z| > 4.5)

**Problem:** Extreme z-scores (5-7) fire very close to potential reversal points.
While some extreme z trades win (IP SHORT at -6.71), the risk of quick reversal is
higher at those levels.

**Proposed fix in hermes_constants.py:**
```python
ZSCORE_PUMP_MAX_Z = 4.5        # was None — cap |z| at 4.5 for new entries
                               # Reject signal if |z| > 4.5 (blow-off territory)
                               # Directional bias preserved, but don't enter at peak
ZSCORE_PUMP_MAX_Z_SHORT = 4.0  # NEW: stricter cap for SHORT (more violent reversals)
```

> **Note:** This needs to be implemented in `signals/zscore_pump.py` (detection function)
> and possibly `signal_compactor.py` (gate logic). T must approve before implementing.

### 4c. Minimum Cooldown After Extreme-Z SL Hit

**Problem:** Some tokens get multiple signals in quick succession after a loss (e.g.,
rs-r188 SHORT hit SL in 3 seconds, then another signal fired).

**Proposed fix in hermes_constants.py:**
```python
ZSCORE_PUMP_EXTREME_COOLDOWN_BARS = 15  # NEW: if entry hit SL at |z| > 4.0,
                                        #   wait 15 bars (~30 min) before re-fire
                                        #   instead of standard COOLDOWN_BARS (5)
```

> **Note:** Implementation in `zscore_pump.py` cooldown tracking. T must approve.

### 4d. Divergence Filter Tightening (Optional — Lower Threshold)

**Current:** `ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 3.0` — only kicks in when z > 3.0

**Proposed (optional):**
```python
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 2.5  # was 3.0 — catch reversal earlier
ZSCORE_PUMP_DIVERGENCE_VEL_THD = -0.4    # was -0.5 — sharper rejection of tired moves
```

> **Note:** This may reduce signal volume. T must approve.

---

## 5. Implementation Plan

### Step 1: Add constants to hermes_constants.py (No logic changes yet)
- Add `ZSCORE_PUMP_MAX_Z`, `ZSCORE_PUMP_MAX_Z_SHORT`, `RS_COMBO_SL_MULTIPLIER`,
  `ZSCORE_PUMP_EXTREME_COOLDOWN_BARS`
- Do NOT implement the logic yet — just define the constants

### Step 2: Implement z-score cap in zscore_pump.py
- In `detect_zscore_pump()` function: reject signal if `|z| > ZSCORE_PUMP_MAX_Z`
  (or `ZSCORE_PUMP_MAX_Z_SHORT` for SHORT direction)
- Log when signals are rejected due to extreme z

### Step 3: Implement cooldown extension in zscore_pump.py
- Track when an entry hit SL at `|z| > 4.0`
- Apply `ZSCORE_PUMP_EXTREME_COOLDOWN_BARS` instead of standard `COOLDOWN_BARS`

### Step 4: Implement SL multiplier (coordinate with T)
- This requires changes in `position_manager.py` or `decider_run.py`
- Read `RS_COMBO_SL_MULTIPLIER` and widen ATR-based SL for combo signals

### Step 5: Test and verify
- Run smoke test after changes
- Monitor next 24h for signal volume change and win rate improvement

---

## 6. Decisions Required from T

Before implementing, T needs to decide:

1. **Approve z-score cap?** Yes/No → If yes, what values (4.5/4.0)?
2. **Approve cooldown extension?** Yes/No
3. **Approve SL widening for combo signals?** Yes/No → If yes, which file handles it?
4. **Approve divergence tightening (2.5 vs current 3.0)?** Yes/No/Maybe

---

## 7. Files to Modify

| File | Changes |
|------|---------|
| `hermes_constants.py` | Add new constants only |
| `signals/zscore_pump.py` | Implement z-cap + extreme cooldown |
| `position_manager.py` | (Possibly) SL multiplier for combos — T approval required |
| `decider_run.py` | (Possibly) SL multiplier for combos — T approval required |

---

## 8. What NOT to Change (Based on Data)

- `ZSCORE_PUMP_THRESHOLD = 2.0` — performing adequately, don't raise
- `ZSCORE_PUMP_LOOKBACK = 70` — leave as-is
- `RS_DECIDER_MIN_TOUCHES = 200` — reasonable floor
- Signal source weights in signal_compactor.py — working as intended

---

**Next step:** Report back to T with this plan. Await approval before implementing.