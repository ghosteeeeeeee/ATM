# Plan: zscore-pump SHORT Divergence Fix + Constants Hardening

**Date:** 2026-05-24
**Status:** Ready for Implementation (awaiting approval)
**Type:** Code fix + constants tuning

---

## Context: What Went Wrong

### STRK SHORT (May 24, 14:18 UTC)
- Signal: `rs-r478,zscore-pump-`, conf=83.8, z=-5.777
- Entry: 0.03914 → ATR SL hit at -1.303% after 6422s (~107 min)
- z=-5.777 = blow-off bottom (price collapsing, reversal imminent), but zscore-pump treated it as bearish continuation
- Immediately pumped against us — was a local bottom entry, not a short continuation

### PROVE SHORT (May 24, 14:18 UTC)
- Signal: `rs-r478,rs-r96,zscore-pump-`, conf=82.02, z=-4.606
- Entry: 0.26411 → ATR SL hit at -1.028% after 6399s (~107 min)
- Same pattern: extreme negative z at the bottom, caught a falling knife

### Root Cause
The `_check_divergence()` function in `zscore_pump.py` **only validates positive z-scores** (LONG signals). For SHORT signals, it returns `False` immediately at line 130 without any analysis:

```python
peak_z = max(recent_zs)
if peak_z < ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
    return False  # ← almost always triggers for negative z
```

This means every zscore-pump SHORT passes through `_check_divergence()` unexamined — no blow-off bottom detection, no reversal scrutiny.

---

## Phase 1: Code Fix (Minimal, Targeted)

**File:** `/root/.hermes/scripts/signals/zscore_pump.py`

### Change 1: Add `direction` parameter to `_check_divergence()`

**Current (line 93):**
```python
def _check_divergence(prices: list, lookback: int) -> bool:
```

**New:**
```python
def _check_divergence(prices: list, lookback: int, direction: str) -> bool:
```

### Change 2: Update the call site at line 270

**Current:**
```python
if _check_divergence(prices, lookback):
```

**New:**
```python
if _check_divergence(prices, lookback, direction):
```

### Change 3: Replace the divergence check block (lines 127-152)

**Current:**
```python
    peak_z = max(recent_zs)
    if peak_z < ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
        return False  # never got extreme — no divergence possible

    peak_idx = max(idx for idx, z in enumerate(recent_zs) if z == peak_z)
    bars_since_peak = len(recent_zs) - 1 - peak_idx

    if bars_since_peak < ZSCORE_PUMP_DIVERGENCE_BARS:
        return False

    neg_vel_bars = 0
    for i in range(peak_idx + 1, len(recent_zs)):
        vel = recent_zs[i] - recent_zs[i - 1]
        if vel < ZSCORE_PUMP_DIVERGENCE_VEL_THD:
            neg_vel_bars += 1
        elif vel > 0:
            neg_vel_bars = 0
        else:
            pass

    if neg_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
        return True  # divergence detected — REJECT signal

    return False
```

**New (replaces entire block lines 127-152):**
```python
    peak_z = max(recent_zs)   # most positive z in window
    nadir_z = min(recent_zs)  # most negative z in window

    # ── LONG divergence ─────────────────────────────────────────────────────
    # Pattern: z spiked extremely positive, now collapsing (VVV top reversal)
    # Catches: z=+4.16 peak → dropping for 8+ bars while price makes new highs
    if direction == 'LONG' and peak_z >= ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
        peak_idx = max(idx for idx, z in enumerate(recent_zs) if z == peak_z)
        bars_since_peak = len(recent_zs) - 1 - peak_idx
        if bars_since_peak >= ZSCORE_PUMP_DIVERGENCE_BARS:
            neg_vel_bars = 0
            for i in range(peak_idx + 1, len(recent_zs)):
                vel = recent_zs[i] - recent_zs[i - 1]
                if vel < ZSCORE_PUMP_DIVERGENCE_VEL_THD:
                    neg_vel_bars += 1
                elif vel > 0:
                    neg_vel_bars = 0
            if neg_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
                return True  # LONG divergence — REJECT

    # ── SHORT divergence ────────────────────────────────────────────────────
    # Pattern: z was extremely negative (blow-off bottom), now recovering
    # Catches: z=-5.77 crash → turning back up = reversal, not continuation
    # This is what killed STRK and PROVE
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
                    pos_vel_bars = 0  # reset if z keeps falling (still crashing)
            if pos_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
                return True  # SHORT divergence — REJECT

    return False
```

---

## Phase 2: Constants Tuning (after code fix is live)

Once the SHORT side is protected by code, these constants become effective:

| Constant | Current | Proposed | Effect |
|---|---|---|---|
| `ZSCORE_PUMP_DIVERGENCE_EXTREME_Z` | 3.5 | 2.5 | Catches blow-off bottoms earlier (z=-2.5 instead of z=-3.5) |
| `ZSCORE_PUMP_COOLDOWN_BARS` | 5 | 20 | Prevents re-firing into chop/bounce after initial signal |
| `RS_DECIDER_MIN_TOUCHES` | 200 | 300 | Only strong RS levels boost conf; filters out r478 noise |
| `ZSCORE_PUMP_THRESHOLD` | 3.0 | 3.5 | Very strong moves only — reduces total signal volume |

---

## Verification Steps

1. **Unit test `_check_divergence()` in isolation** — mock `prices` with a blow-off bottom recovery pattern (z=-5.0 → rising back up), verify it returns `True` for `direction='SHORT'`
2. **Verify existing LONG behavior unchanged** — same VVV pattern test for `direction='LONG'` returns `True`
3. **Grep + py_compile after patch** — confirm no syntax errors
4. **Watch the next STRK/PROVE signals** — they should be rejected with log message "SHORT divergence detected"
5. **Check PostgreSQL signals table** — conf should be lower on bounce-type SHORTs (divergence blocks before conf is computed)

---

## What This Prevents

- STRK z=-5.777 SHORT at 14:18 → **REJECTED** (blow-off bottom recovery)
- PROVE z=-4.606 SHORT at 14:18 → **REJECTED** (blow-off bottom recovery)
- Future falling knife shorts at z < -2.5 with recovering momentum → **REJECTED**
- Mid-chop re-fires (COOLDOWN_BARS=20) → **BLOCKED**

---

## What This Does NOT Fix (future work)

- ATR SL floor values still override ACCEL phase in `tpsl_utils.py` — first-candle-tight SL needs code change
- `momentum_state`, `rsi_14`, `macd_hist` null in all signal DB records — no price-based confirmation available yet for signal filtering
- Bidirectional confusion (same token firing LONG and SHORT repeatedly) — needs a coherence filter between same-token signals