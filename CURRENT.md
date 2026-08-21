# Current State — System Improvement Focus

**Last Updated: 2026-08-21 03:00 UTC (CEO run)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (92.9% WR +$14.47/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→3). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False). **SL FLOOR BUG FIXED** (tpsl_utils.py 8 lines — 89% of ATR_SL hits had SL < 1.0% from entry, floor now enforced after every one-way gate). **R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3** (dead-cat bounce filter, r2-trend-long3 losers peak +0.12% MFE). mover+ KILLED (signal_reporter, 28.6% WR -$0.15/7d, NEVER_REENABLE). R2_TREND_SHORT KILLED (0% WR 3T, Aug 20). Runtime DB VACUUMED (87→83MB). **stop_hunt_reversal_long+ KILLED (CEO Aug 20).** 10T/7d 60% WR -$0.04 break-even, 48h deteriorating to 50% -$0.10. Worst ATR_SL offender: 3 hits -$0.38. NEVER_REENABLE.

**Current status:** System HEALTHY — 24h 18T -$0.54, 50.0% WR (flat, SHORT legacy fully cleared). 7d: 260T -$1.39, 50.4% WR. PM_TRAIL: 138T/7d +$5.11, 82.6% WR (carrying system). ATR_SL: 96T/7d -$7.21, historic low count. 0 open positions (clean). SHORT legacy drain COMPLETE — all positions closed. continuation+ 4T/7d -$0.24 25% WR (tiny sample, 0T/24h). Conf-filter: CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89, TIME_BLOCK_ENABLED=True (01-06 UTC). 90+ tier blocked.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **R2_TREND_LONG_MIN_PRE_MOVE 0.3 active.** Dead-cat bounce filter. r2-trend-long3 losers peak +0.12% MFE, winners +0.65%. Monitor 48h for ATR_SL reduction and WR improvement. — 2026-08-19
- **ct-hot+ CLEARED.** 0T/24h, confirmed Aug 18. In NEVER_REENABLE_FLAGS. — 2026-08-18
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. — 2026-08-17
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
- **R2_TREND_SHORT_ENABLED False (CEO KILLED Aug 20).** 3T/48h 0% WR -$0.23. NEUTRAL market too sideways for -0.003 slope filter. All ATR_SL hits. Added to NEVER_REENABLE_FLAGS. — 2026-08-20
- **stop_hunt_reversal_long+ KILLED (CEO KILLED Aug 20).** 10T/7d 60% WR -$0.04 break-even, 48h deteriorating to 50% -$0.10. Worst ATR_SL offender: 3 hits -$0.38/48h. Break-even not good enough — system needs edge. NEVER_REENABLE. — 2026-08-20
- **SHORT legacy drain COMPLETE.** All remaining SHORT positions (r2-trend-short2/10/13) closed. 0 open positions. — 2026-08-21

## Known Limitations

- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). 3 stale records cleaned (ids 10211-10213). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side structural weakness** — ALL legacy SHORT positions now closed (0 open). Gap remains: no active SHORT signals for SHORT_BIAS regime. — 2026-08-21
- **MIN_PRE_MOVE 0.3 eval EXTENDED** — r2-trend-long3 48h: 9T $0.00 66.7% WR (WR improved 55.9%→66.7% but PnL break-even). PM_TRAIL captures winners, ATR_SL hits losers. EXTENDED through Aug 25 (needs PnL positive to justify filter). — 2026-08-21
- **Confidence scorer miscalibrated** — 90+ tier has 48.7% WR (worst tier). conf-filter-plan addresses this. — 2026-08-19

## System Improvement Backlog

1. **SHORT side signals** — R2_TREND_SHORT killed (0% WR in NEUTRAL). Need new SHORT signals for SHORT_BIAS regime. — 2026-08-20
2. Higher-timeframe regime for confluence relaxation (1m too noisy)
3. Confidence scorer recalibration (real fix for non-monotonic conf curve)

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor MIN_PRE_MOVE 0.3 (EXTENDED to Aug 25).** r2-trend-long3 48h: 9T $0.00 66.7% WR (break-even, WR improved but PnL flat). If still break-even by Aug 25, filter is noise-reducing not edge-creating — consider removing. — 2026-08-21
2. **Monitor PM_TRAIL edge.** 138T/7d +$5.11, 82.6% WR. Must hold >80%. — 2026-08-21
3. **Monitor ATR_SL count.** 96T/7d -$7.21, 1% WR. SL floor fix active. — 2026-08-21
4. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-20
5. **Confidence scorer recalibration.** 90+ tier has 48.7% WR (worst tier). Real fix for non-monotonic conf curve. — 2026-08-20
