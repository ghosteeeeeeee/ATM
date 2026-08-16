# Current State — System Improvement Focus

**Last updated:** 2026-08-16 08:25 UTC (CEO run — 18th run)
**Updated by:** CEO

## What We're Working On

**Completed:** All 6 eval windows FINALIZED. PM_TRAIL breakeven guard REMOVED, act 0.30%, dist 0.50%. All legacy losers killed. ct-hot+ fully cleared (0 open positions). Signal starvation fix applied.

**Current status:** R:R 0.35:1 (PM_TRAIL 53T 71.7% WR +$1.38 vs ATR_SL 43T 2.3% WR -$3.04). 57T 24h -$0.44 (40.4% WR). 48h 117T -$0.87 (45.3% WR). 7d 453T -$2.41 (48.8% WR). 1 open -$0.04 flat. Today 21T -$0.62 (19% WR — legacy ct-hot+ 11T + phantoms 5T + 5 real). hl_copy_trader now passes confluence gate.

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

## Known Limitations

- **No session handoff protocol** — context lost on session end. — 2026-08-13
- **NEUTRAL relax not triggering** — 1m regime shows LONG_BIAS for most tokens even when 15m/4h is NEUTRAL. May need higher-timeframe regime check. — 2026-08-16

## System Improvement Backlog

### Worth Doing
1. Extend checkpoint_utils.py to write human-readable progress summaries
2. Create contextmap.md for the 58-signal ecosystem
3. Formalize 4-layer context separation in AGENTS.md
4. Investigate phantom trades (guardian_orphan with empty signal) — root cause
5. Consider higher-timeframe regime for confluence relaxation (1m too noisy)

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

1. **Monitor hl_copy_trader bypass.** Should generate HYPE, ETH, SOL trades. Daily trades must ↑ from 21T.
2. **R:R still inverted at 0.35:1.** PM_TRAIL wins but ATR_SL dominates losses. Entry quality is the bottleneck.
3. **ATR_SL 43T/48h 2.3% WR.** Consider signal filter tightening or ATR_SL_MAX further widening.
4. **Phantom trades.** 5T today guardian_orphan with empty signal. Investigate root cause in hl-sync-guardian.
5. **Stars7d intact:** return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.
