# === INDEPENDENT VERDICT === — Direction Matrix v2 SPEC (pre-build audit, 2026-11-23)

**Auditor**: independent (own-conclusions). All files read from scratch; every claim
below re-verified by running code/queries on this box. No other analysis trusted.
**Spec under review**: `brain/plans/direction-matrix-v2-spec.md` (v1.0 DRAFT).
**Date**: 2026-11-23.

Reproduce (commands I ran):
- `python3 scripts/dir_matrix.py --selfcheck` → **PASS (42 checks)**
- import probe of `dir_matrix, structure_analysis, adx_atr_analysis, continuum_engine, auto_analysis` → **all 5 IMPORT OK, no writes on import**
- sqlite3 ro queries on `data/candles.db` (schema/span/coverage/breadth)
- jsonl prefix scans on `data/dir_matrix_predictions.jsonl` (191 rows, 188 resolved)
- continuum history span query on `/var/www/hermes/data/continuum_data.json`
- zigzag causal-prefix + crafted lookahead-trap tests (see claim 1)
- EMA300 warmup decay computation on the 539 closed BTC 4h bars

---

## Claim 1 — Structure/ADX primitives exist, importable, anchor-evaluable without lookahead; confirm-lag discipline implementable as written

**Verdict: PARTIAL**

**Evidence**
- Import: all five claimed modules import cleanly (tested). `adx_atr_analysis`
  transitively pulls `hermes_constants` + `backtest_trend_momentum_v3.compute_adx`
  (module has `if __name__ == '__main__'` guard at :625, no module-level I/O) — safe.
- Purity: `atr`/`zigzag`/`classify` (structure_analysis.py:47/57/87) and
  `_wilder_atr`/`_adx_peak`/`_atr_peak`/`_post_peak_extreme` (adx_atr_analysis.py:47/65/78/90)
  are all pure functions on arrays. `classify(swings, last_close)` uses ONLY the swings
  handed to it + last_close — no hidden state.
- Causality: zigzag has the prefix property — `zigzag(full[:k+1])` equals the swings
  confirmed by bar k in the full run (tested at k=150/300/450/599: PASS). So slicing
  the candle series at anchor t gives exactly the swings confirmed by t. No new
  primitive code needed — the discipline is implementable as written.
- **Trap (not disclosed)**: the discipline requires RE-RUNNING zigzag per anchor slice.
  A naive implementation that runs zigzag once on the full fetch and filters by
  `extreme_idx ≤ t` LEAKS: I crafted a slow-retrace series where a swing with
  extreme at bar 100 is confirmed at bar ~700 — filter-by-idx includes it at t=300,
  the sliced run does not (leak=1 demonstrated). Spec wording ("confirmed by bar t")
  is correct but silent on filter-vs-rerun.
- **Not anchor-safe (not disclosed)**: `structure_analysis.analyze()`/`load_candles()`
  and `adx_atr_analysis.lifecycle()`/`_load()` fetch latest-N by `ts DESC` with only
  `is_closed=1` (the HIGH-1 lie — seeder marks forming bars closed). v2 must NOT use
  these entry points; it must call the named primitives with v1's anchor-bounded
  `fetch_sql`. Spec names the primitives (right ones) but never says the package
  entry points are unusable at a past anchor.
- Lifecycle-flag composition (TRENDLESS/RUNNING/PEAKED/DUAL-PEAK/EXHAUSTION) lives in
  `lifecycle()` which is DB-bound; re-deriving it on sliced arrays is small new code
  (~20 lines) — not disclosed as new code, but trivial.
- `auto_analysis.chop_flips_24h` (:28) reads the RECORDED `continuum_data.json`
  anchored at the file's own last entry — not t-anchored at all. Spec correctly says
  "t-anchored PORT … computed from candles_1h" — disclosed ✓.

**Confidence**: high (all four sub-points tested or read directly).
**Notes**: implementable with existing primitives; required build discipline is
"primitives + anchor-bounded slice per row, never analyze()/lifecycle()".

---

## Claim 2 — Continuum definitions self-contained/portable; 48h parity check meaningful

**Verdict: PARTIAL**

**Evidence**
- Definitions ARE self-contained and pure: `ema` (:122), `zscore` (:132),
  `linreg_slope` (:184), `classify_ema300_position` (:280), `classify_zscore` (:289),
  `linreg_slope_multi_tf` (:216) — constants come from `continuum_constants`;
  `trend_quality` = ema9/ema20/ema50 alignment (:653-670), pure given closes.
  Module import OK, `if __name__ == '__main__'` guard at :1468 — no live-only state
  in these functions themselves.
- **Entanglement the spec doesn't mention**: the RECORDED stream in
  `continuum_data.json` is (a) **1m timeframe, 30s tick density** (5,757 entries /
  48.0h — span claim ~48h verified: 47.999h), (b) `price` = live hl_cache tick
  (engine :598-602, not candle close), (c) `ema300_position`/`zscore_tier` recorded
  are **HysteresisState-confirmed** (:623-631 — path-dependent, needs replay of prior
  state), (d) EMA window = `limit=400` 1m closes (:587). A parity check that
  "recomputes vs recorded" must pick, per family, which of these it matches; spec
  names none of it and sets no tolerance. Raw side recomputed from candles will
  deviate from recorded confirmed position BY DESIGN.
- 48h parity over features used on 30d/90d windows: a smoke test for gross port
  bugs only. It cannot exercise EMA warmup behavior, regime coverage, or
  hysteresis-replay drift. Spec's own framing ("a feature family that can't
  reproduce the recorded stream is a finding") is honest, but without field/
  window/tolerance pinned it risks becoming guaranteed-noise or a silently loosened
  tolerance.

**Confidence**: high (read engine source; queried history: timeframes Counter={'1m':5756},
median gap 30s).
**Notes**: definitions port cleanly; parity check needs pinning (field, window,
tolerance) and must be labeled smoke-test-only.

---

## Claim 3 — v1 machinery reuse isolates FEATURES as the only variable (limb d premise)

**Verdict: PARTIAL**

**Evidence**
- Reusable pieces exist, are pure, and import safely: `fetch_sql`/`fetch_tier`
  (anchor-bounded, :225/:239), `EPS_BPS` table (:83, 5/10/20, formula-checked by
  selfcheck), `classify` labels (:368), `train_mask_at` (:454), `fit_pipeline`
  (:468), `proba3`, `cluster_ci` (:525), `walk_forward` (:884), `tier_features`/
  `align_features` (:266/:335 — no-lookahead asserted by selfcheck, re-run PASS 42).
  Module-level code = imports + constants only; `__main__` guard :1282; **no timer
  state, no writes on import** (verified by reading the whole module + import probe).
- **Gap at 4h**: limb (d) says "v1 refit on the same window". v2's 4h window is 90d;
  v1's machinery hardcodes `WINDOW_DAYS=30` (:86) and `FETCH_DAYS['4h']=85` (:90).
  Refitting v1 on the 90d window requires monkey-patching those module globals (or
  an equivalent) inside v2's process. Feasible without editing v1 files, but the
  spec specifies no mechanism — if the builder skips it, v1 trains 30d while v2
  trains 90d and the features-only premise breaks for 4h.
- "Identical test rows" also requires intersecting the usable masks (v2's extra
  features have extra NaN/warmup → feat_ok can drop rows v1 keeps). Implied by the
  wording, not spelled out.
- 15m/1h (both 30d, same fetch) isolate features cleanly as written ✓.

**Confidence**: high.
**Notes**: premise holds at 15m/1h today; 4h limb-d mechanics are underspecified.

---

## Claim 4 — Limb (d) head-to-head methodology: leakage-free for both, paired Brier sound at n=144 with day-clustered CI

**Verdict: PARTIAL**

**Evidence**
- Leakage-free: yes, for both — `walk_forward` fits only the first 80% of usable
  rows; features are causal (selfcheck no-lookahead re-run by me: PASS, 42 checks);
  labels are evaluation-only. v1 refit inside v2's process reads no future bar.
  (Caveat: at 4h the same-window patch of claim 3 must actually happen.)
- Paired comparison on identical rows with per-row Brier difference is the correct
  structure for "which model is better on the same outcomes" ✓.
- **CI fragility**: 1h test = 20% × 720 = 144 rows spanning **6 days → D=6 clusters**
  (15m: 576 rows, D=6–7). Cluster-robust t-CI with 6 clusters is few-cluster-biased;
  "CI excludes 0" as a pass/fail hinge at D=6 carries material false-pass/false-fail
  risk. This is v1 review finding 5/F7, explicitly *accepted as LOW* there — v2 spec
  does not re-disclose it. 4h (D=18) is acceptable.
- Also inherited: v1 review's "1-row train/test boundary leakage" (finding 4, accepted
  LOW) rides along in `walk_forward`.

**Confidence**: high on leakage/pairing (read + re-ran); medium-high on the
few-cluster critique (standard econometrics; D values computed from the spec's own
window math).
**Notes**: methodology structurally sound; the CI layer is the weak joint and it is
undisclosed in v2.

---

## Claim 5 — Calibration layer: 100-call floor justified; walk-forward wording airtight; raw+calibrated logging enough

**Verdict: PARTIAL**

**Evidence**
- 100-call floor: arbitrary but conservative and pre-registered — Platt on 3-class
  logits ≈ 6-9 params → ≥10-15 events/param at 100 samples. Cadence math from v1's
  live log: 15m ≈25 calls/day, 1h ≈25/day, 4h ≈6/day → floor reached ≈4-5d / 4-5d /
  ≈17d; below floor → raw + `UNCALIBRATED-CAL` flag = honest degradation ✓. Not
  power-derived, but as a *floor* it is defensible; not arbitrary in effect.
- Leakage line: "fitted on resolved v2 calls older than the current prediction".
  Any reading that yields labeled pairs implies `ts + H ≤ join-time ≤ T`:
  `resolve_rows` only joins when `ts+H ≤ now` (dir_matrix.py:565), and fitting needs
  `actual` (unresolved rows have none). So no reading leaks the scored row (the row
  scored at T has ts=T, ts+H>T, and no actual). **Effectively airtight** — but the
  spec never states the exact predicate; an implementer should assert `ts+H ≤ T`.
- **Gap 1 (real)**: limb (a) explicitly evaluates **raw** (`Brier(v2 raw)`), while
  §3 makes **calibrated** the query headline. No limb evaluates the calibrated
  output. A Platt fit on 100 calls can distort what consumers see while status says
  VALIDATED (for raw). Conversely raw can fail (b) CITL for a reason the calibrator
  fixes. Gate target ≠ displayed quantity.
- **Gap 2 (conditional leak)**: "raw and calibrated both logged" is enough for honest
  scoring ONLY if score/validate uses the logged calibrated value (produced at predict
  time, before the outcome existed). If score refits a calibrator on all resolved
  calls and rescores them, that is in-sample. Spec's "Never fit on the rows it says
  it scores" states intent but pins no mechanism (store calibrator params/fit-set
  bounds per row).
- **Internal contradiction**: spec header line 4 says v1's resolved-call log "becomes
  v2's external **calibration**/evaluation set"; §3 says the calibrator is fitted on
  **v2's own** resolved calls. These are different sets — calibrating v2 on v1's
  probabilities is methodologically invalid (different model). §3 is the correct one;
  the header must be fixed.

**Confidence**: high on all sub-points (mechanics read; cadence computed from live
jsonl: 191 rows / 188 resolved, spans verified).
**Notes**: floor OK; wording OK-in-effect; the raw-vs-calibrated gate gap and the
header contradiction are required fixes.

---

## Claim 6 — Gate completeness: 4 limbs, construct adversarial pass scenarios, check each blocked

**Verdict: PARTIAL** (scenarios below)

Adversarial scenarios constructed and evaluated:

| # | Scenario | Result |
|---|---|---|
| S1 | Mean-collapse: constant p = train freqs on every row | **BLOCKED** — limb (a) diff ≈ 0, CI includes 0 → FAIL |
| S2 | Near-constant predictor marginally better than base (captures tiny real signal) | **PASSES** — genuinely beats base with CI excluding 0 and, if test≈train freqs, CITL passes; top-decile limb passes vacuously (all rows in one bin, wide CI — v1 finding 6, unfixed in v2 wording). Arguably not "useless" (it has measured skill), but the top-decile sub-limb contributes ~nothing at degenerate p |
| S3 | Beats v1 but loses to base | **BLOCKED** — limb (a) |
| S4 | Beats base but loses to v1 | **BLOCKED** — limb (d) |
| S5 | Degenerate one-hot side-heavy (always modal class) | **BLOCKED** — limb (b): mean p one-hot vs class freqs → max diff ≈ freq of non-modal classes >> 0.05 |
| S6 | Model passes a/b/d with n < 300 at 4h | **PARTIAL-BLOCK (ambiguity)** — (c) says "UNSTABLE-LOW-N if n<300" but never says the flag *blocks* VALIDATED; v1 precedent had `pass_c=True` always (flag only). Wording must state whether UNVALIDATED accompanies the flag |
| S7 | **Displayed quantity ungated**: raw passes all 4 limbs, calibrated headline (fit on 100 calls) is distorted | **LEAKS** — no limb evaluates calibrated output (claim 5 Gap 1) |
| S8 | Calibrator refit at score time on all resolved calls, then rescored | **LEAKS (conditional)** — in-sample unless spec pins "score the logged calibrated value" (claim 5 Gap 2) |
| S9 | First gate run not blind: features designed after observing v1's Nov 21-23 failures, which sit INSIDE the first gate's test slice (last 6 days of the 30d window ending at run time) | **LEAKS (design-time contamination)** — spec's fresh-bars rule covers *amendments*, not the first run; overlap unacknowledged |
| S10 | Few-cluster CI (D=6) false-passes limb (a)/(d) | **LEAKS (statistical)** — claim 4 |
| S11 | Strong-in-TREND, catastrophic-in-CHOP model | **PASSES with disclosure only** — per-regime Brier is a disclosure, not a limb; acceptable for informational status but notable given regime-conditioning is v2's whole premise |

- "Beat v1 but lose to base" is indeed covered by (a) — the spec's parenthetical is
  correct ✓.

**Confidence**: high (each scenario traced against the literal limb definitions).
**Notes**: 6 of 11 scenarios cleanly blocked; S7/S8/S9/S10 leak or go ungated;
S6 is a wording ambiguity; S2/S11 are accepted-limitation class.

---

## Claim 7 — Feature budget ≤110 vs n: overfit risk at 1h; stated mitigation sufficient? THE PATTERN claim intact?

**Verdict: PARTIAL**

**Evidence**
- Ratios: 1h train 576 rows / ~110 features → multinomial LR ≈ 3×110 coefs
  (≈220 effective + intercepts) ≈ **2.5 rows per coefficient**. 4h: usable ≈519 rows
  (539 closed − ~19 rolling-warmup − 1 label), train ≈415 → ≈**1.9 rows/coef** —
  4h is MORE overfit-prone than 1h despite clearing the n≥300 floor (the floor counts
  rows, not rows/params). 15m (train 2304) is comfortable.
- Stated mitigation: L2, `C=1.0` frozen, StandardScaler fit-on-train-only,
  `random_state` fixed, features frozen at build time, one-shot pre-registered gate,
  amendments need fresh bars (§5 stopping-rule symmetry). Sufficient for **honesty**
  (an overfit model fails (a)/(d) OOS) — not sufficient for *power*; spec does not
  claim success, so this is acceptable if expectations are set.
- THE PATTERN ("no feature fishing"): pre-declaration + fresh-bars amendments is the
  correct discipline and is written down ✓ — building 110 first does NOT undermine it,
  with one exception: **S9** (features were designed using v1's 48h failures on data
  overlapping the first gate's test slice).
- **Data-depth defect (the strongest finding here)**: 4h DB holds exactly 540 rows /
  89.83d total (verified). A 90d window therefore has **zero pre-window headroom** —
  the very defect v1 review MED-2 flagged (with a prescribed fix: "fetch full history,
  slice window afterwards") becomes *uncorrectable* at 90d. Measured EMA300
  (span=300, 4h) seed influence: 0.88 after 20 bars, **0.51 after 100 bars**, 0.135
  after 300; two different seed points still differ 0.9% at bar 539. First ~100-300
  bars of the 90d window carry cold EMA features feeding all three models. Row-count
  claim verified literally: 540 total, 539 anchor-closed, ≈519 usable ≥300 ✓ — but
  "540 samples" oversells *warm* samples. Spec does not mention warmup at all.
- Breadth/N=20: 184 distinct tokens in candles_1h; **182 have ≥700/720 rows in the
  last 30d** — N=20 trivially satisfiable ✓. ts = INTEGER epoch, columns
  token/ts/open/high/low/close/volume/is_closed → v1's `ts + interval ≤ anchor`
  pattern ports cleanly ✓.

**Confidence**: high (all numbers queried/computed).
**Notes**: mitigation adequate for validity, thin for power; 4h warmup is a spec-level
omission.

---

## Claim 8 — v1-read-only guarantee: nothing in v2's design requires editing v1 files

**Verdict: AGREE**

**Evidence**
- `dir_matrix.py` module level: imports (`numpy/pandas/joblib/scipy/sklearn/paths`),
  `sys.path.insert`, constants, function/class defs — **nothing else**. No timer
  state, no reads, no writes at import. `if __name__ == '__main__'` guard at
  :1282-1283 ✓. Import probe: OK, no files created by the import.
- Limb d importing `fit_pipeline` (or `build_dataset`/`walk_forward`) is side-effect
  free apart from `sys.path.insert` (benign). Monkey-patching `WINDOW_DAYS`/`FETCH_DAYS`
  for the same-window refit happens in v2's process — no v1 file is written.
- "v1 continues untouched and collecting": `systemctl is-enabled hermes-dir-matrix.timer`
  → **enabled**, active, next 22:00 UTC; jsonl mtime 21:00 UTC today (hourly ✓).
  v1 read of its jsonl while v1 appends: `read_calls` skips malformed lines with a
  WARN ✓.
- All five reuse modules import OK (tested).
- Caveat (not a read-only issue): v1's F1 stale-label defect was found in
  result-3; the current v1 code carries the re-join fix (`resolve_rows`
  "RE-VERIFIED every run", :557) — verified present.

**Confidence**: high.
**Notes**: read-only guarantee is real; v2's own `resolve` must carry the same
re-join fix (spec silent on it).

---

## Claim 9 — Scope drift: nothing smuggled beyond "regime-conditioned structure-aware v2"; §6 non-goals consistent

**Verdict: AGREE**

**Evidence**
- §6 non-goals (deeper models, order-book, funding/OI, speed-percentile, multi-asset,
  trading path, dashboards) are all consistent with the body: §5 creates only
  v1-precedent artifacts (script, timer/service, own jsonl/state, validation report,
  checkpoints); consumers informational + shadow/CEO gate unchanged; breadth uses
  other tokens only as *features* for the BTC-only model (not multi-asset modeling);
  query/JSON only, no dashboard. No trading-path language added. Speed-percentile
  exclusion matches verified data state: `speed_history.json` entries end
  2026-04-29 (file mtime 2026-05-09 → "stale, May-2026" ✓), `speeds.db` = 0 bytes ✓.

**Confidence**: high.
**Notes**: one wording bug (header "calibration set", claim 5) — that is an
internal contradiction, not scope drift.

---

## Data-claim verification (spec §1 failure table + §2 data)

| Spec claim | Verdict | Evidence |
|---|---|---|
| 4h window → "540 rows ≥ 300 floor" | **AGREE (with warmup caveat)** | 540 rows / 89.83d total; 539 anchor-closed; ≈519 usable after rolling warmup + label. Floor clears. Zero EMA headroom — see claim 7. |
| ≥20 tokens with 1h over 30d breadth window (N=20) | **AGREE** | 182 tokens with ≥700/720 hourly rows in last 30d (184 distinct total). |
| ts epoch INTEGER + column names → anchor pattern ports | **AGREE** | Schema verified; identical to v1's fetch predicate. |
| continuum history ≈48h | **AGREE** | 47.999h (5,757 entries, 2026-11-21 21:19 → 11-23 21:19). |
| speed_history stale May-2026 / speeds.db 0 bytes | **AGREE** | mtime 2026-05-09, last entry ~2026-04-29; speeds.db 0 bytes. |
| CITL 0.08–0.14 > 0.05 | **AGREE** | v1 gate: 0.0839 (1h) / 0.1012 (4h) / 0.1357 (15m). |
| 4h ≥70% calls hit 31% (n=13) | **AGREE (exact)** | Recomputed from jsonl: 4/13 = 31%. |
| 4h n=180 UNSTABLE-LOW-N | **AGREE** | v1 gate window 180 < 300. |
| "Brier > base at every horizon (0.633/0.740/1.062 vs 0.581/0.663/0.628 on 48h)" | **PARTIAL** | Qualitative claim reproduced on current log: model 0.624/0.686/1.032 vs freq-base 0.592/0.637/0.612 — Brier > base at all three ✓. Exact triples NOT reproducible: prefix scan over all resolutions found no (n, numbers) match; spec gives no reproduce command (THE PATTERN gap; likely an earlier snapshot + possibly a different base definition). |
| "hit 43/19/18% vs modal baselines 53/38/45%" | **PARTIAL** | Direction confirmed on current log: argmax hit 44/26/29% vs modal-class hit 47/43/43% — hit below modal at all three ✓. Exact percentages not reproducible (best prefix fits: .45/.25/.25 vs .50/.41/.45); no reproduce command. |
| ε errata (pinned table 5/10/20) carried | **AGREE** | `EPS_BPS` (:83) + selfcheck formula assertions pass. |

---

## OVERALL

**OVERALL VERDICT: PROCEED-WITH-CHANGES**

The spec is fundamentally sound: data claims check out (breadth N=20, 4h row count,
stale-speed exclusions), the reuse/import/read-only claims are real (all five modules
import clean; `dir_matrix` has a `__main__` guard and zero import side effects; v1
timer confirmed enabled and collecting), the confirm-lag discipline is implementable
with the existing pure primitives (zigzag prefix property tested PASS), and the core
gate design blocks the obvious degenerate passes (mean-collapse, one-hot, beat-v1-
lose-base, beat-base-lose-v1 all blocked). v1's headline failure claims are directionally
reproduced; two exact numeric rows are not.

What must change before build: the gate validates RAW while consumers will see
CALIBRATED (ungated displayed quantity), the header contradicts §3 on whose calls
calibrate v2, limb (d)'s 4h same-window mechanics are unspecified, the 4h 90d window's
zero-warmup data reality is undisclosed, the few-cluster CI fragility (D=6) that v1's
own review flagged is silently inherited, and UNSTABLE-LOW-N's effect on the verdict
is ambiguous.

### Required changes (numbered, implementable — all before build unless noted)

1. **Fix header line 4**: v1's resolved-call log is the *evaluation/comparison* set
   only; calibration is fit on **v2's own** resolved calls per §3 (calibrating v2 on
   v1's probabilities is invalid). State v1 jsonl's exact role (disclosures) and note
   the F1 label-heal history (fix now present in v1 `resolve_rows`).
2. **Gate the displayed quantity**: either add limbs for the CALIBRATED output
   (re-run (a)/(b) on calibrated p where a calibrator exists) or make raw the headline
   until calibrated output passes its own limbs. Today no limb evaluates what the
   query shows.
3. **Pin calibrator mechanics**: write the fit predicate as an explicit
   `assert ts + H ≤ T`; store calibrator params/fit-set bounds with each logged call;
   mandate that `score`/`validate` score the **logged** calibrated value (never
   refit-then-rescore). Keep the 100-call floor + `UNCALIBRATED-CAL`.
4. **Specify limb-d 4h mechanics**: in-process patch (or parameterization) of
   `dir_matrix.WINDOW_DAYS` (30→90) and `FETCH_DAYS['4h']` (85→≥90) so v1 is refit on
   the identical 90d window, plus intersect the usable-row masks so test rows are
   literally identical; state no v1 file is written. Without this, 4h limb d is
   window-confounded and the features-only premise breaks.
5. **Disclose the 4h warmup reality**: DB depth = 90d total → zero pre-window
   headroom for a 90d window (EMA300 seed weight 0.51 at bar 100, ~0.9% residual
   seed bias at bar 539; v1 MED-2's prescribed fix is impossible at this window).
   Restate the claim as "540 rows, ~519 usable, EMA-warmth degraded for the first
   ~100–300 bars", and either accept+disclose, shorten the window (e.g. 60d), or add
   a warmup margin to `feat_ok`.
6. **Re-disclose few-cluster CI**: 15m/1h gate test spans 6 days → D=6 (15m D=6–7)
   day clusters; "CI excludes 0" hinges on a fragile few-cluster t-CI (v1 review F7,
   accepted there, absent here). Report D in the validation report and mark (a)/(d)
   CI fragile at D<10 (consider wild-bootstrap/CR2).
7. **Define UNSTABLE-LOW-N semantics**: state explicitly whether n<300 *blocks*
   VALIDATED or is flag-only (v1 precedent was flag-only). Recommend: verdict cannot
   be VALIDATED with n<300.
8. **Pin the parity check**: per family, name the recorded field, the definition
   (raw vs HysteresisState-confirmed), the recomputation window (`limit=400` 1m
   closes), and tolerance (recorded price is a live 30s tick, not a close); label the
   48h span a smoke test, not evidence for 30d/90d behavior.
9. **Attach reproduce commands to §1's failure table** (or recompute it at spec
   freeze): two rows (Brier triple 0.633/0.740/1.062 vs 0.581/0.663/0.628; hit
   43/19/18 vs modal 53/38/45) do not reproduce from the current log — direction
   holds, numbers don't (THE PATTERN rule 1).
10. **Disclose first-gate blindness** (or run the first gate on bars after spec
    freeze): feature design consumed v1's Nov 21–23 failures, which lie inside the
    first gate's test slice; the fresh-bars rule currently covers amendments only.
11. **One chop definition**: the regime flag should reuse v1's existing `1h_chop24`
    (already inside the 57) instead of also porting `auto_analysis.chop_flips_24h`
    (recorded-stream anchored, different EMA seeding) — two chop flags that can
    disagree would corrupt the regime× features and per-regime reporting.
12. **Carry v1's resolve re-join fix** (already in v1 `resolve_rows`, :557) into v2's
    `resolve` mode + a selfcheck case; spec §5 lists the mode but states no
    correctness requirement for it.
