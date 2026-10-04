# CEO Report — 2026-10-04 — Plan Review: Trade Learning System

## VERDICT

**APPROVE P0 with corrections. APPROVE architecture in principle. MODIFY decisions 2–5. DO NOT adopt plan's numbers or T3 timeline as written.** Plan's diagnosis is directionally right (brain learns at wrong granularity, gates unlearnable, exits static) but three evidence claims are wrong and two component recommendations collide with reality on this box. Auditor/watchdog are NOT redundant — assign them ownership, don't replace them.

## EVIDENCE CHECKS

| Claim | Verdict | Verified fact |
|---|---|---|
| wr_estimate None for recorded pair | **CONFIRMED but root cause WRONG** | None returned for SUSHI/doji-bottom-long AND SUSHI/bb-squeeze+. trade_log HAS both pairs. `wr_estimate()` reads synapse/concept network via `recall(token,k=50)`; `decay ed_wr_estimate()` reads trade_log directly and returns numbers. 144/304 pairs with n≥3 return None from wr_estimate. **One-line fix, not schema fix.** |
| Cell census 10/31/40/78/493 → 81 cells n≥10 | **DISPROVED** | Live 90d signal×regime×direction: **18/24/30/51/302 → 72 cells n≥10** (15 at WR≥60%, 28 profitable, 23 at WR≥55%). Plan overcounted both ends. Thesis survives; success metric must be restated ≥60, not 81. |
| Exit-path 30d table | **CONFIRMED** | pm-trail 292T 81.2% +$17.69; atr_sl_hit 355T 46.5% −$3.90; CL-T1 83T 0% −$11.73. CL-T1 all pre-fix (c6cd1246 Oct 2, dead since Sep 29) — **0 valid CL-T1 trades in 30d window**. |
| signal_outcomes 2,842 rows w/ regime+thesis_mfe | **HALF-TRUE** | Rows=2,842 ✓ regime=2,776 (98%) ✓ **thesis_mfe=56 (2%) — effectively empty**. DB at `data/signals_hermes_runtime.db` (AGENTS.md path stale). Live writes partial (18 closed-today vs ~34 portfolio; 163/7d vs 217 brain). decider_run already queries it for 24h WR — table is load-bearing. |
| "5k MFE/MAE pairs for T3 calibration" | **DISPROVED** | Brain 90d: 3,384 closed, **only 233 have mfe_pct/mae_pct (6.9%)**. 30d: 118/946. T3 quantile calibration cannot run on 5k pairs — ~233 is the real corpus. |

**Findings the plan missed:**
1. **hard_max_loss family = 39T 0%WR −$5.32/30d** — fragmented across ~25 exit_reason labels (`hard_max_loss_-1.04%` etc.). Plan's exit table never aggregated it. Second-biggest bleed after dead CL-T1; dominates current 24h flip negative. **Normalize exit_reason families before any T2/T3 stats run.**
2. **trail_sl / atr_trail_hit** just landed (Oct 1–3): 3T +$0.45 / 8T +$1.58, both 100%WR, separate labels from profit-monster-trail. Learner sees 3 trail labels; T3 would miscalibrate unless grouped.
3. **b960ffe8 48h trading-config freeze live until Oct 6 00:38.** P0 is non-trading code/schema — safe. P1–P6 live changes wait.
4. **T3 candidate grid collides with CEO_PROTECTED `PM_TRAIL_ACTIVATE_PCT=0.40` / `PM_TRAIL_DISTANCE_PCT=0.20`.** Plan proposes tuning "trail activation 0.3/0.4/0.6%" — that IS the protected constant. Search space must be bounded by protected values or T3 violates the hard rule.

## AUDITOR-WATCHDOG RECOMMENDATION (T directive)

**Do not build parallel infrastructure. Do not overload existing components. Assign ownership:**

| Component | Cadence | Owns (repurpose/add) | Does NOT own |
|---|---|---|---|
| `pipeline_watchdog.py` (hermes-watchdog.timer) | 1min | **Unchanged** — liveness only: heartbeat, signal rate, trade recency, crashes, syntax, DB-leak. Verified: zero trade context today. | Outcomes, MFE/MAE, gates |
| `trade_watchdog.py` (hermes-trade-watchdog.timer) | 30min | **REPURPOSE — T1 live layer.** Already computes MFE giveback on open positions + reads regime_5m.json/continuum/volatility_gate. ADD: write live MFE/MAE snapshots to signal_outcomes for open positions. 30min cadence is right (1min overkill). | Cell stats, exit configs, gate changes |
| signal_outcomes write path | at close | **FIX in P0** — position_manager `_ensure_signal_outcomes_table` + hl-sync-guardian + cut_loser already write; coverage ~75%. Close the gap; join on trade_id (verified). | Historical backfill (nightly job) |
| **T2 cell-stats job (NEW)** | nightly | Compute n/WR/expectancy from signal_outcomes + brain trades → `brain/cell_stats`. Deterministic code. | Proposals, live changes |
| **T4 gate shadow (NEW, folds into T2 or small hourly)** | nightly | Forward-close shadow records; per-gate context-band shadow WR. | Gate changes — CEO approves |
| `brain_auditor` (opencode agent prompt, hourly :30) | hourly | **REPURPOSE as consumer, not computer.** Reads cell stats + gate shadow + watchdog steers → proposes deltas to kanban. Already has CEO-approval workflow (verified: EXTREME pump-chain- gate revert 06:39, ATR_TP_MIN 11:35). It is an LLM reviewer — "0 config changes" lines prove it judges, it cannot compute nightly stats. | Computing cell stats, replaying exits |
| **P6 training timer (NEW)** | weekly | Recompute cells, propose exit configs + gate changes w/ shadow eval + rollback plan → kanban. **Auditor does NOT cover this** — auditor is reviewer, not tuner. | Applying changes; touching protected flags |

**Net:** existing cadence covers *review and live open-position sensing*. New deterministic jobs cover *computation* (T2 nightly, T4 shadow, P6 weekly proposals). brain_auditor remains the hourly CEO-facing loop that consumes their output. Pipeline watchdog stays pure liveness. **Delta to plan:** T1 live-stream rides trade_watchdog (no new job); T4 audit feeds brain_auditor hourly (no new weekly report channel); P6 is the only new periodic compute job besides T2 — and its output lands in the existing kanban approval path, not a parallel one.

## DECISIONS

1. **P0 — APPROVE with scope correction.** Fix = point `wr_estimate` at trade_log (same logic as `decayed_wr_estimate`), NOT synapse schema. Add to P0: signal_outcomes write-path fix, exit_reason family normalization (hard_max_loss ×25, trail ×3), MFE/MAE write reliability. Backfill joins `trade_id` → `trades.id` (verified). Exclude pre-fix CL-T1 (all 83 trades) from any calibration. Dead 0-byte DB cleanup: fine, marginal. **No trading behavior change — safe under freeze.**
2. **Selection philosophy — CONFIRM with two guardrails.** Fewer trades, positive-expectancy cells only is correct (28/72 n≥10 cells profitable today). Modify: (a) require n≥15 OR strict Bayesian backoff for live selection — n≥10 at 60% over 90d is still thin; (b) **trade-count floor: 7d ≥ ~150** (currently 217). System is already signal-starved (ema_reclaim 0 trades EVER, 100% NEUTRAL regime). Do not cut below viable flow. Metric = PnL, not WR alone.
3. **Shadow-first — APPROVE.** 1-week lag right for exit configs and gate relaxations. Tighten P5: live-on-3-cells requires ≥15 shadow trades per cell AND shadow WR ≥ 90d baseline, compared within same regime.
4. **Guardrails — CONFIRM + 3 additions.** 5 changes/cycle, 10% magnitude, −5pp auto-rollback: keep. Add: (a) **no proposal may touch CEO_PROTECTED_FLAGS or PM_TRAIL_*** — T3 search space bounded by protected values (0.40/0.20 are floors/ceilings, not search bounds); (b) define rollback baseline window explicitly (7d pre-change WR, same query); (c) exit_reason normalization + MFE/MAE collection are prerequisites, not parallel work.
5. **P6 weekly timer — APPROVE with dependency fix.** New timer yes; live changes still CEO-only via kanban. **Re-sequence:** P6 cannot run meaningfully until normalization + reliable MFE/MAE collection land (currently 6.9% coverage). Move from "week 4" to "after P0 cleanup + 2wk MFE/MAE collection".

## PLAN DELTAS

| Phase | Plan said | Change to |
|---|---|---|
| P0 | wr_estimate fix + schema + backfill + dead DBs | + signal_outcomes write-path fix + exit_reason normalization + MFE/MAE write fix. wr_estimate = one-line trade_log redirect. Cell census restated **72 n≥10** not 81. |
| P1 | T2 cell store live, 81 cells success metric | T2 = new **nightly deterministic job**; brain_auditor reviews hourly (existing). Metric: ≥60 n≥10 cells published w/ backoff. |
| P2 | T3 exit optimizer, calibrate from 5k MFE/MAE pairs | **Blocked on data**: real corpus ~233 pairs/90d. Insert **P2a: 2 weeks reliable MFE/MAE collection** before quantile calibration. Bound search space by PM_TRAIL_* protected constants. |
| P3 | T4 shadow outcomes + first automated gate audit | Shadow records computed in T2/nightly; audit report **feeds brain_auditor existing hourly loop** (kanban), not a new weekly report. |
| P4–P5 | T5 shadow then live on 3 cells | Safety claim holds for gates (T5 adds layer, never removes). **Fails for exit constants** until PM_TRAIL bounded. P5 requires ≥15 shadow trades/cell same-regime. |
| P6 | Weekly training timer | Yes, but depends on P0 normalization + P2a MFE/MAE collection. Proposals→kanban→CEO only. |
| — | (not in plan) | Note b960ffe8 freeze until Oct 6 00:38. P0 non-trading OK; live changes wait. |

## RISKS

1. **T3 vs CEO_PROTECTED PM_TRAIL_*** — highest severity. Unbounded search = hard-rule violation. Mitigation: protected constants are immutable bounds; per-cell exit_config_id resolves *within* them.
2. **MFE/MAE sparsity** — T3 v1 would overfit 233 pairs. Mitigation: P2a collection period first; backoff on n<20.
3. **exit_reason fragmentation** — hard_max_loss ×25 labels poisons cell stats and exit optimizer. Mitigation: normalization is P0 prerequisite, not optional.
4. **Starvation feedback loop** — selection philosophy + already-starved NEUTRAL regime could drop trade count below signal-detection viability. Mitigation: 7d trade-count floor ≥150; selection must not block fail-open to signal-level stats when cell empty.
5. **SQLite migration under load** — signal_outcomes ALTER TABLE is metadata-only (safe with busy_timeout); batch backfill UPDATEs or run during low activity. Known "database is locked" pattern on price_collector — don't add another heavy writer without busy_timeout.
6. **Decider already queries signal_outcomes** (24h WR at :108) — schema extension must not break that query path. Additive columns only; verify decider_run import after P0.

## NEXT STEPS

1. **bug_hunter:** P0 — `wr_estimate` → trade_log redirect (one-liner); signal_outcomes write-path coverage gap; exit_reason family normalization map; verify decider_run signal_outcomes query unaffected. Non-trading, freeze-safe.
2. **self_learner:** snapshot 72 n≥10 cells (regime×signal×direction) to `data/signal_regime_memory.json` with WR/expectancy — baseline before any selection logic.
3. **signal_analyst:** start MFE/MAE write-reliability audit — where position_manager should write mfe_pct/mae_pct on close; target ≥90% of new closes within 2wk (P2a gate).
4. **CEO (me):** restate P1–P6 success metrics per deltas above; update plan file with corrected census + component ownership table. Live changes wait for freeze end Oct 6 00:38.
5. **Do NOT:** start T3 calibration, enable T5 live, or add a second weekly report channel. Do not touch PM_TRAIL_* or any CEO_PROTECTED flag.

*All numbers DB-verified 2026-10-04 via psql brain + associative_memory.db + data/signals_hermes_runtime.db + systemd unit inspection.*
