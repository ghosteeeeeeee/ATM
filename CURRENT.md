# Current State — System Improvement Focus

**Last Updated: 2026-09-03 ~10:32 UTC (CEO)**
**Updated by: CEO**

## Current Status

Today (Sep 3) is BEST DAY since Aug 28: 65.4% WR. Kills verified working. accel-300-v3-long+ CEO_PROTECTION expires tomorrow Sep 4 05:00.

- **24h:** 52T, 57.7% WR, -$1.16 (verified from DB)
- **Today (Sep 3):** 26T, 65.4% WR, -$0.11 (best day since Aug 28)
- **7d:** 399T, 51.6% WR, -$2.35
- **7d LONG:** 167T 47.3% WR -$2.97 (bleeding — v3-long+ $1.18, v2-long $0.74 legacy)
- **7d SHORT:** 232T 54.7% WR +$0.62 (profitable)
- **Market:** NEUTRAL (100% of trades)
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **RANGE_REVERSION KILLED.** Zero post-kill trades. NEVER_REENABLE_FLAGS.
- **R2_TREND_LONG KILLED.** signal_reporter killed Sep 3. NEVER_REENABLE_FLAGS. 0 new trades post-kill.
- **ACCEL_300_V3_LONG:** CEO_PROTECTED until Sep 4 05:00 UTC. 20T/7d 35% WR -$1.18. ALL ATR_SL. Needs T DISABLE after expiry.
- **BB_BOUNCE_V2_LONG:** Live. 13T/7d 76.9% WR +$0.20. Strong performer.
- **EMA300_DIP:** Live. 14T/7d 71.4% WR +$0.19. Strong performer.
- **Coin tracker:** FIXED. Timer enabled, running every 30min.
- **CONF_FILTER_MIN=70.** Lowered from 75.
- **Disk:** 82% (approaching 85% trigger)
- **Open positions:** 5 (bb-bounce-v2-long+ x2, ema300-dip, bb-bounce-short, slow-grind-). ~$0 unrealized.
- **Core backbone:** accel-300-v2- SHORT 72T/7d +$1.46 52.8% WR. bb-bounce-short 58T/7d 63.8% WR +$0.06.
- **Top performer:** bb-bounce-v2-long+ 13T/7d 76.9% WR +$0.20. ema300-dip 14T/7d 71.4% WR +$0.19.

**⚠️ CEO-PROTECTED BLEEDER (PENDING):**
1. **accel-300-v3-long+** — 20T/7d 35% WR -$1.18. CEO_PROTECTED until Sep 4 05:00 UTC. Needs DISABLE after expiry.

## Today's Changes (Sep 3)

0. **CEO 10:32 — VERIFIED + UPDATE.** DB: 24h 52T 57.7% WR -$1.16. Today: 26T 65.4% WR -$0.11 (BEST DAY since Aug 28). Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.11 (improving). 9 hours traded, 6 green hours. Kills verified: range-reversion 0 post-kill trades (last closed Sep 2 13:50), r2-trend-long3 0 post-kill trades (last closed Sep 3 01:02). accel-300-v3-long+ still CEO_PROTECTED, 4T/24h 25% WR -$0.48. Open positions flat (~$0 unrealized). No signal_compactor timeout issues in recent logs. **ACTIONS: (1) Updated CURRENT.md. (2) Prepared to disable accel-300-v3-long+ tomorrow. (3) Monitoring bb-bounce-v2-long+ and ema300-dip for expansion.**

## Today's Changes (Sep 3)

0. **CEO 06:34 — VERIFIED + UPDATE.** DB: 24h 52T 51.9% WR -$1.63. 7d: 399T 51.6% WR -$2.35. **r2-trend-long3 KILL CONFIRMED** — signal_reporter killed it, 0 new trades post-kill (last trade closed 01:02 UTC). accel-300-v3-long+ still CEO_PROTECTED, 4 trades/24h ALL ATR_SL losers (-$0.59). bb-bounce-v2-long+ 13T/7d 76.9% WR +$0.20 strong. ema300-dip 9T/7d 66.7% WR +$0.16. 5 open positions all small. Disk 82%. Market 100% NEUTRAL. Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.17 (improving).
1. **CEO 02:15 — VERIFIED + ESCALATION.** DB: 24h 52T 51.9% WR -$1.86. 7d: 399T 51.6% WR -$2.35. 3 consecutive negative days. **ESCALATED to T: (1) DISABLE r2-trend-long3 — 10T/7d 30% WR -$0.55, CEO_PROTECTED since Aug 17, now bleeding. (2) DISABLE accel-300-v3-long+ after Sep 4 05:00 UTC — 18T/7d 33.3% WR -$0.98.** bb-bounce-v2-long+ 12T/7d 83.3% WR +$0.35 strong. volume-breakout 6T/7d confluence 100% WR. SHORT side +$0.62/7d profitable. System needs T approval to kill 2 protected bleeders.

## Today's Changes (Sep 2)

0. **Orchestrator 18:35 — VERIFIED.** All systems nominal. Dead signals (v3-long+, range-reversion) confirmed 0 post-kill trades. LONG_NEUTRAL_BLOCK working: ME LONG allowed (LONG_BIAS regime bypass). BTC-CRASH filter active, blocking SHORTs during BTC weakness. 5 open positions, -$0.15 unrealized. 59 closed today, -55% portfolio PnL (bad day but filters working). confluence-/ichimoku- SHORT still bleeding 7T/7d 28.6% WR -$0.46, CEO_PROTECTED. Disk 82%. No changes needed — steady state. NEVER_REENABLE enforcement flagged by signal reporter (code-level fix needed).
1. **CEO 14:40 — ACTION. LONG_NEUTRAL_BLOCK.** DB: 24h 63T 42.9% WR -$1.96. 7d: 411T 50.1% WR -$2.19. LONG side -$2.07/24h ALL signals negative. SHORT +$0.11/24h. ALL 63 trades in NEUTRAL. **ROOT CAUSE: No regime filter for LONG entries.** FIX: Added LONG_NEUTRAL_BLOCK_ENABLED=True + check in signal_compactor.py. Blocks LONG when 4h regime NEUTRAL. Bypass: 2+ types or 1m LONG_BIAS. V3_LONG + range_reversion kills verified (zero post-kill trades). BB_BOUNCE_V2_LONG TESTING, 0 trades. confluence-,ichimoku- SHORT CEO_PROTECTED FLAGGED FOR T.
1. **CEO 10:30 — VERIFIED + ACTION.** DB: 24h 59T 47.5% WR -$1.18. 48h: 128T 47.7% WR -$1.97. 7d: 417T 50.6% WR -$1.12. Today Sep 2: 37T 48.6% WR -$0.74. **BUG: accel-300-v2-short- still trading despite ACCEL_300_V2_ENABLED=False.** 7T/24h 28.6% WR -$0.06. Flag was True until commit 383057fb at 02:59 UTC. **FIX: Added ACCEL_300_V2_ENABLED + ACCEL_300_V2_MINUS_ENABLED to NEVER_REENABLE_FLAGS.** SHORT backbone 72T/7d +$1.46 52.8% WR strong. BB_BOUNCE_SHORT 4T/24h +$0.14 100% WR. 5 open range-reversion-long+ positions (breakeven). confluence-,ichimoku- SHORT still CEO_PROTECTED bleeding -$0.46/7d — FLAGGED FOR T. Market ALL NEUTRAL.
1. **CEO 09:00 — VERIFIED + ACTION.** DB: 24h 60T 48.3% WR -$1.15. 48h: 129T 48.1% WR -$1.95. 7d: 418T 50.5% WR -$1.41. **ROOT CAUSE: accel-300-v3-long+ RE-ENABLED after first kill** — was set True with tighter filters (MIN_GAP=2.0), still bleeding 16T/24h -0.70 37.5% WR, ALL ATR_SL in NEUTRAL. **KILLED AGAIN + added to NEVER_REENABLE_FLAGS.** BB_BOUNCE_V2_LONG NameError auto-fixed at 08:25, now live TESTING. 5 open range-reversion-long+ positions (GRASS, SOL, NEO, ALT, DOGE). SHORT +$0.36/24h, LONG -$1.51/24h. confluence-,ichimoku- SHORT still CEO_PROTECTED bleeding -$0.46/7d — FLAGGED FOR T.
1. **Orchestrator 06:38 — ACTION.** Killed BB_BOUNCE_LONG_ENABLED. DB verified: 24h 64T 48.4% WR -$1.06, 7d 418T 50.5% WR -$1.11. BB_BOUNCE_LONG: 17T/24h 52.9% WR -$0.36. Removed from CEO_PROTECTED_FLAGS, kept in NEVER_REENABLE_FLAGS. Disk 82%. 1 open (DOGE SHORT flat). Signal reporter flagged accel-300-v3-long+ 15T/24h 40% WR -$0.62 for tuning. confluence-,ichimoku- SHORT 7T/7d 28.6% WR -$0.46 flagged for T review. CONF_FILTER_MIN lowered to70 (from 75) — stale issue resolved.
1. **CEO 06:10 — VERIFIED + ACTION.** DB: 24h 63T 49.2% WR -$0.90 (improved from -$0.97). V3_LONG kill verified — last trade 05:15, no post-kill entries. **FIXED coin tracker timer** — 18 days stale → running every 30min, 96 coins processed. BB_BOUNCE_LONG still bleeding 18T/24h -$0.29, FLAGGED FOR T. CONF_FILTER_MIN gap — trades at conf=51,59,60,62 executing despite filter=70. 3 open positions. Daily trend: Aug 28 +$1.55 → Sep 2 -$0.24 (in progress).
1. **CEO 07:30 — VERIFIED + ACTION.** DB: 24h 61T 47.5% WR -$0.97. 7d: 416T 50.0% WR -$1.31. 48h: 127T 47.2% WR -$1.71. **ROOT CAUSE CORRECTED: Previous CEO overcounted — combined accel-300-v2-long + v3-long as one signal.** Actual v2-long: only 4T/24h (closing old positions, not new entries). v3-long: 14T/24h -$0.51, 42.9% WR, ALL ATR_SL — the real #1 loss source. **KILLED ACCEL_300_V3_LONG_ENABLED.** NOT CEO_PROTECTED. BB_BOUNCE_LONG still True, CEO_PROTECTED, FLAGGED for T. 7d SHORT profitable (+$0.48), LONG bleeding (-$1.79). System needs SHORT-heavy allocation.
1. **CEO 06:00 — VERIFIED + CRITICAL FLAG.** DB: 24h 60T 46.7% WR -$1.08. 7d: 405T 50.6% WR -$0.62. 48h: 114T 46.5% WR -$1.49. **CRITICAL DISCOVERY: accel-300-v2-long STILL TRADING despite constant=False.** 11T/24h -$0.52, 27.3% WR. Previous CEO run at 01:40 reported "DEAD (zero trades post-kill)" — WRONG. This is the #1 bleeding source. Needs CODE investigation — check signals_runner.py for cached imports or bypass paths. BB_BOUNCE_LONG_ENABLED still True, 23T/24h -$0.28 bleeding. 5 open SHORT (all slightly profitable). System profitable without these 2 blockers (+$1.72/7d).
2. **CEO 01:40 — VERIFIED + FLAGGED.** DB: 24h 62T 48.4% WR -$1.00. 7d: 406T 50.7% WR -$0.61. WITHOUT LEGACY: +$1.72/7d 54.7% WR. FLAGGED bb-bounce-long+ and confluence-,ichimoku- for T review.

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

- **LONG_NEUTRAL_BLOCK DEPLOYED.** Blocks LONG entries when 4h regime is NEUTRAL. Expected to stop -$1.50+/24h LONG bleeding. Bypass: 2+ signal types or 1m LONG_BIAS. — 2026-09-02
- **RANGE_REVERSION KILLED.** 6T/24h standalone -$0.62, 16.7% WR. ALL ATR_SL in NEUTRAL. Added to NEVER_REENABLE_FLAGS. — 2026-09-02
- **R2_TREND_LONG KILLED.** signal_reporter killed Sep 3. NEVER_REENABLE_FLAGS. 0 new trades post-kill. — 2026-09-03
- **ACCEL_300_V3_LONG CEO_PROTECTED until Sep 4 05:00.** 19T/7d 31.6% WR -$1.21. ALL ATR_SL. Needs T DISABLE after expiry. — 2026-09-02
- **BB_BOUNCE_V2_LONG LIVE.** 13T/7d 76.9% WR +$0.20. Strong performer, candidate for expansion. — 2026-09-02
- **CONF_FILTER_MIN=70.** Lowered from 75. — 2026-09-02
- **volume_breakout ACTIVE.** 6T/7d confluence 100% WR +$0.40, standalone 0% WR -$0.29. — 2026-08-31
- **DELEGATED: Build NEUTRAL regime signal.** 3rd backbone candidate. — 2026-09-01
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- DEAD.** All 3 variants disabled (SHORT killed Aug 31). NEVER_REENABLE_FLAGS. — 2026-08-31
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11. CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 3T/7d +$0.30 66.7% WR. CEO_PROTECTED. — 2026-08-23
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** Filters weak entries. — 2026-08-29

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **T: DISABLE accel-300-v3-long+ after Sep 4 05:00 UTC.** 19T/7d 31.6% WR -$1.21. CEO_PROTECTED expires then. — 2026-09-04
2. **Monitor bb-bounce-v2-long+.** 13T/7d 76.9% WR +$0.20. Consider expanding if holds. — 2026-09-03
3. **Monitor ema300-dip.** 9T/7d 66.7% WR +$0.16. Good standalone performer. — 2026-09-03
4. **Monitor volume_breakout.** 6T/7d — confluence trades 100% WR, standalone 0%. Need more data. — 2026-09-03
5. **Monitor disk.** Currently 82%. Below 85% trigger. — 2026-09-03
6. **Monitor signal_compactor timeouts.** 6x in last 2h — non-fatal but investigate if persistent. — 2026-09-03
