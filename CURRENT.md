# Current State — System Improvement Focus

**Last Updated: 2026-09-16 ~18:30 UTC (brain_auditor)**
**Updated by: brain_auditor (DB-verified)**

## Current Status

24h: 21T, 66.7% WR, +$1.33. 0 open. Market NEUTRAL. Pipeline running, no errors.

- **24h (rolling):** 21T, 66.7% WR, +$1.33 (DB-verified — POSITIVE). pullback-entry- dominant.
- **Today (calendar):** 21T closed. 0 open.
- **7d:** 255T, 55.7% WR, +$2.72 (DB-verified — POSITIVE). SHORT dominant | LONG legacy aging out.
- **7d REGIME:** EXTREME 97T 59.8%WR +$2.91★ | HIGH 107T 54.2%WR +$0.79 | NORMAL 54T 53.7%WR -$0.10.
- **7d EXIT:** profit-monster-trail carries system | rr_engine_resistance -$1.08 (7d #1 exit drag).
- **7d ACTIVE SIGNALS:** pullback-entry- SHORT 87T/59.8%WR +$3.78★ | pump-chain- SHORT 49T/61.2%WR +$1.25 | rr-struct+ LONG 15T/73.3%WR +$0.59 | mover- SHORT 7T/85.7%WR +$0.56
- **7d DRAGGERS:** trend_purity+ 11T/36.4%WR -$0.90 (KILLED) | pullback-entry+ 5T/0%WR -$0.61 (KILLED) | rr-struct-v2+ 10T/40%WR -$0.45 (KILLED) | breakout-long+ 4T/25%WR -$0.35 (KILLED)
- **Market:** NEUTRAL (100%).
- **Open:** 0 trades.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **KILLED (Sep 16 10:34):** STANDALONE_BYPASS cleanup — removed dead accel-300-v4-short, ema300-dip-long, ema300-dip-short. **KILLED (Sep 16 05:15):** trend_ignition (brain_auditor, 0 trades in 3+ days, dead signal, LONG-only impossible in NEUTRAL). **KILLED (Sep 16 02:08):** breakout-long+ (auto_1hr, 0%WR -$0.60, fires LONG in NEUTRAL without BTC gate). **KILLED (Sep 15 ~14:40):** rr-struct-v2+ (CEO, 10T/40%WR -$0.45, all ATR SL). **KILLED (Sep 15 05:10):** pump-chain+ NORMAL regime blocked (signal_reporter). **KILLED (Sep 14 22:45):** rr-struct- (CEO). **KILLED (Sep 14 16:08):** pump-chain+ (auto_1hr, NEVER_REENABLE). **KILLED (Sep 13):** trend_purity+ (auto_1hr). **KILLED (Sep 11):** accel-300-v4-short-, PUMP_FLOW+ (NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** ~81% (23G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%. (brain_auditor changed MIN 1.2%→1.3% at 22:34 UTC Sep 14)
- **BAD_TRADE_HOURS:** {3,5,13,14,15,21} — soft penalty active.
- **SHORT_NORMAL_PENALTY=1.0:** REMOVED CEO Sep 16. Monitoring expired, SHORT NORMAL profitable (61.8%WR +$0.59/7d). Expected +$0.26/7d.
- **SHORT_RSI_FLOOR=25:** Working.
- **SHORT_RSI_CEILING=65:** Working. Blocking ADA SHORT at RSI 68.

**🟢 R:R STATUS (POSITIVE 7d, FLAT 24h)**
7d PnL +$2.66 (POSITIVE). SHORT +$3.72 carries LONG -$1.06 (improving, legacy aging out). 24h -$0.17 (FLAT). System structurally healthy.

**🟢 rr_engine_resistance FIX VERIFIED.** 0 post-fix rr_engine exits in 6+ days (since Sep 10). Confirmed working. Can remove from monitoring.

**🟢 cut-loser-CL-T1 HEALTHY.** 7d: 7 exits, avg -$0.17/trade, -$1.19 total. Mechanism working as designed — fast cuts prevent larger losses.

**🟢 FEATURES RECORDING VERIFIED.** DOT and ETC closed today with features_recorded=TRUE (rsi=44.44, 40.0). IO gap confirmed: has _signal_metadata but features_recorded=FALSE (opened during fix deployment). Fix working for new trades.

**🟢 SHORT_NORMAL_PENALTY=0.85:** WORKING. 24h 6T 83.3%WR +$0.60. 7d 34T 61.8%WR +$0.59. Monitoring expired.

**🟢 pump-chain+ NORMAL BLOCK:** Signal_reporter blocked Pump_Flow from NORMAL regime. Active since 05:10 UTC Sep 15.

**🟡 SIGNAL DIVERSITY ISSUE:** Only 2 signal types pass confluence in NEUTRAL (pullback-entry-, pump-chain-). Need new signals for resilience.

**🔴 trend_ignition: DISABLED.** brain_auditor 05:15 UTC Sep 16. 0 trades in 3+ days, dead signal.

**🟢 momentum_cache.db:** Empty (0 bytes since Sep 12). Service inactive. Pipeline unaffected. Low priority.

**🟡 STALE SIGNAL EXECUTION:** 31.8% of 7d trades (81/255) fire on stale signals. Stale WR 49.4% vs fresh 59.0%. Pullback-entry- SHORT: stale 53.5%WR +$0.28 vs fresh 65.9%WR +$3.50. ~$4.86/7d lost from stale execution.

**🟢 EXIT CONDITIONS FIX COMPLETE.** position_manager.py UPDATE now includes exit_conditions. All close paths (brain.py, position_manager.py) now write exit_conditions. Old blank trades (254/255 7d) remain blank — new trades will have data. — 2026-09-16 ~18:30 UTC

**🟢 RSI TIMEFRAME MISMATCH FIXED.** SHORT_RSI_CEILING now uses 1m data (signal_compactor.py:2728). ETC SHORT RSI=70.14 would have been blocked. — 2026-09-16 ~15:45 UTC

## Today's Changes (Sep 16)

1. **brain_auditor ~18:30 UTC — 1 CODE FIX APPLIED.** exit_conditions recording COMPLETED: position_manager.py line 1089 UPDATE now includes exit_conditions = reason. Root cause: position_manager closes 150/255 7d trades (ATR SL/trail) via direct UPDATE bypassing brain.py. Previous brain.py fix only covered profit_monster/cut_loser path. DB: 24h 21T 66.7%WR +$1.33 (POSITIVE). 7d: 255T 55.7%WR +$2.72 (POSITIVE). 0 open. Market NEUTRAL. **LOSING AUTOPSY:** 7 losers — 5x pullback-entry- SHORT (4 stale, 1 fresh variance), 2x breakout-long+ (killed). ETH SHORT RSI 25.91 pre-fix (5m filter bug). **STALE:** 81/255 7d trades 31.8%. Stale WR 49.4% vs fresh 59.0%. ~$4.86/7d. **CREATIVE:** STALE_MAX_AGE_MINUTES filter — skip signals >30min. Needs backtest. **NO CONFIG CHANGE.**
2. **daily_orchestrator ~18:30 UTC — 4 CODE FIXES APPLIED.** exit_conditions recording COMPLETED: profit_monster.py, cut_loser.py, sniper_exit.py now pass --exit-conditions to brain.py CLI. hl_fill_monitor.py passes exit_conditions= kwarg directly. All 4 callers pass exit mechanism + PnL%. New trades will have exit_conditions populated. DB: 22T 58%WR +5.11% (GOOD DAY). 0 open. Market NEUTRAL. **NO CONFIG CHANGE** — code fix only. Next: stale signal revalidation, resistance proximity filter.
2. **brain_auditor ~17:00 UTC — NO CONFIG CHANGE.** DB: 24h 18T 55.6%WR +$0.15 (FLAT). 7d: 259T 55.6%WR +$2.67 (POSITIVE). **LOSING AUTOPSY:** 6 losers — ETH SHORT RSI=71.61 (pre-fix trade), DOT SHORT RSI=64.22 (borderline EXTREME whipsaw), ETC SHORT RSI=70.14 (BUG FIXED), 3x breakout-long+ (killed). **DRIFT:** exit_conditions brain.py fix applied but profit_monster/cut_loser NOT yet passing --exit-conditions (258/259 7d trades blank). **STALE SIGNAL:** 80 stale 50%WR -$0.64 vs 179 fresh 58.1%WR +$3.31. Gap ~$3.95/7d. **CREATIVE:** Tighten SHORT_RSI_CEILING 65→60: safe (1 trade blocked, 0 winners) but sample too small — monitor. Stale revalidation needs design.
1. **brain_auditor ~15:45 UTC — 1 CODE FIX APPLIED.** RSI timeframe alignment FIXED: signal_compactor.py:2728 changed candles_5m → candles_1m. SHORT_RSI_CEILING now uses 1m data (matches entry_rsi_14). ETC SHORT RSI=70.14 would have been blocked. DB: 24h 17T 52.9%WR +$0.45 (FLAT). 7d: 264T 55.7%WR +$2.23 (POSITIVE). **LOSING AUTOPSY:** 6 24h losers — 3x pullback-entry- SHORT (ATR SL), 3x breakout-long+ (killed). rr_engine_resistance 36T/7d -$1.31 — #1 exit drag. **CREATIVE:** Resistance proximity filter for SHORT entries (~$0.50-0.72/7d potential). **exit_conditions** partially fixed — brain.py accepts param, callers not yet updated. **Stale signal 31.2%** — stale WR 49.4% vs fresh 58.1%.
1. **brain_auditor ~15:00 UTC — 1 CODE FIX APPLIED.** exit_conditions recording FIXED: brain.py close_trade() now accepts exit_conditions param, adds to UPDATE statement, and CLI parser supports --exit-conditions. Callers (profit_monster, cut_loser) not yet updated — next step. DB: 24h 24T 57.7%WR +$0.55 (FLAT). 7d: 268T 55.8%WR +$3.73 (POSITIVE). **NEW FINDING: rr_engine_resistance SHORT exits 36T/7d -$1.31.** All losses ~1% (near ATR boundary). Pattern: SHORT enters near resistance, price drifts up, rr_engine cuts. **CREATIVE:** Resistance proximity filter for SHORT entries — skip if price within 1.0% of nearest resistance. Needs data verification. **Stale signal 31.2%** — stale WR 49.4% vs fresh 58.1%.
2. **brain_auditor ~14:00 UTC — 1 CODE FIX APPLIED.** RSI timeframe mismatch FIXED: signal_compactor.py:2728 changed candles_5m → candles_1m. SHORT_RSI_CEILING now uses 1m data. DB: 24h 26T 57.7%WR +$0.55 (FLAT). 7d: 269T 55.8%WR +$3.73 (POSITIVE). **LOSING AUTOPSY:** ETC SHORT RSI=70.14 (BUG FIXED), DOT SHORT stale, 3x breakout-long+ (killed). **exit_conditions 99.96% blank** — CODE FIX NEEDED. **Stale signal 31.2%** — stale WR 49.4% vs fresh 58.1%.
2. **brain_auditor ~13:00 UTC — NO CONFIG CHANGE.** DB: 24h 25T 64%WR +$0.05 (FLAT). 7d: 267T 55.4%WR +$1.32 (POSITIVE). **RSI BUG CONFIRMED:** SHORT_RSI_CEILING uses candles_5m (signal_compactor.py:2728) but entry_rsi_14 stores 1m RSI. ETC SHORT entered RSI=70.14 (>65) but passed 5m filter. Fix: change to candles_1m. **exit_conditions BUG CONFIRMED:** brain.py close_trade() UPDATE at line 909 never sets exit_conditions — root cause is UPDATE statement missing the column. Fix: add param + column. **Stale signal 30.7%** — fresh WR 58.2% vs stale 50.0%. **LOSING AUTOPSY:** ETC SHORT RSI=70.14 (filter mismatch), DOT SHORT RSI=64.22 (borderline, stale), 3x breakout-long+ (killed), SOL LONG rr-struct-v2+ (killed). **CREATIVE:** (1) Align SHORT_RSI_CEILING to 1m data. (2) Add exit_conditions tracking. (3) Execution-time revalidation for stale signals.
2. **brain_auditor ~12:15 UTC — NO CONFIG CHANGE.** DB: 24h 25T 64%WR +$0.05 (FLAT). 7d: 267T 55.4%WR +$1.32 (POSITIVE). **RSI TIMEFRAME MISMATCH:** SHORT_RSI_CEILING uses5m candles but entry_rsi uses1m data. ETC SHORT entered RSI=70.14 (>65) but passed filter. **exit_conditions 99.96% empty** — 266/267 trades. **Stale signal 30.7%** — stale WR 50.0% vs fresh 58.2%. **LOSING AUTOPSY:** DOT SHORT RSI=64.22 (borderline), ETC SHORT RSI=70.14 (>65 ceiling, filter mismatch), 3x breakout-long+ (killed). **CREATIVE:** (1) Align RSI filter to 1m data. (2) Add exit_conditions tracking. (3) Volume confirmation for pullback-entry-. No config change — all code-level fixes.
3. **CEO ~10:34 UTC — CONFIG CHANGE.** STANDALONE_BYPASS cleanup + regime memory update. Pipeline restarted.
3. **brain_auditor ~09:00 UTC — NO CONFIG CHANGE.** STALE SIGNAL ROOT CAUSE found. EXIT_CONDITIONS 99% blank. No config change.
3. **CEO ~08:30 UTC — CONFIG CHANGE.** SHORT_NORMAL_PENALTY removed (0.85→1.0). Monitoring expired. SHORT NORMAL 7d: 34T 61.8%WR +$0.59 (profitable). Penalty was blocking good entries. Expected +$0.26/7d. **24h:** 27T 48.1%WR -$0.52 (FLAT). **7d:** 275T 54.9%WR +$2.66 (POSITIVE). 5 open SHORT. Market NEUTRAL. Monitoring 5 items.
4. **brain_auditor ~06:00 UTC — NO CONFIG CHANGE.** DB: 24h 27T 51.9%WR -$0.17 (FLAT). 7d: 275T 54.9%WR +$2.66 (POSITIVE). SHORT +$3.72★. **FEATURE RECORDING UNTESTED** — 2/27 24h trades have features (retroactive only). 0 new trades since fix (02:34 UTC). Monitor next trade. **rr_engine_resistance VERIFIED** — 0 exits 24h+. **LOSING TRADE AUTOPSY:** DOT SHORT RSI 64.22, ETC SHORT RSI 70.14 (above SHORT_RSI_CEILING=65). ETC possible filter gap. **NO CONFIG CHANGE** — monitoring 5 items.
5. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 27T 48.1%WR -$0.52. 5 open SHORT. Market NEUTRAL. **Feature recording VERIFIED** — DOT, ETC closed with features_recorded=TRUE. IO gap confirmed (deployment timing). **rr_engine fix CONFIRMED** — 0 exits in 6+ days. **NEW: 54% stale signal execution** (is_stale=true in metadata). **NEW: exit_conditions blank** on all trades. **NO CONFIG CHANGE** — monitoring stale filter need, exit recording, signal diversity.
6. **brain_auditor ~05:15 UTC — CONFIG CHANGE.** DISABLED trend_ignition (TREND_IGNITION_ENABLED=False, TREND_IGNITION_PLUS_ENABLED=False). 0 trades in 3+ days, dead signal, LONG-only impossible in NEUTRAL.
7. **brain_auditor ~02:45 UTC — NO CONFIG CHANGE.** FEATURE RECORDING VERIFIED: 5 open trades retroactively recorded (rsi=71.61, 85.17, 70.14, 60.47, 64.22). No new trades since fix — verify next 24h. **trend_ignition DEAD:** 0 trades in 3+ days, recommend disable. **ATR SL below-entry 59.4%** (structural, pullback-entry- 71% but profitable). **SIGNAL DIVERSITY:** Only 2 types in NEUTRAL. **NO CONFIG CHANGE** — monitoring.
8. **auto_1hr ~02:08 UTC — KILLED breakout-long+.** 3T/7d 0%WR -$0.60. Fires LONG in NEUTRAL without BTC regime gate. Removed from active signals.
9. **CEO ~02:15 UTC — NO CONFIG CHANGE.** DB: 24h 29T 51.7%WR -$0.10 (FLAT). 7d: 278T 55.8%WR +$3.08 (POSITIVE, improved from +$1.83). Market NEUTRAL. **NEW FINDING: cut-loser-CL-T1 bleed** 7 exits -$1.19. **Signal diversity issue:** Only 2 signal types in NEUTRAL. 5 items in monitoring.

## Today's Changes (Sep 15)

1. **signal_reporter ~05:10 UTC — REGIME BLOCK.** Added 'Pump_Flow': 0.0 to VOL_PHASE_MULTS[('NORMAL', '*')] in volatility_gate_v2.py:249. pump-chain+ LONG 0%WR -$0.44 in NORMAL (3T). Wins in EXTREME (46.7%WR +$0.22). Preserves EXTREME/HIGH access while blocking NORMAL losses.
2. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 37T 48.6%WR -$0.66. 7d: 302T 53.0%WR -$0.23. Market NEUTRAL. **LOSING TRADE AUTOPSY:** All losses legacy flushing or normal variance. **No config change — 4 items in monitoring.**
3. **CEO ~10:00 UTC — NO CONFIG CHANGE.** DB: 24h 31T 54.8%WR +$0.10. 7d: 290T 53.1%WR +$0.29. Market NEUTRAL. **No config change — system positive, 4 items in monitoring.**
4. **brain_auditor ~11:50 UTC — CONFIG CHANGE.** BB DEAD ZONE FILTER DEPLOYED. SHORT_BB_DEAD_ZONE_MIN=0.70, SHORT_BB_DEAD_ZONE_MAX=0.85. Expected +$0.52/7d.
5. **CEO ~14:40 UTC — CONFIG CHANGE.** DB: 24h 29T 44.8%WR -$0.59. 7d: 284T 53.5%WR +$1.05. **KILLED rr-struct-v2+ LONG.** 10T/7d 40%WR -$0.45. All exits ATR SL/MAE-GUARD — poor LONG entries in NEUTRAL. Removed from STANDALONE_BYPASS. Pipeline restarted.
6. **CEO ~22:45 UTC — NO CONFIG CHANGE.** DB: 24h 31T 51.6%WR +$0.06. 7d: 280T 53.9%WR +$1.83. System structurally healthy. Legacy LONG drag aging out. No action needed.

## Active Decisions

- **RSI BUG FIXED.** brain_auditor 15:45 UTC Sep 16. signal_compactor.py:2728 changed candles_5m → candles_1m. SHORT_RSI_CEILING now uses 1m data (matches entry_rsi_14). ETC SHORT (RSI=70.14) would have been blocked. — 2026-09-16
- **exit_conditions recording FIXED.** brain.py accepts exit_conditions param + CLI. All callers updated (profit_monster, cut_loser, sniper_exit, hl_fill_monitor). New trades will have exit data. — 2026-09-16 ~18:30 UTC
- **STALE SIGNAL EXECUTION ROOT CAUSE FOUND.** brain_auditor 09:00 UTC Sep 16. 30.7% of trades fire on stale signals. Fresh WR 58.2% vs stale 50.0%. ~$3.85/7d lost. — 2026-09-16
- **SHORT_NORMAL_PENALTY REMOVED.** CEO 08:30 UTC Sep 16. Monitoring expired. SHORT NORMAL profitable. — 2026-09-16
- **trend_ignition DISABLED.** brain_auditor 05:15 UTC Sep 16. 0 trades in 3+ days, dead signal. — 2026-09-16
- **Feature recording fix VERIFIED.** DOT, ETC closed with features_recorded=TRUE. IO gap is deployment timing. — 2026-09-16 ~06:35 UTC
- **R:R POSITIVE (7d, improving).** 7d PnL +$2.66 (POSITIVE). SHORT +$3.72 carries LONG -$1.06 (improving, legacy aging out). — 2026-09-16 ~05:15 UTC
- **rr_engine_resistance FIX CONFIRMED.** 0 post-fix exits in 6+ days. No longer needs monitoring. — 2026-09-16 ~06:35 UTC
- **cut-loser-CL-T1 HEALTHY.** 7d 7 exits -$1.19, avg -$0.17. Mechanism working as designed. — 2026-09-16 ~05:15 UTC
- **breakout-long+ KILLED.** auto_1hr 02:08 UTC Sep 16. 0%WR -$0.60. — 2026-09-16
- **rr-struct-v2+ KILLED.** CEO 14:40 UTC Sep 15. 10T/40%WR -$0.45, all ATR SL. — 2026-09-15
- **SHORT BB DEAD ZONE (0.70-0.85).** DEPLOYED. 0 trades in 7d (filter working). — 2026-09-15 ~11:50 UTC
- **SHORT_NORMAL_PENALTY=0.85.** EXPIRED monitoring. Working well: 24h 6T 83.3%WR +$0.60. — 2026-09-14 ~05:30 UTC
- **pump-chain+ NORMAL BLOCKED.** Signal_reporter 05:10 UTC Sep 15. — 2026-09-15
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
4. **NEXT: Execution-time revalidation for stale signals.** 31.2% stale, WR 49.4% vs fresh 58.1%. ~$3.85/7d lost. Needs design — check signal staleness before executing. — 2026-09-16
5. **INVESTIGATE: Resistance proximity filter for SHORT entries.** rr_engine_resistance exits 36T/7d -$1.31. Needs resistance data to verify impact on winners. — 2026-09-16
6. **DEVELOP: New signals for NEUTRAL regime.** Only 2 signal types pass confluence. Need diversity. — 2026-09-16
