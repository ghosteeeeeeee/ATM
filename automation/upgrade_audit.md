# Upgrade Audit Trail

**Created:** 2026-08-28
**Purpose:** Track plan evaluations and implementation status

---

## Plan: 2026-08-27_ponytail-full-audit.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Full codebase audit — 33,765 lines of dead/duplicate code identified across 80 dead scripts, zombie code, dead signal registry entries, and core function duplication
- **Difficulty:** Level 1 (deletions) / Level 3 (refactoring)
- **Value:** HIGH — 22% of codebase is dead code
- **Status:** IN PROGRESS
- **Reason:** Starting with Level 1 safe deletions: stale imports, dead registry entries, dead code blocks

## Plan: spec-guitar-tuning.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Multi-dimensional adaptive tuning (signal × regime parameter matrix)
- **Difficulty:** Level 3-4 (architecture change, 8-week timeline)
- **Value:** HIGH — auto-tunes parameters per market regime
- **Status:** DEFERRED
- **Reason:** Needs regime column in signal_outcomes first (Phase 0). Massive scope. Defer until Phase 0 is complete.

## Plan: fish-finder-species-census-2026-08-26.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Add missing signal species (Volume Profile, Beta Decoupler, Regime Transitions, Liquidity)
- **Difficulty:** Level 2-3 (new signals/filters)
- **Value:** MEDIUM-HIGH — fills blindspots, +5-10% WR potential
- **Status:** PENDING
- **Reason:** Volume Profile (P0) uses local candles.db — feasible. Beta Decoupler (P1) uses local data. Defer to signal-lab.

## Plan: 2026-08-26_30s-price-interval-migration.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Split architecture for 30s price collection — dual-track writes
- **Difficulty:** Level 1 (1 line change)
- **Value:** HIGH — faster exit management without signal regression
- **Status:** IMPLEMENTED
- **Reason:** Already deployed. price_history quantized to minute boundaries.

## Plan: exit-mechanics-v2.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Fix backwards PROFIT_MONSTER_BYPASS_SIGNALS — proven signals missing, losing signals bypassed
- **Difficulty:** Level 1 (constant change)
- **Value:** HIGH — PM Trail interferes with proven winners
- **Status:** IMPLEMENTED
- **Reason:** Bypass list already updated: bb_bounce+, confluence, stop_hunt_reversal added. ct-hot+ removed (correctly gets PM Trail now).

## Plan: exit-spec-review.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Independent review of exit-mechanics-ownership spec
- **Difficulty:** N/A (review only)
- **Value:** MEDIUM — caught factual errors in original spec
- **Status:** COMPLETED
- **Reason:** Review done, recommendations incorporated into exit-mechanics-v2.

## Plan: automation-team-improvements.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Fix broken learning engines (session learner dead, self-learner stuck, A/B learner defunct)
- **Difficulty:** Level 1-2 (mixed)
- **Value:** HIGH — learning engines drive system improvement
- **Status:** PARTIAL
- **Reason:** Self-learner expanded (PARAM_CONFIG 20+ params, param_map 15+ signals). AB learner deleted. Session learner still dead (0 session_summaries). Needs OpenMemory bridge.

## Plan: btc-crash-filter-plan.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** BTC flash crash detection — acceleration filter to catch crashes 2-3 min earlier
- **Difficulty:** Level 2 (new filter logic)
- **Value:** HIGH — prevents trades during cascade crashes
- **Status:** IMPLEMENTED
- **Reason:** BTC acceleration filter deployed. Constants: BTC_ACCEL_VEL_THRESHOLD, BTC_ACCEL_WINDOW, BTC_ACCEL_BLOCK_DURATION.

## Plan: mae-guard-multialt-spec.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Re-enable MAE Guard at 2.0% + add Multi-Alt Divergence Filter (Layer 6)
- **Difficulty:** Level 2 (new filter + re-enable)
- **Value:** HIGH — cascade protection, +$1.92 net PnL in backtest
- **Status:** IMPLEMENTED
- **Reason:** MAE Guard re-enabled (CL_MAE_GUARD_ENABLED=True, widened to 3.0%). Multi-alt divergence filter deployed (MULTI_ALT_DIVERGENCE_ENABLED=True).

## Plan: signal_confluence_spec.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Meta-signal detecting persistence + compounding of first-order signals
- **Difficulty:** Level 2 (new signal)
- **Value:** MEDIUM-HIGH — validates signal quality via temporal persistence
- **Status:** IMPLEMENTED
- **Reason:** signal_confluence.py created, registered in __init__.py, constants added, Layer 2 enforcement in signal_schema.py, source weights in compactor, REGIME_SIGNALS updated.

## Plan: regime-transition-analysis-2026-08-24.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Fix V-reversal losses — TIDE too slow, DIRECTIONAL_OUTCOME too weak
- **Difficulty:** Level 1 (constant changes)
- **Value:** HIGH — prevents ~$18-19 per V-reversal incident
- **Status:** IMPLEMENTED
- **Reason:** DIRECTIONAL_OUTCOME velocity tiers upgraded: 0.6: 0.0 (3+/5 hard block), 0.4: 0.5. BTC 30m momentum filter pending.

## Plan: conf-filter-plan.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Filter high-confidence trades (90+) that are worst performers
- **Difficulty:** Level 1 (constant change)
- **Value:** HIGH — turns losing system into break-even (+$1.45 PnL)
- **Status:** IMPLEMENTED
- **Reason:** CONF_FILTER_MAX = 89 deployed. Blocks raw conf >= 90 at compactor level.

## Plan: confidence-calibration-plan.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Investigate non-monotonic confidence curve, proposed fix to store raw vs inflated
- **Difficulty:** N/A (investigation)
- **Value:** LOW — proposed fix rejected, existing filter already working
- **Status:** COMPLETED (no action needed)
- **Reason:** CONF_FILTER already blocks worst cases. Non-monotonic curve is noise (15 trades per extreme tier). Fix would be redundant and risky.

## Plan: atr-sl-widen.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Widen ATR stop loss to reduce premature stops
- **Difficulty:** Level 1 (constant change)
- **Value:** MEDIUM — reduces premature stop-outs
- **Status:** IMPLEMENTED (likely)
- **Reason:** ATR_SL_MIN was widened to 0.015 (1.5%) per exit-spec-review notes.

## Plan: cascade-crash-analysis-2026-08-23.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Analyze cascade crash losses and propose protections
- **Difficulty:** Level 2 (analysis + filters)
- **Value:** MEDIUM — informs crash filter design
- **Status:** COMPLETED
- **Reason:** Analysis complete, fed into btc-crash-filter-plan and mae-guard-multialt-spec.

## Plan: favorites-daily-update-spec.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Daily favorites list update automation
- **Difficulty:** Level 2 (automation)
- **Value:** LOW-MEDIUM — maintains favorites list
- **Status:** UNKNOWN
- **Reason:** Needs verification of current state.

## Plan: signal-confluence-spec (duplicate)
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Same as signal_confluence_spec.md
- **Difficulty:** N/A
- **Value:** N/A
- **Status:** DUPLICATE
- **Reason:** Already evaluated above.

## Plan: review-guitar-tuning.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Independent review of guitar-tuning spec
- **Difficulty:** N/A (review)
- **Value:** MEDIUM — caught feasibility issues with 4D matrix
- **Status:** COMPLETED
- **Reason:** Review done, led to v2 spec with 2D matrix.

## Plan: spec-signal-regime-memory.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Signal enable/disable per regime (dormant vs active)
- **Difficulty:** Level 2-3
- **Value:** MEDIUM — complementary to guitar tuning
- **Status:** PENDING
- **Reason:** Overlaps with guitar tuning spec. Defer until guitar tuning Phase 0 (regime column) is done.

## Plan: atr-spike-signal-build.md / atr-spike-backtest-results.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** ATR spike signal design and backtest
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED (atr_spike.py exists in signals/)

## Plan: sl-tuning.md / r2-trend-long-trailing-sl-tuning.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Stop loss and trailing SL tuning
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED (ATR SL params in hermes_constants.py, self-learner tunes them)

## Plan: coin_tracker_analysis_expansion.md / coin_tracker_setup_improvements.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Expand coin tracker analysis and setup
- **Difficulty:** Level 2
- **Value:** LOW-MEDIUM
- **Status:** UNKNOWN
- **Reason:** Needs verification.

## Plan: imx-spike-detection.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** IMX-specific spike detection
- **Difficulty:** Level 2
- **Value:** LOW — token-specific, low trade volume
- **Status:** SKIPPED
- **Reason:** Niche token-specific feature, low priority.

## Plan: 2026-08-21_copy-trader-entry-timing-deep-dive.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Deep dive into copy trader entry timing
- **Difficulty:** Level 2 (analysis)
- **Value:** MEDIUM
- **Status:** UNKNOWN
- **Reason:** Needs verification.

## Plan: 2026-08-22_copy-trader-dashboard-enhancements.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Copy trader dashboard improvements
- **Difficulty:** Level 2
- **Value:** LOW — cosmetic
- **Status:** PENDING
- **Reason:** Low priority, dashboard is working.

## Plan: 2026-08-21_hl-reconciliation-postmortem-spec.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** HL reconciliation postmortem
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** UNKNOWN

## Plan: signal-cluster-analysis-2026-08-26.md / signal-cluster-brainstorm-2026-08-26.md
- **Date scanned:** 2026-08-28 00:53
- **Core request:** Signal cluster analysis and brainstorm
- **Difficulty:** N/A (analysis)
- **Value:** MEDIUM — informed fish-finder-species-census
- **Status:** COMPLETED
- **Reason:** Analysis complete, fed into fish-finder-species-census.

---

## Summary

| Status | Count | Plans |
|--------|-------|-------|
| IMPLEMENTED | 10 | 30s-migration, exit-mechanics, btc-crash, mae-guard, confluence, velocity-tiers, conf-filter, atr-sl-widen, atr-spike, sl-tuning |
| COMPLETED (analysis/review) | 5 | exit-spec-review, confidence-calibration, cascade-analysis, signal-cluster, review-guitar-tuning |
| IN PROGRESS | 1 | ponytail-full-audit |
| PARTIAL | 1 | automation-team-improvements |
| PENDING | 4 | fish-finder, spec-signal-regime-memory, favorites-daily, copy-trader-dashboard |
| DEFERRED | 1 | guitar-tuning (needs Phase 0 first) |
| SKIPPED | 1 | imx-spike-detection |
| UNKNOWN | 4 | copy-trader-deep-dive, hl-reconciliation, coin-tracker-* |
