# SPEC: Direction Matrix — BTC P(up/side/down) per horizon, rolling, self-calibrating

**Status**: v1.0 — OPERATOR-ORDERED (T, 2026-11-22: "prices can only go up, down or sideways… BTC only for now"). New line, NOT a revival: different target (candle returns vs trade P&L), different data (candles vs signal-source cells), different consumer (informational query). The closed `probability-matrix-spec.md` stopping rule requires NEW spec + NEW bars for any *trade-gate* revival — this is that new spec for a different problem; nothing closed reopens.
**Date**: 2026-11-22

## 0. One-liner

Every hour, train rolling-window classifiers that answer **"chance BTC goes up in the next 15m/1h/4h"** as calibrated probabilities (up/side/down), log every call, resolve each call against what actually happened, and publish Brier/reliability so we can always check whether the probability call was correct.

## 1. Requirements (from operator, verbatim intent)

1. Three-way outcome: **up / down / sideways** (per horizon).
2. Multiple factors, like the **full-analysis skill**: MTF MACD, RSI, z-score, BB position, EMA structure, volume ratio, momentum, chop-regime flag (its §chop adjustment), cross-TF agreement.
3. **Probabilities per timeframe** = one probability vector per prediction horizon.
4. **Rolling window** — retrains slide with data.
5. **Self-tuning**: every call is logged; once the horizon elapses, the actual outcome is joined back → historical accuracy is measurable and is the tuning signal.
6. **Queryable at any point**: "chance of going up 90%" style output.

## 2. Design

### 2.1 Target
- Asset: **BTC only** (v1). Horizons **H ∈ {15m, 1h, 4h}** (candle tiers; 1m/5m excluded from horizons — 1m depth ~30d is too thin for honest OOS and 5m adds little beyond 15m).
- Label at candle close t: `r = close(t+H)/close(t) − 1` → **up** if `r ≥ ε_H`, **down** if `r ≤ −ε_H`, else **side**.
- Deadbands (CLI defaults, documented, fixed — labels must be stable across retrains for calibration comparability): **pinned table ε = 5bps·√(H_minutes/15) → 15m: 5bps, 1h: 10bps, 4h: 20bps** (v1.0 errata: the original `√(H/60)` formula yielded 2.5/5/10 and contradicted the table — the pinned table governs; builder implemented the corrected formula per deviation note 1). Every report prints the ε in use. (If ever used for a trading decision, ε becomes neighbor-test territory — not now.)
- Lookahead rule: features from closed bars ≤ t only; label uses t+H (evaluation-only). Never a feature.

### 2.2 Features (full-analysis factor set, computed from LOCAL `data/candles.db` only — skill's data-source rule, no API)
Per TF in {5m, 15m, 1h, 4h} (1m features only as context for 15m horizon if depth allows; else omit and say so):
- MACD state: EMA8−EMA50 vs signal, histogram slope sign
- RSI(14), z-score(20), BB position(20,2), volume ratio (20-bar avg)
- EMA50 and EMA200 distance (%), EMA300-side (above/below)
- momentum: 1h/4h/24h returns (scaled by rolling vol → z-ized)
- structure-lite: linreg slope sign over 20 bars + higher-TF agreement votes (bull/bear/neutral counts across TFs)
- chop flag: hourly EMA300 flips in last 24h ≥2 (skill's mandatory chop adjustment — as a FEATURE, not a post-hoc score hack)
- plus time-of-day sin/cos (hour of day, UTC) — free, cheap
Target feature count ≈ 40–70. Any factor lifted from the skill is ported as a NUMBER, never as the skill's ±point heuristic (the 0–100 score table is a human device — we fit probabilities instead).

### 2.3 Model
- **sklearn `LogisticRegression`** (multinomial, L2, `C=1.0` default, `max_iter` sufficient) + `StandardScaler`, fit per horizon on the rolling window. sklearn 1.8.0 present (verified).
- **Rolling window: 30d** of closed candles per horizon (15m ≈ 2,880 samples, 1h ≈ 720, 4h ≈ 180 — **4h is low-n: report it loudly, flag UNSTABLE-LOW-N if n < 300**, never pretend).
- Retrain cadence: **hourly** (systemd timer), slide window by 1h.
- Fixed random_state, deterministic ordering, seeded everything — reruns byte-identical for identical data (the §15.6 data-pin rule: every report prints window bounds + row-count + sha of the candle slice).

### 2.4 The self-tuning loop (requirements 5 + 6)
- `predict` run appends one row per horizon to `data/dir_matrix_predictions.jsonl`:
  `{ts, horizon, p_up, p_side, p_down, trained_through, n_train, window, eps}`.
- When `ts + H < now`, the same run (or `resolve` mode) joins the realized class → row gains `actual`, `hit`.
- `score` mode computes, **per horizon**: rolling **Brier** + log-loss of the calls, reliability table (predicted-p decile → empirical frequency, n per bucket), and hit-rate of "≥70% calls" (the operator's "90% example" check: does a 90% call win ~90%?).
- `query` mode (the operator-facing answer):
  ```
  BTC 15m: P(up)=62% P(side)=25% P(down)=13%   [trained through <ts>, 30d n=720]
           reliability: last-30d Brier 0.58 · ≥70% calls: 71% hit (n=41)
  ```
  `--horizon all` / `--json` for machine consumers.

### 2.5 Validation gate (pre-registered, before ANY consumer trusts it)
Walk-forward inside the rolling window (train W−k → test k, k = 20% of window), per horizon:
- **(a)** Brier(p) < Brier(base-rate-frequency predictor), cluster(=day)-robust CI excludes 0
- **(b)** calibration-in-the-large: mean(p) ≈ base rate within ±0.05; top-decile empirical frequency's CI contains its claimed mean p
- **(c)** n disclosed per horizon; 4h judged on its own sample, never pooled to rescue it
All three per horizon → that horizon is **VALIDATED**; else **UNVALIDATED** (output says so in the query line). Status lives in `data/dir_matrix_state.json`.
**Consumers v1: informational only.** Any trading-path consumer (context gate, sizing, arming) requires: validated status + shadow wiring (automatic-implementation) + CEO approval. This spec grants none of that.

### 2.6 Files
- `scripts/dir_matrix.py` — modes: `train` (fit+save), `predict` (train-slide + log calls), `resolve` (join outcomes), `score` (calibration report), `query` (the operator answer), `--selfcheck` (label math, ε, walk-forward no-lookahead, scaler fit-on-train-only, brier math). Header constants documented as CLI defaults (monitor-tool precedent: freq/kill-line shadows).
- `config/hermes-dir-matrix.{timer,service}` — hourly, oneshot, mirrors freq/kill-line unit style (systemd, never cron).
- Outputs: `data/dir_matrix_predictions.jsonl`, `data/dir_matrix_state.json`, report `brain/analysis/direction-matrix-validation.md` (the §2.5 gate run + data-pin header).
- **NEVER touched**: `hermes_constants.py`, trading path (decider/signals/position_manager/tpsl), the closed probability-matrix spec/reports, other timers, `market_phase_gate.py`.

### 2.7 Protocol (standing)
build → **code review** → **bug_hunter last**; per-unit commits, canonical push; data pinned (window+sha) in every report; SELECT/ro reads only on candles.db; THE PATTERN on every claim (n, p-values, OOS); no prescriptive/trading language in outputs until validated + shadowed + CEO-approved.

## 3. Explicit non-goals (v1)
Multi-asset (BTC only, per operator), trading-path consumption, dashboards (CLI + JSON first — `control_tower`/`ladder` could host later), feature selection tuning, hyperparameter search (C fixed; neighbor-test only if this ever becomes a gate), 1m/5m horizons.
