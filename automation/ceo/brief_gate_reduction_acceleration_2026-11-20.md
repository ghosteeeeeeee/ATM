# CEO DECISION BRIEF — "GATES KILLING TRADES" (T: "this is getting ridiculous, it should have been resolved weeks ago")

Requested by T, urgent. Package: `plans/2026-11-20_crash-zero-trade-fixpath.md` · `analysis/crash_window_forensics_2026-11-20.py/.out` (audit-corrected, ce4ab417) · `brain/verdicts/2026-11-20-crash-forensics-own-conclusions.md` (7 corrections applied) · lineage: Oct-8 gate audit (dual-verified) → Oct-12 conundrum D1-D6 (your ALL-GO) → Oct-30 shadow v2 (your 6/6) → Nov-19/20 usefulness deep dive (56 gates, self-audit 6/6, own-conclusions 8 defects corrected) → Nov-20 deep run D1-D7 (CONTINUUM shadow-first shipped, review 12-04) → THIS crash incident. 0 config changes at any stage.

## T's position (verbatim): "we need to figure out what gates are killing trades, this is getting ridiculous, it should have been resolved weeks ago"

The analysis HAS been done — repeatedly and adversarially verified. What has NOT happened is execution at the pace the evidence supports. Current state:

- **27 no-edge gates = 82.4% of all block volume** (46d, cluster-robust, Bonferroni; `nov19_gate_summary.tsv`). They neither help nor hurt per block (|excess|<0.10%) — but they fire continuously: funnel is **93.5:1 blocked:trades** and worsening weekly (21:1 → 93.5:1).
- **Crash incident (Nov 20):** DailyFillCap engaged the whole window killed 84 ready candidates; underneath, the funnel is a **one-way valve** — 298 signals expired, 9 (3.0%) ever converted to a trade; four starvation modes (blocked@approval 170 at 2% recovery, merge-window loop 65, hotset rotation 47, confluence staleness 42). Blocked signals ≈ market (auditor's crash-leg test −0.045%, n=189) — so this is starvation + capital-lock, not a proven goldmine refused.
- **Only ONE removal has shipped in weeks:** CONTINUUM-BLOCK+BULL shadow-first (Nov-20, review 12-04). The other 25 no-edge gates are untouched, queued behind the R1 extended closer (deep run 11-27) and your D7 detection-limit statement — which explicitly says detection limits **never block shadow-first removals** (they're reversible). The blocking instrument is therefore a scheduling choice, not a data gap.
- Two mechanism bugs identified with NO edge question attached: merge-window age-inheritance (P1 — re-fires expire their own pending predecessor every 300s; successor chains loop) and hotset rotation (P2 — approved signals rotated out before execution, 47 rows).

## Decisions requested (reply GO/NAY + dates)

D1. **P1 merge-window fix** — GO to ship shadow-first now? One UPDATE in signal_schema.py (fresh row inherits predecessor's age clock), WOULD-INHERIT-AGE telemetry 14d, review date you set. Mechanism bug: no threshold, no edge claim, no constant touched.

D2. **P2 hotset dwell** — pick one: (a) dwell floor for APPROVED rows (min N cycles before rotation), (b) immediate-execute queue for APPROVED rows, (c) accept rotation as intended churn. (a) recommended, shadow-first.

D3. **DailyFillCap capital decision** (binding crash constraint): (a) keep as-is, (b) SHORT-side carve-out during high-|BTC|-momentum windows, (c) sawtooth tuning (max-15 higher in crash windows), (d) manual T/CEO override protocol. This is capital risk — your call.

D4. **ACCELERATED gate-reduction program (the core ask).** T's frustration: weeks of analysis, one removal shipped. Proposal — batch shadow-first demotion of the no-edge gates, on the already-ratified principle (D7: removals are reversible; detection limits never block them):
- **Batch 1 (this week):** top-5 no-edge gates by volume — CONFLUENCE-GATE-BLOCK (3,436 eps), CONTINUUM-BLOCK/BULL already live, SHORT-RSI-HARD-FLOOR (2,194), LONG-NEUTRAL-CHOP (1,915), LONG-NEUTRAL (1,791), SHORT-NEUTRAL (1,637) — demote to WOULD-BLOCK telemetry + confidence-multiplier (×0.7) instead of hard kill, 14d, review cadence weekly in kanban.
- **Batch 2 (week 2):** next 6 by volume (OVERSOLD-SHORT, RR-ENGINE hard-block tier, PUMP-CHAIN-SHORT-HIGH, CTX-GATE LLM, SHORT-CONTINUUM, PUMP-CHAIN-HIGH).
- **Batch 3 (week 3):** remainder + the MDE-qualified small gates.
- **Success metrics per batch:** trades/day ↑ toward 25-30, block:trade ratio ↓, loss-rate NOT worse than baseline (7d WR/ net vs pre-batch), each gate's admitted cohort counterfactual reported. Any batch that degrades loss-rate reverts that gate immediately.
- **Guardrails unchanged:** no removal without shadow-first telemetry; hermes_constants untouched (demotions are multiplier/flag changes in signal_compactor/decider, each needing your GO per line 2); the 2 WORKS gates (PUMP-CHAIN-RSI-MAX, LONG-RSI-CEILING) and 3 fully-redundant (CONTINUUM pair live, PRESERVE-SPIKE pending) are OUT of scope for demotion.

D5. **R1 extended closer:** keep 11-27, or accelerate to unblock dollar-level decisions sooner? (D4's batch telemetry may make it less blocking.)

D6. **Accountability/cadence:** weekly gate-reduction status to kanban every Friday (blocks:trades ratio, trades/day, per-batch cohort counterfactuals) until the funnel is healthy — so "resolved weeks ago" never happens again by default.

## Constraints honored
hermes_constants.py untouched; no gate removed live except your CONTINUUM pair (shadow-first, reversible, review 12-04); all claims cluster-tested per SOPs §10; every number traceable to committed .out/TSV or the verdict file; DO-NOT-MODIFY and protected flags intact.
