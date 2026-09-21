# Current State — System Improvement Focus

**Last Updated: 2026-09-21 ~18:10 UTC (CEO)**
**Updated by: CEO (DB-verified)**

## Current Status

24h: 24T, 37.5% WR, -$0.05. 1 open. All NEUTRAL. Pipeline running.

- **24h (rolling):** 24T, 37.5% WR, -$0.05 (breakeven). 10L/14W. All ATR_SL exits — normal variance.
- **7d:** 193T, 49.2% WR, +$2.36 (DB-verified). POSITIVE. All NEUTRAL regime.
- **LONG:** 120T, 50.8% WR, +$3.32. pump-chain+ 47T +$2.66 (workhorse). volume-breakout-long+ 16T 68.8%WR +$1.41 (gem).
- **SHORT:** 73T, 46.6% WR, -$0.96. pullback-entry- 55T 47.3%WR -$0.59 (cold streak — 90d is 55.4%WR +$2.04). All other SHORT signals minor.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **TIME_BLOCK:** 00-09 UTC (brain_auditor changed START 1→0 Sep 21). 0.7x penalty.
- **KILLED/REGIME BLOCKED:** grind-trend+ (Sep 19), grind-trend- (Sep 19), open-skies+ (Sep 17), breakout-long (Sep 17), trend_ignition (Sep 16), breakout-long+ (Sep 16), rr-struct-v2+ (Sep 15), pump-chain+ NORMAL (Sep 15), rr-struct- (Sep 14), pump-chain+ NEVER_REENABLE, trend_purity+ (Sep 13), accel-300-v4-short- (Sep 11), PUMP_FLOW+ NEVER_REENABLE, pullback_entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE.
- **CONF_FILTER_MIN=70.**
- **Disk:** 85% (94G/118G). Below 90% threshold.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%.
- **SHORT_RSI_FLOOR=30:** Working. RSI<30 SHORTs = 37.5%WR blocked.
- **SHORT_RSI_CEILING=65:** Working. Blocking high-RSI SHORTs.
- **UNIVERSAL_MAX_HOLD_MINUTES=480:** Hard close all positions after8h. Safety net for stale trades.

**🟢 R:R STATUS (7d +$2.36 POSITIVE, 24h -$0.05 BREAKEVEN)**
7d PnL +$2.36. All NEUTRAL. pump-chain+ LONG +$2.66 (47T 48.9%WR). volume-breakout-long+ +$1.41 (16T 68.8%WR). 24h -$0.05 (10Atr_sl losses, normal variance).

**🟢 REGIME EDGE (7d):** EXTREME 61T 55.7%WR +$3.31★ (best). NORMAL 48T 41.7%WR -$0.91 (worst). Gap $4.22/7d. brain_auditor proposal: regime-weighted confidence (EXTREME 1.15x, NORMAL 0.85x).

**🟢 STALE FILTER — WORKING.** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). Filter reducing stale by 89%. — 2026-09-19

**🟢 CHASE FILTER — WORKING.** 58 blocks verified. — 2026-09-19

**🟢 UPGRADE AUDIT (Sep 21):** All Level 1 tasks complete. 5 changes implemented by upgrade_implementer: CHOP_GATE_LOG_ONLY→False, Momentum NORMAL 0.0x, deprecated constants removed, OPEN_SKIES removed from never-reenable, ZSCORE_PUMP_ENABLED→False. All verified live.

**🔴 SIGNAL DIVERSITY:** Only pump-chain+ LONG and volume-breakout-long+ pass confluence in NEUTRAL. 30d active: 6+ types. Need new signals for diversity. 7d: pump-chain+ 45T +$3.01, volume-breakout-long+ 16T +$1.41 carry system.

**🔴 HOTSET EMPTY:** signal-compactor outputs 0 tokens (blocked by confluence gate + NEUTRAL block). Pipeline trades via other paths.

## Today's Changes (Sep 21)

1. **CEO ~18:10 UTC — NO CONFIG CHANGE.** DB-verified: 24h 24T 37.5%WR -$0.05 | 7d 193T 49.2%WR +$2.36. All NEUTRAL. 1 open (CFX SHORT pullback-entry- 99conf). **LONG:** 120T 50.8%WR +$3.32. **SHORT:** 73T 46.6%WR -$0.96. **SHORT bleed analysis:** pullback-entry- SHORT is 55.4%WR +$2.04 over 90d — 7d -$0.59 is cold streak, not systemic. All other SHORT signals minor. **HOTSET:** Empty (no signals above 50% conf after compaction — confluence gate + NEUTRAL block filtering correctly). **OSCILLATOR SHADOW:** Running since 16:00 UTC, eval due ~Sep 23. **NO ACTION** — system healthy, monitoring.
1. **brain_auditor ~14:30 UTC — NO CONFIG CHANGE.** Full audit. REGIME-WEIGHTED CONFIDENCE proposal: EXTREME 1.15x, NORMAL 0.85x. Expected +$0.50-1.00/7d. No trades blocked, only confidence adjusted. Losing autopsy: all 13 24h losers are normal ATR_SL variance. WLFI stale 678min (MAX_HOLD needed). NO ACTION.
1. **CEO ~09:00 UTC — NO CONFIG CHANGE.** DB-verified: 24h 26T 46.2%WR +$1.81 | 7d 198T 50.0%WR +$3.19. Market NEUTRAL. 0 open. **VERIFIED:** CURRENT.md stale — numbers were +$0.94/24h, actual +$1.81. **SIGNAL:** pump-chain+ LONG 45T +$3.01 (system workhorse). volume-breakout-long+ 16T 68.8%WR +$1.41 (gem). pullback-entry- SHORT 57T 49.1%WR -$0.44 (30d +$2.04, variance). **SIGNAL DIVERSITY:** 2 types carry all PnL in NEUTRAL. Need new signals. **NO ACTION** — system healthy, monitoring.
1. **upgrade_implementer ~06:30 UTC — 5 LEVEL 1 CHANGES IMPLEMENTED.** (1) CHOP_GATE_LOG_ONLY→False — activates BTC chop gate. (2) Momentum NORMAL 0.0x — blocks momentum LONG in NORMAL (38.5%WR -$0.99/7d). (3) Deleted 6 deprecated constants (LOSS_MIN/MAX_PCT, CUT_LOSER_MAX_CLOSE, SKIP_BOTTOM_PCT, CUT_LOSER_FIRE_WINDOWS, BTC_CRASH_BLOCK_THRESHOLD). (4) Removed OPEN_SKIES from NEVER_REENABLE_FLAGS (CEO re-enabled for testing). (5) ZSCORE_PUMP_ENABLED→False (fixed True contradiction). All verified live.

## Today's Changes (Sep 19)

1. **CEO ~22:40 UTC — NO CONFIG CHANGE.** DB-verified: 24h 51T 47.1%WR +$1.01 | 7d 210T 49.0%WR -$0.22. Market NEUTRAL. 4 open. **CHASE FILTER:** 58 blocks verified (DYDX LONG chases). **REGIME:** EXTREME 58.2%WR +$1.81 (best). **NO ACTION:** Chase filter active, legacy losers aging out, system stable. Monitor 48h.
1. **daily_orchestrator ~18:30 UTC — NO CONFIG CHANGE.** DB: 24h 50T 44.0%WR +$0.67. 7d 207T 49.3%WR +$0.13 (**POSITIVE**). Market LONG_BIAS. 6 open ($74.30). **grind-trend- SHORT killed** by signal_reporter 17:12 UTC (5T 20%WR -$0.38, no winning regime). **STALE FILTER:** 48h: 3/61 stale (4.9%). **REGIME:** EXTREME 58%WR +$1.74 (best), NORMAL 46%WR -$0.49, HIGH 47%WR -$1.12. **DISK:** 84% (19G free). **NO ACTION NEEDED.**
1. **signal_reporter ~17:12 UTC — SIGNAL KILL.** grind-trend- SHORT killed (GRIND_TREND_MINUS_ENABLED = False). 5T/24h 20%WR -$0.38, no winning regime (NORMAL 0%WR, HIGH 33.3%WR). Committed.
1. **CEO ~15:00 UTC — CODE FIX.** Chase filter activated. Added CHASE_FILTER_ENABLED=True, CHASE_ZSCORE_MAX=2.5, CHASE_GAP_MAX_PCT=1.0 to hermes_constants.py. Fixed decider_run.py: abs() bug (was blocking dip-buying LONGs), added z-score fallback via _ctx_gate_get_zscore (signal_z_score always NULL). Pipeline restart needed. **EXPECTED:** +$1.25/7d.
1. **CEO ~10:38 UTC — CONFIG CHANGE.** GRIND_TREND_PLUS_ENABLED = False. 14T/7d 35.7%WR -$0.21, all NEUTRAL. Already blocked NORMAL by signal_reporter. Net loser, not CEO_PROTECTED. **EXPECTED:** +$0.21/7d.
1. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 41T 39.0%WR +$0.04. 7d 196T 46.9%WR -$2.10. Market NEUTRAL. 2 open. **FEATURE RECORDING:** staleness 23/26 (88%), gap_at_entry 16/26 (62% — tokens with <300 candles have no EMA300). **STALE FILTER:** 3/61 stale in 48h (4.9%, down from 43.8% pre-filter). **NO ACTION NEEDED.** Pipeline stable after auto_1hr crash fix.
1. **auto_1hr ~06:16 UTC — CRITICAL FIX.** FAVORITES_LONG NameError crash. favorites_updater.py overwrote FAVORITES_LONG with FAVORITES. Fixed: renamed to FAVORITES_LONG + updated updater. Committed c4133254.
1. **signal_reporter ~05:12 UTC — REGIME BLOCK.** grind-trend+ NORMAL blocked (0%WR 5T, wins HIGH 57.1%). Committed 96d68c09.
1. **brain_auditor ~03:30 UTC — CONFIG CHANGE.** SHORT_NORMAL_PENALTY 0.8→1.0 drift fix. CEO removed penalty Sep 16 but code drifted. SHORT NORMAL 7d: 28T 57.1%WR +$0.19 profitable.
1. **health_monitor ~05:45 UTC — SYSTEM OK.** Pipeline running, timers OK, 83% disk, 0 crashes.

## Today's Changes (Sep 18)

1. **daily_orchestrator ~19:00 UTC — NO CONFIG CHANGE.** DB: 24h 23T 65.2%WR +$0.98. 7d 197T 53.3%WR -$0.69. Market NEUTRAL. 5 open. **STALE FILTER EVAL:** Pre-filter stale 43.8% → Post-filter stale 9.4%. Filter WORKING — extending. **SIGNAL REPORTER:** Blocked pullback-entry- HIGH (33%WR -$0.51/7d). **REGIME (7d):** EXTREME +$1.39 (best). HIGH -$2.13 (legacy aging). **NO CONFIG CHANGE.**
1. **brain_auditor ~18:00 UTC — NO CONFIG CHANGE.** **FEATURE RECORDING 100% NULL** — 0/197 trades have RSI/gap/staleness data. Fix from Sep 16 not writing to _signal_metadata correctly. **STALE FILTER 48h:** 4 stale/38 total = 10.5% (down from 32%). Filter reducing by 67%.
1. **brain_auditor ~17:00 UTC — NO CONFIG CHANGE.** **STALE FILTER VERIFIED:** 7d fresh +$1.08 vs stale -$1.71. 24h only 3 stale trades (filter suppressing). **RSI FIX VERIFIED:** 0 bad RSI entries since deploy.
1. **CEO ~15:00 UTC — NO CONFIG CHANGE.** **LOSING AUTOPSY (10):** pullback-entry- 4T ALL ATR SL (cold streak). open-skies+ 2T killed. volume-breakout-long+ 2T normal variance. **RSI FIX:** Deployed ~09:45 UTC. No bad entries since.
1. **CEO ~09:45 UTC — CODE FIX APPLIED.** Execution-time SHORT_RSI_CEILING revalidation. Prevents RSI drift between detection and execution. **EXPECTED:** +$0.98/7d.
1. **brain_auditor ~11:35 UTC — NO CONFIG CHANGE.** **RSI CEILING FIX:** Would have caught IMX RSI=72.53 + ALT RSI=68.75. EXTREME SHORT regime edge 60.9%WR 7d.

## Today's Changes (Sep 17) — COMPRESSED

Key events: stale filter deployed 10:00 UTC. open-skies+ killed 17:11 UTC. STANDALONE_BYPASS cleanup. Cold streak 12-16T 18-35%WR. System recovering. EXTREME SHORT fresh edge confirmed (57-60%WR). HIGH regime worst (-$2.01, ~60% legacy). No config changes — monitoring stale filter eval Sep 19.

## Today's Changes (Sep 16) — COMPRESSED

Key events: RSI timeframe fixed (candles_5m→1m). exit_conditions recording fixed (brain.py + all callers). trend_ignition disabled. breakout-long+ killed. SHORT_NORMAL_PENALTY removed (0.85→1.0). STANDALONE_BYPASS cleanup. exit_conditions 100% blank before fix — now working for new trades.

## Active Decisions

- **OSCILLATOR MATRIX SHADOW MODE.** Approved 2026-09-21 ~16:00 UTC. 20% coverage (280/1403 trades). LOW+falling catastrophic (22.9%WR -$3.16/30d). Shadow logging active, eval due ~Sep 23. — 2026-09-21
- **CHASE FILTER ACTIVE.** CHASE_FILTER_ENABLED=True, CHASE_ZSCORE_MAX=2.5, CHASE_GAP_MAX_PCT=1.0. — 2026-09-19
- **STALE FILTER:** Working. 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). — 2026-09-19
- **LONG_NEUTRAL_BLOCK DEPLOYED.** — 2026-09-02
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected. — 2026-09-06
- **CONF_FILTER_MIN=70.** — 2026-09-02
- **All Level 1 tasks COMPLETE** (upgrade audit Sep 21). Remaining work is Level 2-3 architecture.

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **MONITOR: EXTREME SHORT fresh edge.** pullback-entry- SHORT 6T 83.3%WR +$0.98 in EXTREME. 7d EXTREME: 60T 55%WR +$2.29. — 2026-09-19
2. **DEVELOP: New signals for NEUTRAL regime.** Only pump-chain+ LONG passes confluence. Need diversity. — 2026-09-16
3. **INVESTIGATE: rr_engine_support_br 30% WR (10T -$0.73).** Consider widening support_br threshold. — 2026-09-17
4. **INFRA: signal_reason NULL in trades table.** All trades have NULL signal_reason. Low priority. — 2026-09-17
5. **DISK: 84% (19G free).** Below 88% threshold. Monitor. — 2026-09-21
