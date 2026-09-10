# Regime Transition Smoothing

**Date:** 2026-09-09
**Status:** CEO APPROVED (CONDITIONAL) → AWAITING IMPLEMENTATION
**Trigger:** 50-trade transition zone (trades 26-75) bled $1.45 during LONG→SHORT regime flip. LONGs kept firing while BTC was already falling.
**Core Insight:** We already have 80% of this functionality built. The problem isn't missing systems — it's that existing systems don't talk to each other. This plan is about wiring, not building.
**CEO Verdict:** GO (conditional) — 30 lines + 4 constants. Skip Layer 1 (redundant with existing zscore_accel). Implement Layers 2, 3 (conservative), 4.

---

## Problem Statement

The last 100 trades show a clear regime transition:

```
Trades 1-25:   ██████████ LONG zone     — 21L/4S, 52% WR, PnL: $-0.71
Trades 26-75:  ████▓▓▓▓▓▓ MIXED         — 30L/20S, transition, PnL: $-1.45
Trades 76-100: ▓▓▓▓▓▓▓▓▓▓ SHORT zone    — 5L/20S, 65% WR, PnL: $+1.06
```

**The transition zone is where money bleeds.** 50 trades of churning before the system figured out "we're in a SHORT regime now."

### What hurt in the transition zone

| Signal | Direction | WR | PnL | Problem |
|--------|-----------|-----|------|---------|
| ema300_dip_short | SHORT | 3W/7L | -$0.83 | Shorts fired too early, before momentum confirmed |
| sma20_dip | LONG | 0W/5L | -$0.73 | LONGs kept firing in a falling market |
| bb_bounce_v2_long | LONG | 1W/2L | -$0.29 | LONG bounce signals in bearish regime |
| AIXBT | LONG | 0W/3L | -$0.78 | Same coin, same direction, 3 losses — no circuit breaker |

### BTC Price Action Context (Sep 9 15:00–22:09 UTC)

```
$79,395 ┤ 15:00 High (pre-crash)
        │ ╲
$78,800 ┤   ╲──── consolidation
        │     ╲
$78,400 ┤       ╲── 18:00-19:00 second leg down
        │         ╲
$78,060 ┤   15:20   ╲── first low
        │            ╲
$77,770 ┤             ╲── 22:09 LOW (capitulation)
        │              ╱
$78,370 ┤─────────────╱── stabilization (now)

Hourly MACD(8,50,12):
  Sep 9 19:00  MACD=-135.9  (price accelerating down)
  Sep 9 22:00  MACD= -58.7  (price at LOW, but MACD less negative = DIVERGENCE)
  Sep 10 02:00 MACD=+133.1  (MACD positive while price still near lows)
```

**Hourly MACD bullish divergence confirmed** — price made lower lows from 19:00→22:09, but MACD was already less negative at 22:00 (-58.7) than at 19:00 (-135.9). On the 1m timeframe, the divergence is noisier but the pattern holds.

---

## Existing Systems Audit — What We Already Have

**The user's key insight: we already have 80% of this. The problem is wiring, not building.**

| System | Location | What It Does | Status | CEO Finding |
|--------|----------|-------------|--------|-------------|
| **BTC Momentum Filter** | `signal_compactor.py:789` | Blocks LONG when BTC 30m < -0.12% | ✅ ACTIVE | Reactive — fires AFTER momentum is negative |
| **Directional Outcome** | `signal_compactor.py:569-642` | Penalizes direction after 3+ losses in 15min | ✅ ACTIVE | Penalty (0.7x) too mild — still lets signals through |
| **Directional Lock** | `signal_compactor.py:645` | Hard blocks direction after 4+/5 catastrophic losses | ✅ ACTIVE | Threshold too high — needs lower velocity trigger |
| **ZScore Accel Penalty** | `signal_compactor.py:823-858` | Penalizes when z-score + acceleration disagree | ✅ ACTIVE | **ALREADY DOES LAYER 1** — reads `price_acceleration` |
| **Chop Detector** | `chop_detector.py` | Blocks momentum signals in chop | ✅ ACTIVE | Detects chop, not regime transitions |
| **Directional Cap** | `hermes_constants.py:808-809` | Max 80% open positions in one direction | ✅ ACTIVE | Limits concentration, not SIZE |
| **Loss Cooldown** | `hermes_constants.py:664-665` | 20min cooldown after consecutive losses | ✅ ACTIVE | Per-token only — doesn't block DIRECTION |
| **BTC Momentum Cache** | `signals_hermes_runtime.db:momentum_cache` | Stores BTC velocity, z_direction, phase, momentum_state | ✅ ACTIVE | **momentum_state UNUSED by signal_compactor** |
| **Token Speeds** | `signals_hermes_runtime.db:token_speeds` | Stores price_velocity, acceleration, price_change_30m | ✅ ACTIVE | price_change_30m unused for cross-token comparison |
| **Regime Scanner** | `15m_regime_scanner.py` | Determines LONG_BIAS/SHORT_BIAS/NEUTRAL per token | ✅ ACTIVE | Output not consulted by signal_compactor |

**Key CEO finding:** `get_zscore_accel_penalty()` at `signal_compactor.py:823` already reads `price_acceleration` and penalizes when z-score and acceleration diverge. Layer 1 (gradient detection) is REDUNDANT — adding a second acceleration check creates double-penalization.

---

## Solution: 3 Layers (Wire Existing Systems + Tighten Constants)

### ~~Layer 1: Gradient Detection~~ → SKIPPED (CEO: redundant with zscore_accel)

**Already covered by:** `get_zscore_accel_penalty()` at `signal_compactor.py:823-858` which reads `token_speeds.price_acceleration` and applies a penalty when z-score and acceleration disagree. Adding a second gradient check would double-penalize the same condition.

**If needed later:** Adjust `ZSCORE_ACCEL_*` constants instead of adding a new system.

---

### Layer 2: Directional Bias — CONNECT REGIME SCANNER TO SIGNAL COMPACTOR

**What we have:** `momentum_cache.momentum_state` already stores BTC's momentum classification (strong_long/strong_short/neutral) with confidence. The regime scanner computes this. Signal_compactor never reads it.

**What's missing:** `_score_signal()` uses a crude binary check (`BTC_MOMENTUM_FALLING_THRESHOLD = -0.12%`). The regime scanner's richer analysis (slope, R2, confidence, momentum_state) is wasted.

**The fix:**

In `_score_signal()`, read BTC's `momentum_state` from `momentum_cache`:
- If `momentum_state = 'strong_long'` → boost LONG signals, penalize SHORT signals
- If `momentum_state = 'strong_short'` → boost SHORT signals, penalize LONG signals
- If `momentum_state = 'neutral'` → no bias (current behavior)

**Constants to add:**
```python
DIRECTIONAL_BIAS_ENABLED = True
DIRECTIONAL_BIAS_COUNTER_TREND_PENALTY = 0.6  # multiplier — reduce counter-trend scores
DIRECTIONAL_BIAS_PRO_TREND_BOOST = 1.15       # multiplier — boost pro-trend scores
```

**What changes:** ~20 lines in `_score_signal()`. Reads existing `momentum_cache` row. No new tables.

**CEO verdict:** REAL GAP — biggest value, lowest risk.

---

### Layer 3: Circuit Breaker — TIGHTEN EXISTING CONSTANTS (NOT THRESHOLDS)

**What we have:** `_is_direction_locked()` + `DIRECTIONAL_OUTCOME` system with velocity tiers, integral window, and lock mechanism.

**What the plan proposed (CEO REJECTED):** Lowering WINDOW 5→3 and LOSS_THRESHOLD 3→2. CEO says this fires on noise — 2 losses in 1 hour is normal variance at 2-3 trades/hr.

**What the CEO recommends instead:**

| Constant | Current | New | Why |
|----------|---------|-----|-----|
| `DIRECTIONAL_OUTCOME_PENALTY` | 0.7 | **0.5** | Stronger penalty when directional outcome fires — currently 0.7x still lets signals through |
| `DIRECTIONAL_OUTCOME_LOCK_VELOCITY` | 0.6 | **0.5** | Lock triggers at 2.5/5 losses instead of 3/5 — catches AIXBT pattern earlier |

**These are single-number changes.** No structural risk. The existing velocity tiers and integral window already catch the patterns — we just need the penalty to bite harder.

**CEO verdict:** DO NOT touch WINDOW/THRESHOLD. Change 2 constants only.

---

### Layer 4: Alt-BTC Correlation — USE EXISTING price_change_30m

**What we have:** `token_speeds.price_change_30m` exists for EVERY token, including BTC. This is exactly what we need.

**What's missing:** No code compares alt's `price_change_30m` to BTC's `price_change_30m`.

**The fix:**

In `_score_signal()`, after reading the token's `price_change_30m`, compare to BTC's:
- If alt `price_change_30m` < -0.30% AND BTC `price_change_30m` > -0.10% → DIVERGENT_BEARISH
- Apply penalty to LONG signals on that token

**Constants to add:**
```python
ALT_BTC_DIVERGENCE_ENABLED = True
ALT_BTC_DIVERGENCE_THRESHOLD = -0.30      # % — alt must be below this
ALT_BTC_DIVERGENCE_BTC_MIN = -0.10        # % — BTC must be above this
ALT_BTC_DIVERGENCE_LONG_PENALTY = 0.5     # multiplier
```

**What changes:** ~10 lines in `_score_signal()`. Reads existing data. No new tables.

**CEO verdict:** SIMPLE, LOW RISK, HIGH VALUE.

---

## Final Implementation: 30 Lines + 4 Constants

```
Layer 3:  Change DIRECTIONAL_OUTCOME_PENALTY 0.7→0.5     (1 line)
          Change DIRECTIONAL_OUTCOME_LOCK_VELOCITY 0.6→0.5 (1 line)
Layer 2:  Add directional bias check in _score_signal()    (~20 lines)
Layer 4:  Add alt-BTC divergence check in _score_signal()  (~10 lines)

Total: ~30 lines of new code + 4 constant changes in 2 files
```

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `scripts/hermes_constants.py` | Change 2 existing constants + add ~6 new ones | ~8 lines |
| `scripts/signal_compactor.py` | Add directional bias + alt-BTC divergence checks | ~30 lines |

**That's it. Two files. No new modules. No new DB tables.**

---

## CEO-Approved Implementation Priority

1. **Layer 3 constants** — 2 number changes, immediate effect, zero structural risk
2. **Layer 4 alt-BTC divergence** — 10 lines, independent, easy to test in isolation
3. **Layer 2 directional bias** — 20 lines, highest value but needs careful tuning
4. **Layer 1 gradient** — SKIP (already covered by zscore_accel at line 823)

---

## Testing Strategy (CEO-Approved)

### Pre-Live: Backtest 30 Days

Before ANY live changes, run the proposed changes against last 30d of trades in the DB:
- Compute: how many winning trades would have been blocked by directional bias?
- If >10% of winning trades blocked → thresholds too tight, adjust
- If <5% → safe to proceed

### Phase 1 (Day 1-2): Layer 3 Constants Only
- Change `DIRECTIONAL_OUTCOME_PENALTY` 0.7→0.5 and `LOCK_VELOCITY` 0.6→0.5
- Monitor directional outcome fire rate — should increase from ~5/day to ~8/day
- **Abort trigger:** If >12/day, LOCK_VELOCITY is too aggressive → revert to 0.6

### Phase 2 (Day 3-5): Add Layer 4 (Alt-BTC Divergence)
- Log what would have been blocked vs what traded
- No live effect for 48h (LOG-ONLY mode)
- After 48h: enable live if log shows <5% false positives

### Phase 3 (Day 6-10): Add Layer 2 (Directional Bias)
- This is the global change — monitor for signal starvation
- **Abort trigger:** If total signals drop >20%, reduce `DIRECTIONAL_BIAS_COUNTER_TREND_PENALTY` from 0.6 to 0.7

### Phase 4 (Day 11-14): Evaluate Combined
- Compare 14d transition zone PnL vs baseline
- Decision: keep, adjust, or revert

---

## Risk Analysis

| Layer | Risk | Mitigation | CEO Assessment |
|-------|------|-----------|----------------|
| Layer 3 (constants) | Minimal — just 2 numbers | Fire rate monitoring, abort trigger at >12/day | LOW — single-number changes |
| Layer 4 (alt-BTC) | Per-token, isolated | LOG-ONLY for 48h, <5% false positive threshold | LOW — simple comparison |
| Layer 2 (directional bias) | Global multiplier, could starve signals | Monitor signal volume, reduce penalty if >20% drop | MEDIUM — needs tuning |
| ~~Layer 1 (gradient)~~ | ~~Double-penalization with zscore_accel~~ | ~~SKIP~~ | ~~REMOVED~~ |

**Biggest risk the plan missed:** Signal starvation. System generates ~2-3 signals/hr. If directional bias + alt-BTC divergence block 30% of signals, we drop to ~1.5-2/hr — back to starvation territory. CEO recommends monitoring signal volume as primary health metric.

---

## Expected Impact

Based on the transition zone data and CEO assessment:

| Change | What It Fixes | Estimated PnL Impact |
|--------|--------------|---------------------|
| Layer 3: Stronger penalty (0.7→0.5) | AIXBT-type patterns caught harder | +$0.30 |
| Layer 2: Directional bias (momentum_state) | Counter-trend signals reduced during regime shift | +$0.50 |
| Layer 4: Alt-BTC divergence | LONGs blocked on bleeding alts | +$0.25 |
| **Total** | | **+$1.05 (from -$1.45 to ~-$0.40)** |

**Conservative estimate:** Even 50% effectiveness → save ~$0.50 in the transition zone.

---

## What the CEO Found That We Missed

1. **`get_zscore_accel_penalty()` already does gradient detection** — Layer 1 was redundant. Adding it would double-penalize the same condition.

2. **Directional outcome thresholds don't need changing** — the existing velocity tiers and integral window already catch AIXBT patterns. The problem was the penalty (0.7x) being too mild, not the trigger being too high.

3. **Signal starvation is the real risk** — at 2-3 signals/hr, blocking 30% drops us below minimum viable signal flow. Need to monitor as primary health metric.

4. **The plan over-optimized for one transition zone** — 50 trades, -$1.45. The fixes need to work in normal conditions too, not just during regime shifts.
