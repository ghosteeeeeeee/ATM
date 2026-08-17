# Current State — System Improvement Focus

**Last Updated: 2026-08-17 13:15 UTC (65th run)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (88.8% WR +$8.12/7d). All legacy losers killed (ct-hot+ Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 13). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→5).

**Current status:** System STRONG — 24h 40T +$0.36, 57.5% WR. 3 open (ICP -0.17%, CFX +0.39%, ETH +0.06%). PM_TRAIL carrying system (206T/7d +$8.12, 88.8% WR). ct-hot+ legacy clearing. Aug 17: 19T +$0.17, 52.6% WR (GREEN DAY on track). ATR_SL daily 41→5 (88% reduction). R:R 0.71:1.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ DISABLED (testing ended Aug 17).** 42.4% WR -$0.42/7d. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. — 2026-08-17
- **wave_catcher+ DISABLED (CEO KILLED Aug 17).** Both variants dead (+37.5% WR -$0.42, -25% WR -$0.09). Master switch False. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **SPEED_MIN 40 active.** ATR_SL daily 41→33. Needs continued eval. — 2026-08-16
- **hl_copy_trader in STANDALONE_BYPASS.** Copy-trading bypasses confluence. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Single-type signals allowed in NEUTRAL. — 2026-08-16
- **All range_finder variants disabled.** SHORT side dead. Do NOT enable until SHORT_BIAS regime. — 2026-08-16

## Known Limitations

- **Phantom trades** — guardian_orphan ~6T/day -$0.10 (empty signal from HL sync). — 2026-08-16
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16

## System Improvement Backlog

1. Investigate phantom trades (guardian_orphan) — root cause in hl-sync-guardian
2. Higher-timeframe regime for confluence relaxation (1m too noisy)

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor PM_TRAIL edge.** 206T/7d +$8.12 (88.8% WR). Must hold >80% WR. — 2026-08-17
2. **Monitor ATR_SL count.** 5 in 24h (daily 41→5, 88% reduction). Must stay <15/day. — 2026-08-17
3. **ct-hot+ legacy clearing.** 25T/48h -$0.56 remaining, should clear by Aug 18. — 2026-08-17
4. **Aug 17 daily tracking.** 19T +$0.17, 52.6% WR — on track for green day. — 2026-08-17
5. **Investigate phantom trades.** guardian_orphan 8T/7d -$0.09 — root cause in hl-sync-guardian. — 2026-08-17
6. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-17
