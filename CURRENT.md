# Current State — System Improvement Focus

**Last Updated: 2026-08-20 23:00 UTC (CEO run)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (92.9% WR +$14.47/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→3). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False). **SL FLOOR BUG FIXED** (tpsl_utils.py 8 lines — 89% of ATR_SL hits had SL < 1.0% from entry, floor now enforced after every one-way gate). **R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3** (dead-cat bounce filter, r2-trend-long3 losers peak +0.12% MFE). mover+ KILLED (signal_reporter, 28.6% WR -$0.15/7d, NEVER_REENABLE). R2_TREND_SHORT KILLED (0% WR 3T, Aug 20). Runtime DB VACUUMED (87→83MB).

**Current status:** System HEALTHY — 24h 26T -$0.34, 57.7% WR (red day — SHORT legacy clearing expected after R2_TREND_SHORT kill Aug 20, will age out). 7d: 275T -$1.59, 50.5% WR. PM_TRAIL DOMINANT: r2-trend-long3 18T/7d 94.4% +$0.69 (carrying system). ATR_SL: r2-trend-long3 13T/7d -$0.99 (main active offender). 0 open positions. SHORT legacy clearing: r2-trend-short2 -$0.23, r2-trend-short13 -$0.13, r2-trend-short10 -$0.11 = -$0.47 total (draining after kill Aug 20). LONG side today: r2-trend-long6 3T +$0.25 100%, r2-trend-long3 7T -$0.02 71.4% (IMPROVED), stop_hunt 5T +$0.01 60%, bb_bounce+ 1T +$0.07 100%. stop_hunt_reversal_long+: 10T/7d 60% -$0.04 (break-even, 48h ATR_SL 3T -$0.38 worst offender). r2-trend-long3 MIN_PRE_MOVE 0.3: 7T/24h 71.4% -$0.02 (IMPROVED from 57.6% 7d avg, eval wraps Aug 21). Conf-filter: CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89, TIME_BLOCK_ENABLED=True (01-06 UTC). 90+ tier blocked.

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

## Known Limitations

- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). 3 stale records cleaned (ids 10211-10213). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side structural weakness** — signals firing (NEAR SHORT tl_break_short, ONDO SHORT r2-trend-short2) but blocked by vol gate (ATR > storm threshold). Market condition, not bug (confirmed2026-08-19 short-bias-fix plan). — 2026-08-20
- **MIN_PRE_MOVE 0.3 eval** — r2-trend-long3: 29T/7d, ATR_SL 11T -$0.76, PM_TRAIL 16T +$0.64. Eval through Aug 21. — 2026-08-20
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

1. **Monitor MIN_PRE_MOVE 0.3.** r2-trend-long3: 7T/48h 71.4% +$0.06, 2 ATR_SL -$0.20. Eval through Aug 21. — 2026-08-21
2. **Monitor PM_TRAIL edge.** 151T/7d +$5.89, 84.8% WR. Must hold >80%. — 2026-08-21
3. **Monitor ATR_SL count.** 7T/day historic low (75% reduction from 28 peak) — SL floor fix working. — 2026-08-21
4. **Monitor stop_hunt_reversal_long+.** Borderline (break-even 7d), worst 48h ATR_SL offender (3 hits -$0.38). Watch for degradation. — 2026-08-21
5. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-20
6. **Confidence scorer recalibration.** 90+ tier has 48.7% WR (worst tier). Real fix for non-monotonic conf curve. — 2026-08-20
