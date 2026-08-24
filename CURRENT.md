# Current State — System Improvement Focus

**Last Updated: 2026-08-24 ~10:30 UTC (CEO run 247)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (92.9% WR +$14.47/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→3). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False). **SL FLOOR BUG FIXED** (tpsl_utils.py 8 lines — 89% of ATR_SL hits had SL < 1.0% from entry, floor now enforced after every one-way gate). **R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3** (dead-cat bounce filter, r2-trend-long3 losers peak +0.12% MFE). mover+ KILLED (signal_reporter, 28.6% WR -$0.15/7d, NEVER_REENABLE). R2_TREND_SHORT KILLED (0% WR 3T, Aug 20). Runtime DB VACUUMED (87→83MB). **stop_hunt_reversal_long+ KILLED (CEO Aug 20).** 10T/7d 60% WR -$0.04 break-even, 48h deteriorating to 50% -$0.10. Worst ATR_SL offender: 3 hits -$0.38. NEVER_REENABLE. **ct-hot+ ENTIRE FAMILY KILLED (CEO Aug 22, signal_reporter implemented).** ALL 3 flags False + NEVER_REENABLE_FLAGS. 62T/7d 32.3% WR -$4.04. **Health monitor DB fix** — added correct table references to prompt (was crashing on `no such table: trades`). **CONF_FILTER_MAX lowered 89→85 (CEO Aug 23)** — blocks overconfident trades (90+ tier worst WR 48.7%). **hzscore- KILLED (auto_1hr Aug 23 21:05 + signal_reporter, NEVER_REENABLE).**

**Current status:** System HEALTHY and IMPROVING. CEO run 247 (10:30 UTC): 24h 69T +$0.89, 58.0% WR. 7d: 256T -$0.72, 53.1% WR (improving from -$1.04 Aug 23). **SHORT SIDE TURNED PROFITABLE: 28T/24h +$0.35, 67.9% WR** (was 26.9% WR -$1.40/7d last week). CONF_FILTER_MAX=85 working. Winners: bb_bounce+ (88.9% WR, +$0.72/24h), tl_break_short (88.9% WR, +$0.21/7d), macd-div- (100% WR, +$0.32/24h). hl_copy_trader LONG backbone (53.3% WR, +$2.47/7d). profit-monster-trail 27T +$1.66/24h (carrying system). ATR_SL net +$0.05/24h (SL floor fix working). ct-hot+ legacy draining (38.3% WR, -$3.05/7d, age-out Aug 24-25). signal_compactor tracebacks transient DB lock contention. Disk: 83%. Pipeline: 0 errors, all timers active.

## Active Decisions

- **CONF_FILTER_MAX=85 (CEO Aug 23).** Lowered from 89 — 90+ confidence tier has 48.7% WR (worst tier). Blocks overconfident trades. Monitor 48h for WR improvement. — 2026-08-23
- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **macd-div+ DISABLED (CEO KILLED Aug 23).** 4T/7d 25% WR -$0.40. Dead signal, no edge. MACD_DIVERGENCE_PLUS_ENABLED=False. — 2026-08-23
- **SHORT_NEUTRAL_BLOCK_ENABLED=True (CEO Aug 22, FIXED Aug 23).** SHORT signals 7d: 26T -$1.40, 26.9% WR (ALL losing). Was using 1m regime (noisy — showed LONG_BIAS when 4h NEUTRAL, block never fired). FIX: Now uses 4h regime from PostgreSQL momentum_cache. Block fires when 4h regime is NEUTRAL (64 tokens). In SHORT_BIAS (85 tokens), SHORT signals allowed. — 2026-08-23
- **R2_TREND_LONG_MIN_PRE_MOVE 0.3 active.** Dead-cat bounce filter. r2-trend-long3 losers peak +0.12% MFE, winners +0.65%. Monitor 48h for ATR_SL reduction and WR improvement. — 2026-08-19
- **ct-hot+ RE-ENABLED BY T (RESEARCH_FLAGS).** CEO killed Aug 22, T re-enabled same day ("signal starvation fix"). Flags True, NEVER_REENABLE_FLAGS has comments only (no entries). 35T/7d -$3.28, 31.4% WR — DOMINANT LOSER. CEO cannot disable (RESEARCH_FLAGS). Recommend T disable if bleeding continues. Trades age out Aug 24-25. — 2026-08-23
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
- **MAE-GUARD DISABLED (auto-1hr Aug 23).** Was net -$5.43/week at 1.5% threshold. Cuts winners that recover. Threshold raised to 3.0% if re-enabled. — 2026-08-23

## Known Limitations

- **Disk at 83%** — 92G/118G used. Will trigger cleanup at 85%. Monitor. — 2026-08-23
- **7 failed services** — better-coder, bug-hunter, git-release, hl-volume, mtf-macd-tuner, trading-checklist, wasp. All non-critical utilities, not affecting trading. — 2026-08-22
- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). 3 stale records cleaned (ids 10211-10213). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side TURNED PROFITABLE** — 28T/24h +$0.35, 67.9% WR (was 26.9% WR -$1.40/7d last week). tl_break_short 88.9% WR +$0.21/7d. macd-div- 100% WR +$0.32/24h. SHORT_NEUTRAL_BLOCK + 4h regime filtering confirmed working. — 2026-08-24
- **MIN_PRE_MOVE 0.3 eval EXTENDED** — r2-trend-long3 48h: 9T $0.00 66.7% WR (WR improved 55.9%→66.7% but PnL break-even). PM_TRAIL captures winners, ATR_SL hits losers. EXTENDED through Aug 25 (needs PnL positive to justify filter). — 2026-08-21
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

1. **Monitor CONF_FILTER_MAX=85 (48h eval ending ~Aug 25 08:00 UTC).** Blocks confidence >=85. System WR improved. — 2026-08-24
2. **Monitor MIN_PRE_MOVE 0.3 (eval extended to Aug 25).** If still flat, remove filter. — 2026-08-23
3. **Monitor bb_bounce+ performance.** 80% WR, +$0.32 — emerging winner, small sample. — 2026-08-24
4. **ct-hot+ trades age out Aug 24-25.** System clearing naturally. CEO cannot disable (RESEARCH_FLAGS). — 2026-08-24
5. **Monitor PM_TRAIL edge.** Must hold >80% WR. — 2026-08-23
6. **Monitor disk (85% cleanup trigger).** Currently 83%. — 2026-08-24
7. **Monitor Wyckoff detection improvement.** — 2026-08-22
8. **retroactive-scan-delayed-entry** — Only unimplemented plan. Level 3, ~200 LOC. — 2026-08-21
