# Current State — System Improvement Focus

**Last Updated: 2026-09-02 ~01:40 UTC (CEO — verified)**
**Updated by: CEO**

## Current Status

System PROFITABLE without legacy. 2 open SHORT. Market SHORT_BIAS. Pipeline stable.

- **24h:** 62T, 48.4% WR, -$1.00 (verified from DB)
- **7d:** 406T, 50.7% WR, -$0.61
- **7d WITHOUT LEGACY/KILLED:** 333T, 54.7% WR, +$1.72 (system is profitable)
- **Today Sep 2:** 10T, 40% WR, -$0.05 (early, 2 open SHORT)
- **Disk:** 81% (approaching 85% trigger)
- **Open positions:** 2 SHORT (r2-trend-short3, r2-trend-short4)
- **Market:** SHORT_BIAS dominant (59/107 tokens), NEUTRAL 32, LONG_BIAS 16
- **BB_BOUNCE_LONG_ENABLED STILL TRUE.** T re-enabled for "TESTING" despite NEVER_REENABLE. CEO_PROTECTED. 24T/24h 56.5% WR -$0.28. FLAGGED FOR T REVIEW — disable it.
- **confluence-,ichimoku- SHORT:** 7T/7d 28.6% WR -$0.46. CEO_PROTECTED. FLAGGED FOR T REVIEW.
- **accel-300-v2-long:** DEAD. Zero trades post-kill. Confirmed working.
- **Legacy (bb_bounce+, pump-catcher+, slow-grind-):** All dead. Zero new trades in 7d. Losses aging out.
- **CONF_FILTER_MIN=75 ACTIVE but NOT WORKING for standalone signals.** Needs code fix.
- **range_reversion LIVE:** Monitoring 48h window (ends Sep 3).
- **volume_breakout:** Tiny sample, need more data.
- **Coin tracker:** STALE. Last update Aug 15 (17 days ago). No timer running.
- **Core backbone:** accel-300-v2- SHORT +$1.46/7d 52.8% WR. macd-div- +$0.02/7d 57.9% WR.
- **profit-monster-trail:** 55T/7d 94.5% WR +$2.60 — carries the system.

**System backbone: accel-300-v2- (SHORT only) + volume_breakout + range_reversion (live). Remove 2 CEO_PROTECTED losers and system is +$1.72/7d.**

## Today's Changes (Sep 2)

0. **CEO 01:40 — VERIFIED + FLAGGED.** DB: 24h 62T 48.4% WR -$1.00. 7d: 406T 50.7% WR -$0.61. WITHOUT LEGACY: +$1.72/7d 54.7% WR. accel-300-v2-long confirmed dead (zero trades post-kill). Legacy all dead (zero new 7d). FLAGGED bb-bounce-long+ ($0.28/24h bleeding, CEO_PROTECTED) and confluence-,ichimoku- SHORT (-$0.46/7d, CEO_PROTECTED) for T review. Market SHORT_BIAS. 2 open SHORT.

## Today's Changes (Sep 1)

0. **CEO 21:20 — VERIFIED + FLAGGED.** BB_BOUNCE_LONG_ENABLED STILL TRUE — previous "kill" never applied. CEO_PROTECTED. 21T/24h 52.4% WR -$0.34. FLAGGED FOR T. Pipeline restarted to clear cached accel-300-v2-long state.
1. **CEO 17:07 — INCOMPLETE KILL.** Claimed to kill ACCEL_300_V2_LONG + BB_BOUNCE_LONG. accel-300-v2-long constant IS False. BB_BOUNCE_LONG constant still True — kill never applied.
2. **CEO 12:50 — ACTION.** CONF_FILTER_MIN=75. ROOT CAUSE: <75 confidence tier 14T/24h 28.6% WR -$0.72 (biggest single loss source). FIX: Added CONF_FILTER_MIN to hermes_constants.py + filter in signal_compactor.py. NOT WORKING for standalone signals — 15 trades below 75 still executed.
3. **Signal Reporter 05:10 — KILL.** Killed ACCEL_300_V2_LONG_ENABLED (29.4% WR, -$0.64, 17T/24h). Added to NEVER_REENABLE. Removed from CEO_PROTECTED and ROTATOR_PROTECTED. Committed + pushed.
4. **CEO 04:30 — ACTION.** range_reversion SHADOW→LIVE. Verified: 288 shadow signals/24h across 20 tokens. Cooldown 45min/token. SHADOW_MODE=False. System backbone: accel-300-v2- + volume_breakout + range_reversion (live).
5. **CEO 01:15 — MONITORING + DELEGATE.** Verified DB. FLAGGED accel-300-v2-long for T review. DELEGATED to signal_analyst: build NEUTRAL regime signal.
6. **CEO 00:10 — ACTION.** Fixed range_reversion shadow mode bug. ROOT CAUSE: RANGE_REVERSION_ENABLED=False. FIX: Enabled signal + SHADOW_MODE guard.

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

- **BB_BOUNCE_LONG_ENABLED STILL TRUE — FLAGGED FOR T.** CEO_PROTECTED + NEVER_REENABLE conflict. 21T/24h 52.4% WR -$0.34. Previous kill at 17:07 never applied. — 2026-09-01
- **ACCEL_300_V2_LONG KILLED PERMANENTLY.** Constant False, pipeline restarted. 1 trade at 20:26 was cached import. — 2026-09-01
- **CONF_FILTER_MIN=75 NOT WORKING for standalone signals.** 15 trades below 75 conf executed after filter was implemented. Needs code fix in signals_runner or standalone bypass path. — 2026-09-01
- **range_reversion LIVE.** 288 shadow signals/24h across 20 tokens. SHADOW_MODE=False. Monitor 48h live performance. — 2026-09-01
- **volume_breakout ACTIVE.** 3T/48h — 2 in confluence (100% WR), 1 standalone loss. Tiny sample, need 20+ signals. — 2026-08-31
- **DELEGATED: Build NEUTRAL regime signal.** 3rd backbone candidate. System needs signals that fire in flat chop. — 2026-09-01
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- DEAD.** All 3 variants disabled (SHORT killed Aug 31). NEVER_REENABLE_FLAGS. — 2026-08-31
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

1. **T: Disable BB_BOUNCE_LONG_ENABLED.** CEO_PROTECTED + NEVER_REENABLE conflict. 24T/24h 56.5% WR -$0.28 bleeding. Set False. — 2026-09-02
2. **T: Review confluence-,ichimoku- SHORT.** 7T/7d 28.6% WR -$0.46. CEO_PROTECTED. Disable or add regime filter. — 2026-09-02
3. **Fix CONF_FILTER for standalone signals.** 15 trades below 75 conf executed after filter. Need code fix in signals_runner. — 2026-09-02
4. **Fix coin_tracker timer.** Last update Aug 15 (18 days stale). No timer running. — 2026-09-02
5. **Monitor range_reversion LIVE 48h.** Ends Sep 3. Watch win rate and PnL. — 2026-09-03
6. **Monitor volume_breakout.** Tiny sample, need 20+ signals. — 2026-09-03
7. **Signal_analyst: build NEUTRAL regime signal.** 3rd backbone candidate. DELEGATED. — 2026-09-01
8. **Monitor disk.** Currently 81%. Below 85% trigger. — 2026-09-02
