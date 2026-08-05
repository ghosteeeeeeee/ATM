# SNX Slow Grind Analysis — mtp-zscore Tuning Case Study (2026-05-29)

## The Move

SNX drifted from 0.295 → 0.320 (+8.67%) over 3 hours, 15:25–18:30 UTC.
Pace: ~0.05%/min — slow, continuous, no explosive spike.

```
15:25 | 0.29509
15:45 | 0.29760   (+0.85%)
16:15 | 0.29890   (+1.29%)
16:45 | 0.30380   (+2.96%)
17:15 | 0.30620   (+3.76%)
17:45 | 0.31270   (+5.97%)
18:15 | 0.32020   (+8.51%)
18:30 | 0.31993   (+8.42%)
```

## mtp-zscore Simulation Results (all configs: 3/3 agree, z_max=5.0)

| Config | Fires | First | Last | Direction |
|--------|-------|-------|------|-----------|
| 50/100/150 z_min=1.0 (current) | 109 | 17:07 | 18:28 | LONG |
| 15/30/60 z_min=0.5 | 157 | 16:06 | 18:22 | LONG (with early SHORT) |
| 15/30/60 z_min=0.75 | 139 | 16:08 | 18:22 | LONG (with early SHORT) |
| **20/40/80 z_min=0.5** | **147** | **16:18** | **18:23** | **LONG (cleaner)** |
| 10/20/40 z_min=0.5 | 146 | 15:58 | 18:22 | LONG (most SHORT noise) |

## The SHORT Noise Problem

Faster configs (15/30/60) fire SHORT at 16:06–16:58 before flipping to LONG.
These are NOT false shorts — they're the mtp-zscore system correctly reading the 1-2 bar
pullbacks within the slow grind. When SNX had a -0.2% to -0.5% pullback, the short window
z-score went negative while mid/long were still positive → direction disagreement (no fire).

But when the pullback was slightly larger (e.g., 15:55–16:00: -0.2%), the short window
z-score went sufficiently negative that all 3 periods agreed on SHORT briefly.

**This is a real detection problem, not a code bug.** The system is working as designed —
the issue is that the design threshold (z_min=1.0) is too low on these fast windows
for this market character.

## Solution: EMA-Angle Trend Filter

Rather than raising z_min (which delays valid entries), add a trend filter:
- Only allow LONG when EMA300 angle > 0 (uptrend confirmed)
- Only allow SHORT when EMA300 angle < 0 (downtrend confirmed)

This kills fake SHORT signals during slow grinding uptrends without affecting detection speed.

## Recommended Constants (Option A — Balanced)

```python
MTP_ZSCORE_LB_SHORT = 20    # was 50  — fast response to move starts
MTP_ZSCORE_LB_MID   = 40    # was 100
MTP_ZSCORE_LB_LONG  = 80    # was 150
Z_SHORT_Z_MIN      = 0.5   # was 1.0  — lower threshold = earlier detection
Z_MID_Z_MIN        = 0.5   # was 1.0
Z_LONG_Z_MIN       = 0.5   # was 1.0
# Code change needed: EMA-angle trend filter (EMA300 angle gate in detect_mtp_zscore)
```

## What This Doesn't Fix

This tuning helps SLOW directional moves. It does NOT fix:
- XLM-style choppy stair-step runs (still fires too often — see mtp-zscore-xlm-choppy-run)
- Explosive blow-off moves (z_score surges past z_max=5.0 and gets rejected)

These are separate failure modes requiring different solutions.