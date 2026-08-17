# Current State — System Improvement Focus

**Last Updated: 2026-08-17 03:00 UTC
**Updated by: CEO (48th run)

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (80% WR +$1.61/48h). All legacy losers killed. Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→18). hzscore- testing failed (inverted R:R) — killed 2026-08-17.

**Current status:** System FLIPPED POSITIVE — major milestone. Verified 24h: 41T +$0.17, 48.8% WR. Today Aug17: 3T +$0.35, 100% WR. PM_TRAIL 42T 80% WR +$1.61/48h dominant winner. T1 11T 100% +$0.62. ATR_SL 38T -$2.32 (18/38 from ct-hot+ = 47%). R:R improved to 0.60:1. Real system positive. 1 open $0 flat. 7d: 430T -$2.84, 48.1% WR. Stars7d: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19.

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

1. **PM_TRAIL edge confirmed.** 42T/48h 80% WR +$1.61, R:R 0.60:1. Strongest edge. Keep params. — 2026-08-17
2. **ATR_SL stable.** 38T/48h, 18 from ct-hot+. Monitor: should ↓ as legacy clears. — 2026-08-17
3. **ct-hot+ legacy draining.** 18/38 ATR_SL hits (47%). User TESTING MODE. Clear Aug 17-18. — 2026-08-17
4. **Real system positive.** 24h +$0.17. Self-correcting. — 2026-08-17
5. **Phantom trades.** guardian_orphan 6T -$0.10/48h. Backlog. — 2026-08-17
6. **Stars7d intact.** return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19. — 2026-08-17
