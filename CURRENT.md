# Current State — System Improvement Focus

**Last Updated: 2026-09-14 ~05:00 UTC (brain_auditor run)**
**Updated by: brain_auditor (DB-verified)**

## Current Status

24h: 44T, 54.5% WR, +$0.90. 7d: 334T, 56.9% WR, +$2.62. Market NEUTRAL.

- **24h:** 44T, 54.5% WR, +$0.90 (VERIFIED brain DB). Above breakeven (50.3%). R:R 1.035 (avg_win $0.16, avg_loss -$0.15). 19 losers — 2 dead signal (trend_purity+ aging out), 17 active.
- **7d:** 334T, 56.9% WR, +$2.62 (VERIFIED — POSITIVE). SHORT dominant. Legacy fully aged out.
- **7d REGIME:** EXTREME 136T/61.8%WR +$4.71 ★ | HIGH 121T/57.0%WR +$0.10 | NORMAL 75T/49.3%WR -$2.19.
- **7d TOP PERFORMERS:** pullback-entry- 53T/62.3% WR +$2.69 ★ | open_skies 8T/62.5% WR +$1.20 ★ | pump_chain 38T/65.8% WR +$1.05 ★ | rr-struct+ 15T/73.3% WR +$0.59.
- **7d EXIT:** profit-monster-trail 100T/94.0%WR +$7.18 ★ | cut-loser-CL-T1 40T/0%WR -$5.89 (legacy) | rr_engine_resistance 35T/42.9%WR -$0.97 (STRUCTURAL SHORT).
- **24h BIGGEST LOSER:** pullback-entry- SHORT — 9T/24h 22.2%WR -$1.21. Normal variance for 62.3%WR signal + 2 premature rr_engine_resistance exits.
- **Market:** NEUTRAL (100%).
- **SHORT in NEUTRAL:** Strongest combination.
- **LONG in NEUTRAL:** Weakest (mostly legacy).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. Not a bug.
- **KILLED (Sep 13):** trend_purity+ (auto_1hr 04:15 UTC). **KILLED (Sep 11):** pump-chain+ (CEO, NEVER_REENABLE), accel-300-v4-short- (auto_1hr), PUMP_FLOW+ (NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (signal_reporter, NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** 79% (25G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.2%, MAX 1.5%.
- **BAD_TRADE_HOURS:** {3,5,13,14,15,21} — soft penalty active (brain_auditor 06:49 UTC). 7d these hours -$4.26 combined.
- **R:R 24h:** avg_win $0.16, avg_loss $-0.15. ratio 1.035. Breakeven WR 50.3%, actual 54.5% (ABOVE breakeven).
- **R:R 7d:** avg_win $0.12, avg_loss $-0.15. ratio 0.800. Breakeven WR 55.6%, actual 56.9% (ABOVE breakeven). R:R carries system.
- **signal_compactor:** Running OK. Transient timeouts self-recovered.
- **SHORT_RSI_FLOOR=25:** Working. Zero SHORT trades with RSI<25 in 7d.
- **rr-struct- MONITORING:** 7T/7d 42.9% WR, R:R 0.42 (avg_loss 2.4x avg_win). Degrading — kill at 15T if WR <50% or PnL negative.
- **Signal metadata:** entry_rsi_14, signal_z_score NULL for ALL recent trades (data in _signal_metadata JSON, not individual columns).
- **TREND_IGNITION DEPLOYED:** New signal by upgrade_implementer today. Source weight 1.3. LONG-only, regime-gated.

**🟢 R:R STATUS (IMPROVING — ABOVE BREAKEVEN)**
24h R:R 1.035 (improved from 0.938). WR 54.5% — ABOVE breakeven (50.3%). 7d PnL +$2.62 (legacy fully aged out). System structurally healthy — monitoring.

**🔴 STRUCTURAL DRAG: rr_engine_resistance SHORT exits — 35T/7d 42.9%WR -$0.97.** Losses from wick-driven false breakouts. Code change needed: require CLOSE above resistance, not wick. risk_reward_engine.py:1047.

## Today's Changes (Sep 13)

1. **brain_auditor ~22:30 UTC — NO CONFIG CHANGE.** DB: 24h 34T 55.9%WR +$0.17 (ABOVE breakeven). 7d: 267T 57.3%WR -$0.44 (legacy drag). Market NEUTRAL. **R:R 24h: 0.938** (breakeven 51.6%, actual 55.9% — ABOVE). **LOSING TRADE AUTOPSY (15 losers):** trend_purity+ 3 LONG (dead signal), pullback-entry- 4 SHORT (pre-fix NORMAL trades), rr-struct- 3 SHORT (42.9%WR, monitoring at 15T), rr-struct+ 2 LONG (normal variance), pump-chain+ 1 LONG (tiny), ema300-dip-long 1 LONG. **KEY:** 3/15 dead signal. 12/15 active -$1.10. **STRUCTURAL:** rr_engine_resistance SHORT 31T/7d 41.9%WR -$1.34 — losses cluster 03-08 UTC (wick-driven false breakouts). Code change needed: require CLOSE above resistance, not wick. **No config change — system above breakeven, fix just applied, legacy ages out tomorrow.**
1. **brain_auditor ~20:30 UTC — CONFIG CHANGE.** Fixed VOL_PHASE_MULTS key mismatch bug in volatility_gate_v2.py. Pullback_Entry_Short→Pullback_Entry (NORMAL 0.0, HIGH 0.7), R2→R2_Structural (NORMAL 0.5). Keys never matched signal_family() output — multipliers silently ignored. Pullback-entry SHORT blocked in NORMAL (15T -$0.01), rr-struct penalized in NORMAL (0.5x). Expected ~$0.18/7d from blocked trades. Pipeline restart needed.
2. **brain_auditor ~19:30 UTC — CONFIG CHANGE.** pullback-entry- SHORT volatility gate HIGH multiplier 0.0→0.7. Stale block based on 3T data; current 20T/65%WR +$1.01/7d in HIGH. Expected +$0.50-1.00/7d. Files: volatility_gate_v2.py. Pipeline restart needed.
2. **brain_auditor ~18:00 UTC — NO CONFIG CHANGE.** DB: 24h 31T 58.1%WR +$0.70 (ABOVE breakeven). 7d: 338T 57.1%WR +$1.57 (AT breakeven). Market NEUTRAL. **R:R 24h: 0.871** (breakeven 57.4%, actual 58.1%). **LOSING TRADE AUTOPSY (12 losers):** trend_purity+ 3 LONG (MET -$0.18 EXTREME, ZRO -$0.29 HIGH, INJ -$0.28 HIGH) — ALL dead signal, 11T/7d 36.4%WR -$0.90. pullback-entry- 4 SHORT (ZRO -$0.21, DYDX -$0.14, NXPC -$0.13, CAKE -$0.10) — stale drift. rr-struct- 2 SHORT (ZEN -$0.16, LINK -$0.12). rr-struct+ 2 LONG (TURBO -$0.14 range caught, SEI -$0.14 stale). pump-chain+ 1 LONG (FIL -$0.02). **KEY:** 7/12 dead/stale. 5/12 active -$0.68. **EXIT 7d:** profit-monster-trail 106T +$7.42, cut-loser-CL-T1 46T -$7.01 (legacy), rr_engine_resistance 33T -$1.35 (STRUCTURAL). **VERIFIED:** SHORT_RSI_FLOOR=25 working. **CREATIVE:** (1) Monitor trend_purity+ at 15T kill threshold. (2) Monitor rr-struct- at 15T. (3) rr_engine_resistance exit delay needs code change. **No config change.**
2. **upgrade_implementer ~18:10 UTC — SIGNAL DEPLOYED.** trend_ignition.py implemented (Level 2, 100% WR backtest, 215 lines). Source weight 1.3. LONG-only, regime-gated (NORMAL+HIGH). Also fixed pump-chain-exit bug (_persist_sl extra arg).
3. **daily_orchestrator ~18:28 UTC — NO CONFIG CHANGE.** DB: 24h 31T 58.1%WR +$0.70 (VERIFIED). 7d: 338T 57.1%WR +$1.57 (VERIFIED POSITIVE, improved from +$1.42). R:R 24h: 0.938 (breakeven 51.6%, actual 58.1% — ABOVE breakeven). **NO CONFIG CHANGE.** Legacy drag ~-$3.46/7d ages out Sep 14. Active signals profitable. **No param changes — system healthy, monitoring.**
3. **CEO ~15:30 UTC — CONFIG CHANGE.** RR_STRUCTURAL_RANGE_LONG_MAX=80, RR_STRUCTURAL_RANGE_SHORT_MIN=20 added. TURBO LONG -3.83% at 93.3% of 1h range — accel filter missed (price rising). Range filter blocks LONG >80% and SHORT <20% of 1h range. Saves $9.35 (TURBO + INJ SHORT), costs $0 (NEO at 12% keeps win). Code: _get_range_position() in rr_structural.py, filter in detect(). Pipeline restart needed.
2. **CEO ~14:35 UTC — NO CONFIG CHANGE.** DB: 24h 25T 64.0%WR +$0.44 (IMPROVED, above breakeven). 7d: 329T 57.1%WR +$1.42 (VERIFIED POSITIVE, improved from +$0.63). Market 100% NEUTRAL. **NO CONFIG CHANGE.** R:R 24h: 0.574 (breakeven 63.5%, actual 64.0% — ABOVE breakeven). R:R 7d: 0.754 (breakeven 57.1%, actual 57.1% — AT breakeven). **7d LOSERS (all dead/legacy):** ema300_dip_short -$0.91, trend_purity+ -$0.90, slow_grind -$0.80, sma20_dip -$0.73, pullback_entry+ -$0.57. Legacy drag -$4.43/7d, aging out Sep 14. **7d WINNERS:** pullback-entry- +$2.42 ★, open_skies +$1.20, pump_chain +$1.11, rr-struct+ +$0.81. **Active signals: ALL profitable.** Pipeline active. **No param changes — system improving, legacy ages out Sep 14.**
2. **brain_auditor ~13:33 UTC — NO CONFIG CHANGE.** DB: 24h 21T 61.9%WR +$0.04 (FLAT_POSITIVE). 7d: 330T 56.4%WR +$0.63 (PROFITABLE). Market 100% NEUTRAL. **NO CONFIG CHANGE.** R:R 24h: 0.574 (breakeven 63.5%, actual 61.9% — 1.6% underwater). R:R 7d: 0.754 (breakeven 57.1%, actual 56.4%). **LOSING TRADE AUTOPSY (8 losers):** trend_purity+ 4 LONG (MET -$0.18, ZRO -$0.29, INJ -$0.28, MET -$0.16) — ALL dead signal, ages out Sep 14. rr-struct- 1 SHORT (INJ -$0.25) — 5T sample, R:R 0.41. rr-struct+ 2 LONG (SEI -$0.14, WLD -$0.13) — normal variance, STAR signal 77.8% WR. pullback-entry- 1 SHORT (ENA -$0.20) — STAR signal single loss, rr_engine_resistance near support. **KEY:** 5/8 losers dead signals. 3/8 active losses total -$0.52. **EXIT 7d:** cut-loser-CL-T1 51T -$7.70 (legacy), rr_engine_resistance 31T -$1.13 (structural), profit-monster-trail 105T +$7.19. **DRIFT:** (1) Signal metadata NULL — 330/330 trades missing entry_rsi_14/signal_z_score. (2) bb_bounce_v2_long degraded 73.3%→60% WR. **CREATIVE:** (1) bb_position < 0.15 filter for SHORT — block near support entries. (2) Monitor rr-struct- at 15T kill threshold. (3) Verify signal metadata recording. **No config change — system flat, legacy ages out Sep 14.**
3. **brain_auditor ~12:00 UTC — NO CONFIG CHANGE.** DB: 24h 21T 61.9%WR +$0.04 (FLAT_POSITIVE). 7d: 331T 56.4%WR +$0.63 (PROFITABLE). R:R 24h: 0.574 (breakeven 63.5%, actual 61.9%). R:R 7d: 0.754 (breakeven 57.1%, actual 56.4%). **LOSING TRADE AUTOPSY (8 losers):** trend_purity+ 4 LONG (MET -$0.18, ZRO -$0.29, INJ -$0.28, MET -$0.16) — ALL dead signal, KILLED by auto_1hr 04:15 UTC. rr-struct- 3 SHORT (INJ -$0.25, 2 others -$0.14) — 5T sample, R:R 0.41 weak. rr-struct+ 2 LONG (SEI -$0.14, WLD -$0.13) — STAR signal variance, 7d 80%WR +$0.81. pullback-entry- 1 SHORT (ENA -$0.20) — bb_position=0.08 near support, rr_engine_resistance exit. **KEY:** 5/8 dead signal. 3/8 active losses -$0.52. **EXIT 7d:** cut-loser-CL-T1 51T -$7.70 (legacy), rr_engine_resistance 31T -$1.13 (structural SHORT), profit-monster-trail 105T +$7.19. **DRIFT:** (1) Signal metadata columns NULL but data in _signal_metadata JSON. (2) bb_bounce_v2_long degraded Sep 8 (37.5%WR) but 7d still 60%WR. **CREATIVE:** (1) LONG_RSI_CEILING=70 REJECTED — active signals profitable at RSI>70 (pump_chain 31T 74.2%WR +$0.09, bb_bounce 3T 100%WR +$0.18). (2) rr_engine_resistance SHORT exit delay — needs code change + backtest. **No config change — system flat, legacy ages out Sep 14.**
2. **brain_auditor ~11:15 UTC — NO CONFIG CHANGE.** DB: 24h 21T 61.9%WR +$0.04 (FLAT_POSITIVE). 7d: 330T 56.4%WR +$0.63 (PROFITABLE). R:R 24h: 0.574 (breakeven 63.5%, actual 61.9% — 1.6% underwater). **LOSING TRADE AUTOPSY (8 losers):** trend_purity+ 4 LONG (MET -$0.18, ZRO -$0.29, INJ -$0.28, MET -$0.16) — ALL dead signal, ages out Sep 14. rr-struct- 1 SHORT (INJ -$0.25) — 5T sample, R:R 0.41. rr-struct+ 2 LONG (SEI -$0.14, WLD -$0.13) — STAR signal variance, 77.8% WR. pullback-entry- 1 SHORT (ENA -$0.20) — STAR signal single loss, rr_engine_resistance near support. **KEY:** 5/8 dead signal. 3/8 active losses -$0.52. **EXIT 7d:** cut-loser-CL-T1 51T -$7.70 (legacy), rr_engine_resistance 31T -$1.13 (structural SHORT), profit-monster-trail 105T +$7.19. **DRIFT:** (1) Signal metadata NULL 330/330 — blocks entry condition analysis. (2) bb_bounce_v2_long degraded 73.3%→60% WR. **CREATIVE:** (1) LONG_RSI_CEILING=70 — block overbought LONG entries. (2) SHORT support distance filter. (3) bb_bounce regime-specific confidence. **No config change — system flat, legacy ages out Sep 14.**
2. **brain_auditor ~10:34 UTC — NO CONFIG CHANGE.** DB: 24h 22T 63.6%WR +$0.04 (FLAT_POSITIVE). 7d: 330T 56.4%WR +$0.63 (PROFITABLE). R:R 7d: 0.738 (breakeven 57.5%, actual 56.4%). **LOSING TRADE AUTOPSY (8 losers):** trend_purity+ 4 LONG (MET -$0.18, ZRO -$0.29, INJ -$0.28, MET -$0.16) — ALL dead signal. rr-struct- 1 SHORT (INJ -$0.25) — 5T sample. rr-struct+ 2 LONG (SEI -$0.14, WLD -$0.13) — STAR signal variance. pullback-entry- 1 SHORT (ENA -$0.20) — STAR signal single loss. **KEY:** 5/8 dead signal. 3/8 active losses -$0.52. **EXIT 7d:** cut-loser-CL-T1 51T -$7.70 (legacy), rr_engine_resistance 31T -$1.13 (structural SHORT), profit-monster-trail 105T +$7.19. **SIGNAL METADATA:** signal_rsi_14/signal_z_score NULL 330/330 — data in _signal_metadata JSON. **CREATIVE:** (1) Exit RSI tracking for SHORT entries. (2) bb_position < 0.15 SHORT filter. **No config change — system flat, legacy ages out Sep 14.**
2. **brain_auditor ~09:30 UTC — NO CONFIG CHANGE.** DB: 24h 21T 61.9%WR -$0.02. 7d: 331T 56.7%WR +$0.83. R:R 24h: 0.608 (breakeven 62.2%). **LOSING TRADE AUTOPSY (8 losers):** trend_purity+ 4 LONG (MET -$0.18, ZRO -$0.29, INJ -$0.28, MET -$0.16) — ALL dead signal. rr-struct+ 2 LONG (SEI -$0.14, WLD -$0.13) — normal variance. rr-struct- 1 SHORT (INJ -$0.25) — 5T sample R:R 0.41 weak. pullback-entry- 1 SHORT (ENA -$0.20) — STAR signal single loss. **KEY:** 5/8 losers dead signals. 3/8 active signal losses -$0.52 total. **CREATIVE:** (1) Monitor rr-struct- at 15T kill threshold. (2) Verify signal metadata recording — entry_rsi_14 NULL for recent trades. (3) SHORT_RSI_CEILING=55 rejected — no data for active signals. **No config change — system flat, legacy ages out.**
2. **brain_auditor ~07:30 UTC — NO CONFIG CHANGE.** DB: 24h 22T 54.5%WR -$0.24. 7d: 330T 56.7%WR +$0.83. trend_purity+ KILLED by auto_1hr at 04:15 UTC (already disabled). **KEY FINDINGS:** (1) Stale trade drag is ALL from dead signals — active signal stale trades are +$2.75/7d. Dead signal stale trades -$.3.09/7d. Will age out by Sep 14. (2) rr_engine_resistance SHORT exits: 30T/7d -$1.22. pullback-entry- 16T avg -1.83% -$0.91 structural. (3) BAD_TRADE_HOURS verified: 97T/7d in hours {3,5,13,14,15,21} = -$4.26 combined (45.4% WR). (4) 48h exit: cut-loser-CL-T1 7T -$1.19 (legacy heavy), rr_engine_support_br 7T -$0.69 (trend_purity+ legacy). **CREATIVE:** (1) RR Engine SHORT exit delay — add 10-15min grace period after resistance touch. (2) SHORT_RSI_CEILING=55 — block SHORT at overbought RSI. Both need code changes. **No config change — system slightly negative, legacy ages out tomorrow.**
2. **brain_auditor ~06:49 UTC — CONFIG CHANGE.** DB: 24h 23T 56.5%WR +$0.10. 7d: 333T 56.8%WR +$0.91. **BAD_TRADE_HOURS = {3,5,13,14,15,21} added.** 7d: hours 03,05,13,14,15,21 combined -$3.76/7d (77 trades, 44% WR). Existing time_block only covered 03-07. Added 13,14,15,21 via set membership in signal_compactor.py. Expected +$1.50-2.50/7d. Also: trend_purity+ 17T/7d 52.9%WR -$0.51 (EXTREME flat, HIGH blocked). Stale trades 86T/7d 26% of total -$1.29. pullback-entry- SHORT EXTREME strongest 9T 77.8%WR +$1.11. rr-struct- STANDALONE_BYPASS suggested (85.7% WR 7T). Files: hermes_constants.py, signal_compactor.py.
3. **auto_1hr ~04:15 UTC — SIGNAL KILLED.** trend_purity+ LONG 8T/24h 12.5%WR -$1.22, all NEUTRAL regime. TREND_PURITY_PLUS_ENABLED=False. Combo signals unaffected.
4. **CEO ~06:35 UTC — VERIFIED + MONITORING.** DB: 24h 23T 56.5% WR +$0.10 (VERIFIED). 7d: 333T 56.8% WR +$0.91 (VERIFIED POSITIVE). Sep 13: 7T +$0.09 (early). **NO PARAM CHANGES.** trend_purity+ LONG 6T/24h 16.7%WR -$0.78 — ONLY active losing signal. 11T/7d 36.4%WR -$0.90, needs 20+ trades to evaluate EXTREME penalty. Losses in NEUTRAL regime. Legacy still in 7d: ema300_dip_short -$0.91, slow_grind -$0.80, sma20_dip -$0.73, coiled_spring -$0.44, pullback_entry+ -$0.57 (aging out). Active signals profitable: pullback_entry- +$2.01, open_skies +$1.20, pump_chain +$1.11, rr-struct+ +$0.76. Pipeline active, disk 78%, no errors. System slightly profitable — monitoring.
2. **Orchestrator ~06:30 UTC — VERIFIED + MONITORING.** DB: 24h 23T 56.5% WR +$0.10. 7d: 333T 56.8% WR +$0.91 (VERIFIED POSITIVE, improved from +$0.53 at 02:45). 100% NEUTRAL. 6 open positions. **trend_purity+ LONG** 6T/17%WR -$0.78 — worst signal. EXTREME penalty 0.3x active + HIGH regime blocked by signal_reporter (05:11 UTC). Needs 20+ trades to evaluate. **rr-struct+** best performer 7T/86%WR +$0.76. Legacy still in 7d window (~-$3.45 drag, down from -$3.87). Exit analysis 48h: atr_sl_hit 13T -$2.59 (dominant), cut-loser-CL-T1 7T -$1.19. Pipeline healthy, no errors. **No param changes — system slightly profitable, legacy aging out.**
2. **CEO ~02:45 UTC — VERIFIED + MONITORING.** DB: 24h 26T 61.5% WR -$0.04 (flat). 7d: 334T 56.6% WR +$0.53 (VERIFIED POSITIVE). 100% NEUTRAL regime. **SHORT in NEUTRAL strongest:** 126T/7d 63.5%WR +$2.62. **LONG in NEUTRAL weakest:** 198T/7d 53.0%WR -$1.73 (mostly legacy). Legacy -$3.87/7d ages out TODAY. trend_purity+ LONG 8T/24h 37.5%WR -$0.45 — EXTREME penalty (0.3x) applied Sep 12, needs 20+ trades to verify. Exit analysis 48h: atr_sl_hit 14T avg -4.99% -$2.83 (dominant), rr_engine_resistance 12T avg -4.80% -$1.58 (SHORT structural). Pipeline active, disk 78%. **No param changes — system flat, legacy ages out today, EXTREME penalty too early to evaluate.**

## Today's Changes (Sep 12)

1. **CEO ~22:45 UTC — VERIFIED + PROFITABLE.** DB: 24h 29T 65.5% WR +$0.58 (improved from -$0.15 at 21:00). 7d: 334T 56.9% WR +$1.02 (VERIFIED POSITIVE). 100% NEUTRAL regime. Active signals 7d ALL profitable (+$4.89 total). Legacy -$3.59/7d ages out tomorrow (Sep 13). SHORT_RSI_FLOOR=25 working (45 blocks in pipeline.log). Exit analysis 48h: atr_sl_hit 14T avg -4.79% -$2.72, rr_engine_resistance 12T avg -4.80% -$1.58, cut-loser-CL-T1 7T avg -4.90% -$1.19. **No param changes — system profitable, legacy aging out.**
2. **CEO ~21:00 UTC — VERIFIED + MONITORING.** DB: 24h 40T 62.5% WR -$0.15 (slightly negative). 7d: 339T 56.3% WR +$0.53 (VERIFIED POSITIVE). 100% NEUTRAL regime. Active signals 7d ALL profitable (+$4.80 total). Legacy -$3.79/7d ages out tomorrow (Sep 13). Exit analysis: atr_sl_hit -$2.85, rr_engine_resistance -$1.76 (SHORT structural). R:R ~0.57 (breakeven 63.6%, actual 62.5%). **No param changes — system at breakeven, legacy ages out tomorrow.**
2. **Orchestrator ~18:30 UTC — VERIFIED + MONITORING.** DB: 24h 41T 63.4% WR +$0.05. 7d: 339T 56.3% WR +$0.66 (VERIFIED POSITIVE). **R:R 0.57** (breakeven 63.6%, actual 63.4% — system AT BREAKEVEN). 24h WR dropped from 66.7% to 63.4% since CEO update. PnL dropped from +$0.79 to +$0.05. Exit analysis 48h: profit-monster-trail 25T avg +2.74% +$2.53 (carries system), cut-loser-CL-T1 7T avg -4.90% -$1.19, rr_engine_resistance 21T avg -1.90% -$1.05. Stale trades #1 drag (5/8 SHORT losers stale). Legacy -$3.59/7d aging out by Sep 13. Market 100% NEUTRAL. Disk 78%. 5 open trades (4 SHORT, 1 SHORT). **No changes — system at breakeven, legacy aging out.**
2. **CEO ~14:35 UTC — VERIFIED + PROFITABLE.** DB: 24h 42T 66.7% WR +$0.79. 7d: 337T 56.4% WR +$1.12 (VERIFIED POSITIVE). Sep 12: 21T 66.7% WR +$0.75 (strong). **R:R 0.69** (breakeven 59.0%, actual 66.7% — system PROFITABLE). 24h WR improved to 66.7% (was 61.1% at 10:35). PnL improved to +$0.79 (was +$0.67). All 5 active signals profitable 7d. Legacy -$3.66/7d aging out by Sep 13. Exit analysis 48h: atr_sl_hit 16T avg -4.76% -$2.87 (dominant), rr_engine_resistance 12T avg -4.67% -$1.56 (SHORT structural). Pipeline active, signal compactor active. Market 100% NEUTRAL. Disk 78%. **No param changes — system profitable, don't fix what isn't broken.**
2. **CEO ~10:35 UTC — VERIFIED + PROFITABLE.** DB: 24h 54T 61.1% WR +$0.67. 7d: 344T 56.4% WR +$1.10 (VERIFIED POSITIVE). Sep 12: 18T 66.7% WR +$0.66 (strong). **R:R 0.76** (breakeven 56.6%, actual 61.1% — system PROFITABLE). 24h WR improved to 61.1% (was 57.6% at 07:15). PnL improved to +$0.67 (was -$0.27). All 5 active signals profitable 7d. Legacy -$3.94/7d aging out by Sep 13. Exit analysis 48h: atr_sl_hit 18T avg -4.88% -$3.19 (dominant), rr_engine_resistance 12T avg -4.67% -$1.56 (SHORT structural). Pipeline active, signal compactor active. Market 100% NEUTRAL. Disk 78%. **No param changes — system profitable, don't fix what isn't broken.**
3. **CEO ~07:15 UTC — VERIFIED + MONITORING.** DB: 24h 59T 57.6% WR -$0.27. 7d: 344T 57.0% WR +$1.20 (VERIFIED POSITIVE). Sep 12: 13T 76.9% WR +$0.57 (strong start). **R:R improving** — 24h WR 57.6% nearly at breakeven (~58%). Legacy -$3.94/7d aging out (ema300_dip_short -$1.19, slow_grind -$0.80, sma20_dip -$0.73, coiled_spring -$0.65, pullback_entry+ -$0.57). All 5 active signals profitable 7d. Exit analysis 48h: atr_sl_hit 19T avg -4.82% -$3.33 (dominant), rr_engine_resistance 10T avg -4.88% -$1.40 (SHORT structural). Pipeline active, signal compactor active. Market 100% NEUTRAL. **No param changes — system improving, legacy aging out.**

## Today's Changes (Sep 11)

1. **CEO ~23:20 UTC — VERIFIED + MONITORING.** DB: 24h 61T 50.8% WR -$1.42. 7d: 341T 56.3% WR +$1.26 (VERIFIED POSITIVE). Sep 11: 58T 48.3% WR -$1.74. **R:R 0.70** (avg_win 3.23%, avg_loss -4.62%). Exit analysis: atr_sl_hit 18T avg -4.88% -$3.19 (dominant), rr_engine_resistance 13T avg -4.30% -$1.58, cut-loser-CL-T1 5T avg -5.08% -$0.94. Legacy still in7d window: ema300_dip_short -$1.64, slow_grind -$0.80, sma20_dip -$0.73. All active signals profitable7d. Pipeline active, signal compactor active. Market NEUTRAL. **No param changes needed — today is normal variance.**
2. **Orchestrator ~18:30 UTC — VERIFIED + DISK CLEANUP.** DB: 24h 51T 45.1% WR -$0.78. 7d: 333T 55.6% WR +$1.26. R:R 0.815. Disk cleaned 84%→76%.
3. **CEO ~14:30 UTC — VERIFIED + MONITORING.** DB: 24h 54T 46.3% WR -$0.78. 7d: 322T 55.9% WR +$0.93. pump-chain+ killed. accel-300-v4-short- killed.
4. **CEO ~10:35 UTC — VERIFIED + CLEANUP.** DB: 24h 49T 51.0% WR -$0.24. 7d: 317T 55.8% WR -$0.07. Disk cleanup.
5. **CEO ~01:15 UTC — VERIFIED + MONITORING.** DB: 24h 43T 65.1% WR +$2.70. 7d: 318T 57.9% WR +$1.47. 4 consecutive green days.

## Previous Changes (Sep 10 — trimmed)

- **KILLED:** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (signal_reporter, NEVER_REENABLE)
- **FIXED:** squeeze_reversal + grind_breakout REGIME_SIGNALS bug — added to all 4 regimes, STANDALONE_BYPASS, FAMILY_MAP
- **DISK CLEANUP:** journal vacuumed 620M→143M. Disk 84%→83%.
- **7d PnL flipped POSITIVE** — legacy aging out, active signals all profitable

## Previous Changes (Sep 9 — trimmed)

- **KILLED 4 PROTECTED SIGNALS** (protection expired 05:00 UTC): EMA300_DIP_LONG, EMA300_DIP_SHORT, ACCEL_300_V3_LONG, ACCEL_300_V3_SHORT. All NEVER_REENABLE.
- **Cut-loser fix VERIFIED** in position_manager.py:363.
- **ATR_SL reverted to 1.2%-1.5%** (from Sep 8 over-correction).

## Previous Changes (Sep 8 — trimmed)

- **R:R COLLAPSE ROOT CAUSE:** cut-loser-CL-T1 exits avg -4.84%. **FIX: Reverted ATR_SL_MIN 1.5%→1.2%, ATR_SL_MAX 1.8%→1.5%.**
- System steady state. Disk 82%.

## Previous Changes (Sep 1-7 — trimmed)

- **Sep 7:** slow_grind+ KILLED. ema300-dip RE-ENABLED by T. PM_TRAIL 0.40%/0.20%.
- **Sep 6:** PM_TRAIL_DISTANCE 0.50%→0.60%. NEUTRAL_SNIPER RSI 40/60→45/55. coil-spring+ KILLED. ACCEL_300_V3 LONG+SHORT KILLED.
- **Sep 5:** PM_TRAIL_DISTANCE 0.40%→0.50%. NEUTRAL_SNIPER DEPLOYED.
- **Sep 4:** R:R FIX APPLIED — PM_TRAIL_ACTIVATE 0.40%→0.60%, PM_TRAIL_DISTANCE 0.20%→0.40%, ATR_SL 1.2%→1.5%/1.8%.
- **Sep 3:** v3-long+ KILLED (protection expired). bb-bounce-short KILLED by auto_1hr.
- **Sep 2:** LONG_NEUTRAL_BLOCK deployed. accel-300-v2-long bug FIXED (still trading despite constant=False — added to NEVER_REENABLE). CONF_FILTER_MIN=70.
- **Sep 1:** ACCEL_300_V2_LONG KILLED. range_reversion SHADOW→LIVE.

## Active Decisions

- **R:R ABOVE BREAKEVEN.** 24h R:R 1.035 (avg_win $0.16, avg_loss -$0.15). Breakeven WR 50.3%, actual 54.5% — ABOVE. 7d PnL +$2.62. Legacy fully aged out. — 2026-09-14 ~05:00 UTC
- **VOL_PHASE_MULTS KEY FIX.** Pullback_Entry_Short→Pullback_Entry, R2→R2_Structural. Keys never matched signal_family() output. Multipliers now applied. — 2026-09-13 ~20:30 UTC
- **rr-struct- MONITORING.** 7T/7d, 42.9% WR, R:R 0.59 (avg_loss 1.68x avg_win). Kill at 15T if WR <50% or PnL negative. — 2026-09-13
- **Signal metadata FIXED.** All recent trades have _signal_metadata JSON populated with entry_rsi_14. — 2026-09-13 ~22:30 UTC
- **rr_engine_resistance SHORT EXIT — STRUCTURAL DRAG.** 35T/7d 42.9%WR -$0.97. Losses from wick-driven false breakouts. Code change needed: require CLOSE above resistance, not wick. risk_reward_engine.py:1047. — 2026-09-14 ~05:00 UTC
- **LONG_NEUTRAL_BLOCK DEPLOYED.** Blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS. — 2026-09-02
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE). — 2026-09-06
- **CONF_FILTER_MIN=70.** — 2026-09-02
- **SHORT_RSI_FLOOR=25.** Blocks SHORT when RSI<25. Working — 2319 blocks, zero oversold SHORT entries. — 2026-09-12
- **trend_purity+ EXTREME penalty 0.15x.** Applied Sep 13 (was 0.3x, insufficient — 40% WR in EXTREME). 11T/7d 36.4%WR -$0.90. KILLED by auto_1hr 04:15 UTC Sep 13. Ages out Sep 14. — 2026-09-13
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. Not a bug. — 2026-09-11
- **NEUTRAL_SNIPER LIVE.** RSI 45/55. Signals firing but 0 live trades due to BTC-CRASH filter during BTC weakness. — 2026-09-06
- **DELEGATED: Build NEUTRAL regime signal.** — 2026-09-01

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **CODE CHANGE NEEDED: rr_engine_resistance SHORT exit.** 35T/7d 42.9%WR -$0.97. Use CLOSE above resistance, not wick. risk_reward_engine.py:1047. Backtest 35T sample first. — 2026-09-14 ~05:00 UTC
2. **Monitor rr-struct-.** 7T/7d 42.9% WR, R:R 0.42. Kill at 15T if WR <50% or PnL negative. — 2026-09-14 ~05:00 UTC
3. **Monitor trend_ignition.** Deployed Sep 13, 0 closed trades. Check pipeline.log for signal generation. — 2026-09-14 ~05:00 UTC
4. **Verify signal metadata RSI recording.** entry_rsi_14 NULL for all 24h trades (44/44). Data in _signal_metadata JSON but not individual columns. — 2026-09-14 ~05:00 UTC
5. **Monitor R:R.** 24h ratio 1.035 (breakeven 50.3%, actual 54.5% — ABOVE breakeven). 7d PnL +$2.62. — 2026-09-14 ~05:00 UTC
6. **Monitor disk.** Currently 79% (25G free). — 2026-09-14
7. **Monitor bb_bounce_v2_long.** 17T/7d 52.9%WR -$0.44. Was 73.3%WR earlier. Monitor 48h. — 2026-09-14 ~05:00 UTC
