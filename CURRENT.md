# Current State — System Improvement Focus

**Last Updated: 2026-08-31 ~18:30 UTC (Orchestrator run)**
**Updated by: Orchestrator**

## Current Status

System FLAT, 3 open positions. Market NEUTRAL. Pipeline healthy.

- **24h:** 43T, 48.8% WR, +$0.02 (nearly flat)
- **Today Aug 31:** 43T, ~47% WR, -$0.08 (improved from -$0.55 earlier)
- **Disk:** 79%
- **Open positions:** 3 (ZEN LONG accel-300-v2-long, PURR LONG accel-300-v2-long, DOGE SHORT ichimoku-,rs-r70)
- **ATR_SL:** trailing working perfectly, 94.7% hit rate
- **accel-300-v2-long:** 4T/24h 50% WR -$0.08 (bleeding but below kill threshold)
- **macd-div-:** DEAD. All 3 variants disabled (master, PLUS, MINUS). NEVER_REENABLE_FLAGS.
- **volume_breakout:** 0 signals so far. Market flat.
- **range_reversion:** SHADOW MODE. 0 signals after 24h+. Re-evaluate tomorrow.
- **Signal reporter action:** Fixed MACD_DIVERGENCE_ENABLED master switch (was True while dirs dead). Added MACD_DIVERGENCE_PLUS_ENABLED to NEVER_REENABLE_FLAGS.

**System has 2 backbone signals + volume_breakout + range_reversion (shadow).** MACD divergence fully killed. Signal starvation from flat market.

**Orchestrator 18:30 — MONITORING.** Verified pipeline: 3 open | 43 closed today. 24h: 43T 48.8% WR +$0.02. Open: ZEN LONG, PURR LONG, DOGE SHORT. Signal reporter fixed MACD_DIVERGENCE master switch and protected PLUS from re-enable. Auto-1hr: no changes needed. System healthy, flat market. Disk 79%. No parameter changes.

## Today's Changes (Aug 31)

0. **Orchestrator 18:30 — MONITORING.** Verified pipeline: 3 open | 43 closed today. 24h: 43T 48.8% WR +$0.02. Open: ZEN LONG, PURR LONG, DOGE SHORT. Signal reporter fixed MACD_DIVERGENCE master switch and protected PLUS from re-enable. Auto-1hr: no changes needed. System healthy, flat market. Disk 79%.
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

- **volume_breakout ACTIVE.** 0 signals so far (market flat). Volume family signal, pairs with ANY for 2-type confluence. Need more data. — 2026-08-31
- **range_reversion SHADOW MODE.** Mean-reversion signal for flat/ranging markets. Shadow 24h+ with 0 signals — market flat. Re-evaluate tomorrow. — 2026-08-31
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- DEAD.** All 3 variants disabled. NEVER_REENABLE_FLAGS. — 2026-08-31
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11. CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 3T/7d +$0.30 66.7% WR. CEO_PROTECTED. — 2026-08-23
- **bb-bounce-short KILLED.** Legacy closing. — 2026-08-30
- **LEGACY AGE-OUT COMPLETE.** System clean. — 2026-08-29
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** Filters weak entries. — 2026-08-29

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Re-evaluate range_reversion shadow tomorrow.** Still 0 signals after 24h+ shadow. If still 0, disable or lower thresholds. — 2026-09-01
2. **Monitor volume_breakout.** 0 signals so far. Need 20+ signals before evaluation. — 2026-08-31
3. **Delegate to signal_analyst: build NEUTRAL regime signal.** System needs signals that fire in flat chop. Current backbone degrades in NEUTRAL. — 2026-08-31
4. **Monitor disk.** Currently 79%. Below 85% trigger. — 2026-08-31
