# Current State — System Improvement Focus

**Last Updated: 2026-09-21 ~06:30 UTC (daily_orchestrator)**
**Updated by: daily_orchestrator (DB-verified)**

## Current Status

24h: 26T, 50% WR, +$0.94. 3 open. Market NEUTRAL. Pipeline running.

- **24h (rolling):** 26T, 50% WR, +$0.94. pump-chain+ LONG 12T 58.3%WR +$1.01 (carrying). pullback-entry- SHORT 8T 50%WR +$0.10.
- **Today (calendar):** 11T closed, 2W 18.2% WR, -$0.70 (rough early day, normal variance).
- **7d:** 203T, 48.8% WR, +$1.21 (DB-verified). POSITIVE.
- **Market:** NEUTRAL (3 open trades).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **TIME_BLOCK:** 01-09 UTC (extended Sep 20). 0.7x penalty.
- **KILLED/REGIME BLOCKED:** grind-trend+ (Sep 19), grind-trend- (Sep 19), open-skies+ (Sep 17), breakout-long (Sep 17), trend_ignition (Sep 16), breakout-long+ (Sep 16), rr-struct-v2+ (Sep 15), pump-chain+ NORMAL (Sep 15), rr-struct- (Sep 14), pump-chain+ NEVER_REENABLE, trend_purity+ (Sep 13), accel-300-v4-short- (Sep 11), PUMP_FLOW+ NEVER_REENABLE, pullback_entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE.
- **CONF_FILTER_MIN=70.**
- **Disk:** 84% (19G free). Below 90% threshold.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%.
- **SHORT_RSI_FLOOR=30:** Working. RSI<30 SHORTs = 37.5%WR blocked.
- **SHORT_RSI_CEILING=65:** Working. Blocking high-RSI SHORTs.

**🟢 R:R STATUS (7d +$1.21 POSITIVE, 24h +$0.94)**
7d PnL +$1.21. EXTREME carries (+$2.29). NORMAL bleeds (-$1.27). 24h +$0.94.

**🟢 STALE FILTER — WORKING.** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). Filter reducing stale by 89%. — 2026-09-19

**🟢 CHASE FILTER — WORKING.** 58 blocks verified. — 2026-09-19

**🟢 UPGRADE AUDIT (Sep 21):** All Level 1 tasks complete. 5 changes implemented by upgrade_implementer: CHOP_GATE_LOG_ONLY→False, Momentum NORMAL 0.0x, deprecated constants removed, OPEN_SKIES removed from never-reenable, ZSCORE_PUMP_ENABLED→False. All verified live.

**🔴 SIGNAL DIVERSITY:** Only pump-chain+ LONG passes confluence in NEUTRAL. EXTREME edge confirmed (55%WR +$2.29/7d). NORMAL bleeds (-$1.27/7d). Need new signals for diversity. 30d active: 6 types.

**🔴 HOTSET EMPTY:** signal-compactor outputs 0 tokens (blocked by confluence gate + NEUTRAL block). Pipeline trades via other paths.

## Today's Changes (Sep 21)

1. **upgrade_implementer ~06:30 UTC — 5 LEVEL 1 CHANGES IMPLEMENTED.** (1) CHOP_GATE_LOG_ONLY→False — activates BTC chop gate. (2) Momentum NORMAL 0.0x — blocks momentum LONG in NORMAL (38.5%WR -$0.99/7d). (3) Deleted 6 deprecated constants (LOSS_MIN/MAX_PCT, CUT_LOSER_MAX_CLOSE, SKIP_BOTTOM_PCT, CUT_LOSER_FIRE_WINDOWS, BTC_CRASH_BLOCK_THRESHOLD). (4) Removed OPEN_SKIES from NEVER_REENABLE_FLAGS (CEO re-enabled for testing). (5) ZSCORE_PUMP_ENABLED→False (fixed True contradiction). All verified live.
1. **daily_orchestrator ~06:30 UTC — NO CONFIG CHANGE.** DB-verified: 24h 26T 50%WR +$0.94 | 7d 203T 48.8%WR +$1.21. Market NEUTRAL. 3 open. pump-chain+ LONG carrying (+$1.01/24h). Today rough (11T 18.2%WR -$0.70) but early. **No critical issues. All upgrade audit changes verified. System healthy.**

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
