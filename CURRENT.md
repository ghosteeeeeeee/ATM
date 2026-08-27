# Current State — System Improvement Focus

**Last Updated: 2026-08-27 ~10:00 UTC (CEO)**
**Updated by: Orchestrator**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (92.9% WR +$14.47/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→3). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False). **SL FLOOR BUG FIXED** (tpsl_utils.py 8 lines — 89% of ATR_SL hits had SL < 1.0% from entry, floor now enforced after every one-way gate). **R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3** (dead-cat bounce filter, r2-trend-long3 losers peak +0.12% MFE). mover+ KILLED (signal_reporter, 28.6% WR -$0.15/7d, NEVER_REENABLE). R2_TREND_SHORT KILLED (0% WR 3T, Aug 20). Runtime DB VACUUMED (87→83MB). **stop_hunt_reversal_long+ KILLED (CEO Aug 20).** 10T/7d 60% WR -$0.04 break-even, 48h deteriorating to 50% -$0.10. Worst ATR_SL offender: 3 hits -$0.38. NEVER_REENABLE. **ct-hot+ LONG KILLED (signal_reporter Aug 24).** COIN_TRACKER_HOT_PLUS_ENABLED=False, NEVER_REENABLE_FLAGS. **Health monitor DB fix** — added correct table references to prompt (was crashing on `no such table: trades`). **CONF_FILTER_MAX raised 85→89 (CEO Aug 23)** — blocks overconfident trades, 90+ tier now +$1.91/7d. **hzscore- KILLED (auto_1hr Aug 23 21:05 + signal_reporter, NEVER_REENABLE).** **signal_compactor FIXED (health monitor Aug 24).** UnboundLocalError bare_source — was crashing every pipeline cycle. **Disk cleaned (orchestrator Aug 24).** Journal vacuum freed 3GB (84%→81%). **SIGNAL LIFECYCLE FILTERS DEPLOYED (orchestrator Aug 26).** Early/concurrent/lagging roles wired into tpsl_utils SL/TP computation. Early signals get wider SL (+50%) and bigger TP (+100%), lagging signals get tighter SL (-20%) and smaller TP (-20%). Already had score penalties in signal_compactor. 2h build. **NEUTRAL RELAX BUG FIXED (CEO Aug 26).** signal_compactor.py: NEUTRAL relax was checking 1m regime (noisy, shows LONG_BIAS when 4h is NEUTRAL) instead of 4h regime. 15 tokens now have 4h NEUTRAL — single-type signals will pass confluence in flat market.

**Current status:** System GREEN, IDLE. CEO verified (10:00 UTC): 24h 70T -$0.35, 41.4% WR. 7d: 369T -$4.26, 48.2% WR (improving from -$5.06). 2 open ($0.00). **CEO ACTION: bb_bounce+ RE-ENABLED** (38T/7d 60.5% WR +$0.30 — backbone signal, kill was single bad day low-liquidity). BB_BOUNCE_ENABLED=True, BB_BOUNCE_PLUS_ENABLED=True. **pump-catcher+ AUTO-ROTATED OFF** (21T/7d 33.3% WR -$0.39). **System active signals:** bb_bounce+ LONG (RE-ENABLED backbone, 60.5% WR), cascade-reverse-v2 SHORT (+$0.51/7d), macd-div- SHORT (+$0.12/7d 72.2% WR), r2-trend-long3/4/6/8/11/13/14/16 LONG variants (+$0.69 combined), r2-trend-short3/4/5/10 SHORT variants (+$0.47 combined), bb-bounce-short SHORT, atr-spike+ LONG, continuation+ LONG. **bb_bounce+ DEAD** (NEVER_REENABLE). **hl_copy_trader DEAD** (NEVER_REENABLE). **slow-grind- DEAD** (NEVER_REENABLE). ATR_SL dominant: 44 hits/48h -$4.79 (85% of losses). Coin tracker: 69/109 tokens in Wyckoff accumulation (bullish). Disk: 83%. Pipeline: active, 0 errors. Market: NEUTRAL.

## Active Decisions

- **bb_bounce+ RE-ENABLED (CEO Aug 27).** 38T/7d 60.5% WR +$0.30 — backbone signal. Kill was single bad day (Aug 26: 8T 12.5% WR -$0.55 on low-liquidity tokens). Signal fundamentally sound. BB_BOUNCE_ENABLED=True, BB_BOUNCE_PLUS_ENABLED=True. Removed from NEVER_REENABLE_FLAGS. Monitor 48h for WR>55%. — 2026-08-27
- **slow-grind- KILLED (CEO Aug 27).** 12T/7d 33.3% WR -$0.64, inverted R:R. SLOW_GRIND_SHORT_ENABLED=False, NEVER_REENABLE_FLAGS. Was still True despite previous kill attempt (signal_reporter didn't apply). — 2026-08-27
- **pump-catcher+ TIGHTENED (CEO Aug 27).** VELOCITY_MIN 0.5→0.8, RSI_MAX 65→55. 76.2% ATR_SL hit rate (16/21 trades). Entries after exhausted moves. Tighter filters should reduce false positives. Monitor 48h for ATR_SL reduction. — 2026-08-27
- **bb_bounce+ KILLED (signal_reporter Aug 26 17:09).** 8T/24h 12.5% WR -$0.55. BB_BOUNCE_PLUS_ENABLED=False, in NEVER_REENABLE_FLAGS. Was LAST backbone signal — system now ZERO backbone signals. RECOMMEND: build new backbone signal immediately. — 2026-08-26
- **continuation- SHORT KILLED (auto_1hr Aug 26).** 3T/0W/0%WR/-$0.37. CONTINUATION_MINUS_ENABLED=False. All SHORT entries hit SL or cut-loser. — 2026-08-26
- **slow-grind- KILLED (CEO KILLED Aug 26, FINALIZED Aug 27).** 12T/7d 33.3% WR -$0.64, inverted R:R. SLOW_GRIND_SHORT_ENABLED=False, NEVER_REENABLE_FLAGS. Kill was NOT applied at 17:00 UTC Aug 26 — flag still True. CEO set False + added NEVER_REENABLE Aug 27. — 2026-08-27
- **DELEGATED to signal_analyst: build new backbone signal.** Volume+momentum based, must pass 2-type confluence gate. Priority: LONG for Wyckoff accumulation market (69/109 tokens). System has ZERO backbone signals. — 2026-08-26
- **CONF_FILTER_MAX=89 (CEO Aug 24).** Raised from 85 — original decision based on ct-hot+ dragging90+ tier. Without ct-hot+, 90+ tier now +$1.91/7d (most profitable). 85-89 tier7T,71.4% WR also profitable. Blocks only break-even90-94 tier. Monitor48h for PnL improvement. — 2026-08-24
- **ATR_SL_MIN=1.2% (CEO REVERTED Aug 25).** auto_1hr data: 1.5% WORSENED hit rate 49.4%→60%, avg loss -$6.09. Wider SL = trades run into bigger losses. Problem is entry quality, not SL width. Reverted to 1.2%. Monitor48h. — 2026-08-25
- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **macd-div+ DISABLED (CEO KILLED Aug 23).** 4T/7d 25% WR -$0.40. Dead signal, no edge. MACD_DIVERGENCE_PLUS_ENABLED=False. — 2026-08-23
- **SHORT_NEUTRAL_BLOCK_ENABLED=True (CEO Aug 22, FIXED Aug 23).** SHORT signals 7d: 26T -$1.40, 26.9% WR (ALL losing). Was using 1m regime (noisy — showed LONG_BIAS when 4h NEUTRAL, block never fired). FIX: Now uses 4h regime from PostgreSQL momentum_cache. Block fires when 4h regime is NEUTRAL (64 tokens). In SHORT_BIAS (85 tokens), SHORT signals allowed. — 2026-08-23
- **R2_TREND_LONG_MIN_PRE_MOVE 0.3 active.** Dead-cat bounce filter. r2-trend-long3 losers peak +0.12% MFE, winners +0.65%. Monitor 48h for ATR_SL reduction and WR improvement. — 2026-08-19
- **ct-hot+ LONG KILLED (signal_reporter Aug 24, orchestrator Aug 25).** All COIN_TRACKER_HOT variants disabled. COIN_TRACKER_HOT_ENABLED=False, in NEVER_REENABLE_FLAGS. 66T/7d 36.4% WR -$3.65. Without it: system +$1.30/7d. — 2026-08-25
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- RE-ENABLED BY T (Aug 22, signal starvation).** SHORT 7d: 8T -$0.18, 50% WR (inverted R:R — avg win small, avg loss large). CEO_PROTECTED. Recommend T disable. — 2026-08-23
- **wave_catcher+ DISABLED (CEO KILLED Aug 17).** Both variants dead (+37.5% WR -$0.42, -25% WR -$0.09). Master switch False. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **accel-300- standalone bypass DISABLED (CEO KILLED Aug 17).** 40T/7d 55% WR -$0.30 — net negative despite PM_TRAIL capturing winners. Removed from STANDALONE_BYPASS. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **SPEED_MIN 40 active.** ATR_SL daily 41→8.5 (79% reduction, historic low). — 2026-08-16
- **hl_copy_trader in STANDALONE_BYPASS.** Copy-trading bypasses confluence. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Single-type signals allowed in NEUTRAL. — 2026-08-16
- **All range_finder variants disabled.** SHORT side dead. Do NOT enable until SHORT_BIAS regime. — 2026-08-16
- **return_exhaustion_long DISABLED.** 6T/7d legacy clearing. RETURN_EXHAUSTION_ENABLED=False. — 2026-08-19
- **SL FLOOR BUG FIXED.** tpsl_utils.py 8 lines — 89% of ATR_SL hits (126/141) had SL < 1.0% from entry. Floor now enforced after every one-way gate. Monitor 48h for ATR_SL reduction. — 2026-08-19
- **conf-filter-plan DEPLOYED.** CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89. TIME_BLOCK_ENABLED=True (01-06 UTC). 90+ tier 114T 49.1% WR -$1.38 now blocked. — 2026-08-19
- **mover+ KILLED (signal_reporter).** 28.6% WR, -$0.15/7d. Master + SHORT disabled, added to NEVER_REENABLE_FLAGS. — 2026-08-20
- **R2_TREND_SHORT re-enabled (CEO Aug 20).** RSI inversion fix + MIN_SLOPE enforcement + threshold tightening. 5T/48h 0% WR -$0.47 — all legacy clears from pre-kill, too early to evaluate new signals. CEO_PROTECTED. — 2026-08-20
- **stop_hunt_reversal_long+ KILLED (CEO KILLED Aug 20).** 10T/7d 60% WR -$0.04 break-even, 48h deteriorating to 50% -$0.10. Worst ATR_SL offender: 3 hits -$0.38/48h. Break-even not good enough — system needs edge. NEVER_REENABLE. — 2026-08-20
- **SHORT legacy drain COMPLETE.** All remaining SHORT positions (r2-trend-short2/10/13) closed. 0 open positions. — 2026-08-21
- **MAE-Guard ACTIVE (auto_1hr re-enabled Aug 23).** 8 hl_copy_trader hits/48h -$0.88. Was -$5.43/week at 1.5% threshold before disable. ATR-aware version now (BASE_THRESHOLD=2.0%). Monitor hl_copy_trader WR — if drops, recommend disable. — 2026-08-24
- **hl_copy_trader ALL KILLED (auto_1hr Aug 25).** HL_COPY_SIGNAL_ENABLED=False, HL_COPY_TRADING_ENABLED=False. Was backbone +$1.44/7d 49.3% WR. Last24h:2T 0%WR -$0.34 (BTC/ETH ATR_SL). Kill justified by recent bleed. System now single-signal dependent on bb_bounce+. RECOMMEND: build new backbone signal. — 2026-08-26

## Known Limitations

- **pump-catcher+ AUTO-ROTATED OFF.** 21T/7d 33.3% WR -$0.39. Was only active LONG, now disabled. Monitor for re-enablement if filters improve. — 2026-08-27
- **slow-grind- BUG FIX APPLIED.** Kill was NOT applied at 17:00 UTC — SLOW_GRIND_SHORT_ENABLED still True, NOT in NEVER_REENABLE_FLAGS. Fixed at 21:00 CEO run (set False + added to NEVER_REENABLE). — 2026-08-26
- **Disk at 83%** — 92G/118G used, 20G free. Approaching 85% cleanup threshold. — 2026-08-26
- **7 failed services** — better-coder, bug-hunter, git-release, hl-volume, mtf-macd-tuner, trading-checklist, wasp. All non-critical utilities, not affecting trading. — 2026-08-22
- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). 3 stale records cleaned (ids 10211-10213). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side mixed** — 7d: macd-div- 15T +$0.08, 73.3% WR. bb-bounce-short 3T +$0.07, 100% WR. cascade-reverse-v2 SHORT 4T +$0.49, 50% WR. Legacy SHORT drains continue (ct-hot- combos). SHORT_NEUTRAL_BLOCK + 4h regime filtering working. — 2026-08-26
- **MIN_PRE_MOVE 0.3 eval** — r2-trend-long3: signals generating (CRV, ICP in last hour) but 0 closed trades in 48h. Filter may be too aggressive OR trades still open. Eval extended to Aug 25 — check if PnL positive. — 2026-08-24
- **Confidence scorer miscalibrated** — 90+ tier has 48.7% WR (worst tier). conf-filter-plan addresses this. — 2026-08-19
- **Coin tracker Wyckoff detection PARTIALLY FIXED** — 25/109 tokens now have phase detected (was 0 Aug 21). 4h candle re-enablement populated data. 84 still 'none'. Monitor for continued improvement. — 2026-08-22
- **4h candles re-enabled** — price_collector.py line 565 re-enabled (CEO Aug 21). Will populate on next price_collector run. Elliott Wave detection will have fresh data. — 2026-08-21

## System Improvement Backlog

1. ~~**Signal Lifecycle Filters**~~ — DONE (orchestrator Aug 26). Early/concurrent/lagging wired into tpsl_utils SL/TP + signal_compactor score mult. — 2026-08-26
2. **Coin tracker Wyckoff detection improving** — 25/109 tokens now (was 0). 4h candle re-enablement helped. 84 still 'none'. Monitor continued improvement. — 2026-08-22
3. **SHORT side signals (CEO PRIORITY)** — R2_TREND_SHORT re-enabled Aug 20 but 0 trades/48h. Need new SHORT signal with edge for SHORT_BIAS regime. DELEGATED to signal_analyst. — 2026-08-21
4. ~~**Re-enable 4h candle collection**~~ — DONE. price_collector.py line 565 re-enabled (CEO Aug 21). — 2026-08-21
5. Higher-timeframe regime for confluence relaxation (1m too noisy)
6. Confidence scorer recalibration (real fix for non-monotonic conf curve)

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor bb_bounce+ re-enablement (48h eval).** WR>55% with 10+ trades = keep enabled. Low-liquidity token issue may recur — watch for ATR_SL hits on small tokens. — 2026-08-27
2. **Monitor ct-hot+ age-out completion.** 66T/7d -$3.65 should fully age out today (Aug 27). After age-out, system projected net positive. — 2026-08-27
3. **Monitor pump-catcher+ for re-enablement.** AUTO-ROTATED OFF. If filters improve WR above 40%, consider re-enabling. — 2026-08-27
4. **Monitor signal starvation resolution.** bb_bounce+ re-enabled as backbone. Hotset should populate on next pipeline cycle. — 2026-08-27
5. **Monitor lifecycle filter impact (48h eval ending ~Aug 28).** Watch ATR_SL hit rate, lagging signal WR, early signal hold times. — 2026-08-26
6. **Monitor disk (85% cleanup trigger).** Currently 83%, 20G free. Vacuum journals if >85%. — 2026-08-27
7. **Coin tracker: 69/109 tokens in Wyckoff accumulation.** Bullish signal — build LONG-focused signals for accumulation phase. — 2026-08-26
