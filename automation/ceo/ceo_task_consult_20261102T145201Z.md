# CONSULT RUN 20261102T145201Z (UTC)

You are running a BOUNDED, READ-ONLY consult. Base persona/rules follow after this block.

## HARD LIMITS (this run)
- **BUDGET: ~15 minutes (extended consult: CEO_CONSULT_BUDGET=900s). This is a DEEP consult — work the question thoroughly: read the relevant code (cite file:line) and run the SQL you need to verify every number you cite. Still READ-ONLY — recommend, do not edit. Depth welcome; the ~400-word soft cap below does not apply when the brief demands a detailed answer.**
- **READ-ONLY. Do NOT edit ANY file. Do NOT change params, flags, or blacklists.**
- Do NOT develop signals. Do NOT tune signals. Do NOT dispatch subagents.
- Do NOT write to ceo_report.md or ceo_kanban.md — answer HERE, in this session.
- No session lock is held. If you believe an edit is needed, say so as a recommendation and stop.

## THE QUESTION
Answer the directed brief below. Verify any numbers you cite with a quick query (base prompt SQL rules apply — never trust old reports). Give a clear VERDICT (approve/reject/modify + rationale). If the brief asks for a review, lead with the verdict, then the reasons.

--- BRIEF ---
# BRIEF: mfe-exit parameters + loss-side options (T consult, 2026-11-01)

**From:** Hermes agent session (in-DSH, T's direct request) · **Type:** consult = OPINION ONLY, no edits
**Full report:** `/root/.hermes/brain/reports/2026-11-01_mfe-exit-performance-and-loss-options.md`
**Verdict to respect:** `brain/verdicts/2026-10-31_mfe-exit-sim-independent-verify.md` (independent auditor: direction robust, magnitude not decision-grade; p=0.135 vs actual closes, n=45)

## Context you need

- **mfe-exit** (shipped 2026-10-31, commits `e56e7942`/`e40c3cf8`): closes a mirror trade when price gives back **30% of peak favorable move**, engaging only after peak ≥ **0.40% price** (`MFE_EXIT_ARM_PCT=0.004`, `MFE_EXIT_GIVEBACK_PCT=0.30`, scope `jup_yolo` signals only, revert = `MFE_EXIT_ENABLED=False`). The first no-arm run churned (38s–5min fee-negative closes) — T called it "isn't exactly what we were looking for"; armed run since then: **8/8 wins, +1.6…+2.35% lev, holds 17min–5.4h**.
- **Grid** (83 closed mirror trades, audited replay engine, fees −0.45% lev/trade): giveback 40% **loses to 30% at every arm**. Arms (giveback 30%): 0.00 → +36.50 gross/−0.85 after fee; **0.20 → +54.11/+16.76, WR 85%, holds 0.7h**; **0.40 (shipped) → +50.71/+13.36, WR 77%, holds 1.2h**; 0.65 → +38.58/+1.23, holds 2.5h; 1.00 → −26.32 (42/83 never engage → floor). Shipped stack = pm-trail + mfe together: `pm+g30_arm0.40` = **+16.65 after fee, 77% WR**. Reality (pm_actual) = −45.01 after fee, WR 64%.
- **Entry quality:** 61% of mirror entries ≥ +0.20% favorable in first 15m (median +0.28%); median time-to-peak 226min, median peak +0.91% — T's read: "the REALLY good ones have entries right after the peak/trough."
- **Loss attribution (83 closed):** atr_sl_hit 12 (−53.8) + hard_max_loss 10 (−42.0) = 22/28 losses, both ≈ −0.8…−0.9% price @5x; stale 2 (−11.1); cut-loser-CL-T1 1; mfe_exit 3 (−0.8 total). Sizes are at the **$11.1 notional floor** — cannot shrink.
- **Your own standing constraints:** `PM_TRAIL_*`/`CUT_LOSER_PNL`/blacklists are protected (T/CEO only); automatic-implementation = shadow → OOS → enforce; MFE-CUT universal timeout FAILED candle-OOS (40.2% false-kills) — signal-scoped is the only proven path.

## Questions (opinion requested)

**Q1 — mfe-exit parameters.** T asked "see if 40% gives better returns; we want the trade to survive longer AND potentially more profit." Grid says: giveback 40% is strictly worse; arm 0.40 (shipped) is the best *balance*; arm 0.20 makes ~26% more profit but holds drop to 0.7h; arm 0.65 doubles holds but after-fee profit ≈ 0. **Do you ratify shipped arm 0.40 / giveback 0.30, or would you steer to 0.20 (profit) or another rule entirely (e.g., giveback that widens with peak, time-component)?** State your recommendation + one-line rationale.

**Q2 — loss-side ladder (T: "report only").** Which would you pursue, in what order, and what ships as shadow vs enforce-now?
   a. **JUP HML shadow eval is DUE** (45 distinct ≥ pre-registered N=40): evaluate −0.65/−0.50 price vs current −0.80 baseline; enforce if net-positive. Opinion: run the eval now? Any methodology guardrails you insist on?
   b. **jup-scoped never-armed TAT** (never reach +0.40% peak by 45–60min → cut): ship as shadow only, given MFE-CUT's OOS failure class?
   c. **`CUT_LOSER_PNL` −4.00 → −3.00**: you tightened direction? (brain_auditor just moved −6→−4 on 10-31.)
   d. **ATR-SL unit-mismatch fix** (SL de-facto fixed 2.50% system-wide): system-wide now, jup-scoped floor first, or defer?

**Q3 — anything you see that we're missing** in this picture (sample-size discipline, fee/slippage, entry-side instead of exit-side, etc.).

## Format

Numbered answers Q1/Q2/Q3, concrete (values + where they'd change), no edits — T implements.
--- END BRIEF ---

## OUTPUT
Print your answer to this session (stdout). Do NOT append to any report file. Max ~400 words unless the brief demands more detail.
