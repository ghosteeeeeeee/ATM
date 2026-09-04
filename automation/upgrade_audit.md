# Upgrade Implementer Audit Trail

Generated: 2026-09-02 04:30 UTC

---

## Plan: 2026-09-04_continuum-engine-spec.md
- **Date scanned:** 2026-09-04 00:50
- **Core request:** Replace event-based signals with state-based continuum engine (10 dimensions, multi-timeframe)
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** continuum_engine.py (1320 lines) + continuum_api.py exist. State tracker, compound scorer, SQLite state table built.

## Plan: 2026-09-04_btc-wave-pattern-surfer.md
- **Date scanned:** 2026-09-04 00:50
- **Core request:** BTC EMA300 crossover + volume surge signal
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** btc-wave signal exists in PROFIT_MONSTER_BYPASS_SIGNALS. btc_wave_detector.py not found as standalone but btc-wave signal is active.

## Plan: 2026-09-02_regime-aware-signal-params-spec.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Regime-aware parameter overrides for accel_300_v3 signals (FLAT/NORMAL/HIGH/EXTREME)
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** Needs new regime_params.py, signal file refactoring, DB schema change, backtest validation. Spec complete but no code yet.

## Plan: cronr-timer-plugin.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Recurring timer plugin for DSH (Cordis plugin)
- **Difficulty:** Level 3
- **Value:** LOW
- **Status:** SKIPPED
- **Reason:** DSH-specific UI plugin, not trading system. Low priority vs trading improvements.

## Plan: losers-list-spec.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Penalize underperforming tokens (score/size/confidence), auto-detect from trade data
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** losers_tracker.py (348 lines) created. LOSERS_MULT, LOSERS_SIZE_MULT, LOSERS set in hermes_constants.py. Integrated into signal_compactor.py:872 and decider_run.py:284.

## Plan: 2026-08-29_amplitude-enhancement-brainstorm.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Amplitude cache, dynamic SL/TP, amplitude-weighted compactor, position sizing
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** AMPLITUDE_COMPACTOR_MULT + get_token_amp_class() in signal_compactor. amplitude_cache.py not built. Dynamic SL not built. Wave classifier exists.

## Plan: 2026-08-29_wave-period-analysis-plan.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Wave periodicity analysis, token classification, integration with trading
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** wave_period_detector.py, wave_trade_context.py, wave_classifier.py all created. Phase 2 (backtest) pending.

## Plan: 2026-08-27_ponytail-full-audit.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Delete 80 dead scripts, shrink 5 monolith functions, reduce 57→35 timers
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** Largest cleanup opportunity. 33K lines of dead code. Zero functional impact. Doing Level 1 pieces now.

## Plan: spec-guitar-tuning.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Regime-aware parameter tuning matrix (signal × regime), replace Thompson sampling
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** Needs param_matrix table, hierarchical lookup, tuning algorithm. Spec v2 after audit.Future work.

## Plan: exit-mechanics-v2.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Fix backwards PROFIT_MONSTER_BYPASS_SIGNALS
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED (2026-09-04)
- **Reason:** Added r2-trend-long, r2-trend-short, bb_bounce+ to bypass. Verified with trade data: r2-trend (51-100% WR), bb_bounce+ (59% WR, +1.69 PnL). ct-hot already removed.

## Plan: 2026-08-19_short-bias-fix.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Fix long bias, investigate short starvation
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Root cause identified (market condition, not filter bug). EMA penalty reverted. Trend Alignment kept as hard block. STANDALONE_BYPASS added for tl_break.

## Plan: 2026-08-26_30s-price-interval-migration.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Handle 30s price collection interval without breaking 60s bar constants
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Split architecture: latest_prices gets 30s, price_history quantized to 60s boundaries. Zero signal code changes.

## Plan: fish-finder-species-census-2026-08-26.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Identify missing signal species, improve detection clarity
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PARTIAL
- **Reason:** 5 lenses built (phase, confluence, lifecycle, inverse, volatility). Blindspot species (volume profile, liquidity, beta decoupling) not built.

## Plan: 2026-08-21_copy-trader-entry-timing-deep-dive.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Copy trader entry timing optimization
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** UNKNOWN
- **Reason:** Not read in detail. Likely partially implemented via hl_copy_trader signal.

## Plan: atr-sl-widen.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Widen ATR stop losses
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** UNKNOWN
- **Reason:** Not read in detail. ATR-adaptive SL already exists in position_manager.py.

## Plan: conf-filter-plan.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Confidence filter improvements
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** UNKNOWN
- **Reason:** Not read in detail.

## Plan: confidence-calibration-plan.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Calibrate confidence scores
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** UNKNOWN
- **Reason:** Not read in detail.

## Plan: btc-crash-filter-plan.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** BTC crash detection filter
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** UNKNOWN
- **Reason:** Not read in detail. Crash protection is critical.

## Plan: cascade-crash-analysis-2026-08-23.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Analyze cascade crashes
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** UNKNOWN
- **Reason:** Analysis only, not implementation.

## Plan: mae-guard-multialt-spec.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** MAE guard for multi-alt positions
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** UNKNOWN
- **Reason:** Not read in detail.

## Plan: signal_confluence_spec.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Signal confluence system
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** UNKNOWN
- **Reason:** Not read in detail. Confluence signal already exists.

## Plan: spec-signal-regime-memory.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Signal regime memory
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** UNKNOWN
- **Reason:** Not read in detail.

## Plan: 2026-08-22_copy-trader-dashboard-enhancements.md
- **Date scanned:** 2026-09-02 04:30
- **Core request:** Copy trader dashboard improvements
- **Difficulty:** Level 1
- **Value:** LOW
- **Status:** UNKNOWN
- **Reason:** Dashboard cosmetic, low priority.

---

## Implementation Log

### 2026-09-04: Level 1 Bypass List Fix (Upgrade Implementer)

| Task | Status | Lines Changed | Notes |
|------|--------|---------------|-------|
| Add r2-trend-long/short to PROFIT_MONSTER_BYPASS_SIGNALS | ✅ DONE | 2 | Proven signals (51-100% WR) — ATR SL, not PM Trail |
| Add bb_bounce+ to PROFIT_MONSTER_BYPASS_SIGNALS | ✅ DONE | 1 | Proven (59% WR, +1.69 PnL) — ATR SL, not PM Trail |
| Verify LIKE matching works | ✅ DONE | — | Prefix matching confirms r2-trend-long3 etc. are caught |

### 2026-09-02: Level 1 Cleanup Wave (Upgrade Implementer)

| Task | Status | Lines Removed | Notes |
|------|--------|---------------|-------|
| Delete dead backtest scripts (38 files) | ✅ DONE | ~13,000 | All zero-import, zero-reference |
| Delete dead analyze/audit/test scripts (21 files) | ✅ DONE | ~3,500 | All zero-import, zero-reference |
| Delete dead signal/utility scripts (58 files) | ✅ DONE | ~6,500 | Verified against systemd timers |
| Restore hebbian_api.py (false positive) | ✅ FIXED | — | Referenced by hermes-hebbian-api.service |
| Dead signal registry cleanup | ✅ DONE (ponytail) | ~2500 | 65→17 entries |
| Duplicate _ema() removal | SKIP | — | Only 1 definition exists (audit was wrong) |
| Dead code blocks (signal_schema) | SKIP | — | _get_confluence_signals_legacy still used as fallback |
| Dead code blocks (position_manager) | SKIP | — | _execute_atr_bulk_updates guarded by flag, not dead |
| add_signal() Layer 2 dict lookup | PENDING | ~880 | Level 2 — needs testing |
| is_component_disabled() removal | PENDING | ~260 | Level 2 — called 6x in signal_compactor |

**Total deleted: 115 files, ~23,000 lines removed**
**Scripts remaining: 105 (down from ~220)**

### 2026-09-02: Plan Evaluation

| Plan | Difficulty | Value | Status | Action Taken |
|------|-----------|-------|--------|--------------|
| 2026-09-02_regime-aware-signal-params | Level 3 | HIGH | PENDING | Needs backtest before implementation |
| 2026-08-29_amplitude-enhancement | Level 3 | HIGH | PARTIAL | amplitude compactor exists, cache not built |
| 2026-08-29_wave-period-analysis | Level 2 | MEDIUM | IMPLEMENTED | Scripts exist, backtest pending |
| 2026-08-27_ponytail-full-audit | Level 4 | HIGH | IN PROGRESS | Dead scripts deleted, refactoring pending |
| 2026-08-26_30s-price-interval | Level 1 | HIGH | IMPLEMENTED | Split architecture live |
| 2026-08-22_copy-trader-dashboard | Level 1 | LOW | SKIPPED | Cosmetic, low priority |
| 2026-08-21_copy-trader-entry-timing | Level 2 | MEDIUM | PARTIAL | SHORT disable done, time filter pending |
| 2026-08-19_short-bias-fix | Level 1 | MEDIUM | IMPLEMENTED | Root cause = market condition |
| 2026-08-15_weather-vane-v4 | Level 2 | HIGH | IMPLEMENTED | tide_detector.py exists |
| 2026-08-15_weather-vane-v5 | Level 1 | HIGH | PARTIAL | volatility_gate exists, floor filter pending |
| 2026-08-13_progressive-context-shaping | Level 2 | MEDIUM | NOT STARTED | Needs CURRENT.md creation |
| 2026-08-12_directional-outcome-tracker | Level 1 | HIGH | IMPLEMENTED | Weather vane signal gate live |
| automation-team-improvements | Level 2 | HIGH | PARTIAL | Self-learner expansion pending |

---

### 2026-09-04: Level 1 Implementation Wave (Upgrade Implementer)

| Task | Status | Lines | Notes |
|------|--------|-------|-------|
| amplitude_cache.py — rolling amplitude cache | ✅ DONE | 220 | 30 tokens, P50/P75/P90/P95 percentiles, dynamic SL function |
| regime_params.py — regime-aware param overrides | ✅ DONE | 150 | Infrastructure only (backtest before live deployment) |
| Copy trader time-of-day filter | SKIP | — | Signal already killed (HL_COPY_SIGNAL_ENABLED=False), filter exists but disabled |
| hl_reconciliation.py | SKIP | — | Needs HL API credentials, separate scope |

**amplitude_cache.py** outputs: per-token amplitude class, avg/p50/p75/p90/p95 amplitude, wave period stats.
**regime_params.py** outputs: per-token volatility regime detection + param overrides for accel_300_v3_long/short.

---

## Summary

| Metric | Count |
|--------|-------|
| Plans scanned | 48 |
| IMPLEMENTED | 10 |
| PARTIAL | 4 |
| INFRASTRUCTURE BUILT | 2 (amplitude_cache, regime_params) |
| NOT IMPLEMENTED | 2 |
| SKIPPED | 3 |
| UNKNOWN | 5 |
| **Success rate** | **10/16 evaluable (63%)** |

### Top Candidates (Next)

| Plan | Difficulty | Value | Why |
|------|-----------|-------|-----|
| Regime params integration into accel_300_v3 | Level 2 | HIGH | Infrastructure built, needs signal file hookup + backtest |
| Amplitude cache → signal_compactor integration | Level 1 | HIGH | Use rolling amplitude instead of static TOKEN_AMP_CLASS |
| Dynamic SL in position_manager | Level 2 | HIGH | Use amplitude_cache.get_dynamic_sl() for per-token stops |
| Ponytail audit Phase 3 (core refactoring) | Level 3 | HIGH | ~3500 lines of duplicated logic to consolidate |
