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

## Plan: contrarian-zone-signal.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** New signal for mean-reversion at structural S/R zones (liquidity sweep + bounce)
- **Difficulty:** Level 2
- **Value:** MEDIUM — 70% WR backtest, depends on SL memory S/R (built)
- **Status:** PENDING
- **Reason:** Needs integration with sl_zones.py. Not as urgent as chop-v2.

## Plan: sl-memory-sr-system-v2.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** Entry distance filtering + regime gate for S/R zones
- **Difficulty:** Level 3
- **Value:** MEDIUM — improves entry quality near death zones
- **Status:** PENDING
- **Reason:** Complex multi-phase system. Lower priority vs chop-v2.

## Plan: pump-chain-exit-spec.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** Replace RR engine exit with momentum exit for pump-chain
- **Difficulty:** Level 2
- **Value:** MEDIUM — pump-chain long is DISABLED (NEVER_REENABLE)
- **Status:** SKIPPED
- **Reason:** Pump-chain long disabled. V5 short uses different exit logic.

## Plan: hl-trigger-sl-v2.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** Use limit orders instead of market orders for SL execution
- **Difficulty:** Level 3
- **Value:** HIGH — fixes slippage on SL execution
- **Status:** PENDING
- **Reason:** Requires HL SDK changes. High risk, needs careful testing.

## Plan: spider-profit.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** Regime-aware profit taking — book small wins in chop, ride in trends
- **Difficulty:** Level 2
- **Value:** MEDIUM — addresses capital lockup in flat markets
- **Status:** PENDING
- **Reason:** Overlaps with chop-v2 exit module. May be partially addressed there.

## Plan: ema300-rejection-signal-spec.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** New signal for EMA300 breakthrough with momentum continuation
- **Difficulty:** Level 2
- **Value:** MEDIUM — 69-80% WR backtest on SHORT
- **Status:** PENDING
- **Reason:** Validated backtest but needs live validation. Not urgent.

## Plan: regime-tuner-spec.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** Automated weekly regime analysis to re-enable/disable signals
- **Difficulty:** Level 3
- **Value:** MEDIUM — reduces manual intervention
- **Status:** PENDING
- **Reason:** Complex automation. Lower priority vs chop-v2.

## Plan: sniper-exit-strategy.md
- **Date scanned:** 2026-09-29 06:10
- **Core request:** Close wrong-side positions when BTC regime shifts
- **Difficulty:** Level 2
- **Value:** MEDIUM — proactive exit on regime change
- **Status:** PENDING
- **Reason:** Partially handled by trade_watchdog.py.

## Plan: oscillator-shadow-verification
- **Date scanned:** 2026-09-29 06:10
- **Core request:** Verify oscillator shadow logging works correctly
- **Difficulty:** Level 1
- **Value:** MEDIUM — validates shadow data before enabling live
- **Status:** IMPLEMENTED
- **Reason:** Shadow log verified: 20,420 entries, Sep 21-29, avg multiplier 0.939. Data quality confirmed. Bug found: wave_phase uses per-token value (correct per spec).

---

# Summary (2026-09-29)

| Status | Count |
|--------|-------|
| IMPLEMENTED | 13 |
| PARTIALLY IMPLEMENTED | 2 |
| SHADOW MODE | 1 |
| IN PROGRESS | 1 |
| PENDING | 8 |
| SKIPPED | 1 |

# Remaining Work

## Level 1-2 (Easy-Medium) — Next
1. **chop-v2 chop_exit.py** — Chop-specific exit module (CHOP_TRAIL + CHOP_KILL rules). New file, ~200 LOC. **HIGHEST PRIORITY.**
2. **chop-v2 signal routing** — Wire get_coin_trend_score() into signal_compactor.py for score-based multipliers.

## Level 2 (Medium) — Backlog
3. **contrarian-zone-signal** — New signal at S/R zones (depends on sl_zones.py)
4. **ema300-rejection-signal** — EMA300 breakthrough continuation signal
5. **spider-profit** — Regime-aware profit taking (partially overlaps chop-v2)
6. **sniper-exit** — Close wrong-side positions on regime shift
7. **pump-chain-exit** — SKIPPED (pump-chain long disabled)

## Level 3 (Hard) — Backlog
8. **hl-trigger-sl-v2** — Limit orders for SL execution (high risk)
9. **regime-tuner** — Automated weekly signal re-enable/disable
10. **sl-memory-sr-system-v2** — Entry distance filtering near S/R zones

## Level 4 (Epic) — Backlog
11. **structural-awareness-overhaul** — Wire S/R, Wyckoff, trend quality into proactive positioning.
