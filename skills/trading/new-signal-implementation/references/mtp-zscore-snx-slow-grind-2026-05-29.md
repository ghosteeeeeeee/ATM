# mtp-zscore SNX Slow Grind — Case Study (2026-05-29)

## Context

T asked: "look at SNX 1min price-history between 15:25 and 18:30 on the 28th, I want to catch that move (or at least a part of it), how do we tweak mtp-zscore to catch that"

## The Move

SNX drifted from 0.295 → 0.320 (+8.67%) over 3 hours.
Pace: ~0.05%/min — slow, grinding, no explosive spike.

Current mtp-zscore (50/100/150, z_min=1.0) first fired at 17:07 — 42 min late.
The signal was correct once it fired, but missed the first third of the move.

## Key Insight

Current lookbacks (50/100/150) are calibrated for **explosive** moves. For slow grinding trends,
shorter windows + lower z_min catch the start ~40 min earlier.

## Simulation Results

| Config | First Fire | Direction |
|--------|-----------|-----------|
| 50/100/150 z_min=1.0 (current) | 17:07 | LONG |
| 15/30/60 z_min=0.5 | 16:06 | LONG (early SHORT noise) |
| 20/40/80 z_min=0.5 | 16:18 | LONG (cleaner) |
| 10/20/40 z_min=0.5 | 15:58 | LONG (most SHORT noise) |

## The SHORT Noise Problem

Faster lookbacks cause brief direction disagreements during small pullbacks within the slow uptrend.
Solution: add EMA300-angle trend filter (only LONG when angle > 0).

## Recommended Fix

```python
# hermes_constants.py
MTP_ZSCORE_LB_SHORT = 20   # was 50
MTP_ZSCORE_LB_MID   = 40   # was 100
MTP_ZSCORE_LB_LONG  = 80   # was 150
Z_SHORT_Z_MIN       = 0.5  # was 1.0
Z_MID_Z_MIN         = 0.5  # was 1.0
Z_LONG_Z_MIN        = 0.5  # was 1.0

# Code change in mtp_zscore.py: add EMA-angle trend filter
# Block LONG when EMA300 angle < 0, block SHORT when angle > 0
```

Full data and analysis: `../trading-signal-quality/references/mtp-zscore-snx-slow-grind-2026-05-29.md`