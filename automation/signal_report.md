# Signal Performance Report
**Generated:** 2026-08-06 19:00 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 8,929 | **WR:** 12.7% | **PnL:** -6,814.84%
- **Date range:** 2026-03-11 → 2026-08-06

---

## WINNERS (WR > 55%, PnL > 0, 5+ trades)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce,hzscore+ | LONG | — | — | — | 3 | 100.0% | +1.27 | ENABLED |
| hzscore+,return_exhaustion_long | LONG | 2 | 0.0% | -0.48 | 7 | 57.1% | +0.86 | ENABLED |
| ma100-cross,vortex_break_long | LONG | — | — | — | 5 | 80.0% | +0.82 | ENABLED |
| ma100-cross,return_exhaustion_long | LONG | 2 | 100.0% | +1.14 | 5 | 60.0% | +0.74 | ENABLED |
| return_exhaustion-,vortex_break_short | SHORT | — | — | — | 3 | 66.7% | -0.11 | ENABLED |
| hzscore-,return_exhaustion- | SHORT | 4 | 50.0% | -1.02 | 8 | 62.5% | -0.63 | ENABLED |

**Verdict:** All winners are enabled. Keep.

---

## LOSERS (WR < 30%, PnL < -2%, 5+ trades — ALL TIME)

| Signal | Dir | Trades | WR | Total PnL | Avg PnL | Status | Rec |
|--------|-----|--------|----|-----------|---------|--------|-----|
| accel-300-,rs-s-broken | SHORT | 1072 | 3.8% | -1200.10 | -1.120 | DISABLED | **DISABLE** (already off) |
| inv-accel-300- | SHORT | 186 | 17.2% | -101.90 | -0.548 | DISABLED | **DISABLE** (already off) |
| accel-300+,rs-r-broken | LONG | 66 | 0.0% | -92.54 | -1.402 | DISABLED | **DISABLE** (already off) |
| inv-accel-300+ | LONG | 151 | 14.6% | -83.87 | -0.555 | DISABLED | **DISABLE** (already off) |
| accel-300+ | LONG | 160 | 15.0% | -79.85 | -0.499 | DISABLED | **DISABLE** (already off) |
| gap-300+,zscore-momentum+ | LONG | 128 | 18.0% | -71.49 | -0.558 | DISABLED | **DISABLE** (already off) |
| tl_break_long | LONG | 140 | 19.3% | -70.23 | -0.502 | ENABLED | **DISABLE** |
| tl_break_short | SHORT | 131 | 22.1% | -62.18 | -0.475 | ENABLED | **DISABLE** |
| gap-300- | LONG | 132 | 19.7% | -60.21 | -0.456 | DISABLED | **DISABLE** (already off) |
| gap-300-,zscore-momentum- | SHORT | 118 | 17.8% | -59.09 | -0.501 | DISABLED | **DISABLE** (already off) |
| hzscore+,pct-hermes- | SHORT | 112 | 16.1% | -55.08 | -0.492 | ENABLED | **DISABLE** |
| hzscore- | LONG | 76 | 15.8% | -53.50 | -0.704 | ENABLED | **DISABLE** |
| gap-300+,pct-hermes+ | LONG | 80 | 13.8% | -51.86 | -0.648 | DISABLED | **DISABLE** (already off) |
| hzscore+,pct-hermes-,vel-hermes- | SHORT | 64 | 17.2% | -34.05 | -0.532 | ENABLED | **DISABLE** |
| pct-hermes+ | LONG | 64 | 14.1% | -33.83 | -0.529 | ENABLED | **DISABLE** |
| accel-300- | SHORT | 72 | 18.1% | -30.24 | -0.420 | DISABLED | **DISABLE** (already off) |
| gap-300+,ma-cross-5m+ | LONG | 32 | 3.1% | -27.10 | -0.847 | DISABLED | **DISABLE** (already off) |
| gap-300-,oc-zscore-v9- | SHORT | 50 | 14.0% | -26.73 | -0.535 | DISABLED | **DISABLE** (already off) |
| tl_break_short | LONG | 55 | 23.6% | -26.22 | -0.477 | ENABLED | **DISABLE** |
| accel-300+,rs-s72 | LONG | 30 | 6.7% | -25.61 | -0.854 | DISABLED | **DISABLE** (already off) |

---

## MARGINAL (WR 30-50%, mixed signals)

| Signal | Dir | Trades | WR | PnL | Status | Note |
|--------|-----|--------|----|-----|--------|------|
| accel-300+,rs-s44 | LONG | 20 | 35.0% | +50.97 | DISABLED | Profitable but low WR |
| accel-300+,rs-s32 | LONG | 14 | 21.4% | +0.02 | DISABLED | Break-even |
| hl_reconcile | LONG | 16 | 37.5% | -0.76 | DISABLED | Negligible |
| decider | LONG | 13 | 30.8% | -2.28 | DISABLED | Loser |
| trend_purity+ | LONG | 16 | 25.0% | -4.02 | ENABLED | **DISABLE** |
| accel-300-vel- | LONG | 20 | 40.0% | -5.29 | DISABLED | Loser |
| accel-300+,trend_purity+ | LONG | 20 | 40.0% | -5.61 | ENABLED | **DISABLE** |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found in the high-volume category. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## CRITICAL FINDINGS

### 1. Enabled signals hemorrhaging money

These are **still enabled** but are the worst performers by PnL:

| Signal | Trades | WR | PnL | Action |
|--------|--------|----|-----|--------|
| tl_break_long | 140 | 19.3% | -70.23 | **DISABLE** |
| tl_break_short | SHORT 131 | 22.1% | -62.18 | **DISABLE** |
| hzscore+,pct-hermes- | SHORT 112 | 16.1% | -55.08 | **DISABLE** |
| hzscore- | LONG 76 | 15.8% | -53.50 | **DISABLE** |
| hzscore+,pct-hermes-,vel-hermes- | SHORT 64 | 17.2% | -34.05 | **DISABLE** |
| pct-hermes+ | LONG 64 | 14.1% | -33.83 | **DISABLE** |
| tl_break_short | LONG 55 | 23.6% | -26.22 | **DISABLE** |
| trend_purity+ | LONG 16 | 25.0% | -4.02 | **DISABLE** |
| accel-300+,trend_purity+ | LONG 20 | 40.0% | -5.61 | **DISABLE** |

**Total bleeding from these enabled losers: -341.73% PnL across 678 trades.**

### 2. TL_BREAK is the biggest live offender

`tl_break_long` (140 trades, 19.3% WR, -70.23 PnL) and `tl_break_short` (131 trades, 22.1% WR, -62.18 PnL) — both enabled, both catastrophic. Combined: -132.41 PnL.

### 3. hzscore+/pct-hermes combinations are money pits

`hzscore+,pct-hermes-` SHORT (112 trades, 16.1% WR, -55.08), `hzscore+,pct-hermes-,vel-hermes-` SHORT (64 trades, 17.2% WR, -34.05), and `pct-hermes+` LONG (64 trades, 14.1% WR, -33.83) — all enabled, all losers. Combined: -123.26 PnL.

### 4. Winners are low-volume

The best performers have tiny sample sizes (2-7 trades). Too early to boost, but worth monitoring.

---

## RECOMMENDATIONS

1. **[DISABLE] TL_BREAK_ENABLED** — Both long/short variants losing badly (combined -132 PnL). 19-22% WR over 271 trades. No sign of improvement.
2. **[DISABLE] hzscore+,pct-hermes- SHORT** — 16.1% WR, -55 PnL over 112 trades.
3. **[DISABLE] hzscore+ short variant with vel-hermes-** — 17.2% WR, -34 PnL over 64 trades.
4. **[DISABLE] pct-hermes+ LONG** — 14.1% WR, -33.83 PnL over 64 trades.
5. **[DISABLE] hzscore- LONG** — 15.8% WR, -53.50 PnL over 76 trades.
6. **[DISABLE] trend_purity+ LONG** — 25% WR, -4 PnL over 16 trades.
7. **[DISABLE] accel-300+,trend_purity+ LONG** — 40% WR but -5.61 PnL over 20 trades.
8. **[WATCH] ma100-cross + return_exhaustion combinations** — Showing promise (60-100% WR) but sample size too small (2-5 trades).
9. **[WATCH] bb_bounce,hzscore+ LONG** — 100% WR over 3 trades. Needs more data before boosting.

**Immediate action:** Disable the 7 signals listed above. This should stop ~341 PnL bleeding per measurement period.

---

*Report auto-generated. Next report: ~6h from now.*
