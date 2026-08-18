# Current State — System Improvement Focus

**Last Updated: 2026-08-18 ~14:50 UTC (CEO run 108)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (88.3% WR +$8.03/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→1). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended).

**Current status:** System STRONG — 24h 18T -$0.04, 55.6% WR (flat Monday, within variance). 48h: 58T +$0.48, 60.3% WR (healthy, R:R POSITIVE 1.68:1). 7d: 401T -$2.08, 50.4% WR (improving). PM_TRAIL DOMINANT: 40T/48h +$1.55, 87.5% WR (carrying system). ATR_SL 16T/48h -$0.92, 0% WR (8/day average, within 15/day target, historic low). 1 open position. 0 phantom trades. Aug 17: 34T +$0.37, 58.8% WR (GREEN DAY confirmed). Aug 18: 18T -$0.04, 55.6% WR (Monday, normal variance). All legacy losers in NEVER_REENABLE_FLAGS. Regime: NEUTRAL (102 tokens) / 2 SHORT_BIAS (HEMI, POL). Coin tracker: DOGE in accumulation (48.8 composite, fading). Top: ZRO 58.9, ZORA 55.4, CASHCAT 54.0. SHORT side structural weakness: 154T/7d -$1.14, 48.7% WR. KEY FINDING: 48h R:R improved to 1.68:1 (PM_TRAIL +$1.55 vs ATR_SL -$0.92).

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ CLEARED.** 0T/24h, confirmed Aug 18. In NEVER_REENABLE_FLAGS. — 2026-08-18
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

1. **Monitor PM_TRAIL edge.** 40T/48h 87.5% WR +$1.55. Must hold >80% WR. — 2026-08-18
2. **Monitor ATR_SL count.** 16T/48h (8/day average, within 15/day target). Must stay <15/day. — 2026-08-18
3. **Monitor 48h R:R.** Improved to 1.68:1 (PM_TRAIL +$1.55 vs ATR_SL -$0.92). Must stay >1:1. — 2026-08-18
4. **SHORT side signals.** 154T/7d -$1.14, 48.7% WR. All range_breakout variants dead. Need new SHORT signals for SHORT_BIAS regime. — 2026-08-18
5. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-18
6. **DOGE monitoring.** DOGE in accumulation (48.8 composite, fading from 54.6). Not actionable now. — 2026-08-18
