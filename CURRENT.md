# Current State — System Improvement Focus

**Last Updated:** 2026-08-16 20:30 UTC  
**Updated by:** CEO (38th run)

## What We're Working On

**Completed:** PM_TRAIL dist 0.20% WORKING (70% WR +$0.26/48h). All legacy losers killed. Signal starvation fix (hl_copy_trader bypass, NEUTRAL relax). SPEED_MIN 40 deployed (ATR_SL daily: 41→15).

**Current status:** ct-hot+ USER TESTING MODE (flags True, "DO NOT DISABLE"). 17T/24h -$0.58 29.4% WR — 18/36 ATR_SL hits are ct-hot+. Non-ct-hot real system: 22T/24h flat (-$0.01). PM_TRAIL 48h: 10T 70% WR +$0.26 (avg +0.23%). ATR_SL 48h: 36T avg -0.70% -$2.50 (92% of losses). R:R inverted 0.33:1. 7d: 436T -$2.49 (48.6% WR). Stars7d: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 22T 63.6% +$0.25, r2-trend-long2 17T 64.7% +$0.19. SIGNAL_FILTER_SPEED_MIN 40 eval window active (needs 24h). Market bearish. 3 open flat ($0.00).

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
- **SHORT side is a net drag.** 12T/48h 8.3% WR -$0.40. All range_finder SHORT killed. Do NOT enable new SHORT signals until regime shifts to SHORT_BIAS. — 2026-08-16
- **COIN_TRACKER_HOT DISABLED AGAIN.** MIN_COMPOSITE 55 still bleeding — 10T opened today 18.2% WR -$0.51. Real system (excl ct-hot+) 43.2% WR nearly flat. Re-enable only with composite 70+ after backtest. — 2026-08-16
- **SIGNAL_FILTER_SPEED_MIN raised 30→40.** ATR_SL 37T/48h 2.7% WR -$2.45 dominates. Higher speed min = fewer but better entries. NEUTRAL override at15 unchanged. — 2026-08-16
- **WAVE_CATCHER_MINUS_ENABLED DISABLED.** Was True per user testing, but 4T/48h 25% WR -$0.09. No edge. — 2026-08-16
- **continuation removed from STANDALONE_BYPASS.** CONTINUATION_ENABLED=False but was in bypass list. Dead signals shouldn't bypass confluence. — 2026-08-16
- **signal_reporter kill bug found.** Agent added ct-hot+/- to NEVER_REENABLE_FLAGS but didn't set flags to False. Flags still True at runtime. Compactor suppression (0.5x/0.3x) works — signals don't reach hotset. Prompt updated with verification step. — 2026-08-16

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

1. **ATR_SL eval window.** SPEED_MIN 40 deployed today. ATR_SL daily: 41→15. If still >25/48h after 24h → raise to 45. — 2026-08-16
2. **ct-hot+ user TESTING MODE.** Flags True (user re-enabled). 17T/24h -$0.58 29.4% WR. 18/36 ATR_SL hits are ct-hot+. Cannot disable. Monitor WR trend. — 2026-08-16
3. **PM_TRAIL 0.20% dist.** 70% WR +$0.26/48h. Must hold >60%. — 2026-08-16
4. **R:R 0.33:1** — inverted. PM_TRAIL +0.23% vs ATR_SL -0.70%. Structural constraint at 0.20% dist. Only lever: reduce ATR_SL frequency. — 2026-08-16
5. **Stars7d intact:** return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 22T 63.6% +$0.25, r2-trend-long2 17T 64.7% +$0.19. — 2026-08-16
6. **Phantom trades.** guardian_orphan 3T -$0.14/48h. Backlog item. — 2026-08-16
7. **Legacy age-out.** ct-hot+ old entries clearing Aug 17-18. — 2026-08-16
