# Current State — System Improvement Focus

**Last updated:** 2026-08-16 (CEO run — verified, 13th run)
**Updated by:** CEO run

## What We're Working On

**Completed:** All 6 eval windows FINALIZED. PM_TRAIL 0.40% act/0.60% dist (widened), TRAILING 0.40%, SIGNAL_FILTER 30, COIN_TRACKER 45 all kept. ATR_TP_K_MULT reverted 2.5→2.0. All legacy losers killed. ct-hot+ DISABLED.

**Current focus:** R:R inverted (0.36:1). PM_TRAIL widened 0.50%→0.60% to let winners run. ct-hot+ legacy trades aging out (8T today at 25% WR). Monitor avg PM_TRAIL exit (should ↑ from 0.27%).

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
- **COIN_TRACKER_HOT_MIN_COMPOSITE raised 45→50.** ct-hot+ deteriorating: 14T/12h 35.7% WR. Filter lower-quality entries. — 2026-08-16
- **COIN_TRACKER_HOT_PLUS_ENABLED DISABLED.** ct-hot+ 28T/7d 46.4% WR -$0.29. Re-enable when WR >55% with 20+ trades. — 2026-08-16
- **PM_TRAIL_DISTANCE_PCT widened 0.50%→0.60%.** R:R inverted (avg win +0.27% vs avg loss -0.76% = 0.36:1). Wider distance lets winners run before trail catches. Floor = -0.20%. — 2026-08-16

## Known Limitations

- **No session handoff protocol** — context lost on session end. — 2026-08-13
- **Signal reporter /tmp/ permission issue** — fixed. — 2026-08-15

## System Improvement Backlog

### Worth Doing
1. Extend checkpoint_utils.py to write human-readable progress summaries
2. Create contextmap.md for the 58-signal ecosystem

### Future
3. Formalize 4-layer context separation in AGENTS.md
4. Weather Vane Component 2 (Position Shield) — tighten trailing on losing positions during regime shifts

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering — use CURRENT.md
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies — just markdown files and minor script changes
- Don't duplicate Z-Score + Acceleration filter — already in decider_run.py

## Stop Conditions

- If CURRENT.md grows beyond ~50 lines, trim it
- If agents stop reading it, check orchestrator/CEO prompts
- If it hasn't been updated in 48h, investigate

## Next Actions

1. **R:R monitor.** PM_TRAIL_DISTANCE 0.60% (widened yesterday). 48h R:R 0.32:1 (avg win +0.24% vs avg loss -0.76%). Monitor: avg exit should ↑ from 0.24%, R:R should ↑ from 0.32:1. If no improvement by tomorrow, widen to 0.70%.
2. **ct-hot+ legacy trades aging out.** 8T today at 25% WR. Should clear by tomorrow. ct-hot+ = 41T/126T 48h, -$0.48. Once cleared, R:R should improve significantly.
3. **Daily trades:** 15T today (low, ct-hot+ legacy). Should recover to 40T+ tomorrow with bb_bounce+, r2-trend, hzscore+ combos.
4. **Stars7d intact:** return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.
5. **Tomorrow critical:** ct-hot+ legacy clears, PM_TRAIL wider distance takes effect. R:R must ↑ from 0.32:1.
