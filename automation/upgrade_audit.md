# Upgrade Audit Trail

**Generated:** 2026-08-14 06:30 UTC
**Plans scanned:** 8

---

## Plan: r2-trend-long-trailing-sl-tuning.md
- **Date scanned:** 2026-08-14 06:30
- **Core request:** Widen trailing SL from 0.8% to 2.0% and raise activation from 0.4% to 0.8% for r2_trend_long entries
- **Difficulty:** Level 1 (config tweak)
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** Plan recommends changing global TRAILING_DISTANCE_PCT (affects ALL signals). Backtest data is 2Z-only. Plan itself notes "Does trail=2.0% work on other tokens? Need to test on more winners." No per-signal override mechanism exists in r2_trend_long.py — would need either global change or new DB column. Risky without multi-token validation.

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
- **Status:** IMPLEMENTED
- **Reason:** ZSCORE_ACCEL_ENABLED in hermes_constants.py (line 620). Logic implemented in decider_run.py (lines 766-770) as hard block, not penalty multiplier. Different integration point than planned but same effect.

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
- **Status:** IMPLEMENTED
- **Reason:** Component 1 (Signal Gate) live. Component 2 (Position Shield) unblocked but not implemented. Component 3 (Recovery) inherent in rolling window.

---

## Summary

| Metric | Count |
|--------|-------|
| Plans scanned | 8 |
| IMPLEMENTED | 6 |
| IN PROGRESS | 1 |
| PENDING | 1 |
| SKIPPED | 0 |

### Pending Candidates

1. **r2_trend_long trailing SL tuning** — Level 1 — HIGH value — Needs multi-token validation before changing global TRAILING_DISTANCE_PCT. Safest path: backtest on 3+ tokens, then either global change or add per-signal trailing_distance column.

### Already Done (no action needed)
- weather-vane-v5 (volatility floor)
- weather-vane-v4 (tide detection)
- weather-vane-v3 (z-score + accel)
- weather-vane-v2 (hysteresis, derivative, integral)
- progressive-context-shaping (CURRENT.md)
- directional-outcome-tracker (signal gate)
