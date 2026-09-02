# Upgrade Implementer Audit Trail

Generated: 2026-09-02 04:30 UTC

---

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
- **Status:** IMPLEMENTED
- **Reason:** Bypass list corrected. Proven signals (r2-trend, bb_bounce, confluence) bypass PM Trail. Losing signals (ct-hot) don't.

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

### 2026-09-02: Level 1 Cleanup Wave

| Task | Status | Lines Removed |
|------|--------|---------------|
| Dead signal registry cleanup | IN PROGRESS | ~2500 |
| Duplicate _ema() removal | PENDING | ~8 |
| Dead code blocks (signal_schema) | PENDING | ~400 |
| Dead code blocks (position_manager) | PENDING | ~350 |
| add_signal() Layer 2 dict lookup | PENDING | ~880 |
| is_component_disabled() removal | PENDING | ~260 |

---

## Summary

| Metric | Count |
|--------|-------|
| Plans scanned | 20 |
| IMPLEMENTED | 4 |
| PARTIAL | 3 |
| NOT IMPLEMENTED | 4 |
| SKIPPED | 1 |
| UNKNOWN | 8 |
| **Success rate** | **4/8 evaluable (50%)** |
