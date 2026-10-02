# 2026-10-02 — Independent Audit: SHORT-BB-DEAD-ZONE Filter

**Auditor:** independent subagent (fresh eyes, no priming beyond the 5 claims under review)
**Scope:** PostgreSQL `brain.trades`, all closed SHORT trades; code at `scripts/signal_compactor.py:3585-3613`; constants at `scripts/hermes_constants.py:897-902`
**Scripts:** `audit/audit_bb_deadzone.py`, `audit/audit_bb_supplementary.py` (full outputs in `audit/`)
**Data:** 3,051 closed SHORTs; 1,971 (64.6%) carry `entry_bb_position`; 695 carry `_signal_metadata.bb_position`; range 2026-05-20 → 2026-10-02

---

## Claim-by-claim verdict

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Dead zone 0.7-0.85: 167T, 35.9% WR, -$1.23, justified to block | **CONFIRM (numbers) / NUANCE (justification)** | Reproduced exactly. WR 35.9% vs 44.3% rest: z=-2.085, **p=0.037**, Fisher p=0.041. Negative in every month with data (Jun -$0.89, Jul -$0.03, Sep -$0.26) incl. profitable June. BUT: (a) mean-pnl permutation NOT significant (p=0.38, CI [-0.020,+0.006]); (b) vs currently-allowed bands p=0.093; (c) p=0.037 does not survive ~10-test multiple-comparison correction; (d) **the filter reads `_signal_metadata.bb_position`, the analysis used `entry_bb_position` — these disagree on band ~53-68% of the time (mean \|diff\| 0.22)**; in the filter's actual view the dead zone is 50T **58.0% WR**, net -$0.88, nothing significant (WR p=0.38, pnl p=0.64) |
| 2 | 0.85+: 269T, 39.8% WR, -$3.33, should also be blocked | **NUANCE — do NOT blanket-block** | Numbers reproduced exactly. But WR edge NOT significant (z=-1.35, **p=0.18**); mean-pnl barely (p=0.039, CI [-0.0257,-0.0006]). Entire loss concentrated in **accel_300_,rs_r: 48T 27.1% WR -$1.86, in-zone vs out z=-2.79 p=0.005** — while dominant signal accel_300_,rs_s_broken is **flat** in 0.85+ (169T 43.2% +$0.02). In the filter's actual view **>1.00 is PROFITABLE** (26T 65.4% WR +$0.98) |
| 3 | <0.2: 855T, 45.3% WR, +$3.51, most profitable band | **CONFIRM (all-time USD) / DISPUTE (as an edge)** | Reproduced exactly. But: WR vs rest not significant (p=0.19); mean-pnl borderline (p=0.053); **avg pnl_pct NEGATIVE (-0.04%)** — profitable only in absolute USD; and **reversed hard recently: 30d 30.0% WR -$2.78, 90d 19.3% WR -$3.96 — now the WORST band**. All-time edge is May-July only |
| 4 | 0.5-0.7: 203T, 46.8% WR, +$1.60, good band | **DISPUTE** | Reproduced (203T/46.8%/+$1.60) but decomposes: **0.50-0.55 = 43T 55.8% WR +$1.34, mean-pnl p=0.035, CI [+0.009,+0.056] — statistically positive, and ALREADY BLOCKED by live DEAD_ZONE2 (0.35-0.55)**; 0.55-0.70 = 160T 44.4% +$0.26, indistinguishable from average (WR p=0.83, pnl p=0.75). The "good band" is the blocked sub-band |
| 5 | STX bb=0.7417 correctly blocked | **CONFIRM (event) / UNVERIFIABLE (outcome)** | Log `pipeline.log`: 5× `🚫 [SHORT-BB-DEAD-ZONE] STX bb_position 0.7417` 2026-10-02 01:22-01:26. Price path ambiguous: 0.3738 → 0.3685 (-1.4%, favorable, trail may have banked win) → 0.3805 (+1.8% by 03:00, 0.5% SL hit ~02:00). Outcome depends on exit mechanics; single case proves nothing |

## Statistical significance (all-time, column bb)
- Dead zone WR vs rest: **p=0.037** (marginal; not robust to multiple comparisons; not significant vs allowed-bands p=0.093)
- Dead zone mean pnl: p=0.38 — **not significant**
- 0.85+ WR: p=0.18 — **not significant**; mean pnl p=0.039 (barely)
- accel_300_,rs_r × 0.85+: WR **p=0.005**, mean pnl p=0.007 — the only robust finding
- accel_300_,rs_s_broken × dead zone: WR p=0.053 — marginal
- 0.50-0.55 mean pnl (blocked by DEAD_ZONE2): **p=0.035 positive**
- Filter's-eye-view (metadata bb): **nothing about the dead zone is significant** (58% WR, pnl p=0.64); >1.00 profitable (+$0.98)

## Confounders
- **Signal composition:** dead zone dominated by accel_300_,rs_s_broken (97/167); same signal 37.1% WR in-zone vs 47.4% out (+$7.05) → genuine conditional edge, not pure composition. But accel_300_,rs_r (46.2% WR in-zone) and rs_r,rs_s_broken (50%) are FINE in the dead zone → blanket block over-inclusive.
- **Time:** dead zone negative every month incl. profitable June → not purely period-driven. 30d/90d windows directionally consistent but tiny n (8/43) and NOT significant (p=0.38/0.60).
- **Regime:** `volatility_regime` null for 159/167 dead-zone trades; `entry_regime_4h` 100% null → regime confounding **cannot be ruled out** from the trades table.
- **Experiment arms:** all dead-zone and 0.85+ trades are sl_group=control, ~all live → no A/B confound.
- **Data completeness:** bb column coverage collapsed — Aug 2026 3/719 (0%), Sep 35% → recent-window bb analysis rests on selected samples.

## Code review (signal_compactor.py:3585-3613)
- Dead zone1 blocks `MIN <= bb <= MAX` — **inclusive at 0.85**; the 13 exact-0.85 trades netted **+$0.61 at 69.2% WR** — the inclusive boundary blocks historically net-positive trades. Suggest `< MAX` if 0.85+ is not blocked.
- Dead zone2 (0.35-0.55) blocks the historically best sub-band 0.50-0.55; OpenMemory: deployed 2026-09-15 on a **7-day** basis ("Expected +0.99/7d"). Live impact since 09-29: dead-zone1 29 blocks, **dead-zone2 182 blocks**.
- **Code comments cite 7-day numbers as justification** (3586-3587: "7d: 17T 41.2%WR"; 3601: "25T 44%WR -$0.99/7d… Preserves 0.55-0.70 (70.6%WR +$0.95)"). All-time: 0.55-0.70 is **44.4% WR +$0.26**, not 70.6% — comments will mislead future auditors.
- **Filter coverage gap (critical):** metadata bb_position coverage by signal — pullback-entry 100%, pump-chain 100%, accel_300_v 100%, bb_bounce_short 100%, **accel_300_,rs_s_broken 0/1021 (0%), accel_300_,rs_r 0/281 (0%)**. The dominant SHORT flow (52%+ of bb shorts) is structurally invisible to both dead-zone filters — they fire only on minority signal families.
- **Variable mismatch (critical):** `entry_bb_position` written by `feature_recorder.record_entry_features` at trade ENTRY; filter reads detection-time `_signal_metadata.bb_position`. Band flips on 53-68% of overlapping trades per family (pump-chain 53%, pullback-entry 67.5%). The all-time justification was computed on a variable the filter never reads.
- `signal_created_at` is NULL for 100% of trades → staleness auditing impossible from DB (AGENTS.md documented failure mode, unverifiable).

## Recommendations
1. **Keep dead-zone1 (0.70-0.85) as deployed** — weak-but-real column-view evidence (WR p=0.037, negative every month) — but re-justify honestly: the filter's own decision variable shows 58% WR in-zone; today it mostly adds safety margin, not proven edge.
2. **Do NOT extend the block to 0.85+ as a blanket rule.** WR edge not significant (p=0.18); loss is concentrated in accel_300_,rs_r (p=0.005); dominant signal is flat there; >1.00 is profitable in the filter's view. If action is wanted: **signal-specific rule — block accel_300_,rs_r SHORT at bb≥0.85**, not a band block.
3. **Fix DEAD_ZONE2:** narrow to 0.35-0.50 or exempt 0.50-0.55 — it is blocking the single best all-time band (55.8% WR, +$1.34, p=0.035) and has produced 182 blocks in 4 days.
4. **Do not treat <0.2 as a go-zone** — recently worst band (30d 30% WR); monitor, don't boost.
5. **Data fixes before any further bb-based filter work:** (a) make accel-family signals record bb_position in metadata, or the dead-zone filters are cosmetic for most flow; (b) pick ONE canonical bb variable (recommend recording detection-time bb into a dedicated column at entry); (c) restore bb feature recording (Aug≈0% coverage); (d) populate signal_created_at; (e) update stale7d code comments with all-time figures.
6. **Materiality caveat:** whole SHORT book all-time is -$4.62 on 3,051 trades at ~$11.36 avg size. These band effects are real but tiny in absolute USD at current sizing.

**Confidence:** High on all reproduced numbers and tests (ran twice, cross-checked via independent SQL + Python paths). Medium on the "keep vs extend" recommendation — direction is consistent across months and signals, but every individual all-time test is marginal (p 0.03-0.05) and the variable-mismatch finding means the historical justification and the live filter operate on different quantities; the honest statement is "no robust evidence to extend, some weak evidence the existing zone is bad, and a critical unresolved question about which bb variable the edge actually lives in."
