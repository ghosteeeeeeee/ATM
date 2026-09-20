# Current State — System Improvement Focus

**Last Updated: 2026-09-20 ~05:00 UTC (brain_auditor)**
**Updated by: brain_auditor (DB-verified)**

## Current Status

24h: 50T, 44.0% WR, +$0.38. 4 open. Market NEUTRAL. Pipeline running.

- **24h (rolling):** 50T, 44.0% WR, +$0.38. pump-chain+ LONG 19T 47.4%WR +$0.62, grind-trend+ LONG 18T 50.0%WR +$0.24 (disabled). Losers: pump-chain+ LONG 8T -$1.18 (biggest), grind-trend+ LONG 8T -$0.54 (disabled), grind-trend- SHORT 4T -$0.40 (disabled).
- **Today (calendar):** 50T closed (Sep 20). 4 open.
- **7d:** 212T, 48.6% WR, -$0.16 (DB-verified). **SLIGHTLY NEGATIVE.** EXTREME regime best (57.1%WR +$1.81). pump-chain+ LONG EXTREME 18T 61.1%WR +$1.11. Legacy killed signals aging out in 7d data.
- **Market:** NEUTRAL (4 open trades).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **KILLED/REGIME BLOCKED:** grind-trend+ (Sep 19, CEO killed — 14T 35.7%WR -$0.21, all NEUTRAL), grind-trend- (Sep 19, signal_reporter killed — 5T 20%WR -$0.38, no winning regime), grind-trend+ NORMAL (Sep 19, 0%WR), pullback-entry- HIGH (Sep 18, 33%WR), open-skies+ (Sep 17, 36%WR), breakout-long (Sep 17), trend_ignition (Sep 16), breakout-long+ (Sep 16), rr-struct-v2+ (Sep 15), pump-chain+ NORMAL (Sep 15), rr-struct- (Sep 14), pump-chain+ (Sep 14 NEVER_REENABLE), trend_purity+ (Sep 13), accel-300-v4-short- (Sep 11), PUMP_FLOW+ (Sep 11 NEVER_REENABLE), pullback_entry+ (Sep 10 NEVER_REENABLE), pump-chain- (Sep 10 NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** 84% (19G free). Trending up but below 90% threshold. Compress if crosses 88%.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%. (brain_auditor changed MIN 1.2%→1.3% at 22:34 UTC Sep 14)
- **BAD_TRADE_HOURS:** NOT IMPLEMENTED — stale reference, no code exists. REMOVE.
- **SHORT_NORMAL_PENALTY=1.0:** REMOVED CEO Sep 16. Monitoring expired, SHORT NORMAL profitable (61.8%WR +$0.59/7d). Expected +$0.26/7d.
- **SHORT_RSI_FLOOR=25:** Working.
- **SHORT_RSI_CEILING=65:** Working. Blocking ADA SHORT at RSI 68.

**🟢 R:R STATUS (7d SLIGHTLY NEGATIVE, 24h POSITIVE)**
7d PnL -$0.16. SHORT +$0.20 carries LONG +$0.24. 24h +$0.38. Total active 30d: +$4.93.

**🟢 STALE FILTER — WORKING, EXTENDED.** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). Filter reducing stale by 89%. EXTREME SHORT fresh 83.3%WR +$0.98 = confirmed edge. — 2026-09-19

**🟢 CHASE FILTER — VERIFIED WORKING.** 58 blocks in logs (DYDX LONG chases: gap>1.0%, z>2.5). Deployed 15:00 UTC Sep 19. Expected +$1.25/7d. — 2026-09-19

**🟢 SYSTEM FIXES VERIFIED:** rr_engine (0 exits 6+ days), cut-loser-CL-T1 (7d -$1.19, working), exit_conditions (new trades have data), RSI timeframe (1m data, 0 bad entries since).

**🔴 SIGNAL DIVERSITY CRITICAL:** Only pump-chain+ LONG and volume-breakout-long+ LONG pass confluence reliably. rr-struct+ LONG 66.7%WR +$0.52 also strong. pullback-entry- SHORT 49.2%WR -$0.19 nearly breakeven. Need new signals for NEUTRAL diversity. 30d active: 6 types (+$4.93).

**🟢 FEATURE RECORDING:** _signal_metadata RSI+momentum 187/188 trades (WORKING). **gap_at_entry + staleness_minutes** — decider_run.py injects EMA300 gap% and signal age into metadata. Since fix: staleness 23/26 (88%), gap 16/26 (62% — <300 candles = no EMA300), is_stale 26/26 (100%). — 2026-09-19

## Today's Changes (Sep 20)

1. **brain_auditor ~05:00 UTC — NO CONFIG CHANGE.** DB-verified: 24h 50T 44.0%WR +$0.38 | 7d 212T 48.6%WR -$0.16. Market NEUTRAL. 4 open. **LOSING AUTOPSY (22):** pump-chain+ LONG 8T -$1.18 (biggest loser). grind-trend+ LONG 8T -$0.54 (disabled signal). grind-trend- SHORT 4T -$0.40 (disabled signal). **TIME PATTERN:** pump-chain+ LONG hours 0,2,4 UTC: 10T 0%WR -$1.27. Pattern clear but sample small (needs 20+). **REGIME (7d):** EXTREME best. pump-chain+ LONG EXTREME 18T 61.1%WR +$1.11. pullback-entry- SHORT EXTREME 13T 53.8%WR +$0.27. **CREATIVE:** (1) Monitor pump-chain+ LONG hour 0,2,4 pattern (2) Evaluate pullback-entry- SHORT NORMAL regime penalty (3) Volume filter for pump-chain+ LONG EXTREME. **NO ACTION** — all items need more data. Monitor 48h.

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

- **CHASE FILTER ACTIVE.** CHASE_FILTER_ENABLED=True, CHASE_ZSCORE_MAX=2.5, CHASE_GAP_MAX_PCT=1.0. Blocks LONG chasing. Pipeline restart needed. **EXPECTED:** +$1.25/7d. — 2026-09-19
- **STALE FILTER:** Working. 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). EXTREME SHORT fresh 83.3%WR +$0.98 = edge. — 2026-09-19
- **grind-trend+ NORMAL BLOCKED.** signal_reporter 05:12 UTC Sep 19. 0%WR (5T). Wins HIGH 57.1%. — 2026-09-19
- **pullback-entry- HIGH BLOCKED.** signal_reporter 17:09 UTC Sep 18. 33%WR. Wins only EXTREME (65% WR). — 2026-09-18
- **RSI BUG FIXED.** signal_compactor.py:2728 candles_5m→1m. SHORT_RSI_CEILING now 1m data. — 2026-09-16
- **exit_conditions FIXED.** brain.py + all callers. New trades have exit data. — 2026-09-16
- **SHORT_NORMAL_PENALTY REMOVED.** SHORT NORMAL profitable. — 2026-09-16
- **trend_ignition DISABLED.** 0 trades in 3+ days. — 2026-09-16
- **rr_engine_resistance FIX CONFIRMED.** 0 exits 6+ days. — 2026-09-16
- **LONG_NEUTRAL_BLOCK DEPLOYED.** — 2026-09-02
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected. — 2026-09-06
- **CONF_FILTER_MIN=70.** — 2026-09-02

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **DONE: RSI timeframe alignment.** signal_compactor.py:2728 changed candles_5m → candles_1m. SHORT_RSI_CEILING now uses 1m data. — 2026-09-16
2. **DONE: exit_conditions recording fix applied.** brain.py close_trade() now accepts exit_conditions param, adds to UPDATE, CLI supports --exit-conditions. — 2026-09-16
3. **DONE: Update all callers to pass --exit-conditions.** profit_monster.py, cut_loser.py, sniper_exit.py (CLI), hl_fill_monitor.py (direct). All pass exit mechanism + PnL%. — 2026-09-16 ~18:30 UTC
4. **DONE: Execution-time SHORT_RSI_CEILING revalidation.** decider_run.py safety section. Prevents RSI drift between detection and execution. — 2026-09-18
5. **DONE: Stale filter evaluation.** Pre-filter stale 43.8% (7/16). Post-filter stale 9.4% (3/32). Filter reducing stale by 78%. Extending. — 2026-09-18
6. **DONE: open-skies+ KILLED.** signal_reporter 17:11 UTC Sep 17. No regime >50% WR. Wave_phase gate no longer needed. — 2026-09-17
7. **DONE: Feature recording fix.** gap_at_entry (EMA300 gap%) and staleness_minutes (signal age) injected into _signal_metadata in decider_run.py before execute_trade(). — 2026-09-18
8. **DONE: Stale filter working.** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). Filter reducing stale by 89%. — 2026-09-19
9. **NEXT: Execution-time revalidation for stale signals.** Further improvement possible with execution-time check. — 2026-09-16
10. **INVESTIGATE: rr_engine_support_br 30% WR (10T -$0.73).** Consider widening support_br threshold. — 2026-09-17
11. **DEVELOP: New signals for NEUTRAL regime.** Only 2 signal types pass confluence. Need diversity. — 2026-09-16
12. **MONITOR: EXTREME SHORT fresh edge.** pullback-entry- SHORT 6T 83.3%WR +$0.98 in EXTREME — system edge. Stale filter protecting. 7d EXTREME: 52T 58%WR +$1.74. — 2026-09-19
13. **MONITOR: volume-breakout-long+ RSI/momentum pattern.** Both 7d losers had RSI>60 + weak momentum. 3 trades only — need 20+ before filter. Monitor until Oct 1. — 2026-09-17
14. **INFRA: signal_reason NULL in trades table.** All trades have NULL signal_reason. Use `signal` column for analytics. Low priority fix. — 2026-09-17
15. **DISK: 84% (19G free).** Below 88% threshold. Monitor. — 2026-09-19
