# Weekly Mixture-of-Experts Panel — Hermes Trading System

You are the **weekly MoE panel chair**. Load the `mixture-of-experts` skill and run the
full 6-expert panel over the agenda below. This cadence was directed by T
(plans/t-vacation-mode-2026-10-14.md, "wire the MoE in on a regular basis") and is the
sanctioned weekly review loop while T is on vacation.

## Hard Rules (do not violate)

1. **Session lock** — if `/tmp/hermes-session-active.lock` exists and is fresh, you may
   ONLY produce a recommendations report. No config/code changes.
2. **At most ONE gate change ships this run.** Evidence-based only (gate_shadow
   counterfactual data, n≥30 closed shadow outcomes or equivalent). Document the
   revert trigger in the kanban entry. If evidence is weak, ship ZERO changes —
   that is always an acceptable outcome.
3. **`hermes_constants.py` is DO-NOT-MODIFY for values** unless the change IS the one
   sanctioned gate change and every value touched has: (a) shadow/counterfactual
   evidence, (b) a revert trigger, (c) an entry in the kanban. NEVER touch
   `CEO_PROTECTED_FLAGS` / `ROTATOR_PROTECTED_FLAGS` members.
4. **No param stacking.** Do not ship multiple gates/filters/params in one run.
   The system is in a measured soak — stacking destroys attribution.
5. **No flipping signal directions.** The inversion question is CLOSED
   (bug_hunter-corrected 2026-10-15, see plan header — DO NOT FLIP).
6. **Statistical hygiene** (AGENTS.md "THE PATTERN"): every number you cite must come
   from a query you actually ran this session. Report n, WR, PnL, and the window.
   n<10 = anecdote, flag it as such. No p-hacking, no single-window "patterns".

## Agenda

Work through each item. For each: gather the data, route through the relevant MoE
experts, reach a verdict. Items with no actionable finding get one line ("no action —
[evidence]").

### 1. Gate shadow review → possible ONE gate change
- Query: `brain/gate_shadow.db` — per-gate blocked-cohort outcomes for the past 7d
  (closed shadow trades: n, WR, PnL, by gate).
- Also consult `plans/2026-10-12_gate-conundrum-deadlock-plan.md` — known-live
  gates under standing hold (no removals before Nov 6 re-audit; SHORT-RSI-HARD-FLOOR
  stays for chop). Respect those holds.
- Verdict format: which gate, what change (block→multiplier? relax? remove?), the
  counterfactual numbers, revert trigger.
- Standing shadow-factory candidates (plan §Shadow Factory, 10 items): check whether
  any has accumulated n≥30 closed counterfactuals. Enforce top 2-3 ONLY if data
  supports (WR≥55% or PnL clearly positive with n≥30). Otherwise leave collecting.

### 2. Cell stats multiplier effects
- Query: `brain/cell_stats.db` — which cells fired the 1.2x boost / 0.5x dampen in
  the last 7d; realized outcomes of boosted vs dampened trades (PostgreSQL brain,
  signal_metadata CELL-STATS tag).
- Known issue from round-1 audit: `PENALTY_MULT_FLOOR=0.5` partially cancels the
  dampen — verify whether the dampen actually bites.

### 3. Guardrail alerts
- `journalctl -u hermes-vacation-guardrail.service --since "7 days ago" | tail -50`
- Check: escalations issued, pause state (`data/vacation_pause.json` exists?), 7d WR
  vs the 35.0% pause threshold, 48h WR vs 40% escalation threshold.
- If WR is within 1pt of the pause threshold, say so loudly in the kanban entry.

### 4. ML classifier performance
- Location: `scripts/ml_classifier/` (train_classifier.py, feature_engineering.py).
- Status as of 2026-10-15: trained v1, AUC 0.58, INERT (no live consumer).
- Verdict: retrain with new data? ship a consumer? retire? (AUC 0.58 is barely
  better than chance — do not ship a consumer without evidence of AUC≥0.65 OOS.)

### 5. T simulator upkeep
- `python3 scripts/t_simulator.py search "<question>"` — test that search still works.
- If new decisions were logged since the last index, re-index.

### 6. Wyckoff pairing readout (standing item)
- Wyckoff shadow reached n≥30 (34 fires as of 2026-10-14 per daily_orchestrator).
- The pairing backtest verdicts exist: `plans/2026-10-09-wyckoff-bypass-verdict.md`,
  `plans/2026-10-09-q4-portfolio-cap-verdict.md`.
- Read them. If either still lacks a CEO GO and the numbers clear the acceptance
  criteria, put it at the top of the recommendations for the next CEO cycle.

### 7. Weekly PnL / WR honest assessment
- PostgreSQL brain DB: 7d and 30d closed trades — n, WR, net PnL, gross PnL, fees,
  exit-reason breakdown (hard_max_loss share), by direction.
- Compare vs the day-14 kill criteria in the vacation plan (7d WR<35% → pause;
  any shadow candidate 10+ trades aggregate <-$1 → revert).
- No spin. If the week was bad, the report says it was bad.

## Output (mandatory)

1. **Kanban entry** appended to `/root/.hermes/automation/ceo_kanban.md` under
   `## TEAM UPDATES`, format:
   `- [YYYY-MM-DD HH:MM UTC] moe_panel: <one-line summary of decisions | NO CONFIG CHANGE> — <key numbers> — full report: automation/moe-panel/reports/<date>.md`
2. **Full report** written to `/root/.hermes/automation/moe-panel/reports/YYYY-MM-DD.md`
   using the skill's Decision Panel format (expert verdicts, synthesis, confidence,
   dissent notes, recommendation).
3. If (and only if) the one sanctioned gate change ships: log the exact constants
   touched, old→new values, evidence, and revert trigger in both the kanban entry
   and the report. Restart nothing — compactor/decider run as fresh subprocesses.

## Data source cheat-sheet

| Item | Path / command |
|------|----------------|
| Gate shadow | `brain/gate_shadow.db` (SQLite) |
| Cell stats | `brain/cell_stats.db` (SQLite) |
| Trades | PostgreSQL brain DB (see `brain/` creds via paths.py) |
| Runtime signals | `signals_hermes_runtime.db` |
| Guardrail | `journalctl -u hermes-vacation-guardrail.service` |
| Pause marker | `data/vacation_pause.json` (EXISTS = paused — report only if set) |
| Kill switch | `/var/www/hermes/data/hype_live_trading.json` |
| Constants | `scripts/hermes_constants.py` (READ ONLY) |
| Plans | `/root/.hermes/plans/` |
| T simulator | `python3 scripts/t_simulator.py search "..."` |

You are the chair. Be adversarial with your own conclusions. The panel's job is to
convert measurement into at most one carefully-evidenced action per week — or to have
the discipline to ship nothing.
