# Upgrade Audit Trail

**Created:** 2026-09-06
**Updated:** 2026-09-08 17:30
**Scanned:** 62 plans in /root/.hermes/plans/

---

## Summary

| Metric | Count |
|--------|-------|
| Plans scanned | 62 |
| Already implemented | 37 |
| Pending (wirable) | 1 |
| Pending (new work) | 7 |
| Concluded (no action needed) | 3 |
| Rejected by verification | 2 |
| Tooling (not trading) | 2 |
| Analysis-only (no action) | 10 |
| **Total evaluated** | **62** |

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
| `2026-08-21_hl-reconciliation-postmortem-spec.md` | L2 | HIGH | IMPLEMENTED — `hl_reconciliation.py` + systemd timer |
| `2026-08-26_30s-price-interval-migration.md` | L1 | HIGH | IMPLEMENTED — minute-boundary quantization in signal_schema.py |
| `2026-08-27_ponytail-full-audit.md` | L3 | HIGH | Phase 1 DONE — 80 dead scripts deleted, ai_decider/signal_gen removed, sys.path cleaned |
| `2026-08-21_copy-trader-entry-timing-deep-dive.md` | L2 | HIGH | Phase 1 DONE — SHORT copy disabled, trader_performance update fixed |
| `2026-08-28_losers-list-spec.md` | L2 | MEDIUM | IMPLEMENTED — `losers_tracker.py`, score + position penalties live |
| `2026-08-29_wave-period-analysis-plan.md` | L2 | MEDIUM | Phase 1 DONE — wave_period_detector.py created, classification complete |
| `2026-08-29_amplitude-enhancement-brainstorm.md` | L3 | HIGH | Partially done — amplitude_cache.py exists, compactor multiplier live |
| `trade_velocity_tracking.md` | L2 | MEDIUM | IMPLEMENTED — velocity_backfill.py, signal_velocity_stats table in PostgreSQL |
| `2026-09-04_btc-wave-pattern-surfer.md` | L3 | HIGH | IMPLEMENTED — btc_wave_detector.py exists |
| `2026-09-04_continuum-engine-spec.md` | L4 | HIGH | IMPLEMENTED — continuum_engine.py exists |
| `2026-08-13_progressive-context-shaping-spec.md` | L1 | LOW | Partially done — CURRENT.md pattern exists in brain/ |
| `2026-09-02_regime-aware-signal-params-spec.md` | L2 | HIGH | IMPLEMENTED — `regime_params.py` wired into accel_300_v3 signals |
| `2026-09-06_pullback_entry_signal.md` | L2 | MEDIUM | IMPLEMENTED — `pullback_entry.py` signal live, all infrastructure connected |
| `2026-09-07_accel300-long-fix-plan.md` | L1 | HIGH | IMPLEMENTED — RSI<50, pre15<0, mom=falling filters live in decider_run.py for V3 LONG |
| `2026-09-07_accel300-v4-killer-signal.md` | L1 | HIGH | IMPLEMENTED — RSI>50 filter (SHORT), z>0 filter (HIGH regime) live in decider_run.py for V3 SHORT |
| `2026-09-06_doji_signal_system.md` | L2 | HIGH | IMPLEMENTED — `doji_top.py` signal live, all infrastructure connected |
| `2026-09-08_grind-breakout-signal-spec.md` | L2 | HIGH | IMPLEMENTED — `grind_breakout.py` committed (b77064d0), RSI 35-65 quality filter applied, AVNT LONG blacklisted |
| `2026-09-08_grind-breakout-quality-filters.md` | L1 | HIGH | IMPLEMENTED — RSI 35-65 filter in grind_breakout spec, params updated |
| `2026-09-08_grind-breakout-backtest-data.md` | L1 | LOW | Analysis only — backtest data consumed into grind_breakout.py params |
| `atr-spike-signal-build.md` | L2 | HIGH | IMPLEMENTED — `signals/atr_spike.py` live, all params in hermes_constants.py |
| `atr-spike-backtest-results.md` | L1 | MEDIUM | IMPLEMENTED — backtest confirms atr_spike signal quality, params tuned |
| `imx-spike-detection.md` | L2 | HIGH | IMPLEMENTED — atr_spike signal was built from this spec |
| `btc-crash-filter-plan.md` | L2 | HIGH | IMPLEMENTED — `btc_crash_filter.py` live, `BTC_CRASH_BLOCK_*` params active |
| `cascade-crash-analysis-2026-08-23.md` | L2 | HIGH | IMPLEMENTED — `MULTI_ALT_DIVERGENCE_*` params live in btc_crash_filter.py |
| `conf-filter-plan.md` | L1 | HIGH | IMPLEMENTED — `CONF_FILTER_ENABLED=True`, `CONF_FILTER_MAX=89` in signal_compactor.py |
| `exit-mechanics-v2.md` | L1 | MEDIUM | IMPLEMENTED — bypass list fix done: bb_bounce+, confluence, stop_hunt_reversal all in PROFIT_MONSTER_BYPASS_SIGNALS |
| `coin_tracker_analysis_expansion.md` | L3 | MEDIUM | Phase 1 DONE — Wyckoff, Elliott Wave, S/R, trend quality, volume profile all in coin_tracker_analysis.py |
| `signal-cluster-analysis-2026-08-26.md` | L2 | LOW | Analysis complete — 69,990 signals analyzed, cascade patterns documented |
| `signal-cluster-brainstorm-2026-08-26.md` | L2 | LOW | Analysis complete — no actionable implementation |
| `signal_confluence_spec.md` | L3 | HIGH | IMPLEMENTED — `signals/confluence.py` exists and runs |

### ⏳ PENDING (Wirable — code exists but not connected)

| Plan | Difficulty | Value | Status | What's Missing |
|------|-----------|-------|--------|----------------|
| `2026-08-21_copy-trader-entry-timing-deep-dive.md` | L1 | MEDIUM | PARTIALLY DONE | Time filter code exists (`COPY_BAD_HOURS_ENABLED=False`). Intentionally disabled per comment. Low priority. |

### 📋 PENDING (New work required)

| Plan | Difficulty | Value | Status | Notes |
|------|-----------|-------|--------|-------|
| `coin_tracker_setup_improvements.md` | L1 | HIGH | NOT STARTED | 5 fixes: regime gate, confirming analyses, MIN_COMPOSITE raise, age decay, kill warm bypass. Signal currently killed. |
| `automation-team-improvements.md` | L2 | HIGH | PARTIALLY DONE | PARAM_CONFIG expanded (30+ params), param_map covers 20+ signals, A/B learner deleted. Remaining: OpenMemory bridge (L2), hebbian monitoring (L1). |
| `r2-trend-long-trailing-sl-tuning.md` | L1 | MEDIUM | NOT STARTED | Analysis recommends trail=2.0%, activation=0.8% for r2_trend_long. Current: 0.8%/0.8%. |
| `exit-strategy-refactor.md` | L3 | MEDIUM | FUTURE | Per-signal exit strategy routing. Simple fix (bypass list split) already deployed. Full refactor deferred. |
| `exit-mechanics-ownership.md` | L3 | MEDIUM | DRAFT | Exit ownership model — superseded by exit-mechanics-v2.md (bypass list fix already done) |
| `2026-08-22_copy-trader-dashboard-enhancements.md` | L3 | MEDIUM | NOT STARTED | Phase 2 dashboard features (copy delay analysis, pro portfolio view, regime performance) |
| `2026-09-07_market-sync-protection-plan.md` | L2 | HIGH | DECISION NEEDED | Auditor found 88-92% false positive rate. Needs decision: integrate with MAE guard or do nothing |
| `2026-09-07_partial-close-trailing-runner.md` | L2-L3 | HIGH | DEFERRED | 4 options: partial close (complex), regime trail, tiered trail, time trail. CEO pinned PM_TRAIL_DISTANCE_PCT at 0.20% — blocks trail widening. Needs backtest before any implementation. |
| `trend_momentum_spec.md` | L2 | HIGH | NOT STARTED | Full trend_momentum signal (EMA alignment + slope + acceleration). Backtested: 35% WR, 3.0:1 R:R, +67.89% net PnL over 14d. Only killed near_sma variant exists. |
| `trend_momentum_v4_spec.md` | L1 | HIGH | NOT STARTED | V4 filters for trend_momentum: SKIP_HOURS, AFTER_WIN_ONLY, token blacklist. +7.9% WR improvement. Requires trend_momentum signal first (L2). |

### ❌ REJECTED (by verification agent)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| `atr-sl-widen.md` | L1 | HIGH | REJECTED | ATR SL widening to k=2.0-2.5 rejected — zero of 30 losing trades would be saved. Current values kept. |
| `2026-08-19_short-bias-fix.md` | L1 | MEDIUM | CONCLUDED | No changes needed, system working correctly |

### 🔧 TOOLING (not trading)

| Plan | Difficulty | Value | Status | Notes |
|------|-----------|-------|--------|-------|
| `cronr-timer-plugin.md` | L3 | LOW | NOT STARTED | DSH/Cordis recurring timer plugin — separate from trading system |

### 📊 ANALYSIS (informational only, no implementation needed)

| Plan | Difficulty | Value | Status | Notes |
|------|-----------|-------|--------|--------|
| `exit-spec-review.md` | L1 | LOW | CONCLUDED | Independent review of exit-mechanics-ownership — recommended Phase 0 only (bypass fix, already done) |
| `confidence-calibration-plan.md` | L1 | LOW | CONCLUDED | No action needed, existing filters confirmed working |
| `2026-08-19_short-bias-fix.md` | L1 | MEDIUM | CONCLUDED | No changes needed |
| `regime-transition-analysis-2026-08-24.md` | L2 | LOW | CONCLUDED | Incident analysis — documented, lessons applied to Weather Vane system |
| `favorites-daily-update-spec.md` | L2 | MEDIUM | SPEC ONLY | Daily favorites update spec — not implemented, weekly updater still in place |
| `fish-finder-species-census-2026-08-26.md` | L2 | LOW | CONCLUDED | Blindspot analysis — informational, no code changes needed |
| `spec-guitar-tuning.md` | L3 | MEDIUM | SPEC NEEDS REVISION | Multi-dimensional adaptive tuning — verified needs revision, v2 addresses findings |
| `review-guitar-tuning.md` | L1 | LOW | CONCLUDED | Independent verification of guitar-tuning spec |
| `spec-signal-regime-memory.md` | L3 | MEDIUM | SPEC NEEDS REVISION | Signal regime memory — verified needs revision, v2 addresses findings |
| `sl-tuning.md` | L1 | MEDIUM | CONCLUDED | Analysis recommends 0.75% SL for atr_spike — already implemented in atr_spike.py |

### 🧹 CANDIDATES FOR DELETION

| Plan | Reason |
|------|--------|
| `exit-mechanics-ownership.md` | Superseded by exit-mechanics-v2.md (bypass list fix done) |
| `exit-spec-review.md` | Review document, not actionable |
| `atr-spike-backtest-results.md` | Backtest results already consumed into atr_spike.py params |
| `signal-cluster-brainstorm-2026-08-26.md` | Brainstorm, no actionable outcomes |

---

## Recommended Implementation Order

### Level 1 (EASY) — Completed
- ✅ AVNT added to LONG_BLACKLIST (grind_breakout 10% WR, trend_momentum 12% WR)
- ✅ conf < 90 filter implemented
- ✅ accel300 RSI < 50 filter implemented
- ✅ pullback_entry signal implemented
- ✅ doji_top exit signal implemented

### Level 2 (MEDIUM) — Do Next
1. **trend_momentum signal** — full EMA alignment + slope + acceleration signal (~250 LOC). Backtested: 35% WR, 3.0:1 R:R. v4 filters add +7.9% WR.
2. **automation-team-improvements.md** — OpenMemory bridge for session learner (remaining L2 item)
3. **Market sync protection** — needs decision (88-92% false positive rate, integrate with MAE guard vs do nothing)
4. **partial-close-trailing-runner.md** — needs backtest first (MFE > 2x realized PnL check). CEO pinned trail at 0.20%.

### Level 3+ (HARD) — Later
5. **exit-strategy-refactor.md** — full per-signal exit routing (bypass list split already done)
6. **spec-guitar-tuning.md** — multi-dimensional adaptive tuning (needs revision first)
7. **spec-signal-regime-memory.md** — signal regime memory (needs revision first)
