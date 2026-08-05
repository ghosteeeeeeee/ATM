# Z_MAX blocks SHORT at extended z-scores — BSV case 2026-05-28

## Symptom
BSV in sustained downtrend. Z-scores: S=-3.301 M=-3.280 L=-3.209 (all negative =
SHORT direction). System should have fired SHORT repeatedly but fired nothing.

## Root Cause
Z_MAX=3.0 rejects ANY period where |z| > 3.0, even when:
- z is negative (correct SHORT direction — not a reversal call)
- the move is not reversing — it's accelerating into the trend

With Z_MAX=3.0 and z~-3.3:
```
abs(z)=3.3 > 3.0  →  vote = None  →  0/3 periods voting  →  no signal
```

Changing Z_MAX to 5.0 with Z_MIN=1.0 → same bars all fire SHORT correctly.

## Design Intent (from code comment + anatomy)
Z_MAX upper bound was meant to reject "overextended" moves where the move had gone
so far a mean-reversion reversal was imminent. The assumption: z > +3 or z < -3
means the price has diverged so far from the mean that a snap-back is likely.

## The Bug Pattern (when Z_MAX fires incorrectly)
1. Asset in a structural downtrend — not a temporary spike
2. z-score drops continuously below -3.0 as the trend accelerates
3. Every period (14/50/150-bar) has |z| > Z_MAX → all periods rejected
4. Result: signal completely silent during the exact move you want to catch
5. The "overextended" reading is actually "continuing strong momentum" in this context

## Diagnostic Query
```python
# Compute z-scores at each bar for last 30 bars — shows which bars trigger and why
LB_S, LB_M, LB_L = 14, 50, 150
Z_MIN, Z_MAX = 2.0, 3.0  # current
# Result: all bars → None (|z| > Z_MAX on reject)

Z_MIN, Z_MAX = 1.0, 5.0  # proposed fix
# Result: all bars → SHORT (|z| in range, z<0)
```

## Fix
hermes_constants.py — lower Z_MIN and raise Z_MAX:
```python
# Current (blocks extended moves at |z|>3):
Z_SHORT_Z_MIN = 2.0;  Z_SHORT_Z_MAX = 3.0
Z_MID_Z_MIN   = 2.0;  Z_MID_Z_MAX   = 3.0
Z_LONG_Z_MIN  = 2.0;  Z_LONG_Z_MAX  = 3.0

# Recommended for SHORT-trending assets:
Z_SHORT_Z_MIN = 1.0;  Z_SHORT_Z_MAX = 5.0
Z_MID_Z_MIN   = 1.0;  Z_MID_Z_MAX   = 5.0
Z_LONG_Z_MIN  = 1.0;  Z_LONG_Z_MAX  = 5.0
```

## Tuning Framework
| Market condition | Z_MAX suggestion |
|------------------|------------------|
| Range-bound / consolidating | 3.0 (catches reversals, no extended moves) |
| Trending, wants to catch continuation | 5.0+ |
| Very volatile assets (BSV-like) | 5.0+ with Z_MIN=1.0 |

## Related
- mtp-zscore-signal-anatomy-2026-05-28.md — signal anatomy from same date (LONG case)
- zscore-tuner-bug md — tuner sweep failures
- zscore-momentum-debug.md — momentum calibration
