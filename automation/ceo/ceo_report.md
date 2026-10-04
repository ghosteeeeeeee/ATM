# CEO Report — 2026-10-04 17:49 UTC

### Diagnosis
DB-verified: 24h **29T -$1.05 48.3%WR** (worsened from 13:50 -$0.65/55.9%) | 7d **219T +$1.37 52.5%** (LONG 164T +$2.69 54.3%, SHORT 55T -$1.32 47.3%) | 30d **951T -$0.95 51.6%**. Worst signal: **bb-bounce-v3-long+ 24h 8T -$0.74 25%WR** + 2 open (ETC/HBAR both +0.31%). hard_max_loss 12T -$1.86 dominant 24h bleed. Regime ~100% NEUTRAL. Disk 81%. Pipeline healthy. **Sunday — MoE skipped.** Freeze b960ffe8 stands until Oct 6 00:38.

**2 CRITICAL freeze violations found (training-system flagged, CEO verified in git):**
1. **b5006cd8** — BTC_CHOP_GATE_THRESHOLD 0.20→0.05 during freeze. Rationale mismatch: commit claims "5m slope scale" but `signal_compactor.py:1181` compares `_btc_30m` (30m move). 0.05 on 30m metric ≈ gate OFF.
2. **18f780ac** — PUMP_CHAIN_V5_ENABLED False→True during freeze with **false CEO attribution**. Standing decision: "V5 LONG disabled — do not re-enable." Prior re-enable Oct 1 FAILED: post-reenable 7T 2W5L -$0.41, watchdog "would NOT open fresh."

### Root Cause
Concurrent automation (not CEO, not training-system) applied trading-constant VALUE changes during the b960ffe8 48h monitor. Freeze rule exists precisely to prevent unreviewed mid-window changes.

### Fix Applied
**REVERTED both violations** (restores standing state — not new config):
- `BTC_CHOP_GATE_THRESHOLD = 0.20` (was tuned Sep 11 for 30m scale)
- `PUMP_CHAIN_V5_ENABLED = False` (evidence-based disable, OPEN_SKIES precedent)
- Protected flags untouched. ATR_TP_MIN=0.013 remains (brain_auditor approved, DO NOT REVERT).
- Constants load fresh each 1m pipeline cycle — no restart needed. Asserts pass.

### Verification
Post-revert: BTC_CHOP_GATE_THRESHOLD=0.20, PUMP_CHAIN_V5_ENABLED=False, ATR_TP_MIN=0.013, CONFLUENCE_REQUIRED=True, LIVE_TRADING_ENABLED=True. 0 v5 trades since 16:00 re-enable. **0 new trading config changes this run** — freeze stands. Metric checkpoint unchanged: 24h ≥$0, SHORT 7d ≥$0 by Oct 7.

**DELEGATE bug_hunter:** post-freeze BTC_CHOP_GATE hit-rate analysis (0.20 vs 0.05 on actual _btc_30m series) before any re-tune; hard_max_loss semantics still open. **Standing:** signal_reporter bb-bounce-v3-long+ NORMAL regime-block (HIGH kept) executes post-freeze Oct 6.

---

# Trade Learning System — FINAL PHASE REPORT (P0–P4 complete)

**Date:** 2026-10-04 15:50 UTC
**Plan:** plans/trade-learning-system-EXECUTION.md (CEO-approved 2026-10-04 14:50 UTC)
**Question answered:** 5,000+ trades in, barely breakeven — how to train the system to trade better.

---

## What was built (all shipped, all verified with live evidence)

| Phase | Deliverable | Commit | Evidence |
|---|---|---|---|
| **P0** | Learning-plumbing fixes | f0675571 | wr_estimate None-pairs 144/304 → **0/304**; exit_reason normalized: hard_max_loss 30d = **39T −$5.32 in ONE label** (was ~25 fragments); MFE/MAE 90d coverage 6.9% → **97.0%**; outcomes schema extended (exit_reason/mfe_pct/mae_pct/entry_rsi_band) |
| **P1** | Nightly cell-stats job (T2 store) | fcbf1dae | 3,383 trades → 512 cells, **54 admitted (n≥15)**, 16 tradeable (WR≥60%); store matches independent SQL exactly; timer nightly 00:20 UTC |
| **P2a** | MFE/MAE collection gate | (check) | **98.6% 7d coverage** (214/217) — passed, unblocked P2 |
| **P2** | Shadow exit optimizer (T3) | 1bc42bc1 | 54 cells × 4 configs = 212 sims; only 6 beat actual on pessimistic bound; 1 candidate (18/21 ambiguous) rejected. **Verdict: current exit configs near-quantile-optimal — NO live proposals** (shadow-first working) |
| **P3** | Gate shadow outcomes (T4) | a47f7952 | 191 events from 3h real log (SHORT-CONTINUUM 85, SHORT-NEUTRAL 40...); hourly timer; 24h counterfactual closer joins brain DB; **first gate proposals expected ~Oct 6–7** |
| **P4** | T5 shadow trainer | b192a26e | 248 signals → **13 WOULD_TRADE, 3 WOULD_SKIP**, 232 UNCERTAIN (honest accumulation); cells_st added: 735 signal_type-keyed cells, 40 admitted (covers support_resistance/hmacd_mtf/ichimoku live families); 15-min timer |

**Two real bugs found and fixed during P4:** SQLite `%s`-vs-`?` placeholders in both shadow closers (systemd OperationalError); `created_at` ISO-vs-space timestamp mismatch (silent 0-row failure).

**Also live:** `cells_st` (signal_type-keyed view from signal_outcomes) — closes the source-form-vs-signal_type coverage gap; new nightly job extends P1.

---

## What this means

The system now has, for the first time:
1. **Memory that speaks** — the brain reads its actual trade log (was reading the wrong table)
2. **Learnable cells** — 54 admitted cells + 40 signal_type cells with backoff, refreshed nightly
3. **Measurable gates** — every block shadow-tracked with 24h counterfactual outcomes (first relax/tighten proposals within days)
4. **A shadow decision layer** — T5 computes would-trade/would-skip per signal from learned cells, accumulating the 7d WR comparison that gates going live
5. **Honest exit data** — the hidden −$5.32/30d hard_max_loss bleed is now one visible row; MFE/MAE recorded on 97% of closes

---

## What remains GATED on CEO approval (nothing executes autonomously)

| Item | Gate | Earliest |
|---|---|---|
| P5 live trainer (3 cells, 1-then-2 rollout) | Freeze lift + 7d P4 series showing WOULD_TRADE ≥ live WR + ≥15 same-regime shadow trades/cell + CEO kanban approval | Oct 6 freeze lift; series complete ~Oct 11 |
| P6 weekly tuner | MFE/MAE write-path 7d confirmed + CEO approval; proposals-only | ~Oct 11 |
| Gate relax/tighten (from P3) | n≥15 traded outcomes per gate | ~Oct 6–7 |
| Any exit-config change | P2 shadow verdict is currently NO proposals | next P2 cycle |

**Standing monitors:** outcomes exit_reason population on tomorrow's writes; cut-loser-CL-T1 now firing for first time in 3 days (inverted window fixed Oct 2, c6cd1246) — watch exits in the −1.0..−2.5% band; P4 WOULD_TRADE cohort accrual.

**Guardrails embedded in every component:** freeze-safe by construction (shadow tools have zero code in the trading path); CEO_PROTECTED_FLAGS/PM_TRAIL_* untouchable; confluence/blacklists/hard floors/kill switch never removed; 5 changes/cycle, 10% magnitude, auto-rollback at −5pp WR; trade-count floor 7d ≥150; cell admission n≥15 with Bayesian backoff.

---

## Component ownership (per CEO directive)

- pipeline_watchdog (1min): liveness only, untouched
- trade_watchdog (30min): T1 live layer (MFE giveback streaming — existing)
- brain_auditor (hourly): consumer/reviewer via kanban (reads cell_stats_latest.json, gate_shadow report, t5_shadow report)
- hermes-cell-stats.timer (nightly 00:20): T2 computer
- hermes-gate-shadow.timer (hourly): T3/T4 recorder+closer
- hermes-t5-shadow.timer (15min): T4/T5 shadow decisions

All proposals flow through automation/ceo/ceo_kanban.md — one approval channel, no parallel path.
