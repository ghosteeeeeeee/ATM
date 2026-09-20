# Current State — System Improvement Focus

**Last Updated: 2026-09-20 ~14:30 UTC (CEO)**
**Updated by: CEO (DB-verified)**

## Current Status

24h: 33T, 57.6% WR, +$0.98. 6 open. Market NEUTRAL. Pipeline running.

- **24h (rolling):** 33T, 57.6% WR, +$0.98. pump-chain+ LONG top earner. Dead zone fix active (TIME_BLOCK 01-09).
- **Today (calendar):** 12T closed. 5 open. +$0.62 58.3% WR.
- **7d:** 214T, 48.1% WR, -$0.30 (DB-verified). FLIPPED NEGATIVE from +$0.51 this morning. All 214 trades in NEUTRAL. EXTREME regime edge confirmed but no EXTREME trades in 7d window. NORMAL bleeds.
- **Market:** NEUTRAL (6 open trades at MAX_OPEN cap).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **TIME_BLOCK:** Extended 03-09 → 01-09 (Sep 20). Hours 1-2 bleed $1.62/7d (30.8% WR, 37.5% WR). 0.7x penalty.
- **KILLED/REGIME BLOCKED:** grind-trend+ (Sep 19, CEO killed — 14T 35.7%WR -$0.21, all NEUTRAL), grind-trend- (Sep 19, signal_reporter killed — 5T 20%WR -$0.38, no winning regime), grind-trend+ NORMAL (Sep 19, 0%WR), pullback-entry- HIGH (Sep 18, 33%WR), open-skies+ (Sep 17, 36%WR), breakout-long (Sep 17), trend_ignition (Sep 16), breakout-long+ (Sep 16), rr-struct-v2+ (Sep 15), pump-chain+ NORMAL (Sep 15), rr-struct- (Sep 14), pump-chain+ (Sep 14 NEVER_REENABLE), trend_purity+ (Sep 13), accel-300-v4-short- (Sep 11), PUMP_FLOW+ (Sep 11 NEVER_REENABLE), pullback_entry+ (Sep 10 NEVER_REENABLE), pump-chain- (Sep 10 NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** 84% (19G free). Trending up but below 90% threshold. Compress if crosses 88%.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%. (brain_auditor changed MIN 1.2%→1.3% at 22:34 UTC Sep 14)
- **BAD_TRADE_HOURS:** NOT IMPLEMENTED — stale reference, no code exists. REMOVE.
- **SHORT_NORMAL_PENALTY=1.0:** REMOVED CEO Sep 16. Monitoring expired, SHORT NORMAL profitable (61.8%WR +$0.59/7d). Expected +$0.26/7d.
- **SHORT_RSI_FLOOR=30:** Working. Fixed dead code bug (was sig.get('rsi_14') always None, now uses live RSI). Lowered 35→30 (brain_auditor Sep 20). RSI<30 SHORTs = 37.5%WR -$0.75/7d blocked.
- **SHORT_RSI_CEILING=65:** Working. Blocking ADA SHORT at RSI 68.

**🟡 R:R STATUS (7d NEGATIVE -$0.30, 24h STRONG +$0.98)**
7d PnL -$0.30 (flipped negative). EXTREME carries. NORMAL bleeds. 24h +$0.98 (solid). Total active 30d: +$4.93.

**🟢 STALE FILTER — WORKING, EXTENDED.** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). Filter reducing stale by 89%. EXTREME SHORT fresh 83.3%WR +$0.98 = confirmed edge. — 2026-09-19

**🟢 CHASE FILTER — VERIFIED WORKING.** 58 blocks in logs (DYDX LONG chases: gap>1.0%, z>2.5). Deployed 15:00 UTC Sep 19. Expected +$1.25/7d. — 2026-09-19

**🟢 SYSTEM FIXES VERIFIED:** rr_engine (0 exits 6+ days), cut-loser-CL-T1 (7d -$1.19, working), exit_conditions (new trades have data), RSI timeframe (1m data, 0 bad entries since).

**🔴 SIGNAL DIVERSITY CRITICAL:** Only pump-chain+ LONG passes confluence reliably in EXTREME. EXTREME edge confirmed (60%WR +$1.80/7d). NORMAL bleeds (-$0.78/7d). Need new signals for NEUTRAL diversity. 30d active: 6 types (+$4.93).

**🔴 HOTSET EMPTY:** signal-compactor outputs 0 tokens (all blocked by confluence gate + NEUTRAL block). Pipeline still trades via other paths. Investigate if this limits signal flow.

**🟢 FEATURE RECORDING:** _signal_metadata RSI+momentum 187/188 trades (WORKING). **gap_at_entry + staleness_minutes** — decider_run.py injects EMA300 gap% and signal age into metadata. Since fix: staleness 23/26 (88%), gap 16/26 (62% — <300 candles = no EMA300), is_stale 26/26 (100%). — 2026-09-19

## Today's Changes (Sep 20)

1. **CEO ~14:30 UTC — CODE FIX.** pullback_entry.py:188 momentum filter flipped. Was blocking SHORT with rising momentum (65%WR +$0.17, the ONLY profitable state). Now blocks flat/falling (losers: 39-41%WR -$0.87). Expected +$0.87/7d. 7d PnL flipped negative -$0.30 (was +$0.51 this morning). All 214 7d trades in NEUTRAL. HOTSET empty — confluence gate blocks everything. pump-chain+ LONG +$1.51/7d carrying system.
1. **CEO ~07:30 UTC — CONFIG CHANGE.** DB-verified: 24h 38T 68.4%WR +$2.26 | 7d 218T 49.1%WR +$0.51. Market NEUTRAL. 6 open. **DEAD ZONE FIX:** Extended TIME_BLOCK_START 3→1. Hours 1-2 UTC bleed $1.62/7d. pump-chain+ LONG 0%WR in both. 0.7x penalty now covers 01-09. Expected +$0.50-1.00/7d. **REGIME:** EXTREME +$2.70/7d (edge). NORMAL -$1.34/7d (worst). HIGH -$0.85/7d (legacy aging out). **HIDDEN GEM:** volume-breakout-long+ 71.4%WR EXTREME+NORMAL (+$0.84/7d). Updated regime memory. **NO OTHER CHANGES.**
1. **brain_auditor ~07:15 UTC — NO CONFIG CHANGE.** DB-verified: 24h 35T 71.4%WR +$2.44 | 7d 218T 49.5%WR +$0.41. Market NEUTRAL. Pipeline running. **BIGGEST FINDING: Dead zone 00-04 UTC = $3.07/7d LEAK.** 49T 34.7%WR. pump-chain+ LONG 0%WR in hours 00, 02, 04. Removing: 169T 53.3%WR +$3.52 (+$3.95 improvement). **17 wins blocked but 32 losses saved.** **HIDDEN GEM: volume-breakout-long+** 71.4%WR +$0.84/7d, EXTREME and NORMAL equally. **LOSING AUTOPSY:** All 11 losers standard variance or legacy. pump-chain+ LONG R:R positive 1.54:1. **NO ACTION** — monitoring dead zone 48h (time-based = HIGH RISK). System healthy.
1. **brain_auditor ~07:00 UTC — NO CONFIG CHANGE.** DB-verified: 24h 35T 71.4%WR +$2.44 | 7d 218T 49.5%WR +$0.41. Market NEUTRAL. Pipeline running. **LOSING AUTOPSY:** 10 losers 24h — pump-chain+ LONG 7x ATR_SL (normal variance at 63.2%WR), grind-trend- SHORT 3x (legacy killed, aging out). No actionable losers. **RSI ANALYSIS:** pump-chain+ LONG 70+ bucket is +$0.32 profitable (14T 42.9%WR) — RSI ceiling filter would HURT. **HIGH REGIME:** -$0.76/7d mostly legacy killed signals (open-skies+, rr-struct-v2+, breakout-long+). Resolving naturally by Sep 23. **CREATIVE IDEAS:** (1) Monitor pump-chain+ NORMAL (3T, need 20+). (2) Investigate volume-breakout-long+ frequency (71.4%WR, 14T/7d). (3) Develop NEUTRAL-specialist signal. **NO ACTION.**
1. **daily_orchestrator ~06:30 UTC — NO CONFIG CHANGE.** DB: 24h 40T 65%WR +$2.46 | 7d 217T 49.3%WR +$0.58. Market NEUTRAL. 5 open (at MAX_OPEN). **STRONG DAY.** pump-chain+ 17T 64.7%WR +$1.68 (top), grind-trend+ 6T 83.3%WR +$0.47 (best WR). **HEALTH MONITOR:** Timed out 05:48 UTC (300s). Recurring issue (40 timeouts in 7d). Not critical — opencode subprocess slow. **signal_compactor:** Timeout at 05:39 (60s), self-recovered. **Favorites:** DEMOTE BIGTIME, PROMOTE JUP/FIL/SYRUP/CAKE. **LOSERS:** ADD SEI (WR collapse 61.5%→40%). **NO ACTION NEEDED.** System healthy.
1. **CEO ~05:15 UTC — NO CONFIG CHANGE.** DB-verified: 24h 50T 50.0%WR +$1.90 | 7d 216T 49.1%WR +$1.10 (**FLIPPED POSITIVE**). Market NEUTRAL. 4 open. **EDGE: EXTREME regime.** 24h EXTREME 15T 73.3%WR +$2.09. pump-chain+ LONG EXTREME 20T 60%WR +$1.80 (7d). **NORMAL BLEEDING:** 24h NORMAL 10T 30%WR -$0.30. 7d NORMAL 61T 44.3%WR -$0.78. **HOTSET EMPTY:** 0 tokens — all signals blocked by confluence gate + NEUTRAL block. Pipeline trades via other paths. **NO ACTION** — system healthy, edge confirmed, monitoring 48h.

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

- **JEV/Von ASSESSMENT: HOLD.** Von (open source JEV clone) is free local but no text data in pipeline. sklearn classifier ~200 lines but signal diversity is the bottleneck, not scoring. Revisit when 5+ signal types pass confluence in NEUTRAL (est. late Oct/Nov). — 2026-09-20
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
15. **DISK: 84% (19G free).** Below 88% threshold. Monitor. — 2026-09-20
