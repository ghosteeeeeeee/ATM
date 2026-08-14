# Plan: r2_trend_long Trailing SL Tuning

**Created:** 2026-08-14
**Status:** Research complete, implementation pending
**Token analyzed:** 2Z (7-hour wave, 2026-08-13 21:00 to 2026-08-14 03:00)

---

## Problem

r2_trend_long fires LONG entries on mature trends. Two losing trades (2Z -3.04%, CHIP -2.53%) entered late and got stopped out. Current trailing SL params are too tight — they exit winning trades too early.

## Wave Characteristics (2Z)

- **Entry zone:** $0.0488 (flat base, 21:00)
- **Peak:** $0.05155 (02:20)
- **Max move:** +5.63% over 7 hours
- **Largest pullback before peak:** 1.47% (Dip 1: $0.0494→$0.0488)
- **Max drawdown from any peak:** 1.88% (at 02:32, after peak)

## Pullback Episodes (sorted by depth)

| # | Peak Time | Peak$ | Depth | Duration |
|---|-----------|-------|-------|----------|
| 1 | 02:21 | $0.05155 | 1.88% | 37min |
| 2 | 22:44 | $0.04947 | 1.47% | 60min |
| 3 | 00:44 | $0.05040 | 1.23% | 5min |
| 4 | 00:22 | $0.04999 | 0.96% | 9min |
| 5 | 01:59 | $0.05112 | 0.72% | 2min |
| 6 | 21:17 | $0.04902 | 0.60% | 41min |
| 7 | 02:10 | $0.05137 | 0.49% | 4min |
| 8 | 21:05 | $0.04898 | 0.47% | 4min |

## Key Finding

**Trail distance must be > 1.88% to survive the entire wave.**

| Trail Distance | Result | Exit PnL |
|---------------|--------|----------|
| 0.8% (current) | Stopped at 22:52 | +0.54% |
| 1.0% | Stopped at 22:54 | +0.35% |
| 1.2% | Stopped at 23:04 | +0.13% |
| 1.5% | Stopped at 02:31 | +3.98% |
| 1.8% | Stopped at 02:32 | +3.64% |
| **2.0%** | **SURVIVED** | **+4.95%** |
| 2.5% | SURVIVED | +4.95% |
| 3.0% | SURVIVED | +4.95% |

## Current vs Recommended Params

| Parameter | Current | Recommended | Why |
|-----------|---------|-------------|-----|
| TRAILING_ACTIVATION_PCT | 0.40% | **0.80%** | Wait for trend to establish |
| TRAILING_DISTANCE_PCT | 0.80% | **2.00%** | Survives 1.88% max drawdown |
| ATR_SL_MAX (hard SL) | 2.50% | 2.50% | Already adequate |

## Root Cause of Losing Trades

| Trade | Entry Price | Peak Price | Room to Run | Problem |
|-------|-------------|------------|-------------|---------|
| 2Z winner | $0.0509 | $0.05155 | +1.3% | Entered late, captured +1.59% |
| 2Z loser | $0.05146 | $0.05155 | +0.2% | Entered at peak, no room |
| CHIP loser | $0.023144 | — | — | Stale + overextended |

**Trade 2 entered at the absolute peak.** No trailing SL can fix a peak entry. The accel filter added today (R2_TREND_LONG_MAX_ACCEL=0.005) should prevent future peak entries.

## Signal Entry Filters (added 2026-08-14)

1. **R2_TREND_LONG_MAX_ACCEL = 0.005** — blocks LONG when price is accelerating up (overextended)
2. **R2_TREND_LONG_BLOCK_STALE = True** — blocks stale tokens (fixed silent exception bug)

## Open Questions for Further Research

1. **Does trail=2.0% work on other tokens?** This analysis is 2Z-only. Need to test on more winners.
2. **What's the optimal activation %?** 0.8% waited for trend establishment. Test 0.5%-1.5% range.
3. **Does wider trail reduce win rate?** Wider trail = more trades held through drawdowns = some might reverse.
4. **ATR-based trail distance?** Should trail distance scale with ATR? Low-vol tokens need tighter trail.
5. **Entry timing fix:** The signal fires late in the wave. Can we detect "wave maturity" and skip?

## Files Changed (2026-08-14)

- `scripts/hermes_constants.py` — added R2_TREND_LONG_MAX_ACCEL = 0.005
- `scripts/signals/r2_trend_long.py` — accel filter, stale bug fix

## Data Source

- `signals_hermes.db` → `price_history` table (1m candles)
- `signals_hermes_runtime.db` → `signals` table (signal metadata)
