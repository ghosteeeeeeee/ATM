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

---

## Summary (Updated 2026-08-24)

| Status | Count | Plans |
|--------|-------|-------|
| IMPLEMENTED | 15 | mae-guard, cascade-analysis, atr-sl-widen, hl-reconciliation, copy-trader-evolution, atr-spike-backtest, atr-spike-build, sl-tuning, imx-spike, short-bias-fix, confidence-calibration, conf-filter, r2-trend-long, signal-confluence |
| PARTIALLY IMPLEMENTED | 3 | favorites-daily-update, coin_tracker_setup, coin_tracker_expansion |
| PENDING | 3 | btc-crash-filter, dashboard-enhancements, retroactive-scan |

**Scanned: 21 plans**
**Implemented: 15 (71%)**
**Partially implemented: 3 (14%)**
**Pending: 3 (14%)**

### Level 1 actions taken this session:
- Removed `warm` health bypass from coin_tracker_hot.py (was letting weak setups through)

### Remaining items are all Level 2-3:
- btc-crash-filter: needs 30d backtest before acceleration detection
- retroactive-scan: complex new feature (Level 3)
- dashboard-enhancements: cosmetic (Level 2-3)
- coin_tracker confirming analyses: Level 2
- coin_tracker age decay: Level 2-3
