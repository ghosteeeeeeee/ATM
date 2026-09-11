## CEO Report — 2026-09-12 ~01:00 UTC (BTC Momentum Sync Decision)

### Diagnosis

**DB VERIFIED (my own queries):** 24h: 60T, 50.0% WR, -$1.45. 7d: 341T, 56.3% WR, +$0.80. cut-loser-CL-T1: 63T, 0% WR, -$9.56 (BIGGEST SINGLE DRAG). atr_sl_hit: 53T, avg -5.22%, -$8.76. BTC score NOT in trade metadata (0/341). RSI/z-score NOT populated (0/341). TREND_FILTER defined but NOT enforced in compactor. Regime almost all NEUTRAL (331/341).

**Independent verdict found:** Plan's numbers wrong (bleed is -$1.94 not -$1.42, BTC bearish 63% not 56%, transitions 806 not 514). Staleness diagnosis wrong — hard block removal is the issue, not the decay formula. BUT concept is sound: LONGs bleed when BTC is bearish.

### Decision: GO (MODIFIED)

**Rationale:** The tide mechanism (BTC 3h momentum + SHORT WR) already exists and is wired into scoring (signal_compactor.py:1240). It provides a 0.7x penalty / 1.2x boost — soft filter, not hard block. The plan's Layer 1 wants a harder gate. Layer 5 (continuum context boost) is already built, just needs wiring. The plan's Layer 2 (hard staleness) was removed intentionally on Sep 4 — respect that decision.

### Priority Order (REVISED)

| # | Change | Why | Effort |
|---|--------|-----|--------|
| 1 | **Wire Continuum Context Boost** (Layer 5) | Already built in continuum_context.py:276. Just call `get_trend_boost()` in signal_compactor scoring. Zero new code, just wiring. | 15 min |
| 2 | **Add BTC score/trend_bias to _signal_metadata** | PREREQUISITE for verifying Layer 1. Without this, we can't correlate BTC state with trade PnL. Store in signal_compactor when creating trades. | 30 min |
| 3 | **Investigate cut-loser-CL-T1** | 0% WR, -$9.56 across 63 trades. The plan doesn't address this but it's the BIGGEST drag. Need to understand WHY it fires at -5% avg. | 1 hour |
| 4 | **Enforce TREND_FILTER in compactor** | Already defined (TREND_FILTER_ENABLED=True) but only used in 4 signal detectors. Add as universal gate in _score_signal(). | 30 min |
| 5 | **Strengthen tide mechanism** | Current: 0.7x penalty (soft). Consider: hard block when BTC score <30 (STRONG_BEAR). Only after verifying Layer 5 impact. | 1 hour |
| 6 | **RSI/z-score recording** | Populate entry_rsi_14, signal_z_score at trade creation for future validation. | 30 min |
| 7 | **Transition Detection** (Layer 2) | Defer — 12.6min transitions need faster detection than plan's 30min window. Build after Layers 1-5 proven. | Future |

### What I'm NOT Doing

- **NOT restoring hard staleness block.** Removed Sep 4 intentionally. The verdict correctly identifies this as the root cause of stale trades, but the removal was deliberate — signals that survive hotset rounds should execute. The staleness_mult (0.1/min decay) already penalizes old signals in scoring. Adding BTC momentum staleness (score shift >15 → kill) is better than a hard time block.
- **NOT implementing Layer 4 (Transition Detection) now.** The plan's frequency data was wrong (806 transitions, not 514). Needs different approach — faster detection window, smaller delta threshold.
- **NOT touching protected flags.** PM_TRAIL, ATR_SL, LIVE_TRADING_ENABLED, CONFLUENCE_REQUIRED — all untouched.

### Concerns

1. **cut-loser-CL-T1 0% WR is the real emergency.** 63 trades, every single one a loss, -$9.56. This dwarfs the LONG bleed. Need to investigate whether the threshold is too tight or the mechanism is counterproductive.
2. **TREND_FILTER gap** is a free fix — defined but not enforced. Should have been caught earlier.
3. **No BTC score in metadata** means we're flying blind on correlation. This must be fixed before Layer 1 can be validated.

### Delegation

- [ ] DELEGATE to bug_hunter: Investigate cut-loser-CL-T1 — why does it fire at -5% avg? Is the threshold wrong? Query trades WHERE exit_reason='cut-loser-CL-T1' and analyze the pattern.
- [ ] DELEGATE to signal_analyst: Wire get_trend_boost() into signal_compactor.py scoring pipeline. Add BTC score/trend_bias to _signal_metadata INSERT. Add TREND_FILTER enforcement in _score_signal().

---

## CEO Report — 2026-09-11 ~18:24 UTC

### Diagnosis

24h: 52T, 48.1% WR, -$1.06. 7d: 330T, 56.4% WR, +$1.38 (VERIFIED POSITIVE). 48h: 95T, 57.9% WR, +$3.06 (STRONG). Sep 11: 46T, 45.7% WR, -$1.29. R:R 24h: 0.74 (avg_win 3.37%, avg_loss -4.53%). 4 open (all SHORT). Disk 83%.

**#1 loss driver: rr_engine_resistance** — 16 SHORT trades/24h, avg -2.09%, -$0.82 total. Structural — SHORT entries in 98% NEUTRAL market hitting resistance levels. Working as designed but biggest single drag.

**#2 loss driver: pump-chain+ LONG** — 10T/24h 30% WR, -$0.59. Still firing despite 30.8% WR over 7d (13T/7d -$0.29). Auto_1hr didn't kill (has wins, below threshold). **Should be killed.**

**#3 loss driver: pullback-entry- SHORT** — 8T/24h 37.5% WR, -$0.42. Bad day (7d is 69% WR +$1.93). Variance.

**#4 loss driver: atr_sl_hit** — 21T/24h, avg -0.64%, -$0.67. Normal SL exits.

**Profit source: profit-monster-trail** — 8T/24h, avg +3.58%, +$1.07. Only green exit type.

### Root Cause

Today's -$1.29 is structural rr_engine_resistance (-$0.82) + pump-chain+ bleed (-$0.59) + variance on pullback-entry- (-$0.42). However, 48h is +$3.06 and 7d is +$1.38 — system is structurally profitable. Today is a bad day, not a structural failure. R:R 0.74 means breakeven WR ~57%, actual 48.1% today.

### Fix Applied

**pump-chain+ LONG should be killed.** 13T/7d 30.8% WR -$0.29, 10T/24h 30% WR -$0.59. Not auto-killed because "has wins." This is the only actionable fix today. All other losses are structural (rr_engine) or variance (pullback-entry- bad day).

**No param changes.** PM_TRAIL/ATR_SL protected. Active signals all profitable on 7d.

### Verification

- DB verified: 24h 52T 48.1% WR -$1.06. 7d 330T 56.4% WR +$1.38. 48h 95T 57.9% WR +$3.06.
- All 5 active signals profitable 7d: pullback_entry- 29T/69%WR +$1.93 ★, open_skies 19T/63.2%WR +$1.56 ★, bb_bounce_v2_long 39T/71.8%WR +$1.20 ★, pump_chain 41T/68.3%WR +$1.11, pump-chain- 31T/64.5%WR +$0.61.
- pump-chain+ 13T/7d 30.8%WR -$0.29 — only non-legacy signal bleeding.
- 4 open: 3x pump-chain- SHORT, 1x mover- SHORT. Near breakeven.
- Disk: 83%.

### Next Actions

1. **Kill pump-chain+ LONG.** Set PUMP_FLOW_PLUS_ENABLED=False, add to NEVER_REENABLE_FLAGS. -$.59/24h bleeding removed.
2. **Monitor R:R.** 0.74 (breakeven 57%). System 7d WR 56.4% — nearly there.
3. **Legacy exits by Sep 12.** ema300_dip_short -$1.51, ema300_dip -$0.40, slow_grind -$0.80, sma20_dip -$0.73, coiled_spring -$0.65. Will age out.
4. **Monitor rr_engine_resistance.** Structural, but -$0.82/24h. If persistent, consider widening resistance threshold.
5. **Disk at 83%.** 2% from threshold.
