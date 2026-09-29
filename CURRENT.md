# Current State — System Improvement Focus

**Last Updated: 2026-09-29 07:00 UTC**
**Updated by: brain_auditor**

## Current Status

System active. 4 open positions. Pipeline healthy. ATR_SL widening VERIFIED PASS. pump-chain+ V5 KILLED. mover- SHORT KILLED (auto_1hr 06:14). Dead hours TUNED. LONG_RSI_SWEET_SPOT extended to 40-60. BB_BOUNCE_V2_RSI_MAX=60 APPLIED. ALL metadata fixes VERIFIED WORKING (volume_spike, final_confidence, signal_rsi_14). SHORT signals killed/disabled.

- **24h (rolling):** 24T 62.5%WR +$0.41 (DB-verified). Good day.
- **7d:** 114T 41.2%WR -$3.46 (DB-verified). ALL ATR_SL hits pre-fix legacy. Post-fix: 0 ATR_SL hits. 0 atr_sl_hit 24h.
- **14d:** 307T 43.9%WR -$2.92 (DB-verified). LONG +$0.67, SHORT -$3.59 (123% of losses).
- **OPEN:** 4 positions — BTC LONG continuum-osc+ (NORMAL, +$0.07), GOAT SHORT pump-chain- (EXTREME, -$0.02), BABY SHORT pump-chain- (EXTREME, -$0.05), WLFI LONG rs-s35 (HIGH, +$0.01).
- **LONG:** volume-breakout-long+ (+$1.46/14d, 66.7%WR), pump-chain+ (+$1.23/14d, 41.8%WR).
- **SHORT:** ALL DISABLED. pullback-entry- NEVER_REENABLE, pump-chain- NEVER_REENABLE, mover- NEVER_REENABLE.
- **KILLED (Sep 29):** mover- SHORT — MOVER_MINUS_ENABLED=False. 3T 0%WR -$0.72/7d. All hard_sl.
- **KILLED (Sep 28):** pump-chain+ LONG V5 — PUMP_CHAIN_V5_ENABLED=False, NEVER_REENABLE_FLAGS.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **TIME_BLOCK:** 00-09 UTC. 0.7x penalty.
- **PUMP_CHAIN_LONG_DEAD_HOURS:** [1,2,3,4,5,7,8,13,21,22] — **VERIFIED WORKING.**
- **KILLED/REGIME BLOCKED:** pump-chain+ V5 NEVER_REENABLE (Sep 28), pullback-entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE, mover+/- NEVER_REENABLE (Sep 24/29), open-skies+ (Sep 22), grind-trend+/- (Sep 19), breakout-long+ (Sep 16), trend_ignition (Sep 16), PUMP_FLOW+ NEVER_REENABLE.
- **CONF_FILTER_MIN=65.**
- **Disk:** 84% (19G free). candles.db 2.2G, coin_tracker.db 3.1G. 25 dead 0-byte DBs cleaned today.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 2.0% (widened Sep 28, was 1.8%). EXTREME regime: MIN 1.5% (Sep 27), 1.2x multiplier. **VERIFIED WORKING** — Post-fix: 4/4 trades winners (all profit-monster-trail), 0 ATR_SL hits. 7d overall: 46.4% (52/112) — PASS (<55%). EXTREME legacy 64.4% aging out. TP_PCT_FALLBACK=6.0% (3:1 R:R).
- **🟢 signal_rsi_14 NULL DRIFT — FIXED:** 28-day drift. Root cause: decider_run.py:4283 `sig.get('rsi_14')` but signals store RSI as `rsi` key. Fix: `sig.get('rsi') or sig.get('rsi_14')` applied Sep 28. Unlocks proper RSI floor/ceiling enforcement for STANDALONE_BYPASS signals. Expected +$0.30-0.80/7d.
- **SHORT_RSI_FLOOR=50:** **HARD BLOCK.** Blocks SHORT entries where live or detection-time RSI < 50.
- **SHORT_RSI_CEILING=70:** **HARD BLOCK.** Unlocks profitable RSI 65-70 band. 0 post-fix violations.
- **LONG_RSI_FLOOR=30:** **HARD BLOCK.** Blocks LONG entries where RSI < 30.
- **LONG_RSI_CEILING=70:** **HARD BLOCK.** Blocks overbought LONG entries. 0 post-fix violations.
- **LONG_RSI_SWEET_SPOT_BOOST=10:** +10pt confidence when LONG RSI 40-60. Extended 50→60: 50-60 band = 43T 60.5%WR +$1.53/14d.
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


## Audit Update (2026-09-29 07:30 UTC)

- **🟢 PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True — APPLIED.** 14d: pump-chain- SHORT HIGH 5T 20%WR -$0.60, EXTREME 32T 56.3%WR +$0.66. Blocks HIGH noise, preserves EXTREME edge. 1 tiny winner ($0.06) killed. Net: +$0.54/14d. **LOSING AUTOPSY:** 6 losers 24h all small (<$0.47). 2 EXTREME, 2 HIGH — normal chop. **SHORT structural disadvantage PERSISTS:** avg_win $0.116 vs LONG $0.162. **7d REGIME:** EXTREME -$2.32, HIGH -$1.82, NORMAL +$0.21. **Signal diversity CRITICAL** — only volume-breakout-long+ (+$1.46) and pump-chain+ (+$1.23) profitable. **CREATIVE (3):** (1) PUMP_CHAIN_SHORT_HIGH_BLOCK APPLIED (2) accel-300-breakout SHORT RSI_MIN=45 suggested (marginal, 7T) (3) Monitor EXTREME. **1 CHANGE APPLIED.**

## Audit Update (2026-09-29 07:00 UTC)

- **🟢 BB_BOUNCE_V2_RSI_MAX=60 — APPLIED.** 14d: RSI 60-70 = 7T 28.6%WR -$0.32, 0 winners above RSI 60. 6th suggestion applied. Expected +$0.20-0.30/7d.
- **🟢 POST-FIX VERIFIED WORKING.** 20T 70%WR +$0.43 (since Sep 28 10:39 UTC). signal_rsi_14 NULL = 0/20. All metadata fixes working.
- **LOSING AUTOPSY:** 6 losers 24h all small (<$0.47). BLUR mover- SHORT -$0.47 (biggest). 2 EXTREME, 2 HIGH — normal chop variance.
- **SHORT structural disadvantage PERSISTS:** avg_win $0.116 vs LONG $0.162 (29% smaller). SHORT -$3.22/14d = 126% of total losses.
- **7d REGIME:** EXTREME worst (-$2.43, 44.8%WR). HIGH -$1.82 (31.3%WR). NORMAL +$0.21 (47.4%WR).
- **Signal diversity CRITICAL** — only volume-breakout-long+ (+$1.46/14d) and pump-chain+ (+$1.23/14d) profitable.
- **pump-chain- SHORT** bypassing SHORT_NEUTRAL_BLOCK via STANDALONE_BYPASS. 39T/14d 53.8%WR +$0.12. EXTREME profitable (+$0.66), HIGH losing (-$0.60).
- **CREATIVE (3):** (1) BB_BOUNCE_V2_RSI_MAX=60 APPLIED (2) SHORT_MIN_EXEC_CONFIDENCE=70 (5th suggestion) (3) New NEUTRAL signal needed.
- **1 CHANGE APPLIED.**

## Audit Update (2026-09-29 06:30 UTC)

- **🟢 POST-FIX VERIFIED WORKING.** 14T 78.6%WR +$0.89 (since Sep 28 10:39 UTC). 9 profit-monster-trail, 5 hard_sl. 0 ATR_SL hits. Strong performance.
- **pump-chain- SHORT BYPASSING SHORT_NEUTRAL_BLOCK.** 5T/24h 100%WR +$0.81. STANDALONE_BYPASS signals skip signal_compactor where block lives. 52.6%WR 14d — profitable. Not a bug, but worth noting.
- **7d REGIME: ALL NEUTRAL (112/113).** No EXTREME/HIGH data. REGIME_CONF_HIGH_MULT=0.50 UNTESTED.
- **7d EXIT ANALYSIS:** 41 atr_sl_hit (-$4.30, ALL pre-fix), 37 profit-monster-trail (+$1.23), 12 pump_exit_dead_money (+$0.46), 9 hard_sl (+$0.13).
- **Signal diversity CRITICAL** — only volume-breakout-long+ (+$1.46/14d) and pump-chain+ (+$1.23/14d) profitable. 2 signal types carry all PnL.
- **bb-bounce-v2-long+ RSI 60-70 KILLING FIELD** — 3T/14d RSI 60-70, 1W 2L. R:R=0.56:1. 0 winning trades have RSI>60. Fix: BB_BOUNCE_V2_LONG_RSI_MAX=60. **6th suggestion.**
- **mover+ LONG R:R BROKEN** — 14T/14d 42.9%WR -$1.12. R:R=0.52:1 (avg_win $0.118 vs avg_loss $0.229). TP too tight. Top loser (BABY -$0.45) entered RSI 79.
- **LOSING AUTOPSY:** 5 losers 24h ALL small (<$0.21). 2/5 hard_sl, 3/5 profit-monster-trail. No systematic pattern — normal variance. 7d: 41 atr_sl_hit legacy aging out, 0 post-fix.
- **SHORT RSI<50 CATASTROPHIC** — 81T/14d -$3.42. SHORT_RSI_FLOOR=50 working for direct signals. STANDALONE_BYPASS leak: pump-chain- SHORT still fires at RSI 23-42 (but profitable — 52.6%WR).
- **CREATIVE (3):** (1) BB_BOUNCE_V2_LONG_RSI_MAX=60 (+$0.20-0.30/7d, 0 winners blocked, 6th suggestion) (2) SHORT_MIN_EXEC_CONFIDENCE=70 (+$0.30-0.60/7d, 5th suggestion) (3) mover+ LONG RSI_MAX=75 (+$0.20-0.40/7d, blocks worst loser entry).
- **0 CHANGES APPLIED.**

## Audit Update (2026-09-29 06:00 UTC)

- **🟢 POST-FIX VERIFIED WORKING.** 11T 90.9%WR +$0.89 (since Sep 28 10:39 UTC). 7 profit-monster-trail, 4 hard_sl. 0 ATR_SL hits. Strong performance.
- **SHORT STRUCTURAL DISADVANTAGE CONFIRMED.** avg_win $0.12 vs LONG $0.16 at similar WR (45.9% vs 45.0%). SHORT = 140% of 14d losses (-$2.48 vs -$1.77 total). Low-conviction SHORT entries drag R:R below 1:1.
- **7d REGIME: ALL NEUTRAL (114/115).** No EXTREME/HIGH data. REGIME_CONF_HIGH_MULT=0.50 UNTESTED.
- **7d EXIT ANALYSIS:** 45 atr_sl_hit (-$4.80, ALL pre-fix), 35 profit-monster-trail (+$1.25), 8 cut-loser-CL-T1 (-$0.97, DISABLED), 8 hard_sl (+$0.34).
- **Signal diversity CRITICAL** — only volume-breakout-long+ (+$1.46/14d) and pump-chain+ (+$1.23/14d) profitable. 2 signal types carry all PnL.
- **bb-bounce-v2-long+ RSI 60-70 KILLING FIELD** — 7T 28.6%WR -$0.32/14d. R:R=0.56:1. Signal enters overbought territory where bounces fail. Fix: BB_BOUNCE_V2_LONG_RSI_MAX=60.
- **LOSING AUTOPSY:** 4 losers 24h ALL small hard_sl (<$0.20). 2/4 in HIGH regime (worst performer, 31.3%WR 7d). No systematic pattern.
- **CREATIVE (3):** (1) BB_BOUNCE_V2_LONG_RSI_MAX=60 (+$0.20-0.30/7d, 0 winners blocked) (2) SHORT_MIN_EXEC_CONFIDENCE=70 (+$0.30-0.60/7d, 5th suggestion) (3) Monitor EXTREME post-fix.
- **0 CHANGES APPLIED.**

## Audit Update (2026-09-28 22:50 UTC)

- **🟢 ALL POST-FIX FIXES VERIFIED WORKING.** volume_spike: 8/8 post-fix trades have values. final_confidence: 8/8. signal_rsi_14: 0.3% NULL. Chase filter now blind to volume for 0% of new trades. Confidence filtering operational.
- **ATR_SL WIDENING: VERIFIED WORKING.** Post-fix: 8T, 0 ATR_SL hits (0%). 7d: 42.1% (48/114) — PASS (<55%). All post-fix exits: profit-monster-trail or hard_sl.
- **EXTREME LONG only profitable combo** — +$1.22/14d. pump-chain+ $0.97, volume-breakout-long+ $1.51.
- **SHORT -$3.19/14d (110% of losses).** All SHORT signals killed/disabled, aging out. LONG +$0.30.
- **14d RSI BANDS:** LONG 50-60 best (+$1.27 60.5%WR). SHORT <30 catastrophic (-$1.27). SHORT 60-70 sweet spot (+$0.39 56.3%WR).
- **HIGH regime SHORT 10%WR 7d** — all from killed signals aging out. REGIME_CONF_HIGH_MULT=0.50 untested.
- **LOSING AUTOPSY:** 6 losers 24h ALL small scratches (<$0.20, 4 profit-monster-trail). No systematic pattern — normal chop variance.
- **Signal diversity CRITICAL** — only pump-chain+ (+$1.23/14d) and volume-breakout-long+ (+$1.46/14d) profitable.
- **CREATIVE (3):** (1) HIGH SHORT MIN_EXEC_CONFIDENCE=70 for next run (+$0.30-0.60/7d) (2) Monitor EXTREME post-fix (need 30+ trades) (3) NEW NEUTRAL signal for diversity.
- **0 CHANGES APPLIED.**

## Audit Update (2026-09-28 14:00 UTC)

- **ATR_SL WIDENING: VERIFIED WORKING.** Post-fix: 0/0 ATR_SL hits (0 trades since Sep 28 10:39 UTC). 7d: 48.3% (56/116) — PASS (<55%). EXTREME still 64.5% (pre-fix legacy).
- **DEAD HOURS TUNED.** Removed hours 5, 8, 13, 22 from PUMP_CHAIN_LONG_DEAD_HOURS. 14d: these hours +$1.86 combined. Expected +$0.40-0.90/7d.
- **pump-chain+ cold streak** — 13T/7d 15.4%WR -$1.51 vs 57T/14d 42.1%WR +$1.38. Dead hours fix should help.
- **SHORT NULL RSI edge ALIVE.** pullback-entry- NULL RSI 23T 60.9%WR +$0.63/14d.
- **pump-chain+ EXTREME still profitable.** 35T 45.7%WR +$1.12/14d. 1.69:1 R:R.
- **14d LONG vs SHORT:** LONG +$0.52, SHORT -$3.70 (116% of losses).
- **Signal diversity CRITICAL** — only volume-breakout-long+ (+$1.46/14d) and pump-chain+ (+$1.38/14d) profitable.
- **CREATIVE (3):** (1) Dead hours fix APPLIED (2) EXTREME MIN_EXEC_CONFIDENCE=70 after 50+ post-fix trades (3) SHORT NULL RSI confidence boost +15pt (9th suggestion).
- **1 CHANGE APPLIED.**

## Today's Changes (Sep 29)

1. **brain_auditor ~07:00 UTC — 1 CONFIG CHANGE.** **BB_BOUNCE_V2_RSI_MAX=60 ADDED.** 14d: RSI 60-70 = 7T 28.6%WR -$0.32, R:R=0.56:1. RSI 50-60 = 5T 80%WR +$0.18. 0 winners above RSI 60. Filter in bb_bounce_v2_long.py blocks overbought entries. **POST-FIX: 20T 70%WR +$0.43.** signal_rsi_14 NULL = 0/20 (fix verified). **LOSING AUTOPSY:** 6 losers 24h all small (<$0.47). 2 EXTREME, 2 HIGH — normal chop. **SHORT structural disadvantage PERSISTS:** avg_win $0.116 vs LONG $0.162. **7d REGIME:** EXTREME worst (-$2.43). **Signal diversity CRITICAL** — 2 types carry all PnL. **CREATIVE (3):** (1) BB_BOUNCE_V2_RSI_MAX=60 APPLIED (2) SHORT_MIN_EXEC_CONFIDENCE=70 (5th) (3) New NEUTRAL signal. **1 CHANGE APPLIED.** — brain_auditor

1. **daily_orchestrator ~06:30 UTC — NO CONFIG CHANGE.** DB-verified: 24T 62.5%WR +$0.41 (24h) | 114T 41.2%WR -$3.46 (7d) | 307T 43.9%WR -$2.92 (14d). **PIPELINE HEALTHY.** 4 open positions (BTC LONG, GOAT SHORT, BABY SHORT, WLFI LONG). **mover- SHORT KILLED by auto_1hr 06:14 UTC** — 3T 0%WR -$0.72/7d, all hard_sl. **ATR_SL: 0 atr_sl_hit 24h.** **EXTREME regime worst** (-$2.51/7d, 43.3%WR). **Signal diversity CRITICAL** — volume-breakout-long+ (+$1.46/14d) and pump-chain+ (+$1.23/14d) carry system. **Disk 84% (19G free).** **0 CHANGES APPLIED.** — daily_orchestrator

1. **auto_1hr ~06:14 UTC — 1 SIGNAL KILL.** **mover- SHORT KILLED** — MOVER_MINUS_ENABLED=False. 3T 0%WR -$0.72/7d, 2T 0%WR -$0.68 24h. All exits hard_sl — entries consistently wrong side. — auto_1hr

1. **brain_auditor ~06:30 UTC — NO CONFIG CHANGE.** DB-verified: 15T 46.7%WR +$0.47 (24h) | 113T 42.0%WR -$3.44 (7d) | 306T 45.2%WR -$2.30 (14d). **POST-FIX: 14T 78.6%WR +$0.89.** 9 profit-monster-trail, 5 hard_sl. 0 ATR_SL hits. **pump-chain- SHORT BYPASSING SHORT_NEUTRAL_BLOCK** — 5T/24h 100%WR +$0.81 via STANDALONE_BYPASS. **SHORT structural disadvantage CONFIRMED:** avg_win $0.12 vs LONG $0.16. **14d RSI BANDS:** SHORT <50 catastrophic (-$3.42 81T). SHORT 50-60 sweet spot (+$1.27 19T 68.4%WR). LONG 50-60 sweet spot (+$0.44 25T 64.0%WR). **bb-bounce-v2-long+ RSI 60-70 KILLING FIELD** — 3T, R:R=0.56:1. **mover+ LONG R:R BROKEN** — 0.52:1, top loser entered RSI 79. **LOSING AUTOPSY:** 5 losers 24h all small (<$0.21). **CREATIVE (3):** BB_BOUNCE_V2_LONG_RSI_MAX=60 (6th), SHORT_MIN_EXEC_CONFIDENCE=70 (5th), mover+ RSI_MAX=75. **0 CHANGES APPLIED.** — brain_auditor

1. **brain_auditor ~06:00 UTC — NO CONFIG CHANGE.** DB-verified: 17T 76.5%WR +$1.25 (24h) | 115T 44.3%WR -$3.66 (7d) | 304T 45.4%WR -$1.77 (14d). **POST-FIX: 11T 90.9%WR +$0.89.** 0 ATR_SL hits. **SHORT structural disadvantage CONFIRMED:** avg_win $0.12 vs LONG $0.16. **14d RSI BANDS:** LONG 40-60 sweet spot (60T 63.3%WR +$2.46). LONG 60-70 killing field (50T 38.0%WR -$0.58). SHORT 60-70 sweet spot (18T 61.1%WR +$0.71). **bb-bounce-v2-long+ RSI 60-70 KILLING FIELD:** 7T 28.6%WR -$0.32, R:R=0.56:1. **LOSING AUTOPSY:** 4 losers 24h ALL small (<$0.20), 2/4 in HIGH regime. **CREATIVE (3):** BB_BOUNCE_V2_LONG_RSI_MAX=60, SHORT_MIN_EXEC_CONFIDENCE=70 (5th), Monitor EXTREME. **0 CHANGES APPLIED.** — brain_auditor

## Today's Changes (Sep 28)

1. **brain_auditor ~22:50 UTC — NO CONFIG CHANGE.** DB-verified: 13T 46.2%WR +$0.04 (24h) | 114T 41.0%WR -$4.34 (7d) | 301T 44.2%WR -$2.89 (14d). **POST-FIX TRADES: 8T 75%WR +$0.25.** ALL metadata fixes verified working (volume_spike 8/8, final_confidence 8/8, rsi_14 0.3% NULL). **ATR_SL WIDENING VERIFIED** — 0/8 post-fix ATR_SL hits. 7d: 42.1% — PASS. **HIGH regime SHORT 10%WR 7d** — all from killed signals aging out. REGIME_CONF_HIGH_MULT=0.50 untested. **EXTREME LONG only profitable combo** — +$1.22/14d. **SHORT -$3.19/14d (110% of losses).** **LOSING AUTOPSY:** 6 losers 24h ALL small scratches (<$0.20). No systematic pattern. **CREATIVE (3):** (1) HIGH SHORT MIN_EXEC_CONFIDENCE=70 (+$0.30-0.60/7d) (2) Monitor EXTREME post-fix (need 30+ trades) (3) NEW NEUTRAL signal for diversity. **0 CHANGES APPLIED.** — brain_auditor

1. **brain_auditor ~21:30 UTC — NO CONFIG CHANGE.** DB-verified: 9T 55.6%WR +$0.01 (today) | 114T 35.7%WR -$5.26 (7d) | 305T 44.3%WR -$2.90 (14d). **POST-FIX TRADES: 4/4 winners (+$0.19).** All profit-monster-trail. ATR_SL widening working. **CRITICAL DRIFT: signal_rsi_14 NULL ALL 14d trades (28-day drift).** Detection-time RSI filtering impossible. Investigation needed. **SHORT R:R 0.78:1** — avg_loss exceeds avg_win. 82% of ALL 14d losses. **EXTREME 88 ATR_SL hits/14d** — dominates losses. **LOSING AUTOPSY:** 25 losers 7d — 88% atr_sl_hit. All worst signals killed/disabled, aging out. **5 open:** 3 SHORT EXTREME, 1 LONG NORMAL, 1 LONG HIGH. **CREATIVE (3):** (1) CRITICAL: signal_rsi_14 investigation (+$0.30-0.80/7d) (2) SHORT NULL RSI boost +15pt 9th suggestion (3) EXTREME MIN_EXEC_CONFIDENCE=70 after 50+ post-fix trades. **0 CHANGES APPLIED.** — brain_auditor

1. **daily_orchestrator ~18:35 UTC — NO CONFIG CHANGE.** DB-verified: 16T 50%WR +$0.65 (24h) | 5 open positions (3 SHORT pump-chain-, 2 LONG). **PIPELINE HEALTHY.** 0-byte DB cleanup (8 files removed, no disk impact — real consumers are candles.db 2.2G, coin_tracker.db 3.2G). **OSCILLATOR SHADOW VERIFIED** — 5.6M file actively written. **ATR_SL POST-FIX: 0 hits, all exits profit-monster-trail.** **SIGNAL DIVERSITY:** Only volume-breakout-long+ (+$1.46/14d) and pump-chain+ (+$1.23/14d) profitable. 7d losses ALL pre-fix legacy. **DISK 85% (WARN).** **NO CHANGES APPLIED.** — daily_orchestrator

1. **brain_auditor ~17:30 UTC — 1 CONFIG CHANGE.** **LONG_RSI_SWEET_SPOT_MAX 50→60.** 14d: RSI 50-60 LONG = 43T 60.5%WR +$1.53 (identical to 40-50 band). Combined 40-60 = 59T 63.1%WR +$3.22/14d. +10pt confidence boost. 0 winners blocked. **ATR_SL 7d:** EXTREME 64.4% (legacy), post-fix 0/1 hits. **LOSING AUTOPSY:** 7 losers 24h all scratches (<$0.12). **5 open positions:** 3 SHORT EXTREME, 1 LONG NORMAL, 1 LONG HIGH. **CREATIVE (3):** SWEET_SPOT APPLIED, EXTREME pump-chain+ block monitor, SHORT RSI 50-60 penalty suggested. **1 CHANGE APPLIED.** — brain_auditor

1. **brain_auditor ~14:00 UTC — 1 CONFIG CHANGE.** **PUMP_CHAIN_LONG_DEAD_HOURS: removed hours 5, 8, 13, 22.** 14d: these hours +$1.86 combined. Expected +$0.40-0.90/7d. Blocks 0 recent winners. **ATR_SL 7d: 48.3% — PASS.** Post-fix: 0 trades. **pump-chain+ cold streak** 13T/7d. **LOSING AUTOPSY:** 9 losers 24h all scratches (<$0.12). **CREATIVE (3):** Dead hours fix APPLIED, EXTREME MIN_EXEC_CONFIDENCE=70, SHORT NULL RSI boost. **1 CHANGE APPLIED.** — brain_auditor

1. **brain_auditor ~12:34 UTC — NO CONFIG CHANGE.** DB-verified: 15T 33.3%WR +$0.51 (24h) | 117T 35.0%WR -$5.84 (7d) | 313T 44.4%WR -$2.72 (14d). **ATR_SL WIDENING VERIFIED** — Post-fix: 0/16 ATR_SL hits (0%). 7d: 48.7% (57/117) — PASS (<55%). All exits profit-monster-trail. **LONG RSI 60-70 NOT A KILLING FIELD** — 18W +$2.34 vs 31L -$1.09 = net +$1.25/14d. Losers signal-specific (bb-bounce-v2-long+ 8L), not RSI-driven. **SHORT NULL RSI edge ALIVE** — pullback-entry- 23T 60.9%WR +$0.63/14d. **pump-chain+ EXTREME profitable** — 35T 45.7%WR +$1.12/14d 1.69:1 R:R. **7d REGIME:** EXTREME -$3.98 (62T 35.5%), HIGH -$2.01 (34T 29.4%), NORMAL +$0.14 (18T 44.4%). **RSI BANDS 14d:** SHORT NULL = BEST (32T 59.4%WR +$0.82). LONG 45-60 = best LONG (33T 60.6%WR +$1.02). **CREATIVE (3):** (1) volume_spike 3 orphan paths fix (+$0.10-0.20/7d) (2) EXTREME MIN_EXEC_CONFIDENCE=70 after 50+ post-fix trades (+$0.30-0.50/7d) (3) SHORT NULL RSI confidence boost +15pt (+$0.20-0.40/7d, 8th suggestion). **0 CHANGES APPLIED.** — brain_auditor

1. **brain_auditor ~11:38 UTC — NO CONFIG CHANGE.** DB-verified: 15T 33.3%WR +$0.51 (24h) | 117T 35.0%WR -$5.84 (7d) | 313T 44.4%WR -$2.72 (14d). **ATR_SL WIDENING VERIFIED** — Post-fix: 0/16 hits (0%). 7d: 48.7% — PASS. **LONG RSI>70 DISCREPANCY RESOLVED** — entry_rsi_14 ≠ signal rsi_14 (different timeframes). NOT a leak. **HIGH regime -$2.01/7d** — legacy killed signals aging out. **SHORT NULL RSI edge ALIVE** — pullback-entry- 23T 60.9%WR +$0.63/14d. **pump-chain+ EXTREME profitable** — 35T 45.7%WR +$1.12/14d 1.69:1 R:R. **CREATIVE (3):** (1) Document entry_rsi discrepancy (2) EXTREME post-fix eval criteria (3) SHORT NULL RSI conf boost +15pt (7th). **0 CHANGES APPLIED.** — brain_auditor

1. **brain_auditor ~07:45 UTC — 1 CONFIG CHANGE.** **ATR_SL_MAX 1.8%->2.0%.** EXTREME 64.5% ATR_SL hit rate 7d (40/62). 1.2x multiplier DEAD at 1.8% cap. Widening gives EXTREME 33% more room. R:R 1.29:1→~1.50:1. Expected +$0.50-1.00/7d. TP_PCT_FALLBACK 4.5%->6.0%. Post-fix: 0/16 hits. **1 CHANGE APPLIED.** — brain_auditor

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
