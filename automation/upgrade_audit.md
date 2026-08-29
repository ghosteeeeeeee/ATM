# Upgrade Implementer — Audit Trail

**Scanned:** 2026-08-29 04:30 UTC
**Plans scanned:** 43

---

## Plan Evaluation Summary

| Status | Count | Notes |
|--------|-------|-------|
| ✅ IMPLEMENTED | 8 | Already done before this scan |
| 🔄 IN PROGRESS | 2 | Partially done, waiting on dependencies |
| ⏳ PENDING (Level 1) | 6 | Easy wins, ready to implement |
| ⏳ PENDING (Level 2) | 3 | Medium complexity, needs design |
| ⏳ PENDING (Level 3+) | 4 | Complex, defer for now |
| ❌ SKIPPED | 20 | Too complex, low value, or superseded |

---

## Implemented Plans (No Action Needed)

### 1. losers-list-spec.md
- **Core request:** Auto-detect and penalize underperforming coins
- **Difficulty:** Level 2
- **Status:** ✅ IMPLEMENTED — `losers_tracker.py` exists, `LOSERS` set in hermes_constants.py, systemd timer configured
- **Reason:** Full implementation exists. Dead code cleanup could improve it but core is done.

### 2. vortex_break zombie signal
- **Core request:** Disable vortex_break consuming thread pool for zero output
- **Difficulty:** Level 1
- **Status:** ✅ IMPLEMENTED — `VORTEX_BREAK_ENABLED = False` with NEVER_REENABLE comment
- **Reason:** Already fixed per ponytail audit 2026-08-27.

### 3. 30s-price-interval-migration
- **Core request:** Split architecture for 30s price collection
- **Difficulty:** Level 1
- **Status:** ✅ IMPLEMENTED — Dual-track writes in place, signals use 60s bars
- **Reason:** Complete. Migration spec deferred (not needed with split architecture).

### 4. exit-mechanics-v2 (BYPASS_SIGNALS fix)
- **Core request:** Fix backwards PROFIT_MONSTER_BYPASS_SIGNALS list
- **Difficulty:** Level 1
- **Status:** ✅ IMPLEMENTED — Proven signals (r2-trend, bb_bounce, confluence) in bypass; losing signals (ct-hot) removed from bypass
- **Reason:** Already corrected. List now matches signal performance data.

### 5. mae-guard-multialt-spec
- **Core request:** Re-enable MAE Guard at 2.0% with ATR-aware scaling
- **Difficulty:** Level 1
- **Status:** ✅ IMPLEMENTED — `CL_MAE_GUARD_ENABLED = True`, widened to 3.0% on 2026-08-26
- **Reason:** Already re-enabled. BTC crash filter also exists as btc_crash_filter.py.

### 6. confidence-calibration-plan
- **Core request:** Fix non-monotonic confidence curve
- **Difficulty:** Level 2
- **Status:** ✅ INVESTIGATED — Existing CONF_FILTER (raw ≥ 90) already blocks worst tier
- **Reason:** Multiple investigation rounds concluded existing filter is sufficient. No code change needed.

### 7. short-bias-fix
- **Core request:** Investigate why system is long-biased
- **Difficulty:** Level 1
- **Status:** ✅ INVESTIGATED — Root cause is market conditions (bull market), not filter bugs
- **Reason:** Counter-trend SHORTs correctly blocked (26% WR). Trend-aligned SHORTs work (54% WR). No changes needed.

### 8. signal registry pruning
- **Core request:** Clean dead signals from registry
- **Difficulty:** Level 1
- **Status:** ✅ IMPLEMENTED — Registry pruned 65 → 15 entries on 2026-08-27
- **Reason:** Dead signal families removed. Flags preserved in hermes_constants.py for documentation.

---

## Pending Level 1 Tasks (Easy Wins)

### 9. Dead code blocks in signal_schema.py (~400 lines)
- **Core request:** Remove unreachable code
- **Difficulty:** Level 1
- **Value:** MEDIUM — Reduces codebase noise, prevents confusion
- **Status:** ⏳ PENDING
- **Blocks:** None
- **Key dead blocks:** `ALLOWED_SIGNAL_SOURCES` frozenset, `expire_pending_signals()`, legacy migration code, `_get_confluence_signals_legacy()`

### 10. _ema() deduplication in signal_schema.py
- **Core request:** Same 4-line function defined 3 times
- **Difficulty:** Level 1
- **Value:** LOW — DRY cleanup, prevents future drift
- **Status:** ⏳ PENDING
- **Lines:** signal_schema.py:439, 561, 631

### 11. Dead code in position_manager.py (~350 lines)
- **Core request:** Remove unreachable exit code blocks
- **Difficulty:** Level 1
- **Value:** MEDIUM — TIME_EXIT + PEAK_EXIT blocks dead, volume cache dead
- **Status:** ⏳ PENDING
- **Key dead blocks:** `_execute_atr_bulk_updates()`, volume cache system, TIME_EXIT + PEAK_EXIT blocks

### 12. Remove hyperliquid-trader.py
- **Core request:** File duplicates position_manager SL/TP monitoring
- **Difficulty:** Level 1
- **Value:** LOW — Prevents conflicting close operations
- **Status:** ⏳ PENDING
- **Risk:** Need to verify no systemd timer references it

### 13. Merge redundant systemd timers
- **Core request:** Consolidate overlapping timers
- **Difficulty:** Level 1
- **Value:** LOW — Reduces CPU churn
- **Status:** ⏳ PENDING
- **Candidates:** signal-report + signal-reporter, health-monitor + smoke-test + watchdog, duplicate regime scanners

### 14. Clean stale signal_gen imports
- **Core request:** Remove dead imports from disabled signals
- **Difficulty:** Level 1
- **Value:** LOW — Signals are disabled, imports never execute
- **Status:** ⏳ PENDING
- **Files:** phase_accel.py, pump_catcher.py, trend_purity.py, ma_cross_5m.py, accel_300.py, inverse_accel_300.py

---

## Pending Level 2 Tasks (Medium Complexity)

### 15. Signal Regime Memory — "Species of Fish"
- **Core request:** Persist regime at signal entry, classify signals by regime
- **Difficulty:** Level 2
- **Value:** HIGH — Prevents killing good signals that underperform in wrong regime
- **Status:** ⏳ PENDING — Requires DB schema change (entry_regime column)
- **Dependencies:** None, but touches signal_schema.py, signal_compactor.py, position_manager.py
- **Key insight:** Regime computed at entry but discarded by close. Must persist entry_regime in signals table.

### 16. Guitar Tuning — Param Matrix
- **Core request:** 2D matrix (signal × regime) for adaptive parameter tuning
- **Difficulty:** Level 2-3
- **Value:** MEDIUM — Improves parameter optimization per regime
- **Status:** ⏳ PENDING — Needs param_matrix table, hierarchical fallback lookup
- **Dependencies:** Requires regime persistence (item 15) first

### 17. Hebbian OpenMemory Bridge
- **Core request:** Wire OpenMemory → Hebbian learning (replace dead session dumps)
- **Difficulty:** Level 2
- **Value:** MEDIUM — Session learner currently dead (0 rows)
- **Status:** ⏳ PENDING — New script + systemd timer
- **Dependencies:** OpenMemory running on port 8080

---

## Pending Level 3+ Tasks (Defer)

### 18. run_compaction() refactoring (1,533 lines → 15 functions)
- **Difficulty:** Level 3
- **Value:** HIGH for maintainability, LOW for immediate PnL
- **Reason:** Touches core signal processing. High risk of regression. Defer.

### 19. add_signal() kill-switch dict lookup (900 lines → 20)
- **Difficulty:** Level 3
- **Value:** MEDIUM — DRY cleanup, but working code
- **Reason:** signal_schema.py is the most critical file. Refactor needs comprehensive testing.

### 20. Amplitude Enhancement System
- **Core request:** Use wave amplitude for position sizing and filtering
- **Difficulty:** Level 3
- **Value:** HIGH — 3x amplitude difference between long/short waves is significant
- **Status:** ⏳ PENDING — Analysis scripts exist, integration pending
- **Key finding:** Long waves (8h+) have 3x higher amplitude than short waves (<2h)

### 21. Fish-Finder Species Census (new signals)
- **Core request:** Add Volume Profile, Liquidity, Beta Decoupling signals
- **Difficulty:** Level 3-4
- **Value:** MEDIUM — Fills blindspots but needs L2 data for some
- **Status:** ⏳ PENDING — Needs API access for liquidity/beta data

---

## Skipped Plans (20)

| Plan | Reason |
|------|--------|
| copy-trader-evolution-spec | Complex multi-system, no clear MVP |
| retroactive-scan-delayed-entry | High complexity, uncertain value |
| signal_confluence_spec | Already implemented via signal_confluence.py |
| regime-transition-analysis | Analysis only, not actionable yet |
| atr-sl-widen | Already done (ATR_SL_MIN = 0.015) |
| atr-spike-signal-build | Signal exists, backtest results reviewed |
| btc-crash-filter-plan | Already implemented as btc_crash_filter.py |
| cascade-crash-analysis | Analysis report, not a plan |
| coin_tracker_analysis_expansion | Low priority, cosmetic |
| coin_tracker_setup_improvements | Low priority |
| conf-filter-plan | Conf filter already working per investigation |
| favorites-daily-update-spec | Already implemented (favorites_updater.py) |
| imx-spike-detection | Niche, low sample size |
| r2-trend-long-trailing-sl-tuning | Already done via ATR-adaptive |
| sl-tuning | Already done |
| weather-vane v2-v5 | Analysis framework, not actionable |
| directional-outcome-tracker-spec | Analysis framework |
| progressive-context-shaping-spec | Speculative, needs data |
| copy-trader-entry-timing-deep-dive | Analysis, not implementation |
| hl-reconciliation-postmortem-spec | Postmortem, not plan |

---

## Success Tracking

| Task | Difficulty | Time | Result |
|------|-----------|------|--------|
| (none yet) | - | - | - |

---

*Generated by Upgrade Implementer — scan plans/, evaluate, implement easy wins first.*
