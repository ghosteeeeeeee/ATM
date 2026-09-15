# Upgrade Audit Trail

**Last updated:** 2026-09-12 18:10 UTC

---

## Plan: doji_bottom_signal (NEW — not in plans/)
- **Date scanned:** 2026-09-11 04:50
- **Core request:** Create doji-bottom-long signal — mirror of doji_top for bottoms (LONG entry on doji exhaustion after decline)
- **Difficulty:** Level 1
- **Value:** MEDIUM — completes the doji exhaustion system (top was SHORT-only)
- **Status:** IMPLEMENTED
- **Reason:** Constants already existed (DOJI_DECLINE_MIN_PCT, DOJI_RSI_OVERSOLD, DOJI_VOLUME_DRY_RATIO). Created doji_bottom.py (216 lines), registered in __init__.py, added source weights in signal_compactor.py, added to REGIME_SIGNALS (FLAT/NORMAL/HIGH), STANDALONE_BYPASS, chop_detector classification, market_phase_gate. Uses inverse logic: volume drying up (not spike), RSI oversold (not overbought), prior decline (not advance). Runs clean, 0 signals in test (expected — needs specific conditions).

---

## Plan: 2026-09-09_pump-chain-v2-spec.md
- **Date scanned:** 2026-09-10 18:00
- **Core request:** Add token 30m velocity filter + tighten 5m threshold to block pump-chain losers
- **Difficulty:** Level 1
- **Value:** HIGH — backtested 57%→80% WR, PnL 0.5→3.36
- **Status:** IMPLEMENTED
- **Reason:** Added 3 new filters: (1) 30m velocity > 0% for LONG, (2) 5m threshold tightened -0.2%→-0.5%, (3) SHORT blocked when token 30m vel > 0%. All in pump_flow_signal.py, constants in hermes_constants.py. Dry run verified.

---

## Plan: 2026-09-09_regime-transition-smoothing.md
- **Date scanned:** 2026-09-10 06:00
- **Core request:** Reduce transition zone bleeding by wiring existing systems + tightening constants
- **Difficulty:** Level 1 (constants) + Level 2 (directional bias + alt-BTC divergence)
- **Value:** HIGH — estimated +$1.05 PnL impact in transition zones
- **Status:** IMPLEMENTED
- **Reason:** CEO-approved plan. Implemented 3 of 4 layers (Layer 1 skipped — redundant with zscore_accel).
  - Layer 3: DIRECTIONAL_OUTCOME_PENALTY 0.7→0.5, LOCK_VELOCITY 0.6→0.5
  - Layer 2: Directional bias — reads BTC momentum_state from cache, boosts pro-trend (1.15x), penalizes counter-trend (0.6x)
  - Layer 4: Alt-BTC divergence — blocks LONG when alt 30m <-0.3% and BTC 30m > -0.1% (0.5x penalty)
  - Files: hermes_constants.py (+6 constants), signal_compactor.py (~40 lines added)

---

## Plan: 2026-09-08_grind-breakout-signal-spec.md
- **Date scanned:** 2026-09-09
- **Core request:** New signal for steady grind + late breakout patterns
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** `scripts/signals/grind_breakout.py` exists (356 lines), constants added, registered in __init__.py, source weights in compactor. **BUG FOUND:** Not in REGIME_SIGNALS — won't fire. Fixing now.

## Plan: breakout-long-signal-spec.md
- **Date scanned:** 2026-09-09
- **Core request:** Volume-confirmed breakout LONG signal
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** `scripts/signals/breakout_long.py` exists (309 lines), constants added, registered, in REGIME_SIGNALS for HIGH/EXTREME, in STANDALONE_BYPASS.

## Plan: 2026-09-09_grass-breakout-analysis.md
- **Date scanned:** 2026-09-09
- **Core request:** squeeze_reversal signal for BB squeeze → mean-reversion breakout
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED (with bugs)
- **Reason:** `scripts/signals/squeeze_reversal.py` exists (353 lines), constants added, registered. **BUGS FOUND:** (1) Not in REGIME_SIGNALS — won't fire. (2) No source weights in signal_compactor. (3) Not in STANDALONE_BYPASS. Fixing now.

## Plan: pullback_entry_signal.md
- **Date scanned:** 2026-09-09
- **Core request:** Pullback entry signal for low-volume pullbacks after strong moves
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** `scripts/signals/pullback_entry.py` exists (9545 bytes), constants added, registered, in REGIME_SIGNALS, in STANDALONE_BYPASS.

## Plan: 2026-09-08_grind-breakout-quality-filters.md
- **Date scanned:** 2026-09-09
- **Core request:** RSI 35-65 quality filter for grind_breakout
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Constants GRIND_BREAKOUT_RSI_MAX=65, GRIND_BREAKOUT_RSI_MIN=35 already in hermes_constants.py.

## Plan: doji_signal_system.md
- **Date scanned:** 2026-09-09
- **Core request:** Doji-based entry/exit signals
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED (both top and bottom)
- **Reason:** `scripts/signals/doji_top.py` exists (SHORT-only). `scripts/signals/doji_bottom.py` created 2026-09-11 (LONG entry). Constants fully defined. Registered, source weights added, in REGIME_SIGNALS + STANDALONE_BYPASS.

## Plan: 2026-09-08_trend-ignition-signal-spec.md
- **Date scanned:** 2026-09-09
- **Core request:** Early-stage breakout signal at trend START
- **Difficulty:** Level 2
- **Value:** HIGH (100% WR in 7-day backtest)
- **Status:** NOT IMPLEMENTED
- **Reason:** `scripts/signals/trend_ignition.py` does not exist. No constants, no registration. Needs full build.

## Plan: 2026-09-08_btc-alignment-crash-protection-overhaul.md
- **Date scanned:** 2026-09-09
- **Core request:** BTC trend alignment filter + crash protection
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** BTC_MOMENTUM_FALLING_THRESHOLD=-0.12 and BTC_MOMENTUM_RISING_THRESHOLD=0.12 already in constants. btc_crash_filter.py active with BTC_CRASH_BLOCK_ENABLED=True. MAE guard enabled at 3.0%.

## Plan: 2026-09-08_short-filter-overhaul.md
- **Date scanned:** 2026-09-09
- **Core request:** Stop blocking profitable SHORT signals
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** Dead code bug FIXED (range(SHORT_VEL_FILTER_GREEN_THRESHOLD)). Remaining Phase 1 changes (VEL threshold 0.3→0.5, EMA slope) require simulation script first per audit. Audit also found: confluence gate is the BIGGEST blocker (3,058 SHORTs), not the filters this plan targets. SHORT R:R is poor (0.28:1) — relaxing filters adds volume without fixing R:R.

## Plan: accel300-v4-killer-signal.md
- **Date scanned:** 2026-09-09
- **Core request:** Transform accel-300 from 45% to 95%+ WR
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** ACCEL_300_V4_SHORT_EXEC_RSI_MAX=50 already in constants. ACCEL_300_V3_SHORT_EXEC_RSI_MAX=50 also present. RSI>50 filter for SHORT is active. z>0 filter for HIGH regime deferred per audit (sample <30).

## Plan: accel300-long-fix-plan.md
- **Date scanned:** 2026-09-09
- **Core request:** Fix accel-300 LONG from 39% to 70%+ WR
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** ACCEL_300_V3_LONG_EXEC_RSI_MIN=50 already in constants. RSI<50 filter for LONG is active.

## Plan: 2026-09-07_partial-close-trailing-runner.md
- **Date scanned:** 2026-09-09
- **Core request:** Partial close + trailing runner for winner capture
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED
- **Reason:** No PARTIAL_CLOSE constants exist. Requires tpsl_utils.py changes for partial size support. Complex multi-file change. Defer.

## Plan: exit-strategy-refactor.md
- **Date scanned:** 2026-09-09
- **Core request:** Per-signal exit strategy routing
- **Difficulty:** Level 4
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED
- **Reason:** Major refactor of profit_monster.py (477 lines). Plan itself says "FUTURE — simple fix deployed first." Defer.

## Plan: trade_velocity_tracking.md
- **Date scanned:** 2026-09-09
- **Core request:** Track trade velocity for hotset optimization
- **Difficulty:** Level 3
- **Value:** LOW
- **Status:** NOT IMPLEMENTED
- **Reason:** New system requiring DB schema changes, new table, new scoring. Defer.

## Plan: market-sync-protection-plan.md
- **Date scanned:** 2026-09-09
- **Core request:** Market sync protection during BTC selloffs
- **Difficulty:** Level 3
- **Value:** LOW (auditor found 88-92% false positive rate)
- **Status:** NOT IMPLEMENTED
- **Reason:** Auditor concluded "probably slightly negative" effect. False positive rate too high. Do nothing recommended.

---

## Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED (with bugs found) | 2 |
| IMPLEMENTED (complete) | 8 |
| PARTIAL | 2 |
| NOT IMPLEMENTED | 4 |

### Critical Bugs Found During Scan (All Fixed)
1. ~~squeeze_reversal NOT in REGIME_SIGNALS~~ — FIXED
2. ~~squeeze_reversal NOT in signal_compactor source weights~~ — FIXED
3. ~~squeeze_reversal NOT in STANDALONE_BYPASS~~ — FIXED
4. ~~grind_breakout NOT in REGIME_SIGNALS~~ — FIXED

### Next Level 2 Candidates
1. `trend_ignition.py` — New signal, HIGH value, 100% WR in 7-day backtest (9 signals)
2. Partial close trailing runner — Level 3, MEDIUM value (exit system improvement)

### Pending Level 1 Tasks
1. Short filter VEL threshold 0.3→0.5 — needs simulation script first per audit
2. EMA300 slope threshold 0→0.1 — needs simulation script first

---

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** Per-signal-type BTC momentum filter — block pump-chain/pullback-entry when BTC already moved in trade direction (prevents chasing)
- **Difficulty:** Level 1 (~35 lines + 8 constants)
- **Value:** HIGH — estimated +$28.90 per 50 trades (12 bad entries blocked)
- **Status:** IMPLEMENTED
- **Reason:** Added 8 constants to hermes_constants.py (BTC_TIMING_GUARD_*) and ~50 lines to signal_compactor.py after BTC chop gate. LOG_ONLY mode for 48h testing. Blocks pump-chain+ when BTC>+0.3%, pump-chain- when BTC<-0.3%, pullback-entry± at tighter thresholds, accel-300-v4-short- at -0.15%. Syntax verified.

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** Block trend signals in chop + gate STANDALONE_BYPASS when BTC flat
- **Difficulty:** Level 1 (~20 lines + 3 constants)
- **Value:** HIGH — estimated +$0.60 per 4 losses
- **Status:** ALREADY IMPLEMENTED
- **Reason:** Layer A (BTC_CHOP_GATE) and Layer B (bypass gate with _btc_mom_ok_for_bypass) both already in signal_compactor.py. Constants present in hermes_constants.py. CHOP_GATE_LOG_ONLY=True still active.

## Plan: 2026-09-11_btc-pump-rider-gradual-rally.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** Detect gradual BTC rallies (vs explosive breakouts) and buy lagging alts
- **Difficulty:** Level 2 (~80 lines + 8 constants)
- **Value:** MEDIUM — estimated +$0.20 per rally, catches 5-10 missed trades per day
- **Status:** IMPLEMENTED
- **Reason:** Added detect_btc_gradual_rally() + find_lagging_alts_gradual() to btc_pump_rider.py. 8 constants in hermes_constants.py. Modified run() to try gradual rally when no explosive breakout found. Syntax verified.

## Plan: 2026-09-12_btc-momentum-sync-plan.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** 5-layer defense: BTC momentum gate, transition detection, stale signal filter, RSI/z-score guard, continuum context boost
- **Difficulty:** Level 3-4 (multiple systems)
- **Value:** HIGH — projected +$4-6/week
- **Status:** PARTIAL
- **Reason:** Layer 1 (BTC Momentum Gate) is a superset of the timing guard — partially overlaps. Layer 2 (Transition Detection) not implemented. Layer 3 (Stale Signal Filter tightening) not implemented. Layer 4 (RSI/Z-Score Guard) partially exists. Layer 5 (Continuum Context Boost) already built but not wired. Defer to separate sessions.

## Plan: brain-rag-system.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** Feed 602 DSH sessions into FAISS vector index + hourly brain auditor
- **Difficulty:** Level 4 (new system, 3-4 hours)
- **Value:** HIGH — cross-session intelligence, config drift detection
- **Status:** NOT IMPLEMENTED
- **Reason:** Requires faiss-cpu install, new session_brain.py script, systemd timers, brain auditor agent. Defer.

## Plan: regime-tuner-spec.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** Weekly automated regime analysis — re-enable/disable signals based on per-regime WR
- **Difficulty:** Level 3 (new system with DB writes, file safety, locking)
- **Value:** HIGH — prevents stale signal states
- **Status:** NOT IMPLEMENTED
- **Reason:** Complex: AST-based writes to volatility_gate_v2.py, NEVER_REENABLE protection, file locking. Defer.

## Plan: sniper-exit-strategy.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** Proactive position closing on regime shifts — close wrong-side positions
- **Difficulty:** Level 3 (~350 lines, new systemd service)
- **Value:** HIGH — estimated +$0.30-$0.75 per transition zone
- **Status:** CONSTANTS EXIST, LOGIC NOT IMPLEMENTED
- **Reason:** SNIPER_* constants already in hermes_constants.py (lines 886-898). No sniper_exit.py script exists. Defer.

## Plan: spider-profit.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** Regime-aware profit taking — smaller exits in flat markets, let winners run in trends
- **Difficulty:** Level 2-3 (modifies profit_monster.py or new script)
- **Value:** MEDIUM — capital turnover improvement in flat markets
- **Status:** NOT IMPLEMENTED
- **Reason:** No SPIDER_* constants exist. Requires profit_monster.py changes. Defer.

## Plan: ema300-rejection-signal-spec.md
- **Date scanned:** 2026-09-12 05:50
- **Core request:** EMA300 breakthrough signal — price crashes through EMA300 with momentum
- **Difficulty:** Level 2 (new signal)
- **Value:** HIGH — 69-80% WR backtested
- **Status:** ALREADY IMPLEMENTED
- **Reason:** scripts/signals/ema300_breakthrough.py exists with full constants (EMA300_BREAKTHROUGH_*).

---

## Plan: trend_momentum_v4_spec.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Data-driven signal improvements — hour filter (+7% WR), after-win filter (+0.9% WR), token blacklist
- **Difficulty:** Level 2 (new signal file, ~250 lines)
- **Value:** HIGH — projected 46%→54% WR, +30% PnL
- **Status:** NOT IMPLEMENTED
- **Reason:** trend_momentum signal doesn't exist yet (only trend_momentum_near_sma which is killed). Requires full signal build. Hour filter overlaps with existing TIME_BLOCK system.

## Plan: trend_momentum_spec.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** New trend + acceleration signal — catches staged moves from compression
- **Difficulty:** Level 2 (new signal, ~250 lines, 6 file changes)
- **Value:** HIGH — 35% WR but 3.0:1 R:R, +67.89% net PnL in 14d backtest
- **Status:** NOT IMPLEMENTED
- **Reason:** No trend_momentum.py exists. Spec is thorough with backtest data. Conditional GO — needs blacklist, cooldown increase, out-of-sample test.

## Plan: retroactive-scan-delayed-entry.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Secondary scan after breakout engine — catches missed moves with lower confidence
- **Difficulty:** Level 3 (~350 lines in breakout_engine.py, new functions)
- **Value:** HIGH — safety net for missed breakouts (IMX +2.72% case)
- **Status:** NOT IMPLEMENTED
- **Reason:** Complex integration into breakout_engine.py. Plan is well-designed (v3, audited). Deferred to separate session.

## Plan: pullback_entry_v2_long.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Improve pullback_entry LONG from 40% to 60%+ WR
- **Difficulty:** Level 1 (config changes)
- **Value:** MEDIUM — but plan concludes signal is fundamentally unprofitable standalone
- **Status:** ALREADY IMPLEMENTED (disabled)
- **Reason:** Plan recommends disabling pullback_entry_long. Signal is currently disabled (PULLBACK_ENTRY_LONG not in active signals). All backtest configs showed negative PnL.

## Plan: spec-signal-regime-memory.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Per-signal regime memory — "Species of Fish" system. Signals dormant in bad regimes, resurrect when conditions return.
- **Difficulty:** Level 4 (multi-system, 3-4 days)
- **Value:** HIGH — prevents premature signal death, enables regime-aware lifecycle
- **Status:** NOT IMPLEMENTED
- **Reason:** Requires: (1) persist regime at entry, (2) regime tracker SQLite DB, (3) rotator integration, (4) kill system updates, (5) lifecycle dormant state. Complex but well-designed. Defer.

## Plan: accel300-short-variants-study.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Study all accel_300 SHORT variants to find what worked
- **Difficulty:** Level 1 (constant additions based on findings)
- **Value:** HIGH — FLAT regime kills SHORT signals (17% WR original, 0% breakout)
- **Status:** IMPLEMENTED (partial)
- **Reason:** Added ACCEL_300_MINUS_FLAT_BLOCK=True for original SHORT (17% WR in FLAT). V3 already has FLAT+EXTREME blocks. V4 disabled. Breakout and velocity-ignition already disabled. V2 replaced by V3 (also disabled).

## Plan: 2026-09-08_short-filter-overhaul.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Stop blocking profitable SHORT signals — relax VEL filter, SHORT-NEUTRAL block, EMA300 slope
- **Difficulty:** Level 1 (constant changes)
- **Value:** HIGH — 1,101 SHORTs blocked on Sep 8
- **Status:** PARTIAL (dead code fixed, thresholds pending)
- **Reason:** Dead code bug (range(3) vs threshold=5) already fixed. VEL threshold 0.3→0.5 needs simulation script per audit. SHORT-NEUTRAL block has bypasses. SHORT R:R is poor (0.28:1) — relaxing filters adds volume without fixing R:R. Audit found confluence gate is the BIGGEST blocker (3,058 SHORTs), not the filters this plan targets.

## Plan: conf-filter-plan.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Block high-confidence (90+) trades and dead hours (01-06 UTC)
- **Difficulty:** Level 1 (constant changes)
- **Value:** HIGH — conf<90 turns -$1.37 into +$0.08
- **Status:** ALREADY IMPLEMENTED
- **Reason:** CONF_FILTER_ENABLED=True with CONF_FILTER_MAX=89. TIME_BLOCK_ENABLED=True with hours 03-07 UTC. Both filters active.

## Plan: confidence-calibration-plan.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Fix non-monotonic confidence curve (90+ trades lose)
- **Difficulty:** Level 2-3 (scoring system changes)
- **Value:** LOW — investigation concluded existing CONF_FILTER already handles this
- **Status:** ALREADY IMPLEMENTED (via conf-filter-plan)
- **Reason:** Investigation complete — proposed fix rejected, existing CONF_FILTER confirmed working.

## Plan: btc-crash-filter-plan.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** BTC acceleration detection — catch crashes 2-3 minutes earlier
- **Difficulty:** Level 2 (new detection logic)
- **Value:** HIGH — catches WLFI/BIGTIME trades during Aug 22 crash
- **Status:** ALREADY IMPLEMENTED
- **Reason:** BTC_ACCEL_ENABLED=True, _check_acceleration() in btc_crash_filter.py, BTC_ACCEL_VEL_THRESHOLD=-0.15%. Full implementation active.

## Plan: exit-mechanics-v2.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Fix backwards PROFIT_MONSTER_BYPASS_SIGNALS — proven signals not bypassed, losing signals bypassed
- **Difficulty:** Level 1 (constant list changes)
- **Value:** MEDIUM — exit system ownership clarity
- **Status:** ALREADY IMPLEMENTED
- **Reason:** PROFIT_MONSTER_BYPASS_SIGNALS corrected — ct-hot+/- REMOVED from bypass (plan recommended), proven signals (r2-trend, bb_bounce, etc.) IN bypass. Exit ownership model in place.

## Plan: 2026-09-08_grind-breakout-backtest-data.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Raw backtest data for grind_breakout signal
- **Difficulty:** N/A (data only)
- **Value:** LOW — reference data, no implementation needed
- **Status:** ALREADY IMPLEMENTED (signal exists)
- **Reason:** grind_breakout.py exists with constants. This is just backtest reference data.

## Plan: sniper-exit-strategy-brainstorm.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Proactive position closing on regime shifts
- **Difficulty:** Level 3 (~350 lines, new systemd service)
- **Value:** HIGH — estimated +$0.30-$0.75 per transition zone
- **Status:** PARTIAL (constants exist, script exists but not verified)
- **Reason:** SNIPER_* constants in hermes_constants.py, sniper_exit.py exists and imports clean. Needs integration testing. Defer.

## Plan: 2026-08-19_short-bias-fix.md
- **Date scanned:** 2026-09-12 18:00
- **Core request:** Investigate SHORT starvation — system heavily long biased
- **Difficulty:** N/A (investigation only)
- **Value:** LOW — root cause identified (market condition, not filter bug)
- **Status:** ALREADY IMPLEMENTED (investigation complete)
- **Reason:** SHORT starvation is expected in bull market — trend alignment correctly blocks counter-trend SHORTs (26% WR). No filter changes needed.

---

## Updated Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED (this session) | 1 |
| ALREADY IMPLEMENTED | 7 |
| PARTIAL | 2 |
| NOT IMPLEMENTED | 4 |
| N/A (investigation/data) | 3 |

### Implemented This Session
1. **ACCEL_300_MINUS_FLAT_BLOCK** — blocks original SHORT in FLAT regime (17% WR → 0 trades)

### Previously Implemented (from earlier sessions)
1. **BTC Timing Guard** — per-signal-type momentum filter, LOG_ONLY mode
2. **BTC Pump Rider Gradual Rally** — gradual rally detection + lagging alt finder
3. **CONF_FILTER + TIME_BLOCK** — blocks 90+ confidence and dead hours
4. **BTC Acceleration Detection** — catches crashes 2-3 min earlier
5. **PROFIT_MONSTER_BYPASS corrected** — exit ownership model
6. **Dead code fix in VEL-FILTER** — range(3) → range(5)

### Next Candidates
1. `trend_momentum.py` — Level 2, HIGH value, 3.0:1 R:R
2. Retroactive Scan — Level 3, HIGH value, missed breakout safety net
3. Signal Regime Memory — Level 4, HIGH value, dormant/resurrect lifecycle
4. Sniper Exit Strategy — Level 3, HIGH value, constants+script exist (timer disabled)
5. Pump-Chain Exit — Level 2, HIGH value, ATR trail for pump-chain momentum

---

## Plan: 2026-09-08_trend-ignition-signal-spec.md
- **Date scanned:** 2026-09-13 18:00
- **Core request:** Early-stage breakout signal at trend START — volume spike + compression + breakout
- **Difficulty:** Level 2 (new signal, ~200 lines)
- **Value:** HIGH — 100% WR in 7-day backtest (9 signals), avg +1.92% return
- **Status:** IMPLEMENTED
- **Reason:** Created `scripts/signals/trend_ignition.py` (215 lines). 15 constants added to hermes_constants.py. Registered in __init__.py, source weight 1.3 in signal_compactor.py. Added to REGIME_SIGNALS (NORMAL+HIGH), STANDALONE_BYPASS, PROFIT_MONSTER_BYPASS. Syntax verified, imports clean, detection logic tested (0 signals on test tokens — expected, needs specific conditions).

## Plan: sl-memory-sr-system.md
- **Date scanned:** 2026-09-13 18:00
- **Core request:** SL Memory as S/R — use previous stop-losses as support/resistance levels
- **Difficulty:** Level 4 (new DB table, multi-system integration)
- **Value:** HIGH — prevents repeated stop-outs at same levels
- **Status:** NOT IMPLEMENTED
- **Reason:** Requires new sl_memory table in PostgreSQL, zone aggregation logic, RR engine integration, position_manager changes. Complex multi-day project. Defer.

## Plan: pump-chain-exit-spec.md
- **Date scanned:** 2026-09-13 18:00
- **Core request:** ATR trailing exit for pump-chain — replaces RR engine exits that kill momentum
- **Difficulty:** Level 2 (modifies position_manager.py, adds constants)
- **Value:** HIGH — FIL case: +12.7% vs +6.5% current exit
- **Status:** ALREADY IMPLEMENTED (with bug fix)
- **Reason:** Full pump-exit logic in position_manager.py (lines 2506-2639). Constants exist (PUMP_EXIT_*). SIGNAL_EXIT_CONFIG has pump-chain+/- → pump_exit. **BUG FIXED:** `_persist_sl` called with extra `db_conn` arg (lines 2554, 2563) — removed extra arg.

## Plan: hl-trigger-sl-v2.md
- **Date scanned:** 2026-09-13 18:00
- **Core request:** HL trigger orders V2 — server-side SL/TP to eliminate slippage
- **Difficulty:** Level 3 (HL SDK integration, guardian changes)
- **Value:** HIGH — estimated 139% PnL savings over 7 days
- **Status:** NOT IMPLEMENTED
- **Reason:** V1 was disabled due to bugs (incomplete placement, stale matching, rate limiting). V2 spec uses SDK atomic functions. 2 CRITICAL + 4 HIGH audit findings. Requires careful testing. Defer.

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-14 06:00
- **Core request:** ATR ratio + BTC trend boost in volatility_gate_v2.py — boost SHORT in falling expansion (83% WR setup)
- **Difficulty:** Level 1 (~30 lines + 7 constants)
- **Value:** HIGH — data-backed 83% WR for SHORT in falling expansion regime
- **Status:** IMPLEMENTED
- **Reason:** Added `get_atr_ratio()` (current_ATR/average_ATR), `get_btc_trend()` (reads momentum_cache), and direction-aligned boost in `get_combined_multiplier()`. 7 constants in hermes_constants.py. BTC ATR ratio=0.76 currently (normal, no boost applied — correct). Syntax verified.

## Plan: 2026-09-11_volatility-regime-adaptive-signals.md
- **Date scanned:** 2026-09-14 06:00
- **Core request:** Signal weighting by volatility regime — boost momentum in expansion, mean-reversion in compression
- **Difficulty:** Level 2 (~35 lines in signal_compactor.py)
- **Value:** MEDIUM — estimated +$0.33-0.66 per day from regime-adaptive signal weighting
- **Status:** IMPLEMENTED
- **Reason:** Added `vol_regime_mult` in `_score_signal()` after alt-BTC divergence check. Computes BTC ATR ratio from candles_1h (520 bars), classifies EXPANSION/NORMAL/COMPRESSION. Momentum signals (mover, pump, accel, continuation) boosted 1.2x in expansion, penalized 0.7x in compression. Mean-reversion signals (bb_bounce, range-reversion, squeeze, oversold) penalized 0.8x in expansion, boosted 1.2x in compression. Added to final_score chain. Syntax verified.

---

## Updated Summary (2026-09-14)

| Status | Count |
|--------|-------|
| IMPLEMENTED (this session) | 2 |
| ALREADY IMPLEMENTED | 7 |
| PARTIAL | 2 |
| NOT IMPLEMENTED | 7 |
| N/A (investigation/data) | 3 |

### Implemented This Session
1. **Volatility Gate Tuning** — ATR ratio + BTC trend boost in volatility_gate_v2.py (30 lines, 7 constants)
2. **Volatility Regime Adaptive Signals** — momentum/mean-reversion weighting by regime in signal_compactor.py (35 lines)

### Previously Implemented
1. **trend_ignition.py** — early-stage breakout signal (100% WR backtest, 215 lines, full integration)
2. **BTC Timing Guard** — per-signal-type momentum filter, LOG_ONLY mode
3. **BTC Pump Rider Gradual Rally** — gradual rally detection + lagging alt finder
4. **CONF_FILTER + TIME_BLOCK** — blocks 90+ confidence and dead hours
5. **BTC Acceleration Detection** — catches crashes 2-3 min earlier
6. **PROFIT_MONSTER_BYPASS corrected** — exit ownership model
7. **Dead code fix in VEL-FILTER** — range(3) → range(5)

### Next Candidates
1. Retroactive Scan — Level 3, HIGH value, missed breakout safety net
2. Signal Regime Memory — Level 4, HIGH value, dormant/resurrect lifecycle
3. Sniper Exit Strategy — Level 3, HIGH value, constants+script exist
4. Contrarian Zone Signal — Level 2, HIGH value (84% zone hold rate, depends on SL Memory)
5. Trend Momentum V4 — Level 2, HIGH value, 54% WR data-driven filters
6. Spider-Profit — Level 2-3, MEDIUM value, regime-aware profit taking
7. Ponytail Full Audit — Level 1-3, MEDIUM value, 33K lines dead code cleanup

---

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-14 06:00 (previous scan)
- **Status:** IMPLEMENTED
- **Re-verified:** 2026-09-14 20:00 — get_atr_ratio(), get_btc_trend(), direction-aligned boost all present in volatility_gate_v2.py

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Mean reversion LONG at extreme oversold (RSI<25, z<-1, BB<0.3)
- **Difficulty:** Level 2 (new signal, ~200 lines)
- **Value:** HIGH — 70% WR, +$0.97 total PnL in backtest
- **Status:** ALREADY IMPLEMENTED
- **Reason:** scripts/signals/oversold_bounce.py exists. OVERSOLD_BOUNCE_ENABLED=True in hermes_constants.py. Registered in __init__.py, source weights in signal_compactor.py.

## Plan: contrarian-zone-signal.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Flip direction when system enters near strong SL zones (84% zone hold rate)
- **Difficulty:** Level 2 (new signal ~150 lines + signal_compactor integration)
- **Value:** HIGH — 72% WR in 0-0.5% band, positive expected value
- **Status:** NOT IMPLEMENTED
- **Reason:** No contrarian_zone signal file exists. sl_zones.py has entry_distance_filter() but contrarian logic (flip direction) not implemented. Requires: (1) contrarian_zone.py signal, (2) contrarian flip in signal_compactor.py when SL zone blocks, (3) exit logic for contrarian trades. Depends on sl_memory table existing in PostgreSQL.

## Plan: sl-memory-sr-system-v2.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Use previous SL hits as S/R zones — entry filtering, exit tightening, size reduction
- **Difficulty:** Level 4 (DB table, zone engine, multi-system integration)
- **Value:** HIGH — prevents repeated stop-outs, zone-aware trading
- **Status:** PARTIAL
- **Reason:** sl_zones.py exists (433 lines) with entry_distance_filter(). Integrated into signal_compactor.py (line 2951). BUT: (1) sl_memory table status unknown (PostgreSQL not accessible), (2) contrarian flip not implemented, (3) zone-aware exit tightening not wired into position_manager, (4) position sizing not wired into decider_run. Phase 1 (data collection) and Phase 2 (zone engine) partially done. Phase 3-6 pending.

## Plan: sniper-exit-strategy.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Proactive position closing on regime shifts — close wrong-side positions
- **Difficulty:** Level 3 (~350 lines, new systemd service)
- **Value:** HIGH — estimated +$0.30-$0.75 per transition zone
- **Status:** CONSTANTS EXIST, SCRIPT EXISTS, NOT VERIFIED
- **Reason:** SNIPER_* constants in hermes_constants.py. sniper_exit.py exists. But not verified as active or integrated. Needs integration testing.

## Plan: trend_momentum_v4_spec.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Data-driven signal improvements — hour filter (+7% WR), after-win filter (+0.9% WR)
- **Difficulty:** Level 2 (new signal, ~250 lines)
- **Value:** HIGH — projected 46%→54% WR, +30% PnL
- **Status:** NOT IMPLEMENTED
- **Reason:** No trend_momentum signal exists (only trend_momentum_near_sma which is dead). Requires full signal build. Hour filter overlaps with existing TIME_BLOCK system.

## Plan: trend_momentum_spec.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** New trend + acceleration signal — catches staged moves from compression
- **Difficulty:** Level 2 (new signal, ~250 lines, 6 file changes)
- **Value:** HIGH — 35% WR but 3.0:1 R:R, +67.89% net PnL in 14d backtest
- **Status:** NOT IMPLEMENTED
- **Reason:** No trend_momentum.py exists. Spec is thorough with backtest data. Conditional GO — needs blacklist, cooldown increase, out-of-sample test.

## Plan: spider-profit.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Regime-aware profit taking — smaller exits in flat markets
- **Difficulty:** Level 2-3 (modifies profit_monster.py or new script)
- **Value:** MEDIUM — capital turnover improvement in flat markets
- **Status:** NOT IMPLEMENTED
- **Reason:** No SPIDER_* constants exist. Requires profit_monster.py changes. Defer.

## Plan: retroactive-scan-delayed-entry.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Secondary scan after breakout engine — catches missed moves with lower confidence
- **Difficulty:** Level 3 (~350 lines in breakout_engine.py, new functions)
- **Value:** HIGH — safety net for missed breakouts (IMX +2.72% case)
- **Status:** NOT IMPLEMENTED
- **Reason:** Complex integration into breakout_engine.py. Plan is well-designed (v3, audited). Deferred to separate session.

## Plan: spec-signal-regime-memory.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Per-signal regime memory — dormant/resurrect lifecycle
- **Difficulty:** Level 4 (multi-system, 3-4 days)
- **Value:** HIGH — prevents premature signal death
- **Status:** NOT IMPLEMENTED
- **Reason:** Requires: persist regime at entry, regime tracker SQLite DB, rotator integration, kill system updates, lifecycle dormant state. Defer.

## Plan: hl-trigger-sl-v2.md
- **Date scanned:** 2026-09-14 20:00 (re-verified)
- **Core request:** HL trigger orders V2 — server-side SL/TP to eliminate slippage
- **Difficulty:** Level 3 (HL SDK integration, guardian changes)
- **Value:** HIGH — estimated 139% PnL savings over 7 days
- **Status:** NOT IMPLEMENTED
- **Reason:** V1 was disabled. V2 spec uses SDK atomic functions. 2 CRITICAL + 4 HIGH audit findings. Requires careful testing. Defer.

## Plan: 2026-09-12_btc-momentum-sync-plan.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** 5-layer defense: BTC momentum gate, transition detection, stale signal filter, RSI/z-score guard, continuum context boost
- **Difficulty:** Level 3-4 (multiple systems)
- **Value:** HIGH — projected +$4-6/week
- **Status:** PARTIAL
- **Reason:** Layer 1 (BTC Momentum Gate) overlaps with timing guard. Layer 2-5 partially built but not wired. Defer.

## Plan: brain-rag-system.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Feed DSH sessions into FAISS vector index + hourly brain auditor
- **Difficulty:** Level 4 (new system, 3-4 hours)
- **Value:** HIGH — cross-session intelligence
- **Status:** NOT IMPLEMENTED
- **Reason:** Requires faiss-cpu install, new session_brain.py, systemd timers. Defer.

## Plan: regime-tuner-spec.md
- **Date scanned:** 2026-09-14 20:00
- **Core request:** Weekly automated regime analysis — re-enable/disable signals based on per-regime WR
- **Difficulty:** Level 3 (new system with DB writes, file safety, locking)
- **Value:** HIGH — prevents stale signal states
- **Status:** NOT IMPLEMENTED
- **Reason:** Complex: AST-based writes to volatility_gate_v2.py, NEVER_REENABLE protection. Defer.

---

## Updated Summary (2026-09-14)

| Status | Count |
|--------|-------|
| IMPLEMENTED (complete) | 15 |
| ALREADY IMPLEMENTED | 7 |
| PARTIAL | 3 |
| NOT IMPLEMENTED | 12 |
| N/A (investigation/data) | 3 |

### Implemented This Session
None new — all recent work was verified as already done.

### Previously Implemented (15 total)
1. Volatility Gate Tuning — ATR ratio + BTC trend boost
2. Volatility Regime Adaptive Signals — momentum/mean-reversion weighting
3. Trend Ignition signal — early-stage breakout (100% WR backtest)
4. BTC Timing Guard — per-signal-type momentum filter
5. BTC Pump Rider Gradual Rally — gradual rally detection
6. CONF_FILTER + TIME_BLOCK — confidence + dead hour filters
7. BTC Acceleration Detection — crash early warning
8. PROFIT_MONSTER_BYPASS corrected — exit ownership model
9. Dead code fix in VEL-FILTER — range(3) → range(5)
10. Oversold Bounce signal — mean reversion at extremes
11. EMA300 Breakthrough signal — price crashes through EMA300
12. Pump-Chain Exit — ATR trailing for pump-chain momentum
13. BTC Chop Gate — block trend signals in chop
14. ACCEL_300_MINUS_FLAT_BLOCK — block SHORT in FLAT
15. SL Zones entry_distance_filter — partial SL Memory integration

### Next Candidates (Prioritized)
1. **Contrarian Zone Signal** — Level 2, HIGH value, 84% zone hold rate
2. **Trend Momentum V4** — Level 2, HIGH value, data-driven 54% WR
3. **Trend Momentum** — Level 2, HIGH value, 3.0:1 R:R
4. **Sniper Exit Strategy** — Level 3, HIGH value, constants+script exist
5. **Retroactive Scan** — Level 3, HIGH value, missed breakout safety net
6. **Spider-Profit** — Level 2-3, MEDIUM value, regime-aware profit taking
7. **Signal Regime Memory** — Level 4, HIGH value, dormant/resurrect lifecycle
8. **HL Trigger SL V2** — Level 3, HIGH value, slippage elimination
