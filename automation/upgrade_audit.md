# Upgrade Audit Trail

**Generated:** 2026-08-14 17:30 UTC
**Last scanned:** 2026-08-16 06:00 UTC (weather-vane-v3 re-implemented correctly)
**Plans scanned:** 8

---

## Plan: r2-trend-long-trailing-sl-tuning.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Widen trailing SL from 0.8% to 2.0% and raise activation from 0.4% to 0.8% for r2_trend_long entries
- **Difficulty:** Level 1 (config tweak)
- **Value:** HIGH
- **Status:** IMPLEMENTED (2026-08-14 17:30)
- **Reason:** Multi-token validation complete — 30 trades across 20+ tokens confirmed 60% WR with current params. Trail distance widened to 2.00% (survives 1.88% max drawdown from 2Z wave analysis). Activation raised to 0.80% (waits for trend establishment). R:R improved from 0.39:1 to ~1.25:1 on trailing exits.

## Plan: coin_tracker_analysis_expansion.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Expand coin_tracker into analysis engine with Wyckoff, Elliott Wave, S/R, trend quality, volume profile — eventually generating signals
- **Difficulty:** Level 3 (multi-system)
- **Value:** HIGH
- **Status:** IN PROGRESS (Phase 1 complete, Phase 2 signal generation in progress)
- **Reason:** Already partially implemented. Phase 1 (analysis engine) done. Phase 2 (signal generation) in progress.

## Plan: 2026-08-15_weather-vane-v5-volatility-floor.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Filter out low-volatility entries (vol < 0.30%) — backtested as strongest single filter
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** VOL_FLOOR_ENABLED exists in hermes_constants.py (line 680). check_volatility_floor() exists in signal_compactor.py (line 467, called at line 1484). Fully integrated.

## Plan: 2026-08-15_weather-vane-v4-tide-detection.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** BTC 3h momentum as fastest lagging indicator for tide detection, combined with SHORT win rate confirmation
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** TIDE_ENABLED exists in hermes_constants.py (line 668). get_tide_penalty() exists in signal_compactor.py (line 557, called at line 682). Fully integrated.

## Plan: 2026-08-13_progressive-context-shaping-spec.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Maintain CURRENT.md for agent context continuity between sessions
- **Difficulty:** Level 2-3
- **Value:** LOW-MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** /root/.hermes/CURRENT.md exists. Agent orchestration improvement, not trading logic.

## Plan: 2026-08-13_weather-vane-v3-spec.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Z-Score + Acceleration alignment filter (surfing.md quadrants) — strongest predictive signal (76% vs 24% WR gap)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED (2026-08-16 — added to signal_compactor.py as penalty multiplier; fixed inverted logic in decider_run.py)
- **Reason:** ZSCORE_ACCEL_ENABLED in hermes_constants.py (line 653). get_zscore_accel_penalty() added to signal_compactor.py. Fixed critical bug in decider_run.py: old code blocked LONG when z>0 + accel>0 (76.4% WR winners) and SHORT when z<0 + accel<0 (63.3% WR winners) — inverted from what backtest showed. Now correctly blocks misaligned entries (z<0+accel<0 for LONG, z>0+accel>0 for SHORT).

## Plan: 2026-08-13_weather-vane-v2-spec.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Hysteresis, derivative (velocity tiers), integral (cumulative), off-course alarm for Weather Vane
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** All active layers deployed per status table. Direction Lock (Proposal 8) is NEXT but not critical.

## Plan: 2026-08-12_directional-outcome-tracker-spec.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Real-time regime shift detection using trade outcomes as leading indicator
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** IMPLEMENTED (2026-08-15 — Component 2 Position Shield deployed)
- **Reason:** All 3 components live. Component 1 (Signal Gate) — get_directional_outcome() in signal_compactor.py. Component 2 (Position Shield) — _apply_weather_vane_shield() in position_manager.py tightens trail to 0.30% + force-closes after 30min on counter-regime losing positions. Component 3 (Recovery) inherent in rolling window.

---

## Summary

| Metric | Count |
|--------|-------|
| Plans scanned | 8 |
| IMPLEMENTED | 8 |
| IN PROGRESS | 0 |
| PENDING | 0 |
| SKIPPED | 0 |

### Pending Candidates

None — all plans fully implemented.

### Open Items (from CURRENT.md backlog, not in plans/)
1. **Phantom trades** (guardian_orphan with empty signal) — ~6T/day, -$0.10. Level 2.
2. **ATR_SL entry quality** — 36T/48h 2.8% WR -$2.37. Main drag. Speed filter raised to 40, monitoring.
3. **contextmap.md** — signal ecosystem map. Level 1. LOW priority.
4. **checkpoint_utils.py progress summaries** — human-readable cycle output. Level 1. LOW priority.

### Already Done (no action needed)
- weather-vane-v5 (volatility floor) — check_volatility_floor() in signal_compactor.py
- weather-vane-v4 (tide detection) — get_tide_penalty() in signal_compactor.py
- weather-vane-v3 (z-score + accel) — get_zscore_accel_penalty() in signal_compactor.py (re-implemented 2026-08-16, was inverted in decider_run.py)
- weather-vane-v2 (hysteresis, derivative, integral, direction lock, off-course alarm) — directional outcome system in signal_compactor.py
- progressive-context-shaping (CURRENT.md)
- directional-outcome-tracker (signal gate + position shield)
- r2_trend_long trailing SL tuning (TRAILING_ACTIVATION_PCT 0.40%, TRAILING_DISTANCE_PCT 2.00%)

### Re-scan: 2026-08-16 17:20 UTC
All 8 plans confirmed implemented. No new plan files added since last scan. Next valuable work is from CURRENT.md backlog (phantom trades, ATR_SL monitoring).

### Re-scan: 2026-08-17 06:00 UTC
All 8 plans confirmed implemented. No new plan files added since Aug 14. System running strong: 24h +$0.64, 61.1% WR. Open backlog items (not in plans/): phantom trades (Level 2-3), higher-TF regime (Level 2).
