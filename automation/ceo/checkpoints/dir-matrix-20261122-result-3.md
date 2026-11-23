# Direction Matrix v1 — final bug_hunter verification (result-3, 2026-11-23)

**Scope**: `bfd1427b` (build) + `664076ec` (review) + `7dacab98` (fixes), spec
`brain/plans/direction-matrix-spec.md` (ε errata 5/10/20bps). Mandatory last step of
build → review → fixes → **bug_hunter**. Everything below was re-run personally on this
box; no number is taken from a prior report on trust.

**TLDR:** Both fixes verified — HIGH-1 anchor-bounded fetch proven live against a DB
that was lying about forming bars *at probe time*, MED-2 per-tier depth verified with
warmup residue quantified (4h ema300_side: 0 flips vs full-history fetch). Fresh gate
verdicts: **UNVALIDATED ×3 (+4h UNSTABLE-LOW-N)**, no path to a false VALIDATED
anywhere. **Fail-open hunt: 11/11 probes fail-closed, 0 CRITICAL.** One new HIGH:
`resolve` freezes `actual` against DB rows that mutate after the join — **2 of 155
resolved labels already disagree with the healed DB** (one flips a `hit`) — and 3
pre-fix forming-bar calls from the review's own 02:27 run still sit in the score data.
Per-commit verdicts **PASS ×3**; overall **PASS** — the informational timer is safe to
enable (gate honest, status path clean, no trading path), with the resolve-label HIGH
as the top must-fix follow-up before the reliability numbers are trusted as a tuning
signal.

Reproduce: `python3 scripts/dir_matrix.py --selfcheck` · `... validate --report /tmp/v.md`
· `... train|predict|resolve|score|query --horizon all`

---

## 1. Findings

| # | Sev | file:line | What breaks | Fix |
|---|-----|-----------|-------------|-----|
| F1 | **HIGH** | `scripts/dir_matrix.py:558-559` (sticky `actual`) + `:574-585` (`db_lookup`) | **Frozen resolve labels.** `resolve_rows` skips any row that already has `actual`; outcome closes are read once from the live DB (`is_closed=1 AND ts IN (?,?)`) at first matured join and never re-checked. `candles_*.db` rows mutate after write (seeder upsert + aggregator/backfill re-inserts — review Finding 3's own mechanism). **Measured live: 2/155 resolved labels now disagree with the current healed DB** — `15m ts=2026-11-23 02:30` stored `actual=up, hit=False` vs healed `down` (**true hit=True — a correct call scored as a miss**); `1h ts=2026-11-22 23:00` stored `side` vs healed `up` (+25.5bps). No `resolved_at`/join-time closes are stored → undetectable without the kind of audit I ran, permanent, silent, and the hourly timer keeps joining inside the ≤1h post-maturity heal window. Corrupts `score` Brier/logloss/reliability bins and `query`'s last-30d Brier + ≥70% hit — i.e. spec §2.4's self-tuning measurement. Does **not** touch the gate (validate never reads the jsonl) or status. | Re-join matured rows every resolve run: drop the `if row.get('actual') is not None: continue` skip (join is idempotent, ~159 rows), or store `close_in/close_out` at join and re-join when the DB values change. ~3 lines + one selfcheck case. |
| F2 | MED | `data/dir_matrix_predictions.jsonl` — 3 rows logged **pre-fix** at the review's 02:27:54Z predict run (`15m ts=02:30`, `1h ts=03:00`, `4h ts=04:00`) | The fix stops *new* forming-bar calls but the known poisoned products of the bug were never purged or disclosed: 15m 02:30 is already **resolved with features built on a partial bar** and counts in score's n=72; 1h 03:00 and 4h 04:00 are pending (resolve at 04:00 / 08:00). Result-1 §6.6 documents the mechanism, not the inventory. | Purge the 3 rows (they violate the fix's own invariant) or add an explicit disclosure line to result-1/score output. |
| F3 | LOW | `brain/analysis/direction-matrix-validation.md` (as committed at HEAD) | Spec §2.6's report artifact is still the builder's **pre-fix 01:41Z generation**: it lacks the new Fetch/anchor disclosure line that `mode_validate` now emits (`dir_matrix.py:981-987`) and carries stale window/sha. The fix commit regenerated result-1 §6.6 but not this report. | Run `validate` once post-fix and commit the regenerated report (verdicts unchanged). |
| F4 | LOW | `dir_matrix.py:921,622,680,1224-1241` | "**Pinnable** run-ts → reproducible historical recomputes" (corrected §6.6 + EPILOG) is only true **in-code** (`build_dataset(now_ts=…)`): there is no `--now` CLI flag, so `validate`/`train` from the command line always anchor on wall clock. Reproducibility currently requires importing the module (as the review did). | Add `--now <epoch>` or soften the wording to "pinnable via the `now_ts` argument". |
| F5 | LOW | `dir_matrix.py:580-581` | `db_lookup` has no explicit `ts+iv<=now` bound — the only remaining unbounded candles read. Proven safe *today* because `resolve_rows` only calls it when `ts+H <= now`, which makes both bars non-forming by construction (matured gate ⇔ `closed_at ≤ now`, inclusive edge consistent with fetch/selfcheck). Safe only by caller discipline. | Add `AND ts + ? <= ?` with the run's now for defense-in-depth (same predicate as `fetch_sql`). |
| F6 | LOW | `dir_matrix.py:844-850` | Query status suffix sits only on **line 2** of each horizon's block; line 1 (the probability line) and the zero-calls line carry none. Never reads VALIDATED (state default `PENDING`, JSON has `status` per call, no flag suppresses it) — but a consumer grepping line 1 misses the verdict. | Print `· UNVALIDATED` on line 1 too, or emit status first. |
| F7 | LOW | review `664076ec` findings 4–10 unchanged | Still open, accepted: 1-row train/test boundary leakage (4); day-cluster CI fragility at D=6–7 (5); unbounded top-decile CI (6); `hit` tie-break toward `up` (7); selfcheck alignment narrow (one tier/column, no `idx<0` NaN branch — and the new forming-bar assert exercises `'15m'` only, mechanism shared across tiers) (8); no jsonl lock — oneshot timer, low risk (9); wording (10). | As review; none gate-critical. |
| F8 | LOW | `dir_matrix.py:866-917` | Degenerate-window gate crash is fail-*closed* but ungraceful: `walk_forward` on an empty/tiny usable set dies with a raw sklearn/numpy traceback instead of a `[DIR-MATRIX]` message (state is written only after all three horizons — `:957` — so nothing partial is persisted). | Wrap with a clear SystemExit message if it ever matters. |

**No CRITICAL.** Nothing in the delta touches the trading path, `hermes_constants.py`,
`price_collector.py`, or other timers.

## 2. Fix verification

### HIGH-1 — anchor-bounded fetch (`7dacab98`): **VERIFIED, including live**

- **Predicate**: `fetch_sql` (`dir_matrix.py:225-236`) = `… AND is_closed = 1 AND
  ts >= ? AND ts + ? <= ?` with **parameterized per-tier interval** `TF_MIN[tf]*60`
  (900/3600/14400 s) and the run anchor as the last param — visible in every printed
  SQL line (`params=('BTC', …, 3600, 1795404769)` observed). Inclusive `ts+iv == anchor`
  keeps a bar that closes exactly at the anchor — **consistent with the selfcheck**
  (bar `ts=anchor-900` kept, bar `ts=anchor-450` dropped, `dir_matrix.py:1101-1117`).
- **Selfcheck exercises the real SQL, not a re-implementation**: it calls
  `fetch_sql('15m')` and runs *that string* against an in-memory table whose schema
  matches `candles_15m`, inserting a lying `is_closed=1` forming row → assert drops it.
  Suite = **41 checks PASS, exit 0** (was 40 pre-fix; +1 forming-bar).
- **Anchor threading**: one `now_ts` per mode run (`train:622`, `predict:680`,
  `validate:921`) threaded into every horizon's `build_dataset` — same anchor printed
  for all three tiers per run (confirmed in stderr). predict/query anchor = wall clock
  at run start; validate/train anchor = the run's `now_ts` (pinnable in-code — see F4).
  All timestamps epoch-UTC end-to-end (`iso()`/`iso_z()` use `timezone.utc`; day
  clusters and tod sin/cos are UTC; no local-time anywhere).
- **Live proof (2026-11-23 03:31:52Z)** — the DB was lying *at probe time*:
  `candles_1h ts=03:00` (closes 04:00) and `candles_4h ts=00:00` (closes 04:00) both
  `is_closed=1` **while still forming** (28 min / 89 min premature). Unbounded read
  would return closes-04:00 bars; the bounded predicate returns `1h → open 02:00`,
  `4h → open 20:00`. A live `predict` at 03:34:48Z then logged `1h ts=03:00` and
  `4h ts=00:00` — the last *truly closed* bars — instead of the pre-fix run's
  `1h 03:00 / 4h 04:00` future anchors documented in result-2.
- **Historical pinned anchor**: SQL against a pinned `now-3h` keeps only bars with
  `ts+iv ≤ anchor` (`True` verified) — identical predicate for live and pinned runs,
  so both exclude forming bars the same way.
- **No other unbounded candles read** (grepped every `sqlite3`/`candles_`/`sq(` site):
  `fetch_tier:243` (bounded ✓) and `db_lookup:582` (resolve; matured-gated — F5) are the
  only DB call sites; `score`/`query` read the jsonl/state only; feature warmup and
  backfill all go through the same bounded `build_dataset` fetch.
- **Backfill alignment after the fetch change**: asserted per horizon at 4 backfill
  offsets (1h/6h/24h/168h): every `train_mask_at` row has its outcome bar
  (`anchors[i+step]`) closed **≤ that row's own anchor**, in-window, zero unmatured
  leaks (`15m n=2880/2880/2880/2480`, `1h 720/720/720/619`, `4h 179/179/180/154`).
  Labels and features share the same anchor — fetch-bound makes `known ≡ True` at the
  current anchor, and the step correctly excludes the not-yet-labeled last row
  (train `trained_through=03:15` while window ends `03:30` ✓).

### MED-2 — per-tier fetch depth: **VERIFIED**

- `FETCH_DAYS = {'5m': 33, '15m': 35, '1h': 45, '4h': 85}` (`dir_matrix.py:90`),
  printed on every run; clamp note fires when the DB is shallower (observed: `5m:
  DB depth 32.9d < requested 33d — clamped`, every run).
- **No rolling stat changes meaning with fetch depth** (tested `1h`, 40d vs 45d fetch,
  all 720 window rows): `macd_hist_sign`, `macd_hist_slope_sign`, `vol_ratio`, `chop24`
  **byte-identical**; `z20/bb_pos/slope20/mom*z` equal to FP noise (≤1.8e-11,
  re-association only). Hand-check: `z20` at a window row == (c−mean20)/sd20 of the
  **last 20 bars exactly** — a 35/45d fetch does not dilute a 20-bar z (rolling windows
  are index-relative, never fetch-depth-relative). RSI differs ≤1.5e-6 (ewm seed —
  warmup precision, converges with depth).
- **Warmup residue quantified** (`4h`, fixed 85d vs deepest-possible full-DB fetch):
  `ema200_dist_pct` ≤ **0.061 pct-pt**, `ema50_dist_pct` ≤ 1.9e-6, **`ema300_side`:
  0 sign flips** across the window — vs the review's pre-fix measurement at uniform
  41d (0.77 pct-pt max + 1 flip). Only EMA-family values move, in the converging
  direction; nothing changes meaning. (Review's sensitivity already showed full-history
  fetch → same verdicts.)

## 3. Fresh gate verdicts (mine, run 2026-11-23T03:28:47Z + independent recompute)

`validate` fresh (exit 0) → **UNVALIDATED ×3, +4h UNSTABLE-LOW-N**; state file
`data/dir_matrix_state.json` = `15m/1h/4h: UNVALIDATED` (4h `unstable_low_n=true`).

| horizon | n win/trn/tst (days) | (a) Brier m vs base, Δ, day-cluster 95% CI, p | (b) CITL max / top-decile | (c) | VERDICT |
|---|---|---|---|---|---|
| **15m** | 2880/2304/576 (7) | 0.6704 vs 0.6529, **Δ=+0.0174**, CI **[−0.0140, 0.0401]** p=0.282 → FAIL | **0.1169** > 0.05 FAIL; top-dec n=58 claim .498 emp .414 CI [.278,.817] PASS → (b) FAIL | PASS | **UNVALIDATED** |
| **1h** | 720/576/144 (7) | 0.6837 vs 0.6465, **Δ=+0.0373**, CI **[−0.0554, 0.1258]** p=0.378 → FAIL | **0.0907** FAIL; top-dec n=15 claim .554 emp .333 PASS → (b) FAIL | PASS | **UNVALIDATED** |
| **4h** | 180/144/36 (6) | 0.9622 vs 0.6390, **Δ=+0.3232**, CI **[+0.0874, +0.5590]** p=0.0169 → FAIL (significantly worse than base) | **0.1058** FAIL; top-dec n=4 claim .990 emp .500 PASS → (b) FAIL | PASS | **UNVALIDATED + UNSTABLE-LOW-N (180<300)** |

**Independent limb recompute** (my own split/fit/cluster-CI/CITL arithmetic on the
script's `build_dataset` data path — no `walk_forward` code reused):

- `1h`: Δ +0.0373 CI [−0.0554, 0.1258] p 0.3782, CITL 0.0907 — **exact match** to the
  script's report, to every printed digit.
- `4h`: Δ +0.3232 CI [+0.0874, +0.5590] p 0.01685, CITL 0.1058 — **exact match**.
- `15m`: Δ +0.0172 CI [−0.0085, 0.0446] p 0.1478, CITL 0.1130 — **exact match to the
  script's same-anchor rerun** (my run crossed the 03:30 bar close; the 03:28 report
  shows the pre-slide window — only difference is the window slide).
- **No partial path to VALIDATED**: verdict = `pass_a and pass_b and pass_c`
  (`:905`), `pass_c` is "n disclosed" (always printed), and status is written only
  after **all three** horizons compute (`:935-957`, report after that) — a mid-loop
  crash persists nothing. Only `validate` ever writes `status`; `predict` preserves it
  (verified live: status stayed UNVALIDATED across a predict run).
- **Structural compare vs committed report** (§15.6): identical structure — same
  n/train/test (2880/2304/576, 720/576/144, 180/144/36), same limb pattern
  (a FAIL / b1 FAIL / b2 PASS / c PASS), same verdicts, same UNSTABLE-LOW-N trigger;
  only the windows/shas slid 2h15m–3h with wall time (per §15.6 expected). Numbers in
  the fixer's stated neighborhood (result-1: 15m Δ+0.0215/CITL .1357 → fresh
  +0.0174/.1169; 4h +0.3240 → +0.3232).
- **Determinism**: two fresh validates differ only where the 15m window slid
  (1h/4h lines byte-identical); same-anchor reruns are byte-identical (proven by my
  independent recompute reproducing the script's same-anchor numbers exactly).
  `random_state=42` everywhere; selfcheck asserts identical coefs/proba on identical
  data.

## 4. Fail-open hunt — 11/11 fail-closed (0 paths to a false VALIDATED)

| Scenario | Observed | Reads as VALIDATED or as data? |
|---|---|---|
| DB missing/empty tier | `SystemExit: no closed rows for candles_15m (…) — cannot continue`, exit 1 | Error ✓ |
| Fewer bars than warmup (`n < step+50`, `:407`) + empty deep window | `SystemExit … cannot continue` / `too shallow: n=…`, exit 1 | Error ✓ |
| All-labels-one-class fit | sklearn `ValueError: needs samples of at least 2 classes`, traceback, exit 1 | Error ✓ |
| Degenerate/empty walk-forward window | crash (numpy/sklearn) **before** any state/report write | Nothing persisted; no partial VALIDATED ✓ |
| Joblib model missing/corrupt | **No load path exists** — `joblib.dump` only; every `predict` refits from data | Cannot fail ✓ |
| jsonl write failure (`append_calls`) | `FileNotFoundError` propagates; append (`:746`) runs **before** `write_state` (`:752`) → state untouched, exit 1 | Stale status preserved (UNVALIDATED) ✓ |
| Corrupt jsonl line | WARN + skip (2/3 rows kept), no crash | Degraded-but-explicit ✓ |
| Corrupt state JSON | `JSONDecodeError`, exit 1 | Error ✓ |
| Matured-join zero / score zero resolved | explicit `0 matured call(s) joined` / `score: 0 resolved calls — run predict --backfill…`, exit 0 | Explicit 0-data, never fabricated ✓ |
| Query, zero calls | `no call logged yet — run … predict first` per horizon | Instruction line, no probabilities ✓ |
| Query, calls but no validation ever run | status prints `PENDING` (state default) | Never VALIDATED; no flag suppresses status ✓ |

**Fail-to-VALIDATED = CRITICAL: none found.** Status is written exclusively by
`validate` from genuinely computed limbs; nothing hardcodes or defaults to VALIDATED.

## 5. Query / score honesty

- `query --horizon all`: every horizon block's status line ends `· UNVALIDATED`
  (3/3); `--json` emits valid JSON with `status: UNVALIDATED` ×3; line 1 lacks the
  suffix (F6, LOW); zero-calls/no-state paths covered above.
- `score`: `n_calls=159 n_resolved=155`; per-horizon n = 72/67/16 and **reliability
  bins sum exactly to n** (8+8+7·8=72; 7·7+6·6+6=67; 2·6+1·4=16); `≥70% calls: n=0`
  printed as `n=0` (15m), never 0%; per-horizon `n_resolved=0` branch prints `n=0`.
- `resolve`: `155/159` matured joined, `0` immature rows carry `actual`, jsonl
  `159 rows / 159 unique keys` — no dedup dupes; re-run `predict` appends 0
  (idempotent) ✓.

## 6. Hygiene / scope

- `git show --name-status` = exactly the expected files: `bfd1427b` 5 files
  (script, timer, service, validation report, result-1) · `664076ec` 1 file
  (result-2) · `7dacab98` 2 files (script, result-1 §6.6) ✓.
- `git diff HEAD -- scripts/price_collector.py` empty; no commit in the range touches
  it ✓. `hermes_constants.py` **not touched by any of the three commits** (the one
  in-range change belongs to unrelated `b675ab52` continuum_score work; working tree
  clean) ✓.
- Timer **not enabled**: unit not installed in `/etc/systemd/system`, `is-enabled →
  not-found`, `is-active → inactive`; enable line only in the unit comment
  (freq-shadow precedent) ✓. Service = oneshot `dir_matrix.py predict` only.
- `mode=ro` URI on every connect, cursors closed in `finally`, SQL+params printed to
  stderr on every query, zero network imports, imports limited to
  stdlib/numpy/pandas/scipy/sklearn/joblib/`paths` — no trading-path module ✓.
- Result-1 §6 deviations re-checked: ε errata 5·√(H/15) → 5/10/20 (formula+table+
  selfcheck agree) ✓ · `--backfill` default 0 ✓ · 1m omitted with disclosure ✓ ·
  status suffix ✓ · joblib ✓ · §6.6 collector-lag **correction present in result-1**
  ✓ · timer not enabled ✓ · protocol gap (review+bug_hunter) now **closed** ✓.

## 7. Verdicts

| Commit | Verdict | Basis |
|---|---|---|
| `bfd1427b` (build) | **PASS** | Its HIGH-1/MED-2 are verified fixed in `7dacab98`; selfcheck/gates/modes all re-run clean. Residual: F3 (committed validation report is the pre-fix generation). |
| `664076ec` (review) | **PASS** | Findings independently re-verified; its prescribed HIGH-1 fix landed exactly; LOWs 4–10 remain open as accepted (F7). Its "score bins sum / suffix on every line" claims re-confirmed (with F6 nuance). |
| `7dacab98` (fixes) | **PASS** | HIGH-1 proven live against a lying DB; selfcheck 41/41 exercising the real SQL; MED-2 residue quantified to ≤0.061 pct-pt with 0 sign flips; §6.6 correction present. |
| **Overall** | **PASS** — safe to enable the informational timer | Gate honest (UNVALIDATED ×3, independently recomputed), 11/11 fail-open probes fail-closed, no CRITICAL, no trading path, status path clean. **Must-fix follow-up: F1 (HIGH) before the reliability numbers are trusted as spec §2.4's tuning signal** — 3-line re-resolve; F2 purge/disclose alongside it. If the CEO wants zero outstanding HIGHs at enable, land F1 first — it is a data-loop fix, not a gate fix. |

**Uncertainties**: F1's mechanism (join-time stale close vs post-join row mutation)
cannot be disambiguated because no join-time closes/`resolved_at` are stored — the
proposed fix covers both. F2's inventory relies on the review's documented 02:27:54Z
run; I cannot prove no other pre-fix run hit a seeder-active window (result-1's own
runs were reviewed seeder-inactive). Corruption rates (2/155 labels, 3/159 poisoned
anchors) are point-in-time on live mutating data. Per instruction, **no files were
fixed** — report only; this result-3 is the sole file written/committed.
