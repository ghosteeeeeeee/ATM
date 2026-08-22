# Upgrade Audit Trail

Scanned: 22 plans
Implemented: 9 | Partial: 2 | Resolved: 3 | Not Implemented: 1 | Superseded/Draft: 4 | Unknown: 3

---

## IMPLEMENTED (9)

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

### imx-spike-detection.md / atr-spike-signal-build.md
- Difficulty: Level 2 | Value: HIGH
- ATR compression breakout signal. atr_spike.py enabled.

### short-bias-fix.md
- Difficulty: Level 1 | Value: MEDIUM
- SHORT starvation investigation. EMA penalty reverted, Trend Alignment confirmed.

### sl-tuning.md
- Difficulty: Level 1 | Value: MEDIUM
- ATR spike SL tuning. 0.75% SL applied (ATR_SPIKE_SL_PCT=0.75).

---

## PARTIAL (2)

### conf-filter-plan.md
- Difficulty: Level 1 | Value: HIGH
- CONF_FILTER_MAX=89 working. TIME_BLOCK disabled (was hard block killing all signals 01-06 UTC). Needs rework: per-signal penalty instead of blanket block.

### copy-trader-dashboard-enhancements.md
- Difficulty: Level 2-4 | Value: MEDIUM
- Phase 1 complete (stats, trader cards, equity curve). Phase 2-4 not started.

---

## RESOLVED / NO ACTION NEEDED (3)

### confidence-calibration-plan.md
- Difficulty: Level 2 | Value: LOW
- Investigation complete. CONF_FILTER already blocks worst cases. Non-monotonic curve is noise.

### coin_tracker_setup_improvements.md
- Difficulty: Level 2 | Value: LOW
- Signal killed (32.3% WR). Setup improvements irrelevant.

### progressive-context-shaping-spec.md
- Difficulty: Level 1 | Value: LOW
- DRAFT. Awaiting CEO feedback.

---

## NOT IMPLEMENTED (1)

### retroactive-scan-delayed-entry.md
- Difficulty: Level 3 | Value: MEDIUM
- Retroactive breakout scan. Plan v3 exists but no code found. atr_spike.py covers some overlap.

---

## SUPERSEDED (2)

### weather-vane-v2-spec.md / v3-spec.md
- Superseded by v4/v5.

---

## UNKNOWN (3)

### coin_tracker_analysis_expansion.md
- ct-hot dead. Likely irrelevant.

### r2-trend-long-trailing-sl-tuning.md
- Need to check if applied.

### copy-trader-evolution-spec.md / entry-timing-deep-dive.md
- Need to check status.

---

## Next Candidates (Level 1)

1. **conf-filter-plan.md TIME_BLOCK rework** — Change hard block to 0.7x penalty during 01-06 UTC. HIGH value, already coded, just needs tweak.
2. **BTC accel debug logging** — Add velocity values to crash filter log output. Easy, improves observability.
3. **COPY_BAD_HOURS** — Check if copy signal time blocking is optimal.
