# Current State — System Improvement Focus

**Last Updated: 2026-09-01 ~00:10 UTC (CEO run — verified)**
**Updated by: CEO**

## Current Status

System FLAT, 3 open LONG positions. Market DEAD NEUTRAL. Pipeline healthy.

- **24h:** 48T, 37.5% WR, -$0.82 (worst day since Aug 25 -$1.79)
- **7d:** 377T, 49.1% WR, -$1.60
- **Today Aug 31:** 48T, 37.5% WR, -$0.82 (3-day decline from Aug 28 +$1.55)
- **Disk:** 80%
- **Open positions:** 3 LONG (all small, <$0.04 each)
- **accel-300-v2-long MIN_GAP=2.0:** Post-fix 4T 50% WR +$0.46 (vs pre-fix 8T 12.5% WR -$0.74). Fix working.
- **range_reversion SHADOW:** FIXED — was broken (ENABLED=False = never ran). Now enabled + SHADOW_MODE=True guard. Test: 1 signal (WLFI LONG). Will evaluate 48h.
- **volume_breakout:** 2T/24h, 100% WR, +$0.38. Tiny sample.
- **confluence-,ichimoku- SHORT:** 3T/24h 0% WR -$0.28 (CEO_PROTECTED — flagged for T review)
- **macd-div-:** 3T/24h 33.3% WR -$0.08 (CEO_PROTECTED)
- **Disk:** 80% (approaching 85% trigger)

**System has accel-300-v2- backbone + volume_breakout + range_reversion (shadow). MACD divergence fully killed. Signal starvation from flat market (~2/hr).**

**CEO 00:10 — ACTION.** Fixed range_reversion shadow mode bug. ROOT CAUSE: RANGE_REVERSION_ENABLED=False prevented signal from running (registry skips disabled). 0 signals after 25h+ was code bug, not market. FIX: Enabled signal + SHADOW_MODE=True guard. Test run: 1 signal emitted (WLFI). Will evaluate48h shadow before enabling live.

## Today's Changes (Sep 1)

0. **CEO 00:10 — ACTION.** Fixed range_reversion shadow mode bug. ROOT CAUSE: RANGE_REVERSION_ENABLED=False prevented signal from running. FIX: Enabled signal + SHADOW_MODE=True guard. Test: 1 signal (WLFI LONG conf=70%). Will evaluate 48h.

## Today's Changes (Aug 31)

0. **CEO 20:00 — ACTION.** Raised ACCEL_300_V2_LONG_MIN_GAP 1.5→2.0. ROOT CAUSE: 5T/24h 20% WR, ALL ATR_SL exits at -4.5% to -4.9%. Same pattern as SHORT fix (Aug 29). Expected: fewer trades but higher WR.
1. **Orchestrator 18:30 — MONITORING.** Verified pipeline: 3 open | 43 closed today. 24h: 43T 48.8% WR +$0.02. Open: ZEN LONG, PURR LONG, DOGE SHORT. Signal reporter fixed MACD_DIVERGENCE master switch and protected PLUS from re-enable. Auto-1hr: no changes needed. System healthy, flat market. Disk 79%.
1. **Signal Reporter 17:11 — FIX.** Fixed MACD_DIVERGENCE_ENABLED master switch True→False (both directions already dead). Added MACD_DIVERGENCE_PLUS_ENABLED to NEVER_REENABLE_FLAGS. No new kills, no boosts. System healthy.
2. **CEO 16:30 — MONITORING.** Verified DB: 24h 42T 42.9% WR -$0.33. Open: 1. macd-div- DEGRADED flagged for T review. ATR_SL MIN_GAP=2.0 working. No parameter changes.
3. **CEO 15:30 — MONITORING.** Verified DB: 24h 39T 48.7% WR -$0.56. macd-div- DEGRADED. No changes.
4. **CEO 11:20 — MONITORING.** Verified DB: 24h 40T 50% WR -$0.55. macd-div- STAR DEGRADED. volume_breakout first trade closed. No changes.
5. **CEO 08:00 — MONITORING.** volume_breakout FIRST SIGNAL FIRED. macd-div- degraded. No changes.
6. **CEO 02:45 — MONITORING.** atr_sl_hit trailing profitable. No changes.

## Today's Changes (Aug 30)

0. **CEO 23:00 — CLEANUP.** Disabled stale timers. Verified DB: 24h 36T 55.6% WR -$0.38.
1. **CEO 22:15 — DELEGATE.** Built range_reversion signal (shadow mode). Files: scripts/signals/range_reversion.py. Git: f8a0a72b.
2. **CEO 18:30 — ACTION.** Built volume_breakout signal (NEW backbone). ROOT CAUSE: signal starvation. Files: scripts/signals/volume_breakout.py.
3. **CEO 15:30 — ACTION.** Killed BB_BOUNCE_SHORT_ENABLED. System on 2 backbone: accel-300-v2- + macd-div-.
4. **CEO 07:15 — ACTION.** Reverted bb-bounce-short momentum filter (too aggressive).

## Today's Changes (Aug 29)

0. **CEO 19:00 — ACTION.** Raised ACCEL_300_V2_SHORT_MIN_GAP 1.0→2.0 (filters weak entries).
1. **CEO 16:00 — ACTION.** Killed ACCEL_300_V2_MINUS_ENABLED (25% WR -$0.14).
2. **CEO 14:30 — ACTION.** Killed ACCEL_300_V2_LONG_ENABLED (0 trades in 24h+).
3. **CEO 13:15 — ACTION.** Killed 2 dead signals: INVERSE_ACCEL_300_V2, ACCEL_300_V2_LONG_5M.

## Today's Changes (Aug 28)

1. **CEO 23:10 — MONITORING.** 24h 89T 56.2%WR +$1.55 (best day in weeks). 7d: 448T 49.6%WR -$3.96. Legacy bleed: ct-hot+ -$3.91/7d (CEO_PROTECTED), hl_copy SHORT -$0.65/7d, slow-grind- -$0.64/7d. WITHOUT LEGACY: system fully profitable. Disk 83%.
2. **CEO 06:50 — MONITORING.** 24h 73T 53.4% WR +$0.63. 4 consecutive positive hours. System improving.
3. **Orchestrator 06:35 — DISK CLEANUP.** Journal vacuumed to 500MB (-2G), pump_hunter.log truncated (-24MB). Disk 84% → 83%.
4. **CEO 02:35 — KILLED ATR_SPIKE_ENABLED.** 7T/7d 28.6% WR -$0.15, ALL atr_sl_hit exits. Disabled + added to NEVER_REENABLE.

## Active Decisions

- **range_reversion SHADOW FIXED.** Was broken (ENABLED=False = never ran). Now enabled + SHADOW_MODE=True. Evaluate48h shadow before live. — 2026-09-01
- **volume_breakout ACTIVE.** 2T/24h 100% WR +$0.38. Tiny sample, need 20+ signals. — 2026-08-31
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- DEAD.** All 3 variants disabled. NEVER_REENABLE_FLAGS. — 2026-08-31
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11. CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 3T/7d +$0.30 66.7% WR. CEO_PROTECTED. — 2026-08-23
- **bb-bounce-short KILLED.** Legacy closing. — 2026-08-30
- **LEGACY AGE-OUT COMPLETE.** System clean. — 2026-08-29
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** Filters weak entries. — 2026-08-29
- **ACCEL_300_V2_LONG_MIN_GAP=2.0.** Filters weak LONG entries (same as SHORT fix). — 2026-08-31

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Evaluate range_reversion shadow 48h.** First signal: WLFI LONG conf=70%. Monitor signal quality and frequency. — 2026-09-03
2. **Monitor accel-300-v2-long MIN_GAP=2.0 effect.** Post-fix: 4T 50% WR +$0.46. Need 48h. — 2026-09-02
3. **Delegate to signal_analyst: build NEUTRAL regime signal.** System needs signals that fire in flat chop. range_reversion is first, need more. — 2026-09-01
4. **Monitor disk.** Currently 80%. Below 85% trigger. — 2026-09-01
5. **Flag confluence-,ichimoku- SHORT for T review.** 3T/24h 0% WR -$0.28. CEO_PROTECTED. — 2026-09-01
