# zscore_pump Direction Flaw — FET Spike Trap
**Date:** 2026-05-22
**Session context:** T asked to analyze FET price history (last 3h) and why no LONG signal appeared despite a +1.94% rally. Also asked how to improve zscore_pump to catch reversal conditions.

---

## The Pattern Found

FET rallied from 0.19380 → 0.19784 (+1.94%) over 3 hours. Key timestamps:

| Time     | Price   | Z-score | Signal | What happened |
|----------|---------|---------|--------|----------------|
| 01:15    | 0.19408 | +1.653  | ---    | z first crosses +2.0 threshold |
| 01:16    | 0.19468 | **+4.581** | **LONG fired** | EXTREME spike — signal fires |
| 01:26    | 0.19417 | +1.022  | ---    | z drops below threshold (cooldown) |
| 01:31    | 0.19454 | +2.181  | LONG   | signal re-fires |
| 01:36    | 0.19420 | +0.825  | ---    | drops below threshold |
| 01:38    | 0.19389 | -0.146  | ---    | briefly negative |
| 02:40    | 0.19784 | +2.047  | LONG   | still elevated, price +1.94% from entry |

Our SHORT position was open at 0.19406. The signal fires LONG (blocked by open position check) but the direction is wrong for mean-reversion trading. We were already SHORT and the rally caught us.

---

## Root Cause: Momentum Signal Fires WRONG Direction at Extremes

`zscore_pump` philosophy: **"momentum, NOT mean-reversion. Ride the move, don't fade it."**

This creates a fundamental mismatch with our mean-reversion trading:
- `z > +2.0` → fires **LONG** (ride upward momentum)
- But at z=+4.58 (extremely overbought), we want **SHORT** (fade the extreme)

At extreme z-scores, the signal fires in the OPPOSITE direction of what our trading approach requires.

---

## Why zscore_pump Missed the Rally (No LONG Signal in Hot-Set)

1. Signal fired as `zscore_pump_long` at 01:16 — but our open position check blocked it:
   ```python
   if token.upper() in open_pos:  # {FET: 'SHORT'}
       continue  # skip — already in a position
   ```
2. So the LONG signal was correctly blocked by open position check.
3. BUT the underlying issue: the signal was LONG at exactly the local bottom before a +1.94% rally. The direction was fundamentally wrong.

---

## Divergence Check Analysis (Why It Didn't Save Us)

The divergence check (`_check_divergence`) was supposed to catch the spike-and-collapse:
- Peak z=+4.581 at 01:16
- 01:17: z=+4.125 (vel=-0.456, below VEL_THD=-0.5 threshold)
- 01:18: z=+3.776 (vel=-0.349)
- 01:19: z=+2.869 (vel=-0.907, well below threshold)

By bar 3 after the peak, z-velocity was -0.907. With `ZSCORE_PUMP_DIVERGENCE_BARS=3` and `ZSCORE_PUMP_DIVERGENCE_VEL_THD=-0.5`, the condition `neg_vel_bars >= 3` should have been met. **Signal should have been rejected.**

Why it wasn't: The check is called at the bar where z FIRST exceeds threshold (01:16, current bar = peak). At that moment, `bars_since_peak = 0`. With `ZSCORE_PUMP_DIVERGENCE_BARS = 3`, the condition `bars_since_peak < 3` is TRUE — it hasn't been 3 bars yet. Signal fires. Next bar (01:17) z is declining but it's too late — signal already fired.

**Fix:** `bars_since_peak >= 1` (not 3) before checking divergence. One bar of declining z-velocity after an extreme spike should be enough.

---

## The 5 Improvements to Make to zscore_pump

### 1. Flip Direction at Extreme Z-Scores (HIGHEST PRIORITY)

Add asymmetric direction logic for mean-reversion:

```
|z| > 3.0  →  fires OPPOSITE direction (fade the extreme)
  z > +3.0  →  fires SHORT (overbought → expect reversal down)
  z < -3.0  →  fires LONG  (oversold → expect reversal up)

|z| 2.0-3.0  →  fires SAME direction (momentum continuation)
  z > +2.0  →  fires LONG  (upward momentum)
  z < -2.0  →  fires SHORT (downward momentum)
```

At z=+4.581 (FET 01:16), signal would have fired SHORT instead of LONG — catching the exact top.

**Implementation location:** `detect_zscore_pump()` in `signals/zscore_pump.py` lines 229-284.

### 2. Require "Acceleration" — 2-3 Bars Above Threshold

Current behavior: fires the instant z crosses threshold.
Problem: single-bar spike (z=+4.581 at 01:16, then drops to +1.022 at 01:26) is a spike trap.

**Fix:**
```python
# In detect_zscore_pump(), before returning signal:
# Check z has been above threshold for >= 2 consecutive bars
if not _check_sustained_elevation(closes, lookback, threshold, min_bars=2):
    return None
```

### 3. ATR-Proportional Threshold

Fixed threshold (2.0) treats all tokens the same. Replace with:
```
threshold = max(1.5, min(3.0, atr_pct * 50))
```
For FET (ATR=0.042%): threshold = 2.1
For TAO (ATR=0.028%): threshold = 1.5
For volatile token (ATR=0.15%): threshold = 3.0 (capped)

### 4. Fix Divergence bars_since_peak >= 1 (not >= 3)

Change `ZSCORE_PUMP_DIVERGENCE_BARS = 3` → `= 1` in the bars_since_peak check.

Current: peak at bar N → check at bar N → bars_since_peak=0 → wait → check at bar N+3 → reject (too late)
Fixed: peak at bar N → check at bar N+1 → bars_since_peak=1 → reject immediately

### 5. "Second Leg" Confirmation at |z| > 3.5

For mean-reversion entries at extremes, require price to have pulled back from a local high/low first:

```
For SHORT at z > +3.5:
  - Current price < 20-bar high (confirms pullback occurred from local top)

For LONG at z < -3.5:
  - Current price > 20-bar low (confirms pullback occurred from local bottom)
```

This catches the exact FET pattern: at 01:16, price=0.19468 was the 20-bar high. A mean-reversion SHORT signal should have required price to be below that high first.

---

## Key Code Locations

| File | Lines | What to change |
|------|-------|----------------|
| `signals/zscore_pump.py` | 229-284 | `detect_zscore_pump()` — add asymmetric extreme direction flip |
| `signals/zscore_pump.py` | 93-153 | `_check_divergence()` — fix bars_since_peak >= 1 |
| `hermes_constants.py` | 591-609 | `ZSCORE_PUMP_THRESHOLD`, `ZSCORE_PUMP_DIVERGENCE_BARS`, new `ZSCORE_PUMP_MODE` flag |

---

## Session Metadata

- **Data source:** `/root/.hermes/data/candles.db` — `candles_1m(token, ts, open, high, low, close)` 1m candles
- **zscore_pump source:** `/root/.hermes/scripts/signals/zscore_pump.py`
- **Constants:** `/root/.hermes/scripts/hermes_constants.py` lines 591-609
- **Threshold:** ZSCORE_PUMP_THRESHOLD=2.0, ZSCORE_PUMP_LOOKBACK=100
- **Divergence:** ZSCORE_PUMP_DIVERGENCE_ENABLED=True, VEL_THD=-0.5, EXTREME_Z=2.5, BARS=3
- **Cooldown:** ZSCORE_PUMP_COOLDOWN_BARS=20 (~10 min on 1m)