# SPEC: Direction Matrix v2 — regime-conditioned, structure-aware, calibrated

**Status**: v1.1 — incorporates own-conclusions verdict (`brain/verdicts/2026-11-23-direction-matrix-v2-spec-verdict.md`, `717dd5be`), all 12 required changes applied. Ready for build.  
**Relation to v1**: v1 (`scripts/dir_matrix.py` + `hermes-dir-matrix.timer`) **continues untouched and collecting** — its resolved-call log is **v2's EXTERNAL EVALUATION set only (never a calibration set — calibration uses v2's own resolved calls, §3; header v1.0 was wrong, corrected per change 1)**. v2 is a NEW script + NEW state files; v1 code/units/jsonl are read-only inputs, never edited (import-safe: `__main__` guard verified at dir_matrix.py:1282, zero import side effects — claim 8 AGREE).

**Changelog v1.1 (12 verdict changes)**: (1) header calibration-set correction; (2) displayed quantity gated — query headlines RAW until calibrated passes its own limbs (§3); (3) calibrator predicate asserted `ts+H ≤ fit_time`, fit-set bounds stored per row, score uses logged values only; (4) limb-d 4h mechanics specified (in-process patch of `WINDOW_DAYS`/`FETCH_DAYS`, identical usable-row intersection, zero v1 writes); (5) 4h zero-warmup disclosed + sensitivity; (6) few-cluster CI re-disclosure (report D, fragile at D<10); (7) UNSTABLE-LOW-N **blocks VALIDATED**; (8) parity check pinned; (9) §1 numbers given fixed-window reproduce cmd; (10) first-gate blindness handled; (11) one chop definition (v1's `1h_chop24` only); (12) F1 re-join fix carried into v2.

## 0. One-liner

Same operator question — BTC P(up/side/down) per horizon — but with the features that were missing (structure, ADX lifecycle, continuum, regime), a calibration layer trained on honest walk-forward data, and a gate that must beat **both** base rates **and v1 head-to-head** before anything trusts it.

## 1. Why v2 (measured v1 failures driving each change)

| v1 failure (48h live evidence) | v2 answer |
|---|---|
| Faded both trend legs (down-lean before +9.9% pump, up-lean before dump); per-horizon hit 43/19/18% vs modal baselines 53/38/45% | Persistence features (structure/AD lifecycle/linreg alignment) + **regime flag & per-regime reporting** |
| Model Brier > base at every horizon (0.633/0.740/1.062 vs 0.581/0.663/0.628 on 48h) | Richer features + calibration layer + head-to-head limb vs v1 |
| CITL miscalibrated (0.08–0.14 > 0.05) | **Platt calibration, walk-forward** on v2's OWN resolved calls (never trained on calls it is calibrating; never on v1's log) |
| 4h n=180 (UNSTABLE-LOW-N) | 4h trains on **90d** (540 samples ≥ 300 floor); 15m/1h keep 30d |
| 4h ≥70% calls hit 31% (n=13) | calibration layer + gate limb (b) unchanged — overconfident calls must die at the gate |
| horizons contradict (15m down / 4h up) | cross-horizon state features (4h regime/state fed into 1h/15m models) |

**§1 numbers provenance (change 9)**: the 48h hit/Brier triples above were computed ad-hoc in the design session — reproduce with the FIXED window (call ts ∈ [2026-11-21T21:05Z, 2026-11-23T21:05Z], resolved rows only, p-key map `p_up/p_side/p_down`, modal baseline = argmax class of actuals):
`python3 -c "<derive hits/brier-vs-class-freq per horizon from data/dir_matrix_predictions.jsonl with the fixed bounds>"` — full snippet pinned in the validation report at build time. Drift note: healed-label corrections (F1) may move ≤2 rows after the pin; directions of all claims held across the auditor's own independent re-derivation (qualitative ✓). **Every §-table number in v2's report ships with its reproduce cmd (THE PATTERN — including on my own tables).**

## 2. Data & features (reuse-first, per operator)

### 2.1 Sources — all LOCAL, no API (full-analysis data-source rule)
1. **`data/candles.db`** (mode=ro, **anchor-bounded fetch** `ts+interval ≤ anchor` — v1's HIGH-1 fix, copied verbatim): every feature is computed from closed bars ≤ anchor, so training rows and live rows share one code path.
2. **Reused engines** (import/port definitions — NEVER redefine):
   - `structure_analysis.py`: `atr`, `zigzag`, `classify` primitives → per-TF structure state at bar t. **Confirm-lag discipline (full-analysis §15.2)**: swings count only if confirmed by bar t (no unconfirmed-extreme lookahead).
   - `adx_atr_analysis.py`: `_wilder_atr`, `_adx_peak`, `_atr_peak`, `_post_peak_extreme` → ADX value/slope, lifecycle flags (TRENDLESS / RUNNING / PEAKED / DUAL-PEAK / EXHAUSTION).
   - `continuum_engine.py` **definitions**: EMA300 side, z-score tier windows, linreg windows/alignment, trend_quality — read the definitions from source. **Parity check pinned (change 8)**: field = `ema300_position` (raw boolean-by-price definition vs recompute), window = last 400 ticks of recorded history, tolerance = 0 mismatches expected for the raw definition; the recorded **HysteresisState-confirmed** fields (`zscore_tier`, `ema300_position` hysteresis) are **path-dependent at 1m/30s ticks and will legitimately diverge from close-time recomputes — reported as informational divergence with the definition difference stated, NOT as a pass/fail**. The 48h recorded span is a **smoke test only** (features run over 30d/90d — stated everywhere it's cited).
   - Chop regime: **v1's existing `1h_chop24` feature, reused as-is (change 11 — one chop definition only; no third variant)**. `auto_analysis.chop_flips_24h` used solely for live-parity display, not as a feature source.
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
- **Calibration layer (new)**: per horizon, a **Platt (logistic) calibrator** fitted on **v2's OWN resolved calls** (change 1: never v1's log — that is evaluation-only) satisfying **asserted predicate `ts + H ≤ fit_time`** (change 3), with fit-set bounds + calibrator params **stored per logged prediction row**. Minimum 100 resolved calls before any calibration applies — below that, output raw + flag `UNCALIBRATED-CAL`. Never fit on the rows it scores. `score` reads ONLY the logged calibrated value — never refits at score time (refit-at-score = in-sample).
- **Output / headline rule (change 2 — the displayed quantity is the gated quantity)**: both raw and calibrated p are logged per row. `query` headlines **RAW** p; calibrated p appears on a secondary line labeled `cal:` (informational). Headline switches to calibrated **only after calibrated p passes its own limbs** (see gate limb (e)). A quantity never gated can never be the primary display.

## 4. The gate (pre-registered — must pass before ANY consumer trusts v2)

Walk-forward (train 80% → test 20%, day-clustered CI), per horizon — **four limbs, all required**:
- **(a)** Brier(v2 raw) < Brier(base-rate predictor trained on train), CI excludes 0
- **(b)** CITL ≤ 0.05 (max |mean p − base| across classes); top-decile CI contains claimed mean
- **(c)** n disclosed per horizon; 4h judged alone; UNSTABLE-LOW-N if n < 300
- **(d) NEW — head-to-head**: Brier(v2) < Brier(**v1 model**) on the **identical test rows**, CI excludes 0. **4h mechanics pinned (change 4)**: v1 refit in-process with `WINDOW_DAYS`/`FETCH_DAYS['4h']` patched (30→90/85→90 equivalents — in-memory only, **zero v1 writes**, import-safe probe re-verified), both models scored on the **intersection of usable rows** (feat_ok masks both), so limb d isolates features exactly as designed.
- **(e) NEW — calibrated limb**: whenever calibration is eligible (n≥100), same (a)+(b) must pass on **calibrated** p — required for the headline-switch rule (§3), not for raw-VALIDATED status.
- **Disclosures (not limbs)**: per-regime Brier table (CHOP vs TREND — catastrophic regime slice is report-only, change 11 in verdict's S11); hit vs modal-class baseline; calibrated vs raw; **cluster count D printed per limb; limbs (a)/(d) flagged FRAGILE when D < 10** (1h test spans 6 days → D=6, few-cluster t-CI is the known v1-F7 fragility — re-disclosed per change 6).
- **UNSTABLE-LOW-N BLOCKS VALIDATED (change 7, the stronger option)**: n < 300 → that horizon's verdict = UNVALIDATED, period — flag AND blocker.
- **First-gate blindness (change 10)**: features were designed using 2026-11-21→23 tape evidence (§1's pump/dump). Every gate run whose test slice overlaps data that informed design is labeled **NON-BLIND (advisory)** in the report. **The first OFFICIAL gate** — the only one whose verdict may move status to VALIDATED — must have its test rows **entirely after the spec freeze (close-time > 2026-11-23T23:59Z)**; earlier runs inform, never validate.
- **4h warmup reality (change 5)**: DB hard-caps at 90d → the 90d window has **zero EMA headroom** (simple seed → ~0.51 weight at bar 100, ~0.9% residual bias at bar 539; v1's MED-2 depth fix is IMPOSSIBLE here). Accepted-with-disclosure: seed EMAs at window start, quantify seed-residual per feature in the report, plus **sensitivity run excluding the first 100 rows** — gate verdicts must not flip (flip → report, don't commit).
- Verdict = a∧b∧c∧d per horizon → VALIDATED else UNVALIDATED (never partial). Status in `data/dir_matrix_v2_state.json`; query line always carries it, non-suppressible.
- **Consumers**: informational only until VALIDATED; any trading-path use = shadow (automatic-implementation) + CEO approval, unchanged.

## 5. Files & protocol

- **Create**: `scripts/dir_matrix_v2.py` (modes: `train/predict/resolve/score/validate/query/--selfcheck`; own jsonl `data/dir_matrix_v2_predictions.jsonl`, own models dir, own state), `config/hermes-dir-matrix-v2.{timer,service}` (hourly, modeled on v1 units; **enabled only after bug_hunter PASS** per v1 precedent), report `brain/analysis/direction-matrix-v2-validation.md` (data-pin: window bounds + row count + sha per §15.6), result checkpoints `automation/ceo/checkpoints/dir-matrix-v2-*-result-*.md`.
- **Read-only inputs**: `dir_matrix.py` (machinery/definitions by import), `structure_analysis.py`, `adx_atr_analysis.py`, `continuum_engine.py`, `auto_analysis.py`, v1 jsonl (**evaluation + head-to-head only — NEVER calibration, change 1**), candles.db.
- **NEVER touched**: v1 script/units/jsonl/state, `hermes_constants.py` (tunables = documented CLI defaults, shadow-monitor precedent), trading path, closed `probability-matrix` artifacts.
- **F1 carried forward (change 12)**: v2's `resolve` re-joins matured rows against healed candles every run (v1's post-bug_hunter `resolve_rows` semantics: adopt healed label with `CORRECTED` log, return `(new, corrected)`) + the same selfcheck case (stale resolved label corrected, 0 new / 1 corrected).
- **Protocol**: build → code review → **bug_hunter last**; per-unit commits; canonical push; THE PATTERN on every number (n, cluster-robust CI, **reproduce cmd for every table incl. our own**, data-pin).
- **Stopping-rule symmetry** (from v1): gate runs on frozen bars; failures get ONE honest report; design changes = spec amendment with fresh bars, never bar edits.

## 6. Non-goals (v2)

Deeper models (n too small: 720 rows at 1h), order-book/history features (not stored), funding/OI (not local), speed-percentile (stale stream), multi-asset (BTC only), trading-path consumption, dashboards (query/JSON first).
