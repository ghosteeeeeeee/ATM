# SL Tightness Analysis — 2026-05-07

## Finding: 96% of Right-Signal Losses Were Preventable by Widening SL

From 126 SL-hit losses in trades.json:

| Category | Count | % |
|----------|-------|---|
| RIGHT signal (price moved our way, got stopped out) | 71 | 56% |
| WRONG signal (price never went our way) | 55 | 44% |

### For the 71 RIGHT_SIG losses:

| Metric | Value |
|--------|-------|
| Avg worst adverse move (max dip against us) | **0.334%** |
| Avg max favorable move (peak in our direction) | **0.107%** |

Signal was right but barely — price ticks +0.10%, then whips down -0.33% and hits our SL.

### SL survival analysis:

| SL Floor | RIGHT_SIG Saved | Still Lose (RIGHT_SIG) |
|----------|----------------|----------------------|
| 0.20% (was) | 0/71 (0%) | 71 |
| 0.50% (now) | 60/71 (85%) | 11 |
| 0.75% | 68/71 (96%) | 3 |
| 1.00% | 70/71 (99%) | 1 (COMP SHORT) |

**96% of right-signal losses would have been saved with a 0.75% SL.**

### Key trade: COMP SHORT
The 1 trade that can't be saved: worst_adr=+1.03%, max_fav=+0.03%.
Price immediately went against us and never returned. Signal was fundamentally wrong.

### Action Taken
Changed `ATR_SL_MIN_ACCEL` from 0.20% → **0.50%** in hermes_constants.py.

Further improvement possible: trailing SL activation at +0.15% profit (1.5× avg max_fav),
to lock in winners before the spike-and-reverse pattern cuts them.
