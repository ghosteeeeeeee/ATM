# Current State — System Improvement Focus

**Last Updated: 2026-08-20 04:15 UTC (CEO run 161)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (92.9% WR +$14.47/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→3). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False). **SL FLOOR BUG FIXED** (tpsl_utils.py 8 lines — 89% of ATR_SL hits had SL < 1.0% from entry, floor now enforced after every one-way gate). **R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3** (dead-cat bounce filter, r2-trend-long3 losers peak +0.12% MFE). Runtime DB VACUUMED (87→83MB).

**Current status:** System HEALTHY — 24h 24T +$0.45, 70.8% WR (7th consecutive green day). 7d: 288T -$1.47, 51.0% WR (improving). Daily: Aug 13 -$0.85 → Aug 14 -$0.56 → Aug 15 +$0.02 → Aug 16 -$0.49 → Aug 17 +$0.37 → Aug 18 -$0.38 → Aug 19 +$0.42 (7th green). PM_TRAIL DOMINANT: 153T/7d +$5.91, 85.0% WR (carrying system). ATR_SL: 14T/48h -$1.38 (SL floor fix working, historic low). profit-monster-T1: 12T/7d +$0.69, 100% WR. 0 open positions. 0 phantom trades. All legacy losers 0T/24h confirmed dead. Market: NEUTRAL. stop_hunt_reversal_long+: 3T/24h 0% -$0.38 (ATR_SL losses today, monitoring). r2-trend-long3: MIN_PRE_MOVE 0.3 eval active (PM_TRAIL 3T/24h 100% +$0.17). SHORT side: 2T/24h -$0.06 spike_exhaustion_short- only (r2_trend_short, bb_bounce_short still 0T — structural gap, NEUTRAL 0.5x multiplier blocking). Conf-filter: CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89, TIME_BLOCK_ENABLED=True (01-06 UTC). 90+ tier blocked.

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

## Known Limitations

- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side structural weakness** — 0T/24h from enabled signals (r2_trend_short, bb_bounce_short, spike_exhaustion_short-). ALL 69T/7d -$1.60 SHORT PnL from legacy trades. New SHORT signals not firing. — 2026-08-20
- **MIN_PRE_MOVE 0.3 eval** — r2-trend-long3: 29T/7d, ATR_SL 11T -$0.76, PM_TRAIL 16T +$0.64. Eval through Aug 21. — 2026-08-20
- **Confidence scorer miscalibrated** — 90+ tier has 48.7% WR (worst tier). conf-filter-plan addresses this. — 2026-08-19

## System Improvement Backlog

1. **SHORT side signals** — all legacy dead, 0T/24h. DELEGATED to signal_analyst. — 2026-08-19
2. Higher-timeframe regime for confluence relaxation (1m too noisy)
3. Confidence scorer recalibration (real fix for non-monotonic conf curve)

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor MIN_PRE_MOVE 0.3.** r2-trend-long3 29T/7d, ATR_SL 11T → PM_TRAIL 16T — filter working. Eval through Aug 21. — 2026-08-21
2. **Monitor PM_TRAIL edge.** 155T/7d +$6.01. Must hold >80% WR. — 2026-08-21
3. **Monitor ATR_SL count.** 7T/day historic low (68% reduction from 22 peak) — SL floor fix working. — 2026-08-21
4. **SHORT side signals.** 0T/24h from enabled signals. ALL legacy trades. DELEGATED to signal_analyst. — 2026-08-20
5. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-20
