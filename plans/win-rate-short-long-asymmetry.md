# Win-Rate Short/Long Asymmetry Fix Plan

**Created**: 2026-04-29
**Status**: BACKLOG
**Goal**: Close the win-rate gap between SHORTS (48.9%) and LONGS (35.6%)

---

## Current State

| Direction | Trades | Win Rate | Avg PnL |
|-----------|--------|----------|---------|
| LONG      | 118    | 35.6%    | +0.162% |
| SHORT     | 45     | 48.9%   | +0.506% |

**Key asymmetry**: SHORTS have +13.3% higher win rate and 3x better avg PnL.

---

## Root Causes (5 Problems)

### PROBLEM 1: ma-cross-5m+ is a disaster — BLACKLIST IT
- **Data**: 15 trades, 20% WR, avg loss on all but 3 tiny wins
- **Root cause**: MA cross on 5m is lagging noise — fires after the move already happened
- **Fix**: Add `ma-cross-5m+` to `SIGNAL_SOURCE_BLACKLIST` in hermes_constants.py

### PROBLEM 2: pct-hermes+ fires too eagerly for LONG
- **Data**: `pct-hermes+` alone → 33.3% WR on 21 longs, -0.096% avg (excluding STRK outliers)
- **Root cause**: Threshold `percentile_long <= 45` is too loose. Only deeply suppressed prices (pct_long <= 35) have real edge.
- **Code location**: signal_gen.py line ~971
- **Fix**: Change `has_pct_signal` threshold for LONG from `<= 45` to `<= 38`

### PROBLEM 3: gap-300- LONG fires too frequently without proper confluence
- **Data**: 75 gap-300- longs, 38.7% WR. 62.7% of losses are tiny (-0.5% to 0%) — SL hit immediately
- **Root cause**: MIN_GAP_PCT = 0.05% is too low — even small noise gaps trigger tracking
- **Code location**: gap300_signals.py line ~33
- **Fix**: Raise MIN_GAP_PCT from 0.05 to 0.08. Also consider COLLAPSE_PCT from 0.70 to 0.75.

### PROBLEM 4: oc-rsi- SHORT fires too early in mean-reversion cycles
- **Data**: `oc-rsi-` SHORT → 28.6% WR (7 trades), multiple tiny losses on FIL, ADA
- **Root cause**: RSI mean-reversion on lower timeframe catches knives without momentum confirmation
- **Fix**: Require oc-rsi- to confirm with velocity OR z_score alignment (same pattern as successful hzscore+,pct-hermes-,vel-hermes- combo)

### PROBLEM 5: vel-hermes+ barely fires — asymmetric signal availability
- **Data**: `vel-hermes+` LONG → 2 trades only vs 24 for vel-hermes- SHORT
- **Root cause**: vel-hermes+ requires negative velocity (z-score falling). In trending markets velocity is often positive, so "good LONG entry" rarely fires.
- **Fix**: Add grace condition: allow neutral/positive velocity to still signal LONG when percentile_long <= 30 (deeply suppressed). Similar to the pct_long < 40 criterion already used in exhaustion phase.

---

## Implementation Steps

### Step 1: Blacklist ma-cross-5m+
**File**: `/root/.hermes/scripts/hermes_constants.py`
**Action**: Add `'ma-cross-5m+'` to `SIGNAL_SOURCE_BLACKLIST`
**Risk**: LOW — removes a clearly losing signal

### Step 2: Tighten pct-hermes+ LONG threshold
**File**: `/root/.hermes/scripts/signal_gen.py` (around line 971)
**Action**: Change `percentile_long <= 45` to `percentile_long <= 38`
**Risk**: MEDIUM — changes signal generation behavior for ~21 trades in dataset

### Step 3: Raise MIN_GAP_PCT for gap-300
**File**: `/root/.hermes/scripts/gap300_signals.py` (line 33)
**Action**: Change `MIN_GAP_PCT = 0.05` to `MIN_GAP_PCT = 0.08`
**Risk**: MEDIUM — reduces signal volume, improves quality

### Step 4: Require confluence for oc-rsi-
**File**: `/root/.hermes/scripts/signal_gen.py`
**Action**: Add velocity or z_score requirement to oc-rsi- signal generation
**Risk**: MEDIUM — requires finding the oc-rsi- generation code

### Step 5: vel-hermes+ grace condition
**File**: `/root/.hermes/scripts/signal_gen.py` (velocity scoring section ~line 1026)
**Action**: Add condition: if percentile_long <= 30, set vel_score = +5 even with neutral velocity
**Risk**: LOW — adds a small grace condition

---

## Validation Plan

After each change:
1. Check signal generation volume (should not drop more than 30%)
2. Run backtest if possible
3. Monitor live WR for 50+ trades before drawing conclusions
4. Compare SHORT vs LONG WR gap — target is gap < 5%

---

## Notes

- profit-monster exits are excellent for BOTH directions (~100% WR, 2.5%+ avg PnL)
- Most losses are tiny (-0.5% to 0%) — SL is working correctly, entries are the issue
- Regime data was all None — per-token regime filtering is the intended path (already in place)
- Confidence >= 99 longs have 55% WR — high-conviction signals work, it's the low-conf ones dragging WR down
