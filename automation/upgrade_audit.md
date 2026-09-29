# Upgrade Audit Trail

## Plan: thesis-validation-system.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Track MFE after each trade to validate thesis. Boost re-entry scores when thesis was validated. Override cooldowns when setup improves.
- **Difficulty:** Level 3 (HARD) — new DB columns, score formula changes, cooldown override logic, MFE integration
- **Value:** HIGH — turns 98.6% signal expiry into executed trades on validated setups
- **Status:** NOT IMPLEMENTED
- **Reason:** No TVS_ENABLED, no thesis_validated column in signal_outcomes. Complex multi-file change requiring DB migration, signal_compactor.py score formula, cooldown override logic, and MFE integration from position_manager.py.

## Plan: chop-v2-spec.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Per-coin trend classification (0-100 score), score-based signal routing, chop-specific exit module (CHOP_TRAIL, CHOP_KILL).
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — get_coin_trend_score exists, but should_trade_signal_v2 and chop_exit.py not built
- **Value:** HIGH — fixes <2h trades -$281.92% PnL in NEUTRAL, fixes cut-loser-CL-T1 -$505.32%
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** get_coin_trend_score() exists in chop_detector.py. But: should_trade_signal_v2() not implemented, chop_exit.py not created, chop exit config not in hermes_constants.py, score-based routing multipliers not in signal_compactor.py.

## Plan: 2026-09-23_regime-based-signal-fixes.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Block LONG when linreg=LEAN_BEAR, block accel-300 SHORT in RECOVERY, disable pullback-entry- SHORT.
- **Difficulty:** Level 1 (EASY) — config changes and simple condition blocks
- **Value:** HIGH — prevents 0% WR trades in bad conditions
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** All 3 fixes confirmed in code: LEAN_BEAR LONG block in signal_compactor.py, accel-300 RECOVERY block, pullback-entry- MINUS_ENABLED=False.

## Plan: 2026-09-23_emergency-winrate-fix.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Lower SHORT_RSI_FLOOR 50→40, disable loser signals, add oversold SHORT guard, add continuum bullish SHORT penalty.
- **Difficulty:** Level 1 (EASY) — config changes
- **Value:** HIGH — unblocks SHORT in RSI 40-50 sweet spot
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** SHORT_RSI_FLOOR=40, trend_purity disabled, pullback-entry disabled, oversold guard active, bullish SHORT penalty in signal_compactor.py.

## Plan: continuum-integration-spec.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Wire continuum oscillator phases, market phases, volume regime, z-score, wyckoff into signal scoring.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — multiple integration points in signal_compactor.py
- **Value:** MEDIUM-HIGH — faster regime detection, better direction alignment
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** LEAN_BEAR LONG block exists. But: phase boost (phase>=3 → 1.3x), market_phase boost, volume_regime boost, zscore_tier boost, wyckoff_phase filter, phase 6 auto-approve all NOT implemented.

## Plan: pump-chain-v5-spec.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Add velocity filter (30m > -0.3%) and continuum oscillator filter (block bottoming/flat) to pump-chain.
- **Difficulty:** Level 2 (MEDIUM) — signal file changes
- **Value:** HIGH — pump-chain+ 51.9% WR → estimated 90%+ with filters
- **Status:** NOT IMPLEMENTED
- **Reason:** No velocity filter in pump_chain_long.py. No continuum oscillator filter checking wave_phase/momentum_state from signal metadata.

## Plan: trade-watchdog-spec.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Autonomous trade monitor with profit lock, regime alignment, stale trade detection, auto-execution.
- **Difficulty:** Level 3 (HARD) — new system with dashboard, API, systemd
- **Value:** MEDIUM — proactive trade management
- **Status:** EXISTS (trade_watchdog.py) — needs verification of completeness

## Plan: structural-awareness-overhaul.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Wire existing systems (coin_tracker_analysis, sl_zones, continuum_oscillator) into a structural bias engine, entry optimizer, proactive positioner.
- **Difficulty:** Level 4 (EPIC) — 3 new files, multiple integration points
- **Value:** MEDIUM — structural awareness, but high complexity risk
- **Status:** NOT IMPLEMENTED
- **Reason:** structural_bias.py, entry_optimizer.py, proactive_positioner.py not created. High risk of over-engineering.

## Plan: pump-catching-and-exit-optimization.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Block chop, catch pumps, ride winners. BTC Timing Guard, pump-chain velocity, PM trail widening, cut-loser tightening.
- **Difficulty:** Level 1-2 (EASY-MEDIUM)
- **Value:** MEDIUM-HIGH
- **Status:** MOSTLY IMPLEMENTED
- **Reason:** BTC Timing Guard raised to 1.0% ✅, cut-loser tightened to -0.50% ✅, time block extended to 09:00 ✅. NOT done: pump-chain velocity filter, pump_flow_engine velocity raise, PM trail widening, BTC breakout signal.

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Implement continuum oscillator as confidence multiplier system with shadow mode → validation → live.
- **Difficulty:** Level 1 (EASY) — flip OSCILLATOR_MULT_ENABLED to True
- **Value:** MEDIUM — multipliers already defined, just needs activation
- **Status:** IN SHADOW MODE
- **Reason:** OSCILLATOR_MULTS defined in hermes_constants.py. OSCILLATOR_MULT_ENABLED = False (shadow mode). Shadow logging may or may not be wired in signal_compactor.py.

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-29 17:00
- **Core request:** Exit system fixes, signal kills, regime gating, token management, speed filter, time-of-day.
- **Difficulty:** Level 1 (EASY) — config changes
- **Value:** HIGH — estimated +$4.21/7d
- **Status:** ✅ MOSTLY IMPLEMENTED
- **Reason:** pullback-entry- exit changed to ATR ✅, ema300-dip-long killed ✅, ENA blacklisted ✅, cut-loser tightened ✅, speed threshold added ✅, time block extended ✅. All key fixes done.
