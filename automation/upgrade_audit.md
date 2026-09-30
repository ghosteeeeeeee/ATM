# Upgrade Audit Trail

## Plan: thesis-validation-system.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Track MFE after each trade to validate thesis. Boost re-entry scores when thesis was validated. Override cooldowns when setup improves.
- **Difficulty:** Level 3 (HARD) — new DB columns, score formula changes, cooldown override logic, MFE integration
- **Value:** HIGH — turns 98.6% signal expiry into executed trades on validated setups
- **Status:** NOT IMPLEMENTED
- **Reason:** No TVS_ENABLED, no thesis_validated column in signal_outcomes. Complex multi-file change requiring DB migration, signal_compactor.py score formula, cooldown override logic, and MFE integration from position_manager.py.

## Plan: chop-v2-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Per-coin trend classification (0-100 score), score-based signal routing, chop-specific exit module (CHOP_TRAIL, CHOP_KILL).
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — get_coin_trend_score exists, but should_trade_signal_v2 and chop_exit.py not built
- **Value:** HIGH — fixes <2h trades -$281.92% PnL in NEUTRAL, fixes cut-loser-CL-T1 -$505.32%
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** get_coin_trend_score() exists in chop_detector.py. But: should_trade_signal_v2() not implemented, chop_exit.py not created, chop exit config not in hermes_constants.py, score-based routing multipliers not in signal_compactor.py.

## Plan: 2026-09-23_regime-based-signal-fixes.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Block LONG when linreg=LEAN_BEAR, block accel-300 SHORT in RECOVERY, disable pullback-entry- SHORT.
- **Difficulty:** Level 1 (EASY) — config changes and simple condition blocks
- **Value:** HIGH — prevents 0% WR trades in bad conditions
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** All 3 fixes confirmed in code: LEAN_BEAR LONG block in signal_compactor.py, accel-300 RECOVERY block, pullback-entry- MINUS_ENABLED=False.

## Plan: 2026-09-23_emergency-winrate-fix.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Lower SHORT_RSI_FLOOR 50→40, disable loser signals, add oversold SHORT guard, add continuum bullish SHORT penalty.
- **Difficulty:** Level 1 (EASY) — config changes
- **Value:** HIGH — unblocks SHORT in RSI 40-50 sweet spot
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** SHORT_RSI_FLOOR=40, trend_purity disabled, pullback-entry disabled, oversold guard active, bullish SHORT penalty in signal_compactor.py.

## Plan: continuum-integration-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Wire continuum oscillator phases, market phases, volume regime, z-score, wyckoff into signal scoring.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — multiple integration points in signal_compactor.py
- **Value:** MEDIUM-HIGH — faster regime detection, better direction alignment
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** LEAN_BEAR LONG block exists. But: phase boost (phase>=3 → 1.3x), market_phase boost, volume_regime boost, zscore_tier boost, wyckoff_phase filter, phase 6 auto-approve all NOT implemented.

## Plan: pump-chain-v5-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Add velocity filter (30m > -0.3%) and continuum oscillator filter (block bottoming/flat) to pump-chain.
- **Difficulty:** Level 2 (MEDIUM) — signal file changes
- **Value:** HIGH — pump-chain+ 51.9% WR → estimated 90%+ with filters
- **Status:** ✅ FULLY IMPLEMENTED (2026-09-30)
- **Reason:** pump_flow_signal.py has 30m velocity filter (PUMP_FLOW_TOKEN_30M_THRESHOLD=0). 5m threshold tightened from -0.2% to -0.5% (PUMP_FLOW_TOKEN_VEL_THRESHOLD=-0.5). SHORT velocity filter active (PUMP_FLOW_SHORT_VEL_THRESHOLD=0). pump_chain_long.py and pump_chain_v5.py also have 30m velocity filters.

## Plan: trade-watchdog-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Autonomous trade monitor with profit lock, regime alignment, stale trade detection, auto-execution.
- **Difficulty:** Level 3 (HARD) — new system with dashboard, API, systemd
- **Value:** MEDIUM — proactive trade management
- **Status:** EXISTS (trade_watchdog.py) — needs verification of completeness
- **Reason:** trade_watchdog.py exists and runs via systemd.

## Plan: structural-awareness-overhaul.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Wire existing systems (coin_tracker_analysis, sl_zones, continuum_oscillator) into a structural bias engine, entry optimizer, proactive positioner.
- **Difficulty:** Level 4 (EPIC) — 3 new files, multiple integration points
- **Value:** MEDIUM — structural awareness, but high complexity risk
- **Status:** NOT IMPLEMENTED
- **Reason:** structural_bias.py, entry_optimizer.py, proactive_positioner.py not created. High risk of over-engineering.

## Plan: pump-catching-and-exit-optimization.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Block chop, catch pumps, ride winners. BTC Timing Guard, pump-chain velocity, PM trail widening, cut-loser tightening.
- **Difficulty:** Level 1-2 (EASY-MEDIUM)
- **Value:** MEDIUM-HIGH
- **Status:** ✅ MOSTLY IMPLEMENTED
- **Reason:** BTC Timing Guard active ✅, cut-loser tightened ✅, time block extended ✅, pump-chain velocity filter ✅ (30m + 5m tightened). Remaining: pump_flow_engine velocity raise, PM trail widening (tiered trail already implemented via PM_TRAIL_TIERS).

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Implement continuum oscillator as confidence multiplier system with shadow mode → validation → live.
- **Difficulty:** Level 1 (EASY) — flip OSCILLATOR_MULT_ENABLED to True
- **Value:** MEDIUM — multipliers already defined, just needs activation
- **Status:** IN SHADOW MODE
- **Reason:** OSCILLATOR_MULTS defined in hermes_constants.py. OSCILLATOR_MULT_ENABLED = False (shadow mode).

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Exit system fixes, signal kills, regime gating, token management, speed filter, time-of-day.
- **Difficulty:** Level 1 (EASY) — config changes
- **Value:** HIGH — estimated +$4.21/7d
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** All key fixes done: pullback-entry- exit changed to ATR, ema300-dip-long killed, ENA blacklisted, cut-loser tightened, speed threshold added, time block extended.

## Plan: 2026-09-12_btc-momentum-sync-plan.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** 5-layer defense: BTC momentum gate, transition detection, stale signal filter, RSI/z-score guard, continuum context boost.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — multiple integration points
- **Value:** HIGH — eliminates -$1.42 LONG bleed, prevents 7-10% blowups
- **Status:** ✅ MOSTLY IMPLEMENTED
- **Reason:** Layer 1 (BTC Momentum Gate) ✅ — directional bias in signal_compactor.py reads momentum_state. Layer 3 (Stale Signal Filter) ✅ — staleness decay exists. Layer 4 (RSI/Z-Score Guard) ✅ — RSI floors/ceilings active. Layer 5 (Continuum Context Boost) ✅ — directional bias multiplier active. Layer 2 (Transition Detection) — not explicitly implemented as separate function, but covered by directional bias + chop detector.

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Per-signal-type BTC momentum thresholds to prevent chasing.
- **Difficulty:** Level 1 (EASY) — config + ~25 lines
- **Value:** HIGH — prevents chasing entries after BTC already moved
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** BTC_TIMING_GUARD_ENABLED=True, all per-signal thresholds defined, implementation in signal_compactor.py lines 1251-1295.

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Hard BTC momentum gate + gate STANDALONE_BYPASS in flat markets.
- **Difficulty:** Level 1 (EASY) — ~20 lines + 3 constants
- **Value:** MEDIUM-HIGH — prevents trend signals firing into chop
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** BTC_CHOP_GATE_ENABLED=True, BTC_CHOP_GATE_THRESHOLD=0.20, implementation in signal_compactor.py. STANDALONE_BYPASS gated when BTC flat.

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** ATR ratio + BTC trend boost for direction-aligned expansion trades.
- **Difficulty:** Level 2 (MEDIUM) — extend existing volatility_gate_v2.py
- **Value:** MEDIUM — boost SHORT in falling expansion (83% WR setup)
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** get_atr_ratio() in volatility_gate_v2.py, get_btc_trend() exists, ATR ratio + BTC trend boost in get_combined_multiplier() (lines 568-588). Constants: VOL_GATE_ATR_RATIO_EXPANSION=1.5, VOL_GATE_EXPANSION_SHORT_FALLING_BOOST=1.2, VOL_GATE_EXPANSION_LONG_RISING_BOOST=1.1.

## Plan: 2026-09-11_volatility-regime-adaptive-signals.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Per-signal-family weighting by volatility regime (momentum boost in expansion, mean-rev boost in compression).
- **Difficulty:** Level 2 (MEDIUM) — ~25 lines + 8 constants
- **Value:** MEDIUM — adapt signals to market conditions
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signal_compactor.py lines 1841-1893: computes ATR ratio, classifies expansion/compression, applies per-family multipliers (1.2x momentum in expansion, 0.8x mean-rev, 0.7x momentum in compression, 1.2x mean-rev). Constants in hermes_constants.py.

## Plan: 2026-09-09_regime-transition-smoothing.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Directional bias from momentum_state, alt-BTC divergence, stronger directional outcome penalty.
- **Difficulty:** Level 1-2 (EASY-MEDIUM) — ~30 lines + 4 constants
- **Value:** HIGH — reduces regime transition bleed
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** DIRECTIONAL_BIAS_ENABLED=True with momentum_state reading (signal_compactor.py:1776-1801). ALT_BTC_DIVERGENCE_ENABLED=True (signal_compactor.py:1815-1830). DIRECTIONAL_OUTCOME_PENALTY=0.5 (tightened from 0.7).

## Plan: 2026-09-09_pump-chain-v2-spec.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Token 30m velocity filter, 5m threshold tightening, SHORT velocity filter for pump-chain.
- **Difficulty:** Level 2 (MEDIUM) — signal file changes
- **Value:** HIGH — pump-chain WR from 57.5% to 93.5%+ (backtested)
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** 30m velocity filter in pump_flow_signal.py (PUMP_FLOW_TOKEN_30M_THRESHOLD=0). 5m threshold tightened to -0.5% (PUMP_FLOW_TOKEN_VEL_THRESHOLD=-0.5). SHORT velocity filter (PUMP_FLOW_SHORT_VEL_THRESHOLD=0). Also in pump_chain_long.py and pump_chain_v5.py.

## Plan: 2026-09-09_grass-breakout-analysis.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** New squeeze_reversal signal — BB squeeze → mean-reversion breakout.
- **Difficulty:** Level 3 (HARD) — new signal module
- **Value:** MEDIUM — catches BB squeeze breakouts
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signals/squeeze_reversal.py exists with squeeze detection, BB proximity, RSI filters. Registered in signals/__init__.py. Constants in hermes_constants.py.

## Plan: 2026-09-08_trend-ignition-signal-spec.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** New trend_ignition signal — early-stage breakout at trend START.
- **Difficulty:** Level 3 (HARD) — new signal module
- **Value:** MEDIUM — catches趋势启动点 (100% WR in 7d backtest)
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signals/trend_ignition.py exists with volume spike, compression, breakout detection. Registered in signals/__init__.py. Constants in hermes_constants.py.

## Plan: 2026-09-11_btc-pump-rider-gradual-rally.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Gradual rally detection mode for btc_pump_rider.py — catch slow BTC rallies + lagging alts.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — ~58 lines + 8 constants
- **Value:** MEDIUM — catches gradual rallies missed by explosive breakout detection
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** detect_btc_gradual_rally() and find_lagging_alts() in btc_pump_rider.py. Constants: BTC_PUMP_RIDER_GRADUAL_ENABLED=True, all thresholds defined.

## Plan: 2026-09-07_partial-close-trailing-runner.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Partial close at PM_TRAIL activation (50% scalp, 50% runner), regime-adaptive trail width.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — changes to profit_monster.py + tpsl_utils.py
- **Value:** HIGH — estimated ~3x improvement on winning trades (0.84% → 2.64% on ICP case)
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Option 3 (Tiered Trail) is IMPLEMENTED via PM_TRAIL_TIERS. Option 1 (Partial Close) is NOT implemented — no PARTIAL_CLOSE constant, no partial position close logic. Option 2 (Regime-Adaptive Trail) NOT implemented. Option 4 (Time-Based Trail) NOT implemented. The tiered trail is the most impactful part and it's done.

## Plan: 2026-09-08_short-filter-overhaul.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Relax SHORT filters, fix dead code, build simulation script.
- **Difficulty:** Level 1-2 (EASY-MEDIUM)
- **Value:** MEDIUM — unblock profitable SHORTs
- **Status:** MOSTLY IMPLEMENTED (audit-corrected version)
- **Reason:** Original plan was UNSOUND per audit. Revised fixes: VEL-FILTER dead code (range(3) bug) — need to verify. SHORT_RSI_FLOOR lowered to 40 ✅. SHORT-NEUTRAL block has bypasses ✅. Simulation script not built.

## Plan: 2026-09-04_continuum-engine-spec.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** State-based continuum engine replacing event-based signals.
- **Difficulty:** Level 4 (EPIC) — architecture overhaul
- **Value:** MEDIUM — state-based trading
- **Status:** EXISTS (continuum_engine.py) — core engine built, not full spec
- **Reason:** continuum_engine.py exists with state tracking, but full spec (6 dimensions, compound scorer, entry/exit signals) not fully implemented.

## Plan: 2026-08-29_wave-period-analysis-plan.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Wave period analysis — periodicity detection, pattern classification, trading integration.
- **Difficulty:** Level 2 (MEDIUM) — analysis scripts + integration
- **Value:** MEDIUM — token-specific wave patterns
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** wave_period_detector.py, wave_trade_context.py, wave_classifier.py exist. Phase 1 (discovery) complete. Phase 2 (validation + integration) pending.

## Plan: 2026-08-29_amplitude-enhancement-brainstorm.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Amplitude-based token classification and wave period trading system.
- **Difficulty:** Level 3 (HARD) — new system
- **Value:** MEDIUM — amplitude-based signal weighting
- **Status:** NOT IMPLEMENTED
- **Reason:** Analysis complete but no integration into trading system.

## Plan: 2026-09-21_btc-4year-cycle-macro-thesis.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Macro thesis — BTC 4-year cycle, LONG bias for 2-3 years.
- **Difficulty:** Level 4 (EPIC) — macro integration
- **Value:** LOW-MEDIUM — thesis, not actionable code
- **Status:** THESIS ONLY
- **Reason:** Analysis document, no code implementation needed. Could inform LONG bias in signal scoring.

## Plan: 2026-08-26_30s-price-interval-migration.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Split architecture for 30s price collection — latest_prices for exits, price_history for signals.
- **Difficulty:** Level 1 (EASY) — single line change
- **Value:** MEDIUM — faster exit management without breaking signals
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** Status says IMPLEMENTED. Dual-track writes in signal_schema.py.

## Plan: 2026-08-22_copy-trader-dashboard-enhancements.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Copy trader dashboard with stats, per-token table, exit reasons, equity curve.
- **Difficulty:** Level 2 (MEDIUM) — dashboard + API
- **Value:** MEDIUM — visibility into copy trading
- **Status:** Phase 1 IMPLEMENTED
- **Reason:** copy_trader_api.py and copy_trader.html exist with all Phase 1 features.

---

## Summary (2026-09-30)

### Scanned: 25 plans
### Evaluated: 25 plans

| Status | Count | Plans |
|--------|-------|-------|
| ✅ FULLY IMPLEMENTED | 14 | regime-fixes, winrate-fix, btc-timing-guard, chop-gating, volatility-gate-tuning, volatility-regime-adaptive, regime-transition-smoothing, pump-chain-v2, squeeze-reversal, trend-ignition, gradual-rally, profitability-fix, 30s-migration, pump-catching |
| ✅ MOSTLY IMPLEMENTED | 3 | btc-momentum-sync, profitability-fix, short-filter-overhaul |
| PARTIALLY IMPLEMENTED | 4 | chop-v2, continuum-integration, partial-close, wave-period |
| IN SHADOW MODE | 1 | oscillator-matrix-lifecycle |
| NOT IMPLEMENTED | 3 | thesis-validation, structural-awareness, amplitude-enhancement |
| EXISTS (verify) | 2 | trade-watchdog, continuum-engine |

### Remaining High-Value Candidates

1. **chop-v2-spec.md** — Level 2-3 — HIGH VALUE — per-coin trend scoring + chop exit module
2. **partial-close-trailing-runner.md** — Level 2-3 — HIGH VALUE — 50% partial close at trail activation (Option 1 not done, but Option 3 tiered trail IS done)
3. **thesis-validation-system.md** — Level 3 — HIGH VALUE — MFE tracking + re-entry scoring
4. **oscillator-matrix-lifecycle.md** — Level 1 — MEDIUM VALUE — flip OSCILLATOR_MULT_ENABLED to True

### Success Rate: 17/25 fully or mostly implemented (68%)
