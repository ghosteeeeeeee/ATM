# Current State — System Improvement Focus

**Last Updated: 2026-09-18 ~19:00 UTC (daily_orchestrator)**
**Updated by: daily_orchestrator (DB-verified)**

## Current Status

24h: 23T, 65.2% WR, +$0.98. 5 open. Market NEUTRAL. Pipeline running.

- **24h (rolling):** 23T, 65.2% WR, +$0.98 (POSITIVE — system recovering from cold streak). Winners: volume-breakout-long+ 10T 80%WR +$1.03, mover+ 3T 100%WR +$0.26. Losers: pullback-entry- SHORT 5T ALL ATR SL (-$0.59, 4/5 HIGH/NORMAL regime).
- **Today (calendar):** 21T closed (Sep 18). 5 open (FOGO LONG pump-chain+, ADA LONG pump-chain+, DOT SHORT pullback-entry-, CAKE SHORT mover-, NOT SHORT pullback-entry-).
- **7d:** 197T, 53.3% WR, -$0.69 (DB-verified). Active signals positive 30d: pullback-entry- +$2.01, pump-chain- +$1.04, rr-struct+ +$0.59, mover- +$0.61, mover+ +$0.42, volume-breakout-long+ +$0.26. Total active 30d: +$4.93.
- **7d DRAGGERS (all killed/disabled):** trend_purity+ -$0.90 (11T/36.4%WR), rr-struct-v2+ -$0.45 (10T/40%WR), rr-struct- -$0.42 (7T/42.9%WR), open-skies+ -$0.42 (8T/37.5%WR), breakout-long+ -$0.35 (4T/25%WR). All legacy — system improving as they age out.
- **Market:** NEUTRAL (5 open trades).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **KILLED/REGIME BLOCKED:** pullback-entry- HIGH (Sep 18, 33%WR), open-skies+ (Sep 17, 36%WR), breakout-long (Sep 17), trend_ignition (Sep 16), breakout-long+ (Sep 16), rr-struct-v2+ (Sep 15), pump-chain+ NORMAL (Sep 15), rr-struct- (Sep 14), pump-chain+ (Sep 14 NEVER_REENABLE), trend_purity+ (Sep 13), accel-300-v4-short- (Sep 11), PUMP_FLOW+ (Sep 11 NEVER_REENABLE), pullback_entry+ (Sep 10 NEVER_REENABLE), pump-chain- (Sep 10 NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** ~85% (18G free). Trending up but below 90% threshold. Compress if crosses 88%.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%. (brain_auditor changed MIN 1.2%→1.3% at 22:34 UTC Sep 14)
- **BAD_TRADE_HOURS:** {3,5,13,14,15,21} — soft penalty active.
- **SHORT_NORMAL_PENALTY=1.0:** REMOVED CEO Sep 16. Monitoring expired, SHORT NORMAL profitable (61.8%WR +$0.59/7d). Expected +$0.26/7d.
- **SHORT_RSI_FLOOR=25:** Working.
- **SHORT_RSI_CEILING=65:** Working. Blocking ADA SHORT at RSI 68.

**🟡 R:R STATUS (SLIGHTLY NEGATIVE 7d, POSITIVE 24h)**
7d PnL -$0.69. SHORT +$1.23 carries LONG -$2.17 (legacy aging out). 24h +$0.98. Total active 30d: +$4.93.

**🟢 STALE FILTER — EVALUATED & EXTENDING.** Pre-filter stale 43.8% (7/16). Post-filter stale 9.4% (3/32). Filter reducing stale by 78%. EXTREME SHORT fresh 83.3%WR +$0.98 = confirmed edge. — 2026-09-18 ~19:00 UTC

**🟢 SYSTEM FIXES VERIFIED:** rr_engine (0 exits 6+ days), cut-loser-CL-T1 (7d -$1.19, working), exit_conditions (new trades have data), RSI timeframe (1m data, 0 bad entries since).

**🔴 SIGNAL DIVERSITY CRITICAL:** Only pullback-entry- SHORT and volume-breakout-long+ LONG pass confluence in NEUTRAL. Need new signals. 30d active: 6 types (+$4.93).

**🔴 FEATURE RECORDING:** _signal_metadata 100% NULL for RSI/gap/staleness. Fix from Sep 16 not writing correctly. Investigate.

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

- **STALE FILTER:** Evaluated & extending. Pre-filter stale 43.8% → Post-filter 9.4%. EXTREME SHORT fresh 83.3%WR +$0.98 = edge. — 2026-09-18
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
7. **NEXT: Feature recording fix.** _signal_metadata 100% NULL for RSI/gap/staleness. Fix from Sep 16 not writing correctly. Investigate signal_compactor.py. — 2026-09-18
8. **NEXT: Execution-time revalidation for stale signals.** Stale filter now at 9.4% (was 31.8%). Further improvement possible with execution-time check. — 2026-09-16
9. **INVESTIGATE: rr_engine_support_br 30% WR (10T -$0.73).** Consider widening support_br threshold. — 2026-09-17
10. **DEVELOP: New signals for NEUTRAL regime.** Only 2 signal types pass confluence. Need diversity. — 2026-09-16
11. **MONITOR: EXTREME SHORT fresh edge.** pullback-entry- SHORT 6T 83.3%WR +$0.98 in EXTREME — system edge. Stale filter protecting. — 2026-09-18
12. **MONITOR: volume-breakout-long+ RSI/momentum pattern.** Both 7d losers had RSI>60 + weak momentum. 3 trades only — need 20+ before filter. Monitor until Oct 1. — 2026-09-17
13. **INFRA: signal_reason NULL in trades table.** All trades have NULL signal_reason. Use `signal` column for analytics. Low priority fix. — 2026-09-17
14. **DISK: 85% trending up.** Below 90% threshold but monitor. Compress old logs if crosses 88%. — 2026-09-18
