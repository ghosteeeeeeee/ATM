# Current State — System Improvement Focus

**Last Updated: 2026-08-25 ~18:35 UTC (Orchestrator Run)**
**Updated by: Orchestrator**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (92.9% WR +$14.47/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→3). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False). **SL FLOOR BUG FIXED** (tpsl_utils.py 8 lines — 89% of ATR_SL hits had SL < 1.0% from entry, floor now enforced after every one-way gate). **R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3** (dead-cat bounce filter, r2-trend-long3 losers peak +0.12% MFE). mover+ KILLED (signal_reporter, 28.6% WR -$0.15/7d, NEVER_REENABLE). R2_TREND_SHORT KILLED (0% WR 3T, Aug 20). Runtime DB VACUUMED (87→83MB). **stop_hunt_reversal_long+ KILLED (CEO Aug 20).** 10T/7d 60% WR -$0.04 break-even, 48h deteriorating to 50% -$0.10. Worst ATR_SL offender: 3 hits -$0.38. NEVER_REENABLE. **ct-hot+ LONG KILLED (signal_reporter Aug 24).** COIN_TRACKER_HOT_PLUS_ENABLED=False, NEVER_REENABLE_FLAGS. **Health monitor DB fix** — added correct table references to prompt (was crashing on `no such table: trades`). **CONF_FILTER_MAX raised 85→89 (CEO Aug 23)** — blocks overconfident trades, 90+ tier now +$1.91/7d. **hzscore- KILLED (auto_1hr Aug 23 21:05 + signal_reporter, NEVER_REENABLE).** **signal_compactor FIXED (health monitor Aug 24).** UnboundLocalError bare_source — was crashing every pipeline cycle. **Disk cleaned (orchestrator Aug 24).** Journal vacuum freed 3GB (84%→81%).

**Current status:** System YELLOW. Orchestrator verified (18:35 UTC): 24h 38T 42.1% WR -$1.54. 7d: 316T 50.6% WR -$3.73. Today Aug 25: 32T closed -$1.43. 5 open (ICP SHORT, ETH SHORT, GMT SHORT, BTC LONG, HBAR SHORT). **ct-hot+ KILLED (orchestrator)** — COIN_TRACKER_HOT_ENABLED=False, in NEVER_REENABLE_FLAGS. Without ct-hot+: 7d 235T 57.0% WR +$1.30 (system profitable). **hl_copy_trader SHORT** worst performer today: 11T 27.3% WR -$0.95. bb_bounce+ 12T 50% WR -$0.17 (mixed day). 70-79 conf tier DOMINANT LOSS today: 5T 0% WR -$0.77. 90+ tier: 16T 50% WR -$0.25. Signal reporter FIXED (SQL INTERVAL syntax error — switched to Python timestamps). Disk: 82%. Pipeline: active, 0 errors.

## Active Decisions

- **CONF_FILTER_MAX=89 (CEO Aug 24).** Raised from 85 — original decision based on ct-hot+ dragging90+ tier. Without ct-hot+, 90+ tier now +$1.91/7d (most profitable). 85-89 tier7T,71.4% WR also profitable. Blocks only break-even90-94 tier. Monitor48h for PnL improvement. — 2026-08-24
- **ATR_SL_MIN=1.5% (auto_1hr Aug 25).** Raised from 1.2%. Today 17 ATR_SL hits 41.2% WR avg -$1.38 (yesterday 32 hits 25% WR avg -$3.34). Floor working. Monitor 48h. — 2026-08-25
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

## Known Limitations

- **Disk at 81%** — 90G/118G used. Cleaned 3GB journal vacuum (was 84%). Safe for now. — 2026-08-24
- **7 failed services** — better-coder, bug-hunter, git-release, hl-volume, mtf-macd-tuner, trading-checklist, wasp. All non-critical utilities, not affecting trading. — 2026-08-22
- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). 3 stale records cleaned (ids 10211-10213). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side mixed** — 24h 16T +$0.12, 37.5% WR. 7d: tl_break_short 10T +$0.02, 80% WR. macd-div- 6T +$0.19, 83.3% WR. Legacy SHORT drains continue (ct-hot- combos). SHORT_NEUTRAL_BLOCK + 4h regime filtering working. — 2026-08-24
- **MIN_PRE_MOVE 0.3 eval** — r2-trend-long3: signals generating (CRV, ICP in last hour) but 0 closed trades in 48h. Filter may be too aggressive OR trades still open. Eval extended to Aug 25 — check if PnL positive. — 2026-08-24
- **Confidence scorer miscalibrated** — 90+ tier has 48.7% WR (worst tier). conf-filter-plan addresses this. — 2026-08-19
- **Coin tracker Wyckoff detection PARTIALLY FIXED** — 25/109 tokens now have phase detected (was 0 Aug 21). 4h candle re-enablement populated data. 84 still 'none'. Monitor for continued improvement. — 2026-08-22
- **4h candles re-enabled** — price_collector.py line 565 re-enabled (CEO Aug 21). Will populate on next price_collector run. Elliott Wave detection will have fresh data. — 2026-08-21

## System Improvement Backlog

1. **Coin tracker Wyckoff detection improving** — 25/109 tokens now (was 0). 4h candle re-enablement helped. 84 still 'none'. Monitor continued improvement. — 2026-08-22
2. **SHORT side signals (CEO PRIORITY)** — R2_TREND_SHORT re-enabled Aug 20 but 0 trades/48h. Need new SHORT signal with edge for SHORT_BIAS regime. DELEGATED to signal_analyst. — 2026-08-21
3. ~~**Re-enable 4h candle collection**~~ — DONE. price_collector.py line 565 re-enabled (CEO Aug 21). — 2026-08-21
4. Higher-timeframe regime for confluence relaxation (1m too noisy)
5. Confidence scorer recalibration (real fix for non-monotonic conf curve)

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor ATR_SL_MIN=1.5% (48h eval ending ~Aug 27 08:05 UTC).** Raised from 1.2% today. Only 1 trade has new SL so far. — 2026-08-25
2. **Monitor CONF_FILTER_MAX=89 (48h eval ending ~Aug 26 15:30 UTC).** 90+ tier +$1.46/7d. 70-79 tier -$5.18/7d (dominant loss, ct-hot+ driven). — 2026-08-25
3. **Monitor MIN_PRE_MOVE 0.3 (eval today Aug 25).** Check if filter producing results. — 2026-08-24
4. **Monitor bb_bounce+ performance.** 72.4% WR +$0.83/7d (today 66.7% — small sample). — 2026-08-25
5. **Monitor hl_copy_trader LONG.** 51.4% WR +$1.98/7d (today 40% — small sample). — 2026-08-25
6. **Monitor disk (85% cleanup trigger).** Currently 82%. — 2026-08-25
7. **DELEGATE to signal_analyst: Build new SHORT signal with edge for SHORT_BIAS regime.** — 2026-08-24
8. **retroactive-scan-delayed-entry** — Only unimplemented plan. Level 3, ~200 LOC. — 2026-08-21
