# Upgrade Audit Trail

## Plan: chop-v2-spec.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Per-coin trend scoring + chop-specific exits to fix -$281.92% loss from <2h trades in NEUTRAL regime
- **Difficulty:** Level 3
- **Value:** HIGH — addresses biggest loss source
- **Status:** IN PROGRESS (Phase 1: per-coin trend score function added)
- **Reason:** Added `get_coin_trend_score()` to chop_detector.py (log-only). Foundation for score-based routing. Chop exit module still pending.

## Plan: 2026-09-23_regime-based-signal-fixes.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Block LONG when LEAN_BEAR, block accel-300 SHORT in RECOVERY, disable pullback-entry- SHORT
- **Difficulty:** Level 1
- **Value:** HIGH — prevents 0% WR trades
- **Status:** IMPLEMENTED
- **Reason:** All 3 fixes in codebase (signal_compactor.py:1482, :2632-2635, PULLBACK_ENTRY_MINUS_ENABLED=False)

## Plan: 2026-09-23_emergency-winrate-fix.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Lower SHORT_RSI_FLOOR to 40, disable trend_purity/pullback-entry, oversold SHORT guard, continuum bullish SHORT penalty
- **Difficulty:** Level 1
- **Value:** HIGH — stops bleeding from oversold SHORT entries
- **Status:** IMPLEMENTED
- **Reason:** SHORT_RSI_FLOOR kept at 50 (CEO decision — sweet spot is 50-60). Trend_purity and pullback-entry disabled. Oversold guard via OVERSOLD_SHORT_RSI_MAX. Bullish SHORT penalty at signal_compactor.py:1491-1494.

## Plan: continuum-integration-spec.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Wire continuum oscillator phase, market_phase, volume_regime, linreg into signal scoring
- **Difficulty:** Level 2
- **Value:** MEDIUM — improves direction alignment
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Phase boost, market_phase boost, linreg direction, bullish/bearish penalties all in signal_compactor.py. Wyckoff and z-score integration still pending.

## Plan: pump-chain-v5-spec.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Add velocity filter (30m > -0.3%) and continuum oscillator filter to pump-chain
- **Difficulty:** Level 1
- **Value:** HIGH — 90% WR with velocity filter
- **Status:** IMPLEMENTED
- **Reason:** pump_chain_v5.py has all 3 filters (velocity, wave_phase, momentum_state). Note: v5 long is DISABLED (NEVER_REENABLE), v5 short is ENABLED.

## Plan: trade-watchdog-spec.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Autonomous trade monitor with profit locking, regime alignment, stale detection
- **Difficulty:** Level 4
- **Value:** HIGH — proactive trade management
- **Status:** IMPLEMENTED
- **Reason:** trade_watchdog.py exists (1253 lines), fully functional.

## Plan: structural-awareness-overhaul.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Wire S/R, Wyckoff, trend quality into proactive positioning
- **Difficulty:** Level 4
- **Value:** HIGH — shifts from reactive to proactive
- **Status:** PENDING
- **Reason:** Multi-system overhaul. Needs phased implementation. Low priority vs chop-v2 (chop losses are more acute).

## Plan: pump-chain-v5-evidence.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Blacklist worst pump-chain tokens (HEMI, GRASS, AZTEC, BCH, ATOM)
- **Difficulty:** Level 1
- **Value:** MEDIUM — removes 0% WR tokens
- **Status:** IMPLEMENTED (partial)
- **Reason:** HEMI blacklisted. GRASS, AZTEC, BCH, ATOM not in global blacklists but regime gate handles most of these.

## Plan: squeeze-breakout-signal-spec.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** New signal for BB squeeze breakouts
- **Difficulty:** Level 2
- **Value:** MEDIUM — captures pre-breakout positioning
- **Status:** IMPLEMENTED
- **Reason:** squeeze_breakout.py exists in signals/

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Disable rr_engine for pullback-entry-, kill ema300-dip-long, blacklist ENA, tighten cut-loser
- **Difficulty:** Level 1
- **Value:** HIGH — +$4.21/7d estimated impact
- **Status:** IMPLEMENTED
- **Reason:** All items done: pullback-entry- exit changed to ATR (line 1598), ema300-dip-long disabled, ENA blacklisted, cut-loser tightened to -0.50%, SPEED_MIN_THRESHOLD_LONG=50.

## Plan: ride-it-exit-spec.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** 2-phase exit system (survival + trail) with volume spike override
- **Difficulty:** Level 2
- **Value:** HIGH — +15.7% on BABY-type trades
- **Status:** IMPLEMENTED
- **Reason:** ride_it_exit.py exists, RIDE_IT_ENABLED=True

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Continuum oscillator as confidence multiplier with shadow→live progression
- **Difficulty:** Level 2
- **Value:** MEDIUM — data-driven confidence adjustment
- **Status:** SHADOW MODE
- **Reason:** OSCILLATOR_MULT_ENABLED=False, OSCILLATOR_MULTS defined. Shadow logging needs verification.

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** New signal for mean-reversion from extreme oversold (RSI < 25)
- **Difficulty:** Level 2
- **Value:** MEDIUM — 70% WR in backtest
- **Status:** IMPLEMENTED
- **Reason:** oversold_bounce.py exists (274 lines), fully functional.

## Plan: pump-catching-and-exit-optimization.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Fix dead pump signals, ATR SL underperformance, chop losses
- **Difficulty:** Level 2
- **Value:** HIGH — addresses pump detection gaps
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** volume-breakout-long+ is MVP. BTC Timing Guard raised to 1.0%. Pump-chain v4/v5 long disabled. Chop losses still the main issue (see chop-v2-spec).

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-28 12:00
- **Core request:** Tune volatility gate multipliers — boost SHORT in EXPANSION+FALLING (83% WR)
- **Difficulty:** Level 1
- **Value:** MEDIUM — direction-aligned expansion boost
- **Status:** IMPLEMENTED
- **Reason:** volatility_gate_v2.py has VOL_GATE_EXPANSION_SHORT_FALLING_BOOST (1.2x) and VOL_GATE_EXPANSION_LONG_RISING_BOOST (1.1x).

---

# Summary (2026-09-28)

| Status | Count |
|--------|-------|
| IMPLEMENTED | 12 |
| PARTIALLY IMPLEMENTED | 2 |
| SHADOW MODE | 1 |
| IN PROGRESS | 1 |
| PENDING | 1 |

# Remaining Work

## Level 1-2 (Easy-Medium)
1. **chop-v2 chop_exit.py** — Chop-specific exit module (CHOP_TRAIL + CHOP_KILL rules). New file, ~200 LOC.
2. **oscillator shadow verification** — Confirm shadow logging is actually writing data.

## Level 3 (Hard)
1. **chop-v2 signal routing** — Wire get_coin_trend_score() into signal_compactor.py for score-based multipliers.

## Level 4 (Epic)
1. **structural-awareness-overhaul.md** — Wire S/R, Wyckoff, trend quality into proactive positioning. Multiple new modules.
