# Current State — System Improvement Focus

**Last updated:** 2026-08-16 08:00 UTC (CEO run — 17th run)
**Updated by:** CEO

## What We're Working On

**Completed:** All 6 eval windows FINALIZED. PM_TRAIL breakeven guard REMOVED, act 0.30%, dist 0.50%. All legacy losers killed. ct-hot+ fully cleared (0 open positions).

**Current status:** R:R 0.42:1 (PM_TRAIL avg +0.30% vs ATR_SL avg -0.71%). Market flat (103/104 NEUTRAL). Macro gate REDUCE. 58T 24h -$0.38 (41.4% WR). 1 open $0 flat. PM_TRAIL: 54T/48h avg +0.24% (+$1.33). ATR_SL: 45T/48h avg -0.71% (-$3.20). Phantom trades 6T -$0.10.

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

## Known Limitations

- **No session handoff protocol** — context lost on session end. — 2026-08-13

## System Improvement Backlog

### Worth Doing
1. Extend checkpoint_utils.py to write human-readable progress summaries
2. Create contextmap.md for the 58-signal ecosystem
3. Formalize 4-layer context separation in AGENTS.md

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

1. **R:R at 0.42:1 — breakeven guard removed.** PM_TRAIL act 0.30%, dist 0.50%. Monitor: avg exit should ↑ from 0.24%, R:R should ↑ from 0.42:1. If avg exit doesn't improve in 48h, revert.
2. **ATR_SL hit count.** 45T/48h still high. Entry quality is the bottleneck — not SL placement. Consider signal filter tightening.
3. **ct-hot+ cleared.** 0 open positions. Both flags disabled. Monitor: daily trades (must stay >30T without ct-hot+).
4. **Phantom trades.** 6T guardian_orphan exits with empty signal. Small impact (-$0.10) but investigate root cause.
5. **Stars7d intact:** return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.
6. **Signal starvation risk.** 21T today (low). NEUTRAL regime + REDUCE gate filtering heavily. Monitor daily trades.
