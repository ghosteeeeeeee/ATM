# SPEC: Probability Matrix — calibrated P(win) + EV admission layer

**Status**: 🔴 **CLOSED EXPERIMENT — archived 2026-11-20 per pre-registered stopping rule (no revisit scheduled).** Outcome record: P0 signal-cells run = **STOP 1/4** (`brain/analysis/probability-matrix-calibration.md`); single bounded B3 iteration (family cells, bars unchanged, CEO decision `checkpoints/20261120T141947Z-decision.md`) = **STOP 2/4** — (a) FAIL Δ+26.5pp p=0.254 G=5, (b) PASS (p 0.2456 vs conf 0.3939, CI excl. 0 — *proves confidence-as-probability is worse than a coin, not that p is good*), (c) FAIL (0.2517 vs 0.2500, p=0.598 — p still ≈ coin OOS), (d) PASS 36.6% (`...-calibration-family.md`, bug_hunter SHIP `checkpoints/20261120T141947Z-result-2.md`). Stopping rule: 4/4 required, no further data-design iterations (B1/B2 barred), no bar amendments ever. Tool `scripts/probability_matrix.py` remains available for read-only re-runs; P1/P2 never shipped; hermes_constants untouched. A future revival requires a NEW spec with NEW pre-registered bars and an explicit CEO ruling — not a re-run of this one.  
**Date**: 2026-11-19 (v1.0 4fe2153a → v1.1)  
**Inputs**: `brain/summaries/beat-the-market-thorp-kassouf.md`, `brain/context/probability-matrix-context.md` (`1d59afbc`)  
**Pattern**: automatic-implementation (shadow → enforce, pre-registered bars)

**Changelog v1.1** (from verdict): (1) p_win source contradiction resolved §3.1; (2) coverage metric defined vs train-admitted cells with measured numbers §3.1/§4/§9; (3) §1.2 mechanism + numbers corrected (PnL inversion reproduced, WR inversion not, n=155 = pump-chain subset); (4) confidence field pinned for Brier §4; (5) §3.2 fixed (trade-level Brier, p clipping, 0-win handling, ev≡avg_pnl_raw note, ε stated); (6) §4 bar hardened (baseline limb, conf mapping, same metric, cluster-robust); (7) P1 limbs rewritten (executed-n, observable blocked cohort, CI, all-trades denominator); (8) signal-churn risk added §9; (9) reuse list extended §2.

## 0. One-liner

Turn our existing per-cell win-rate statistics into a **calibrated P(win) and a forward-looking expected value per signal**, run as a read-only study first, then a shadow counterfactual, then — only on a pre-registered bar with CEO approval — an EV admission gate beside (never inside) the live path.

## 1. Problem (evidence, not vibes)

1. **No predictive EV anywhere.** Repo grep (auditor-confirmed): no `P(win) × payoff` product in trading code; expectancy-as-raw-mean-PnL exists (`cell_stats.avg_pnl`, analysis scripts) but nothing uses a *predictive* probability with payoff sizes. No Brier/log-loss code exists either.
2. **Confidence does not behave like a probability** (corrected per verdict):
   - `final_confidence` is the raw invented confidence from each signal file (base + bonuses); `signal_compactor.py:2270-2294` separately produces `score`/`penalty_product` (live hotset confirms conf 85.36 = final_confidence 85.36, penalty_product 0.066). The earlier "product of ~25 multipliers" description applied to `score`, not `final_confidence` — fixed here.
   - **PnL inversion reproduced by auditor** (30d, from `trades`): conf 90+ → n=277 **−$3.00** vs 70–89 → n=68 **−$0.68**.
   - **WR inversion NOT reproduced** at 30d (90+ 56.7% vs 70–89 47.1%, and the quoted 49.7%/n=155 figure is a **pump-chain-only subset**, p=0.21 n.s.). Claim restated as: high confidence predicts *worse PnL*, not proven worse WR.
3. **Calibration never studied.** Bucket→WR reliability proposed (`brain/transcript-mining/i-gave-jev-control-of-a-trading-bot.md:66`), never run.
4. **Book principle we ignore**: price = Σ payoff × probability after hard bounds and a fitted conditional expectation (Thorp/Kassouf Ch8). We have the fitted expectation (`cell_stats.py`); we never take the EV step.

## 2. Design principles

- **Reuse first (extended per verdict §9):**
  - `cell_stats.py` — nightly store per `(signal, direction, volatility_regime)`: WR tiers (**note: at n≥15 the store keeps `wr_raw`, shrinkage only applies below — the matrix layer must apply its own prior/clipping for probability use**), `avg_pnl`, **MFE/MAE quantiles**, `tradeable`; live consumer `signal_compactor.py:2211-2268`. **This IS the normal price curve — the matrix reads it, never writes a second WR store.**
  - `correlation_engine._bayesian_confidence` (`:160-164`, prior 0.50, K=10) — adopt the same prior convention.
  - **`trades.mfe_pct` (99.4% coverage)** — preferred over `_signal_metadata` for payoff quantiles; `_signal_metadata` (67 keys; `final_confidence` only in 41.5% of 90d trades) for state-vector logging only.
  - **`cluster_t.py`** — cluster-robust significance for every bar limb (trades cluster by signal/token; plain Fisher/Welch p-values are optimistic).
  - **`exit_optimizer_shadow`** — existing shadow precedent to mirror, alongside freq/kill-line wiring.
  - `streak_analysis.py` — script conventions (data-anchored window, SELECT-only, reproduce one-liner).
- **Anti-patterns forbidden** (survey + verdict): no new 0–100 weighted composite; no third "N sources agree" score; no RF training; **no hardcoded probability tables — every number data-derived or it doesn't ship**; no re-derivation of stored columns presented as new (see §3.2 honesty note).
- **Bounds before probabilities** (book): existing hard gates (blacklists, RSI floors, `CONFLUENCE_REQUIRED`, hard blocks) remain the P=0/P=1 layer.
- **THE PATTERN** on every claim: n everywhere, cluster-robust p-values, OOS handling for signal churn (§4), reproduce command, independent verification before any enforce. Locked-test protocol from `brain/SOPs.md` applies to any final threshold.

## 3. Architecture

```
trades (+ mfe_pct) ──► cell_stats (existing)                    [P(win) source, live store]
        │
        ├────────────► EV layer (NEW, read-only):               [predictive payoff layer]
        │                ev(c) = p(c)·E[win|c] + (1−p(c))·E[loss|c]
        │                (predictive: p from prior/shrunk, not raw frequency — see §3.2)
        │
        ├────────────► calibration study (NEW):                 [trust layer]
        │                trade-level Brier + reliability under churn-aware folds (§4)
        │
        └────────────► consumers, phased (§6): P0 study → P1 shadow → P2 gate (CEO-gated)
```

### 3.1 Cell schema, p_win source, coverage (contradiction resolved)

- **Cell**: `c = (signal_source, direction, volatility_regime)` — identical axes to cell_stats. No new axes in phase 1; each future axis = own change with neighbor-test + locked-test.
- **p_win source — two distinct uses, stated explicitly (no contradiction):**
  1. **Production/counterfactual use (P1 shadow, P2)**: read the **live cell_stats store** as-is (nightly refreshed — this is what production would consume). For probability hygiene the matrix applies: `p = clip((n·wr_raw + K·0.50)/(n+K), ε_p, 1−ε_p)` with K=10 (matching `correlation_engine`), **regardless of the store's tier behavior** (store keeps raw at n≥15; matrix always blends for probability use). `ε_p = 0.01`.
  2. **Calibration-study use (P0)**: a **frozen train snapshot** of cell statistics, so the OOS claim has a frozen predictor (§4).
- **Coverage metric (defined per verdict)**: `coverage = (test trades whose cell was admitted in train with n≥15) / (all test trades)`. **Measured by auditor on 60d/30d: 45.7% train, 7.1% clean-OOS, 58.8% in-window, 70.5% live-store (in-sample)**. P0 must report coverage per fold against train-admitted cells; **expected OOS coverage is LOW (~7–50%) because of signal churn — this is a measured fact, not an assumption** (§9).
- **Cell admission for gating**: `n ≥ 15`. **0-win or 0-loss cells are NOT `UNCALIBRATED`** (verdict §3.2 fix): with blending always applied, a 0-win cell gets `p > 0` from the prior, `ev` is computable, and **the gate applies to it** (an all-loss cell must be *blocked*, not exempted — no fail-open). `UNCALIBRATED` is reserved for `n < 15` only; those are excluded from gating and reported as a coverage gap.

### 3.2 Formulas (final; honesty note + edge cases pinned)

```
p(c)           = clip((n_c·wr_raw_c + K·0.50)/(n_c + K), 0.01, 0.99)      # K=10, always blended
ev_usdt(c)     = p(c)·mean(pnl | win, c) + (1−p(c))·mean(pnl | loss, c)
ev_per_risk(c) = ev_usdt(c) / |mean(pnl | loss, c)|   ONLY when |mean(pnl|loss,c)| ≥ ε_amt (ε_amt = 0.05 USDT);
                 otherwise report ev_usdt only, ev_per_risk = null (never divide into noise)
brier          = (1/|T|) · Σ_{t∈T} ( p(cell(t)) − y_t )²     # TRADE-level, single definition,
                 y_t = 1 if pnl_usdt>0 else 0; p clipped as above before scoring
```

**Honesty note (verdict §3.2)**: when `p` equals the raw win frequency, `ev_usdt` is algebraically `cell_stats.avg_pnl` — a stored column. The matrix's value is **not** a new mean; it is (a) using a *blended/predictive* p rather than raw frequency, (b) evaluating whether that p is **calibrated OOS** (§4), and (c) the decision layer built on it. P0/P1 reports must state this; never present `ev_usdt ≈ avg_pnl` as a discovery.

## 4. Calibration study (P0 gate — must pass before ANY shadow)

**Question**: does `p(c)` predict outcomes better than `final_confidence`, and is it calibrated — **under signal churn**?

Design (`scripts/probability_matrix.py calibrate`, SELECT-only, conventions of `streak_analysis.py`):
1. **Churn-aware evaluation, not a single 60/30 split** (verdict §2): **rolling-origin folds** — e.g., 3+ folds of `train 30d → test 7d` stepping forward; every fold's cells admitted from that fold's train only; coverage reported per fold against train-admitted cells (expected low — report it, don't hide it). Additionally the **live-store reliability curve** as a clearly-labeled **in-sample descriptive** view (70.5% coverage, leakage flagged in the output header).
2. **Metrics (single definitions, same for both predictors):** trade-level **Brier** and **log-loss** (p clipped `ε_p=0.01`) for `p(c)` vs `final_confidence` mapped to [0,1] (`/100`) vs baseline `0.5`. **Confidence comparison runs on the intersection subset** where `final_confidence` exists (41.5% of 90d trades) — coverage printed in the report header; if intersection < 30% of test trades, the confidence comparison is reported as LOW-COVERAGE, not silently dropped.
3. **Significance: cluster-robust** via `brain/analysis/cluster_t.py` convention (cluster = signal source) for the Brier difference; plain p-values flagged as optimistic.
4. Reproduce one-liner printed; output committed to `brain/analysis/probability-matrix-calibration.md`.

**Pass bar (pre-registered, all four or the spec stops with an honest report):**
- **(a) Discrimination:** top-2 p-decile observed WR > bottom-2, cluster-robust p<0.05, sign preserved on the final test fold.
- **(b) Beats confidence:** `Brier(p) < Brier(conf)` on the intersection subset, cluster-robust paired CI excludes 0 (if LOW-COVERAGE: limb INCONCLUSIVE → spec stops, confidence replacement not justified).
- **(c) Beats baseline:** `Brier(p) < Brier(0.5)`, CI excludes 0.
- **(d) Coverage disclosure:** per-fold coverage table published; if worst-fold coverage < 10%, P0 reports **LOW-COVERAGE** and P1 waits for more data rather than loosening `n_min` (loosening n = the overfit trap).

## 5. Payoff/band layer (P0 report only — no decisions)

Per cell, descriptive payoff distribution from **`trades.mfe_pct` (99.4% coverage)** + win/loss conditional means: the realized band (win/loss means, MFE/MAE quantiles) our SL/TP/trail actually produced. **Descriptive only** — feeds the P2 sizing discussion; sizing changes are T-gated and need their own spec.

## 6. Phased rollout (automatic-implementation)

### P0 — Study (first build)
- `scripts/probability_matrix.py` (`calibrate`, `report`; SELECT-only; `--help`; SQL+params printed; cursors in `finally`)
- Output: `brain/analysis/probability-matrix-calibration.md`
- **Zero trading-path files.**

### P1 — Shadow (ships only if P0 passes all four limbs)
- `scripts/ev_shadow.py` + `config/hermes-ev-shadow.{timer,service}` (hourly; mirror freq/kill-line + `exit_optimizer_shadow` precedent)
- **Counterfactual scope (explicit, per verdict §7):** the **executed-trade cohort only** — the gate is OFF, so everything executes and **both cohorts' outcomes are observable**: `blocked-cohort` = executed trades whose cell would fail the EV gate (`ev_usdt < 0` or `UNCALIBRATED`); `admitted-cohort` = the rest. Signals already blocked by other gates are **out of scope and stated as a limitation** (their EV-gate effect is unobservable without re-simulation).
- Log per executed trade: `p`, `ev_usdt`, cohort, cell `n`, plus what happened. Log-only; zero enforcement.
- Registration: `data/shadow_disposition.json` entry (`kind=shadow`, deadline **+14d**, `default_action=KEEP SHADOW`, no `auto_flip_flag`) + checkpoint_registry pending entry — proven kill-line wiring.
- **Pre-registered enforce bar (written now, before data; all four + CEO):**
  1. **n ≥ 100 executed trades evaluated** (executed, not signal-rows)
  2. **Blocked-cohort value:** net PnL of the blocked cohort **≤ −$0.50** with **cluster-robust 95% CI excluding 0** (i.e., the gate would have removed real losses — significance required, point estimate alone insufficient)
  3. **No starvation:** blocked share of **all executed trades ≤ 20%** (all-trades denominator)
  4. **Calibration still holds** on the shadow window (limb (a) sign preserved) **+ explicit CEO approval — never unattended; no code path can flip itself.**
- Re-test gate if P2 rejected later: same limbs on a fresh window + locked test.

### P2 — Enforce candidate (separate spec + CEO ruling on the bar above)
- Ceiling: **admission gate only** — block `ev_usdt < 0`; `UNCALIBRATED` (n<15) handled per P1 cohort definition; new `False`-default flag in `hermes_constants.py`, staged per automatic-implementation; flip = one line with ruling recorded.
- **Not in P2**: replacing `final_confidence`, any sizing change, any cell-axis expansion — follow-on specs with their own bars.

## 7. Validation protocol (every phase)

1. Code review subagent + **bug_hunter last** on each build.
2. Independent cold verification of numbers feeding any ruling (own-conclusions — consumed this spec at v1.0; re-audit of v1.1 changes optional before P0 build).
3. Neighbor test for any introduced threshold (ε, bucket count, EV cutoff) — hill not spike (SOPs rule-change loop).
4. Locked test: final thresholds tuned on train, **looked at once** on held-out data.
5. Restart pipeline after any committed signal-path change (P0/P1 have none; P2 does).

## 8. Files

**Create**: `scripts/probability_matrix.py`, `brain/analysis/probability-matrix-calibration.md`, (P1) `scripts/ev_shadow.py`, `config/hermes-ev-shadow.{timer,service}`, registry/disposition entries.  
**Read-only**: `cell_stats.db`, `trades`, `signal_compactor.py`, `correlation_engine.py`, `cluster_t.py`.  
**NOT touched in P0/P1**: `hermes_constants.py` (P1 may add `PROB_MATRIX_*` new-name defaults only if needed), `decider_run.py`, `signals/*`, `position_manager.py`, `tpsl_utils.py`, any `*_ENABLED`, H/kill-line timers, stop-tighten.  
**Landmine quarantine (separate queue — matrix must not build upon them)**: dead `signals.effective_confidence` (0/12,401 rows, 3 read sites, zero writers — auditor-confirmed); dead `SIGNAL_QUALITY_*` (constants-only refs); `SCORE_WEIGHTS` imported-unused (`continuum_engine.py:40`); dual confidence-field semantics drift (`decider_run.py:4796-4807`).

## 9. Risks & honest unknowns

- **Signal churn (measured, verdict §2)**: clean 60d→30d split covers only **7.1%** of test trades (root cause: labels like `jup_yolo_mirrored` going 0→168 trades); train coverage 45.7%. Mitigation: rolling-origin folds (§4), coverage disclosure every report, `n_min` never loosened to chase coverage, and **new signals are born `UNCALIBRATED` by design** — the system's coverage grows as labels mature. If churn stays this severe, P1's n≥100 executed-trades limb simply takes longer — that is the correct behavior, not a reason to relax.
- **p may not beat confidence**: if limb (b) is inconclusive/LOW-COVERAGE, spec stops honestly (book: results don't support it → you don't trade it).
- **Regime drift**: cell_stats nightly refresh adapts cells; calibration decays — P1 limb 4 re-checks reliability at deadline.
- **Observational bias**: cells condition on admitted trades; gate changes admission → P1's on-executed counterfactual is the honest test (scope stated §6); blocked-by-other-gates signals remain unmeasured (stated limitation).
- **Thin cells / `UNCALIBRATED` share**: reported per fold; a large UNCALIBRATED share means P2 has little surface to act on — reported, never papered over.

## 10. Rollback

- P0: `git revert` analysis scripts — no state, no path.
- P1: `systemctl disable --now hermes-ev-shadow.timer` + revert — log-only, no trading state ever written.
- P2: flag `True→False` + pipeline restart (one line, recorded in ruling).
