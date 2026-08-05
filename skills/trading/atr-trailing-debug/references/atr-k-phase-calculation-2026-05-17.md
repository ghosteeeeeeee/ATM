# ATR TP/SL K/Phase Calculation — T's Reference
**Date:** 2026-05-17
**Purpose:** Complete walkthrough of the ATR TP/SL computation chain with K multipliers and phase logic.

---

## The Three-Stage Pipeline

```
ATR(14) / entry_price  →  atr_pct
        ↓
Stage 1: _atr_tier(atr_pct)         — volatility bucket → base k
        ↓
Stage 2: _phase_from_pct()          — momentum phase   → phase multiplier
        ↓
Stage 3: compute_atr_sl_tp()         — apply floors + trailing gate
        ↓
   new_sl / new_tp  →  _persist_atr_levels()  →  DB
```

---

## Stage 1 — Volatility Tier (K Base)

Source: `hermes_constants.py` lines 293-304 + `_atr_tier()` in `tpsl_utils.py:61`

| atr_pct | Tier | Base k | Formula result |
|---------|------|--------|----------------|
| < 1% (LOW) | ATR_K_LOW_VOL | 1.0 | SL = 1.0 × ATR |
| 1–3% (NORMAL) | ATR_K_NORMAL_VOL | 0.75 | SL = 0.75 × ATR |
| > 3% (HIGH) | ATR_K_HIGH_VOL | 0.5 | SL = 0.5 × ATR |

**Example AVAX SHORT** @ entry=$9.244, ATR=0.0236 (0.26%):
- atr_pct = 0.0236/9.244 = 0.00255 → **LOW_VOL** → k=1.0
- SL distance = 1.0 × 0.0236 = $0.0236

**Example STBL SHORT** @ entry=$0.03194, ATR=$0.0003 (0.79%):
- atr_pct = 0.0003/0.03194 = 0.94% → **LOW_VOL** → k=1.0
- Since 0.94% < ATR_SL_MIN (0.50%), floor overrides: SL = entry × 0.50%

---

## Stage 2 — Phase Multiplier

Source: `hermes_constants.py` lines 331-342 + `_phase_from_pct()` in `tpsl_utils.py:73-88`

**Phase detection (direction-specific percentile):**

| Direction-specific percentile | Velocity > 0 | Velocity < 0 |
|------------------------------|-------------|-------------|
| ≥ 90 | accelerating | exhaustion |
| 70–89 | building | exhaustion |
| < 70 | neutral | neutral |

**Phase multipliers applied to base k:**

| Phase | Stall (vel < 0) | Fast (pctl ≥ 70) | Slow (pctl < 70) |
|-------|----------------|-----------------|-----------------|
| neutral | base_k | base_k | base_k |
| building | base_k | base_k | base_k |
| accelerating | **0.25** | **0.15** | **0.10** |
| exhaustion | **0.25** | **0.15** | **0.10** |
| extreme | **0.10** | **0.05** | **0.05** |

**final_k = base_k × phase_multiplier**

When all positions showed `k=1.000` in the PM log — they were all NEUTRAL phase, no multiplier applied.

---

## Stage 3 — Floors, Caps, Trailing Gate

Source: `hermes_constants.py` lines 265-280 + `compute_atr_sl_tp()` in `tpsl_utils.py`

**Floors and caps:**

| Constant | Value | Applies to |
|---------|-------|-----------|
| ATR_SL_MIN | 0.005 (0.50%) | Established trades — floor |
| ATR_SL_MAX | 0.007 (0.70%) | Established trades — cap |
| ATR_TP_MIN | 0.015 (1.5%) | Established trades — floor |
| ATR_TP_MAX | 0.05 (5.0%) | Established trades — cap |
| ATR_SL_MIN_INIT | 0.003 (0.30%) | New trades — floor |
| ATR_SL_MAX_INIT | 0.005 (0.50%) | New trades — cap |
| ATR_SL_MIN_ACCEL | 0.007 (0.70%) | ACCELERATING phase — floor |
| ATR_TP_MIN_ACCEL | 0.010 (1.0%) | ACCELERATING phase — floor |

**TP formula:**
```
TP = ref_price × (1 - k × atr_pct × 1.25)
```
Where `1.25` = `ATR_TP_K_MULT` (makes TP tighter than SL proportionally).

**Trailing gate (tpsl_utils.py lines 397-434):**
- SHORT: `needs_sl = True` only when `new_sl < current_sl` (can only tighten, never loosen)
- LONG: `needs_sl = True` only when `new_sl > current_sl` (can only lower, never raise)

---

## What T Can Adjust Right Now

| Knob | Default | Effect if raised | Effect if lowered |
|------|---------|-----------------|------------------|
| `ATR_K_LOW_VOL` | 1.0 | Wider SL for low-vol | Tighter SL — more stop-outs |
| `ATR_K_NORMAL_VOL` | 0.75 | Wider SL for mid-vol | Tighter SL |
| `ATR_K_HIGH_VOL` | 0.5 | Wider SL for high-vol | Tighter SL |
| `ATR_SL_MIN` | 0.005 (0.50%) | Tighter overall SL floor | Wider floor — less stop-outs |
| `ATR_SL_MAX` | 0.007 (0.70%) | Raise cap | Lower cap — smaller SL range |
| `ATR_TP_MIN` | 0.015 (1.5%) | TP farther from entry | TP closer — take profit sooner |
| `K_PHASE_ACCEL_STALL` | 0.25 | Exit faster in accel stall | Stay longer |
| `K_PHASE_ACCEL_FAST` | 0.15 | Exit faster in accel fast | Stay longer |
| `K_PHASE_EXT_FAST` | 0.05 | Ultra-tight in extreme fast | Looser in extreme fast |
| `ATR_TP_K_MULT` | 1.25 | TP farther (bigger wins) | TP closer (faster wins) |

**For current positions** (all showed `k=1.000` = NEUTRAL phase): phase multipliers are inactive. Main levers are base K values + SL/TP floors.

---

## Two Phase Detection Systems (Warning)

| System | Used by | Thresholds |
|--------|---------|-----------|
| `_phase_from_pct()` in tpsl_utils.py | ATR k scaling | 50 / 70 / 90 |
| `detect_phase()` in signal_gen.py | Signal generation | 60 / 75 / 88 / 95 |

These produce DIFFERENT phase labels for the same coin/momentum state. The ATR k scaling uses `_phase_from_pct`, NOT `detect_phase`. Do not assume they agree.