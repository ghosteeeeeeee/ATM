# Upgrade Audit Trail

Scanned: 24 plans (2026-08-23)
Implemented: 13 | Partial: 3 | Resolved: 3 | Pending Level 1: 3 | Pending Level 2+: 2

---

## IMPLEMENTED (13)

### btc-crash-filter-plan.md
- Difficulty: Level 2 | Value: HIGH
- BTC crash detection + acceleration filter. Phase 1 (absolute threshold) + Phase 2 (acceleration detection) deployed.

### weather-vane-v4-tide-detection.md
- Difficulty: Level 2 | Value: MEDIUM
- BTC 3h momentum + SHORT WR tide indicator. TIDE_ENABLED + get_tide_penalty() in signal_compactor.py.

### weather-vane-v5-volatility-floor.md
- Difficulty: Level 1 | Value: HIGH
- Block low-volatility entries. VOL_FLOOR_THRESHOLD=0.15% in signal_compactor.py.

### hl-reconciliation-postmortem-spec.md
- Difficulty: Level 2 | Value: HIGH
- Automated HL reconciliation. Status: IMPLEMENTED per plan.

### favorites-daily-update-spec.md
- Difficulty: Level 3 | Value: MEDIUM
- Daily favorites + rhythm + hebbian sync. All scripts exist.

### directional-outcome-tracker-spec.md
- Difficulty: Level 2 | Value: HIGH
- Weather vane trade outcome suppression. DIRECTIONAL_OUTCOME_ENABLED=True.

### imx-spike-detection.md / atr-spike-signal-build.md / atr-spike-backtest-results.md
- Difficulty: Level 2 | Value: HIGH
- ATR compression breakout signal. atr_spike.py enabled with trend filter + EMA proximity.

### short-bias-fix.md
- Difficulty: Level 1 | Value: MEDIUM
- SHORT starvation investigation. EMA penalty reverted, Trend Alignment confirmed as hard block.

### sl-tuning.md
- Difficulty: Level 1 | Value: MEDIUM
- ATR spike SL tuning. 0.75% SL applied (ATR_SPIKE_SL_PCT=0.75). Best params confirmed.

### conf-filter-plan.md (partial)
- Difficulty: Level 1 | Value: HIGH
- CONF_FILTER_MAX=89 deployed. TIME_BLOCK deployed as penalty (0.7x during 01-06 UTC).

### confidence-calibration-plan.md
- Difficulty: Level 2 | Value: LOW
- Investigation complete. CONF_FILTER already blocks worst cases. Non-monotonic curve is noise.

### weather-vane-v2-spec.md / v3-spec.md
- Superseded by v4/v5. No action needed.

### coin_tracker_analysis_expansion.md
- Difficulty: Level 3 | Value: MEDIUM
- Phase 1 complete (Wyckoff, Elliott Wave, S/R, Trend, Volume Profile). ct-hot signal killed but analysis feeds dashboard.

---

## PENDING — LEVEL 1 (3 quick wins)

### atr-sl-widen.md — MAE Guard disable (net -$5.43/week)
- Difficulty: Level 1 | Value: HIGH
- MAE Guard at 1.5% is HURTING: kills winners that would recover. 7-day sim shows -$5.43/week.
- **Action:** Set CL_MAE_GUARD_ENABLED = False in hermes_constants.py

### atr-sl-widen.md — features_recorded bug
- Difficulty: Level 1 | Value: HIGH
- record_entry_features() writes data but features_recorded column stays FALSE.
- **Root cause (2026-08-23):** momentum_cache stores slope/regime/trend but NOT rsi_14/macd_hist/atr_14/bb_position. record_entry_features() gets all-NULL row → falls back to _compute_intel_from_prices() → often insufficient data (<26 prices) → returns False. Only 3/38 recent trades recorded.
- **Fix needed:** Populate momentum_cache with full indicators in 15m/4h regime scanners, OR modify record_entry_features() to compute directly from price_history when momentum_cache is empty.

### r2-trend-long-trailing-sl-tuning.md
- Difficulty: Level 1 | Value: MEDIUM
- TRAILING_DISTANCE_PCT already widened to 2.0% — APPLIED. No further action.

---

## PENDING — LEVEL 2+ (2 candidates)

### copy-trader-dashboard-enhancements.md
- Difficulty: Level 2-4 | Value: MEDIUM
- Phase 1 complete (stats, trader cards, equity curve). Phase 2-4 not started.

### retroactive-scan-delayed-entry.md
- Difficulty: Level 3 | Value: MEDIUM
- Retroactive breakout scan. atr_spike.py covers some overlap. Full plan not implemented.

---

## RESOLVED / NO ACTION (3)

### coin_tracker_setup_improvements.md
- Difficulty: Level 2 | Value: LOW
- ct-hot signal killed. Setup improvements irrelevant (dashboard only).

### progressive-context-shaping-spec.md
- Difficulty: Level 1 | Value: LOW
- DRAFT. Awaiting CEO feedback.

### favorites-daily-update-spec.md (rhythm part)
- Already implemented. favorites_rhythm.py + favorites_hebbian_sync.py exist.

---

## Summary

| Category | Count |
|----------|-------|
| Implemented | 13 |
| Pending Level 1 | 3 (MAE guard, features_recorded, trailing SL verify) |
| Pending Level 2+ | 2 (copy-trader, retroactive scan) |
| Resolved/No Action | 3 |
| Superseded | 2 |
| **Total scanned** | **24** |

## Next Candidates

1. **MAE Guard disable** — Level 1 — HIGH value — saves ~$5.43/week
2. **features_recorded backfill** — Level 1 — HIGH value — enables entry feature analysis
3. **Copy-trader dashboard Phase 2** — Level 2 — MEDIUM value — copy delay analysis
