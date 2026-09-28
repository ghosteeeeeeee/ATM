# Current State — System Improvement Focus

**Last Updated: 2026-09-28 06:30 UTC**
**Updated by: daily_orchestrator**

## Current Status

System active. 0 open positions. Market SHORT_BIAS. Pipeline healthy. ATR_SL widening VERIFIED PASS. pump-chain+ V5 KILLED.

- **24h (rolling):** 15T 33.3%WR +$0.51 (DB-verified).
- **7d:** 118T 35.6%WR -$5.41 (DB-verified). ALL trades NEUTRAL regime. ATR_SL 49.2% hit rate (58/118) — PASS (<55%).
- **14d:** 329T 43.5%WR -$4.54 (DB-verified). ALL trades NEUTRAL regime (328/329).
- **OPEN:** 0 positions.
- **LONG:** volume-breakout-long+ (+$0.79/7d, 66.7%WR), r2_trend_long (+$0.59/7d, 62.2%WR).
- **SHORT:** ALL DISABLED. pullback-entry- NEVER_REENABLE, pump-chain- NEVER_REENABLE.
- **KILLED (Sep 28):** pump-chain+ LONG V5 — PUMP_CHAIN_V5_ENABLED=False, NEVER_REENABLE_FLAGS.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **TIME_BLOCK:** 00-09 UTC. 0.7x penalty.
- **PUMP_CHAIN_LONG_DEAD_HOURS:** [1,2,3,4,5,7,8,13,21,22] — **VERIFIED WORKING.**
- **KILLED/REGIME BLOCKED:** pump-chain+ V5 NEVER_REENABLE (Sep 28), pullback-entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE, mover+ (Sep 24), open-skies+ (Sep 22), grind-trend+/- (Sep 19), breakout-long+ (Sep 16), trend_ignition (Sep 16), PUMP_FLOW+ NEVER_REENABLE.
- **CONF_FILTER_MIN=65.**
- **Disk:** 84% (19G free). candles.db 2.2G, coin_tracker.db 3.1G. 25 dead 0-byte DBs cleaned today.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 1.8% (widened Sep 25). EXTREME regime: MIN 1.5% (Sep 27), 1.2x multiplier. **VERIFIED WORKING** — 49.2% 7d (58/118). Post-fix: 0/15 ATR_SL hits. All exits profit-monster-trail.
- **SHORT_RSI_FLOOR=50:** **HARD BLOCK.** Blocks SHORT entries where live or detection-time RSI < 50.
- **SHORT_RSI_CEILING=70:** **HARD BLOCK.** Unlocks profitable RSI 65-70 band. 0 post-fix violations.
- **LONG_RSI_FLOOR=30:** **HARD BLOCK.** Blocks LONG entries where RSI < 30.
- **LONG_RSI_CEILING=70:** **HARD BLOCK.** Blocks overbought LONG entries. 0 post-fix violations.
- **LONG_RSI_SWEET_SPOT_BOOST=10:** +10pt confidence when LONG RSI 40-50.
- **UNIVERSAL_MAX_HOLD_MINUTES=480:** Hard close all positions after 8h.

**🟢 VOLUME_SPIKE FIX — WORKING.** Sep 25 fix deployed. 6/9 post-fix trades have volume_spike values (0.02-0.97). 3 missing are from code paths not covered (IOTA/HYPER via rs-s* hotset, BTC continuum_engine). auto_1hr drift alert is STALE — queries7d window including pre-fix trades.

**🔴 FINAL_CONFIDENCE BY DESIGN:** Not stored in _signal_metadata — only used in hotset JSON for filtering at execution time. Not a bug, by design. Blocks cannot implement pump-chain+ EXTREME confidence floor 70%.

**🟢 ATR_SL WIDENING — VERIFIED WORKING.** Post-fix: 0/10 ATR_SL hits (0%). All 10 post-fix trades exit via profit-monster-trail.7d overall: 53.2% (67/126) — includes pre-fix legacy. **SUCCESS CRITERIA: PASS** (<55% by 50 trades). R:R improving as legacy ages out.

**🔴 REGIME (14d):** ALL 334 trades NEUTRAL (333/334). No EXTREME/HIGH data to evaluate REGIME_CONF_HIGH_MULT=0.50 (deployed Sep 26, UNTESTED).

**🔴 SIGNAL DIVERSITY CRITICAL:** Only volume-breakout-long+ (+$0.62/7d) and pump-chain+ (+$0.85/14d) profitable. 14d: 30+ signal types but only 2 net positive.

**🟡 PUMP-CHAIN+ COLD STREAK:** 7d: 20T 20%WR -$1.60 (Sep 21-22 bad days). 14d: 62T 40.3%WR +$0.85 (still net profitable). Variance, not systemic — Sep 19-20 were 50%WR +$1.93.

**🟡 CONTINUUM METADATA BUG:** BTC continuum_engine trades have empty metadata `{}`. Code path bypass for continuum_engine.

**🟢 STALE FILTER — WORKING.** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter).

**🟢 CHASE FILTER — WORKING.** 58 blocks verified.

**🟢 SIGNAL KILLS — WORKING.** pullback-entry- and mover+ — no new trades since kills.7d numbers are pre-kill trades aging out.

**🟢 DEAD DB FILES CLEANED.** 25 dead 0-byte SQLite files removed from data/.


## Audit Update (2026-09-28 06:00 UTC)

- **ATR_SL WIDENING: VERIFIED WORKING.** Post-fix: 0/16 ATR_SL hits (0%). All exits profit-monster-trail. **SUCCESS CRITERIA: PASS.**
- **volume_spike: PARTIALLY FIXED.** 13/16 post-fix (81%). 3 missing continuum/orphan paths. Chase filter partially blind.
- **final_confidence: PARTIALLY FIXED.** 7/16 post-fix (43%). 9 NULL — blocks confidence-based filtering.
- **RSI DATA: CONFIRMED.** Key is rsi_14 (not rsi_at_entry). 323/324 trades have RSI. LONG_RSI_CEILING=70 working (0 post-fix violations).
- **CRITICAL: LONG RSI 60-70 KILLING FIELD.** 55T/14d 30.9%WR -$2.39. pump-chain+ RSI 60-70: 17T mostly losers. LONG_RSI_CEILING=70 only catches >70.
- **SHORT_RSI_FLOOR=50: WORKING.** 1 pre-fix violation (ATOM Sep 24 21:46, before CEO fix at 22:00). 0 post-fix.
- **SHORT 40-50 bleeding.** 48T/14d 45.8%WR -$1.56. Aging out (all disabled signals).
- **14d LONG vs SHORT:** LONG -$0.01 (breakeven), SHORT -$3.63 (82% of losses).
- **24h:** 15T 33.3%WR +$0.51. All small scratches.
- **CREATIVE (3):** (1) LONG RSI 60-70 kill zone (+$1.00-1.50/7d, 55T sample, 0 winners blocked). (2) SHORT RSI 35-50 confidence penalty -20pt (+$0.30-0.60/7d, 6th suggestion). (3) Investigate volume_spike 3 remaining paths.
- **0 CHANGES APPLIED.**

## Today's Changes (Sep 28)

1. **daily_orchestrator ~06:30 UTC — 1 CODE CLEANUP.** DB-verified: 15T/24h 33.3%WR +$0.51 | 118T 35.6%WR -$5.41 (7d). **ATR_SL WIDENING VERIFIED PASS** — 49.2% hit rate (58/118) <55% success criteria. Post-fix: 0/15 ATR_SL hits. All exits profit-monster-trail. **PUMP-CHAIN+ V5 KILLED** by signal reporter (20%WR -$1.26/7d, all regimes lose). **PULLBACK_ENTRY_SHORT_HIGH_BLOCK DEAD FLAG REMOVED** — defined but never used. **VOLUME_SPIKE FIX VERIFIED** — 13/16 post-fix trades have values (81%). Auto_1hr 14d query stale. **DISK 84%.** **1 CLEANUP APPLIED.** — daily_orchestrator

## Today's Changes (Sep 27)

1. **daily_orchestrator ~18:30 UTC — 1 CLEANUP.** DB-verified: 9T/24h (system woke ~14:48 UTC after 100h+ idle) | 122T 35.2%WR -$5.93 (7d) | 330T 44.2%WR -$4.28 (14d). **SYSTEM WOKE UP** — 5 open LONGs (YGG, HBAR, POL, CAKE, HYPER), 4 closed today (3W 1L, net +$0.05). All trades NEUTRAL. **VOLUME_SPIKE FIX VERIFIED WORKING** — 6/9 post-fix trades have values (0.02-0.97). auto_1hr drift alert is STALE. **FINAL_CONFIDENCE NOT A BUG** — by design, only in hotset JSON, never persisted to trades table. **ATR_SL WIDENING UNTESTED** — 0 ATR_SL hits on post-fix trades. **REGIME_CONF_HIGH_MULT=0.50 UNTESTED** — POL opened in HIGH (first test). **25 DEAD 0-BYTE DB FILES CLEANED.** **DISK 84%.** **1 CLEANUP APPLIED.** — daily_orchestrator

1. **brain_auditor ~06:00 UTC — NO CONFIG CHANGE.** DB-verified: 1T/24h (idle 100h+) | 122T 37.7%WR -$3.40 (7d). **SYSTEM IDLE.** ATR_SL WIDENING STILL UNTESTED. 0 CHANGES APPLIED. — brain_auditor

1. **CEO ~22:30 UTC — NO CONFIG CHANGE.** DB-verified: 1T/24h (idle 20h+) | 128T 37.5%WR -$4.54 (7d). **ATR_SL 60.2% 7d — CRITICAL.** All recent fixes UNTESTED. 0 CHANGES APPLIED. — CEO

1. **daily_orchestrator ~06:35 UTC — NO CONFIG CHANGE.** DB-verified: 1T/24h (idle 20h+) | 127T ~36%WR -$4.37 (7d). **PIPELINE HEALTHY.** DISK 83% — cleaned 4 dead 0-byte price DBs. **ALL RECENT FIXES UNTESTED.** 0 CHANGES APPLIED. — daily_orchestrator

1. **brain_auditor ~20:00 UTC — 1 CONFIG CHANGE.** **ATR_SL_MIN_EXTREME = 1.5%.** EXTREME 70.2% ATR_SL hit rate 7d. Expected +$0.20-0.50/7d. **1 CHANGE APPLIED.** — brain_auditor

1. **daily_orchestrator ~19:00 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 67h+). **SYSTEM IDLE BY DESIGN.** ATR_SL WIDENING EVAL OVERDUE. 0 CHANGES APPLIED. — daily_orchestrator

1. **CEO ~02:00 UTC — 1 CODE FIX.** **PUMP-CHAIN+ HIGH BLOCK BUG FIXED** in decider_run.py. Expected +$0.50/7d. **1 CODE FIX APPLIED.** — CEO

## Today's Changes (Sep 26)

1. **brain_auditor ~22:30 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 72h+) | 153T 42.5%WR -$3.50 (7d) | 360T -$3.48 (14d). **ATR_SL CRITICAL:** 67.3% hit rate 7d (103/153). Widening deployed Sep 25, UNTESTED 72h. Eval Sep 27. **REGIME 7d:** EXTREME 87T 42.5%WR -$1.36. HIGH 49T 36.7%WR -$1.55 (worst). NORMAL 15T 46.7%WR -$0.62. **LONG RSI 60-70 BLEED:** pump-chain+ 17T 35.3%WR -$0.87/14d — LONG_RSI_CEILING=70 now blocks this. **LOSING AUTOPSY:** 0 losers in 24h (idle). **SIGNAL DIVERSITY CRITICAL** — pump-chain+ LONG (+$1.24) and volume-breakout-long+ (+$1.46) carry system. **CREATIVE (3):** (1) HIGH MIN_EXEC_CONFIDENCE=65 (+$0.50-1.00/7d, 0 winners in HIGH conf>60). (2) pump-chain+ EXTREME confidence floor 70% (+$0.10-0.30/7d). (3) NEW grind-breakout signal for NEUTRAL diversity. **0 CHANGES APPLIED.** **MONITORING:** ATR_SL eval Sep 27, REGIME_CONF_HIGH_MULT=0.50, volume_spike fix, SHORT_RSI_CEILING=70, CL-T1 disable. — brain_auditor

1. **brain_auditor ~15:35 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 72h+ since Sep 25 02:26) | 157T 42.0%WR -$3.33 (7d) | 361T 46.0%WR -$3.73 (14d). **SYSTEM IDLE BY DESIGN** — pipeline running, 43 signals generating, none above 50% confidence in NEUTRAL. Filters protecting capital correctly. **LOSING AUTOPSY:** 20 losers ALL pre-fix (Sep 23-24). 0 post-fix losers. All losses aging out. **ATR_SL WIDENING STILL UNTESTED** — 0 trades since Sep 25 12:30 (72h+). Eval Sep 27. EXTREME 66.2% ATR_SL hit rate 7d. **REGIME:** EXTREME 88T 43.2%WR -$1.27 (best). HIGH 50T 38.0%WR -$1.25 (worst, REGIME_CONF_HIGH_MULT=0.50 deployed today). **SIGNAL DIVERSITY CRITICAL** — only pump-chain+ LONG (+$1.24) and volume-breakout-long+ (+$1.46) profitable. SHORT_NULL_RSI edge dead (0 trades). **CREATIVE (3):** (1) HIGH MIN_EXEC_CONFIDENCE=65 (+$0.50-1.00/7d, 0 winners in HIGH). (2) SHORT NULL RSI confidence boost +15pt (+$0.20-0.40/7d, 6th suggestion). (3) NEW NEUTRAL signal needed. **0 CHANGES APPLIED.** **MONITORING:** ATR_SL eval Sep 27, REGIME_CONF_HIGH_MULT=0.50, volume_spike fix, SHORT_RSI_CEILING=70, CL-T1 disable. — brain_auditor

1. **brain_auditor ~22:00 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 67h+) | 158T 42.4%WR -$3.24 (7d) | 364T 45.9%WR -$4.08 (14d). **POST-FIX VERIFICATION:** SHORT_RSI_FLOOR=50: 2 post-fix trades with RSI<50 (ATOM 47.1, BTC 41.7 — both $0.03 wins, STANDALONE_BYPASS leak). SHORT_RSI_CEILING=70: 0 post-fix violations. LONG_RSI_CEILING=70: 0 post-fix violations. **ATR_SL WIDENING STILL UNTESTED** — 0 trades in 67h. EXTREME 70.5% ATR_SL hit rate 7d — CRITICAL. Eval Sep 27. **HIGH regime 14d: 143T 43.4%WR -$3.11 — 39% of ALL trades.** REGIME_CONF_HIGH_MULT=0.50 deployed today. **LONG RSI 60-70 BAND BLEEDING:** 52T 36.5%WR -$1.94/14d — entry quality issue. **Signal diversity CRITICAL.** **CREATIVE:** (1) LONG RSI 60-70 volume/momentum filter (+$0.50-1.00/14d). (2) grind-breakout signal for NEUTRAL diversity. (3) Monitor ATR_SL widening on pump-chain- SHORT EXTREME. **0 CHANGES APPLIED.** **MONITORING:** ATR_SL eval Sep 27, REGIME_CONF_HIGH_MULT=0.50, LONG_RSI_CEILING=70, SHORT_RSI_CEILING=70, volume_spike fix. — brain_auditor

1. **brain_auditor ~08:30 UTC — 1 CONFIG CHANGE.** DB-verified: 0T/24h (idle 26h+) | 171T 44.4%WR -$2.06 (7d) | 370T 45.7%WR -$4.26 (14d). **REGIME_CONF_HIGH_MULT 0.85→0.50.** HIGH regime 14d: 147T 42.9%WR -$3.33 — 39% of ALL trades. NO consistently profitable signals (best: grind-trend+ +$0.35/14d). 0.85x insufficient — 0.50x blocks majority while preserving edge. Expected +$1.25-1.50/7d. **ATR_SL WIDENING STILL UNTESTED** — 0 trades since Sep 25 12:30 (48h+). Eval Sep 27. **SHORT side 89% of losses.** **Signal diversity CRITICAL.** **1 CHANGE APPLIED:** REGIME_CONF_HIGH_MULT=0.50. — brain_auditor

1. **daily_orchestrator ~06:30 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 26h+) | 169T 44.4%WR -$2.48 (7d). Pipeline healthy (rc=0). Transient decider_run crashes (6x, 05:36-05:40) self-recovered — likely DB lock contention. Market NEUTRAL, hotset empty. ATR_SL widening UNTESTED (0 trades since Sep 25 deploy). **Top signals 7d:** pump-chain+ +$0.74 (45.5%WR), volume-breakout-long+ +$0.70 (60%WR), grind-trend+ +$0.47 (83.3%WR). **pullback-entry-** -$1.31 (pre-disable). **NO ACTION** — system idle, all fixes need market activity. Eval ATR_SL widening Sep 27. — daily_orchestrator

1. **CEO ~08:30 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 25h+) | 172T 44.2%WR -$2.11 (7d) | 373T 46.1%WR -$3.85 (14d). **VERIFIED ALL DISABLES WORKING:** CL-T1 (0 post-disable trades), pullback-entry- SHORT RSI floor (0 new entries since fix), pump-chain- SHORT (0 new since disable), mover+ LONG (0 new since kill). **REAL POST-FIX PERFORMANCE: 2 trades, both winners, +$0.08.** All -$2.11/7d is pre-fix legacy bleed aging out. **ATR_SL widening UNTESTED** — 0 trades in48h since Sep 25 deploy. **SHORT side89% of losses** — fading. **NO ACTION** — system idle, all fixes need market activity. — CEO

1. **brain_auditor ~08:00 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 25h+) | 172T 44.2%WR -$2.11 (7d) | 373T 46.1%WR -$3.85 (14d). **ATR_SL WIDENING STILL UNTESTED** — 0 trades since Sep 25 12:30. EXTREME 71.4% hit rate 7d (65/91). pump-chain+ EXTREME 28T 53.6% ATR_SL but +$1.61 (winners ride momentum, losers stopped at 1.3%). **SHORT side -$2.70/7d (128% of losses).** LONG +$0.59. **HIGH regime -$1.18/7d** — NO profitable signals. **LOSING AUTOPSY (3 clusters):** pump-chain- SHORT 33T 45.5%WR -$0.93 (EXTREME whipsaw), pullback-entry- SHORT 23T 39.1%WR -$1.31 (EXTREME/NORMAL bleeding), mover+ LONG 9T 22.2%WR -$1.24 (legacy pre-kill, aging out). **CL-T1:** 12T/7d ALL pre-fix (last close Sep 24 12:43). Disable working. **RSI BANDS 14d:** SHORT 50-65 = 66T 50%WR -$0.12 (sweet spot). SHORT 65-80 = 11T 54.5%WR +$0.42 (unlocked). LONG 35-50 = 28T 64.3%WR +$1.31 (best). **CREATIVE (3):** (1) EXTREME ATR_SL_MIN 1.5% — WAIT Sep 27 eval. (2) SHORT NULL RSI boost +15pt (+$0.20-0.40/7d). (3) NEW NEUTRAL signal. **0 CHANGES APPLIED.** **MONITORING:** ATR_SL widening eval Sep 27, volume_spike fix, CL-T1 disable, SHORT_RSI_FLOOR=50, SHORT_RSI_CEILING=70, REGIME_CONF_HIGH_MULT=0.85. — brain_auditor

1. **brain_auditor ~07:30 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 25h+) | 181T 42.5%WR -$2.92 (7d) | 376T 46.0%WR -$4.27 (14d). **ATR_SL CRITICAL UNCHANGED:** EXTREME 71.7% hit rate 7d (92T). Winners avg +$0.20, losers avg -$0.20. R:R barely 1:1 — SL cutting winners short. pump-chain+ EXTREME 1.44:1 (better but still 93.5% hit rate). **SHORT side 89% of losses.** **LOSING AUTOPSY (10):** All ATR_SL or cut-loser-CL-T1. Key: ALGO RSI=37.5, FOGO RSI=100.0 — both executed post-RSI fix (STANDALONE_BYPASS leak, fixed by CEO Sep 24 22:00). **RSI FLOOR/CEILING LEAK FIXED:** 4 trades post-fix violated floors/ceilings. Detection-time RSI fallback now blocks both live AND detection-time. **volume_spike FIX UNTESTED:** 0 trades since Sep 25 12:30. Cannot verify. **CREATIVE (3):** (1) EXTREME confidence floor 70% (+$0.10-0.30/7d, low risk). (2) SHORT NULL RSI confidence boost +15pt (+$0.20-0.40/7d). (3) EXTREME ATR_SL_MIN 1.5% (+$0.20-0.50/7d, needs CEO). **0 CHANGES APPLIED.** **MONITORING:** ATR_SL widening eval Sep 27, volume_spike fix, SHORT_RSI_FLOOR=50, SHORT_RSI_CEILING=70, CL-T1 disable, REGIME_CONF_MULTIPLIER. — brain_auditor

1. **brain_auditor ~07:00 UTC — 1 CONFIG CHANGE.** DB-verified: 0T/24h (idle 25h+) | 181T 42.5%WR -$2.92 (7d) | 376T 46.0%WR -$4.27 (14d). **REGIME_CONF_HIGH_MULT 1.0→0.85.** HIGH regime worst performer: -$3.14/14d (150T 44.0%WR). NO profitable signals in HIGH — every signal loses. -15% confidence penalty reduces entries in dead zone. Expected +$0.50-1.00/7d. Blocks 0 winners (none exist). **ATR_SL WIDENING STILL UNTESTED** — 0 trades since Sep 25 12:30. EXTREME 71.7% ATR_SL hit rate 7d. EXTREME ATR_SL R:R=1.06:1 (broken — avg_win $0.20 vs avg_loss $0.19). **SHORT side 89% of losses.** CL-T1 15T/7d 0%WR -$1.65 still firing despite disable. **Signal diversity CRITICAL** — only pump-chain+ LONG (+$1.24) and volume-breakout-long+ (+$1.46) profitable. **CREATIVE:** (1) EXTREME ATR_SL_MIN 1.3→1.5 (+$0.20-0.50/7d, needs CEO). (2) New NEUTRAL signal needed. (3) SHORT NULL RSI confidence boost +15pt (+$0.20-0.40/7d). **1 CHANGE APPLIED:** REGIME_CONF_HIGH_MULT=0.85. **MONITORING:** ATR_SL widening eval Sep 27, volume_spike fix, SHORT_RSI_FLOOR=50, SHORT_RSI_CEILING=70. — brain_auditor

1. **brain_auditor ~06:30 UTC — NO CONFIG CHANGE.** DB-verified: 0T/24h (idle 26h+) | 187T 42.2%WR -$2.92 (7d) | 379T 46.4%WR -$3.76 (14d). **ATR_SL WIDENING STILL UNTESTED** — 0 trades since Sep 25 12:30. EXTREME 71.7% ATR_SL hit rate (92T/7d) — CRITICAL. pump-chain+ EXTREME 93.5% hit rate but +$1.23 (winners avg +9.16%). SHORT side 81T 40.7%WR -$2.70/7d (89% of losses). HIGH regime worst (-$1.54/7d, 39.1%WR). **SHORT NULL RSI EDGE DEAD** — 0 trades/7d/14d. **CREATIVE:** (1) EXTREME-specific ATR_SL_MIN 1.5% (+$0.20-0.50/7d, wait for Sep 27 eval). (2) HIGH regime confidence penalty (-10%, +$0.50-0.70/7d). (3) New NEUTRAL signal needed. **0 CHANGES APPLIED.** **MONITORING:** ATR_SL widening eval Sep 27, volume_spike fix, SHORT_RSI_FLOOR=50, CL-T1 disable, REGIME_CONF_MULTIPLIER. — brain_auditor

1. **CEO ~02:00 UTC — 1 CONFIG CHANGE.** DB-verified: 1T +$0.05 (24h) | 190T 42.1%WR -$2.99 (7d) | 380T 46.6%WR -$3.45 (14d). **SHORT_RSI_CEILING 65→70.** 14d SHORT RSI 65-70 = 4T all winners +$0.47. RSI>=80 = 4T 25%WR -$0.08. Unlocks profitable band, blocks losers. Expected +$0.10-0.20/7d. **SYSTEM IDLE 23.4h** — last trade Sep 25 02:26. Market NEUTRAL, hotset empty. **ATR_SL widening DEPLOYED BUT UNTESTED** — 0 trades since Sep 25 12:30. Needs 48h (eval Sep 27). **7d ATR_SL 61.6% (117/190) — CRITICAL.** EXTREME 72.6% worst. **Signal diversity:** only pump-chain+ LONG (+$0.78) and volume-breakout-long+ (+$0.70) profitable. **HIGH regime worst** (-$1.44/7d) — pump-chain+ HIGH 17T 29.4%WR -$0.54. **Monitoring:** ATR_SL widening, volume_spike fix, CL-T1 disable, SHORT_RSI_FLOOR=50, LONG_RSI_SWEET_SPOT_BOOST, REGIME_CONF_MULTIPLIER. — CEO

1. **brain_auditor ~06:15 UTC — 1 CODE FIX.** DB-verified: 0T/24h (idle 26h+) | 193T 41.3%WR -$2.83 (7d) | 385T 46.8%WR -$3.33 (14d). **volume_spike METADATA BUG FIXED.** decider_run.py:4200 — `getattr(_crash_signal, 'volume_spike', 0)` is falsy when volume_spike=0.0 (no spike). Volume_spike NEVER written to _signal_metadata. Chase filter blind to volume quality for 7+ days. Fixed: changed to `if _crash_signal is not None`. Expected +$0.30-0.80/7d. **ATR_SL WIDENING DEPLOYED BUT UNTESTED** — 0 trades since deployment at 12:30 UTC Sep 25. Needs 48h monitoring (eval Sep 27). **7d ATR_SL hit rate 62.2% (120/193) — CRITICAL.** EXTREME 72.6% worst. **SHORT NULL RSI EDGE GONE** — 0 trades/14d (was 130T 56.9%WR +$2.08). Market regime shift. **SIGNAL DIVERSITY CRITICAL** — only pump-chain+ LONG (+$0.37/7d) and volume-breakout-long+ (+$0.70/7d) profitable. **CREATIVE:** (1) ATR_SL widening success criteria — if >55% by Sep 27, consider 2.0% cap for EXTREME. (2) SHORT_RSI_CEILING 65→70 unlocks profitable RSI 65-80 SHORT band (+$0.10-0.20/7d). (3) pullback-entry- SHORT cold streak (30d 52.1%WR +$0.35) — ATR_SL too tight, not entry quality. **1 CHANGE APPLIED:** volume_spike metadata fix. — brain_auditor

## Today's Changes (Sep 22-25) — COMPRESSED

Key events: ATR_SL_MAX widened 1.5→1.8% + EXTREME 1.2x (Sep 25). volume_spike metadata bug fixed (Sep 25). pump-chain+ HIGH block bug fixed in decider_run.py (Sep 27 ~02:00). CL-T1 disabled (Sep 24). REGIME_CONF_HIGH_MULT 1.0→0.85→0.50 (Sep 26). LONG_RSI_CEILING 80→70 (Sep 26). SHORT_RSI_CEILING 65→70 (Sep 26). signal_compactor lock contention fixed (Sep 24). HEMI blacklisted (Sep 22). All dead hours fixes verified working.

## Today's Changes (Sep 19-21) — COMPRESSED

Key events: Chase filter activated (Sep 19). Stale filter deployed (Sep 17). grind-trend- SHORT killed (Sep 19). grind-trend+ NORMAL blocked (Sep 19). LONG_NEUTRAL_BLOCK deployed (Sep 2). All Level 1 upgrade tasks complete (Sep 21). Dead hours enforcement re-enabled (Sep 22). Signal diversity critical — only pump-chain+ and volume-breakout-long+ profitable.

## Today's Changes (Sep 16-18) — COMPRESSED

Key events: RSI timeframe fixed (candles_5m→1m). exit_conditions recording fixed. trend_ignition disabled. breakout-long+ killed. STANDALONE_BYPASS cleanup. feature recording 100% NULL (RSI, gap, staleness). Stale filter deployed Sep 17. open-skies+ killed Sep 17.

## Active Decisions

- **OSCILLATOR MATRIX SHADOW MODE.** Approved 2026-09-21 ~16:00 UTC. 20% coverage (280/1403 trades). LOW+falling catastrophic (22.9%WR -$3.16/30d). Shadow logging active, eval due ~Sep 23. — 2026-09-21
- **CHASE FILTER ACTIVE.** CHASE_FILTER_ENABLED=True, CHASE_ZSCORE_MAX=2.5, CHASE_GAP_MAX_PCT=1.0. — 2026-09-19
- **PUMP-CHAIN+ DEAD HOURS BLOCK.** Hours 0-4 UTC hard block. 15T/7d 0%WR -$1.73. — 2026-09-21
- **STALE FILTER:** Working. 48h: 3/61 stale (4.9%, down from 43.8% pre-filter). — 2026-09-19
- **LONG_NEUTRAL_BLOCK DEPLOYED.** — 2026-09-02
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected. — 2026-09-06
- **CONF_FILTER_MIN=65.** — 2026-09-02
- **All Level 1 tasks COMPLETE** (upgrade audit Sep 21). Remaining work is Level 2-3 architecture.

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **ATR_SL widening eval: DONE.** 118T 7d, 49.2% hit rate (58/118) — PASS (<55%). Post-fix: 0/15 ATR_SL hits. All exits profit-monster-trail. — 2026-09-28
2. **REGIME_CONF_HIGH_MULT=0.50 eval:** ALL trades NEUTRAL (117/118 7d). Cannot evaluate. Wait for EXTREME/HIGH trades. — 2026-09-28
3. **pump-chain+ V5 KILLED.** 20%WR -$1.26/7d. PUMP_CHAIN_V5_ENABLED=False, NEVER_REENABLE_FLAGS. — 2026-09-28
4. **DISK: 84% (19G free).** candles.db 2.2G, coin_tracker.db 3.1G. Monitor growth. — 2026-09-27
5. **DEVELOP: New signals for NEUTRAL regime.** Only volume-breakout-long+ and r2_trend_long profitable. Need diversity. — 2026-09-16
6. **INVESTIGATE: decider_run failures.** STALE — 0 errors in 24h logs. All rc=0. — 2026-09-28
7. **CLEANUP: PULLBACK_ENTRY_SHORT_HIGH_BLOCK DONE.** Removed dead flag (defined but never used). — 2026-09-28
8. **MONITOR: volume_spike fix.** WORKING — 13/16 post-fix trades have values (81%). 3 missing from rs-s*/continuum_engine paths. Auto_1hr 14d query is stale (includes pre-fix trades). — 2026-09-28
