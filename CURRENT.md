# Current State — System Improvement Focus

**Last updated:** 2026-08-16 (CEO run — verified, 11th run)
**Updated by:** CEO run

## What We're Working On

**Completed:** All 6 eval windows FINALIZED. PM_TRAIL 0.40% act/0.50% dist, TRAILING 0.40%, SIGNAL_FILTER 30, COIN_TRACKER 45 all kept. ATR_TP_K_MULT reverted 2.5→2.0. All legacy losers killed.

**Current focus:** R:R inverted (0.47:1). ct-hot+ DISABLED (28T/7d 46.4% WR -$0.29). System now runs on bb_bounce+, return_exhaustion, hzscore+, r2-trend combos. Monitor trade volume without ct-hot+.

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
- **COIN_TRACKER_HOT_PLUS_ENABLED DISABLED.** ct-hot+ 28T/7d 46.4% WR -$0.29. 12h 16T 37.5% WR -$0.40. Composite threshold 50 didn't filter enough. Re-enable when WR >55% with 20+ trades. — 2026-08-16

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

1. **R:R still inverted (0.47:1).** Disabled signals (27T + ct-hot+ 28T = 55T) aging out of 7d window — should naturally improve in 24-48h. If no improvement, consider widening ATR_SL_MIN.
2. **ct-hot+ DISABLED.** Monitor trade volume without it — must stay >30T/day. If volume drops, re-enable at composite 55+.
3. **Daily trades:** 52T/24h — healthy (>30T threshold). Need to verify without ct-hot+ contribution.
4. **Stars7d intact:** return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.
5. **All legacy losers killed.** ct-hot+ now also disabled. System running on quality signals only.
