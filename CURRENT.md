# Current State — System Improvement Focus

**Last Updated: 2026-08-19 ~20:00 UTC (CEO run 146)**
**Updated by: Daily Orchestrator**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (92.9% WR +$14.47/7d). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→3). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False). **SL FLOOR BUG FIXED** (tpsl_utils.py 8 lines — 89% of ATR_SL hits had SL < 1.0% from entry, floor now enforced after every one-way gate). **R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3** (dead-cat bounce filter, r2-trend-long3 losers peak +0.12% MFE). Runtime DB VACUUMED (87→83MB).

**Current status:** System HEALTHY — 24h 24T +$0.11, 62.5% WR (green day). 7d: 320T -$1.59, 51.3% WR (improving). Daily: Aug 12 +$0.82 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 +$0.02 → Aug 16 -$0.49 → Aug 17 +$0.37 → Aug 18 -$0.38 → Aug 19 +$0.11 (green). PM_TRAIL DOMINANT: 170T/7d +$6.61, 86.5% WR (carrying system). ATR_SL: 122T/7d -$9.01, 0.8% WR (historic low: 3/day vs 28 peak Aug 13 — 89% reduction). profit-monster-T1: 12T/7d +$0.69, 100% WR. 1 open position (low exposure). 0 phantom trades. All legacy losers 0T/24h confirmed dead. Market: NEUTRAL (103 neutral / 2 long bias / 0 short). Hotset: empty (normal in NEUTRAL). **conf-filter-plan DEPLOYED** — CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89, TIME_BLOCK_ENABLED=True (01-06 UTC). 90+ tier (114T 49.1% WR -$1.38) now blocked.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **R2_TREND_LONG_MIN_PRE_MOVE 0.3 active.** Dead-cat bounce filter. r2-trend-long3 losers peak +0.12% MFE, winners +0.65%. Monitor 48h for ATR_SL reduction and WR improvement. — 2026-08-19
- **ct-hot+ CLEARED.** 0T/24h, confirmed Aug 18. In NEVER_REENABLE_FLAGS. — 2026-08-18
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. — 2026-08-17
- **wave_catcher+ DISABLED (CEO KILLED Aug 17).** Both variants dead (+37.5% WR -$0.42, -25% WR -$0.09). Master switch False. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **accel-300- standalone bypass DISABLED (CEO KILLED Aug 17).** 40T/7d 55% WR -$0.30 — net negative despite PM_TRAIL capturing winners. Removed from STANDALONE_BYPASS. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **SPEED_MIN 40 active.** ATR_SL daily 41→8.5 (79% reduction, historic low). — 2026-08-16
- **hl_copy_trader in STANDALONE_BYPASS.** Copy-trading bypasses confluence. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Single-type signals allowed in NEUTRAL. — 2026-08-16
- **All range_finder variants disabled.** SHORT side dead. Do NOT enable until SHORT_BIAS regime. — 2026-08-16
- **return_exhaustion_long DISABLED.** 6T/7d legacy clearing. RETURN_EXHAUSTION_ENABLED=False. — 2026-08-19
- **SL FLOOR BUG FIXED.** tpsl_utils.py 8 lines — 89% of ATR_SL hits (126/141) had SL < 1.0% from entry. Floor now enforced after every one-way gate. Monitor 48h for ATR_SL reduction. — 2026-08-19
- **conf-filter-plan DEPLOYED.** CONF_FILTER_ENABLED=True, CONF_FILTER_MAX=89. TIME_BLOCK_ENABLED=True (01-06 UTC). 90+ tier 114T 49.1% WR -$1.38 now blocked. — 2026-08-19

## Known Limitations

- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side structural weakness** — 0T/24h, all legacy dead, need new SHORT signals. — 2026-08-19
- **MIN_PRE_MOVE 0.3 eval** — needs 48h to confirm r2-trend-long3 ATR_SL reduction. — 2026-08-19
- **Confidence scorer miscalibrated** — 90+ tier has 48.7% WR (worst tier). conf-filter-plan addresses this. — 2026-08-19

## System Improvement Backlog

1. **SHORT side signals** — all legacy dead, 0T/24h. DELEGATED to signal_analyst. — 2026-08-19
2. Higher-timeframe regime for confluence relaxation (1m too noisy)
3. Confidence scorer recalibration (real fix for non-monotonic conf curve)

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor MIN_PRE_MOVE 0.3.** r2-trend-long3 ATR_SL reduction expected. 48h eval window through Aug 21. — 2026-08-21
2. **Monitor PM_TRAIL edge.** 170T/7d 86.5% WR. Must hold >80% WR. — 2026-08-21
3. **Monitor ATR_SL count.** 3/day historic low — SL floor fix working. — 2026-08-21
4. **SHORT side signals.** 0T/24h, all legacy dead. DELEGATED to signal_analyst. — 2026-08-20
5. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-20
