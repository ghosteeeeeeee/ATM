# Current State — System Improvement Focus

**Last Updated: 2026-09-04 ~23:00 UTC (CEO)**
**Updated by: CEO**

## Current Status

ema300-dip KILLED by signal_reporter at 17:14 UTC. v3-long+, v3-short-, slow-grind- all dead. System on 2 backbone signals: bb-bounce-v2-long+, accel-300-v2-short-. **R:R FIX APPLIED** — PM_TRAIL widened (0.40%→0.60% activate, 0.20%→0.40% distance), ATR_SL raised (1.2%→1.5% min, 1.5%→1.8% max). Only 1 trade closed post-fix — need 20+ to evaluate.

- **24h:** 45T, 48.9% WR, -$1.82 (verified DB)
- **7d:** 384T, 53.6% WR, -$4.89 (verified DB)
- **7d TOP 3:** bb-bounce-v2-long+ 34T/76.5% WR +$0.88 ★ | continuation+ 4T/100% WR +$0.30 | ema300-dip-short 2T/100% WR +$0.16 (too few trades)
- **7d WORST 3:** accel-300-v3-long+ 35T/42.9% WR -$1.34 (KILLED) | ema300-dip 54T/63% WR -$0.84 (KILLED) | accel-300-v2-long 21T/28.6% WR -$0.74 (legacy)
- **Market:** 100% NEUTRAL
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **BB_BOUNCE_V2_LONG:** Live. 34T/7d 76.5% WR +$0.88. STAR performer.
- **ACCEL_300_V2_SHORT-:** Live. 11T/7d 27.3% WR -$0.20. ALL trades in NEUTRAL regime (27.3% WR). Monitor.
- **CONTINUATION+:** Live. 4T/7d 100% WR +$0.30. Too few trades to evaluate.
- **EMA300_DIP KILLED.** signal_reporter killed 17:14 UTC. NEVER_REENABLE_FLAGS.
- **EMA300_DIP_SHORT:** Live. 2T/7d 100% WR +$0.16. Promising, small sample.
- **Coin tracker:** FIXED. Timer enabled, running every 30min.
- **CONF_FILTER_MIN=70.** Lowered from 75.
- **Open positions:** 4 (1 LONG ema300-dip legacy, 2 SHORT ema300-dip-short, 1 LONG bb-bounce-v2-long+). All slightly negative (~-$0.25 total).
- **slow-grind-:** KILLED. CEO killed Sep 4. NEVER_REENABLE_FLAGS.
- **Disk:** 84% (19G free). Cleaned ~1G of stale logs/DBs. Approaching 85% trigger.

**⚠️ ACTIVE BLEEDERS (CEO_PROTECTED):**
1. **macd-div- SHORT** — 8T/7d 25% WR -$0.50. FLAGGED. Monitor.
2. **confluence-,ichimoku- SHORT** — 7T/7d 28.6% WR -$0.46. FLAGGED FOR T.

**🔴 R:R FIX APPLIED (CEO Sep 4 ~20:00 UTC)**
Exit breakdown (7d system-wide):
- profit-monster-trail: 99T, 92.9% WR, avg +$0.053 (OLD — was capped at ~$0.06 wins)
- atr_sl_hit: 78T, 23.1% WR, avg -$0.077 (OLD — losses avg $0.133)
- cut-loser-CL-T1: 13T, 0% WR, avg -$0.145
- hard_sl: 4T, 0% WR, avg -$0.205
**Fix:** PM_TRAIL_ACTIVATE_PCT 0.40%→0.60%, PM_TRAIL_DISTANCE_PCT 0.20%→0.40%. ATR_SL_MIN 1.2%→1.5%, ATR_SL_MAX 1.5%→1.8%. All fallback/floor values updated to match.
**Expected:** avg win $0.074→$0.11+, avg loss $0.13→$0.15. R:R 0.57→0.73. Breakeven WR drops from 63.7% to 55.6%.

## Today's Changes (Sep 4)

5. **CEO ~23:00 UTC — VERIFIED + MONITORING.** DB: 24h 45T 48.9% WR -$1.82. 7d: 384T 53.6% WR -$4.89. R:R fix deployed ~20:00, only 1 trade closed post-fix (+$0.13). Need 20+ trades to evaluate. ema300-dip legacy closing (19T/24h). ema300-dip-short alive (2T/7d +$0.16 100% WR). 4 open positions ~-$0.25. Disk cleanup ~1G freed (84%). accel-300-v2-short- 27.3% WR ALL NEUTRAL — monitor.
4. **CEO ~20:00 UTC — R:R FIX.** Verified DB: 24h 61T 54.1% WR -$1.93. 7d: 384T 53.6% WR -$4.89. **R:R FIX APPLIED** — PM_TRAIL_ACTIVATE_PCT 0.40%→0.60%, PM_TRAIL_DISTANCE_PCT 0.20%→0.40%. ATR_SL_MIN 1.2%→1.5%, ATR_SL_MAX 1.5%→1.8%. All fallbacks updated (SL_PCT_FALLBACK, STOP_LOSS_DEFAULT, SL_PCT_MIN, TP_PCT_FALLBACK 3.6%→4.5%). TRAILING_ACTIVATION_PCT 0.40%→0.60%. **Expected:** avg win $0.074→$0.11+, R:R 0.57→0.73, breakeven WR 63.7%→55.6%. bb-bounce-v2-long+ STAR (34T/76.5%WR +$0.88/7d) should benefit most. System on 2 backbone signals. 2 open legacy positions flat.
3. **Orchestrator 18:30 — VERIFIED + ANALYSIS.** DB: 24h 58T 60.3% WR -$1.76. 7d: 373T 57.9% WR -$3.63. ema300-dip KILLED at 17:14. R:R ROOT CAUSE: PM_TRAIL wins avg $0.060, ATR_SL losses avg $0.133. NEXT: Fix R:R (done by CEO).
2. **Signal Reporter 17:14 — KILL.** ema300-dip killed. EMA300_DIP_ENABLED=False, added to NEVER_REENABLE. 34T/24h 58.8% WR -$1.13. Last 6h 25% WR -$1.14. Structural: avg loss ($0.15) 2.7x avg win ($0.057). Committed + pushed.
1. **Orchestrator 06:30 — VERIFIED + FLAGGED.** DB: 24h 82T 59.8% WR -$0.73. 7d: 407T 54.1% WR -$3.42. **R:R PROBLEM: 59.8% WR losing money — avg loss > avg win.** All signals negative today. v3-short- killed by auto_1hr (3T/0% WR -$0.48, pre-kill positions). cascade_flip trade (ENA) happened before disable at 04:36. slow-grind- TESTING 3T/7d 33.3% WR -$0.17. 5 open positions small. Disk 84%. 22 failed services (one-shot). Health monitor auto-fixed logs. **CRITICAL: Exit quality is bottleneck — not signal selection. Needs R:R investigation.**
0. **CEO 06:00 — VERIFIED + ACTION.** DB: 24h 82T 59.8% WR -$0.73. 7d: 410T 53.7% WR -$3.42. **v3-long+ CONFIRMED DEAD** — zero Sep 4 trades (last trade Sep 3). v3-short- killed by auto_1hr today (3T/0% WR -$0.48). **KILLED slow-grind-** — 15T/30d 33.3% WR -$0.81. Added to NEVER_REENABLE_FLAGS. Added ACCEL_300_V3_SHORT to NEVER_REENABLE. 3 backbone signals ALL profitable 14d: accel-300-v2- SHORT 72T/52.8%WR +$1.46, bb-bounce-v2-long+ 33T/75.8%WR +$0.86, ema300-dip 44T/68.2%WR +$0.19. Today losses normal variance (ema300-dip 8T/50% -$0.32, bb-bounce 5T/40% -$0.04). 5 open ~$0. Disk 84% ⚠️ approaching 85% trigger. Market 100% NEUTRAL. **EXPECTED IMPACT: slow-grind -$0.81/30d removed. v3-long+ -$1.34/7d already removed. System should be profitable with only backbone signals.**
1. **Orchestrator 06:30 — VERIFIED + FLAGGED.** DB: 24h 82T 59.8% WR -$0.73. 7d: 407T 54.1% WR -$3.42. **R:R PROBLEM: 59.8% WR losing money — avg loss > avg win.** All signals negative today. v3-short- killed by auto_1hr (3T/0% WR -$0.48, pre-kill positions). cascade_flip trade (ENA) happened before disable at 04:36. slow-grind- TESTING 3T/7d 33.3% WR -$0.17. 5 open positions small. Disk 84%. 22 failed services (one-shot). Health monitor auto-fixed logs. **CRITICAL: Exit quality is bottleneck — not signal selection. Needs R:R investigation.**
2. **CEO 02:35 — VERIFIED + ACTION.** DB: 24h 86T 64.0% WR +$0.07. 7d: 416T 54.8% WR -$1.83. **DISABLED ACCEL_300_V3_LONG_ENABLED** — CEO_PROTECTION expired Sep 4 05:00. Flag set False, removed from CEO_PROTECTED_FLAGS, added to NEVER_REENABLE_FLAGS. 35T/7d 42.9% WR -$1.34, ALL ATR_SL. No open v3-long+ positions (safe to kill). 5 open: v3-short x2, bb-bounce-v2-long+ x1, ema300-dip x1, slow-grind- x1. R:R analysis: accel-300-v2- SHORT best at 1.15. bb-bounce-v2-long+ STAR 32T/78.1% WR +$1.00. ema300-dip STAR 40T/67.5% WR +$0.16. **EXPECTED IMPACT: -$1.34/7d bleeding removed. System should be near breakeven or profitable without v3-long+.**

## Today's Changes (Sep 3)

0. **CEO 17:22 — VERIFIED + ACTION.** DB: 24h 75T 66.7% WR +$0.30. Today: 61T 67.2% WR +$0.49 (BEST DAY since Aug 28 +$1.55). Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 +$0.49 (STRONG REVERSAL). 17h traded, system trending positive. ema300-dip 24T/7d 75% WR +$0.69 STAR. bb-bounce-v2-long+ 20T/7d 85% WR +$0.74 STAR. v3-long+ 35T/7d 42.9% WR -$1.34 CEO_PROTECTED until Sep 4 05:00. bb-bounce-short KILLED by auto_1hr at 17:06 (3T/33.3% WR -$0.35). 5 open LONG positions ~$0. Disk 83%. Preserve mechanism bug: STX LONG stale signal. **ACTIONS: (1) Updated CURRENT.md. (2) v3-long+ MUST disable after 05:00 UTC Sep 4. (3) System on 3 strong signals: accel-300-v2- SHORT, bb-bounce-v2-long+, ema300-dip.**
1. **CEO 10:32 — VERIFIED + UPDATE.** DB: 24h 52T 57.7% WR -$1.16. Today: 26T 65.4% WR -$0.11 (best day since Aug 28). Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.11 (improving). 9 hours traded, 6 green hours. Kills verified: range-reversion 0 post-kill trades (last closed Sep 2 13:50), r2-trend-long3 0 post-kill trades (last closed Sep 3 01:02). accel-300-v3-long+ still CEO_PROTECTED, 4T/24h 25% WR -$0.48. Open positions flat (~$0 unrealized). No signal_compactor timeout issues in recent logs. **ACTIONS: (1) Updated CURRENT.md. (2) Prepared to disable accel-300-v3-long+ tomorrow. (3) Monitoring bb-bounce-v2-long+ and ema300-dip for expansion.**
2. **CEO 06:34 — VERIFIED + UPDATE.** DB: 24h 52T 51.9% WR -$1.63. 7d: 399T 51.6% WR -$2.35. **r2-trend-long3 KILL CONFIRMED** — signal_reporter killed it, 0 new trades post-kill (last trade closed 01:02 UTC). accel-300-v3-long+ still CEO_PROTECTED, 4 trades/24h ALL ATR_SL losers (-$0.59). bb-bounce-v2-long+ 13T/7d 76.9% WR +$0.20 strong. ema300-dip 9T/7d 66.7% WR +$0.16. 5 open positions all small. Disk 82%. Market 100% NEUTRAL. Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.17 (improving).
3. **CEO 02:15 — VERIFIED + ESCALATION.** DB: 24h 52T 51.9% WR -$1.86. 7d: 399T 51.6% WR -$2.35. 3 consecutive negative days. **ESCALATED to T: (1) DISABLE r2-trend-long3 — 10T/7d 30% WR -$0.55, CEO_PROTECTED since Aug 17, now bleeding. (2) DISABLE accel-300-v3-long+ after Sep 4 05:00 UTC — 18T/7d 33.3% WR -$0.98.** bb-bounce-v2-long+ 12T/7d 83.3% WR +$0.35 strong. volume-breakout 6T/7d confluence 100% WR. SHORT side +$0.62/7d profitable. System needs T approval to kill 2 protected bleeders.

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

- **ACCEL_300_V3_LONG KILLED.** CEO_PROTECTION expired Sep 4. 35T/7d 42.9% WR -$1.34. NEVER_REENABLE_FLAGS. — 2026-09-04
- **ACCEL_300_V3_SHORT KILLED.** auto_1hr killed Sep 4. 3T/7d 0% WR -$0.48. NEVER_REENABLE_FLAGS. — 2026-09-04
- **LONG_NEUTRAL_BLOCK DEPLOYED.** Blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS. — 2026-09-02
- **RANGE_REVERSION KILLED.** NEVER_REENABLE_FLAGS. — 2026-09-02
- **R2_TREND_LONG KILLED.** NEVER_REENABLE_FLAGS. — 2026-09-03
- **BB_BOUNCE_SHORT KILLED.** NEVER_REENABLE. — 2026-09-03
- **BB_BOUNCE_V2_LONG LIVE.** 32T/7d 78.1% WR +$1.00. STAR. — 2026-09-02
- **EMA300_DIP KILLED.** signal_reporter killed Sep 4. 34T/24h 58.8% WR -$1.13. NEVER_REENABLE_FLAGS. — 2026-09-04
- **CONF_FILTER_MIN=70.** — 2026-09-02
- **volume_breakout ACTIVE.** Confluence trades 100% WR. — 2026-08-31
- **DELEGATED: Build NEUTRAL regime signal.** — 2026-09-01
- **CONF_FILTER_MAX=89.** — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** — 2026-08-23
- **macd-div- DEGRADED.** 10T/7d 30% WR -$0.47. CEO_PROTECTED — flagged for T. — 2026-08-31
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11. CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 3T/7d +$0.30 66.7% WR. CEO_PROTECTED. — 2026-08-23
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** — 2026-08-29

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **CHECKPOINT: R:R FIX EFFECT.** Only 1 trade closed post-fix. Need 20+ trades to verify avg win improvement ($0.074→$0.11+). — 2026-09-04
2. **Monitor accel-300-v2-short-.** 11T/7d 27.3% WR -$0.20. ALL trades in NEUTRAL (27.3% WR). No EXTREME regime trades. Consider regime filter if doesn't improve. — 2026-09-04
3. **Monitor bb-bounce-v2-long+.** 34T/7d 76.5% WR +$0.88. STAR. R:R should improve with wider PM_TRAIL. — 2026-09-04
4. **Evaluate ema300-dip-short expansion.** 2T/7d 100% WR +$0.16. Promising but too small sample. — 2026-09-04
5. **Monitor continuation+.** 4T/7d 100% WR +$0.30. Too few trades to trust. — 2026-09-04
6. **Monitor macd-div-.** 8T/7d 25% WR -$0.50. CEO_PROTECTED — flagged for T. — 2026-09-04
7. **Delegate: Build NEUTRAL regime signal.** 3rd backbone candidate. System on only 2 signals — thin. — 2026-09-01
8. **Monitor disk.** Currently 84% (19G free). Cleaned ~1G. Approaching 85% trigger. — 2026-09-04
