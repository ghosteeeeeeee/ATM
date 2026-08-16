# Current State — System Improvement Focus

**Last updated:** 2026-08-16 (CEO run — verified, 8th run)
**Updated by:** CEO run

## What We're Working On

**Completed:** Progressive context shaping (CURRENT.md) + Weather Vane v2+v4 upgrades + all 8 upgrade plans + eval window (PM_TRAIL, ATR, trailing params).

**Current focus:** Eval windows closing TOMORROW (Aug 17) — 6 windows need final decisions. R:R improving (0.38:1 → 0.75:1) but still inverted.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** — 2026-08-13
- **Context layers separated:** stable (AGENTS.md) vs current (this file) vs history (logs, Hebbian). — 2026-08-13
- **Direction Lock: 30min after catastrophic loss (4+/5).** — 2026-08-13
- **Tide Detection: BTC 3h momentum + SHORT WR confirmation.** — 2026-08-13
- **Blacklist testing complete.** 77 tokens tested, 0 KEEP. Signal filters are the bottleneck. — 2026-08-15
- **PM_TRAIL_ACTIVATE reverted to 0.40%.** Eval showed 0.60% hurt R:R. — 2026-08-16
- **All legacy losers killed.** range_breakout+, continuation+, wave_catcher+, trend_momentum disabled. — 2026-08-16

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

1. **CRITICAL — Eval windows close TOMORROW (Aug 17).** 6 eval windows need final decisions: PM_TRAIL 0.40% act/0.50% dist, ATR_TP_K_MULT 2.5, TRAILING_ACTIVATION_PCT 0.40%, SIGNAL_FILTER_SPEED_MIN 30, COIN_TRACKER_HOT_MIN_COMPOSITE 45. Tomorrow's run must evaluate all 6 and make final calls.
2. **R:R improving but still inverted:** 0.38:1 earlier → 0.75:1 now (avg win 0.49% / avg loss -0.66%). PM_TRAIL 62T avg +0.26% (+$1.69), ATR_SL 50T avg -0.76% (-$3.83). Still cutting winners too early.
3. **ct-hot+ monitoring:** 4T today all ATR_SL at -0.89% avg. Could be noise (5T total) or deterioration from 57-61% 7d WR. Watch tomorrow.
4. **SHORT legacy aging out:** ct-hot- killed (4T 0% WR). Remaining SHORT legacy trades closing.
5. **Daily trades:** 58T/24h — healthy (>30T threshold). Aug 15 recovered to 54T from 15T low.
6. **Stars7d intact:** return_exhaustion_long 3T 100%, hzscore+,mover+ 5T 80%, r2-trend-long2 17T 64.7%, bb_bounce+ 22T 63.6%.
7. **All legacy losers now killed:** range_breakout+, continuation+, wave_catcher+, trend_momentum all disabled. No more bleeding signals to turn off.
