# Current State — System Improvement Focus

**Last Updated: 2026-08-17 05:30 UTC
**Updated by: CEO (51st run)

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (80% WR +$1.61/48h). All legacy losers killed. Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→18). hzscore- testing failed (inverted R:R) — killed 2026-08-17.

**Current status:** System IMPROVING — 48h flipped POSITIVE. Verified 24h: 39T +$0.50, 56.4% WR (improved). 48h: 98T +$0.03, 46.9% WR (flipped positive from -$0.15). PM_TRAIL 44T 73.3% WR +$1.73 (dominant). ATR_SL 35T -$2.16 (stable). R:R 0.80:1. ct-hot+ 33T/48h -$0.42 (user TESTING MODE). 2 open flat. 7d: 434T -$2.84, 48.1% WR. Phantom: 7T/7d -$0.10 (minimal). Stars7d: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ flags True (user TESTING MODE).** DO NOT DISABLE. MIN_COMPOSITE 55. — 2026-08-16
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. Testing failed. — 2026-08-17
- **PM_TRAIL dist 0.20% confirmed working.** 80% WR +$1.61/48h. R:R 0.60:1 (improving). Keep. — 2026-08-17
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

1. **48h flipped POSITIVE.** 98T +$0.03, up from -$0.15. System self-correcting. — 2026-08-17
2. **PM_TRAIL edge confirmed.** 44T/48h 73.3% WR +$1.73, R:R 0.80:1. Strongest edge. — 2026-08-17
3. **ATR_SL stable.** 35T/48h, 18 from ct-hot+ (51%). SPEED_MIN 40 working (41→18 daily). — 2026-08-17
4. **ct-hot+ legacy draining.** 33T/48h -$0.42. User TESTING MODE. Clears Aug 17-18. — 2026-08-17
5. **24h improving.** +$0.50, 56.4% WR (up from +$0.21/51.2%). — 2026-08-17
6. **Stars7d intact.** return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19. — 2026-08-17
