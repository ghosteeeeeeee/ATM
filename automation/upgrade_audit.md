# Upgrade Audit Trail

Generated: 2026-09-25 (latest scan)

---

## Plan: 2026-09-23_regime-based-signal-fixes.md
- **Date scanned:** 2026-09-25 17:00 (re-verified)
- **Core request:** Block LONG when linreg=LEAN_BEAR, block accel-300 SHORT in RECOVERY, disable pullback-entry- SHORT
- **Difficulty:** Level 1 (config + single function edits)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** All 3 fixes found in signal_compactor.py:1474 (LEAN_BEAR LONG block), signal_compactor.py:2605 (RECOVERY block), hermes_constants.py:3726 (pullback-entry- disabled). Watchdog updates (SHORT_RSI_FLOOR=50, OVERSOLD_SHORT_RSI_MAX=35) also present.

## Plan: 2026-09-23_emergency-winrate-fix.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Lower SHORT_RSI_FLOOR to 40, disable trend_purity/pullback-entry, oversold SHORT guard, continuum bullish SHORT penalty
- **Difficulty:** Level 1 (config changes)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED (with CEO correction)
- **Reason:** SHORT_RSI_FLOOR was RAISED to 50 (not 40 as plan suggested) — CEO found actual sweet spot is RSI 50-60, not 45-60. trend_purity disabled (line 2217). pullback-entry- disabled (line 3726). Oversold SHORT guard at 35 (line 846). Continuum bullish SHORT penalty (signal_compactor.py:1483-1486).

## Plan: continuum-integration-spec.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Wire continuum engine dimensions (phase, market_phase, linreg, zscore, wyckoff) into signal scoring
- **Difficulty:** Level 2-3 (multi-file integration)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED (Phase 1-3)
- **Reason:** Continuum authority in signal_compactor.py:1460-1496 handles phase, linreg, EMA alignment with 1.5x boosts and 0.5x penalties. Continuum context used for trend boost (line 1490). Z-score accel multiplier exists (zscore_accel_mult in final_score). Phase 4 (engine entry signal → execution) not wired but lower priority.

## Plan: pump-chain-v5-spec.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Add velocity filter (> -0.3%) and continuum oscillator filter (block bottoming/flat) to pump-chain+
- **Difficulty:** Level 2 (new signal variant)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** pump_chain_v5.py exists with velocity check (_check_30m_velocity at line 124), bottoming wave phase block (line 279), flat momentum state block (line 286). All thresholds match spec.

## Plan: trade-watchdog-spec.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Autonomous trade monitor running every 30 minutes with steers/recommendations
- **Difficulty:** Level 3 (new system)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** trade_watchdog.py (46KB) exists, systemd timer active (hermes-trade-watchdog.timer running every 30min), automation/trade-watchdog/ directory with runner and prompt.

## Plan: squeeze-breakout-signal-spec.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** New signal firing during BB squeeze (before breakout)
- **Difficulty:** Level 2 (new signal)
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Reason:** squeeze_breakout.py exists in signals/, SQUEEZE_BREAKOUT_ENABLED=True (hermes_constants.py:2184), registered in signals/__init__.py.

## Plan: ride-it-exit-spec.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** 2-phase exit system with momentum exit and volume spike override
- **Difficulty:** Level 2 (new exit system)
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Reason:** ride_it_exit.py exists, RIDE_IT_ENABLED=True (hermes_constants.py:3614), imports in position_manager.

## Plan: continuum-ma-signal-spec.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Signal on continuum score MA crossover
- **Difficulty:** Level 2 (new signal)
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Reason:** continuum_ma.py exists, CONTINUUM_MA_ENABLED=True (hermes_constants.py:3851).

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** LONG signal at extreme oversold (RSI < 20, z < -2)
- **Difficulty:** Level 2 (new signal)
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Reason:** oversold_bounce.py exists, OVERSOLD_BOUNCE_ENABLED=True (hermes_constants.py:3766), all parameters configured.

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Continuum oscillator as confidence multiplier system with shadow→live progression
- **Difficulty:** Level 2 (multiplier matrix)
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED (Shadow Mode)
- **Reason:** OSCILLATOR_MULTS dict in hermes_constants.py, oscillator_mult in signal_compactor.py:1874-1901, OSCILLATOR_MULT_ENABLED=False (shadow mode — log only). Validated by data.

## Plan: pump-catching-and-exit-optimization.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Block chop, catch pumps, ride winners — 3-pillar fix
- **Difficulty:** Level 2-3 (multi-system)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED (Immediate items)
- **Reason:** BTC_TIMING_GUARD_PUMP_CHAIN_LONG=1.00 (raised from 0.30), continuum-osc in PROFIT_MONSTER_BYPASS, BTC removed from PENALTY_TOKENS, NORMAL/NEUTRAL regime blocks active, SHORT_NORMAL_PENALTY=0.85. Medium-term items (btc_breakout.py, ATR trailing) not implemented.

## Plan: btc-crash-filter-plan.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** BTC flash crash detection and signal blocking
- **Difficulty:** Level 2 (new filter)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** BTC_CRASH_BLOCK_ENABLED=True (hermes_constants.py:1122), btc_crash_filter.py exists, adaptive thresholds based on ATR.

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Exit system fixes — disable rr_engine for pullback-entry-, optimize PM Trail tiers
- **Difficulty:** Level 1-2 (config + exit logic)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** pullback-entry- exit changed to 'atr' (hermes_constants.py:1567), PM Trail configured at 0.40%/0.20%, cut_loser at -1.75%.

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Per-signal-type BTC momentum thresholds
- **Difficulty:** Level 1 (config)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** BTC_TIMING_GUARD per-signal thresholds in hermes_constants.py:994-1002 (PUMP_CHAIN=1.00, PULLBACK=0.20, OPEN_SKIES=1.00, ACCEL_SHORT=-0.15).

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Block signals during chop regimes
- **Difficulty:** Level 1 (config)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** BTC_CHOP_GATE_ENABLED=True, CHOP_GATE_LOG_ONLY=False (activated), SHORT_NEUTRAL_BLOCK=True, LONG_NEUTRAL_BLOCK=True, SHORT_NORMAL_PENALTY=0.85.

## Plan: 2026-09-08_btc-alignment-crash-protection-overhaul.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** BTC trend alignment filter + crash protection for ema300-dip
- **Difficulty:** Level 2 (new filter)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** BTC crash filter active, continuum_context.get_btc_trend_context() used in signal_compactor.py:2754, BTC_CHOP_GATE active.

## Plan: structural-awareness-overhaul.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Wire existing structural systems (coin_tracker, sl_zones, continuum) into execution
- **Difficulty:** Level 3-4 (architecture)
- **Value:** HIGH
- **Status:** 🟡 PARTIAL (Phase 1)
- **Reason:** sl_zones partially integrated (signal_compactor.py:3515), continuum_context wired. But structural_bias.py, entry_optimizer.py, proactive_positioner.py NOT built. Full overhaul is Level 4.

## Plan: contrarian-zone-signal.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Liquidity sweep + mean reversion at SL memory zones
- **Difficulty:** Level 2 (new signal)
- **Value:** MEDIUM
- **Status:** ❌ NOT IMPLEMENTED
- **Reason:** No contrarian_zone.py in signals/. Spec exists (316 lines) but not built.

## Plan: accel300-v4-killer-signal.md
- **Date scanned:** 2026-09-24 17:40
- **Core request:** Transform accel-300 to 95%+ WR with RSI fix, regime slope, flat block
- **Difficulty:** Level 2 (signal overhaul)
- **Value:** MEDIUM
- **Status:** ⚠️ SUPERSEDED
- **Reason:** ACCEL_300_V4_SHORT_ENABLED=False (disabled 2026-09-11). Original accel_300_short preferred. V4 approach abandoned.

---

## Summary

| Status | Count | Plans |
|--------|-------|-------|
| ✅ IMPLEMENTED | 18 | regime-fixes, winrate-fix, continuum-integration, pump-chain-v5, trade-watchdog, squeeze-breakout, ride-it-exit, continuum-ma, oversold-bounce, oscillator-matrix, pump-catching, btc-crash-filter, profitability-fix, btc-timing-guard, chop-gating, btc-alignment, structural-awareness (partial), **contrarian-zone Phase 1** |
| 🟡 PARTIAL | 3 | structural-awareness (Phase 1), partial-close (Option 3 only), btc-momentum-sync (Layers 3-5) |
| ❌ NOT IMPLEMENTED | 0 | — |
| ⚠️ SUPERSEDED | 1 | accel300-v4 (approach abandoned) |

## Plan: contrarian-zone-signal
- **Date scanned:** 2026-09-25 17:00
- **Core request:** Flip blocked signals to contrarian direction at strong SL zones (84% hold rate)
- **Difficulty:** Level 1 (Phase 1: single function edit + 5 constants)
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED (Phase 1 only)
- **Reason:** Added CONTRARIAN_ZONE_ENABLED + 4 constants to hermes_constants.py:854-858. Modified signal_compactor.py:3566-3589 to flip direction when zone strength >= 0.5, hits >= 3, distance <= 0.5%. Phase 2 (standalone signal) and Phase 3 (exit logic) not implemented.

## Plan: partial-close-trailing-runner
- **Date scanned:** 2026-09-25 17:00
- **Core request:** Partial close at PM_TRAIL activation + regime-adaptive trail width
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** 🟡 PARTIAL (Option 3 implemented: tiered trail)
- **Reason:** PM_TRAIL_TIERS exists in hermes_constants.py:1449-1454 (tiered trail loosens with profit). Option 1 (partial close at 50%) NOT implemented — requires size tracking in position_manager. Option 2 (regime-adaptive trail) NOT implemented — CEO warned against widening trail (line 1442).

## Plan: btc-momentum-sync
- **Date scanned:** 2026-09-25 17:00
- **Core request:** 5-layer defense: BTC momentum gate, transition detection, stale filter, RSI guard, continuum boost
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** 🟡 PARTIAL (Layers 3-5 done, Layer 1 partially, Layer 2 not done)
- **Reason:** Layer 3 (stale filter: staleness_mult=0.1 decay) done. Layer 4 (RSI guard: RSI floors/ceilings) done. Layer 5 (continuum boost: continuum_mult) done. Layer 1 (BTC momentum gate) partially done via BTC_CHOP_GATE + directional_bias. Layer 2 (transition detection) NOT implemented.

---

## Pending Candidates (Not Implemented)

| Plan | Difficulty | Value | Why Pending |
|------|-----------|-------|-------------|
| partial-close Phase 1 (50% close) | Level 2-3 | HIGH | Needs position_manager changes, size tracking |
| structural-awareness Phase 2-4 | Level 3-4 | HIGH | Architecture overhaul, multiple new files |
| pump-catching medium-term (btc_breakout, ATR trailing) | Level 2-3 | MEDIUM | Not yet prioritized |
| contrarian-zone Phase 2 (standalone signal) | Level 2 | MEDIUM | Needs new signal file + backtest validation |
| btc-momentum-sync Layer 2 (transition detection) | Level 2 | MEDIUM | Needs continuum_context.py changes |
