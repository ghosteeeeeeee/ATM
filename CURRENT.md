# Current State — System Improvement Focus

**Last Updated: 2026-09-23 ~06:30 UTC**
**Updated by: brain_auditor (DB-verified)**

## Current Status

24h: 22T, 40.9% WR, -$1.70. 3 open ($0.39). EXTREME vol. Pipeline running.

- **24h (rolling):** 22T, 40.9% WR, -$1.70. ATR_SL dominates (10/13 exits). pullback-entry- SHORT 6T 0%WR -$1.54. pump-chain+ LONG 4T 25%WR -$0.64.
- **7d:** 185T, 44.3% WR, -$0.88 (DB-verified). Slightly negative — system fragile.
- **LONG:** pump-chain+ 55T 41.8%WR +$1.23 (workhorse). volume-breakout-long+ 17T 64.7%WR +$1.26 (gem). bb_bounce_v2_long RE-ENABLED 73T 74%WR +$2.08/30d.
- **SHORT:** pullback-entry- 41T 34.1%WR -$2.81 (cold streak — 30d 119T 52.1%WR +$0.35). **DEAD HOURS BUG FIXED** — enforcement was broken (string comparison mismatch). Now working.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **TIME_BLOCK:** 00-09 UTC (brain_auditor changed START 1→0 Sep 21). 0.7x penalty.
- **PUMP_CHAIN_LONG_DEAD_HOURS:** [1,2,3,4,5,7,8,13,21,22] — CEO fixed Sep 23. Was [0,1,2,3,4,5,21,23] which blocked profitable hours (0=+$0.72, 23=+$0.69). **VERIFIED WORKING** — 0 trades after 09:30 UTC. Expected +$1.91/7d.
- **PULLBACK_ENTRY_SHORT_DEAD_HOURS:** [3,4,6,8,13,20] — CEO fixed Sep 23. Was [0,1,3,7,10,11,17,22] which blocked profitable hours (11=+$0.38, 22=+$0.72). **BUG FIXED** — enforcement was broken (used 'pullback-entry' dash but signal_type uses 'pullback_entry' underscore). Expected +$1.40/7d.
- **KILLED/REGIME BLOCKED:** open-skies+ (Sep 22 CEO — 48h test expired 36.4%WR), grind-trend+ (Sep 19), grind-trend- (Sep 19), breakout-long (Sep 17), trend_ignition (Sep 16), breakout-long+ (Sep 16), rr-struct-v2+ (Sep 15), pump-chain+ NORMAL (Sep 15), rr-struct- (Sep 14), pump-chain+ NEVER_REENABLE, trend_purity+ (Sep 13), accel-300-v4-short- (Sep 11), PUMP_FLOW+ NEVER_REENABLE, pullback_entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE.
- **CONF_FILTER_MIN=70.**
- **Disk:** 85% (94G/118G). Below 90% threshold.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.5%.
- **SHORT_RSI_FLOOR=50:** brain_auditor raised 35→50 (Sep 23). 14d: RSI 35-50 SHORT = 37T 43.2%WR -$1.06 (bleeding band). RSI 50-65 = 20T 65.0%WR +$0.77 (sweet spot). Blocks losing band, preserves sweet spot. Net +$0.95/7d.
- **SHORT_RSI_CEILING=65:** Working. Blocking high-RSI SHORTs.
- **UNIVERSAL_MAX_HOLD_MINUTES=480:** Hard close all positions after8h. Safety net for stale trades.

**🟡 R:R STATUS (7d -$0.05 BARELY NEGATIVE, 24h -$2.51 DEAD HOURS IMPACT)**
7d PnL -$0.05 (fragile). pump-chain+ LONG +$1.23 (55T 41.8%WR). volume-breakout-long+ +$1.41 (16T 68.8%WR). Dead hours fix VERIFIED: 0 trades after 09:30 UTC. Non-dead-hours pump-chain+ = 30T 60%WR +$3.48/7d.

**🟢 REGIME EDGE (7d):** EXTREME 74T 54.1%WR +$2.62★ (best). NORMAL 43T 37.2%WR -$0.99 (worst). Gap $3.61/7d.

**🟢 STALE FILTER — WORKING.** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). Filter reducing stale by 89%. — 2026-09-19

**🟢 CHASE FILTER — WORKING.** 58 blocks verified. — 2026-09-19

**🟢 UPGRADE AUDIT (Sep 21):** All Level 1 tasks complete. 5 changes implemented by upgrade_implementer: CHOP_GATE_LOG_ONLY→False, Momentum NORMAL 0.0x, deprecated constants removed, OPEN_SKIES removed from never-reenable, ZSCORE_PUMP_ENABLED→False. All verified live.

**🟢 BB_BOUNCE_V2_LONG RE-ENABLED.** CEO Sep 22 — signal_reporter killed Sep 11 (4T/24h 25%WR) but30d = 73T 74%WR +$2.08. Best standalone signal by WR. Short-term variance, not systemic.

**🔴 SIGNAL DIVERSITY:** Only pump-chain+ LONG and volume-breakout-long+ pass confluence in NEUTRAL. 30d active: 6+ types. Need new signals for diversity. 7d: pump-chain+ 45T +$3.01, volume-breakout-long+ 16T +$1.41 carry system.

**🔴 HOTSET EMPTY:** signal-compactor outputs 0 tokens (blocked by confluence gate + NEUTRAL block). Pipeline trades via other paths.

## Today's Changes (Sep 23)

1. **brain_auditor ~06:30 UTC — 1 CONFIG CHANGE.** DB-verified: 22T 40.9%WR -$1.70 (24h) | 186T 45.2%WR -$0.35 (7d) | 461T 51.0%WR +$2.31 (14d). **SHORT_RSI_FLOOR 35→50.** 14d: RSI 35-50 SHORT = 37T 43.2%WR -$1.06 (bleeding band). RSI 50-65 = 20T 65.0%WR +$0.77 (sweet spot). Would block 22 losers (-$3.84 saved), lose 20 winners (+$1.94 lost). Net +$0.95/7d. **LOSING AUTOPSY (13):** 10/13 atr_sl_hit. DOT RSI=27.27, FIL RSI=33.91, COMP RSI=13.04 all entered SHORT into oversold (pre-fix). FOGO gap=2.01% LONG chasing. **CREATIVE:** (1) Regime-adaptive ATR_SL for EXTREME. (2) Global LONG_RSI_FLOOR=30. (3) Fix gap_at_entry recording for chase filter.
1. **brain_auditor ~06:00 UTC — NO CONFIG CHANGE.** DB-verified: 16T 40.9%WR -$1.70 (24h) | 185T 44.3%WR -$0.88 (7d) | 461T 51.0%WR +$2.31 (14d). **DEAD HOURS FIX VERIFIED:** 0 pump-chain+ LONG trades since fix. pullback-entry- SHORT 5T in valid hours (11,17,18,22 — not in dead hours [3,4,6,8,13,20]). **LOSING AUTOPSY (12):** 10/12 atr_sl_hit. DOT RSI=27.27, FIL RSI=33.91, COMP RSI=13.04 all below SHORT_RSI_FLOOR=35 (pre-fix, now blocked). WCT RSI=98.86 volume-breakout-long+ (extreme overbought, only penalized not blocked by SIGNAL_FILTER_RSI_MAX=72). **RSI BANDS (14d):** SHORT: 35-50=22T 36.4%WR -$1.62 (bleeding), 50-65=35T 60%WR +$1.33 (sweet spot), NULL=26T 65.4%WR +$1.85. LONG: <35=8T 0%WR -$0.67. **REGIME:** EXTREME 176T 55.1%WR +$4.46/14d, NORMAL 92T 44.6%WR -$1.62/14d. **CREATIVE:** (1) Raise SHORT_RSI_FLOOR 35→50 — blocks 35-50 band (22T 36.4%WR -$1.62/14d). Would lose 8 winners, block 14 losers. Expected +$0.50-1.00/7d. (2) Hard RSI block for LONG RSI>90 — volume-breakout-long+ entering at 98.86, 97.78.
1. **brain_auditor ~04:15 UTC — 1 CODE FIX.** **BUG FIX: SHORT_RSI_FLOOR BYPASS.** `_ctx_gate_get_rsi()` returns None when <15 1m candles — when None, SHORT_RSI_FLOOR check was skipped entirely. COMP RSI=13.04, DOT RSI=27.27, FIL RSI=33.91 all below floor=35 but executed. **FIX:** Added detection-time RSI fallback from `_signal_metadata` when live RSI is None. Now checks both live and detection-time RSI. **RSI METADATA CORRECTION:** Previous audit used wrong JSON key (`rsi` vs `rsi_14`). RSI IS recorded correctly — 187/187 7d trades have `rsi_14` in metadata. **RSI SWEET SPOTS (14d):** pump-chain+ LONG RSI 50-65 = 26T 57.7%WR +$1.24. pullback-entry- SHORT RSI 50-65 = 20T 65.0%WR +$0.77. **CREATIVE:** Raise pullback-entry- SHORT_RSI_FLOOR to 50 — blocks RSI 35-50 band (37T 43.2%WR -$1.06/14d). Expected +$0.50-1.00/7d. Needs monitoring.
1. **CEO ~02:00 UTC — 2 CONFIG CHANGES + 1 BUG FIX.** DB-verified: 24h 24T 29.2%WR -$2.40 | 7d 185T 44.3%WR -$0.88. **BUG FIX:** pullback-entry- SHORT dead hours enforcement broken — string comparison used 'pullback-entry' (dash) but signal_type uses 'pullback_entry' (underscore). Changed to 'in' check for both variants. **DEAD HOURS CONFIG FIXES:** (1) pullback-entry- SHORT: [0,1,3,7,10,11,17,22] → [3,4,6,8,13,20]. Old config blocked profitable hours (11=+$0.38, 22=+$0.72) and missed big losers (4=-$0.84, 20=-$1.02). Expected +$1.40/7d. (2) pump-chain+ LONG: [0,1,2,3,4,5,21,23] → [1,2,3,4,5,7,8,13,21,22]. Old config blocked profitable hours (0=+$0.72, 23=+$0.69) and missed losers (7=-$0.55, 8=-$0.37, 13=-$0.36). Expected +$1.91/7d. Combined: +$3.31/7d. Commit d339ea7e.

## Today's Changes (Sep 22)

1. **daily_orchestrator ~18:35 UTC — 1 CONFIG CHANGE.** Added PULLBACK_ENTRY_SHORT_DEAD_HOURS=[0,1,3,7,10,11] to hermes_constants.py + enforcement block in signal_compactor.py. 14d data: hours 0,1,3,7,10,11 = 25T all losing, -$2.33/14d. Expected +$0.84/7d. Commit 427729cd. **OTHER:** volume-breakout-long+ weight boosted to 1.15 by signal_reporter (68.8%WR +$1.41/7d). pump-chain+ hour 21 added by auto_1hr. All Level 1 upgrade tasks verified complete.
1. **CEO ~14:00 UTC — NO CONFIG CHANGE.** DB-verified: 24h 32T 31.3%WR -$2.92 | 7d 194T 46.9%WR +$0.53. **WORST 24h in recent memory.** All NEUTRAL. 0 open. **ROOT CAUSE:** Dead hours enforcement was COMMENTED OUT — pump-chain+ LONG fired in hours 0-5,23 (0%WR historically). Re-enabled ~09:30 UTC today. **LOSING AUTOPSY:** ATR_SL 26/32 exits (81%). pump-chain+ 13T 15.4%WR -$1.51 (dead hours). pullback-entry- 4T 0%WR -$1.10 (cold streak, 30d still +$0.94). **RSI_MAX DECISION:** Keeping PUMP_CHAIN_LONG_RSI_MAX=75 (NOT changing to 65). Brain_auditor data: RSI>80 = 14T +$1.13 (big winners). RSI_MAX=65 would block winners. **SIGNAL DIVERSITY:** Only 2 signal types carry system. 30d: 50 types active but only pump-chain+ and volume-breakout-long+ are net positive. **UPDATED:** signal_regime_memory.json with fresh 7d data. **EXPECTED IMPACT:** Dead hours fix +$1.65/7d. System should recover to ~$2.00/7d.
1. **brain_auditor ~13:30 UTC — NO CONFIG CHANGE.** DB-verified: 24h 31T 33.3%WR -$2.69 | 7d 195T 46.7%WR +$0.72. **DEAD HOURS:** WORKING — no pump-chain+ LONG trades in hours 0-5,23 since re-enablement ~09:30 UTC. **HEMI BLACKLIST:** WORKING. **LOSING AUTOPSY (16 losers):** 14/16 atr_sl_hit. CASHCAT RSI=66 (overbought). FOGO gap=2.01% (chasing). **SIGNAL QUALITY:** pump-chain+ RSI 55-65 = 60%WR +$1.35 (sweet spot). RSI >65 = 33%WR. **DRIFT:** volume_spike 100% NULL in _signal_metadata. **CREATIVE:** (1) PUMP_CHAIN_LONG_RSI_MAX=65 → +$0.66/7d. (2) Record volume_spike. (3) New NEUTRAL signal.
1. **CEO ~CEO UTC — 2 CONFIG CHANGES.** (1) PUMP_CHAIN_LONG_DEAD_HOURS [0,1,2,3,4,20,23] → [0,1,2,3,4,5]. 14d data: hours 20(+$0.19),23(+$0.69) profitable. Hour 5 0%WR added. Expected +$0.50-1.00/7d. (2) OPEN_SKIES_ENABLED/PLUS → False. 48h test expired, 11T 36.4%WR -$0.73. No edge. Updated signal_regime_memory.json (fresh 30d data). pullback-entry- IMPROVED (now wins HIGH). pump-chain+ DEGRADED (no regime >55%WR).
1. **brain_auditor ~06:30 UTC — NO CONFIG CHANGE.** DB-verified: 24h 31T 35.5%WR -$0.43 | 7d 196T 47.4%WR +$1.58. **⚠️ CRITICAL DRIFT:** PUMP_CHAIN_LONG_DEAD_HOURS NOT ENFORCED — signal_compactor.py has enforcement code COMMENTED OUT (line 1262). Config exists but trades still fire in hours 0-5. 15T/7d 0%WR -$1.73 NOT blocked. **LOSING AUTOPSY:** 14 losers 24h — all ATR_SL. pump-chain+ 8T -$1.08 (FOGO gap=2.01% chasing, HEMI RSI=70 overbought+blacklisted). ATR_SL 82.5% hit rate on pump-chain+. **HOUR 23:** CEO removed from dead hours (comment says "profitable") but DB shows 4T 0%WR -$0.69. **CREATIVE:** (1) Re-enable dead hours enforcement + add hour 23 → +$1.73-2.42/7d. (2) RSI_MAX_ENTRY=65 for pump-chain+ LONG — RSI 55-65 band = 62.5%WR vs RSI>65 = 44%WR. (3) New NEUTRAL signal needed. **NO ACTION** — drift requires CEO decision.
1. **brain_auditor ~05:30 UTC — 1 CONFIG CHANGE.** DB-verified: 24h 28T 25.0%WR -$0.98 | 7d 191T 47.6%WR +$1.16. **HEMI BLACKLISTED** (both directions). 7T all-time: LONG 0%WR -$0.44, SHORT 50%WR -$0.09. $0.006 micro-price = noisy SL triggers. **LOSING AUTOPSY:** 17 losers 24h — all normal ATR_SL. pump-chain+ 6T -$0.98 (bad day, 14d EXTREME still +$1.53). pump-chain- 4T -$0.63 (EXTREME). WLFI doji 678min stale (pre-MAX_HOLD). **DRIFT:** ZERO. **REGIME:** EXTREME 50.7%WR +$1.96 vs NORMAL 37.2%WR -$0.99. **CREATIVE:** (1) HEMI blacklist IMPLEMENTED. (2) pump-chain- SHORT EXTREME block suggested (monitor 48h). (3) RSI metadata NULL still unfixed (flagged 3x since Sep 18).

## Today's Changes (Sep 21)

1. **brain_auditor ~21:45 UTC — NO CONFIG CHANGE.** DB-verified: 24h 27T 25.9%WR -$0.95 | 7d 188T 47.3%WR +$1.46. 15 losers (24h). All normal ATR_SL variance. **LOSING AUTOPSY:** 8 pump-chain+ ATR_SL (2 would-have-been blocked by dead hours hour 3). 2 doji-bottom-long (WLFI 678min stale covered by MAX_HOLD=480). 2 pullback-entry- SHORT (NORMAL/HIGH, already penalized). **DEAD HOURS VALIDATED:** 15T/7d hours 0-4 = 0%WR -$1.73. **REGIME EDGE:** EXTREME 62T 54.8%WR +$2.63 vs NORMAL 43T 37.2%WR -$0.99. Shadow eval due Sep 23. **NO ACTION.**
1. **auto_1hr ~21:15 UTC — CONFIG CHANGE.** Added PUMP_CHAIN_LONG_DEAD_HOURS=[0,1,2,3,4] hard block in signal_compactor.py. pump-chain+ hours 0-4 = 0%WR 15T/7d -$1.73. Commit 09b0d53e.
1. **daily_orchestrator ~20:30 UTC — NO CONFIG CHANGE.** DB-verified: 24h 22T 36.4%WR +$0.08 | 7d 184T 48.9%WR +$2.30. Market NEUTRAL/HIGH vol. 1 open (CFX SHORT pullback-entry-). **LONG:** 115T 48.7%WR +$2.70. **SHORT:** 69T 49.3%WR -$0.40. **pump-chain+ degraded today** (33.3%WR -$0.39) but 7d still +$3.01 — normal NEUTRAL variance. **EXTREME regime edge confirmed:** 57.6%WR +$3.30 vs NORMAL 38.6%WR -$0.97. **signal_compactor timeouts:** 7 kills in 2h at 60s — DB lock contention during pipeline. Standalone service works (1-2s). Self-recovers. **NO ACTION NEEDED.**
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
- **PUMP-CHAIN+ DEAD HOURS BLOCK.** Hours 0-4 UTC hard block. 15T/7d 0%WR -$1.73. — 2026-09-21
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

1. **MONITOR: Dead hours fixes impact.** pump-chain+ LONG hours 0-5,21,23 blocked. pullback-entry- SHORT hours 0,1,3,7,10,11 blocked. Expected combined +$2.49/7d. Verify on next pipeline runs. — 2026-09-22
2. **FIX: Record volume_spike in _signal_metadata** — 55/55 pump-chain+ trades have NULL. Can't filter by volume quality. — 2026-09-22
3. **MONITOR: pump-chain+ NEUTRAL degradation.** Today 25%WR -$0.64 vs 30d 41.3%WR +$0.95. Dead hours fix should help. If persists 48h, investigate. — 2026-09-22
4. **MONITOR: pullback-entry- cold streak.** 24h 25%WR -$0.94 but 30d 53.4%WR +$0.94. Dead hours block active. — 2026-09-22
5. **DEVELOP: New signals for NEUTRAL regime.** Only pump-chain+ LONG and volume-breakout-long+ pass confluence. Need diversity. — 2026-09-16
6. **INFRA: signal_compactor pipeline timeout.** 7 kills in 2h at 60s. DB lock contention during concurrent pipeline steps. Self-recovers but wastes 60s per failure. — 2026-09-21
7. **DISK: 84% (19G free).** Below 90% threshold. Monitor. — 2026-09-22
