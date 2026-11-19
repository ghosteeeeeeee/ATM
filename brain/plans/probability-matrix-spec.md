# SPEC: Probability Matrix — calibrated P(win) + EV admission layer

**Status**: DRAFT for independent verification (own-conclusions) → CEO ruling → shadow  
**Date**: 2026-11-19  
**Inputs**: `brain/summaries/beat-the-market-thorp-kassouf.md` (book distillation), `brain/context/probability-matrix-context.md` (prior-art survey, `1d59afbc`)  
**Pattern**: automatic-implementation (shadow → enforce, pre-registered bars)

## 0. One-liner

Turn our existing per-cell win-rate statistics into a **calibrated P(win) and an expected value per signal**, run them as a read-only study first, then a shadow counterfactual, then — only on a pre-registered bar with CEO approval — an EV admission gate beside (never inside) the live path.

## 1. Problem (evidence, not vibes)

1. **No EV anywhere.** Repo grep: zero `expected_value`/EV trading code. Decisions are made on heuristic scores, never on `P(win) × payoff`.
2. **Confidence is not a probability and inverts.** `final_confidence` = product of ~25 hardcoded multipliers (`signal_compactor.py:2270-2294`). Documented: conf 90+ → **49.7% WR, n=155** (`brain/verdicts/...2026-10-08-pump-chain-v6-verdict.md:20`); 90+ net **−$5.88** vs 70–89 **+$5.24** (`brain/verdicts/...2026-10-14-plan-v3-own-conclusions.md:58`). Higher "confidence" currently predicts *worse* outcomes.
3. **Calibration never studied.** The bucket→WR reliability study was proposed (`brain/transcript-mining/i-gave-jev-control-of-a-trading-bot.md:66`) and never run.
4. **Book principle we ignore**: price = Σ payoff × probability (Thorp/Kassouf Ch8), after hard bounds and a fitted conditional expectation (normal price curves). We have the fitted expectation (`cell_stats.py`) but never take the EV step.

## 2. Design principles

- **Reuse first (survey's reuse list, non-negotiable):**
  - `cell_stats.py` — nightly empirical-Bayes shrunk WR per `(signal, direction, volatility_regime)`, `blend = (n·cell + K·prior)/(n+K)`, K=10, admission n≥15, **already live** in `_score_signal` (`signal_compactor.py:2211-2268`). **This IS the normal price curve. The matrix does not create a second WR store — it reads this one.**
  - `correlation_engine._bayesian_confidence` (`correlation_engine.py:160-164`) — working 0–1 helper; reuse its prior convention (0.50, K=10) for consistency.
  - `_signal_metadata` — 67-key detection-time feature vector (live query confirmed) — the state vector every cell evaluation can log.
- **Anti-patterns explicitly forbidden** (survey): no new 0–100 weighted composite (coin_tracker's 20-weight table is the cautionary tale); no third "N sources agree" score; no RF/`ml_classifier` training (exists, inert, out of scope); no hardcoded probability tables — **every number data-derived or it doesn't ship**.
- **Bounds before probabilities** (book): existing hard gates (blacklists, RSI floors, `CONFLUENCE_REQUIRED`, hard blocks) remain the P=0/P=1 layer. The matrix only assigns probabilities *inside* the feasible band.
- **THE PATTERN discipline** on every claim: n everywhere, p-values, OOS split, reproduce command, independent verification before any enforce. Locked-test protocol from `brain/SOPs.md` applies to the final gate threshold.

## 3. Architecture

```
trades + _signal_metadata ──► cell_stats (existing, shrunk WR)         [P(win) layer]
        │
        ├──────────────────► EV layer (NEW, read-only):                [payoff layer]
        │                     EV(c) = P(c)·E[win|c] + (1−P(c))·E[loss|c]
        │
        ├──────────────────► calibration study (NEW):                  [trust layer]
        │                     bucket P → observed WR, Brier, reliability curve
        │
        └──────────────────► consumers, in phases (§6):
                              P0 study report → P1 shadow log → P2 gate (CEO-gated)
```

### 3.1 Cell schema (phase 1 — exactly the existing axes)

`c = (signal_source, direction, volatility_regime)` — **identical to cell_stats** so its shrunk WR plugs in with zero new fitting. Per cell the EV layer additionally computes from closed trades:

- `n`, `p_win` (from cell_stats, never refit here)
- `avg_win_usdt`, `avg_loss_usdt` (conditional means, net as recorded in `pnl_usdt`)
- `ev_usdt = p_win·avg_win + (1−p_win)·avg_loss`
- `ev_per_risk = ev_usdt / |avg_loss|` (dimensionless; guards cells where absolute size differs)
- calibration fields: bucket decile, observed WR (for §4)

**Cell admission**: `n ≥ 15` (cell_stats' rule) AND `avg_loss` defined (≥1 win and ≥1 loss observed). Otherwise status `UNCALIBRATED` — reported, never used. Cells are never silently dropped; the report lists them.

**Cell expansion (speed band, z band, regime, …)** is FORBIDDEN in phase 1. Each new axis is a separate change with neighbor-test (±band edges) + locked-test before adoption — every added dimension shrinks n and invites overfit (book: per-warrant curves were already noisy; more axes = thinner curves).

### 3.2 Formulas (final, no tunables in code paths)

```
p_win(c)      = cell_stats shrunk WR(c)                    # existing, K=10
ev_usdt(c)    = p_win(c)·mean(pnl | win, c) + (1−p_win(c))·mean(pnl | loss, c)
ev_per_risk(c)= ev_usdt(c) / max(|mean(pnl | loss, c)|, ε)
brier         = mean_over_buckets( (p_win − observed_WR)² )
```

Constants that are genuinely config (`K`, `n_min`, bucket count, ε) go in `hermes_constants.py` **as new names with defaults matching current behavior** (new-flag pattern; existing values untouched — T gate untouched).

## 4. Calibration study (the gate — P0, read-only, must pass before ANY shadow)

**Question**: does `p_win` predict outcomes better than `final_confidence`, and is it calibrated?

Design (run as `scripts/probability_matrix.py calibrate`, SELECT-only):
1. Window: 90d closed trades (same data-anchored approach as `streak_analysis.py`; train 60d / test 30d OOS split).
2. Bucket all trades by `p_win` decile → observed WR per bucket → reliability table (n per bucket printed; buckets with n<30 flagged thin).
3. Metrics: **Brier score** and **log-loss** for `p_win` vs `final_confidence` (as a predictor, monotonic-transform-free) vs baseline 0.5. Hypothesis to confirm/refute: confidence inverts → worse Brier than p_win.
4. Significance: paired bootstrap CI on Brier difference (seeded); if CI crosses 0 → report INCONCLUSIVE, no downstream phases.
5. Reproduce: printed one-liner; output committed to `brain/analysis/probability-matrix-calibration.md`.

**Pass bar (pre-registered)**: (a) reliability monotonicity — top-2 p_win deciles' observed WR > bottom-2, p<0.05; (b) Brier(p_win) < Brier(confidence) with bootstrap CI excluding 0; (c) test-window (30d) sign of (a) preserved. **All three, or the spec dies here with an honest report.**

## 5. Payoff/band layer (phase 1 report only — no decisions)

Book's band payoff maps to our SL/TP/trail: for each cell, report the **realized payoff distribution** (win/loss means, MFE/MAE quantiles from `_signal_metadata` where present) and the implied band. This is *descriptive only* in P0/P1 — it feeds the P2 sizing discussion but makes no decisions. Explicitly out of scope for P2-admission (sizing changes are T-gated and need their own spec).

## 6. Phased rollout (automatic-implementation)

### P0 — Study (this spec's first build)
- `scripts/probability_matrix.py` (`calibrate`, `report` modes; SELECT-only; `--help`; SQL+params printed; cursors in `finally`)
- Output: `brain/analysis/probability-matrix-calibration.md`
- **Zero trading-path files.** Bug: none possible beyond analysis.

### P1 — Shadow (ships only if P0 passes)
- `scripts/ev_shadow.py` + `config/hermes-ev-shadow.{timer,service}` (hourly, modeled on freq/kill-line pairs)
- For every signal evaluated: log counterfactual `p_win`, `ev_usdt`, and **EV-gate decision** (admit/block) + what actually happened — log-only, zero enforcement.
- Registration: `data/shadow_disposition.json` entry (`kind=shadow`, deadline **+14d**, `default_action=KEEP SHADOW`, no `auto_flip_flag`) + checkpoint_registry pending entry — mirror of the proven kill-line wiring (D5).
- **Pre-registered enforce bar (written now, before data):**
  1. n ≥ 100 EV-evaluated decisions
  2. EV-gated subset (trades the gate would have admitted/blocked differently) has **net PnL ≥ actual by ≥ $0.50** over the window with **no >20% trade-count reduction** (mirrors J's bar)
  3. P0 calibration bar still holds on the shadow window (reliability sign preserved)
  4. **Explicit CEO approval — never unattended; no code path can flip itself.**
- Re-test gate if P2 is later rejected: same as above plus locked-test on a fresh window.

### P2 — Enforce candidate (separate spec + CEO ruling on the bar above)
- Scope ceiling: **admission gate only** — e.g., block signals with `ev_usdt < 0` and `UNCALIBRATED` excluded — implemented as a *new* `False`-default flag in `hermes_constants.py`, staged per automatic-implementation (shadow flag ships OFF, flip is a one-line `False→True` with the ruling recorded).
- **Not in P2**: replacing `final_confidence`, any sizing change, any cell-axis expansion. Those are follow-on specs with their own bars.

## 7. Validation protocol (applies to every phase)

1. Code review subagent + **bug_hunter last** on each build (AGENTS mandate).
2. Independent cold verification of any numbers feeding a ruling (own-conclusions — this spec's first consumer).
3. Neighbor test for any threshold introduced (bucket count, ε, EV cutoff) — hill not spike (SOPs rule-change loop).
4. Locked test: final gate threshold tuned on train, **looked at once** on held-out window.
5. Restart pipeline after any committed signal-path change (AGENTS staleness rule) — P0/P1 have no path changes; P2 does.

## 8. Files

**Create**: `scripts/probability_matrix.py`, `brain/analysis/probability-matrix-calibration.md`, (P1) `scripts/ev_shadow.py`, `config/hermes-ev-shadow.{timer,service}`, registry/disposition entries.  
**Read-only**: `cell_stats` DB, `trades`, `signal_compactor.py`, `correlation_engine.py`.  
**NOT touched in P0/P1**: `hermes_constants.py` (except possibly new `PROB_MATRIX_*` constants if P1 needs config — default-valued, new names only), `decider_run.py`, `signals/*`, `position_manager.py`, `tpsl_utils.py`, any `*_ENABLED`, H/kill-line timers, stop-tighten.  
**Landmine cleanup (separate queue, not this spec)**: dead `signals.effective_confidence` column (0/12,400 rows), dead `SIGNAL_QUALITY_*` gates (0 refs), `SCORE_WEIGHTS` unused import in `continuum_engine.py:40`, dual confidence-field semantics drift (`decider_run.py:4796-4807`). These must not be *built upon* by the matrix; fixing them is tracked separately.

## 9. Risks & honest unknowns

- **Cells may be too thin.** 60d train / `(signal×direction×vol)` → many `UNCALIBRATED`. Mitigation: report shows coverage %; if coverage < 50% of trades, P0 reports LOW-COVERAGE and P1 waits for more data rather than loosening n (loosening n = the overfit trap).
- **P(win) may not beat confidence.** Confidence's inversion might be regime-confounded; if Brier comparison is inconclusive, spec stops. (Book: "if the results don't support it, you don't trade it.")
- **Regime drift**: cell_stats' nightly refresh already adapts; calibration decays — P1 shadow re-runs the reliability check at its deadline (bar limb 3).
- **Observational bias** (streak-analysis caveat applies): cells condition on *admitted* trades; the EV gate changes the admitted set → P1's counterfactual is the only honest test, hence shadow-before-enforce.

## 10. Rollback

- P0: `git revert` of analysis scripts — no state, no path.
- P1: `systemctl disable --now hermes-ev-shadow.timer` + revert — log-only, no trading state ever written.
- P2: flag `True→False` + pipeline restart (one-line, recorded in ruling).
