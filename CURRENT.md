# Current State — System Improvement Focus

**Last Updated:** 2026-08-16 15:20 UTC  
**Updated by:** CEO (31st run — verified)

## What We're Working On

**Completed:** All eval windows FINALIZED. PM_TRAIL dist 0.15% WORKING (66.7% WR +$1.09/48h). All legacy losers killed. range_finder+ DISABLED (0.12:1 R:R). range_finder- DISABLED (0% WR SHORT). Signal starvation fix applied (hl_copy_trader bypass, NEUTRAL relax). COIN_TRACKER_HOT DISABLED (36% WR).

**Current status:** Legacy clearing. 24h 51T -$0.55 (37.3% WR — legacy-heavy). 48h: 82 LONG -$0.49 (46.3% WR) + 13 SHORT -$0.50 (7.7% WR). 7d 437T -$2.54 (48.5% WR). Today Aug16: 26T -$0.71 (23.1% WR — worst day, legacy draining). 1 open SYRUP LONG r2-trend-long5 flat (-$0.03). PM_TRAIL 48h: 36T 69.4% WR +$1.07 (avg +0.29%). ATR_SL 48h: 39T 2.6% WR -$2.65 (avg -0.68%). R:R 0.43:1 (PM_TRAIL +0.29% vs ATR_SL -0.68%). Regime NEUTRAL (104N/0L/1S). SHORT side dead (7.7% WR). All range_finder variants disabled. Pipeline active.

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
- **PM_TRAIL_DISTANCE_PCT reverted 0.50%→0.15%.** Per user request (commit a0a971a). Working: 66.7% WR +$1.09 (avg +0.273%). Floor = +0.15%. Keep. — 2026-08-16
- **All legacy losers killed.** range_breakout+, continuation+, wave_catcher+, trend_momentum disabled. — 2026-08-16
- **ATR_TP_K_MULT reverted 2.5→2.0.** 2.5x TP unreachable (1 hit/48h). — 2026-08-16
- **COIN_TRACKER_HOT_ENABLED DISABLED.** 25T/24h 36% WR -$0.56. ATR_SL 18T 0% WR -$1.23 dominates. Re-enable when WR >55% with 20+ trades. — 2026-08-16
- **ATR_SL_MAX widened 2.5%→3.0%.** Reduced avg loss per hit (-0.76%→-0.71%) but NOT hit count. Entry quality is the bottleneck. — 2026-08-16
- **hl_copy_trader added to STANDALONE_BYPASS.** Copy-trading signal blocked by confluence gate in NEUTRAL. Now passes standalone. — 2026-08-16
- **CONFLUENCE_NEUTRAL_RELAX=True.** Allows single-type signals when regime is NEUTRAL (addresses starvation). — 2026-08-16
- **RANGE_FINDER_ENABLED DISABLED.** 9T/7d 33.3% WR -$0.14. R:R 0.12:1. — 2026-08-16
- **RANGE_FINDER_MINUS_ENABLED DISABLED.** 3T/48h SHORT 0% WR -$0.12. Bleeds both directions. — 2026-08-16
- **RANGE_FINDER_SHORT_ENABLED DISABLED.** All range_finder variants dead. — 2026-08-16
- **SHORT side is a net drag.** 13T/48h 7.7% WR -$0.50. Only range_finder- was active SHORT — now killed. Other SHORTs (accel-300-, hzscore-, bb-bounce-short) are legacy clearing. Do NOT enable new SHORT signals until regime shifts to SHORT_BIAS. — 2026-08-16

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

- Don't modify hermes_constants.py for temporary steering — use CURRENT.md (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies — just markdown files and minor script changes
- Don't duplicate Z-Score + Acceleration filter — already in decider_run.py

## Stop Conditions

- CURRENT.md >50 lines → trim
- No update in 48h → investigate
- Agents stop reading → check orchestrator prompts

## Next Actions

1. **Monitor ct-hot+ clear.** Legacy 33T/48h clearing. Should age out by Aug 17-18. No new trades.
2. **SHORT side audit.** All range_finder SHORT killed. Other SHORTs (accel-300-, hzscore-, bb-bounce-short) are legacy clearing. Do NOT re-enable until regime shifts.
3. **PM_TRAIL 0.15% dist monitoring.** Working at 66.7% WR. Must hold >60% WR over 48h.
4. **Phantom trades.** 6T/48h -$0.10, root cause in guardian_orphan (hl-sync-guardian). Backlog item.
5. **ATR_SL entry quality.** 39T/48h, 2.6% WR -$2.65. Entry quality bottleneck — requires signal-level changes. Monitor.
6. **Stars7d intact:** return_exhaustion_long 3T 100%, bb_bounce+ 22T 63.6%, r2-trend-long2 17T 64.7%.
