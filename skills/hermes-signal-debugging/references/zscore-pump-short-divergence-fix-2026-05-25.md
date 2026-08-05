# zscore-pump SHORT Divergence Fix — 2026-05-25

## Problem

`_check_divergence()` in `signals/zscore_pump.py` only checked **positive** z-scores (LONG signals). For SHORT signals, it returned `False` at line 130 before any analysis — meaning every zscore-pump SHORT passed through unexamined.

**Cases:** STRK SHORT (z=-5.777) and PROVE SHORT (z=-4.606) both hit ATR SL ~107 min after entry. Both were blow-off bottoms (reversal imminent), not short continuation.

## Root Cause

```python
# OLD — only examines positive z
peak_z = max(recent_zs)
if peak_z < ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:  # threshold = 3.5
    return False  # ← fires for nearly ALL negative-z (SHORT) signals
```

For STRK at z=-5.777: `peak_z` = least-negative value in window (e.g., -0.2), which is never ≥ 3.5 → returns False, no divergence check.

## Fix Applied (2026-05-25)

**1. Function signature** — added `direction` parameter:
```python
def _check_divergence(prices: list, lookback: int, direction: str) -> bool:
```

**2. Call site** — forward `direction` at line 270:
```python
if _check_divergence(prices, lookback, direction):
```

**3. Divergence block** — replaced single-direction block with bidirectional logic:

```python
peak_z = max(recent_zs)
nadir_z = min(recent_zs)

# LONG: z spiked positive, now collapsing (VVV top reversal)
if direction == 'LONG' and peak_z >= ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
    # ... peak detection, velocity count, REJECT if recovering

# SHORT: z was extremely negative, now recovering (blow-off bottom)
if direction == 'SHORT' and nadir_z <= -ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
    nadir_idx = min(idx for idx, z in enumerate(recent_zs) if z == nadir_z)
    bars_since_nadir = len(recent_zs) - 1 - nadir_idx
    if bars_since_nadir >= ZSCORE_PUMP_DIVERGENCE_BARS:
        pos_vel_bars = 0
        for i in range(nadir_idx + 1, len(recent_zs)):
            vel = recent_zs[i] - recent_zs[i - 1]
            if vel > -ZSCORE_PUMP_DIVERGENCE_VEL_THD:  # z rising (less negative)
                pos_vel_bars += 1
            elif vel < 0:
                pos_vel_bars = 0  # reset if still crashing
        if pos_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
            return True  # SHORT divergence — REJECT
```

## Key Lesson

**When adding a `direction` parameter to a filtering function, the call site MUST forward it.** If the call site doesn't pass the new parameter, the SHORT/LONG branch is dead code — the function still runs but `direction` is never received, so only the default path executes.

## Verification

```bash
cd /root/.hermes/scripts && python3 -c "import py_compile; py_compile.compile('signals/zscore_pump.py', doraise=True); print('Syntax OK')"
```

Watch for log: `SHORT divergence detected — REJECT` in pipeline output for future blow-off bottom SHORTs.

## Phase 2 (pending T approval)

Constants tuning still needed for full protection:
| Constant | Current | Proposed |
|---|---|---|
| `ZSCORE_PUMP_DIVERGENCE_EXTREME_Z` | 3.5 | 2.5 |
| `ZSCORE_PUMP_COOLDOWN_BARS` | 5 | 20 |

Requires T approval before touching `hermes_constants.py`.