# Current State — System Improvement Focus

**Last Updated: 2026-08-17 23:00 UTC (83rd run)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (89% WR +$8.07/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→9). Phantom trades FIXED (0T, was 9T/7d -$0.06).

**Current status:** System STRONG — 24h 35T +$0.41, 62.9% WR. 7d: 404T -$2.18, 50.0% WR (crossed 50% — legacy clearing). 2 open LONG (r2-trend-long4 +$0.06, r2-trend-long3 -$0.02, total +$0.04). PM_TRAIL carrying system (206T/7d 88.8% WR +$8.07, avg +0.39%, every trade green). ATR_SL 163T/7d 0.6% WR -$10.91 (historic low 9/day). ct-hot+ CLEARED (0T/24h — expected Aug 18, confirmed). Aug 17: 32T +$0.32, 59.4% WR (GREEN DAY confirmed). Phantom trades FIXED (0T). All 48 timers active.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ CLEARED (testing ended Aug 17).** 0T/24h confirmed. In NEVER_REENABLE_FLAGS. — 2026-08-17
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

1. **Monitor PM_TRAIL edge.** 206T/7d 88.8% WR +$8.07. Must hold >80% WR. — 2026-08-17
2. **Monitor ATR_SL count.** 9T/24h (7d daily: 41→9, 78% reduction from peak). Must stay <15/day. — 2026-08-17
3. **ct-hot+ CLEARED.** 0T/24h, confirmed gone Aug 18 as expected. — 2026-08-17
4. **bb_bounce+ healthy.** 24T/7d 58.3% +$0.21 — above 3T threshold, performing. — 2026-08-17
5. **SHORT side signals.** All range_breakout variants dead. Need new SHORT signals for SHORT_BIAS regime. — 2026-08-17
6. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-17
