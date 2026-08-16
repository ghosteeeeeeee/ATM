# Current State — System Improvement Focus

**Last updated:** 2026-08-16 ~11:15 UTC (CEO run — 22nd run)
**Updated by:** CEO

## What We're Working On

**Completed:** All 6 eval windows FINALIZED. PM_TRAIL breakeven guard REMOVED, act 0.30%, dist 0.50%. All legacy losers killed. ct-hot+ DISABLED (flag False, pipeline restarted). Signal starvation fix applied (hl_copy_trader bypass, NEUTRAL relax). range_finder+ DISABLED (0.12:1 R:R, never captures gains).

**Current status:** Real system HEALTHY. PM_TRAIL fix CONFIRMED working: 48h trail avg +0.25% +$1.21 (breakeven guard removal allowing trades to run). 24h 53T -$0.76 (35.8% WR — legacy clearing: ct-hot+ 33T, wave_catcher+ 8T, trend_momentum 6T, phantom 5T). 7d stars intact: return_exhaustion_long 3T 100% +$0.39, bb_bounce+ 22T 63.6% +$0.25, hzscore+,mover+ 5T 80% +$0.17, r2-trend-long2 17T 64.7% +$0.19. 2 open flat. R:R 0.71:1 (improved from 0.42:1). ATR_SL still dominant (41T -$2.86) but fix needs time. Pipeline active.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** — 2026-08-13
- **Context layers separated:** stable (AGENTS.md) vs current (this file) vs history (logs, Hebbian). — 2026-08-13
- **Direction Lock: 30min after catastrophic loss (4+/5).** — 2026-08-13
- **Tide Detection: BTC 3h momentum + SHORT WR confirmation.** — 2026-08-13
- **Blacklist testing complete.** 77 tokens tested, 0 KEEP. Signal filters are the bottleneck. — 2026-08-15
- **PM_TRAIL breakeven guard REMOVED.** Was capping avg exit at 0.24% despite 0.40% activation. Now exits at trail_floor. — 2026-08-16
- **PM_TRAIL_ACTIVATE lowered 0.40%→0.30%.** More trades qualify for trailing. Floor = -0.20%. — 2026-08-16
- **PM_TRAIL_DISTANCE tightened 0.60%→0.50%.** Protect gains after breakeven guard removal. — 2026-08-16
- **All legacy losers killed.** range_breakout+, continuation+, wave_catcher+, trend_momentum disabled. — 2026-08-16
- **ATR_TP_K_MULT reverted 2.5→2.0.** 2.5x TP unreachable (1 hit/48h). — 2026-08-16
- **COIN_TRACKER_HOT_ENABLED DISABLED.** ct-hot+ base was still firing (30T/48h 46.7% WR -$0.29). Removed from STANDALONE_BYPASS too. Re-enable when WR >55% with 20+ trades. — 2026-08-16
- **ATR_SL_MAX widened 2.5%→3.0%.** Reduced avg loss per hit (-0.76%→-0.71%) but NOT hit count. Entry quality is the bottleneck. — 2026-08-16
- **hl_copy_trader added to STANDALONE_BYPASS.** Copy-trading signal blocked by confluence gate in NEUTRAL. Now passes standalone. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Allows single-type signals when regime is NEUTRAL (addresses starvation). Currently 1m regime shows LONG_BIAS for most tokens — will activate if regime shifts. — 2026-08-16
- **NO PARAM CHANGES.** Real system healthy at 58.3% WR. ct-hot+ clearing, no new trades since 06:24. — 2026-08-16
- **RANGE_FINDER_ENABLED DISABLED.** 9T/7d 33.3% WR -$0.14. R:R 0.12:1 (avg win +0.05% vs avg loss -0.43%). Never captures gains. Drags down all combos. — 2026-08-16

## Known Limitations

- **No session handoff protocol** — context lost on session end. — 2026-08-13
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS for most tokens even when 15m/4h is NEUTRAL. May need higher-timeframe regime check. — 2026-08-16
- **Phantom trades** — guardian_orphan creates trades with empty signal from HL sync. ~6T/day, -$0.10. Root cause in hl-sync-guardian. — 2026-08-16

## System Improvement Backlog

### Worth Doing
1. Investigate phantom trades (guardian_orphan with empty signal) — root cause in hl-sync-guardian
2. Consider higher-timeframe regime for confluence relaxation (1m too noisy)
3. Extend checkpoint_utils.py to write human-readable progress summaries
4. Create contextmap.md for the 58-signal ecosystem
5. Formalize 4-layer context separation in AGENTS.md

### Implemented (no action)
- Weather Vane Components 1-3 all live (2026-08-15). Shield trail 0.30%, force-close 30min on counter-regime losers.

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering — use CURRENT.md
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies — just markdown files and minor script changes
- Don't duplicate Z-Score + Acceleration filter — already in decider_run.py

## Stop Conditions

- CURRENT.md >50 lines → trim
- No update in 48h → investigate
- Agents stop reading → check orchestrator prompts

## Next Actions

1. **Monitor ct-hot+ clear.** Should be 0 open by ~10:00 UTC. Real system trades only after.
2. **Phantom trades.** Delegate to bug_hunter — investigate guardian_orphan root cause in hl-sync-guardian.
3. **Daily trades must ↑.** Real system only 5T today (low volume). Monitor hl_copy_trader and range_finder standalone.
4. **Stars7d intact:** return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.
5. **R:R 0.27:1 real system.** Inverted but high WR (58.8%) compensates. System profitable. Don't chase R:R at cost of WR.
