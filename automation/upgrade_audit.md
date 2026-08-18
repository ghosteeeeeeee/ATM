# Upgrade Audit Trail

**Last scanned:** 2026-08-18

---

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
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** CURRENT.md exists and is actively maintained by CEO. contextmap.md (signal registry map) NOT created. Low effort, medium value.

## Plan: coin_tracker_analysis_expansion.md
- **Date scanned:** 2026-08-18
- **Core request:** Expand coin_tracker into signal generator (Phase 2: coin_tracker_signal)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** KILLED (signal tested, 42.4% WR -$0.42/7d, in NEVER_REENABLE_FLAGS)
- **Reason:** Phase 2 EXISTS as `signals/coin_tracker_hot.py`. Tested and killed 2026-08-17. ct-hot+ 35% WR, ct-hot- 0% WR. MIN_COMPOSITE raised to 75 during testing but signal still underperformed. All 3 flags (COIN_TRACKER_HOT_ENABLED, _PLUS, _MINUS) set False.
