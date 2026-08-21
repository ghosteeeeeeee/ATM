# Upgrade Audit Trail

**Last scanned:** 2026-08-21 05:50

---

## Plan: conf-filter-plan.md
- **Date scanned:** 2026-08-19
- **Core request:** Block confidence >= 90 trades (48.7% WR, -$1.45) + block 01-06 UTC (39.8% WR, -$1.34)
- **Difficulty:** Level 1
- **Value:** HIGH — turns losing system into break-even (+$2.22 combined)
- **Status:** IMPLEMENTED
- **Reason:** Added CONF_FILTER_MAX=89 and TIME_BLOCK 01-06 UTC to hermes_constants.py. Early-return in _score_signal(). Expected: 326T → 152T, WR 51.8% → 59.2%, PnL -$1.37 → +$0.85.

## Plan: coin_tracker_setup_improvements.md
- **Date scanned:** 2026-08-19
- **Core request:** Fix coin_tracker_hot signal (42.4% WR) with regime gate, confirmations, MIN_COMPOSITE raise
- **Difficulty:** Level 2
- **Value:** LOW — coin_tracker_hot is KILLED (disabled 2026-08-17), fixes are theoretical
- **Status:** SKIPPED
- **Reason:** Signal killed after 42.4% WR. All 3 flags False in NEVER_REENABLE_FLAGS. Fixes only relevant if signal is re-enabled, which requires new testing first.

## Plan: 2026-08-12_directional-outcome-tracker-spec.md
- **Date scanned:** 2026-08-18
- **Core request:** Real-time regime shift detector using trade outcomes as leading indicator
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Component 1 (Signal Gate), Component 2 (Position Shield), Component 3 (Recovery) all live. Velocity tiers, integral, hysteresis, direction lock all deployed.

## Plan: 2026-08-13_weather-vane-v2-spec.md
- **Date scanned:** 2026-08-18
- **Core request:** Autopilot-inspired improvements: hysteresis, derivative, integral, off-course alarm, direction lock
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** All active layers deployed (hysteresis, derivative, integral, off-course alarm, direction lock). Gain scheduling and watchdog skipped (YAGNI).

## Plan: 2026-08-13_weather-vane-v3-spec.md
- **Date scanned:** 2026-08-18
- **Core request:** Z-Score + Acceleration filter based on surfing.md quadrants
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** `get_zscore_accel_penalty()` live in signal_compactor.py. ZSCORE_ACCEL_* params in hermes_constants.py. CEO backtested — 52pt WR gap between best/worst quadrants.

## Plan: 2026-08-15_weather-vane-v4-tide-detection.md
- **Date scanned:** 2026-08-18
- **Core request:** BTC 3h momentum + SHORT WR confirmation for tide detection
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** `get_tide_penalty()` live in signal_compactor.py. TIDE_* params in hermes_constants.py. BTC momentum is fastest lagging indicator (3h shift window).

## Plan: 2026-08-15_weather-vane-v5-volatility-floor.md
- **Date scanned:** 2026-08-18
- **Core request:** Filter out low-volatility entries (no energy = no trade)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** `check_volatility_floor()` live in signal_compactor.py. VOL_FLOOR_* params in hermes_constants.py. CEO tuned threshold to 0.15% (STARVATION FIX).

## Plan: r2-trend-long-trailing-sl-tuning.md
- **Date scanned:** 2026-08-18
- **Core request:** Widen trailing SL from 0.80% to 2.00% for trend signals
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** TRAILING_DISTANCE_PCT = 0.0200 (2.00%) confirmed in hermes_constants.py. Accel filter (R2_TREND_LONG_MAX_ACCEL=0.005) added. Stale block bug fixed.

## Plan: progressive-context-shaping-spec.md
- **Date scanned:** 2026-08-18
- **Core request:** CURRENT.md + contextmap.md for agent session continuity
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** CURRENT.md exists and maintained by CEO. contextmap.md (signal registry map) exists with 62 signals mapped. All components delivered.

## Plan: coin_tracker_analysis_expansion.md
- **Date scanned:** 2026-08-18
- **Core request:** Expand coin_tracker into signal generator (Phase 2: coin_tracker_signal)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** KILLED (signal tested, 42.4% WR -$0.42/7d, in NEVER_REENABLE_FLAGS)
- **Reason:** Phase 2 EXISTS as `signals/coin_tracker_hot.py`. Tested and killed 2026-08-17. ct-hot+ 35% WR, ct-hot- 0% WR. MIN_COMPOSITE raised to 75 during testing but signal still underperformed. All 3 flags (COIN_TRACKER_HOT_ENABLED, _PLUS, _MINUS) set False.

## Plan: atr-spike-signal-build.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Build ATR Spike signal v5 — catch staged moves from ATR compression with quality gates
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** `scripts/signals/atr_spike.py` exists and is live (ATR_SPIKE_ENABLED=True). Quality gates (trend, EMA proximity, volatility, regime) all in place. Backtested 83% WR raw, 78.5% with gates.

## Plan: atr-spike-backtest-results.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Backtest results and token quality ratings for ATR spike signal
- **Difficulty:** Level 1 (analysis only)
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Backtest complete. Signal live. Token tiers rated (WCT/IMX/IO/W = Tier 1).

## Plan: imx-spike-detection.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Detect ATR compression → breakout on IMX (parent plan for atr_spike)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Parent plan for atr_spike signal. All components delivered.

## Plan: sl-tuning.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Tune SL for ATR spike signal — 0.75% recommended, two signal modes
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** ANALYSIS COMPLETE
- **Reason:** 0.75% SL already implemented in atr_spike.py. Two-mode recommendation (breakout + trend) is a future enhancement, not a bug fix. No code changes needed.

## Plan: 2026-08-19_short-bias-fix.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Fix short bias — revert EMA penalty (dead code), keep STANDALONE_BYPASS
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** EMA penalty reverted (not found in tl_break.py). STANDALONE_BYPASS retained for tl_break_long/short. Trend Alignment confirmed as primary filter (counter-trend SHORTs = 26% WR).

## Plan: confidence-calibration-plan.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Fix non-monotonic confidence curve — proposed fix rejected
- **Difficulty:** Level 2
- **Value:** LOW
- **Status:** INVESTIGATION COMPLETE (no action needed)
- **Reason:** CONF_FILTER_MAX=89 already blocks raw conf ≥ 90. Non-monotonic curve is noise (15 trades per extreme tier, CIs overlap 50%). Proposed fix was redundant and risky. Highest ROI: per-signal-type quality analysis.

## Plan: copy-trader-evolution-spec.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Per-trader performance tracking + trader exit correlation
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** `trader_performance` table exists in hl_copy_db.py. `check_trader_exits()` and `update_trader_performance()` exist in hl_fill_monitor.py. COPY_TRADE_EXIT_ENABLED=True. Bypass `'hl_copy_trader'` added to PROFIT_MONSTER_BYPASS_SIGNALS.

## Plan: retroactive-scan-delayed-entry.md
- **Date scanned:** 2026-08-21 05:50
- **Core request:** Secondary scan for missed breakouts — retroactive signals with lower confidence
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** 0 RETRO_ constants in hermes_constants.py. Nothing in breakout_engine.py. This is the only major plan still pending. Requires ~200 LOC in breakout_engine.py + constants + hotset writer.
