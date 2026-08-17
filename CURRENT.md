# Current State — System Improvement Focus

**Last Updated: 2026-08-17 (58th run)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (84.6% WR +$1.85/48h). All legacy losers killed (ct-hot+ Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 13). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→33).

**Current status:** System STRONG — 24h 33T 63.6% WR +$0.68. 2 open ~flat. PM_TRAIL continuing to carry. ATR_SL 32/48h -$2.06 (18 from ct-hot+ legacy). All legacy losers killed. Aug 17: 11T +$0.55, 72.7% WR.

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

1. **Monitor PM_TRAIL edge.** 38T +$1.87/48h. Must hold >80% WR. — 2026-08-17
2. **Monitor ATR_SL count.** 33/day (stable). Must stay <35/48h. — 2026-08-17
3. **ct-hot+ legacy clearing.** Should clear by Aug 18 naturally. — 2026-08-17
4. **Aug 17 daily tracking.** 10T +$0.55, 80% WR — on track for best day in weeks. — 2026-08-17
5. **Market NEUTRAL.** 106 tokens, 3 accumulation. Signal starvation expected. — 2026-08-17
6. **Investigate phantom trades.** guardian_orphan ~6T/day -$0.10 — root cause in hl-sync-guardian. — 2026-08-17
7. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-17
