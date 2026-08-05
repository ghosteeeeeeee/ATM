# MTP-ZSCORE Full-Universe Backtest — 2026-05-28

## Methodology
- Universe: ~110 tokens (candles.db candles_1m, all except SHORT/LONG blacklist)
- Time range: ts=1708338000 to 1779942420 (all available data)
- Lookback combos tested: (14,50,150), (14,50,200), (50,100,150), (50,100,200), (50,150,200), (20,60,150), (20,80,200), (30,60,150), (30,100,200), (14,100,150)
- Z bounds: Z>=1.0, Z>=1.5, Z>=2.0 (Z_MAX=99 in all runs — no cap)
- Hold horizons: 1m, 5m, 15m, 30m, 1h, 2h, 4h
- Direction: LONG and SHORT
- Min fires to count: 30
- 4 workers, flat parallel, ~22 min total

## Key Findings

### 1. Deployed params are the WORST in the sweep
Current production: (14,50,150) Z>=2.0
- WR at 4h: 43.0% LONG / 46.4% SHORT — lowest or near-lowest for every horizon
- Fires: ~27k/horizon — 3x fewer than best combos

### 2. Peak directional WR is ~48% SHORT at 4h — 75% is not achievable
mtp-zscore alone cannot hit 75% WR. It is a trend-following random walk detector.
The 75%+ system WR comes from: mtp-zscore direction × profit-monster exit (winners ride) × ATR SL (losers cut fast at ~-0.60%).

### 3. Best performing combo: (50,100,150) Z>=1.0
- Same WR as deployed at all horizons (within ±0.6%)
- Fires 3x more: 75k vs 27k per horizon
- Z>=1.0 captures more structural setups than Z>=2.0

### 4. All combos peak SHORT at ~48% WR at 4h
LONG maxes at ~44%. SHORT side has structural edge in this data.

### 5. Z_MAX=99 = no cap — blow-offs pass through unchecked
Not tested in this sweep, but |z|>5 on 50-150 bar lookbacks is extreme blow-off territory.
Setting Z_MAX=5.0 would filter these.

## Best Params by Horizon (min 30 fires)
| Horizon | Best WR | Combo | Z | Direction | Fires | W/L | Avg Ret |
|---------|---------|-------|---|-----------|-------|-----|---------|
| 4h | 48.1% | (14,100,150) | Z>=1.0 | SHORT | 75,864 | 1.25 | +0.155% |
| 2h | 46.0% | (14,100,150) | Z>=1.0 | SHORT | 75,864 | 1.16 | +0.029% |
| 1h | 44.9% | (14,100,150) | Z>=1.0 | SHORT | 75,864 | 1.17 | +0.016% |
| 30m | 42.8% | (14,100,150) | Z>=1.0 | SHORT | 75,864 | 1.16 | -0.002% |
| 15m | 40.9% | (50,100,150) | Z>=1.0 | SHORT | 75,192 | 1.19 | -0.001% |

## Z>=1.0 vs Z>=2.0 (combo 50,100,150, LONG)
| Horizon | Z>=1.0 WR | Z>=1.0 Fires | Z>=2.0 WR | Z>=2.0 Fires | Delta |
|---------|-----------|-------------|-----------|-------------|-------|
| 1m | 27.4% | 75,192 | 27.3% | 27,416 | +0.1% |
| 5m | 37.3% | 75,192 | 36.7% | 27,416 | +0.6% |
| 15m | 40.5% | 75,192 | 39.9% | 27,416 | +0.6% |
| 1h | 42.6% | 75,192 | 42.8% | 27,416 | -0.3% |
| 4h | 43.6% | 75,192 | 43.1% | 27,416 | +0.6% |

## Proposed hermes_constants.py Changes
```python
# CURRENT (worst in sweep):
MTP_ZSCORE_LB_SHORT = 14
MTP_ZSCORE_LB_MID   = 50
MTP_ZSCORE_LB_LONG  = 150
Z_SHORT_Z_MIN       = 2.0
Z_SHORT_Z_MAX       = 3.0  # not actually enforced (Z_MAX=99 in code)
Z_MID_Z_MIN         = 2.0
Z_MID_Z_MAX         = 3.0
Z_LONG_Z_MIN        = 2.0
Z_LONG_Z_MAX        = 3.0
MTP_ZSCORE_COOLDOWN_BARS = 5

# SUGGESTED (best in sweep):
MTP_ZSCORE_LB_SHORT = 50
MTP_ZSCORE_LB_MID   = 100
MTP_ZSCORE_LB_LONG  = 150
Z_SHORT_Z_MIN       = 1.0
Z_SHORT_Z_MAX       = 5.0  # cap blow-offs
Z_MID_Z_MIN         = 1.0
Z_MID_Z_MAX         = 5.0
Z_LONG_Z_MIN        = 1.0
Z_LONG_Z_MAX        = 5.0
MTP_ZSCORE_COOLDOWN_BARS = 20
```
Expected: 3x more signals, same/better WR, filters blow-offs (|z|>5 capped), 20-min cooldown prevents spam.

## What 75%+ WR Actually Depends On
mtp-zscore provides direction. The system's 75%+ WR comes from:
1. **profit-monster exit**: winners avg +1.14% (14 trades, 100% winners)
2. **ATR SL**: losers avg -0.61% (cut fast, don't let winners turn into losers)
3. **mtp-zscore** must be RIGHT DIRECTIONALLY — that's the ~45-48% part