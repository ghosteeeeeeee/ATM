# Upgrade Audit Trail

## Plan: chop-v2-spec.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Per-coin trend scoring + chop-specific exits to fix -$281.92% loss from <2h trades in NEUTRAL regime
- **Difficulty:** Level 3
- **Value:** HIGH — addresses biggest loss source
- **Status:** PENDING
- **Reason:** Large architecture change (new chop_exit.py, extend chop_detector.py). Requires careful testing.

## Plan: 2026-09-23_regime-based-signal-fixes.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Block LONG when LEAN_BEAR, block accel-300 SHORT in RECOVERY, disable pullback-entry- SHORT
- **Difficulty:** Level 1
- **Value:** HIGH — prevents 0% WR trades
- **Status:** IMPLEMENTED
- **Reason:** All 3 fixes already in codebase (signal_compactor.py:1482, :2632-2635, PULLBACK_ENTRY_MINUS_ENABLED=False)

## Plan: 2026-09-23_emergency-winrate-fix.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Lower SHORT_RSI_FLOOR to 40, disable trend_purity/pullback-entry, oversold SHORT guard
- **Difficulty:** Level 1
- **Value:** HIGH — stops bleeding from oversold SHORT entries
- **Status:** IMPLEMENTED
- **Reason:** SHORT_RSI_FLOOR kept at 50 (CEO decision — actual sweet spot is 50-60). Trend_purity and pullback-entry disabled. Oversold SHORT guard (RSI < 35) implemented via OVERSOLD_SHORT_RSI_MAX.

## Plan: continuum-integration-spec.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Wire continuum oscillator phase, market_phase, volume_regime, linreg into signal scoring
- **Difficulty:** Level 2
- **Value:** MEDIUM — improves direction alignment
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Phase boost, market_phase boost, linreg direction already in signal_compactor.py. Wyckoff, z-score integration still pending.

## Plan: pump-chain-v5-spec.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Add velocity filter (30m > -0.3%) and continuum oscillator filter to pump-chain
- **Difficulty:** Level 1
- **Value:** HIGH — 90% WR with velocity filter
- **Status:** IMPLEMENTED
- **Reason:** pump_chain_v5.py already has all 3 filters (velocity, wave_phase, momentum_state)

## Plan: trade-watchdog-spec.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Autonomous trade monitor with profit locking, regime alignment, stale detection
- **Difficulty:** Level 4
- **Value:** HIGH — proactive trade management
- **Status:** IMPLEMENTED
- **Reason:** trade_watchdog.py exists (1253 lines), fully functional with profit lock, stale detection, regime alignment.

## Plan: structural-awareness-overhaul.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Wire S/R, Wyckoff, trend quality into proactive positioning
- **Difficulty:** Level 4
- **Value:** HIGH — shifts from reactive to proactive
- **Status:** PENDING
- **Reason:** Multi-system overhaul. Needs phased implementation.

## Plan: pump-chain-v5-evidence.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Blacklist worst pump-chain tokens (HEMI, GRASS, AZTEC, BCH, ATOM)
- **Difficulty:** Level 1
- **Value:** MEDIUM — removes 0% WR tokens
- **Status:** IMPLEMENTED (partial)
- **Reason:** HEMI already blacklisted. GRASS, AZTEC, BCH, ATOM not yet in global blacklists.

## Plan: squeeze-breakout-signal-spec.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** New signal for BB squeeze breakouts
- **Difficulty:** Level 2
- **Value:** MEDIUM — captures pre-breakout positioning
- **Status:** IMPLEMENTED
- **Reason:** squeeze_breakout.py exists in signals/

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Disable rr_engine for pullback-entry-, kill ema300-dip-long, blacklist ENA, tighten cut-loser
- **Difficulty:** Level 1
- **Value:** HIGH — +$4.21/7d estimated impact
- **Status:** MOSTLY IMPLEMENTED
- **Reason:** ema300-dip-long disabled, trend_purity disabled, ENA blacklisted. Check remaining items.

## Plan: ride-it-exit-spec.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** 2-phase exit system (survival + trail) with volume spike override
- **Difficulty:** Level 2
- **Value:** HIGH — +15.7% on BABY-type trades
- **Status:** IMPLEMENTED
- **Reason:** ride_it_exit.py exists, RIDE_IT_ENABLED=True

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Continuum oscillator as confidence multiplier with shadow→live progression
- **Difficulty:** Level 2
- **Value:** MEDIUM — data-driven confidence adjustment
- **Status:** SHADOW MODE
- **Reason:** OSCILLATOR_MULT_ENABLED=False, OSCILLATOR_MULTS defined. Shadow logging active.

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** New signal for mean-reversion from extreme oversold (RSI < 25)
- **Difficulty:** Level 2
- **Value:** MEDIUM — 70% WR in backtest
- **Status:** IMPLEMENTED
- **Reason:** oversold_bounce.py exists (274 lines), fully functional.

## Plan: pump-catching-and-exit-optimization.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Fix dead pump signals, ATR SL underperformance, chop losses
- **Difficulty:** Level 2
- **Value:** HIGH — addresses pump detection gaps
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** volume-breakout-long+ is MVP. BTC Timing Guard threshold needs review.

## Plan: volatility-gate-tuning.md
- **Date scanned:** 2026-09-27 00:00
- **Core request:** Tune volatility gate multipliers for different regimes
- **Difficulty:** Level 1
- **Value:** MEDIUM — regime-aware signal filtering
- **Status:** PENDING
- **Reason:** Config tuning in volatility_gate_v2.py

---

# Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED | 10 |
| PARTIALLY IMPLEMENTED | 2 |
| SHADOW MODE | 1 |
| PENDING | 1 |

# Easy Wins Remaining (Level 1)
1. ~~Add pump-chain v5 blacklist tokens (GRASS, AZTEC, BCH, ATOM) to global blacklists~~ ✅ DONE
2. ~~Volatility gate tuning (config changes)~~ ✅ ALREADY IMPLEMENTED (volatility_gate_v2.py has ATR ratio + BTC trend boost)

# Remaining Work (Level 3-4)
1. **chop-v2-spec.md** — Per-coin trend scoring + chop-specific exits (Level 3, HIGH value)
2. **structural-awareness-overhaul.md** — Wire S/R, Wyckoff, trend quality into proactive positioning (Level 4)
