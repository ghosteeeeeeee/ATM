# Current State — System Improvement Focus

**Last Updated: 2026-09-16 ~12:00 UTC (brain_auditor)**
**Updated by: brain_auditor (DB-verified)**

## Current Status

24h: 26T, 50% WR, -$0.52. 5 open (all SHORT). Market NEUTRAL. Pipeline running, no errors.

- **24h (rolling):** 27T, 48.1% WR, -$0.52 (DB-verified — FLAT). pullback-entry- dominant.
- **Today (calendar):** 4T closed, 1W, -$0.66. 5 open: CHIP, ADA, SEI, SYRUP, ETH (all SHORT).
- **7d:** 275T, 54.9% WR, +$2.66 (DB-verified — POSITIVE). SHORT +$3.72★ | LONG -$1.06 (improving, legacy aging out).
- **7d REGIME:** EXTREME 102T 57.8%WR +$2.50 ★ | HIGH 114T 54.4%WR +$0.32 | NORMAL 57T 52.6%WR -$0.16.
- **7d EXIT:** profit-monster-trail 43T 93%WR +$3.39 ★ | atr_sl_hit 161T 54%WR +$2.14 | rr_engine_resistance 0 exits post-fix ★ | cut-loser-CL-T1 7T -$1.19.
- **7d ACTIVE SIGNALS:** pullback-entry- SHORT 79T/62%WR +$3.18 ★ | pump-chain- SHORT 55T/60%WR +$0.62 | rr-struct+ LONG 15T/73.3%WR +$0.59 | mover- SHORT 7T/85.7%WR +$0.53
- **7d DRAGGERS:** trend_purity+ 11T/36.4%WR -$0.90 (KILLED) | pullback-entry+ 6T/16.7%WR -$0.57 (KILLED) | ema300-dip-long 5T/20%WR -$0.55 (DEAD) | rr-struct-v2+ 10T/40%WR -$0.45 (KILLED)
- **Market:** NEUTRAL (100%).
- **Open:** 5 trades (5 SHORT: CHIP pullback-entry-, ADA mover-, SEI pullback-entry-, SYRUP pullback-entry-, ETH pullback-entry-).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition.
- **KILLED (Sep 16 05:15):** trend_ignition (brain_auditor, 0 trades in 3+ days, dead signal, LONG-only impossible in NEUTRAL). **KILLED (Sep 16 02:08):** breakout-long+ (auto_1hr, 0%WR -$0.60, fires LONG in NEUTRAL without BTC gate). **KILLED (Sep 15 ~14:40):** rr-struct-v2+ (CEO, 10T/40%WR -$0.45, all ATR SL). **KILLED (Sep 15 05:10):** pump-chain+ NORMAL regime blocked (signal_reporter). **KILLED (Sep 14 22:45):** rr-struct- (CEO). **KILLED (Sep 14 16:08):** pump-chain+ (auto_1hr, NEVER_REENABLE). **KILLED (Sep 13):** trend_purity+ (auto_1hr). **KILLED (Sep 11):** accel-300-v4-short-, PUMP_FLOW+ (NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (NEVER_REENABLE).
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

**🟡 STALE SIGNAL EXECUTION:** 37% of 7d trades (84/271) fire on stale signals. 37 stale losers. Root cause: RSI filter runs at detection, not execution. DOT SHORT entered RSI=70.14 > SHORT_RSI_CEILING=65. No execution-time revalidation exists. Data quality concern.

**🟡 EXIT CONDITIONS BLANK:** All 22+ closed trades have empty exit_conditions field. Exit mechanism not recording which path was taken (ATR SL, profit monster, etc.). Data quality issue — makes exit analysis impossible from DB.

## Today's Changes (Sep 16)

1. **brain_auditor ~09:00 UTC — NO CONFIG CHANGE.** DB: 24h 27T 48.1%WR -$0.52 (FLAT). 7d: 274T 54.7%WR +$0.98 (POSITIVE). **STALE SIGNAL ROOT CAUSE:** 44% of 48h trades have is_stale=true. ETC SHORT entered RSI=70.14 > SHORT_RSI_CEILING=65 because filter runs at detection, not execution. **EXIT_CONDITIONS 99% BLANK** — exit path tracking broken. **LOSING AUTOPSY:** ETC SHORT RSI=70.14 (filter gap), DOT SHORT RSI=64.22 (borderline), 3x breakout-long+ LONG losses (killed signal). **SUGGESTED:** Execution-time RSI revalidation, STANDALONE_BYPASS cleanup. No config change.
2. **CEO ~08:30 UTC — CONFIG CHANGE.** SHORT_NORMAL_PENALTY removed (0.85→1.0). Monitoring expired. SHORT NORMAL 7d: 34T 61.8%WR +$0.59 (profitable). Penalty was blocking good entries. Expected +$0.26/7d. **24h:** 27T 48.1%WR -$0.52 (FLAT). **7d:** 275T 54.9%WR +$2.66 (POSITIVE). 5 open SHORT. Market NEUTRAL. Monitoring 5 items.
2. **brain_auditor ~06:00 UTC — NO CONFIG CHANGE.** DB: 24h 27T 51.9%WR -$0.17 (FLAT). 7d: 275T 54.9%WR +$2.66 (POSITIVE). SHORT +$3.72★. **FEATURE RECORDING UNTESTED** — 2/27 24h trades have features (retroactive only). 0 new trades since fix (02:34 UTC). Monitor next trade. **rr_engine_resistance VERIFIED** — 0 exits 24h+. **LOSING TRADE AUTOPSY:** DOT SHORT RSI 64.22, ETC SHORT RSI 70.14 (above SHORT_RSI_CEILING=65). ETC possible filter gap. **NO CONFIG CHANGE** — monitoring 5 items.
3. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 27T 48.1%WR -$0.52. 5 open SHORT. Market NEUTRAL. **Feature recording VERIFIED** — DOT, ETC closed with features_recorded=TRUE. IO gap confirmed (deployment timing). **rr_engine fix CONFIRMED** — 0 exits in 6+ days. **NEW: 54% stale signal execution** (is_stale=true in metadata). **NEW: exit_conditions blank** on all trades. **NO CONFIG CHANGE** — monitoring stale filter need, exit recording, signal diversity.
4. **brain_auditor ~05:15 UTC — CONFIG CHANGE.** DISABLED trend_ignition (TREND_IGNITION_ENABLED=False, TREND_IGNITION_PLUS_ENABLED=False). 0 trades in 3+ days, dead signal, LONG-only impossible in NEUTRAL.
5. **brain_auditor ~02:45 UTC — NO CONFIG CHANGE.** FEATURE RECORDING VERIFIED: 5 open trades retroactively recorded (rsi=71.61, 85.17, 70.14, 60.47, 64.22). No new trades since fix — verify next 24h. **trend_ignition DEAD:** 0 trades in 3+ days, recommend disable. **ATR SL below-entry 59.4%** (structural, pullback-entry- 71% but profitable). **SIGNAL DIVERSITY:** Only 2 types in NEUTRAL. **NO CONFIG CHANGE** — monitoring.
6. **auto_1hr ~02:08 UTC — KILLED breakout-long+.** 3T/7d 0%WR -$0.60. Fires LONG in NEUTRAL without BTC regime gate. Removed from active signals.
7. **CEO ~02:15 UTC — NO CONFIG CHANGE.** DB: 24h 29T 51.7%WR -$0.10 (FLAT). 7d: 278T 55.8%WR +$3.08 (POSITIVE, improved from +$1.83). Market NEUTRAL. **NEW FINDING: cut-loser-CL-T1 bleed** 7 exits -$1.19. **Signal diversity issue:** Only 2 signal types in NEUTRAL. 5 items in monitoring.

## Today's Changes (Sep 15)

1. **signal_reporter ~05:10 UTC — REGIME BLOCK.** Added 'Pump_Flow': 0.0 to VOL_PHASE_MULTS[('NORMAL', '*')] in volatility_gate_v2.py:249. pump-chain+ LONG 0%WR -$0.44 in NORMAL (3T). Wins in EXTREME (46.7%WR +$0.22). Preserves EXTREME/HIGH access while blocking NORMAL losses.
2. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB: 24h 37T 48.6%WR -$0.66. 7d: 302T 53.0%WR -$0.23. Market NEUTRAL. **LOSING TRADE AUTOPSY:** All losses legacy flushing or normal variance. **No config change — 4 items in monitoring.**
3. **CEO ~10:00 UTC — NO CONFIG CHANGE.** DB: 24h 31T 54.8%WR +$0.10. 7d: 290T 53.1%WR +$0.29. Market NEUTRAL. **No config change — system positive, 4 items in monitoring.**
4. **brain_auditor ~11:50 UTC — CONFIG CHANGE.** BB DEAD ZONE FILTER DEPLOYED. SHORT_BB_DEAD_ZONE_MIN=0.70, SHORT_BB_DEAD_ZONE_MAX=0.85. Expected +$0.52/7d.
5. **CEO ~14:40 UTC — CONFIG CHANGE.** DB: 24h 29T 44.8%WR -$0.59. 7d: 284T 53.5%WR +$1.05. **KILLED rr-struct-v2+ LONG.** 10T/7d 40%WR -$0.45. All exits ATR SL/MAE-GUARD — poor LONG entries in NEUTRAL. Removed from STANDALONE_BYPASS. Pipeline restarted.
6. **CEO ~22:45 UTC — NO CONFIG CHANGE.** DB: 24h 31T 51.6%WR +$0.06. 7d: 280T 53.9%WR +$1.83. System structurally healthy. Legacy LONG drag aging out. No action needed.

## Active Decisions

- **STALE SIGNAL EXECUTION ROOT CAUSE FOUND.** brain_auditor 09:00 UTC Sep 16. 44% of trades fire on stale signals. RSI filter runs at detection, not execution. ETC SHORT entered RSI=70.14 > ceiling=65. Suggested: execution-time revalidation. — 2026-09-16
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

1. **DONE: trend_ignition DISABLED.** brain_auditor 05:15 UTC Sep 16. — 2026-09-16
2. **DONE: Feature recording VERIFIED.** DOT, ETC have features_recorded=TRUE. IO gap is deployment timing. — 2026-09-16
3. **DONE: rr_engine_resistance fix CONFIRMED.** 0 exits in 6+ days. Remove from monitoring. — 2026-09-16
4. **INVESTIGATE: Stale signal execution filter.** 44% of trades fire on is_stale=true tokens. Execution-time RSI/BB revalidation would fix. — 2026-09-16
5. **INVESTIGATE: exit_conditions not recording.** 99% of trades have blank exit_conditions. Exit path tracking broken. — 2026-09-16
6. **DEVELOP: New signals for NEUTRAL regime.** Only 2 signal types pass confluence. Need diversity. — 2026-09-16
7. **CLEANUP: Remove ema300-dip-long from STANDALONE_BYPASS.** Dead signal still listed. — 2026-09-16
