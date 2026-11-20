# BRIEF: Post-probability-matrix — ratify closure + residual ruling + sequence the open backlog (2026-11-20)

## Context A — your last ruling executed; ratify or correct

Run `20261120T141947Z` classed rc=124 during its own plan steps 4-5 (report assembly + memory).
The substance had already landed: decision checkpoint (B3, bars frozen, 4/4 stopping rule),
dispatch 1 built+ran family mode (`3219541f`), dispatch 2 bug_hunter **SHIP** (zero defects).
**Final gate: STOP 2/4** (a FAIL Δ+26.5pp p=0.254 G=5; b PASS 0.2456 vs conf 0.3939 p<0.001;
c FAIL 0.2517 vs 0.2500 p=0.598; d PASS 36.6%).

Parent then executed the pre-registered path C closeout:
- Spec header marked **CLOSED EXPERIMENT** with full outcome record (`brain/plans/probability-matrix-spec.md`, committed + pushed)
- `## CEO Deep Run — 20261120T141947Z` appended to `automation/ceo/ceo_report.md` under flock (ruling, numbers, bug_hunter SHIP, C-executed, durable findings)
- OpenMemory store (tags: closed-experiment, gate-stop, ceo-ruling)
- P1/P2 never shipped; `hermes_constants.py` untouched; tool retained read-only

**Ruling 1: RATIFY or CORRECT this closeout.** (State: ratified / amended + what changes.)

## Context B — the one residual finding that needs a scope ruling

Limb (b) PASS quantified: **`final_confidence` as a probability is far worse than a coin —
Brier 0.3939 vs 0.2500 baseline, p<0.001** (family cells, n=265 intersection). We already knew
confidence was PnL-inverted (30d: 90+ conf −$3.00 n=277 vs 70–89 −$0.68); this adds that it is
**miscalibrated as a probability**, not merely anti-predictive as a score.

Known constraints on acting on this:
- The closed spec's P2 explicitly excluded confidence replacement; the closed spec's stopping
  rule bars reopening THAT line of work without a new spec + new bars + explicit CEO ruling.
- Confidence today is a *multiplier* (`final_score = conf × ∏multipliers`), never consumed as
  P(win) — no live path treats it as a probability today (prior-art survey confirmed).
- Landmine quarantine list already tracks: dead `signals.effective_confidence` column
  (0/12,401, no writer), dead `SIGNAL_QUALITY_*` gates (0 refs), `SCORE_WEIGHTS` unused import
  (`continuum_engine.py:40`), dual confidence-field semantics drift (`decider_run.py:4796-4807`).

**Ruling 2: what (if anything) happens because of this finding?** Options as you see fit —
e.g.: (i) record-only (landmine list updated, no work), (ii) landmine-cleanup ticket only
(delete dead column/refs — no behavior change), (iii) authorize a NEW bounded study with NEW
pre-registered bars (state them), (iv) fold into a future signal-quality rework — or reject
the framing. Explicitly rule whether this re-opens anything closed, or not.

## Context C — open backlog inventory (complete, status verified 2026-11-20)

**Scheduled/pre-registered dates (already wired, automatic):**
| Item | Date | Bar/mechanism |
|---|---|---|
| stop-tighten keep/revert eval of LIVE clamp (cap 0.75, live since 11-04) | **11-21** | `data/shadow_disposition.json` deadline; limbs: id 86≥20 MET, net-delta ≥+$0.15/30d (pace +0.69/4d), WR-not-down (mid-eval fisher p=0.094); fail → revert cap 2.5 / ENFORCE=False |
| H freq-deviation shadow bar review (log-only shipped 11-08) | **11-22** | 14d ≥30 alert events + alert-conditioned next-24h source PnL <0 (n≥30) → CEO approval; 93 UNDER/0 OVER as of 11-08 read |
| kill-line shadow enforce review (log-only shipped 11-19) | **12-03** | disposition default KEEP SHADOW; current: r2v2-long3 CROSS 143.5%, 45 dynamic combo labels UNREGISTERED (n_train<10) |

**Authorized, never built (OAK'd 11-08 + 11-19 batches):**
- **D exposure tracking** (% time-in-market + exposure-adjusted return; read-only metric)
- **E detection-vs-execution reconciliation** (gap classes vs `_signal_metadata`; catches the CFX stale-condition class)
- **F 2×ATR(20) stop benchmark** (analysis only; ATR_SL_* changes remain T-gated — note D2's FAIL on the related 0.017 promotion)
- **G session/hour-of-day analysis** (one-shot SQL)
- **S2 event-completion exits analysis** (MFE-past-reversion study before any exit-logic change)
- **S3 null test per signal source** (FIRST check winrate-calculator skill for existing coverage — search-before-build)
- **combo-label kill lines** (the 45 UNREGISTERED dynamic labels — member-split or base-source grouping at next `--derive`)
- **K decision-stream dashboard** (deferred post shadow-batch; viz only)
- **CONF-view items**: B neighbor-test constant sweeps already landed for 3 constants; **landmine cleanup** (see B) pending whatever ruling 2 says.

**Standing constraints for whatever you order:** bug_hunter last on every build; code review
before bug_hunter; automatic-implementation shadow→enforce for anything touching scoring/gates;
systemd not cron; `hermes_constants.py` existing values = T gate, new default-off flags = your
prior authorization pattern; operator "biggest winners go live now" already consumed (evidence-
proven only — ATR_SL attempt died at verification); STOP/locked-test/neighbor rules in
`brain/SOPs.md` immutable by runs.

## Questions — state the ruling

1. **Ratify/close correction** on Context A (one line).
2. **Residual-finding scope ruling** (Context B): which option, exact work authorized, bars if study, and explicitly: does anything closed reopen? (default answer = no)
3. **Sequencing order** for Context C: what gets dispatched THIS run (name items), what queues behind the 11-21/11-22 dates, what stays deferred/killed. If you order builds: fresh subagents, one at a time or explicitly parallel, each with review→bug_hunter.
4. Any **culls** — kill anything in the backlog you no longer want (state KILL + line to remove).

Format: numbered rulings matching the questions, one-line rationale each. If you dispatch work
this run, the checkpoint must precede edits (standard).
