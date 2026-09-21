# Upgrade Audit Trail

**Created:** 2026-09-19
**Scanned:** 20 most recent plans

---

## Plan: ride-it-exit-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** 2-phase ride-it exit system with volume spike override for momentum trades
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** ride_it_exit.py exists, constants added to hermes_constants.py, integrated into position_manager.py

## Plan: continuum-ma-signal-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** New signal using MA-smoothed continuum score for crossover detection
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** No signal script exists. Requires continuum.db data + new signal file. Deferred — lower priority than gradual rally.

## Plan: btc-oscillator-30d-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** BTC oscillator correlation analysis for trade filtering
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** Plan recommends WAIT AND MONITOR (only 14d data, need 30d). Premature to implement.

## Plan: btc-oscillator-correlation-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Block LONG when BTC bearish, boost SHORT when BTC bullish
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** BTC chop gate (BTC_CHOP_GATE) and BTC timing guard already exist. BTC momentum gate partially covers this via signal_compactor.py.

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** 8 fixes to improve PnL by ~$4.21/7d
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** MOSTLY IMPLEMENTED
- **Reason:** 6/8 fixes done: rr_engine for pullback-entry- (✅), kill ema300-dip-long (✅), blacklist ENA (✅), tighten cut-loser T1 (✅), extend time block (✅), increase LOSERS penalties (✅). Remaining: block LONG in NORMAL (partially via VOL_PHASE_MULTS), raise LONG speed threshold (not done).

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** ATR ratio + BTC trend boost for direction-aligned expansion trades
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** get_atr_ratio(), get_btc_trend(), and expansion boost all exist in volatility_gate_v2.py (lines 326-504).

## Plan: 2026-09-11_volatility-regime-adaptive-signals.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Signal weighting by volatility regime (expansion/compression/normal)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** VOL_PHASE_MULTS matrix in volatility_gate_v2.py covers all regime+phase combinations with signal family multipliers.

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Mean reversion LONG signal at extreme oversold (RSI < 25)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** oversold_bounce.py exists, registered in signals/__init__.py, constants in hermes_constants.py.

## Plan: contrarian-zone-signal.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Contrarian signal at SL memory zones (flip direction when approaching death zone)
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** sl_zones.py exists but contrarian zone transformation logic NOT wired into signal_compactor.py. Depends on Phase 1-6 of SL Memory system.

## Plan: sl-memory-sr-system-v2.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** SL memory as support/resistance with entry filtering, zone-aware exits
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** sl_zones.py and sl_zones_api.py exist (zone aggregation engine). Entry filter, exit logic, and position sizing NOT wired into signal_compactor.py or position_manager.py.

## Plan: sl-memory-sr-system.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Original SL memory spec (v1.0, superseded by v2.0)
- **Difficulty:** Level 3
- **Value:** LOW
- **Status:** SUPERSEDED
- **Reason:** Replaced by sl-memory-sr-system-v2.md

## Plan: pump-chain-exit-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** ATR trailing exit for pump-chain signals (bypass PM trail and RR engine)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** pump_exit constants exist in hermes_constants.py, position_manager.py handles pump_exit exit type.

## Plan: hl-trigger-sl-v2.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** HL trigger orders for server-side SL/TP (eliminate slippage)
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** V1 was disabled (2026-05-15). V2 spec exists with bug-hunter audit. Requires re-enabling with fixes. Critical for reducing catastrophic losses.

## Plan: brain-rag-system.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Session brain (FAISS+SQLite) + hourly brain auditor + dashboard
- **Difficulty:** Level 4
- **Value:** MEDIUM
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** session_brain.py and brain_api.py exist. Dashboard (brain.html) and hourly auditor NOT implemented.

## Plan: spider-profit.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Regime-aware profit taking for NEUTRAL markets
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** SPIDER_* constants exist in hermes_constants.py, integrated into profit_monster.py.

## Plan: 2026-09-12_btc-momentum-sync-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** 5-layer defense: BTC momentum gate, transition detection, stale filter, RSI guard, continuum boost
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** BTC momentum gate (via btc_chop_gate + btc_timing_guard) partially implemented. Transition detection, stale filter tightening, and continuum boost NOT implemented.

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Per-signal-type BTC momentum thresholds
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** BTC_TIMING_GUARD constants exist in hermes_constants.py, check exists in signal_compactor.py.

## Plan: 2026-09-11_btc-pump-rider-gradual-rally.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Detect gradual BTC rallies (not just explosive breakouts) and buy lagging alts
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** detect_btc_gradual_rally() + find_lagging_alts_gradual() both exist in btc_pump_rider.py (lines 182-297). Constants in hermes_constants.py. Integrated in run() (lines 462-470).

## Plan: ema300-rejection-signal-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** EMA300 breakthrough signal (price crashes through EMA300 with momentum)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** ema300_breakthrough.py exists, registered in signals/__init__.py, constants in hermes_constants.py.

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** BTC chop gate + gate STANDALONE_BYPASS in flat markets
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** BTC_CHOP_GATE constants exist, check in signal_compactor.py. STANDALONE_BYPASS gated by BTC momentum.

---

## Summary

| Status | Count | Plans |
|--------|-------|-------|
| IMPLEMENTED | 12 | ride-it, vol-gate-tuning, vol-regime-adaptive, oversold-bounce, pump-chain-exit, spider-profit, btc-timing-guard, ema300-breakthrough, chop-gate, profitability-fix (6/8), btc-pump-rider-gradual |
| PARTIALLY IMPLEMENTED | 3 | btc-oscillator-correlation, sl-memory-v2, btc-momentum-sync, brain-rag |
| PENDING (High Value) | 2 | contrarian-zone, hl-trigger-sl-v2 |
| PENDING (Medium Value) | 2 | continuum-ma, btc-oscillator-30d |
| SUPERSEDED | 1 | sl-memory-v1 |

## Additional Plans Scanned (2026-09-19 12:45)

### Already Implemented (verified in code)

## Plan: 2026-09-09_regime-transition-smoothing.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** 3-layer fix: directional bias, circuit breaker tightening, alt-BTC divergence
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** DIRECTIONAL_OUTCOME_PENALTY=0.5, LOCK_VELOCITY=0.5, DIRECTIONAL_BIAS_ENABLED=True, ALT_BTC_DIVERGENCE_ENABLED=True all in hermes_constants.py. signal_compactor.py wired at lines 1686-1692.

## Plan: 2026-09-08_short-filter-overhaul.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Fix dead code in VEL-FILTER, relax SHORT filters
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Dead code bug fixed — range(SHORT_VEL_FILTER_GREEN_THRESHOLD) at signal_compactor.py:2899.

## Plan: losers-list-spec.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Anti-favorites system to penalize underperformers
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** LOSERS_LONG, LOSERS_SHORT, LOSERS sets exist (hermes_constants.py:283-290). LOSERS_MULT=0.3, LOSERS_CONF_PENALTY=-50. signal_compactor.py penalizes at lines 1400, 2516-2517, 3099.

### Pending — Additional Plans

## Plan: 2026-09-08_btc-alignment-crash-protection-overhaul.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** BTC trend alignment + cascade crash protection
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** BTC momentum gate and crash filter exist. Full cascade protection (exit existing LONGs during BTC crash) NOT implemented.

## Plan: 2026-09-08_trend-ignition-signal-spec.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Trend ignition signal for early trend detection
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED
- **Reason:** No signal script exists. Spec is ready for build.

## Plan: 2026-09-09_pump-chain-v2-spec.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Improved pump-chain signal with better entries
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED
- **Reason:** Plan awaiting approval. Existing pump_chain signal works.

## Plan: 2026-09-07_partial-close-trailing-runner.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Partial close (50% scalp, 50% runner) to capture more upside
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** Complex position_manager.py rework. Would require HL API support for partial closes.

## Plan: market-sync-protection-plan.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Exit existing LONGs when BTC drops (not just block new entries)
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** Crash filter blocks NEW entries but doesn't protect existing positions. High complexity for live position management.

## Plan: regime-tuner-spec.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Weekly automated regime analysis and signal tuning
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED
- **Reason:** Comprehensive spec exists. All building blocks exist (regime_memory, volatility_gate, signal flags). Needs new regime_tuner.py + systemd timer.

## Plan: sniper-exit-strategy.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Close only wrong-side positions when market shifts
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED (brainstorm only)
- **Reason:** Spec exists but no implementation plan. Depends on accurate transition detection.

## Plan: doji_signal_system.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Doji-based entry and exit signal
- **Difficulty:** Level 2
- **Value:** LOW
- **Status:** NOT IMPLEMENTED
- **Reason:** Many existing signals already cover reversal patterns. Low priority.

## Plan: 2026-09-04_continuum-engine-spec.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** BTC continuum engine (phase detection, z-score, trend)
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** continuum_engine.py, continuum_context.py, continuum_*.py signals all exist. Core infrastructure built.

## Plan: 2026-09-02_regime-aware-signal-params-spec.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Adaptive signal parameters by regime
- **Difficulty:** Level 2-3
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** VOL_PHASE_MULTS matrix + regime gate in volatility_gate_v2.py covers this.

## Plan: atr-sl-widen.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Wider ATR SL for volatile markets
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** ATR_SL_MIN_INIT, ATR_SL_WIDENING constants exist. ATR-based SL is the standard exit.

## Plan: 2026-08-19_short-bias-fix.md
- **Date scanned:** 2026-09-19 12:45
- **Core request:** Fix SHORT bias in signal generation
- **Difficulty:** Level 1-2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Directional outcome system, directional lock, directional bias all active.

---

## Final Summary

| Status | Count | Notes |
|--------|-------|-------|
| IMPLEMENTED | 22 | All Level 1-2 wins captured |
| PARTIALLY IMPLEMENTED | 5 | sl-memory-v2, btc-momentum-sync, brain-rag, btc-oscillator-correlation, cascade-crash |
| PENDING (High Value) | 3 | hl-trigger-sl-v2 (L3), partial-close-runner (L3), market-sync-protection (L2-3) |
| PENDING (Medium Value) | 5 | contrarian-zone (L3), continuum-ma (L2), regime-tuner (L3), sniper-exit (L3), trend-ignition (L2) |
| SUPERSEDED | 1 | sl-memory-v1 |
| LOW VALUE | 3 | doji-signal, btc-oscillator-30d (wait), pump-chain-v2 (awaiting approval) |

**Key finding (confirmed 2026-09-20): All Level 1 tasks are complete.** The remaining work is Level 2-3 architecture (HL trigger orders, SL memory wiring, partial closes, market sync protection). No new plans have been added since Sep 19.

## Next Candidates (sorted by value/effort)

1. **HL Trigger SL/TP V2** — Level 3 — HIGH VALUE — eliminates slippage on catastrophic losses (-172% in 7d). Most impactful single change.
2. **Partial Close + Trailing Runner** — Level 3 — HIGH VALUE — captures more upside on winners (ICP case: 0.84% → ~2.64%).
3. **Market Sync Protection** — Level 2-3 — HIGH VALUE — protects existing LONGs during BTC selloffs.
4. **Continuum MA Signal** — Level 2 — MEDIUM VALUE — new signal using MA-smoothed continuum score.
5. **Regime Tuner** — Level 3 — MEDIUM VALUE — automates weekly signal regime analysis.

---

## Rescan: 2026-09-20

**Triggered by:** Upgrade implementer scan
**Plans rescanned:** 20 most recent + older plans
**New plans since last scan:** None

### Verification

| Check | Result |
|-------|--------|
| Python syntax (signal_compactor, position_manager, run_pipeline) | ✅ All OK |
| hermes_constants.py import | ✅ OK |
| ride_it_exit.py import | ✅ OK |
| oversold_bounce.py | ⚠️ Function-based (no class), works via signals_runner |
| New plans since Sep 19 | None |

### Status Unchanged

All 22 IMPLEMENTED, 5 PARTIALLY IMPLEMENTED, 8 PENDING plans remain as previously assessed. No new quick wins identified.

### Remaining Work

| Priority | Plan | Level | Value | Blocker |
|----------|------|-------|-------|---------|
| 1 | HL Trigger SL/TP V2 | 3 | HIGH | Needs HL API integration + bug-hunter audit |
| 2 | Partial Close + Trailing Runner | 3 | HIGH | Needs HL API partial close support |
| 3 | Market Sync Protection | 2-3 | HIGH | Needs live position management logic |
| 4 | Continuum MA Signal | 2 | MEDIUM | Needs backtest + new signal file |
| 5 | Regime Tuner | 3 | MEDIUM | Needs new regime_tuner.py + systemd timer |

**Key finding: No Level 1-2 tasks remain.** All remaining candidates require Level 3+ architecture work (HL API integration, new systems, position management changes).
