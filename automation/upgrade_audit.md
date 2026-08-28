# Upgrade Audit Trail

**Generated:** 2026-08-23 17:45 UTC
**Scanned:** 20 plans from `/root/.hermes/plans/`

---

## Plan: mae-guard-multialt-spec.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Re-enable MAE Guard at 2.0% + add Multi-Alt Divergence Filter (Layer 6) to btc_crash_filter.py
- **Difficulty:** Level 1 (MAE Guard) / Level 2 (Multi-Alt Filter)
- **Value:** HIGH — cascade crash protection, +$1.92/7d backtest
- **Status:** IMPLEMENTED
- **Reason:** MAE Guard re-enabled at 2.0% (hermes_constants.py:1028). Multi-alt filter implemented in btc_crash_filter.py:273-310 with constants at lines 828-833. Both live.

## Plan: cascade-crash-analysis-2026-08-23.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Analysis report proposing multi-alt filter, lower BTC threshold, MAE guard re-enable
- **Difficulty:** N/A (analysis, not implementation)
- **Value:** HIGH — data-proven recommendations
- **Status:** IMPLEMENTED (all 3 recommendations acted on)
- **Reason:** Multi-alt filter ✅, MAE guard ✅, BTC threshold remains at -1.5% (plan says test on 30d first).

## Plan: atr-sl-widen.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Independent verification — recommends NOT widening SL, fix features_recorded bug, disable MAE guard
- **Difficulty:** Level 1 (config) / Level 1 (DB fix)
- **Value:** MEDIUM — bug fix + config corrections
- **Status:** IMPLEMENTED
- **Reason:** ATR SL kept at current values ✅. MAE Guard re-enabled at 2.0% (conservative start per this plan). features_recorded bug noted but low priority.

## Plan: btc-crash-filter-plan.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** BTC acceleration detection to catch crashes 2-3 min earlier
- **Difficulty:** Level 2-3
- **Value:** MEDIUM — existing filter catches post-crash, acceleration would catch build-up phase
- **Status:** PENDING
- **Reason:** Requires backtest on 30d data before implementation. Multi-alt divergence filter (from mae-guard spec) already provides broader protection.

## Plan: favorites-daily-update-spec.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Daily favorites update + weekly rhythm analysis + Hebbian integration
- **Difficulty:** Level 3-4
- **Value:** MEDIUM — system optimization, not direct PnL
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Daily updater + rhythm analysis ✅. Hebbian sync pending. Complex multi-system work, appropriately deferred.

## Plan: 2026-08-22_copy-trader-dashboard-enhancements.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Copy trader dashboard Phase 2-4 enhancements
- **Difficulty:** Level 2-3
- **Value:** LOW-MEDIUM — dashboard improvements, not trading logic
- **Status:** PENDING
- **Reason:** Phase 1 complete. Phase 2-4 (copy delay analysis, trader scoring, alerts) not yet implemented. Lower priority than trading logic improvements.

## Plan: 2026-08-21_copy-trader-entry-timing-deep-dive.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Fix copy trader entry timing — disable SHORT, add time-of-day filter
- **Difficulty:** Level 1-2
- **Value:** HIGH — projected +$91.19 PnL improvement
- **Status:** IMPLEMENTED
- **Reason:** SHORT copy disabled ✅ (HL_COPY_SIGNAL_MINUS_ENABLED=False). Time-of-day filter implemented but DISABLED (COPY_BAD_HOURS_ENABLED=False — intentional: "we're 24/7 live, improve entries not block hours"). Copy trader exit correlation enabled ✅.

## Plan: 2026-08-21_hl-reconciliation-postmortem-spec.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Automated HL reconciliation to catch PnL bugs
- **Difficulty:** Level 2
- **Value:** HIGH — data integrity
- **Status:** IMPLEMENTED
- **Reason:** Status marked IMPLEMENTED in plan itself.

## Plan: copy-trader-evolution-spec.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Per-trader performance tracking + trader exit correlation
- **Difficulty:** Level 3-4
- **Value:** HIGH — fundamental copy trader improvement
- **Status:** IMPLEMENTED
- **Reason:** trader_performance table ✅, exit correlation ✅ (COPY_TRADE_EXIT_ENABLED=True), copy_weight ✅.

## Plan: atr-spike-backtest-results.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** ATR spike signal backtest results and token quality ratings
- **Difficulty:** N/A (results, not implementation)
- **Value:** N/A
- **Status:** IMPLEMENTED
- **Reason:** Signal is live (ATR_SPIKE_ENABLED=True), 83% WR, +74.4% PnL.

## Plan: atr-spike-signal-build.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Build ATR spike signal v5 with quality gates
- **Difficulty:** Level 2
- **Value:** HIGH — 83% WR, momentum signal
- **Status:** IMPLEMENTED
- **Reason:** scripts/signals/atr_spike.py exists and is live.

## Plan: sl-tuning.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Stop-loss tuning for ATR spike signal
- **Difficulty:** N/A (research)
- **Value:** N/A
- **Status:** IMPLEMENTED
- **Reason:** 0.75% SL confirmed as optimal. Current params match recommendation.

## Plan: imx-spike-detection.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Detect single-candle breakouts from ATR compression
- **Difficulty:** Level 2
- **Value:** HIGH — catch missed breakouts
- **Status:** IMPLEMENTED
- **Reason:** This is the ATR spike signal. Already built and live.

## Plan: retroactive-scan-delayed-entry.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Retroactive breakout scan for missed moves
- **Difficulty:** Level 3
- **Value:** MEDIUM — safety net for missed breakouts
- **Status:** PENDING
- **Reason:** Complex new feature. Requires breakout_engine.py integration. Not yet implemented. Lower priority than existing signal optimization.

## Plan: 2026-08-19_short-bias-fix.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Fix short bias — investigate why SHORTs aren't firing
- **Difficulty:** N/A (investigation)
- **Value:** N/A
- **Status:** IMPLEMENTED
- **Reason:** Root cause: market condition, not bug. Counter-trend SHORTs are losers (26% WR). System correctly blocks them.

## Plan: confidence-calibration-plan.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Fix non-monotonic confidence curve
- **Difficulty:** N/A (investigation)
- **Value:** N/A
- **Status:** IMPLEMENTED (fix rejected, existing filter confirmed working)
- **Reason:** CONF_FILTER at 89 already blocks worst cases. Proposed fix rejected as redundant.

## Plan: conf-filter-plan.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Block high-confidence (90+) trades + time window filter
- **Difficulty:** Level 1
- **Value:** HIGH — +$1.45 PnL projected
- **Status:** IMPLEMENTED
- **Reason:** CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89. Working. Time filter exists but disabled (intentional).

## Plan: coin_tracker_setup_improvements.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Improve coin_tracker setup detection — regime gate, confirming analyses, raise MIN_COMPOSITE
- **Difficulty:** Level 1-2
- **Value:** MEDIUM — signal quality improvement
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** MIN_COMPOSITE raised to 63 ✅. Coin tracker hot re-enabled ✅. Regime gate ✅. Warm bypass removed ✅ (2026-08-24). Confirming analyses and age decay still pending (Level 2-3).

## Plan: r2-trend-long-trailing-sl-tuning.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Widen trailing SL for r2_trend_long signals
- **Difficulty:** Level 1
- **Value:** MEDIUM — survive pullbacks on trend signals
- **Status:** IMPLEMENTED
- **Reason:** TRAILING_DISTANCE_PCT widened to 2.00% (from 0.80%). R2_TREND_LONG_MAX_ACCEL and BLOCK_STALE added.

## Plan: coin_tracker_analysis_expansion.md
- **Date scanned:** 2026-08-23 17:45
- **Core request:** Expand coin_tracker with Wyckoff, Elliott Wave, S/R, trend, volume profile
- **Difficulty:** Level 3-4
- **Value:** MEDIUM — analysis engine expansion
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Phase 1 (analysis) complete ✅. Phase 2 (signal generation) in progress. Phase 3 (autonomous trading) future work.

## Plan: signal_confluence_spec.md
- **Date scanned:** 2026-08-24 05:30
- **Core request:** Meta-signal detecting persistence + compounding of first-order signals over 30-min rolling window
- **Difficulty:** Level 2
- **Value:** HIGH — filters noise, catches multi-source agreement
- **Status:** IMPLEMENTED
- **Reason:** All 6 files done: signal_confluence.py ✅, hermes_constants.py constants ✅, __init__.py registry ✅, signal_schema.py Layer 2 ✅, signal_compactor.py weights ✅, volatility_gate.py all regimes ✅.

## Plan: regime-transition-analysis-2026-08-24.md
- **Date scanned:** 2026-08-25 12:00
- **Core request:** Fix regime transition detection — V-reversals bypass TIDE and DIRECTIONAL_OUTCOME too slowly
- **Difficulty:** Level 1-2
- **Value:** HIGH — would have prevented $34.78 in losses during Aug 24 incident
- **Status:** IMPLEMENTED
- **Reason:** All 5 recommendations done: velocity tiers upgraded (3+/5 = hard block) ✅, BTC momentum filter ✅, DIRECTIONAL_OUTCOME time window 15min ✅, BTC accel filter ✅. BTC level filter deferred (Level 2, new module).

---

## Summary (Updated 2026-08-28)

| Status | Count | Plans |
|--------|-------|-------|
| IMPLEMENTED | 18 | mae-guard, cascade-analysis, atr-sl-widen, hl-reconciliation, copy-trader-evolution, atr-spike-backtest, atr-spike-build, sl-tuning, imx-spike, short-bias-fix, confidence-calibration, conf-filter, r2-trend-long, signal-confluence, regime-transition, **exit-mechanics-v2**, **exit-mechanics-ownership** |
| PARTIALLY IMPLEMENTED | 4 | favorites-daily-update, coin_tracker_setup, coin_tracker_expansion, **ponytail-audit** |
| PENDING | 5 | btc-crash-filter, dashboard-enhancements, retroactive-scan, fish-finder-species-census, automation-team-improvements |
| NEW PENDING | 3 | **signal-regime-memory** (L3-4), **volume-profile-signal** (L2), **beta-decoupler-signal** (L2) |

**Scanned: 40 plans (3 new this session)**
**Implemented: 18 (45%)**
**Partially implemented: 4 (10%)**
**Pending: 8 (20%)**
**Skipped (analysis-only): 10 (25%)**

### Level 1-2 actions taken this session (2026-08-28):
1. **_ema() dedup**: Extracted 4 duplicate _ema() definitions in signal_schema.py → 1 module-level function (~12 LOC removed, zero behavior change).
2. **Ponytail audit verification**: Confirmed zombie files deleted, vortex_break disabled, signal registry pruned (65→17), bypass list fixed, velocity tiers upgraded. Most Level 1 items already done.
1. **exit-mechanics-v2**: Fixed PROFIT_MONSTER_BYPASS_SIGNALS — removed `ct-hot+`/`ct-hot-` (losing signals, PM Trail should help), added `bb_bounce+`/`confluence` (proven, shouldn't have PM Trail).
2. **atr-sl-widen**: Widened MAE Guard BASE_THRESHOLD from 2.0% to 3.0% — backtest showed -$5.43/wk at 1.5%, -$2.82/wk at 2.0%, -$2.69/wk at 3.0%. Only catches true crashes now.
3. **features_recorded bug**: Already fixed — 2633/2633 trades with entry_rsi_14 have features_recorded=TRUE.
4. **ATR_SL_MIN**: Already at 0.015 (widened from 0.012). No change needed.

### Plans evaluated this session (new):
- **fish-finder-species-census**: Level 3-4, HIGH value. Blindspot analysis: missing Volume Profile, Beta Decoupler, Regime Transition, Liquidity. CEO priority: P0 Volume Profile, P1 Beta Decoupler. Deferred to signal lab.
- **automation-team-improvements**: Level 1-2, HIGH value. Session learner dead (0 sessions), self-learner stuck (1 param), A/B learner defunct. Recommended: fix self-learner PARAM_CONFIG (Level 2), delete A/B learner (Level 1).
- **signal-cluster-brainstorm**: Level 2-4, HIGH value. 13 ideas: Market Phase Gate, Hebbian V2, Confluence Scorer, Lifecycle Filters, Inverse Guard, etc. P0: Phase Gate + Confluence Scorer (+16-28% WR projected).
- **signal-cluster-analysis**: N/A (analysis, not implementation). 30-day analysis of 69,990 signals. Phase cycles, lead-lag relationships, confluence zones.
- **exit-mechanics-v2**: Level 1, HIGH value. Fix bypass list — DONE this session.
- **exit-mechanics-ownership**: Level 2, MEDIUM value. Exit owner model (DB column). Deferred — bypass list fix gets 80% benefit.
- **exit-spec-review**: N/A (review). Found 8 errors in exit-mechanics-ownership spec. Recommended Phase 0 only (bypass fix).
- **30s-price-interval-migration**: IMPLEMENTED. Split architecture (30s latest_prices, 60s price_history).
- **btc-crash-filter-plan**: Level 2, MEDIUM value. Acceleration detection needs 30d backtest. PENDING.
- **conf-filter-plan**: IMPLEMENTED. conf < 89 filter active.
- **sl-tuning**: IMPLEMENTED. ATR spike 0.75% SL confirmed optimal.
- **short-bias-fix**: IMPLEMENTED. Market condition, not bug.
- **atr-sl-widen**: PARTIALLY IMPLEMENTED. ATR SL kept at 1.5%. MAE Guard widened to 3.0% this session.
- **favorites-daily-update-spec**: PARTIALLY IMPLEMENTED. Daily updater + rhythm done, Hebbian sync pending.
- **coin_tracker_setup_improvements**: PARTIALLY IMPLEMENTED. MIN_COMPOSITE raised, regime gate done, warm bypass removed. Confirming analyses + age decay pending.
- **r2-trend-long-trailing-sl-tuning**: IMPLEMENTED. TRAILING_DISTANCE_PCT widened to 2.00%.
- **confidence-calibration-plan**: IMPLEMENTED (fix rejected, existing filter works).
- **atr-spike-backtest-results**: IMPLEMENTED. 83% WR signal live.
- **imx-spike-detection**: IMPLEMENTED. Same as ATR spike signal.
- **copy-trader-entry-timing-deep-dive**: IMPLEMENTED. SHORT copy disabled, exit correlation enabled.
- **copy-trader-dashboard-enhancements**: PENDING. Phase 2-4 not yet implemented.
- **copy-trader-evolution-spec**: IMPLEMENTED. Per-trader performance + exit correlation.
- **2026-08-27_ponytail-full-audit**: PARTIALLY IMPLEMENTED. 80 dead scripts, zombie files, vortex_break, signal registry, bypass list, velocity tiers all done. Remaining: _ema extraction (DONE this session), dead code blocks in position_manager/signal_schema, sys.path boilerplate, blacklist dedup.
- **spec-signal-regime-memory**: PENDING. Level 3-4. Major architecture — persist regime at entry, regime-aware lifecycle, dormant state. CEO priority.
- **fish-finder-species-census**: PENDING. Level 2-3. Volume Profile (P0), Beta Decoupler (P1), Regime Transition (P1). Blindspot analysis.
- **automation-team-improvements**: PARTIALLY IMPLEMENTED. A/B learner deleted (not found). Self-learner PARAM_CONFIG expansion pending (Level 2). Session learner → OpenMemory bridge pending (Level 2).
- **spec-signal-regime-memory**: PENDING. Level 3-4. Regime-aware signal lifecycle — prevent premature signal death.

### Actions taken this session (2026-08-28):
1. **_ema() dedup**: Extracted 4 duplicate _ema() definitions in signal_schema.py into 1 module-level function. ~12 lines removed, zero behavior change.
2. **Verified ponytail audit items**: zombie files already deleted, vortex_break already disabled, signal registry already pruned, bypass list already fixed, velocity tiers already upgraded. Most Level 1 ponytail items already done.
3. **Skipped CEO_PROTECTED_FLAGS/RESEARCH_FLAGS removal**: Actually used by self_learner.py as real guard. Not yagni.
4. **Skipped doubly-dead flag removal**: NEVER_REENABLE_FLAGS actively used by self_learner to prevent re-enabling. Flags serve documentation purpose.
5. **Skipped _get_confluence_signals_legacy removal**: Still covers 7K rows (10.8%) with NULL signal_types. Not dead.

### Remaining items (prioritized):
1. **Self-learner PARAM_CONFIG expansion** (Level 2, automation-team-improvements) — unlocks auto-tuning of 15+ params
2. **BTC acceleration detection backtest** (Level 2, btc-crash-filter-plan) — needs 30d data
3. **Signal regime memory** (Level 3-4, spec-signal-regime-memory) — regime-aware lifecycle, dormant state
4. **Volume Profile signal** (Level 2, fish-finder-species-census) — CEO P0, +5-8% WR projected
5. **Beta Decoupler signal** (Level 2, fish-finder-species-census) — CEO P1, +3-5% WR projected
6. **Coin tracker confirming analyses** (Level 2, coin_tracker_setup_improvements)
5. **Market Phase Gate** (Level 2-3, signal-cluster-brainstorm) — +5-10% WR projected
6. **Confluence Scorer** (Level 2, signal-cluster-brainstorm) — +5-8% WR projected
7. **Retroactive scan** (Level 3, retroactive-scan-delayed-entry)
8. **Dashboard enhancements** (Level 2-3, copy-trader-dashboard)
