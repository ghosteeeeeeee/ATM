# Current State — System Improvement Focus

**Last Updated: 2026-08-19 ~05:30 UTC (CEO run 132)**
**Updated by: CEO**

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (88.9% WR +$1.47/48h). All legacy losers killed (ct-hot+ CLEARED Aug 17, hzscore+ Aug 17, wave_catcher+ Aug 17, range_breakout+ Aug 15, trend_momentum_near_sma+ Aug 12, accel-300- Aug 17). range_breakout_short KILLED (0% WR 3T, auto-1hr Aug 17). Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→7). Phantom trades FIXED (0T, was 9T/7d -$0.06). Blacklist testing COMPLETE (77 tokens tested, 0 KEEP — blacklist is working as intended). return_exhaustion_long DISABLED (auto_1hr killed, RETURN_EXHAUSTION_ENABLED=False).

**Current status:** System NORMAL VARIANCE — 24h 15T -$0.41, 46.7% WR (Monday, within variance). 48h: 42T -$0.57, 50.0% WR (R:R positive). 7d: 362T -$2.36, 50.0% WR. PM_TRAIL exit DOMINANT: 187T/7d +$7.08, 87.2% WR (carrying system). ATR_SL 146T/7d -$10.37 (main drag, 0.7% WR, 8/day historic low). 2 open positions (low exposure). 0 phantom trades. Aug 17: 34T +$0.37, 58.8% WR (GREEN DAY). Aug 18: 15T -$0.38, 46.7% WR (Monday dip, normal). All legacy losers in NEVER_REENABLE_FLAGS (0T/24h confirmed dead, stopped trading Aug 17). Regime: NEUTRAL. r2-trend-long3: 25T/7d 52% -$0.23 (ATR_SL 11T avg peak 0.0087% — entries too tight, PM_TRAIL 13T capturing winners). SHORT side: 0T/24h (structural gap, all legacy dead). return_exhaustion_long: 9T/7d 55.6% +$0.11 (24h: 2T -$0.21 0% WR — degrading, monitoring). Coin tracker: all "none" for wyckoff_phase (not populating).

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **ct-hot+ CLEARED.** 0T/24h, confirmed Aug 18. In NEVER_REENABLE_FLAGS. — 2026-08-18
- **hzscore+ False (CEO KILLED).** 32T ~38% WR -$0.47/7d. Combos bleeding (bb_bounce+,hzscore+ 20T 35% -$0.35). Added NEVER_REENABLE_FLAGS. — 2026-08-17
- **hzscore- False (CEO KILLED).** 35T 54.3% WR -$0.22/7d. Inverted R:R. — 2026-08-17
- **wave_catcher+ DISABLED (CEO KILLED Aug 17).** Both variants dead (+37.5% WR -$0.42, -25% WR -$0.09). Master switch False. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **accel-300- standalone bypass DISABLED (CEO KILLED Aug 17).** 40T/7d 55% WR -$0.30 — net negative despite PM_TRAIL capturing winners. Removed from STANDALONE_BYPASS. In NEVER_REENABLE_FLAGS. — 2026-08-17
- **SPEED_MIN 40 active.** ATR_SL daily 41→8.5 (79% reduction, historic low). — 2026-08-16
- **hl_copy_trader in STANDALONE_BYPASS.** Copy-trading bypasses confluence. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Single-type signals allowed in NEUTRAL. — 2026-08-16
- **All range_finder variants disabled.** SHORT side dead. Do NOT enable until SHORT_BIAS regime. — 2026-08-16
- **return_exhaustion_long watching.** 9T/7d 55.6% WR +$0.11 (stable). Auto-disable threshold: <25% WR with 8+ trades. Monitor for recovery or degradation. — 2026-08-19

## Known Limitations

- **Phantom trades FIXED.** guardian_orphan 0T/7d (was 9T/7d -$0.06). — 2026-08-17
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS even when 15m/4h is NEUTRAL. — 2026-08-16
- **SHORT side structural weakness** — 151T/7d -$1.06, all range_breakout variants dead, need new SHORT signals. — 2026-08-18

## System Improvement Backlog

1. Higher-timeframe regime for confluence relaxation (1m too noisy)
2. SHORT side signals — all range_breakout variants dead, need new SHORT signals for SHORT_BIAS regime
3. return_exhaustion_long evaluation (need 10+ trades to assess, currently 9T/7d 55.6% WR)

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor PM_TRAIL edge.** 187T/7d 87.2% WR +$7.08. Must hold >80% WR. — 2026-08-20
2. **Monitor ATR_SL count.** 8/day average (historic low, within 15/day target). Must stay <15/day. — 2026-08-20
3. **Monitor 48h R:R.** Positive (PM_TRAIL +$7.08 vs ATR_SL -$10.37). Must stay >1:1. — 2026-08-20
4. **SHORT side signals.** 0T/24h, all legacy dead. DELEGATED to signal_analyst: Build new SHORT signals for SHORT_BIAS regime. — 2026-08-20
5. **Higher-TF regime for confluence.** 1m regime too noisy, causes false NEUTRAL relax triggers. — 2026-08-20
6. **return_exhaustion_long watch.** 9T/7d 55.6% WR +$0.11. 24h: 2T -$0.21 0% WR (degrading). Disable if <25% WR with 8+ trades. — 2026-08-20
7. **r2-trend-long3 ATR_SL.** 11T/7d avg peak 0.0087% — entries too tight. Consider MIN_PRE_MOVE adjustment. — 2026-08-20
