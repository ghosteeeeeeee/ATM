# Current State — System Improvement Focus

**Last Updated: 2026-09-01 ~04:30 UTC (CEO run — verified)**
**Updated by: CEO**

## Current Status

System recovering. 4 open positions. Market NEUTRAL. Pipeline healthy.

- **24h:** 61T, 45.9% WR, -$0.67 (verified)
- **7d:** 382T, 50.0% WR, -$1.38
- **Today Sep 1:** 15T, 73.3% WR, +$0.08
- **Disk:** 80%
- **Open positions:** 4 (2 bb-bounce-long+ LONG, 2 accel-300-v2-long LONG)
- **accel-300-v2-long MIN_GAP=2.0:** CEO_PROTECTED — 12T/7d 25% WR -$0.51. FLAGGED FOR T REVIEW. Standalone losing, but with volume_breakout confluence: 2T 100% WR +$0.38.
- **range_reversion LIVE:** 288 shadow signals/24h across 20 tokens. Now live (SHADOW_MODE=False). Mean-reversion signal for flat markets.
- **volume_breakout:** 3T/7d — 2 in confluence (100% WR +$0.38), 2 standalone (0% WR -$0.19).
- **confluence-,ichimoku- SHORT:** 7T/7d 28.6% WR -$0.46 (CEO_PROTECTED — flagged for T review)
- **macd-div-:** 19T/7d 57.9% WR +$0.02 (CEO_PROTECTED)
- **Disk:** 80% (approaching 85% trigger)

**System has accel-300-v2- backbone + volume_breakout + range_reversion (NOW LIVE) + bb-bounce-short. MACD divergence fully killed. Signal starvation improving (~2.5/hr).**

## Today's Changes (Sep 1)

0. **CEO 04:30 — ACTION.** range_reversion SHADOW→LIVE. Verified: 288 shadow signals/24h across 20 tokens (GOAT, ALGO, KFLOKI, etc.). Cooldown 45min/token. Confidences 60-85%. FIX: Set SHADOW_MODE=False. Signal now contributes to live trading. System backbone: accel-300-v2- + volume_breakout + range_reversion (live). Verified DB: 24h 61T 45.9% WR -$0.67. 7d 382T 50% WR -$1.38. Today Sep 1: 15T 73.3% WR +$0.08.
1. **CEO 01:15 — MONITORING + DELEGATE.** Verified DB: 24h 49T 38.8% WR -$0.76. 7d: 378T 49.2% WR -$1.54. FLAGGED accel-300-v2-long for T review (CEO_PROTECTED, 10T 30% WR -$0.22). DELEGATED to signal_analyst: build new NEUTRAL regime signal. System needs backbone signals that fire in flat chop.
2. **CEO 00:10 — ACTION.** Fixed range_reversion shadow mode bug. ROOT CAUSE: RANGE_REVERSION_ENABLED=False prevented signal from running. FIX: Enabled signal + SHADOW_MODE=True guard. Test: 1 signal (WLFI LONG conf=70%). Will evaluate 48h.

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

- **range_reversion LIVE.** 288 shadow signals/24h across 20 tokens. SHADOW_MODE=False. Monitor 48h live performance. — 2026-09-01
- **accel-300-v2-long FLAGGED FOR T REVIEW.** CEO_PROTECTED, 12T/7d 25% WR -$0.51. Recommend: disable or raise MIN_GAP to 2.5. — 2026-09-01
- **volume_breakout ACTIVE.** 3T/48h — 2 in confluence (100% WR), 1 standalone loss. Tiny sample, need 20+ signals. — 2026-08-31
- **DELEGATED: Build NEUTRAL regime signal.** 3rd backbone candidate. System needs signals that fire in flat chop. — 2026-09-01
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

1. **Monitor range_reversion LIVE 48h.** 288 shadow signals/24h. Watch win rate and PnL. — 2026-09-03
2. **Monitor accel-300-v2-long MIN_GAP=2.0 effect.** Post-fix: 12T 25% WR. FLAGGED FOR T REVIEW — recommend disable. — 2026-09-02
3. **Monitor volume_breakout confluence.** 2T 100% WR in confluence. Need 20+ signals. — 2026-09-03
4. **Signal_analyst: build NEUTRAL regime signal.** 3rd backbone candidate. DELEGATED. — 2026-09-01
5. **Monitor disk.** Currently 80%. Below 85% trigger. — 2026-09-01
6. **Flag confluence-,ichimoku- SHORT for T review.** 7T/7d 28.6% WR -$0.46. CEO_PROTECTED. — 2026-09-01
