# Current State — System Improvement Focus

**Last updated:** 2026-08-16 06:30 UTC (Daily Orchestrator — 15th run)
**Updated by:** Daily Orchestrator

## What We're Working On

**Completed:** All 6 eval windows FINALIZED. PM_TRAIL 0.40% act/0.60% dist (widened), TRAILING 0.40%, SIGNAL_FILTER 30, COIN_TRACKER 45 all kept. ATR_TP_K_MULT reverted 2.5→2.0. All legacy losers killed. ct-hot+ fully cleared (0 open positions).

**Current status:** Market flat (103/104 NEUTRAL). Macro gate REDUCE (25% WR < 30). 58 trades today, -5.89% PnL. R:R monitoring PM_TRAIL wider distance effect.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** — 2026-08-13
- **Context layers separated:** stable (AGENTS.md) vs current (this file) vs history (logs, Hebbian). — 2026-08-13
- **Direction Lock: 30min after catastrophic loss (4+/5).** — 2026-08-13
- **Tide Detection: BTC 3h momentum + SHORT WR confirmation.** — 2026-08-13
- **Blacklist testing complete.** 77 tokens tested, 0 KEEP. Signal filters are the bottleneck. — 2026-08-15
- **PM_TRAIL_ACTIVATE reverted to 0.40%.** Eval showed 0.60% hurt R:R. — 2026-08-16
- **All legacy losers killed.** range_breakout+, continuation+, wave_catcher+, trend_momentum disabled. — 2026-08-16
- **ATR_TP_K_MULT reverted 2.5→2.0.** 2.5x TP unreachable (1 hit/48h). — 2026-08-16
- **COIN_TRACKER_HOT_ENABLED DISABLED.** ct-hot+ base was still firing (30T/48h 46.7% WR -$0.29). Removed from STANDALONE_BYPASS too. Re-enable when WR >55% with 20+ trades. — 2026-08-16
- **PM_TRAIL_DISTANCE_PCT widened 0.50%→0.60%.** R:R inverted (avg win +0.27% vs avg loss -0.76% = 0.36:1). Wider distance lets winners run before trail catches. — 2026-08-16
- **ATR_SL_MAX widened 2.5%→3.0%.** ATR_SL dominant drag: 45T -$3.32 (avg loss -0.753%). R:R inverted 0.52:1 (PM_TRAIL avg win +0.39% vs ATR_SL avg loss -0.75%). Wider SL gives trades room to reach PM_TRAIL activation (+0.40%). Monitor: ATR_SL hit count (should ↓), PM_TRAIL capture (should ↑). — 2026-08-16

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

1. **R:R monitor.** PM_TRAIL_DISTANCE 0.60% (widened 2 days ago) + ATR_SL_MAX 3.0% (widened today). Monitor avg exit % and R:R toward 1:1. CTX-GATE currently blocking signals (low volatility).
2. **Market flat.** 103/104 tokens NEUTRAL. No directional bias to trade against. System in REDUCE mode (25% WR). Wait for regime shift.
3. **Stars7d intact:** return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.
4. **Signal starvation risk.** If daily trades <20T when market moves, review SIGNAL_FILTER thresholds.
