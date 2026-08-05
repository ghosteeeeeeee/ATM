# Z-Score Divergence: Short-Term Spot Lookback vs Signal Lookback

**Date:** 2026-05-18
**Signal:** zscore-pump+ on VVV
**Problem:** LONG opened at $14.136 (2026-05-18 03:12:07 UTC), SL hit at $14.036 (-0.70%). zscore-pump+ fired while z-score was collapsing from +2.985 toward negative. A SHORT would have been profitable.

## Key Lesson

When adding a momentum-divergence rejection gate to a z-score signal:
- **Use a separate, SHORT-TERM lookback for spot momentum** (e.g. 20 bars), independent of the signal's long trend lookback (100 bars)
- With 100-bar lookback, z-score never reaches 3.0 — it's too smoothed. The divergence is a SHORT-TERM phenomenon.
- The signal's lookback and the divergence check's lookback must be decoupled.

## Bug Path

1. First attempt: used signal's 100-bar lookback → peak_z = 1.543 << 3.0 → never rejects
2. Second attempt: EXTREME_Z lowered to 2.5, but still used 100-bar lookback → same failure
3. Third attempt: lookback split (20 short-term + 100 signal), but nested slice `prices[-25:]` inside `_check_divergence` discarded the peak at bar 91 (23 bars before window start) → reject=False
4. Fix: caller passes full 2x lookback window, `_check_divergence` uses it without further slicing → peak_z=2.985 >= 2.5, reject=True

## Correct Architecture

```
hermes_constants.py:
  ZSCORE_PUMP_DIVERGENCE_LOOKBACK = 20   # short-term spot lookback
  ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 2.5  # threshold for overextended
  ZSCORE_PUMP_DIVERGENCE_VEL_THD   = -0.3 # z-velocity below = negative momentum
  ZSCORE_PUMP_DIVERGENCE_BARS      = 3    # consecutive neg-vel bars to confirm

zscore_pump.py:
  detect_zscore_pump():
    wide_window = prices[-(lookback*2 + BARS + 2):]  # caller slices wide
    _check_divergence(wides_window, lookback=20)      # NO nested slice inside

  _check_divergence(prices, lookback):
    spot_lookback = ZSCORE_PUMP_DIVERGENCE_LOOKBACK  # use constant, not param
    z_series = compute_zscore(prices, lookback=spot_lookback)  # short-term z
    peak_idx = argmax(z_series)
    peak_z    = z_series[peak_idx]
    bars_since_peak = len(z_series) - 1 - peak_idx
    # count consecutive bars where z-velocity < VEL_THD after peak
```

## VVV Data Validation

- 163 bars of 1min VVV price data (01:52–03:20 UTC) from signals_hermes.db
- At signal time 03:11:08: z(20-bar) peaked at +2.985 at bar 91 (~03:00)
- Then declined: +2.731, +2.210, +2.893, +2.303, +1.938, +1.346, +1.211, +1.094, +1.339, +1.203, +1.086, +1.300, +1.182, +1.082, +0.997, +1.483, +1.395, +1.358
- Crashed: -0.640, -0.735, -0.852, -2.957
- Exactly 3 consecutive bars with z-velocity < -0.3 → REJECT confirmed

## Constants

| Constant | Value | Notes |
|---|---|---|
| DIVERGENCE_LOOKBACK | 20 | Short-term spot lookback, NOT the signal's 100-bar lookback |
| EXTREME_Z | 2.5 | With 20-bar lookback, z reaches +4 peak; 2.5 catches overextension |
| VEL_THD | -0.3 | z-velocity below this = negative momentum confirmation |
| BARS | 3 | Need 3 consecutive neg-vel bars to confirm divergence |

## Price Context

- VVV $14.085 at 03:00 UTC → $14.158 at 03:10 → $14.189 peak at 03:11 → $14.036 by 03:14
- Entry at $14.136 was right at the peak of the move — z-score was already crashing from +2.985
- Filter would have rejected the LONG at 03:11 when z was collapsing and price had marginal new highs
