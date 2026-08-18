# Current State — System Improvement Focus

**Last Updated: 2026-08-18 02:14 UTC (90th run)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (88.5% WR +$8.07/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→9). Phantom trades FIXED (0T, was 9T/7d -$0.06).

**Current status:** System STRONG — 24h 33T +$0.02, 54.5% WR. 7d: 402T -$2.09, 50.0% WR. PM_TRAIL DOMINANT: accel-300- $1.05/7d (22T 100% WR), hzscore- $0.95/7d (19T 100% WR), bb_bounce+ $0.69/7d (13T 100% WR). ATR_SL 160T/7d 0.6% WR -$10.74 (daily: 41→9→1, historic low). 0 open positions (clean). ct-hot+ legacy 33T/7d 42.4% -$0.42 clearing. Aug 17: 34T +$0.37, 58.8% WR (GREEN DAY). Aug 18: 2T $0.00 (early). 0 phantom trades. All 48 timers active. KEY FINDING: 94.4% of ATR_SL trades peaked green but never reached PM_TRAIL activation (+0.40%) — structural issue.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ CLEARING (legacy, expected gone Aug 18).** 1T/24h, 46T/7d 43.5% -$0.50 (all variants). In NEVER_REENABLE_FLAGS. — 2026-08-18
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

1. **Monitor PM_TRAIL edge.** 208T/7d 88.5% WR +$8.07. Must hold >80% WR. — 2026-08-18
2. **Monitor ATR_SL count.** 9T/24h (7d daily: 41→9, 78% reduction from peak). Must stay <15/day. — 2026-08-18
3. **ct-hot+ clearing.** Expected gone, monitoring. — 2026-08-18
4. **SHORT side signals.** All range_breakout variants dead. Need new SHORT signals for SHORT_BIAS regime. — 2026-08-18
5. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-18
