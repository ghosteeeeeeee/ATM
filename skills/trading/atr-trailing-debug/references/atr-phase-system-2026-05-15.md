# ATR Phase System — Complete Reference (2026-05-15)

## Three-Stage Computation Model

```
entry_price + current ATR
        ↓
Stage 1: _atr_tier(atr_pct)         ← volatility → base_k
Stage 2: _atr_sl_k_scaled(...)      ← phase → k_final = base_k × phase_mult
Stage 3: compute_atr_sl_tp()       ← MIN/MAX floor + trailing gate
        ↓
   new_sl / new_tp → written to DB
```

---

## Stage 1 — ATR Tier (`_atr_tier` in tpsl_utils.py:61)

```python
def _atr_tier(atr_pct: float) -> float:
    if atr_pct < ATR_PCT_LOW_THRESH:      # < 1%
        return ATR_K_LOW_VOL               # 1.0
    elif atr_pct > ATR_PCT_HIGH_THRESH:    # > 3%
        return ATR_K_HIGH_VOL              # 0.5
    return ATR_K_NORMAL_VOL                # 0.75 (1–3%)
```

**Note:** hermes_constants.py comment says "k=1.0/2.0/2.5" — stale. Actual values are 1.0 / 0.75 / 0.5.

---

## Stage 2 — Phase Multiplier (`_atr_sl_k_scaled` in tpsl_utils.py:91)

### Phase Detection (`_phase_from_pct`)

```python
def _phase_from_pct(pct: float, velocity: float) -> str:
    if pct >= 90:
        return 'exhaustion' if velocity < 0 else 'accelerating'
    elif pct >= 70:
        return 'exhaustion' if velocity < 0 else 'building'
    return 'neutral'
```

Uses **direction-specific percentile** — `momentum_stats['percentile_long']` or `['percentile_short']` — NOT the overall speed percentile. `speed_percentile` param is only used for fast/slow sub-case branching.

### Sub-Case Branching

```python
stalling = (velocity < 0) and (phase_tier >= PHASE_TIER_ACCELERATING)

if phase_tier < PHASE_TIER_ACCELERATING:
    return base_k  # neutral / building — no squeeze

elif phase_tier == PHASE_TIER_ACCELERATING:
    if stalling:      mult = K_PHASE_ACCEL_STALL   # 0.25
    elif speed_pctl >= 70:  mult = K_PHASE_ACCEL_FAST  # 0.15
    else:              mult = K_PHASE_ACCEL_SLOW   # 0.10

elif phase_tier == PHASE_TIER_EXHAUSTION:
    if stalling:      mult = K_PHASE_EXH_STALL     # 0.25
    elif speed_pctl >= 70:  mult = K_PHASE_EXH_FAST   # 0.15
    else:              mult = K_PHASE_EXH_SLOW    # 0.10

else:  # EXTREME
    if stalling:      mult = K_PHASE_EXT_STALL    # 0.10
    else:             mult = K_PHASE_EXT_FAST     # 0.05  ← tightest possible
```

### Phase Multiplier Table

| Phase | Stall (vel < 0) | Fast (speed_pctl ≥ 70) | Slow (speed_pctl < 70) |
|---|---|---|---|
| neutral | base_k | base_k | base_k |
| building | base_k | base_k | base_k |
| accelerating | 0.25 | 0.15 | 0.10 |
| exhaustion | 0.25 | 0.15 | 0.10 |
| extreme | 0.10 | **0.05** | 0.05 |

**Effective k range:** base_k × 1.0 (neutral) → base_k × 0.05 (extreme-fast). With base_k=1.0, k_final = 0.05–1.0.

---

## Stage 3 — Floor + Trailing (`compute_atr_sl_tp` in tpsl_utils.py:239)

### New Trade Exception

```python
# If peak ≈ entry AND pnl > 0 → trade just opened
if is_new_trade:
    k = _atr_tier(atr_pct)          # reset to base k — no acceleration squeeze
    MIN_SL_PCT = ATR_SL_MIN_INIT    # 0.50% (wider for breathing room)
    MIN_TP_PCT = ATR_TP_MIN         # 1.5%
else:
    MIN_SL_PCT = ATR_SL_MIN_ACCEL   # 0.70% (tighter for established)
    MIN_TP_PCT = ATR_TP_MIN_ACCEL   # 1.0%
```

Prevents 0.05× base_k (extreme-fast) from squeezing a brand-new trade to near-zero.

### Clamping

```python
sl_pct = k * atr_pct
tp_pct = k * ATR_TP_K_MULT * atr_pct   # ATR_TP_K_MULT = 1.25

eff_sl_pct = min(max(sl_pct, MIN_SL_PCT), ATR_SL_MAX)
eff_tp_pct = min(max(tp_pct, MIN_TP_PCT), ATR_TP_MAX)
```

### Trailing Gate (only tighten, never loosen)

```python
# LONG: new_sl must be > current_sl
if new_sl > current_sl:  needs_sl = True   # tighten
else:                     new_sl = current_sl; needs_sl = False  # block

# SHORT: new_sl must be < current_sl
if new_sl < current_sl:  needs_sl = True   # tighten
else:                     new_sl = current_sl; needs_sl = False  # block
```

---

## Import Audit

| Constant | tpsl_utils.py | position_manager.py | self_close_watcher.py | hl-sync-guardian.py |
|---|---|---|---|---|
| `SL_PCT_FALLBACK` | inline import only | ✓ | | |
| `TP_PCT_FALLBACK` | | ✓ | | |
| `STOP_LOSS_DEFAULT` | | ✓ | | |
| `SL_PCT_MIN` | | ✓ | | |
| `ATR_PCT_FALLBACK` | ✓ | | ✓ | ✓ |
| `ATR_TP_K_MULT` | ✓ | | ✓ | ✓ |
| `ATR_SL_MIN/MAX` | ✓ | | | ✓ |
| `ATR_TP_MIN/MAX` | ✓ | | | ✓ |
| `ATR_SL_MIN/MAX_INIT` | ✓ | ✓ | | |
| `ATR_SL/MAX_ACCEL` | ✓ | | | ✓ |
| `ATR_TP_MIN/MAX_ACCEL` | ✓ | | | ✓ |
| `ATR_K_LOW/NORMAL/HIGH` | ✓ | ✓ | | |
| `ATR_PCT_LOW/HIGH_THRESH` | ✓ | | | |
| `PHASE_TIER_*` | ✓ | | | |
| `K_PHASE_*` | ✓ | ✓ | | |

**Inline import mess:** `SL_PCT_FALLBACK` appears as `from hermes_constants import SL_PCT_FALLBACK` inside `compute_atr_sl_price()` and `compute_atr_tp_price()` function bodies (lines 186, 220) — not at module level. This is intentional (local fallback only) but inconsistent with all other imports which are at module level.

---

## Key Constants Summary

| Group | Constant | Value |
|---|---|---|
| TP multiplier | `ATR_TP_K_MULT` | **1.25** — TP always tighter than SL |
| SL floors | `ATR_SL_MIN_INIT` / `ATR_SL_MIN_ACCEL` | 0.50% / **0.70%** |
| TP floors | `ATR_TP_MIN` / `ATR_TP_MIN_ACCEL` | 1.5% / **1.0%** |
| k tier | `ATR_K_LOW/NORMAL/HIGH_VOL` | **1.0 / 0.75 / 0.5** |
| Phase k | `K_PHASE_ACCEL_STALL` / `FAST` / `SLOW` | **0.25 / 0.15 / 0.10** |
| Phase k | `K_PHASE_EXH_STALL` / `FAST` / `SLOW` | **0.25 / 0.15 / 0.10** |
| Phase k | `K_PHASE_EXT_STALL` / `FAST` | **0.10 / 0.05** |