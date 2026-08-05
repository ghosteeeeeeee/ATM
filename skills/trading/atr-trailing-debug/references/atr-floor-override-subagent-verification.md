# ATR Floor Override — Subagent Verification (2026-05-24)

## Live Values (hermes_constants.py:270-299)

```
ATR_SL_MIN         = 0.015  # 1.5%
ATR_SL_MAX         = 0.017  # 1.7%
ATR_SL_MIN_ACCEL   = 0.01   # 1.0%
ATR_SL_MIN_INIT    = 0.01   # 1.0%
ATR_PCT_LOW_THRESH = 0.01   # 1%
ATR_PCT_HIGH_THRESH= 0.015  # 1.5%
ATR_K_LOW_VOL      = 0.5
ATR_K_NORMAL_VOL   = 1.0
ATR_K_HIGH_VOL     = 0.25
K_PHASE_ACCEL_STALL = 0.06
K_PHASE_ACCEL_FAST  = 0.07
```

## Verified Findings

### Finding 1: INIT == ACCEL floor (both 1.0%) — CONFIRMED
Both `ATR_SL_MIN_INIT` and `ATR_SL_MIN_ACCEL` = 0.01 (1.0%). No differentiation between new and established trades at the floor level.

### Finding 2: Phase multiplier bypassed by floor — CONFIRMED
Code: `tpsl_utils.py:371` — `eff_sl_pct = min(max(sl_pct, MIN_SL_PCT), ATR_SL_MAX)`

Example — NORMAL_VOL coin (atr_pct=1.5%):
- base_k = ATR_K_NORMAL_VOL = 1.0
- ACCEL phase multiplier = K_PHASE_ACCEL_FAST = 0.07
- Phase k = 1.0 × 0.07 = **0.07**
- sl_pct = k × atr_pct = 0.07 × 0.015 = 0.00105 (0.105%)
- Floor = ATR_SL_MIN_ACCEL = 0.01 (1.0%)
- 0.105% < 1.0% → **FLOOR BINDS** regardless of phase multiplier

The phase multiplier produces 0.105% SL, but the 1.0% floor overrides it entirely. Phase k of 0.06-0.07 (ACCEL) and 0.01-0.03 (EXH) are all overridden.

### Finding 3: Core bypass — `return base_k` when momentum_stats is None
`tpsl_utils.py:108-109`:
```python
if momentum_stats is None:
    return base_k  # NO phase tightening when momentum unavailable
```
When `momentum_stats` is unavailable (None), the phase multiplier is never applied — `base_k` is returned directly and the entire `_phase_from_pct` block is bypassed.

## What Fix Would Require

Two changes needed for true "first candle out" behavior:

1. **Constants**: ACCEL floor would need to be ≤ k_min × atr_min for the phase multiplier to govern. For ACCEL phase k=0.06-0.07 on a 1.5% ATR coin, the floor would need to be ≤ 0.001 (0.1%) for phase multipliers to take effect.

2. **Code fix**: Floor should not apply to ACCEL/EXH phases when `k × atr_pct < floor` — instead of overriding, the function should let the tight k×atr govern for these phases. Currently the floor unconditionally overrides all phase multipliers.

## Key Code Locations

| Location | Role |
|----------|------|
| `tpsl_utils.py:108-109` | `return base_k` when momentum_stats=None |
| `tpsl_utils.py:333` | `sl_pct = k * atr_pct` (k includes phase multiplier) |
| `tpsl_utils.py:354-363` | INIT vs ACCEL floor selection |
| `tpsl_utils.py:371` | `eff_sl_pct = min(max(sl_pct, MIN_SL_PCT), ATR_SL_MAX)` — floor overrides phase k |