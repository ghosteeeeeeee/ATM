# SPEC: Direction Matrix v2 — regime-conditioned, structure-aware, calibrated

**Status**: v1.0 DRAFT for build (operator-ordered 2026-11-23: "this is v1, let it collect — brainstorm and spec v2, reuse live local data streams where possible").  
**Relation to v1**: v1 (`scripts/dir_matrix.py` + `hermes-dir-matrix.timer`) **continues untouched and collecting** — its resolved-call log becomes v2's external calibration/evaluation set. v2 is a NEW script + NEW state files; v1 code/units/jsonl are read-only inputs, never edited.

## 0. One-liner

Same operator question — BTC P(up/side/down) per horizon — but with the features that were missing (structure, ADX lifecycle, continuum, regime), a calibration layer trained on honest walk-forward data, and a gate that must beat **both** base rates **and v1 head-to-head** before anything trusts it.

## 1. Why v2 (measured v1 failures driving each change)

| v1 failure (48h live evidence) | v2 answer |
|---|---|
| Faded both trend legs (down-lean before +9.9% pump, up-lean before dump); per-horizon hit 43/19/18% vs modal baselines 53/38/45% | Persistence features (structure/AD lifecycle/linreg alignment) + **regime flag & per-regime reporting** |
| Model Brier > base at every horizon (0.633/0.740/1.062 vs 0.581/0.663/0.628 on 48h) | Richer features + calibration layer + head-to-head limb vs v1 |
| CITL miscalibrated (0.08–0.14 > 0.05) | **Platt calibration, walk-forward** on resolved calls (never trained on calls it is calibrating) |
| 4h n=180 (UNSTABLE-LOW-N) | 4h trains on **90d** (540 samples ≥ 300 floor); 15m/1h keep 30d |
| 4h ≥70% calls hit 31% (n=13) | calibration layer + gate limb (b) unchanged — overconfident calls must die at the gate |
| horizons contradict (15m down / 4h up) | cross-horizon state features (4h regime/state fed into 1h/15m models) |

## 2. Data & features (reuse-first, per operator)

### 2.1 Sources — all LOCAL, no API (full-analysis data-source rule)
1. **`data/candles.db`** (mode=ro, **anchor-bounded fetch** `ts+interval ≤ anchor` — v1's HIGH-1 fix, copied verbatim): every feature is computed from closed bars ≤ anchor, so training rows and live rows share one code path.
2. **Reused engines** (import/port definitions — NEVER redefine):
   - `structure_analysis.py`: `atr`, `zigzag`, `classify` primitives → per-TF structure state at bar t. **Confirm-lag discipline (full-analysis §15.2)**: swings count only if confirmed by bar t (no unconfirmed-extreme lookahead).
   - `adx_atr_analysis.py`: `_wilder_atr`, `_adx_peak`, `_atr_peak`, `_post_peak_extreme` → ADX value/slope, lifecycle flags (TRENDLESS / RUNNING / PEAKED / DUAL-PEAK / EXHAUSTION).
   - `continuum_engine.py` **definitions**: EMA300 side, z-score tier windows, linreg windows/alignment, trend_quality — read the definitions from source; **parity check**: recompute vs recorded `continuum_data.json` history over its 48h span; report max deviation (a feature family that can't reproduce the recorded stream is a finding, not a silent port).
   - Chop regime: t-anchored port of `auto_analysis.chop_flips_24h` (hourly EMA300-side flips in trailing 24h; ≥2 = CHOP) computed from `candles_1h` so it works at every training row.
   - v1's feature set (57) + epsilon/label/anchor/fetch machinery carried over unchanged.
3. **NOT used**: `data/speed_history.json` (stale, May-2026), `data/speeds.db` (0 bytes) — velocity/acceleration re-derived from candles instead; any API stream; order-book history (not stored locally).

### 2.2 Brand-new stream (from existing local tables — the one addition)
- **Market breadth**: % of the top-N local tokens (by candles_1h presence, N=20) above their 1h EMA300 and % with positive 1h slope, computed at anchor from `candles_1h`/`candles_4h`. Computed, not recorded — same t-anchored discipline. Rationale: BTC's legs ride the market tide (v1 had zero market-context features).

### 2.3 Feature budget
Target **≤ 110** features (v1's ~57 + structure/AD/continuum/breadth/cross-horizon). Every feature family listed in `--help` with its source engine. No hand-picked post-hoc features: the set is frozen at build time; additions are a spec amendment (THE PATTERN: feature shopping = overfitting).

## 3. Model & calibration

- **Estimator**: sklearn multinomial LogisticRegression, L2, `C=1.0` (frozen), `random_state` fixed, StandardScaler fit on train only — v1's exact pipeline, so head-to-head comparison isolates *features*, not algorithm changes.
- **Windows**: 15m/1h = 30d; **4h = 90d** (540 rows, clears n≥300).
- **Regime flag** is a feature (CHOP=1), plus 2–3 pre-declared interactions only (regime × structure_state, regime × momz) — no feature fishing.
- **Calibration layer (new)**: per horizon, a **Platt (logistic) calibrator** fitted on *resolved v2 calls older than the current prediction* (walk-forward; minimum 100 resolved calls before any calibration applies — below that, output raw + flag `UNCALIBRATED-CAL`). Never fit on the rows it scores.
- **Output**: raw p and calibrated p both logged; query shows calibrated as headline with raw in parens.

## 4. The gate (pre-registered — must pass before ANY consumer trusts v2)

Walk-forward (train 80% → test 20%, day-clustered CI), per horizon — **four limbs, all required**:
- **(a)** Brier(v2 raw) < Brier(base-rate predictor trained on train), CI excludes 0
- **(b)** CITL ≤ 0.05 (max |mean p − base| across classes); top-decile CI contains claimed mean
- **(c)** n disclosed per horizon; 4h judged alone; UNSTABLE-LOW-N if n < 300
- **(d) NEW — head-to-head**: Brier(v2) < Brier(**v1 model**) on the **identical test rows**, CI excludes 0. (v1 refit on the same window inside the gate — feature-provenance isolation; v1 code not modified, its `fit_pipeline` reused by import or by a pinned copy with identical hyperparameters.)
- **Disclosures (not limbs)**: per-regime Brier table (CHOP vs TREND); hit vs modal-class baseline; calibrated vs raw.
- Verdict = a∧b∧c∧d per horizon → VALIDATED else UNVALIDATED (never partial). Status in `data/dir_matrix_v2_state.json`; query line always carries it, non-suppressible.
- **Consumers**: informational only until VALIDATED; any trading-path use = shadow (automatic-implementation) + CEO approval, unchanged.

## 5. Files & protocol

- **Create**: `scripts/dir_matrix_v2.py` (modes: `train/predict/resolve/score/validate/query/--selfcheck`; own jsonl `data/dir_matrix_v2_predictions.jsonl`, own models dir, own state), `config/hermes-dir-matrix-v2.{timer,service}` (hourly, modeled on v1 units; **enabled only after bug_hunter PASS** per v1 precedent), report `brain/analysis/direction-matrix-v2-validation.md` (data-pin: window bounds + row count + sha per §15.6), result checkpoints `automation/ceo/checkpoints/dir-matrix-v2-*-result-*.md`.
- **Read-only inputs**: `dir_matrix.py` (machinery/definitions by import), `structure_analysis.py`, `adx_atr_analysis.py`, `continuum_engine.py`, `auto_analysis.py`, v1 jsonl (head-to-head + calibration set), candles.db.
- **NEVER touched**: v1 script/units/jsonl/state, `hermes_constants.py` (tunables = documented CLI defaults, shadow-monitor precedent), trading path, closed `probability-matrix` artifacts.
- **Protocol**: build → code review → **bug_hunter last**; per-unit commits; canonical push; THE PATTERN on every number (n, cluster-robust CI, reproduce cmd, data-pin).
- **Stopping-rule symmetry** (from v1): gate runs on frozen bars; failures get ONE honest report; design changes = spec amendment with fresh bars, never bar edits.

## 6. Non-goals (v2)

Deeper models (n too small: 720 rows at 1h), order-book/history features (not stored), funding/OI (not local), speed-percentile (stale stream), multi-asset (BTC only), trading-path consumption, dashboards (query/JSON first).
