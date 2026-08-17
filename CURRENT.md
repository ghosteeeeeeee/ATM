# Current State — System Improvement Focus

**Last Updated: 2026-08-17 06:30 UTC
**Updated by: CEO (52nd run)

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (86.5% WR +$1.82/48h). All legacy losers killed. Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→18). hzscore- testing failed (inverted R:R) — killed 2026-08-17. hzscore+ killed 2026-08-17 (32T ~38% WR -$0.47/7d combos bleeding).

**Current status:** System IMPROVING — 24h +$0.61, 57.9% WR. 48h +$0.19, 48.9% WR (positive, improved). PM_TRAIL 37T 86.5% WR +$1.82 (dominant edge). ATR_SL 34T -$2.09 (stable, daily 41→18). R:R 0.87:1. ct-hot+ 33T/48h -$0.42 (user TESTING MODE, clears Aug 17-18). 4 open healthy. 7d: 429T -$2.18, 49.0% WR. hzscore+ killed this run (32T ~38% WR -$0.47/7d combos bleeding). Stars7d: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ flags True (user TESTING MODE).** DO NOT DISABLE. MIN_COMPOSITE 55. — 2026-08-16
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. — 2026-08-17
- **PM_TRAIL dist 0.20% confirmed working.** 86.5% WR +$1.82/48h. R:R 0.87:1. Keep. — 2026-08-17
- **SPEED_MIN 40 active.** ATR_SL daily 41→18. Needs continued eval. — 2026-08-16
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

1. **hzscore+ killed.** 32T ~38% WR -$0.47/7d combos bleeding. Expected +$0.47/7d improvement. — 2026-08-17
2. **PM_TRAIL edge strengthening.** 37T 86.5% WR +$1.82/48h, R:R 0.87:1 (improved from 0.80). — 2026-08-17
3. **24h improving.** +$0.61, 57.9% WR (up from +$0.50/56.4%). — 2026-08-17
4. **48h positive.** +$0.19, 48.9% WR (improved from +$0.03/46.9%). — 2026-08-17
5. **ATR_SL daily stable.** 18/day (from peak 41). SPEED_MIN 40 working. — 2026-08-17
6. **ct-hot+ legacy draining.** 33T/48h -$0.42. User TESTING MODE. Clears Aug 17-18. — 2026-08-17
7. **Stars7d intact.** return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19. — 2026-08-17
