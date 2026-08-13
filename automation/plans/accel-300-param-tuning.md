# Accel-300- SHORT Param Tuning Plan

**Date:** 2026-08-13
**Status:** Ready for CEO review
**Signal:** accel-300- (SHORT only, LONG is dead)

---

## Problem

Two recent losers flagged by user:
- **NXPC SHORT**: Entry $0.1840, SL hit $0.1856 (0.87% loss). Price was grinding UP for 30min before entry.
- **ETC SHORT**: Entry $6.2110, SL hit $6.2457 (0.56% loss). Entry was below the entire 30min trading range — possible stale price feed.

Both hit ATR stop loss. The question: can param tweaks filter these out without hurting winners?

---

## Baseline Performance (actual trades)

| Metric | Value |
|--------|-------|
| Total trades | 93 |
| Win rate | 44.6% |
| Total P&L | -$0.12 |
| Avg win | +0.46% |
| Avg loss | -0.52% |

---

## Backtest Results (8-day, candles_1m, 47 tokens)

| Set | Params (slope/gap/persist) | Trades | WR% | TotPnL | vs Baseline |
|-----|---------------------------|--------|-----|--------|-------------|
| **baseline** | 0.0005 / 0.35 / 7 | 318 | 35.5% | +0.570% | — |
| **M_conservative** | 0.0015 / 0.40 / 9 | 273 | **37.0%** | +0.590% | **+1.5% WR, +0.02% PnL** |
| **F_slope_001** | 0.001 / 0.35 / 7 | 310 | 36.1% | **+0.620%** | **+0.6% WR, +0.05% PnL** |
| I_slope_0008 | 0.0008 / 0.35 / 7 | 313 | 35.8% | +0.590% | +0.3% WR, +0.02% PnL |
| J_persist8 | 0.001 / 0.35 / 8 | 368 | 35.1% | +0.620% | -0.4% WR, +0.05% PnL |
| H_combo | 0.001 / 0.40 / 9 | 384 | 34.4% | +0.570% | -1.1% WR, +0.00% PnL |
| K_gap_045 | 0.001 / 0.45 / 7 | 259 | 35.5% | +0.450% | +0.0% WR, -0.12% PnL |
| L_slopePersist | 0.001 / 0.40 / 8 | 337 | 33.8% | +0.430% | -1.7% WR, -0.14% PnL |

### Key Findings

1. **Slope is the highest-leverage param.** Moving from 0.0005→0.001 improves WR by +0.6% and PnL by +0.05%. Going to 0.0015 gives best WR (37.0%) but slightly lower PnL.

2. **Persistence 8-9 doesn't help.** More persistence = more trades (J_persist8: 368 vs baseline 318) but lower WR. The extra trades are lower quality.

3. **Gap threshold 0.45 is too aggressive.** K_gap_045 kills 59 trades but PnL drops by 0.12%. Over-filtering.

4. **Best overall: F_slope_001.** Single param change (slope 0.0005→0.001), best PnL (+0.62%), improved WR (36.1%). Minimal trade reduction (-8 trades).

5. **Best WR: M_conservative.** Slope 0.0015 + gap 0.40 + persist 9. 37.0% WR but +0.03% less PnL than F.

---

## Validation: Would param changes have caught NXPC/ETC losers?

**No — the backtest shows NXPC and ETC were winners across most param sets.**

- NXPC: 23 backtest signals, mostly wins (+0.02%)
- ETC: 3 backtest signals, 2 wins, 1 breakeven

This means the NXPC/ETC losers were likely caused by:
1. **Execution timing** — entry price didn't match signal price (slippage/stale feed)
2. **ATR SL too tight** — 0.87% and 0.56% SLs are below the 1.0% minimum, suggesting ATR was miscalculated or stale
3. **Market microstructure** — thin liquidity at entry time caused adverse fill

**Param changes won't fix execution issues.** The signal quality is fine — the problem is downstream.

---

## Recommendation

### Option A: Apply F_slope_001 (conservative)
Change `ACCEL_300_REGIME_SLOPE_PCT` from `0.0005` to `0.001`.

- Single param change
- Best PnL improvement (+0.05%)
- WR improvement (+0.6%)
- -8 trades (minimal reduction)
- Lowest risk

### Option B: Apply M_conservative (aggressive)
Change slope to `0.0015`, gap to `0.40`, persistence to `9`.

- Best WR (37.0%)
- -45 trades (more aggressive filtering)
- Slightly lower PnL than F

### Option C: Fix execution instead
The real issue may be ATR SL calculation, not signal quality. Investigate:
- Why SL landed at 0.87% and 0.56% (below 1.0% minimum)
- Whether entry price matches signal price
- Whether ATR values are stale/cached

---

## Next Steps

1. CEO review and decision
2. If approved, apply param change to `hermes_constants.py`
3. Monitor live results for 24h
4. If execution issues persist, investigate ATR SL calculation separately
