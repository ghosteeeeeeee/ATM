# Hermes Constants ATR Tweak — 2026-05-21

T adjusted hermes_constants.py values. Full analysis before implementing any further changes.

## What Changed

| Constant | Old | New | Δ |
|---|---|---|---|
| `K_PHASE_ACCEL_FAST` | 0.10 | 0.08 | -20% tighter |
| `K_PHASE_EXH_FAST` | 0.10 | 0.08 | -20% tighter |
| `K_PHASE_EXT_FAST` | 0.10 | 0.08 | -20% tighter |
| `ATR_K_LOW_VOL` | 1.0 | 0.75 | -25% |
| `ATR_K_NORMAL_VOL` | 2.0 | 0.50 | -75% tighter |
| `ATR_K_HIGH_VOL` | 2.5 | 0.25 | -90% tighter |
| `ATR_SL_MIN` | 0.010 (0.50%) | 0.013 (0.65%) | +30% floor |

## Impact Assessment

### NORMAL_VOL k drop (2.0 → 0.5) — biggest win
Old: at 2% ATR, SL = 4% — only profit_monster could capture anything before SL hit.
New: at 2% ATR, SL = 1% — gives trade room to run.
**This is the right direction.** The old k was way too high.

### HIGH_VOL tokens get biggest relief
Old k=2.5 → new k=0.25 is 10× tighter. High-vol tokens (3%+ ATR) can actually hold positions now.

### LOW_VOL tokens unchanged (floor catches them)
Old: k=1.0 × 0.5% ATR = 0.5% — below old floor (0.50%) anyway.
New: k=0.75 × 0.5% ATR = 0.375% — below new floor (0.65%). Floor wins. Same result.

### `K_PHASE_ACCEL_FAST = 0.08` — risk of cutting winners
SNX SHORT: pct_short=96, speed_pctl high → ACCELERATING fast lane → k = 0.50 × 0.08 = 0.04.
At 1% ATR: SL = 0.04% of price = $0.00012 from current price. One pullback and it's gone.
**T went too far.** The old value (0.10) was already tight. Recommend: 0.12 as middle ground.

## Recommendations (report only, no changes)

1. **Raise `K_PHASE_ACCEL_FAST` to 0.12** — 0.08 is too aggressive. 0.12 is a middle ground.
2. **Add `MIN_PNL_TIGHTEN_PCT` guard** — no minimum profit threshold before phase k kicks in.
   Trade opens at -0.3% but still gets ACCELERATING-phase k treatment. Add 0.5% profit gate.
3. **`ATR_TP_MIN_ACCEL` could raise from 0.011 (1.1%) to 0.015 (1.5%)** — given TP_K_MULT=1.25
   and k=0.5, TP may be tracking too fast. Adding 0.4% gives winners more room.
4. **Blacklist threshold for near-zero ATR tokens** — ATR% < 0.3% tokens get floor-only SL
   (0.65%). Hard to trade — skip regardless of signal quality.

## Key ATR Constants After Tweak

```
ATR_K_LOW_VOL      = 0.75   # <1% ATR
ATR_K_NORMAL_VOL   = 0.50   # 1-3% ATR  
ATR_K_HIGH_VOL     = 0.25   # >3% ATR
K_PHASE_ACCEL_FAST = 0.08   # ACCEL + fast momentum — TIGHT
ATR_SL_MIN         = 0.013   # 0.65% floor (was 0.50%)
ATR_TP_K_MULT      = 1.25   # TP tighter than SL
```

## Phase Detection — Two Systems (same as before, unchanged)

`_phase_from_pct` (tpsl_utils.py:73) — used for k scaling:
- ≥90 + vel>0 → 'accelerating'; vel≤0 → 'exhaustion'
- 70-89 + vel>0 → 'building'; vel≤0 → 'exhaustion'
- <70 → 'neutral'

`detect_phase` (signal_gen.py) — used for signal generation:
- PHASE_BUILDING=60, PHASE_ACCELERATING=75, PHASE_EXHAUSTION=88, PHASE_EXTREME=95
- Also checks 'quiet' when pct < 60 AND |vel| < 0.05

**These produce different labels.** ATR k scaling uses `_phase_from_pct`, NOT `detect_phase`.