# Direction Matrix v1 — code review (result-2, 2026-11-23)

**Scope**: `bfd1427b` (5 files) + spec-errata `a8b0587c` (`brain/plans/direction-matrix-spec.md`).
Read-only review — nothing fixed here; a bug_hunter runs after this.

**TLDR:** The UNVALIDATED gate is **honest and reproducible**: I recomputed every limb
independently from the script's own data path (pinned to the builder's exact windows AND
fresh), hand-checked 3 features + a label against raw candles, and stress-tested the
negative (warm-feature rerun, provisional-label removal, CITL-vs-train-freq alternative) —
**all three horizons stay UNVALIDATED on every variant**. No CRITICAL. One HIGH: the
upstream API seeder marks the **forming** candle `is_closed=1`, so live `predict`/`query`
can build features from a not-yet-closed bar (and result-1 §6.6's collector-lag disclosure
is wrong) — the builder's own gate run happened during a seeder-inactive window and is
clean, but fix before enabling the timer.

## Verdicts

| Commit | Verdict |
|---|---|
| `bfd1427b` (script + config + validation report + result-1) | **PASS-WITH-FIXES** |
| `a8b0587c` (spec errata, 1 line) | **PASS** |
| **Overall** | **PASS-WITH-FIXES** — gate sound; HIGH-1 must land before `enable hermes-dir-matrix.timer` |

## Findings

| # | Sev | Where | What breaks | Fix |
|---|---|---|---|---|
| 1 | **HIGH** | `scripts/dir_matrix.py:214-226` (fetch has no upper-time bound) ← upstream `scripts/price_collector.py:191-196` (`_store_candles` writes `is_closed=1` for EVERY API candle, incl. the exchange's in-progress one) | `is_closed=1` ≠ closed. Evidence at review time: `candles_1h` row ts=02:00 (closes 03:00) and `candles_4h` row ts=00:00 (closes 04:00) both `is_closed=1` with close = current price (89 min premature); predict at 02:27:54Z logged calls anchored at 15m 02:30 / 1h 03:00 / 4h 04:00 — i.e. the newest "closed" base-tier bar was still forming, so the operator-facing `query` line can be computed on a **partial bar** (4h call made 93 min before its bar closes). Same mechanism gives `validate` runs during seeder-active windows (BTC: 4h-age ≥ 2h ⇒ ~50% of the time) **one provisional test label per horizon** (label source bar not yet closed). No *future* data ever enters (everything ≤ now), and the builder's gate run was seeder-inactive — proven by their T_last = last truly-closed bar — so committed numbers are unaffected (sensitivity: dropping that row → same verdicts). result-1 §6.6 ("marks is_closed ≈ one bar period AFTER true close") is factually wrong for seeder rows; also, a just-matured call can resolve against a row the aggregator won't heal (`WHERE volume = 0`) until the seeder's next active window (≤ 2 h later). | dir_matrix: add `AND ts + iv*60 <= ?` (= now) to `fetch_tier` (also closes the missing-upper-bound bug); correct §6.6 disclosure. Upstream: `_store_candles` should set `is_closed` from close-time vs now. |
| 2 | MED | `scripts/dir_matrix.py:85` (`FETCH_DAYS = 41`) | 4h tier gets only **66 pre-window bars** for span-300/200 EMAs (needs ~900; the table holds 90 d — never fetched). Quantified vs full-history fetch: `4h_ema200_dist_pct` mean Δ **0.35**, max **0.77 pct-pt** across the window; `4h_ema300_side` flips 1/181; these columns feed **all three** horizon models. Also breaks byte-reproducibility: features at the same anchor change as `fetch_start` slides (observed: 4h Brier 0.9629 vs report 0.9630 with *identical labels*; 1h-EMA seed shift). The builder applied warmup reasoning to *omit 1m* but not to the fetch window itself. Sensitivity: full-history fetch → **verdicts unchanged** (UNVALIDATED×3), so it does not explain the negative. | Fetch full available history for feature computation, slice the 30 d window afterwards (or `FETCH_DAYS ≥ 120`); document. |
| 3 | MED | committed `brain/analysis/direction-matrix-validation.md:11-13` | Report numbers are **not byte-reproducible**: pin sha recomputed over the exact report window with byte-identical formatting = `6913197d…` ≠ report `cc2e388c…` (15m; 1h/4h likewise) → the candle slice mutated after 01:41:35Z. Evidence: rowid re-insert anomalies (15m ts 2026-11-15 07:15, 1h ts 2026-11-15 06:00), 2 test-label flips (15m) / 1 (1h), 4h labels/freqs unchanged. Cause: multiple writers on the same rows (candle_seed API upsert + aggregator volume-guard + backfill `INSERT OR REPLACE`). dir_matrix itself is read-only (`mode=ro`, SELECT-only) ✓; the data-pin **detected** the drift — that's its job; verdicts robust (same limbs). 4h train freqs reproduce *exactly* (.339/.250/.411) — its labels didn't move. | Archive the pinned candle slice (or validate against a snapshot copy) if byte-reproduction matters; at minimum note that re-runs drift with the live DB. |
| 4 | LOW | `dir_matrix.py:819-831` (`walk_forward` split) | Exactly **1 of 2304 train rows** has its label outcome bar at/after the first test anchor (15m: last train row 11-17 02:15, label from bar closing 02:30 = first test row). One-row boundary leakage; no verdict effect. | Exclude train rows with `anchors[i+step] ≥ first_test_anchor`. |
| 5 | LOW | `dir_matrix.py:479-497` (`cluster_ci`) | Day-cluster CI is fragile at D=6–7: 2 label flips moved 15m limb-(a) p from 0.087 → 0.836 (partial last day gets equal cluster weight); reported `diff` is row-weighted while the CI center is day-weighted. FAIL either way. | Disclose D and both centers (already discloses D); optionally size-weight clusters. |
| 6 | LOW | `dir_matrix.py:848-853` (top-decile CI) | Unbounded normal-theory CI (4h `[−0.742, 1.742]`, n_top=4) — passes vacuously. Cosmetic; (b) fails via CITL regardless. | Clip to [0,1] or mark "uninformative at n<10". |
| 7 | LOW | `dir_matrix.py:523` (`hit` tie-break) | `max(probs, key=…)` breaks exact ties toward `up` (dict order); undocumented. | Document or use an explicit tie rule. |
| 8 | LOW | `dir_matrix.py:1063-1076` (selfcheck alignment) | The brute-force check is **correct** (`flatnonzero(ct ≤ anc)[-1]` ≡ `searchsorted(…, 'right')−1` on sorted `ct`; includes an off-by-one-second anchor) but narrow: one tier, one column, no `idx < 0` (before-first-bar → NaN) branch. My real-data cross-TF spot check (1h/4h columns at a 15m anchor) covers the multi-tier grid. | Add the NaN-before-first-bar case. |
| 9 | LOW | `dir_matrix.py:179-191` (`write_calls`) | No lock on jsonl read-modify-write; a concurrent `predict`+`resolve` could double-append. Timer is oneshot (low risk); ponytail: accept until the timer is enabled. | `flock` on the jsonl if concurrent runs ever happen. |
| 10 | LOW | result-1 §1/§3 wording | "full 30d windows" (some backfill rows span 29.8 d — feature-depth clamp); "spec allowed joblib/pickle" (spec is silent on format). Both immaterial. | Tighten wording. |

No CRITICAL. Nothing touches the trading path, `hermes_constants.py`, or other timers.

## 1. Independent gate recompute (headline — all three horizons)

Method: `dir_matrix.build_dataset` (script's own data path) + my own split/Brier/cluster-CI/CITL
arithmetic, cross-checked against the script's `walk_forward` (matched to 1e-12) and against the
committed report. Two runs: **(A) pinned** to the report's exact window bounds with builder-time
label knowledge; **(B) fresh** on current data, `validate` run twice (byte-identical reports
excluding the `Generated:` line → determinism ✓).

### (A) Pinned-window recompute vs builder's report

| horizon | n win/trn/tst (clusters) | Brier model | Brier base (TRAIN freqs) | Δ | day-cluster 95% CI | p | CITL max vs test (vs train) | top-decile | limbs a/b/c → VERDICT |
|---|---|---|---|---|---|---|---|---|---|
| **15m** mine | 2880/2304/576 (7) | **0.6756** | **0.6534** | **+0.0221** | **[−0.0481, 0.0574]** | **0.836** | **0.1381** (0.2066) | n=58, claim 0.480, emp 0.414, CI [0.282, 0.793] → PASS | FAIL/FAIL/PASS → **UNVALIDATED** |
| 15m report | 2880/2304/576 (7) | 0.6748 | 0.6533 | +0.0215 | [−0.0047, 0.0517] | 0.087 | 0.1357 (—) | n=58, claim 0.482, emp 0.431, CI [0.303, 0.809] → PASS | FAIL/FAIL/PASS → **UNVALIDATED** |
| **1h** mine | 720/576/144 (6) | **0.6802** | **0.6473** | **+0.0329** | **[−0.0661, 0.1319]** | **0.432** | **0.0965** (0.1833) | n=15, claim 0.542, emp 0.333, CI [−0.226, 0.637] → PASS | FAIL/FAIL/PASS → **UNVALIDATED** |
| 1h report | 720/576/144 (6) | 0.6755 | 0.6476 | +0.0279 | [−0.0690, 0.1249] | 0.492 | 0.0839 (—) | n=15, claim 0.550, emp 0.333, CI [−0.189, 0.606] → PASS | FAIL/FAIL/PASS → **UNVALIDATED** |
| **4h** mine | 180/144/36 (6) | **0.9629** | **0.6390** | **+0.3239** | **[0.0997, 0.5482]** | **0.0138** | **0.1011** (0.1767) | n=4, claim 0.987, emp 0.500, CI [−0.742, 1.742] → PASS | FAIL/FAIL/PASS → **UNVALIDATED + UNSTABLE-LOW-N** |
| 4h report | 180/144/36 (6) | 0.9630 | 0.6390 | +0.3240 | [0.0998, 0.5483] | 0.0138 | 0.1012 (—) | n=4, claim 0.987, emp 0.500, CI [−0.742, 1.742] → PASS | FAIL/FAIL/PASS → **UNVALIDATED + UNSTABLE-LOW-N** |

- **4h reproduces to 4 decimals** (labels, freqs, CI, p all exact).
- **15m/1h drift is source-data mutation, not harness error**: pin sha over the report window
  with byte-identical formatting ≠ report sha (Finding 3); train membership/freqs match to 3 dp;
  2–3 test labels differ (recent candles rewritten after 01:41:35Z). The builder's numbers are
  internally self-consistent (their CI/p/means cross-check: t≈2.04, 6 df → p=0.087 ✓).
- Limb outcomes are **identical in both columns** on every horizon: (a) FAIL, (b1) FAIL, (b2)
  PASS, (c) PASS → UNVALIDATED ×3. n's, cluster counts, ε, UNSTABLE-LOW-N trigger all match.

### (B) Fresh `validate` ×2 (current data) — structural reproduce

Byte-identical reports (excl. timestamp); verdicts `15m=UNVALIDATED · 1h=UNVALIDATED ·
4h=UNVALIDATED+UNSTABLE-LOW-N`; n=2880/720/180 unchanged; limb pattern unchanged:
15m Δ+0.0256 CI [−0.0321, 0.0559] CITL 0.1442 · 1h Δ+0.0416 CI [−0.0562, 0.1306] CITL 0.1044 ·
4h Δ+0.3362 CI [0.0730, 0.5095] CITL 0.1300 — all (a) FAIL, (b) FAIL.

### Stress tests — could the honest negative be a harness artifact? (No.)

| Variant | 15m | 1h | 4h |
|---|---|---|---|
| Warm features (full-history fetch, fixes Finding 2) | UNVALIDATED | UNVALIDATED | UNVALIDATED |
| Drop the provisional-label row (Finding 1 mechanism) | UNVALIDATED | UNVALIDATED | UNVALIDATED |
| CITL vs **train** freqs instead of test freqs (spec "base rate" ambiguity) | 0.2066 > 0.05 FAIL | 0.1833 > 0.05 FAIL | 0.1767 > 0.05 FAIL |
| Oracle constant predictor (test freqs) Brier, for reference | 0.6324 < model 0.6756 | 0.6176 < model 0.6802 | 0.5233 < model 0.9629 |

Every variant fails the same limbs. The negative is real: on this walk-forward the model does not
beat a train-frequency constant at any horizon, and calibration-in-the-large misses by 2–3× the
±0.05 budget (test-week class mix shifted hard, e.g. 15m side 0.303 → 0.188).

## 2. Three-feature hand-check (fixed anchor 2026-11-15 12:00 UTC, raw `candles_15m/1h/4h`, independent loop implementations — no pandas, no dir_matrix code)

| Feature (frame column) | Frame value | Independent hand-compute | Δ | Verdict |
|---|---|---|---|---|
| `15m_rsi14` (Wilder α=1/14, seeded at first delta) | 54.941776 | 54.941776 | 0.0 | MATCH |
| `15m_bb_pos` (20,2; sample std) | 0.609029 | 0.609029 | 4.6e-13 | MATCH |
| `15m_ema50_dist_pct` ((c−EMA50)/EMA50·100, span 50) | 0.575503 | 0.575503 | −6.8e-14 | MATCH |
| `1h_rsi14` (cross-TF at same anchor) | 49.209507 | 49.209507 | −1.4e-14 | MATCH (right TF/table) |
| `4h_ema50_dist_pct` (cross-TF) | −8.250072 | −8.250072 (same fetch window) / −8.249896 (full 90 d) | 9.4e-14 / 1.77e-4 | MATCH; residual = Finding-2 seed effect only |
| `15m_z20` direction | 0.4361 | (65351.00−65067.98)/648.967 = 0.4361 | 0 | sign convention ✓ |
| `4h_ema300_side` sign | −1.0 | c 65351 < EMA300 78608 → −1 | 0 | convention ✓ |
| `1h_chop24` (flip≥2/24h) | 0.0 | 0 flips → 0 | 0 | MATCH |

**Label hand-check** at the same anchor: raw closes 65351.00 → 65352.00 ⇒ r = **0.1530 bps**,
frame/dm r = 0.1530 bps, class **side** both, anchor gap **900 s** (same-tier next bar — no tier
mixing; `step = HORIZONS[h] // TF_MIN[base] = 1` for all three horizons), ε=5 bps inclusive
boundaries verified by selfcheck (±5→up/down, 4.9→side).

Feature frame integrity: **57 columns, exactly as specced** — per-TF × {macd_hist_sign,
macd_hist_slope_sign, rsi14, z20, bb_pos, vol_ratio, ema50_dist_pct, ema200_dist_pct,
ema300_side, slope20_pct} + mom{60,240,1440}z (4h tier correctly omits mom60z) + `1h_chop24`
(only 1h) + votes_{bull,bear,neutral} + tod_sin/cos; prefixes confirm each column is sourced
from its own tier's table; all window rows have zero NaN (usable = window−1 exactly);
RSI-computed-but-never-added bug from result-1 §6.8 is fixed (`out['rsi14']` present, line 259).

## 3. Priority checks

1. **No-lookahead (gate path): PASS.** Features causal (truncation test correct; `searchsorted
   closed_at ≤ anchor` brute-force check itself correct — Finding 8 notes its narrowness);
   scaler fit inside the pipeline on **train rows only**; base-rate frequencies from **TRAIN**
   (`freq_tr`, line 833 — never test); split = contiguous `idx[:-k]`/`idx[-k:]` on time-ordered
   rows, no shuffle, `random_state=42` only on deterministic lbfgs; labels eval-only, never
   columns of X. `train_mask_at` requires the label bar closed ≤ anchor for every backfill call
   (verified). **Caveat = Finding 1** (forming-bar `is_closed` lie affects the *live* path and
   future seeder-active gate runs; builder's run clean; no future data ever).
2. **Feature frame: PASS** — table above + 57-column audit.
3. **Labels + ε: PASS** — fixed table 5/10/20 (`5·√(H_min/15)` ✓ errata), inclusive ±ε, same-tier
   1-bar-ahead arithmetic, fixed ε (never window stats) → labels stable across retrains.
4. **Gate arithmetic: PASS** — (a) Δ/CI/p with D=7/6/6 clusters disclosed; (b) CITL = max over
   3 classes of |mean p − freq(test)| ≤ 0.05 (robust to train-freq reading too) + top-decile CI
   contains claim; (c) n=2880/720/180 disclosed, 4h never pooled, UNSTABLE-LOW-N at n<300 fires
   for 4h (180<300). Verdict = `pass_a and pass_b and pass_c` (line 858) — **no partial path
   yields VALIDATED**; `pass_c` only encodes "n disclosed", which the same code always prints.
5. **score/query/resolve: PASS** — dedup by (ts,horizon): 4 predict runs → **0 duplicate keys**,
   final run "no new call rows (all (ts,horizon) already logged)" ✓; matured-join arithmetic
   **149 joined of 152** (3 pending) verified pre-review; `hit = argmax(p) == actual` ✓;
   reliability bins sum to n_resolved (68/67/16 ✓); query prints `· UNVALIDATED` on every line
   from state (only `validate` writes status; `predict` preserves it; default PENDING — never
   suppressible) ✓; ≥70% zero-case prints `n=0`, never 0% (score AND query) ✓.
   Builder's score claims re-derived exactly from the pre-review snapshot: 15m n=67 Brier
   0.6292/ll 1.0550 ≥70% n=0 · 1h n=66 0.6771/1.0700 40% n=5 · 4h n=16 1.0401/2.0521 27% n=11 ✓.
6. **Determinism + data-pin: PASS (with Finding 3)** — selfcheck 40/40; validate ×2
   byte-identical; report carries window bounds + row count + sha per horizon; same-data reruns
   identical, cross-time reruns drift only because the live DB mutates (sha pin exposes it).
7. **Hygiene: PASS** — `mode=ro` + URI ✓, cursors in `finally` ✓, SQL+params printed to stderr ✓,
   zero network imports ✓, only stdlib/sklearn/scipy/joblib/paths imports (no trading path) ✓,
   `git show --name-status bfd1427b` = exactly the 5 files ✓, `hermes_constants.py` diff = 0 ✓,
   timer unit **not installed/enabled** (`systemctl is-enabled` → not-found; enable line in unit
   comment ✓), `--help` epilog prints label/ε/features/model/Brier/gate formulas before any data ✓.
   All six modes + selfcheck ran exit 0 (train n=2880/720/180 = spec §2.3 exactly).
8. **Deviations: PASS with corrections.** (1) ε errata upheld — formula/table/selfcheck agree
   5/10/20; (2) `--backfill` default 0 preserves spec timer behavior ✓; (3) 1m omission
   permitted-with-disclosure ✓ (but see Finding 2 — same warmup logic not applied to the fetch);
   (4) joblib — spec silent, disclosed ✓; (5) timer not enabled ✓. Extra stated notes: query
   suffix required by §2.5 ✓; protocol gap (builder couldn't spawn review) honestly disclosed —
   this review + bug_hunter close it ✓. **Silent issues beyond the five:** the incorrect
   collector-lag disclosure (Finding 1) and the undisclosed 4h-EMA warmup bias (Finding 2);
   `slope20_pct` kept as signed magnitude vs spec's "slope sign" is documented in the script
   header (superset of spec, acceptable).

## 4. Reproduction

```bash
python3 scripts/dir_matrix.py --selfcheck                    # 40/40 PASS
python3 scripts/dir_matrix.py validate --report /tmp/v.md    # verdicts; run twice → byte-identical
python3 scripts/dir_matrix.py score | query --horizon all | predict   # dedup appends 0
# pinned recompute + hand-checks + warmup/provisional sensitivities: /tmp/dmrev/*.py (review scratch)
```

Status after review runs: `data/dir_matrix_state.json` = UNVALIDATED ×3 (4h + UNSTABLE-LOW-N);
predictions jsonl gained only genuinely-new anchors (data slid during review); no tracked file
was modified by this review.
