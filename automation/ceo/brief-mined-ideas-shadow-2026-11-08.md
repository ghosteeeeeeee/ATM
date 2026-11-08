# BRIEF: Transcript-mined ideas — OAK/KILL list + shadow-mode rollout (2026-11-08)

## Context

Four YouTube videos were mined today (2026-11-08). Reports + full transcripts are committed
(`707860ca`, `a98fa8ce`):

- `brain/transcript-mining/this-algo-strategy-has-only-3-rules-and-62-win-rate.md` (Connors 3-rule / 62% WR)
- `brain/transcript-mining/i-gave-jev-control-of-a-trading-bot.md`
- `brain/transcript-mining/i-turned-jev-ai-into-a-247-stock-trader.md`
- `brain/transcript-mining/how-to-actually-build-an-ai-trading-bot-with-claude.md` (3hr ALPHA course — the substantive one)

A session-CEO provisional verdict already ranked video 1 (exposure tracking + 2×ATR(20) stop
benchmark = do now; 7-day breakout signal = park). This brief asks YOU for the binding
build/kill rulings across all four, and — the urgent part — **which items enter shadow mode ASAP**
using the `automatic-implementation` pattern (ship OFF → collect counterfactual → flip ON only on a
pre-registered bar with CEO approval).

**Why this matters now:** the ALPHA-course report directly addresses the 2026-10-08 "THE PATTERN"
failure in AGENTS.md (4 failed analyses: survivorship bias, selection-on-outcome, time-anchor bugs,
unreproducible numbers). The locked-test and neighbor-test items are process-level fixes for that
exact wound — we currently tune constants (ATR_SL 1.0→1.2→, SPEED_MIN 30→40, k-mult 2.5→2.0) on the
same data we judge them on, with no out-of-sample and no ±step robustness check.

## Candidate list — the ask

### Group 1 — Read-only analysis/tooling (no live-path touch; propose just build, no shadow needed)

- **A. Locked test protocol** — pick an out-of-sample window, look ONCE, never tune after seeing it. Needs a written rule (brain/SOPs.md) + a split script.
- **B. Neighbor test** — ±step sweep harness in signal-lab/backtest skills; first run on 3 recently tuned constants (ATR_SL_MIN, SIGNAL_FILTER_SPEED_MIN, ATR_TP_K_MULT) → hill vs spike verdict.
- **C. Backtester self-test** — planted-edge synthetic data mode (engine must recover known ~1% edge minus costs) as a `--self-test` gate.
- **D. Exposure tracking** — % time-in-market per signal source/token + exposure-adjusted return metric.
- **E. Reconciliation script** — classify every live trade gap vs its `_signal_metadata` at detection into fills/timing/data/rounding/limits/rules (catches the CFX detection-vs-execution drift class).
- **F. 2×ATR(20) stop benchmark** — compare against current ATR_SL range on recent trade history.
- **G. Session/hour-of-day analysis** — PostgreSQL: WR/PnL by hour; is there a real session effect?
- **K. Decision-stream dashboard** — surface "why this fired" from `_signal_metadata` on signals.html. (viz only)
- **L. HL API key permission audit** — verify key is trading-only, no withdraw/deposit. (verification task, do today)

### Group 2 — Touches scoring/gates/trading path → SHADOW FIRST (this is the "ASAP" ask)

- **H. Trade-frequency deviation check** — baseline trades/hour per signal source; alert on ½×/2× deviation. **Shadow = compute + log only, no blocking.**
- **I. Kill lines** — per-signal-source max drawdown = 2× its worst *tested* drawdown, pre-committed in a registry. **Shadow = record distance-to-kill-line + alert, no auto-remove.**
- **J. Exposure budget** — dynamic score/confidence adjustment by current open-position load. **Shadow = log the counterfactual score with/without, don't apply.**

### Group 3 — Discipline/docs

- **M. Rule-change loop in brain/SOPs.md** — "no threshold changes from a recent losing stretch; every change goes idea → full gates → paper → swap-on," mirroring the automatic-implementation skill. (Directly fixes the ATR_SL 48h-widening pattern.)

## Question

1. **Ruling per item:** for each of A–M, OAK (build), KILL, or DEFER — with the one-line reason. Do not re-derive whether the ideas are good; the reports contain the analysis. Rule on scope.
2. **Shadow-mode batch (the ASAP part):** for Group 2 (H/I/J), confirm the shadow designs above, set the **pre-registered flip bars** (what counterfactual sample + metric threshold converts each to enforce), and state which shadow flags you authorize shipping **this week**. Per automatic-implementation: ship OFF, zero trading-path behavior change, flip only by explicit CEO approval on data.
3. **Build order:** name the FIRST THREE things built (with the reasoning), and what runs in parallel. Assume one implementation agent at a time.
4. **Constraints to respect:** `hermes_constants.py` values need T's approval — new shadow flags added as `False` are presumably OK but state your ruling explicitly; systemd timers not cron; mandatory subagent code review + bug_hunter as last step on each item; commit per unit.

State the ruling as a table (item / decision / flip-bar if shadow / order), plus any items you KILL and why.
