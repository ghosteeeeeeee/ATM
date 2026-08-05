# SHORT-Bias Diagnosis — rs.py Signal Asymmetry (2026-06-03)

## Core Finding

The SHORT-bias in Hermes signal generation is **NOT a bug in rs.py direction logic**. The code is symmetric. The asymmetry is market-driven + signal-source composition.

## Archive Data (921 trades, 2026-05-11 to 2026-06-03)

```
SHORTs:  394 trades, 49.0% WR, +2646% total pnl
LONGS:   527 trades, 30.6% WR, -1855% total pnl

co-signal SHORT: 364 trades, 166W/198L, avg_pnl=+0.672%
co-signal LONG:  476 trades, 152W/324L, avg_pnl=+0.291%
solo SHORT:       30 trades,  27W/3L,  avg_pnl=+80.065%   ← outliers, likely intraday special handling
solo LONG:       51 trades,   9W/42L, avg_pnl=-39.095%   ← outlier distribution, not representative
```

## Signal-Source Breakdown

| Signal Type | Direction | Trades | Win Rate | Observation |
|---|---|---|---|---|
| accel-300+ | LONG | 398 | 30% | Fires on upward momentum spikes that reverse in downtrend |
| accel-300- | SHORT | 170 | 34% | Fires on downtrend continuation — more aligned |
| zscore-pump+ | LONG | 20 | **0%** | 0 winners, every LONG lost |
| zscore-pump- | SHORT | 24 | **100%** | 24 winners, 0 losses |
| rs-r | SHORT | ~50% WR | | Correctly shorts resistance in downtrend |
| rs-s | LONG | ~50% WR | | Fires bounces but market keeps dropping |

## Root Causes

1. **accel-300+ LONG fires into counter-trend moves**: In a downtrend, upward momentum spikes are reversals, not continuations. accel-300+ captures the spike, but price reverts down.
2. **zscore-pump+ mean-reversion fires too early**: Price is below the mean — signal fires for LONG. But the mean keeps re-pricing lower as the downtrend continues. Every zscore-pump+ LONG lost.
3. **LONG_BIAS regime never fires**: LONG_BIAS requires slope_pct > 0.35%. regime_5m.json shows 0 tokens in LONG_BIAS across 98 scanned. The regime filter that should suppress LONGs in downtrends never activates.
4. **Broken supports accumulate in downtrends**: rs-s-broken SHORT fires when support is breached and price is below it (broken support = resistance). In a downtrend, broken supports accumulate → more SHORTs fire naturally.
5. **Solo signal extremes are misleading**: solo SHORT avg_pnl=+80% and solo LONG avg_pnl=-39% reflect selection bias (trades that become "solo" are non-standard outcomes), not a true strategy comparison.

## rs.py Code Verified Clean

- Bounce confirmation (lines 229-251): symmetric at 0.025% for both LONG and SHORT
- Confidence scoring (lines 380-414): bounce bonus +5 symmetric, no directional bias
- Regime logic (lines 516-540): symmetric, but LONG_BIAS never fires
- Patch 1 (support path, lines 553-563): reclassify moved outside `if broken:` — live
- Patch 2 (resistance path, lines 616-626): reclassify moved outside `if broken:` — live
- ai-engineer audit: 6/6 checks passed, no new bugs

## Pending Data Gap

- 0/41 pending LONGs have price>0 in signals.json
- 28/64 pending SHORTs have price>0
- signals.json was not capturing price data at signal detection time for LONG signals — data pipeline issue separate from rs.py

## Fixes Already Applied

1. Patch 1+2: rs-s-broken / rs-r-broken reclassify patches — broken-level fallthrough now works correctly
2. Patch to signal_compactor.py `_signal_type_key`: rs-s-broken correctly keyed as SHORT (was being treated as LONG)

## Remaining Issues (Not Fixed)

1. **accel-300+ LONG fires independently of RS structure**: momentum generator fires LONG regardless of whether valid support exists. In a downtrend, this creates systematic anti-regime entries.
2. **zscore-pump+ LONG 0% WR**: mean-reversion LONG in sustained downtrend is structurally misaligned. Requires regime confirmation or pump threshold increase.
3. **LONG_BIAS threshold too high**: 0.35% slope_pct never met. Lowering to 0.15-0.20% would allow LONG_BIAS to fire in mild uptrends and suppress LONG signals when market is clearly downtrending.
4. **Pending LONG signals price=0**: data capture bug separate from rs.py — signals not recording price at detection time.

## What Is NOT the Problem

- rs.py bounce confirmation asymmetry: **ruled out** — symmetric at 0.025%
- rs.py confidence scoring directional bias: **ruled out** — symmetric
- rs.py regime logic suppressing SHORTs: **ruled out** — regime is symmetric but LONG_BIAS never fires
- Directional miscategorization in rs.py: **ruled out** — patches applied, code clean
- Losing SHORTs being miscategorized LONGs: **ruled out** — losing SHORTs are correctly timed SHORTs that didn't work out; the underlying signal was correct for the regime