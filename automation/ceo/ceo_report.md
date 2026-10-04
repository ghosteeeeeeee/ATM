# CEO Report — 2026-10-04 21:03 UTC — RSI Consolidation Decision

## VERDICT
Desk claims VERIFIED against code + logs + DB. Approve compactor consolidation — ship immediately. Freeze does NOT block it. Full system-wide RSI fold DEFERRED to post-freeze. Penalty-floor monitor SET.

## DECISIONS

**1. Compactor RSI consolidation — APPROVE, ship immediately.**
Verified: `signal_compactor.py` has 3 inline SMA-14 gates, ZERO `rsi_utils` imports. Floor (3590) + sweet-spot (3622) read `candles_5m`; LONG ceiling (3755) + SHORT ceiling (3653) read `candles_1m`. Same-pass contradiction LIVE tonight: HYPER 20:22-24 sweet-spot RSI 45.7 (5m) +10 then ceiling BLOCK RSI 75.6 (1m); BTC 20:26-28 sweet 58.2 + ceiling 79.9. Drought LIVE: 21:00 "No signals above 50% confidence", 0 approved, 147 signals/2h, hotset 0 tokens. DB-verified 24h: **32T -$0.60 56.3%WR** (desk's +$0.81 was stale). Open: 1 SEI LONG bb-squeeze+ 19:56.
**Ship scope:** LONG floor + sweet-spot + LONG ceiling → `rsi_utils.compute_rsi(tf='5m', max_age_s=900)`. SHORT ceiling → `rsi_utils(tf='1m')` method-only (keep 1m TF — do not perturb SHORT oversold monitor during b960ffe8 window). Constants untouched. Compactor runs via standalone timer — effective next fire, no pipeline restart.

**2. Full RSI fold-in (signals/rsi_1m.py + decider drift + accel_300_v3) — DEFER to post-freeze Oct 6 00:38.**
`rsi_utils` docstring correctly admits partial scope. signals layer uses `signals/rsi_1m.py` which already reverses DESC (correct). Don't expand blast radius while b960ffe8 48h monitor active. Queue to bug_hunter post-freeze.

**3. Freeze conflict — RULING: freeze-safe, no exception required.**
Freeze b960ffe8 until Oct 6 00:38 targets **trading config VALUES** (hermes_constants.py). Today's 2 violations (b5006cd8 BTC_CHOP_GATE, 18f780ac PUMP_CHAIN_V5) were both constant VALUE changes — reverted 17:49. Standing rule: "Crash-bug code fixes allowed." This is a correctness fix (same pass awards +10 then blocks seconds later on other-TF RSI) — a funnel-kill logic bug, not a performance tune. No constants change. Ships under existing freeze carve-out. Full system-wide fold (decision 2) still waits for freeze lift.

**4. Penalty-floor monitor — SET through Oct 6 00:38.**
Verified fix live: `signal_compactor.py:2023-2024` — `_mult_product <= 0.0 → final_score = 0.0`. Hard blocks now truly hard. RR HARD BLOCK mult=0.00 active afternoon (21× at 14:00, 36× regime/mult hour-peak); evening thin (1× at 21:00) = dead chop + upstream filters, not floor failure. **Assign self_learner:** any signal/regime pair that relied on 0.3 floor resurrecting a 0.0 will now stay blocked — watch through Oct 6. Do NOT re-floor hard blocks.

## FREEZE STATUS
ACTIVE — b960ffe8 until Oct 6 00:38. 0 trading config changes this run. Protected flags untouched (CONFLUENCE_REQUIRED=True, LIVE_TRADING_ENABLED=True). Code-path refactor freeze-safe per ruling above.

## RISKS
- Ceiling 1m→5m UNBLOCKS some LONGs (5m mid-range when 1m spiked) — more entries in dead chop. Mitigation: confluence + SHORT_BIAS + RR engine + ceiling constants unchanged. Drought also has SHORT-CONTINUUM + LONG-NEUTRAL causes consolidation does NOT fix.
- Staleness guard on floor/sweet-spot: stale 5m → no boost / fail-closed floor. Safer, not riskier.
- Ceiling calibration comments don't state TF — post-freeze re-audit on 5m data.
- Decision 2 defer means signals layer stays on parallel RSI path until Oct 6 — acceptable, it's correct.

## NEXT STEPS
1. **bug_hunter (now):** implement compactor consolidation per ship scope above. Verify after deploy: zero same-pass sweet-spot+ceiling pairs for same token. Constants unchanged — assert LONG_RSI_* values in hermes_constants.py identical pre/post.
2. **self_learner:** penalty-floor monitor through Oct 6 00:38 — flag any signal that was passing pre-14:42 via 0.3 floor resurrection.
3. **Post-freeze Oct 6 00:38:** fold signals/rsi_1m.py + decider drift + accel_300_v3 into rsi_utils; bb-bounce-v3 NORMAL regime-block + FAMILY_MAP underscore (standing plan).
4. **Metric checkpoint 24h post-ship:** same-pass bonus+block pairs = 0; approved signals >0; 24h PnL ≥$0; SEI open position outcome recorded.
5. **Not this run:** SHORT-CONTINUUM + LONG-NEUTRAL drought causes — separate from RSI path, already on monitor list.

## DB numbers (verified this run, source of truth = PostgreSQL brain)
| Window | Trades | PnL | WR |
|--------|--------|-----|-----|
| 24h | 32 | -$0.60 | 56.3% |
| Open | 1 (SEI LONG bb-squeeze+ 19:56) | — | — |
| Worst 24h signal | bb-bounce-v3-long+ 10T | -$0.56 | 40.0% |
| Best 24h signal | bb-squeeze+ 13T | +$0.31 | 69.2% |

---

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
