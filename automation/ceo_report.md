# CEO Report — Golden Setup Discovery

**Date:** 2026-08-07
**Data:** signal_outcomes (runtime DB)

---

## Top 10 Golden Setups

| # | Combo | Trades | WR% | Total PnL |
|---|-------|--------|-----|-----------|
| 1 | ma100-cross,vortex_break_long | 5 | 80.0 | +0.10 |
| 2 | ma100-cross,return_exhaustion_long | 6 | 66.7 | +0.13 |
| 3 | hwave+,hzscore- | 5 | 60.0 | -0.62 |
| 4 | hzscore+,return_exhaustion_long | 11 | 54.5 | +0.11 |
| 5 | hl_reconcile | 51 | 51.0 | -2.06 |
| 6 | pct-hermes+,zscore-long | 6 | 50.0 | +0.25 |
| 7 | hzscore-,return_exhaustion- | 10 | 50.0 | -0.18 |
| 8 | rs-r84,zscore-pump- | 6 | 50.0 | -0.14 |
| 9 | gap-300+,pct-hermes+,zscore-momentum+ | 6 | 50.0 | -0.77 |
| 10 | bb_bounce | 23 | 47.8 | -0.64 |

---

## Key Discoveries

### Signal Combos — What Works
- **ma100-cross + reversal signals** = highest WR. 80% and 66.7% WR with positive PnL.
- **return_exhaustion_long** appears in 3 top-10 combos — it's the best reversal filter.
- **hzscore pairings** (hzscore+, hwave+) show edge when combined with exhaustion signals.

### Tokens — Best Performers
- MNT: 41.7% WR (12 trades, -0.05 PnL) — cleanest performer
- PROMPT: 40% WR (25 trades, -1.19 PnL) — volume + decent edge
- REZ: 40% WR (10 trades, -1.05 PnL) — next best

### Hours — When to Trade
- **Hour 14 UTC: 20.6% WR** — dominant. 603 trades, 124 wins.
- Hour 12 UTC: 15.3% WR — second best.
- Hours 9-14 UTC cluster is the golden window.
- Hour 24 (end of day): worst at 10.6%.

### Confidence — Lower = Better (Inverted!)
- <80% conf: **16.8% WR** — best bucket by far
- 80-84% conf: 16.3% WR — nearly as good
- 95+ conf: 12.4% WR — worst, yet most trades (4717)
- **Confidence is inversely correlated with WR.** High-confidence signals are overfitted.

---

## CEO Decisions

1. **Filter for ma100-cross + (vortex_break_long OR return_exhaustion_long)** — strongest combo
2. **Prioritize hour 14 UTC window** — or at least don't ignore it
3. **Question the confidence gate** — high confidence ≠ high WR. Review confidence scoring logic
4. **MNT, PROMPT, REZ** — consider weight allocation to best tokens
5. **Investigate return_exhaustion_long** — it's in 3 winning combos, likely a strong filter

---

## Next Steps
- Run signal_analyst to validate combo robustness (sample size concerns for top combos)
- Review confidence scoring algorithm in signal pipeline
- Consider time-based filter for hour 14 UTC window

---

## Acknowledgment — CRITICAL: Phantom Trade Bug (2026-08-07)

**Status:** Debug deployed, awaiting production data.

Two phantom trade patterns identified:
1. **TIGHT SL PHANTOM:** SL set at entry (0.004% instead of 1.0%), instant stop-out. LINK #13352: entry=8.2416, SL=8.2419, stopped in 55s.
2. **GHOST PHANTOM:** Position on HL, zero records in brain DB.

Root cause unknown. `compute_atr_sl_tp()` returns correct SL in simulation (8.159828) but production writes near-entry value (8.241900). Something diverges between sim and prod paths.

**Debug instrumentation live:** `[TPSL-IN]`, `[TPSL-ANCHOR]`, `[TPSL-DEBUG]`, `[PHANTOM-DBG]`, `[PHANTOM-WRITE]`. Auto-triggers for any token with SL < 0.15% from entry.

**Impact:** Capital waste, reconciliation failures, false loss pollution in win rate data.

Next `position_manager` run will capture exact values. Priority: trace prod path divergence from simulation.
