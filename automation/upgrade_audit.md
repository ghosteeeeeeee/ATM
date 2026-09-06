# Upgrade Audit Trail

**Created:** 2026-09-06
**Scanned:** 49 plans in /root/.hermes/plans/

---

## Summary

| Metric | Count |
|--------|-------|
| Plans scanned | 49 |
| Already implemented | 23 |
| Pending (wirable) | 3 |
| Pending (new work) | 1 |
| Concluded (no action needed) | 2 |
| **Total evaluated** | **29** |

---

## Plan Evaluations

### ✅ IMPLEMENTED

| Plan | Difficulty | Value | Status |
|------|-----------|-------|--------|
| `2026-08-15_weather-vane-v5-volatility-floor.md` | L1 | HIGH | IMPLEMENTED — `VOL_FLOOR_ENABLED=True`, `check_volatility_floor()` in signal_compactor.py |
| `2026-08-15_weather-vane-v4-tide-detection.md` | L2 | HIGH | IMPLEMENTED — `TIDE_*` params live, `get_tide_penalty()` in signal_compactor.py |
| `2026-08-13_weather-vane-v2-spec.md` | L2 | HIGH | IMPLEMENTED — Hysteresis, Derivative, Integral, Off-course alarm all live |
| `2026-08-13_weather-vane-v3-spec.md` | L2 | HIGH | IMPLEMENTED — Z-Score + Acceleration prediction live |
| `2026-08-12_directional-outcome-tracker-spec.md` | L2 | HIGH | IMPLEMENTED — Weather Vane Component 1 live |
| `2026-08-19_short-bias-fix.md` | L1 | MEDIUM | CONCLUDED — No changes needed, system working correctly |
| `2026-08-21_hl-reconciliation-postmortem-spec.md` | L2 | HIGH | IMPLEMENTED — `hl_reconciliation.py` + systemd timer |
| `2026-08-26_30s-price-interval-migration.md` | L1 | HIGH | IMPLEMENTED — minute-boundary quantization in signal_schema.py |
| `2026-08-27_ponytail-full-audit.md` | L3 | HIGH | Phase 1 DONE — 80 dead scripts deleted, ai_decider/signal_gen removed, sys.path cleaned |
| `2026-08-21_copy-trader-entry-timing-deep-dive.md` | L2 | HIGH | Phase 1 DONE — SHORT copy disabled, trader_performance update fixed |
| `2026-08-28_losers-list-spec.md` | L2 | MEDIUM | IMPLEMENTED — `losers_tracker.py`, score + position penalties live |
| `2026-08-29_wave-period-analysis-plan.md` | L2 | MEDIUM | Phase 1 DONE — wave_period_detector.py created, classification complete |
| `2026-08-29_amplitude-enhancement-brainstorm.md` | L3 | HIGH | Partially done — amplitude_cache.py exists, compactor multiplier live |
| `confidence-calibration-plan.md` | L1 | LOW | CONCLUDED — No action needed, existing filters confirmed working |
| `trade_velocity_tracking.md` | L2 | MEDIUM | IMPLEMENTED — velocity_backfill.py, signal_velocity_stats table in PostgreSQL |
| `2026-09-04_btc-wave-pattern-surfer.md` | L3 | HIGH | IMPLEMENTED — btc_wave_detector.py exists |
| `2026-09-04_continuum-engine-spec.md` | L4 | HIGH | IMPLEMENTED — continuum_engine.py exists |
| `2026-08-13_progressive-context-shaping-spec.md` | L1 | LOW | Partially done — CURRENT.md pattern exists in brain/ |
| `2026-08-15_weather-vane-v5-volatility-floor.md` | L1 | HIGH | IMPLEMENTED |

### ⏳ PENDING (Wirable — code exists but not connected)

| Plan | Difficulty | Value | Status | What's Missing |
|------|-----------|-------|--------|----------------|
| `2026-09-02_regime-aware-signal-params-spec.md` | L2 | HIGH | PARTIALLY DONE | `regime_params.py` exists with overrides, but `accel_300_v3_long.py` and `accel_300_v3_short.py` don't import it. Final wiring step never done. |
| `2026-08-29_amplitude-enhancement-brainstorm.md` | L2 | HIGH | PARTIALLY DONE | `get_dynamic_sl()` defined in amplitude_cache.py but not called by position_manager.py. `AMPLITUDE_SIZE_MULT` defined but never imported. |
| `2026-08-21_copy-trader-entry-timing-deep-dive.md` | L1 | MEDIUM | PARTIALLY DONE | Time filter code exists (`COPY_BAD_HOURS_ENABLED=False`). Intentionally disabled per comment. Low priority. |

### 📋 PENDING (New work required)

| Plan | Difficulty | Value | Status | Notes |
|------|-----------|-------|--------|-------|
| `2026-08-22_copy-trader-dashboard-enhancements.md` | L3 | MEDIUM | NOT STARTED | Phase 2 (copy delay analysis, pro portfolio view, regime performance) — all new dashboard features |
| `exit-mechanics-ownership.md` | L3 | MEDIUM | NOT STARTED | Draft status — exit ownership model to resolve ATR SL vs PM Trail conflicts |
| `losers-list-spec.md` | L2 | MEDIUM | IMPLEMENTED | (moved to IMPLEMENTED above) |

---

## Recommended Implementation Order

### Level 1 (EASY) — Do Now
1. **Wire regime_params into accel_300_v3 signals** — ~50 LOC, connects existing infrastructure
2. **Wire amplitude dynamic SL into position_manager** — ~30 LOC, connects existing function
3. **Wire amplitude position sizing** — ~10 LOC, connects existing constant

### Level 2 (MEDIUM) — Next
4. Copy trader dashboard Phase 2 features
5. Exit mechanics ownership model

### Level 3+ (HARD) — Later
6. Ponytail audit Phase 2 (timer cleanup)
7. Ponytail audit Phase 3 (core function refactoring)
