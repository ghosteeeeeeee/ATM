# Current State — System Improvement Focus

**Last Updated: 2026-08-17 (56th run)
**Updated by: Daily Orchestrator

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (84.6% WR +$1.85/48h). All legacy losers killed (ct-hot+ Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 14, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 13). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→33).

**Current status:** System STRONG — 24h 33T 66.7% WR +$0.77. 4 open ~flat. Market NEUTRAL (106 tokens). PM_TRAIL DOMINANT (84.6% WR +$1.85/48h). ATR_SL stable (33/day). ct-hot+ disabled (testing ended, 42.4% WR -$0.42). Stars7d: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 58.3% +$0.21, r2-trend-long2 64.7% +$0.19.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ DISABLED (testing ended Aug 17).** 42.4% WR -$0.42/7d. In NEVER_REENABLE_FLAGS. — 2026-08-17
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

1. **Verify bb_bounce+ recovery.** Should improve from 36.8% to ~58% WR without hzscore+ combo drag. — 2026-08-17
2. **Monitor wave_catcher+.** 40% WR (15T) — borderline, auto-kill if drops below 30%. — 2026-08-17
3. **PM_TRAIL edge strong.** 84.6% WR +$1.85/48h. Keep. — 2026-08-17
4. **ATR_SL daily stable.** 33/day (from peak 41). SPEED_MIN 40 working. — 2026-08-17
5. **Market NEUTRAL.** 106 tokens, 3 accumulation. Signal starvation expected. — 2026-08-17
6. **Investigate phantom trades.** guardian_orphan ~6T/day -$0.10 — root cause in hl-sync-guardian. — 2026-08-17
7. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-17
