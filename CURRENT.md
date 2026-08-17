# Current State — System Improvement Focus

**Last Updated: 2026-08-17 17:45 UTC (72nd run)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (89% WR +$8.83/7d, R:R 1.94:1). All legacy losers killed (ct-hot+ Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→5). accel-300- standalone bypass KILLED (40T/7d -$0.30, net negative). Phantom trades FIXED (0T, was 9T/7d -$0.06).

**Current status:** System STRONG — 24h 43T +$0.51, 62.8% WR (improving). 1 open LONG (r2-trend-long14 -$0.03, ~flat). PM_TRAIL carrying system (30T/24h 90% WR +$1.25, avg win 0.42%, daily ALL GREEN). ATR_SL 11T/24h -$0.59 (daily: 41→28→28→20→18→7 — 83% reduction, historic low 7/day). R:R 2.12:1 (PM_TRAIL +$1.25 vs ATR_SL -$0.59 — BEST R:R in weeks). ct-hot+ legacy clearing (1T/24h remaining, clears Aug 18). Aug 17: 27T +$0.28, 59.3% WR (3rd green day on track). range_breakout_short re-enabled by user (28T/7d 46.4% WR -$0.21, monitoring).

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ DISABLED (testing ended Aug 17).** 42.4% WR -$0.42/7d. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. — 2026-08-17
- **wave_catcher+ DISABLED (CEO KILLED Aug 17).** Both variants dead (+37.5% WR -$0.42, -25% WR -$0.09). Master switch False. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **accel-300- standalone bypass DISABLED (CEO KILLED Aug 17).** 40T/7d 55% WR -$0.30 — net negative despite PM_TRAIL capturing winners. Removed from STANDALONE_BYPASS. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **SPEED_MIN 40 active.** ATR_SL daily 41→5 (88% reduction, historic low). — 2026-08-16
- **hl_copy_trader in STANDALONE_BYPASS.** Copy-trading bypasses confluence. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Single-type signals allowed in NEUTRAL. — 2026-08-16
- **All range_finder variants disabled.** SHORT side dead. Do NOT enable until SHORT_BIAS regime. — 2026-08-16

## Known Limitations

- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16

## System Improvement Backlog

1. Higher-timeframe regime for confluence relaxation (1m too noisy)
2. SHORT side signals — all range_breakout variants dead, need new SHORT signals for SHORT_BIAS regime

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor PM_TRAIL edge.** 30T/24h 90% WR +$1.25 (avg win 0.42%, R:R 2.12:1, daily ALL GREEN). Must hold >80% WR. — 2026-08-17
2. **Monitor ATR_SL count.** 7 in 24h (daily 41→7, 83% reduction, historic low). Must stay <15/day. — 2026-08-17
3. **ct-hot+ legacy clearing.** 1T/24h remaining. Should clear by Aug 18. — 2026-08-17
4. **Aug 17 daily tracking.** 27T +$0.28, 59.3% WR — 3rd green day on track. — 2026-08-17
5. **range_breakout_short monitoring.** Re-enabled by user Aug 17. 28T/7d 46.4% WR -$0.21. Track for 48h. — 2026-08-17
6. **SHORT side signals.** All range_breakout variants dead except range_breakout_short (user re-enabled). Need new SHORT signals for SHORT_BIAS regime. — 2026-08-17
7. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-17
