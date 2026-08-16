# Current State — System Improvement Focus

**Last Updated: 2026-08-16 23:55 UTC
**Updated by: CEO (45th run)

## What We're Working On

**Completed:** PM_TRAIL dist 0.15% WORKING (74.4% WR +$1.27/48h, R:R 2.70:1). All legacy losers killed. Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→18).

**Current status:** System IMPROVING. Last 3h: 7T +$0.17 71.4% WR (STRONG). Real system excl ct-hot+: 48T/48h +$0.22 50.0% WR (POSITIVE). PM_TRAIL 39T 74.4% WR +$1.27 (R:R 2.70:1 — strongest edge). T1 12T 100% WR +$0.69. ATR_SL 38T 2.6% WR -$2.32 (daily improving 41→18). ct-hot+ 33T/48h 42.4% WR -$0.42 (user TESTING MODE, flags True). 3 open ~$0 flat. 7d: 437T -$2.62 48.5% WR. Stars7d: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ flags True (user TESTING MODE).** DO NOT DISABLE. MIN_COMPOSITE 55. — 2026-08-16
- **hzscore- True (user TESTING MODE).** 35T 54.3% WR -$0.22/7d. Monitor. — 2026-08-16
- **PM_TRAIL dist 0.15% confirmed working.** 74.4% WR +$1.27/48h, R:R 2.70:1. Keep. — 2026-08-16
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

1. **PM_TRAIL edge confirmed.** 39T/48h 74.4% WR +$1.27, R:R 2.70:1. Strongest edge. Keep params. — 2026-08-16
2. **ATR_SL improving.** Daily: 41→18 (SPEED_MIN 40 working). Monitor: must ↓ from 38/48h. — 2026-08-16
3. **ct-hot+ legacy draining.** 33T/48h -$0.42 (user TESTING MODE). Clear Aug 17-18. — 2026-08-16
4. **Real system positive.** Last 3h 7T +$0.17 71.4% WR. Self-correcting. — 2026-08-16
5. **Phantom trades.** guardian_orphan 6T -$0.10/48h. Backlog. — 2026-08-16
6. **Stars7d intact.** return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19. — 2026-08-16
