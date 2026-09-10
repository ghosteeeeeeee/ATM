# Regime Transition Smoothing

**Date:** 2026-09-09
**Status:** PLAN → AWAITING IMPLEMENTATION
**Trigger:** 50-trade transition zone (trades 26-75) bled $1.45 during LONG→SHORT regime flip. LONGs kept firing while BTC was already falling.

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

### Existing systems that helped (but aren't enough)

| System | What it does | Gap |
|--------|-------------|-----|
| **BTC Momentum Filter** | Blocks LONG when BTC 30m < -0.12% | Reactive — fires AFTER momentum is already negative |
| **Directional Outcome** | Penalizes direction after 3+ losses in 15min | 3-loss threshold too slow — AIXBT lost 3 times before trigger |
| **Chop Detector** | Blocks momentum signals in chop | Detects chop, not the transition FROM one regime TO another |
| **Directional Cap** | Max 80% open positions in one direction | Limits concentration but doesn't reduce position SIZE |
| **Loss Cooldown** | 20min cooldown after consecutive losses | Per-token only — doesn't block the DIRECTION |

---

## Solution: 4-Layer Regime Transition System

### Layer 1: Momentum Gradient Detection (2nd Derivative)

**What:** Detect when BTC is *decelerating* — not just when it's negative. This gives 30-60 minute head start before the actual regime flip.

**Why:** Currently BTC_MOMENTUM_FALLING_THRESHOLD = -0.12% blocks LONGs AFTER momentum is already negative. By then, several losing LONGs have stacked up. The 2nd derivative catches the turn earlier.

**How:**
- Track BTC velocity (1st derivative) over 30m window
- Track BTC acceleration (2nd derivative) — rate of change of velocity
- When velocity is still positive but acceleration is negative → "COOLING" state
- COOLING state → reduce LONG bias, start scanning SHORT setups

**New constants in `hermes_constants.py`:**
```python
BTC_GRADIENT_ENABLED = True
BTC_GRADIENT_VELOCITY_WINDOW = 30        # minutes — same as momentum window
BTC_GRADIENT_ACCELERATION_WINDOW = 15    # minutes — compare two velocity snapshots
BTC_GRADIENT_COOLING_THRESHOLD = -0.05   # % — acceleration below this = decelerating
BTC_GRADIENT_HOT_THRESHOLD = 0.05        # % — acceleration above this = accelerating
BTC_GRADIENT_COOLDOWN_BIAS = 0.5         # multiplier — reduce LONG signal scores by 50% when COOLING
```

**Implementation in `signal_compactor.py`:**
- New function `_get_btc_gradient()` → returns ('ACCELERATING', 'COOLING', 'NEUTRAL')
- Called in `_score_signal()` — when COOLING, apply `BTC_GRADIENT_COOLDOWN_BIAS` multiplier to LONG signals
- When ACCELERATING, no change (current behavior)

**Data source:** Reuse existing `_get_btc_momentum()` which reads from `token_speeds.price_change_30m`. Store two snapshots (current and 15min ago) in `momentum_cache` or a new `btc_gradient_cache` table.

---

### Layer 2: Directional Bias Scaling

**What:** Actively bias signal generation based on BTC momentum direction. Instead of 50/50 LONG/SHORT signal allowance, scale based on BTC trend.

**Why:** The current system fires both LONG and SHORT signals regardless of BTC direction, then filters them later. By the time filtering happens, bad signals have already been generated and some have executed. Pre-biasing reduces the volume of counter-trend signals at the source.

**How:**
- BTC accelerating up → LONG bias (allow all LONG signals, reduce SHORT signal scores)
- BTC accelerating down → SHORT bias (allow all SHORT signals, reduce LONG signal scores)
- BTC flat → neutral (current behavior)

**New constants in `hermes_constants.py`:**
```python
DIRECTIONAL_BIAS_ENABLED = True
DIRECTIONAL_BIAS_BTC_STRONG_THRESHOLD = 0.20   # % — BTC 30m momentum above this = strong trend
DIRECTIONAL_BIAS_BTC_WEAK_THRESHOLD = 0.08     # % — BTC 30m momentum below this = weak/flat
DIRECTIONAL_BIAS_COUNTER_TREND_PENALTY = 0.5   # multiplier — reduce counter-trend signal scores
DIRECTIONAL_BIAS_PRO_TREND_BOOST = 1.15        # multiplier — boost pro-trend signal scores
```

**Implementation in `signal_compactor.py`:**
- New function `_get_directional_bias(btc_momentum)` → returns bias multiplier for LONG and SHORT
- Called in `_score_signal()` — applies bias multiplier to signal confidence
- Integrates with Layer 1 (gradient) — COOLING state reinforces the bias

**Bias matrix:**

| BTC Momentum | LONG Bias | SHORT Bias | Effect |
|-------------|-----------|------------|--------|
| > +0.20% (strong up) | 1.15x boost | 0.5x penalty | Heavily favor LONGs |
| +0.08% to +0.20% | 1.0x (neutral) | 0.8x mild penalty | Slight LONG preference |
| -0.08% to +0.08% | 1.0x | 1.0x | No bias (current) |
| -0.20% to -0.08% | 0.8x mild penalty | 1.0x | Slight SHORT preference |
| < -0.20% (strong down) | 0.5x penalty | 1.15x boost | Heavily favor SHORTs |

---

### Layer 3: Consecutive Loss Circuit Breaker (Enhanced)

**What:** Make the existing directional outcome system more aggressive. After consecutive losses in a direction, hard-block that direction (not just penalty).

**Why:** AIXBT lost 3 times (-4.8%, -3.9%, -3.1%) before any circuit breaker fired. The existing system requires 3 losses in 15 minutes — but AIXBT losses were spread over longer periods. The current penalty multiplier (0.7x) still lets signals through.

**How:**
- Track consecutive losses per DIRECTION (not just per token)
- After 2 consecutive losses in same direction → HARD BLOCK all signals in that direction for N minutes
- After 3+ consecutive losses → extended block + reduce position size when unblocked
- Integrate with existing LOSS_COOLDOWN system (which is per-token)

**New constants in `hermes_constants.py`:**
```python
DIRECTION_CIRCUIT_BREAKER_ENABLED = True
DIRECTION_CB_THRESHOLD_2 = 2              # consecutive losses → soft block (50% score reduction)
DIRECTION_CB_THRESHOLD_3 = 3              # consecutive losses → hard block (0% — all signals blocked)
DIRECTION_CB_SOFT_BLOCK_MINUTES = 15      # soft block duration after 2 losses
DIRECTION_CB_HARD_BLOCK_MINUTES = 30      # hard block duration after 3+ losses
DIRECTION_CB_EXTENDED_BLOCK_MINUTES = 60  # extended block after 4+ losses
DIRECTION_CB_RECOVERY_WINS = 2            # consecutive wins needed to reset counter
```

**Implementation in `signal_compactor.py`:**
- New function `_check_direction_circuit_breaker(direction)` → returns ('PASS', 'SOFT_BLOCK', 'HARD_BLOCK')
- New state tracking: `_direction_loss_streak` dict in memory (or small SQLite table)
- Called early in `_score_signal()` — before other filters
- Integrates with existing `_is_direction_locked()` — circuit breaker is a stricter version

**State machine:**
```
NORMAL → 1 loss → NORMAL (count=1)
       → 2 losses → SOFT_BLOCK (15min, 50% score)
       → 3 losses → HARD_BLOCK (30min, 0% score)
       → 4+ losses → EXTENDED_BLOCK (60min, 0% score)
       
SOFT_BLOCK → 1 win → NORMAL (reset)
           → 1 loss → HARD_BLOCK

HARD_BLOCK → 2 wins → NORMAL (reset)
           → 1 loss → EXTENDED_BLOCK

Any block → timer expires → NORMAL (but count persists for 4 hours)
```

---

### Layer 4: Alt-BTC Divergence Check

**What:** Detect when alts are decoupling from BTC — bleeding while BTC is flat or rising. This catches early contagion before it hits the broader market.

**Why:** During the transition, some alts (AIXBT, DOGE, COMP) were already falling while BTC was still relatively stable. LONG signals on these alts failed because they were in their own bearish micro-regime. Checking alt-BTC correlation catches this.

**How:**
- Track each alt's 30m price change vs BTC's 30m price change
- If alt is falling (negative 30m change) while BTC is flat/slightly positive → divergence detected
- Divergence → block LONG signals on that specific alt
- This is per-token, not global — catches individual alt weakness early

**New constants in `hermes_constants.py`:**
```python
ALT_BTC_DIVERGENCE_ENABLED = True
ALT_BTC_DIVERGENCE_WINDOW = 30             # minutes — comparison window
ALT_BTC_DIVERGENCE_THRESHOLD = -0.30       # % — alt 30m change below this = bearish
ALT_BTC_DIVERGENCE_BTC_MIN = -0.10         # % — BTC must be above this (not crashing) for divergence to matter
ALT_BTC_DIVERGENCE_LONG_PENALTY = 0.4      # multiplier — reduce LONG signal scores on divergent alts
ALT_BTC_DIVERGENCE_SHORT_BOOST = 1.2       # multiplier — boost SHORT signals on divergent alts
```

**Implementation in `signal_compactor.py`:**
- New function `_check_alt_btc_divergence(token, btc_momentum)` → returns ('ALIGNED', 'DIVERGENT_BEARISH', 'DIVERGENT_BULLISH')
- Read alt's `price_change_30m` from `token_speeds` table
- Compare with BTC's `price_change_30m`
- Called in `_score_signal()` — applies divergence penalty/boost

**Divergence matrix:**

| BTC 30m | Alt 30m | Classification | Effect on LONG | Effect on SHORT |
|---------|---------|---------------|----------------|-----------------|
| > -0.10% | > -0.10% | ALIGNED | No change | No change |
| > -0.10% | < -0.30% | DIVERGENT_BEARISH | 0.4x penalty | 1.2x boost |
| > -0.10% | -0.30% to -0.10% | MILD_DIVERGENCE | 0.7x penalty | 1.0x |
| < -0.10% | any | BTC_BEARISH | Use BTC momentum filter instead | No change |

---

## Integration Architecture

All 4 layers feed into `_score_signal()` in `signal_compactor.py`:

```
Signal enters _score_signal()
  │
  ├─ Layer 3: Circuit Breaker → HARD_BLOCK? → return 0 (skip all other filters)
  │                                        → SOFT_BLOCK? → continue with 0.5x multiplier
  │
  ├─ Layer 1: Gradient Detection → COOLING? → mark for Layer 2
  │
  ├─ Layer 2: Directional Bias → apply bias multiplier based on BTC momentum + gradient
  │
  ├─ Layer 4: Alt-BTC Divergence → apply per-token divergence penalty/boost
  │
  ├─ [existing filters: chop detector, directional outcome, momentum, etc.]
  │
  └─ Final score → compare against threshold → pass/fail
```

**Layer 3 (Circuit Breaker) runs FIRST** — it's the emergency brake. If the direction is hard-blocked, no other layer matters.

**Layers 1+2 work together** — gradient detection feeds into directional bias. COOLING state makes the bias more aggressive.

**Layer 4 is per-token** — it catches individual alt weakness that the global layers miss.

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add ~20 new constants for all 4 layers |
| `scripts/signal_compactor.py` | Add 4 new functions, integrate into `_score_signal()` |
| `scripts/btc_crash_filter.py` | Add gradient state to crash detection context |

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/btc_gradient_cache.py` | (Optional) Cache BTC velocity snapshots for gradient calculation. Could also be inline in signal_compactor.py. |

---

## Expected Impact

Based on the transition zone data:

| Layer | Trades Affected | Estimated PnL Improvement |
|-------|----------------|--------------------------|
| Gradient Detection | ~8 LONGs that fired during COOLING | +$0.50 (avoided losses) |
| Directional Bias | ~5 counter-trend signals penalized | +$0.30 (reduced losses) |
| Circuit Breaker | AIXBT 2nd+3rd loss, other repeats | +$0.50 (blocked repeat losers) |
| Alt-BTC Divergence | ~3 LONGs on bleeding alts | +$0.25 (avoided losses) |
| **Total estimate** | | **+$1.55 (from -$1.45 to ~+$0.10)** |

**Conservative estimate:** Even 50% effectiveness would save ~$0.75 in the transition zone.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Over-filtering → signal starvation | Circuit breaker has recovery mechanism (2 consecutive wins to reset). Bias is a multiplier, not a block. |
| Gradient detection false positives (brief BTC dip that recovers) | Use 15-minute acceleration window — short dips don't trigger COOLING |
| Alt-BTC divergence too noisy | Only trigger on strong divergence (< -0.30%), mild divergence gets reduced penalty |
| Interaction with existing chop detector | Circuit breaker is stricter — if CB fires, chop detector is redundant. No conflict. |

---

## Testing Plan

1. **Backtest on last 100 trades:** Apply all 4 layers retroactively, compute what the transition zone PnL would have been
2. **Paper trade for 1 week:** Run all 4 layers in LOG-ONLY mode (score modified but not blocking) to verify they fire correctly
3. **Gradual rollout:**
   - Week 1: Layer 3 only (Circuit Breaker) — highest impact, lowest risk
   - Week 2: Add Layer 4 (Alt-BTC Divergence) — per-token, safe
   - Week 3: Add Layers 1+2 (Gradient + Bias) — global changes, need validation

---

## Implementation Priority

1. **Layer 3 (Circuit Breaker)** — HIGHEST IMPACT, implements in 1-2 hours. Prevents repeat losers like AIXBT.
2. **Layer 4 (Alt-BTC Divergence)** — PER-TOKEN, safe. Catches individual alt weakness.
3. **Layer 1 (Gradient Detection)** — EARLY WARNING. Needs snapshot storage.
4. **Layer 2 (Directional Bias)** — GLOBAL CHANGE. Needs careful tuning of multipliers.

---

## Data from Last 100 Trades (Reference)

```
Overall:  49W/51L = 49% WR
LONG:     23W/33L = 41% WR
SHORT:    26W/18L = 59% WR

Transition zone (trades 26-75): 30L/20S, net PnL: $-1.45
- Worst signal: ema300_dip_short (3W/7L, -$0.83)
- Worst signal: sma20_dip (0W/5L, -$0.73) — all LONGs in falling market
- Worst repeat: AIXBT LONG 0W/3L (-$0.78)
```
