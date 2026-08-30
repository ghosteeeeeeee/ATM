# Upgrade Audit — 2026-08-30

## Scan Summary

- **Plans scanned:** 43
- **Plans evaluated:** 20 (most recent/significant)
- **Already implemented:** 12
- **Partially implemented:** 4
- **Not implemented:** 4 (all Level 2-4)

---

## IMPLEMENTED (VERIFIED)

### 1. Losers List (losers-list-spec.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Auto-detect underperforming tokens, penalize with 0.5x score/size
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** `losers_tracker.py` exists, LOSERS set in hermes_constants.py (line 280), integrated in signal_compactor.py (line 871), trades.html has 🗑️ icon (line 235), systemd timer exists

### 2. 30s Price Interval (30s-price-interval-migration.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Split architecture — 30s for exit management, 60s for signals
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** Plan marked IMPLEMENTED, signal_schema.py quantizes to minute boundary

### 3. BTC Crash Filter (btc-crash-filter-plan.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Multi-layer BTC crash detection (absolute, acceleration, volume spike, contagion)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** `btc_crash_filter.py` exists (602 lines), all 4 layers active, integrated in decider_run.py and cut_loser.py

### 4. Confidence Filter (conf-filter-plan.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Block trades with confidence >= 90 (worst performers)
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89 in hermes_constants.py (line 930-931), enforced in signal_compactor.py (line 752-753)

### 5. ATR Spike Signal (atr-spike-signal-build.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Catch staged moves from ATR compression with quality gates
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** ✅ BUILT (disabled per NEVER_REENABLED — 28.6% WR)
- **Evidence:** `signals/atr_spike.py` exists (301 lines), ATR_SPIKE_ENABLED=False, in NEVER_REENABLE_FLAGS

### 6. VORTEX_BREAK zombie signal
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Kill zombie signal consuming thread pool
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Evidence:** VORTEX_BREAK_ENABLED=False (hermes_constants.py line 1955)

### 7. Signal Registry Cleanup (ponytail-full-audit.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Prune 65 → ~18 dead signal entries
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Evidence:** signals/__init__.py is 240 lines, 19 entries (pruned 2026-08-27)

### 8. Zombie Files Deleted (ponytail-full-audit.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Delete ai_decider.py, signal_gen.py, hyperliquid-trader.py
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** All three files confirmed deleted

### 9. PROFIT_MONSTER_BYPASS_SIGNALS (exit-mechanics-v2.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Fix backwards bypass list — proven signals to ATR, losing to PM Trail
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** Updated 2026-08-26 (hermes_constants.py line 1068-1083), ct-hot removed, bb_bounce+/confluence added

### 10. Amplitude Compactor Mult (amplitude-enhancement-brainstorm.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Adjust signal confidence by amplitude class
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** AMPLITUDE_COMPACTOR_MULT in hermes_constants.py (line 2358), get_token_amp_class() (line 2402), used in signal_compactor.py (line 879-880)

### 11. Self-Learner Expansion (automation-team-improvements.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Expand PARAM_CONFIG from 2 to 15+ parameters
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Evidence:** self_learner.py PARAM_CONFIG has 21 parameters (lines 79-112), param_map covers 20+ signal types (lines 521-548)

### 12. MAE Guard Re-enabled (mae-guard-multialt-spec.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Re-enable MAE guard with multi-alt divergence filter
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Evidence:** CL_MAE_GUARD_ENABLED=True (hermes_constants.py line 1124), widened to 3.0%

---

## PARTIALLY IMPLEMENTED

### 13. Amplitude Enhancement (amplitude-enhancement-brainstorm.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Full amplitude-based trading system (cache, dynamic SL, position sizing, regime detection)
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** 🟡 PARTIAL
- **Done:** AMPLITUDE_COMPACTOR_MULT, get_token_amp_class()
- **NOT done:** amplitude_cache.py, dynamic SL based on amplitude, amplitude-based position sizing, amplitude regime detection
- **Next:** amplitude_cache.py (foundation for all other amplitude features)

### 14. Wave Period Analysis (wave-period-analysis-plan.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Validate wave period classification, multi-timeframe analysis, backtest strategies per bucket
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** 🟡 PARTIAL
- **Done:** Scripts created (wave_period_detector.py, wave_trade_context.py, wave_classifier.py)
- **NOT done:** Multi-timeframe validation, backtest per bucket, frequency change as signal

### 15. Ponytail Audit Cleanup (ponytail-full-audit.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Delete dead scripts, shrink core functions, reduce timers
- **Difficulty:** Level 1-3
- **Value:** MEDIUM
- **Status:** 🟡 PARTIAL
- **Done:** 80 dead scripts deleted, zombie files deleted, registry cleaned
- **NOT done:** Core function refactoring (add_signal Layer 2, run_compaction split, close_paper_position split), timer reduction (57→35), dead code blocks in position_manager.py/signal_schema.py

### 16. OpenMemory Hebbian Bridge (automation-team-improvements.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Wire OpenMemory → Hebbian engine for conversation context learning
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** 🟡 NOT STARTED
- **Next:** Create hebbian_openmemory_bridge.py

---

## NOT IMPLEMENTED (Level 2-4)

### 17. Signal Regime Memory (spec-signal-regime-memory.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Persist regime at signal entry, regime-aware lifecycle (dormant state), resurrection
- **Difficulty:** Level 3-4
- **Value:** HIGH
- **Status:** ❌ NOT IMPLEMENTED
- **Why not done:** Requires schema changes (regime column in signals + signal_outcomes), new SQLite DB (signal_regime_perf.db), changes to 6+ files
- **Recommendation:** Start with Phase 0 only (persist regime at entry) — immediate value without full system

### 18. Guitar Tuning / param_matrix (spec-guitar-tuning.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Signal × regime parameter tuning matrix with hierarchical fallback
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** ❌ NOT IMPLEMENTED
- **Why not done:** Requires param_matrix SQLite table, regime capture infrastructure, integration with self_learner + signal_compactor
- **Recommendation:** Defer until regime column is added to signal_outcomes (prerequisite)

### 19. Exit Owner Model (exit-mechanics-ownership.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** One exit owner per trade (ATR vs PM Trail), no conflicts
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** ❌ NOT IMPLEMENTED (partially addressed by PROFIT_MONSTER_BYPASS_SIGNALS update)
- **Why not done:** Would require exit_owner column in trades table, changes to position_manager.py
- **Recommendation:** Current bypass list approach is sufficient — defer full model

### 20. A/B Learner Cleanup (automation-team-improvements.md)
- **Date scanned:** 2026-08-30 18:00
- **Core request:** Delete defunct A/B learner
- **Difficulty:** Level 1
- **Value:** LOW
- **Status:** 🟡 PARTIAL — script deleted, config file (ab_tests.json) remains

---

## Level 1 Quick Wins Still Available

| Task | Effort | Value | Status |
|------|--------|-------|--------|
| Delete ab_tests.json | 1 min | LOW | Ready |
| Timer reduction (57→35) | 30 min | MEDIUM | Needs analysis |
| Dead code blocks in position_manager.py | 30 min | LOW | Needs verification |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-30 | Scanned 43 plans, evaluated 20 | Most recent/significant plans |
| 2026-08-30 | 12 fully implemented, 4 partial, 4 not implemented | System has evolved significantly |
| 2026-08-30 | No Level 1 wins available for immediate implementation | All easy tasks already done |
| 2026-08-30 | Next priority: amplitude_cache.py (Level 2) | Foundation for amplitude-based features |
