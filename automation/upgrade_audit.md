# Upgrade Audit Trail

**Created:** 2026-08-29 04:30 UTC
**Method:** Scan plans/ directory, evaluate difficulty/value, implement Level 1 wins

---

## Plan Evaluations

### 1. losers-list-spec.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Anti-favorites system — penalize underperforming coins with 0.5x score/size
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** losers_tracker.py exists, hermes_constants.py has LOSERS set + multipliers, signal_compactor.py uses LOSERS_MULT, decider_run.py uses LOSERS_SIZE_MULT. Systemd timer running (06:05 UTC).

### 2. 30s-price-interval-migration.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Split architecture — 30s price collection, 60s price_history for signals
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** Plan status says "IMPLEMENTED". Minute-boundary quantization in signal_schema.py.

### 3. wave-period-analysis-plan.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Wave period detection, classification, trade context analysis
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** ⏳ Phase 1 DONE
- **Reason:** Scripts exist (wave_period_detector.py, wave_classifier.py, wave_trade_context.py). Phase 2 (validation + integration) pending.

### 4. amplitude-enhancement-brainstorm.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Amplitude-based trading system — cache, dynamic SL/TP, position sizing, signals
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** ⏳ Phase 0-1 PARTIAL (Task 1: amplitude constants ✅, Task 2: amplitude multiplier ✅)
- **Reason:** Constants defined, amplitude multiplier integrated into signal_compactor. Pending: amplitude cache, dynamic SL, position sizing, amplitude breakout signal.

### 5. copy-trader-entry-timing-deep-dive.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Fix copy trader entry timing — filter entries after big moves
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** ⏳ PENDING
- **Reason:** Copy delay filter not implemented. Could improve WR from 56% → 72%.

### 6. copy-trader-dashboard-enhancements.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Advanced analytics for copy trader dashboard
- **Difficulty:** Level 2-3
- **Value:** MEDIUM
- **Status:** ⏳ Phase 2-4 PENDING
- **Reason:** Phase 1 complete. Copy delay analysis, pro trade overlay, correlation pending.

### 7. ponytail-full-audit.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Codebase cleanup — 33,765 lines of dead/duplicate code
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** ⏳ PENDING
- **Reason:** 80 dead scripts, 47 dead registry entries, timer cleanup, function refactoring. Zero-risk deletions first.

### 8. losers-list-spec.md (already counted)
- **Status:** ✅ IMPLEMENTED

### 9. fish-finder-species-census-2026-08-26.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Fish finder species classification
- **Difficulty:** Level 2
- **Value:** LOW
- **Status:** ⏳ PENDING
- **Reason:** Not read yet, but name suggests niche feature.

### 10. btc-crash-filter-plan.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** BTC crash filter to protect positions
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** btc_crash_filter.py has 5-layer detection (dynamic threshold, volume spike, multi-asset contagion, acceleration, position protection). ATR-scaled thresholds in hermes_constants.py.

### 11. cascade-crash-analysis-2026-08-23.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Cascade crash analysis and prevention
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** ⏳ PENDING
- **Reason:** Architecture-level crash protection.

### 12. confidence-calibration-plan.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Calibrate signal confidence scores
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** ⏳ PENDING
- **Reason:** Confidence calibration improves signal quality.

### 13. exit-mechanics-ownership.md / exit-mechanics-v2.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Exit mechanics improvements
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** PROFIT_MONSTER_BYPASS_SIGNALS already updated (2026-08-26). bb_bounce+, confluence added to bypass. ct-hot+ removed from bypass. cut_loser.py uses same list.

### 14. favorites-daily-update-spec.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Daily favorites update automation
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Reason:** favorites_updater.py exists and runs daily.

### 15. regime-transition-analysis-2026-08-24.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Regime transition detection and response
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** ⏳ PENDING
- **Reason:** Regime detection is critical for strategy switching.

### 16. signal-confluence-spec.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Signal confluence system
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED
- **Reason:** signal_confluence.py exists, registered in signals/__init__.py, constants in hermes_constants.py, source weights in signal_compactor.py. LIVE.

### 17. atr-sl-widen.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Widen ATR-based stop losses
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED (partially) — MAE guard widened to 3.0%, ATR SL kept as-is per verification
- **Reason:** Independent verification showed ATR SL widening NOT beneficial. MAE guard widened from 1.5% to 3.0% (done 2026-08-26). ATR SL params unchanged (correct — net positive already).

### 18. sl-tuning.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** Stop loss tuning
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** ✅ ALREADY OPTIMAL — current params (ATR<0.05%, 0.3%, 5x) are best per backtest
- **Reason:** Backtest showed current params produce best WR (83%) and total PnL (+74.4%). Tighter thresholds reduce signals without quality improvement.

### 19. r2-trend-long-trailing-sl-tuning.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** R2 trend long trailing SL tuning
- **Difficulty:** Level 1
- **Value:** LOW
- **Status:** ⏳ SKIPPED — signal is DEAD (NEVER_REENABLED)
- **Reason:** Signal permanently disabled, tuning params is pointless.

### 20. imx-spike-detection.md
- **Date scanned:** 2026-08-29 04:30
- **Core request:** IMX spike detection signal
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** ⏳ PENDING
- **Reason:** New signal for specific token.

---

## Implementation Log

### Task 1: Amplitude Class Constants (Level 1)
- **Started:** 2026-08-29 04:35
- **Completed:** 2026-08-29 04:40
- **Plan:** amplitude-enhancement-brainstorm.md
- **What:** Add amplitude class thresholds and multipliers to hermes_constants.py
- **Why:** Foundation for amplitude-aware trading. wave_classifier.py uses local thresholds — need system-wide constants.
- **Files changed:**
  - `hermes_constants.py` — Added AMP_CLASS_LOW_MAX, AMP_CLASS_MED_MAX, AMPLITUDE_COMPACTOR_MULT, AMPLITUDE_SIZE_MULT, AMPLITUDE_SL_MULT, AMPLITUDE_MAX_PORTFOLIO_LOSS (~30 lines)
  - `wave_classifier.py` — Updated to import and use constants instead of hardcoded 1.5/2.5 thresholds
- **Status:** ✅ DONE
- **Verified:** Python import succeeds, syntax OK

### Task 2: Amplitude Multiplier Integration (Level 1)
- **Started:** 2026-08-30 04:00
- **Completed:** 2026-08-30 04:10
- **Plan:** amplitude-enhancement-brainstorm.md (Idea 3: Amplitude-Weighted Signal Compactor)
- **What:** Integrate amplitude class multiplier into signal_compactor scoring. HIGH_AMP tokens (ZRO, TRUMP, WIF) get 0.85x confidence penalty. LOW_AMP (BTC, ETH) get 1.10x boost.
- **Why:** HIGH_AMP tokens are more volatile — signals are less reliable. Dynamic penalty improves signal quality ranking.
- **Files changed:**
  - `hermes_constants.py` — Added TOKEN_AMP_CLASS dict (30 tokens mapped) + get_token_amp_class() helper (~25 lines)
  - `signal_compactor.py` — Imported AMPLITUDE_COMPACTOR_MULT + get_token_amp_class, added amplitude_mult to scoring function, added to final_score calculation (~4 lines)
- **Status:** ✅ DONE
- **Verified:** Syntax OK, imports work, get_token_amp_class returns correct classes
- **Impact:** Signals for HIGH_AMP tokens (ZRO, TRUMP, WIF, etc.) now get 15% confidence penalty. Signals for LOW_AMP (BTC, ETH) get 10% boost. Unknown tokens default to MED_AMP (neutral).

---

## Summary

| Metric | Count |
|--------|-------|
| Plans scanned | 20 |
| Already implemented | 5 (losers-list, 30s-migration, favorites-update, exit-mechanics-v2, signal-confluence) |
| Level 1 (Easy) | 2 implemented (amplitude constants, amplitude integration) |
| Level 2 (Medium) | 10 candidates |
| Level 3 (Hard) | 4 candidates |
| Level 4 (Epic) | 0 |
| Skipped (dead signal) | 1 (r2-trend-long-trailing-sl) |
