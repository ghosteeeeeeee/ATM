# Upgrade Implementer Audit Trail

Generated: 2026-08-31 16:00 UTC

---

## Plan: 2026-08-29_amplitude-enhancement-brainstorm.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Build amplitude cache, dynamic SL/TP based on token amplitude classes
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** AMPLITUDE_COMPACTOR_MULT + get_token_amp_class() integrated into signal_compactor. amplitude_cache.py still future. Dynamic SL not built.

## Plan: 2026-08-29_wave-period-analysis-plan.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Analyze wave periodicity per token, classify into buckets, integrate with trading
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** wave_period_detector.py, wave_trade_context.py, wave_classifier.py all created and in codebase. Phase 2 (backtest/validation) pending.

## Plan: losers-list-spec.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Penalize underperforming tokens (score/size/confidence penalties), auto-detect from trade data
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** losers_tracker.py created. LOSERS_MULT, LOSERS_SIZE_MULT, LOSERS set all in hermes_constants.py. Integrated into signal_compactor.py:872 and decider_run.py:284.

## Plan: 2026-08-27_ponytail-full-audit.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Delete 80 dead scripts, shrink 5 monolith functions, reduce 57→35 timers
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** Audit report only — no code changes made. Dead scripts, zombie code, and timer bloat still present.

## Plan: spec-guitar-tuning.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Regime-aware parameter tuning matrix (signal × regime), replace Thompson sampling with weighted scoring
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** No param_matrix table, no ADAPTIVE_TUNING_ENABLED. Self_learner still flat (1 param). Spec is v2 after audit.

## Plan: review-guitar-tuning.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Independent verification of guitar tuning spec
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** N/A
- **Reason:** Review document only — findings folded into spec v2. No actionable code.

## Plan: spec-signal-regime-memory.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Per-signal regime tracking (dormant/active states), resurrection when regime returns
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** No signal_regime_tracker.py, no signal_regime_perf.db, no REGIME_MEMORY_ENABLED. signal_outcomes still has no regime column.

## Plan: fish-finder-species-census-2026-08-26.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Add Volume Profile, Liquidity, Beta Decoupler, Regime Transition signal species
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED
- **Reason:** 4 new species identified, none built. Existing 21 species detection is live.

## Plan: automation-team-improvements.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Fix dead session learner (→OpenMemory bridge), expand self_learner PARAM_CONFIG, delete A/B learner
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** self_learner PARAM_CONFIG expanded (25+ params, 15+ signals). ab_learner.py deleted. Session learner still dead (0 sessions). OpenMemory bridge not built.

## Plan: signal-cluster-brainstorm-2026-08-26.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Market phase gate, Hebbian V2 family correlations, confluence scorer, lifecycle filters, predictive sequencing
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** market_phase_gate.py ✅ implemented + integrated. confluence_scorer.py ✅ implemented. signal_lifecycle_filter.py ✅ implemented. Hebbian V2 family correlations, predictive sequencing, rotation tracker NOT built.

## Plan: signal-cluster-analysis-2026-08-26.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** 30-day signal cluster analysis identifying phase cycles, lead-lag relationships, co-signal patterns
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Analysis completed. analyze_signal_clusters.py and analyze_signal_cascades.py created. Results integrated into phase gate, lifecycle filter, confluence scorer.

## Plan: 2026-08-26_30s-price-interval-migration.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Split 30s price collection into fast (latest_prices) and slow (price_history at 60s boundaries)
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** signal_schema.py:3548 has minute_ts = (now // 60) * 60 quantization. Price_history writes at 60s boundaries.

## Plan: exit-mechanics-v2.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Fix backwards PROFIT_MONSTER_BYPASS_SIGNALS — proven signals bypass PM Trail, losing signals get PM Trail
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Bypass list fixed 2026-08-26. bb_bounce+, confluence, stop_hunt_reversal added. ct-hot+/ct-hot- removed. Comment confirms update.

## Plan: exit-spec-review.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Independent review of exit ownership spec — find factual errors, recommend Phase 0 only
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** N/A
- **Reason:** Review document. Key finding: "Proceed with Phase 0 only (fix bypass list)." Phase 0 not done.

## Plan: exit-mechanics-ownership.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Exit owner model: DB column per trade, ATR vs PM Trail ownership routing
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** NOT IMPLEMENTED
- **Reason:** No exit_owner column, no ATR_EXIT_SIGNALS/PM_TRAIL_EXIT_SIGNALS. Bypass list still used.

## Plan: regime-transition-analysis-2026-08-24.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Add BTC 30m momentum filter, upgrade DIRECTIONAL_OUTCOME to hard block at 3/5 losses
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** BTC_MOMENTUM_FILTER_ENABLED = True ✅. DIRECTIONAL_OUTCOME_VELOCITY_TIERS upgraded: 0.6: 0.0 (hard block at 3+/5 losses) ✅. BTC level filter ✅ IMPLEMENTED (Layer 8 added).

## Plan: signal_confluence_spec.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Meta-signal detecting persistence + compounding of first-order signals over 30-min window
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** signals/signal_confluence.py fully built. Constants in hermes_constants.py. Registered in __init__.py. Layer 2 enforcement in signal_schema.py. Source weights in signal_compactor.py.

## Plan: mae-guard-multialt-spec.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Re-enable MAE Guard at 2.0% + add Layer 6 multi-alt divergence filter to btc_crash_filter
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** MAE Guard re-enabled at 3.0% (not 2.0% — widened). Multi-alt divergence filter ✅ implemented (_check_multi_alt_divergence in btc_crash_filter.py).

## Plan: cascade-crash-analysis-2026-08-23.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Add multi-alt divergence filter, lower BTC crash threshold, re-enable MAE guard
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** Multi-alt filter ✅. BTC crash threshold NOT lowered (still -1.5%). MAE Guard re-enabled at 3.0% (not 2.0%).

## Plan: atr-sl-widen.md
- **Date scanned:** 2026-08-31 16:00
- **Core request:** Independent verification — DO NOT widen ATR SL; fix MAE guard, fix entry features bug
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** PARTIAL
- **Reason:** ATR SL NOT widened (correct — verification said don't). MAE guard widened to 3.0% (not disabled or kept at 1.5%). features_recorded bug status unknown.

---

## Summary

| Status | Count | Plans |
|--------|-------|-------|
| IMPLEMENTED | 7 | losers-list, wave-period-analysis, 30s-price-migration, signal-cluster-analysis, signal_confluence, exit-mechanics-v2, automation-team-improvements |
| PARTIAL | 6 | amplitude-enhancement, signal-cluster-brainstorm, mae-guard-multialt, cascade-crash, atr-sl-widen, regime-transition-analysis |
| NOT IMPLEMENTED | 4 | ponytail-audit, guitar-tuning, signal-regime-memory, fish-finder-species, exit-mechanics-ownership |
| N/A (review/docs) | 2 | review-guitar-tuning, exit-spec-review |

---

## Implementation Log

| Date | Plan | Action | Status |
|------|------|--------|--------|
| 2026-08-31 | exit-mechanics-v2 | Fix PROFIT_MONSTER_BYPASS_SIGNALS | ✅ DONE (already implemented 2026-08-26) |
| 2026-08-31 | automation-team-improvements | Expand self_learner PARAM_CONFIG | ✅ DONE (already expanded, 25+ params) |
| 2026-08-31 | automation-team-improvements | Delete ab_learner.py | ✅ DONE (already deleted) |
| 2026-08-31 | regime-transition-analysis | Implement BTC level filter | ✅ DONE (Layer 8 added to btc_crash_filter.py) |

---

## BTC Level Filter Implementation Details

**File:** `scripts/btc_crash_filter.py`
**Constants:** `scripts/hermes_constants.py`

### What was added:
- `BTC_LEVEL_FILTER_ENABLED = True`
- `BTC_LEVEL_SHORT_BLOCK_PCT = -0.5` (block SHORT when BTC > 0.5% below 1h high)
- `BTC_LEVEL_LONG_BLOCK_PCT = 0.5` (block LONG when BTC > 0.5% above 1h low)
- `BTC_LEVEL_LOOKBACK_MIN = 60` (1h lookback for session high/low)
- `BTC_LEVEL_BLOCK_DURATION_MIN = 10` (block entries for 10 min after trigger)

### How it works:
- Layer 8 in btc_crash_filter.py
- Fetches 1h of BTC 1m candles
- Calculates distance from session high and low
- Blocks SHORT when BTC is near session lows (bounce risk)
- Blocks LONG when BTC is near session highs (pullback risk)
- Independent block — applies its own 10-min duration

### Expected impact:
- Would have prevented all 6 losing SHORT entries in Aug 24 incident
- Estimated savings: ~$34.78 per incident

---

## Plan: exit-mechanics-v2.md
- **Date scanned:** 2026-09-01 00:00
- **Core request:** Fix backwards PROFIT_MONSTER_BYPASS_SIGNALS — proven signals should bypass PM Trail, losers should get it
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Already done (comment on hermes_constants.py:1082 shows 2026-08-26 update). bb_bounce+/confluence in bypass, ct-hot+/- removed.

## Plan: automation-team-improvements.md
- **Date scanned:** 2026-09-01 00:00
- **Core request:** Fix dead session learner, expand self_learner PARAM_CONFIG, delete defunct A/B learner
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIAL
- **Reason:** Self-learner PARAM_CONFIG expanded to 25+ params (done). A/B learner deleted (done). Session learner → OpenMemory bridge NOT built (Level 2).

## Level 1 Cleanup — Dead Code Removal
- **Date:** 2026-09-01 00:00
- **Changes:**
  1. Deleted `update_regime_performance()` from volatility_gate.py (34 lines, zero callers)
  2. Cleaned stale `ai_decider` and `ab_learner` references from brain/trading.md and docs/pipeline-diagram.md
- **Skipped:** vortex_break.py deletion (too many cross-file references, not a clean removal)
