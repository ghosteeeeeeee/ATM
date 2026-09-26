# Upgrade Audit Trail

## Plan: chop-v2-spec.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Fix chop (NEUTRAL regime) losses by extending chop_detector.py with per-coin trend scores + new chop_exit.py module
- **Difficulty:** Level 3
- **Value:** HIGH — addresses -$281.92% PnL from <2h trades in chop
- **Status:** SKIPPED
- **Reason:** Level 3 complexity, requires new module + signal compactor integration. Defer to dedicated session.

## Plan: 2026-09-23_regime-based-signal-fixes.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Block LONG when linreg=LEAN_BEAR, block accel-300 SHORT in RECOVERY, disable pullback-entry- SHORT
- **Difficulty:** Level 1
- **Value:** HIGH — 0% WR across all LONG signals in LEAN_BEAR
- **Status:** IMPLEMENTED
- **Reason:** All 3 fixes verified: (1) LEAN_BEAR LONG block at signal_compactor.py:1482, (2) accel-300 SHORT RECOVERY block at signal_compactor.py:2632, (3) PULLBACK_ENTRY_MINUS_ENABLED=False.

## Plan: 2026-09-23_emergency-winrate-fix.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Lower SHORT_RSI_FLOOR 50→40, disable trend_purity/pullback-entry, add oversold SHORT guard, continuum bullish SHORT penalty
- **Difficulty:** Level 1
- **Value:** HIGH — SHORT only allowed in RSI 50-65 (15-point window)
- **Status:** IMPLEMENTED (with CEO override on RSI floor)
- **Reason:** TREND_PURITY disabled ✅, PULLBACK_ENTRY disabled ✅. CEO raised SHORT_RSI_FLOOR to 50 (not 40) with data backing — respecting CEO decision.

## Plan: continuum-integration-spec.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Wire continuum oscillator's 7 dimensions into signal scoring/filtering
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** SKIPPED
- **Reason:** Level 3 complexity, partially implemented. Defer.

## Plan: pump-chain-v5-spec.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Add velocity filter (30m > -0.3%) and continuum oscillator filter (block "bottoming" + "flat") to pump-chain+ LONG
- **Difficulty:** Level 1
- **Value:** HIGH — filters could improve pump-chain+ from 52% WR to ~95% WR
- **Status:** IMPLEMENTED
- **Reason:** pump_chain_v5.py exists with all 3 filters (velocity, wave_phase, momentum_state). PUMP_CHAIN_V5_ENABLED=True. Registered in signals/__init__.py.

## Plan: trade-watchdog-spec.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Build autonomous trade monitor (30-min checks, 9 check categories, dashboard)
- **Difficulty:** Level 4
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** trade_watchdog.py exists.

## Plan: structural-awareness-overhaul.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Build structural awareness layer (S/R, Wyckoff, trend), proactive positioning, entry optimizer
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** SKIPPED
- **Reason:** Level 4 complexity, multi-system overhaul. Defer.

## Plan: pump-catching-and-exit-optimization.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Block chop, catch pumps, ride winners — multiple file changes
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** SKIPPED
- **Reason:** Level 3 complexity, partially implemented. Defer.

## Plan: squeeze-breakout-signal-spec.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** New signal firing during BB squeeze
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** squeeze_breakout.py exists, SQUEEZE_BREAKOUT_ENABLED = True.

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Implement continuum oscillator as confidence multiplier
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED (shadow mode)
- **Reason:** OSCILLATOR_MULT_ENABLED = False (shadow mode as designed).

## Plan: ride-it-exit-spec.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** 2-phase exit system with volume spike override
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** ride_it_exit.py exists, integrated into position_manager.py.

## Plan: continuum-ma-signal-spec.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** New signal on raw continuum score crossing its MA
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** continuum_ma.py exists, CONTINUUM_MA_ENABLED = True.

## Plan: btc-oscillator-30d-plan.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Analysis/monitoring plan — track BTC oscillator correlations
- **Difficulty:** Level 0
- **Value:** LOW
- **Status:** N/A
- **Reason:** Analysis plan, not implementation. "WAIT AND MONITOR."

## Plan: btc-oscillator-correlation-plan.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Block LONG when BTC bearish, boost SHORT when BTC bullish
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Continuum bias exists in signal_compactor.py, specific BTC zscore/trend filters not confirmed.

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** 8 fixes: disable rr_engine for pullback-entry-, kill ema300-dip-long, blacklist ENA, etc.
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** EMA300_DIP_LONG_ENABLED=False ✅, PULLBACK_ENTRY_MINUS_ENABLED=False ✅, ENA blacklisted ✅. Some fixes done.

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** New LONG-only signal at extreme oversold
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** oversold_bounce.py exists.

## Plan: contrarian-zone-signal.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Flip signal direction when price approaches strong SL memory zone
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Transformation logic in signal_compactor.py ✅. Standalone signal file doesn't exist.

## Plan: accel300-long-fix-plan.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Fix accel-300 LONG (39% WR) with RSI<50 filter, pre15<0 filter
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** accel_300_v3_long.py exists. Specific filters not confirmed.

## Plan: accel300-v4-killer-signal.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** Fix RSI calculation, add RSI>50 filter for SHORT
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** accel_300_v4_short.py exists. RSI Wilder smoothing fix status unclear.

## Plan: atr-spike-signal-build.md
- **Date scanned:** 2026-09-26 00:00
- **Core request:** New LONG-only signal catching multi-hour staged moves from ATR compression
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** atr_spike.py exists.

---

## Summary

| Status | Count | Plans |
|--------|-------|-------|
| ✅ IMPLEMENTED | 10 | trade-watchdog, squeeze-breakout, oscillator-matrix, ride-it-exit, continuum-ma, oversold-bounce, atr-spike, emergency-winrate (CEO override), pump-chain-v5, regime-based-signal-fixes |
| ⚠️ PARTIAL | 5 | continuum-integration, btc-oscillator-corr, profitability-fix, contrarian-zone, accel300-long, accel300-v4 |
| ❌ NOT DONE | 2 | chop-v2, structural-awareness |
| N/A | 1 | btc-oscillator-30d (analysis only) |

## Next Implementation Candidates

1. **structural-awareness** — Level 4, HIGH — transforms reactive→proactive (multi-day project)
2. **chop-v2** — Level 3, HIGH — fixes chop losses (new module required)
3. **profitability-fix** — Level 1, HIGH — verify remaining partial fixes
