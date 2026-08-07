# Signal Performance Report
**Generated:** 2026-08-07 09:00 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 8,929 | **WR:** 12.7% | **PnL:** -6,814.84%
- **Date range:** 2026-03-11 → 2026-08-07

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce,hzscore+ | LONG | — | — | — | 3 | 100.0% | +1.27 | ENABLED |
| ma100-cross,return_exhaustion_long | LONG | 1 | 100.0% | +0.39 | 6 | 66.7% | +1.13 | ENABLED |
| ma100-cross,vortex_break_long | LONG | — | — | — | 5 | 80.0% | +0.82 | ENABLED |
| hzscore+,return_exhaustion_long | LONG | 4 | 50.0% | +0.02 | 11 | 54.5% | +0.88 | ENABLED |
| hzscore+,ma100-cross | LONG | 1 | 0.0% | -0.38 | 3 | 66.7% | +0.44 | ENABLED |
| return_exhaustion-,vortex_break_short | SHORT | — | — | — | 3 | 66.7% | -0.11 | ENABLED |
| ma100-cross,range_finder | SHORT | 1 | 100.0% | +0.37 | 2 | 100.0% | +0.80 | ENABLED |
| vortex_break_short | SHORT | — | — | — | 2 | 100.0% | +0.89 | ENABLED |

**Verdict:** All winners are enabled. Keep. LONG side dominates — 6 of 8 winning combos are LONG.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| ma100-cross,return_exhaustion- | SHORT | 2 | 50.0% | -0.72 | 6 | 33.3% | -3.03 | ENABLED | **DISABLE** |
| hzscore-,return_exhaustion- | SHORT | 2 | 0.0% | -1.23 | 10 | 50.0% | -1.86 | ENABLED | **WATCH** |

### Long-term losers (still enabled, historical bleeding):

| Signal | Trades | WR | Total PnL | Status | Rec |
|--------|--------|----|-----------|--------|-----|
| tl_break_long | 140 | 19.3% | -70.23 | ENABLED | **DISABLE** |
| tl_break_short | 131 | 22.1% | -62.18 | ENABLED | **DISABLE** |
| hzscore+,pct-hermes- | 112 | 16.1% | -55.08 | ENABLED | **DISABLE** |
| hzscore- | 76 | 15.8% | -53.50 | ENABLED | **DISABLE** |
| hzscore+,pct-hermes-,vel-hermes- | 64 | 17.2% | -34.05 | ENABLED | **DISABLE** |
| pct-hermes+ | 64 | 14.1% | -33.83 | ENABLED | **DISABLE** |
| tl_break_short (LONG dir) | 55 | 23.6% | -26.22 | ENABLED | **DISABLE** |
| trend_purity+ | 16 | 25.0% | -4.02 | ENABLED | **DISABLE** |
| accel-300+,trend_purity+ | 20 | 40.0% | -5.61 | ENABLED | **DISABLE** |

**Total bleeding from enabled losers: -344.72% PnL across 678 trades.**

---

## MARGINAL (30-50% WR, small sample)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| return_exhaustion- | SHORT | 4 | 50.0% | -0.91 | ENABLED | Needs more data |
| hzscore-,return_exhaustion- | SHORT | 10 | 50.0% | -1.86 | ENABLED | Borderline — close to loser threshold |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] ma100-cross,return_exhaustion- SHORT** — New 24h loser: 33.3% WR, -3.03 PnL over 6 trades. Clear signal.
2. **[DISABLE] TL_BREAK_ENABLED** — Both long/short variants hemorrhaging (-132 PnL combined). 19-22% WR over 271 trades.
3. **[DISABLE] hzscore+,pct-hermes- SHORT** — 16.1% WR, -55 PnL over 112 trades.
4. **[DISABLE] pct-hermes+ LONG** — 14.1% WR, -33.83 PnL over 64 trades.
5. **[DISABLE] hzscore- LONG** — 15.8% WR, -53.50 PnL over 76 trades.
6. **[DISABLE] hzscore+,pct-hermes-,vel-hermes- SHORT** — 17.2% WR, -34 PnL over 64 trades.
7. **[DISABLE] trend_purity+ LONG** — 25% WR, -4 PnL over 16 trades.
8. **[DISABLE] accel-300+,trend_purity+ LONG** — 40% WR but -5.61 PnL over 20 trades.
9. **[WATCH] hzscore-,return_exhaustion- SHORT** — 50% WR, -1.86 PnL over 10 trades. Borderline. Monitor next cycle.
10. **[KEEP] All 8 winning combos** — LONG side dominant. bb_bounce,hzscore+ (100% WR, 3T) and ma100-cross combos performing well.

**Immediate action:** Disable ma100-cross,return_exhaustion- SHORT (new finding) + the 7 historical losers. Total estimated PnL recovery: ~345%.

---

*Report auto-generated. Next report: ~6h from now.*
