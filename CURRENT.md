# Current State — System Improvement Focus

**Last Updated: 2026-08-17 (55th run)
**Updated by: CEO

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (84.6% WR +$1.85/48h). All legacy losers killed (hzscore+ Aug 17, wave_catcher+ Aug 14, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 13). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→33).

**Current status:** System STRONGEST IN DAYS — 24h +$0.64, 61.1% WR (improved). 48h +$0.28, 49.5% WR (positive). 7d 429T -$2.05, 49.2% WR. Aug 17: 9T +$0.53, 77.8% WR (EXCELLENT). PM_TRAIL 39T 84.6% WR +$1.85 (DOMINANT, 0.46% avg win). ATR_SL 33T -$2.03 (stable, daily 41→33). R:R 0.73:1. ct-hot+ 33T/48h -$0.42 (user TESTING MODE, clears Aug 17-18). 4 open ~flat. Guardian_orphan 7T -$0.10 (phantom). Stars7d: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19. Market NEUTRAL (106 tokens, 3 accumulation).

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ flags True (user TESTING MODE).** DO NOT DISABLE. MIN_COMPOSITE 55. — 2026-08-16
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. — 2026-08-17
- **PM_TRAIL dist 0.20% confirmed working.** 84.6% WR +$1.85/48h. R:R 0.87:1. Keep. — 2026-08-17
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

1. **ct-hot+ testing clears Aug 17-18.** Expect system improvement when legacy drain stops. — 2026-08-17
2. **PM_TRAIL edge strong.** 39T 84.6% WR +$1.85/48h. Keep. — 2026-08-17
3. **24h STRONG.** +$0.64, 61.1% WR (best in days, improved from 59.5%). — 2026-08-17
4. **48h positive.** +$0.28, 49.5% WR. — 2026-08-17
5. **ATR_SL daily stable.** 33/day (from peak 41). SPEED_MIN 40 working. — 2026-08-17
6. **Market NEUTRAL.** 106 tokens, 3 accumulation (SOL, BTC, DOGE). Signal starvation expected. — 2026-08-17
7. **Stars7d intact.** return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19. — 2026-08-17
8. **hzscore+ killed.** bb_bounce+ should recover from 36.8% to ~58% WR without hzscore+ drag. — 2026-08-17
9. **Aug 17 tracking 77.8% WR.** Best day in a week. — 2026-08-17
