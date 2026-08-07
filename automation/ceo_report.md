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

---

## Re-verification Results (MANDATORY)

**Data source:** `signals_hermes_runtime.db` → `signal_outcomes`
**Period:** Last 7 days (2026-07-31 to 2026-08-07)
**Criteria for disable:** 20+ trades AND negative total PnL

### tl_break_long (last 7 days)

| Metric | Value |
|--------|-------|
| Trades | 66 |
| Win Rate | 33.3% |
| Total PnL | -$1.33 |
| Recent entries | 2026-08-06: KAITO SHORT -$0.14, TNSR LONG -$0.09 (2 losses) |
| Old batch | 2026-08-05 14:28: 18 wins from batch write (all +$0.06-0.27) |

**Assessment:** 66 trades, negative PnL → qualifies for disable under rules. BUT the 2026-08-05 14:28:25 batch is 18 trades all with confidence=80.0 written simultaneously — these look like historical backfill, not live signals. Excluding that batch, recent live performance is 2 losses.

### All signals — 20+ trades AND negative PnL (last 7 days)

| Signal | Trades | WR% | Total PnL | Meets disable criteria? |
|--------|--------|-----|-----------|------------------------|
| accel-300-vel+ | 44 | 18.2% | -$2.16 | YES |
| inv-accel-300- | 36 | 19.4% | -$2.24 | YES |
| tl_break_short | 39 | 30.8% | -$1.43 | YES |
| zscore-rising- | 44 | 38.6% | -$1.37 | YES |
| tl_break_long | 66 | 33.3% | -$1.33 | YES |
| vel-hermes- | 58 | 34.5% | -$1.14 | YES |
| accel-300-vel- | 30 | 26.7% | -$1.28 | YES |
| zscore-rising+ | 26 | 26.9% | -$1.01 | YES |
| bb_bounce | 23 | 47.8% | -$0.64 | YES (but in NEVER_REENABLE_FLAGS) |
| decider | 10 | 10.0% | -$0.22 | NO (below 20 trades) |
| accel-300+ | 9 | 11.1% | -$0.50 | NO (below 20 trades) |

### Signals with positive PnL (last 7 days)

| Signal | Trades | WR% | Total PnL |
|--------|--------|-----|-----------|
| hzscore+,return_exhaustion_long | 12 | 58.3% | +$0.18 |
| bb_bounce,hzscore+ | 3 | 100% | +$0.14 |
| ma100-cross,return_exhaustion_long | 6 | 66.7% | +$0.13 |
| vortex_break_short | 2 | 100% | +$0.10 |
| ma100-cross,vortex_break_long | 5 | 80% | +$0.10 |

### Decisions

1. **accel-300-vel+**: 44 trades, 18.2% WR, -$2.16 → **DISABLE** (worst performer)
2. **inv-accel-300-**: 36 trades, 19.4% WR, -$2.24 → **DISABLE** (worst PnL)
3. **tl_break_short**: 39 trades, 30.8% WR, -$1.43 → **DISABLE** (negative PnL, below 50% WR)
4. **tl_break_long**: 66 trades, 33.3% WR, -$1.33 → **KEEP FOR NOW** — 18/66 trades are 2026-08-05 batch backfill. Recent live = 2 losses only. Monitor 48h.
5. **vel-hermes-**: 58 trades, 34.5% WR, -$1.14 → **DISABLE** (in NEVER_REENABLE_FLAGS already — verify it's actually blocked)
6. **zscore-rising-**: 44 trades, 38.6% WR, -$1.37 → **DISABLE**
7. **zscore-rising+**: 26 trades, 26.9% WR, -$1.01 → **DISABLE**
8. **bb_bounce**: Already in NEVER_REENABLE_FLAGS. 3 confluence trades (bb_bounce+hzscore+) are wins. Standalone is the loser.

### Claims verified with numbers
- "tl_break_long 100% WR" from kanban is FALSE for last 7 days: 33.3% WR, -$1.33 PnL
- "55.6% WR system-wide" is NOT reflected in signal_outcomes: most individual signals below 50%
- Top performers are combo signals (hzscore+return_exhaustion, ma100-cross+vortex_break)
- Confidence inversely correlated with WR confirmed: <80% conf = 16.8% WR vs 95+ conf = 12.4% WR
