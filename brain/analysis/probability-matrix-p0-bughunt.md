# bug_hunter: P0 probability_matrix final verification (post-fix)

**Scope**: commits `037ea1ce` (P0 build) + `631f9289` (code-review fixes) — the full
probability-matrix P0 delta. Contract: `brain/plans/probability-matrix-spec.md` v1.1
(§3.1/§3.2 formulas, §4 four limbs, §8 two-file scope).
**Protocol**: build → code review (PASS-WITH-FIXES, 11/11 applied) → **bug_hunter (this file)**.
**Date**: 2026-11-20. **Verifier**: bug_hunter subagent (fresh eyes on the fixes themselves
and on failure modes both prior passes missed).

**Skill**: `skills/shared/bug-hunter/SKILL.md` loaded and followed (read code → verify logic
vs spec → query actual data → run the code → severity-ranked report → uncertainty check).

---

## 1. Verdict

| Item | Verdict |
|---|---|
| Commit `037ea1ce` (P0 build) | **PASS** — scope/contract met (exactly the 2 spec files, SELECT-only, §3.1/§3.2 formulas, four limbs, honest STOP); its 11 review defects are all remediated by `631f9289` |
| Commit `631f9289` (code-review fixes) | **PASS** — 11/11 fixes present and correct (see §3); none broken |
| **Overall P0 delta** | **PASS** — no CRITICAL, no HIGH; 1 MED + 3 LOW reported, none changes any limb verdict or the GATE |
| Fresh re-run gate | **GATE: STOP** \| limbs **(a)=FAIL (b)=INCONCLUSIVE (LOW-COVERAGE) (c)=FAIL (d)=PASS**, exit 0 — matches the committed report **byte-identically** (`git diff` empty after re-run) |

No fixes were made by this pass (nothing CRITICAL). Findings are report-only.

---

## 2. Findings

| # | Sev | file:line | What breaks | Fix |
|---|---|---|---|---|
| F1 | MED | `scripts/probability_matrix.py:571-580` (limb (a) CI) | Limb (a)'s CR1 is computed on `y − wr_b` treating `wr_b` (bottom-decile WR — a data-dependent statistic) as a fixed constant; the report honestly labels it "ΔWR-proxy". Quantified on this data: **implemented p=0.208 vs proper two-sample cluster-robust p=0.087** on the same trades (conservative in this run, but the direction is data-dependent). Verdict unaffected here: both ≥ 0.05, so limb (a) FAIL and the STOP hold either way (and G=4 is small-G flagged). Risk is future runs where the proxy and the proper test straddle 0.05. | In limb (a), build per-cluster sums `Σ_top(y−wr_top)/n_top − Σ_bot(y−wr_bot)/n_bot` over the union of clusters (CR1, df=G−1) and test `Δ` directly; or at minimum state in §4/§5 that the p-value is a proxy test for a difference of means. |
| F2 | LOW | `scripts/probability_matrix.py:745-749` (test-horizon caveat) | Count is correct (1967/2780 outside horizon) but the label "(train-side / pre-fold-gap)" only names the leading 30d train side; the **trailing ~25d** (anchor−65d → anchor, ~557 trades) is also outside the horizon and unnamed. | Wording: "(train-side 30d + trailing 25d after the last test fold)". |
| F3 | LOW | `scripts/probability_matrix.py:447-452` (decile split ties) | Rank deciles split **identical-p trades** across the top-2/bottom-2 cut by tie-break `(p, signal, close_time)`. Real data: deciles 2/3 share boundary p=0.466 (n=25/25), so some equal-p trades count in bottom-2 and some don't — outcome-relevant since tied trades have different y. Deterministic and documented, but the cut is arbitrary at ties. | Optional: assign whole tie-groups to the same side of the cut (or note the tie count at each boundary in §4). |
| F4 | LOW | `scripts/probability_matrix.py:364-365` (`store_stale`) + `:853-855` (§6 leakage wording) | (a) `n_store_stale` diffs raw store keys vs raw window signals — inconsistent with `matched_*` counts if normalization-fallback matches ever occur (0 this run → latent only). (b) §6 says store "computed from this same 90d window"; store `computed_at=2026-11-20T00:20` vs report anchor `06:33` — same 90d span, ~6h offset. Leakage conclusion (in-sample) unaffected. | (a) diff on normalized keys when reporting fallback matches. (b) say "the store's own 90d window (computed_at …)". |

**CRITICAL: none. HIGH: none.**

Fail-open-to-PASS hunt (critical check): **no failure mode found that can produce a
report reading PASS/PROCEED-TO-P1.** Gate requires all four verdict strings exactly
`'PASS'`; every exception path either exits 1 before the atomic write (tmp+`os.replace`)
or maps to INCONCLUSIVE/FAIL (see §5).

---

## 3. Per-fix verification (11/11)

1. **t-based CI** — **verified**. `cluster_ci` (line 278-284): `crit = t.ppf(0.975, g-1)`
   and `p = 2*t.sf(|t|, g-1)` — same df = G−1 for both; selfcheck asserts both against
   scipy exactly (line 1126-1133, and runs green: `selfcheck PASS (21 asserts)`).
2. **Anchored SQL window** — **verified**. SQL lines 133-135 anchor to
   `(SELECT MAX(close_time) - make_interval(days => %s) …)` under the same
   `status='closed' AND pnl_usdt IS NOT NULL` predicate; zero live `NOW()` in code
   (grep: only the comment saying "NOT NOW()"). Python fold anchor == SQL anchor (fetched
   max row always satisfies `> max−days` for days>0), so no two-clocks drift; printed log
   confirms `SQL start = anchor-90d`.
3. **Small-G caveat** — **verified**. Lines 669-677 collect limbs with `G<10`, log it, and
   emit it in §4 (report line 85) and §7 (line 132): `small-G (G=4/6<10)`.
4. **Rank-key decile split** — **verified**. Final-fold check (lines 583-586) now calls the
   **same** `reliability_buckets` with the same `(p, signal, close_time)` rank key and the
   same `buckets[8:]` / `buckets[:2]` split as the pooled deciles — no threshold
   approximation left. Independent recompute reproduced 55.6% (n=9) vs 0.0% (n=8), Δ=+55.6%.
5. **Finally-cursor** — **verified**. `load_store` initializes `cur = None` and closes it in
   `finally` (lines 187-201); `fetch_trades` closes cur+conn in `finally` (178-182).
6. **Dynamic assert count + 2 asserts** — **verified**. Assert count computed via
   `inspect.getsource` (line 1142-1144): actual assert statements in `selfcheck` = 21,
   printed = 21 (old hardcoded "17" was already wrong vs actual 19 — dynamic count fixes
   the drift class). The 2 new asserts: t(G−1) CI identity (1130) and g<2 raises (1140).
7. **scipy-import-inside-try + limbs b/c wrapped** — **verified**, empirically. Import sits
   inside the `try` with a generic `except Exception → {'ok': False}` (lines 271-277), and
   both limb (b) (622-625) and limb (c) (643-646) callers are additionally wrapped. Ran
   calibrate with a sabotaged `scipy` (import raises): **exit 0, limbs a/b/c = INCONCLUSIVE
   (b also LOW-COVERAGE), GATE STOP, no PROCEED anywhere**; report renders "cluster-robust:
   unavailable (ImportError…)".
8. **Horizon caveat** — **verified** (lines 745-749; report line 49: "35d of the 90d window,
   1967/2780 outside"). Wording nit only → F2.
9. **`is None` fallback chain** — **verified; behavior preserved on every real path.**
   Lines 961-978. Win side: any real mean there is the mean of strictly-positive pnls
   (y=1 ⇒ pnl>0), so it is either `None` or `>0` — truthiness and `is None` are
   **identical** for it. Loss side: mean of pnls≤0 can equal exactly `0.0` only when every
   loss entry is `0.0` (breakeven exits) — that is the one behavioral divergence vs the old
   `or` chain (old: fell through to the global mean; new: keeps the true 0.0, marked by the
   comment at line 967), and that divergence **is the fix** (a real mean is not missing).
   No path yields a wrong-signed avg_win/avg_loss; `ev_per_risk` still floors at EPS_AMT.
10. **`sorted()` collisions sample** — **verified**. Line 391 `sorted(ks)`; report line 25
    renders collision sets in sorted order.
11. **Parity-comment correction** — **verified**. Docstring lines 55-64 and `NORM_RULE`
    113-118 now state the rule is a **SUPERSET, NOT exact parity** vs
    `signal_compactor.py:2245`, with the delta spelled out and "0 fallback matches this
    run" — matches the report (exact 2780, normalized-fallback 0).

---

## 4. Verdict integrity (fresh re-run + independent recompute)

- `python3 scripts/probability_matrix.py --selfcheck` → **PASS (21 asserts)**, exit 0.
- `python3 scripts/probability_matrix.py calibrate --days 90 --folds 5` (run by me):
  **exit 0**, `GATE: STOP | limbs: (a)=FAIL (b)=INCONCLUSIVE (LOW-COVERAGE) (c)=FAIL (d)=PASS`,
  and `git diff -- brain/analysis/probability-matrix-calibration.md` is **empty** → the
  committed report is **byte-identical** to a fresh run (anchor 2026-11-20 06:33:10,
  2780 trades, store computed_at unchanged). No drift.
- **Independent recompute from raw trades** (own script, own folds/admission/deciles/CR1,
  not importing `probability_matrix`) — every number matches the report:

| Quantity | Report | Independent recompute |
|---|---|---|
| raw trades / pooled covered | 2780 / 251 of 813 | 2780 / 251 of 813 |
| per-fold (n_train/n_test/covered) | 1410/121/53, 1100/231/44, 963/133/37, 752/195/75, 746/133/42 | identical |
| limb (c) Brier(p), β, CI, p, G | 0.2512, +0.0012, [−0.0081,+0.0104], 0.759, 6 | 0.2512, +0.0012, [−0.0081,+0.0104], 0.759, 6 |
| limb (a) WR top/bot, Δ, t, p, G | 49.0%/28.0%, +21.0%, +1.60, 0.208, 4 | 49.0%/28.0%, +21.0%, +1.599, 0.208, 4 |
| final-fold sign check | 55.6% (n=9) vs 0.0% (n=8) | 55.556% (n=9) vs 0.000% (n=8) |
| limb (b) intersection, Brier p/conf | 198/813 = 24.4%, 0.2465 / 0.3798 | 198/813 = 24.4%, 0.2465 / 0.3798 |

- **STOP honesty**: limb (c) β = Brier(p) − 0.25 = **+0.0012 > 0** → p is (point-estimate)
  *worse* than baseline and the CI spans 0 → FAIL is the truthful outcome, not an artifact.
  Limb (a) FAIL = p=0.208 ≥ 0.05; cross-checked against a proper two-sample cluster-robust
  test: p=0.087 — still ≥ 0.05, so **the FAIL (and the STOP) are robust** (F1 notes the
  proxy-test gap for the future). Limb (b) fails only on the pre-registered 30% coverage
  floor (24.4%) with the numbers printed — no silent drop. Neither too-negative nor
  too-positive vs reality found.
- Spot-check of GATE string construction: `PROCEED-TO-P1` requires all four verdicts
  `== 'PASS'` exactly; every INCONCLUSIVE/LOW-COVERAGE variant (incl. the
  `'INCONCLUSIVE (LOW-COVERAGE)'` strings) and NaN comparisons (`NaN < x` is False) fall to
  STOP.

---

## 5. Failure modes (each: exit code, message, PASS-leak?)

| Scenario | How tested | Exit | Message | Report reads PASS? |
|---|---|---|---|---|
| DB down (PG) | real CLI with `psycopg2.connect` sabotaged to raise `OSError` | **1** | `[PROB-MATRIX] ERROR OSError: connection refused…` | **No** — no report written (hash unchanged), no GATE in output |
| Empty table / no trades in window | `fetch_trades → []` (and `--days -5`, where `MAX+5d` yields empty) | **1** | `No trades in window — nothing to calibrate.` | **No** — write never reached |
| Zero folds (`--folds 0`) / too few folds (`--days 5`) | real CLI | **1** | `ERROR: only 0 full folds fit in 90d (need >=3…)` | **No** — aborts before building the report |
| scipy missing | fake `scipy` whose import raises | **0** | limbs a/b/c `INCONCLUSIVE`, `cluster-robust: unavailable (ImportError…)` | **No** — `GATE: STOP` |
| G<2 (single cluster) | `cluster_ci` unit | n/a | `{'ok': False, 'need at least 2 clusters'}` | **No** → INCONCLUSIVE |
| n<2 / empty | `cluster_ci` unit | n/a | `need at least 2 observations` | **No** → INCONCLUSIVE |
| mfe all-NULL | `report` mode, all mfe `None` | **0** | quantiles render `n/a` | n/a (report mode has no verdict); no crash |
| confidence all-NULL | `calibrate`, all fc `None` | **0** | limb (b) `INCONCLUSIVE (LOW-COVERAGE)` (0/… < 30%) | **No** — `GATE: STOP` |
| cell_stats.db missing | full `__main__` run with `sqlite3.connect` sabotaged | **1** | `[PROB-MATRIX] ERROR OperationalError: unable to open database file` | **No** — report hash unchanged |
| data < requested window (40d data / 90d window) + folds with 0 covered trades | `calibrate --days 90` on short synthetic span | **0** | honest per-fold table with `0.0%` coverage, worst=0.0% | **No** — limb (d) `INCONCLUSIVE (LOW-COVERAGE)`, `GATE: STOP` |
| committed report after ALL tests | sha256 before/after | — | — | **unchanged (True)** |

Atomicity: report is written to `REPORT_MD + '.tmp'` then `os.replace` — any exception
mid-build leaves the previous report intact (verified by hash guards above).

---

## 6. Trading-path isolation

- **`.execute` sites: exactly 3** — `SQL` (line 163), `STORE_SQL` (194), `SELECT key, value
  FROM meta` (195). All three constants are SELECTs; no INSERT/UPDATE/DELETE/DDL/`commit`
  anywhere in the file (grep clean).
- **Writes**: only `open(tmp)` + `os.replace(tmp, REPORT_MD)` (905-909). `report` mode
  writes nothing (stdout only; ran it: exit 0).
- **Imports**: stdlib + `paths` + `psycopg2`/`_secrets` (lazy) + `scipy` (lazy, in try) +
  `cluster_t` (selfcheck only). **No** `hermes_constants`, signals, `signal_compactor`,
  decider, position_manager, tpsl imports (grep clean — matches are comments only).
- **Commits**: `git show --stat` — `037ea1ce` = 2 files, `631f9289` = 2 files, both exactly
  `scripts/probability_matrix.py` + `brain/analysis/probability-matrix-calibration.md`
  (spec §8: P0 touches ONLY these two) ✅.
- **Store PK**: `cells` table has `PRIMARY KEY (signal, direction, regime)`; live check
  519 rows / 519 distinct keys → no duplicates to silently overwrite in `match_store`.

---

## 7. Uncertainty check (skill step 9)

- **Assumptions**: the proper two-sample CR test used in the F1 cross-check is the standard
  cluster-robust difference-of-means (CR1, union G, df=G−1); with G=4 both tests are
  indicative (small-G caveat already in the report).
- **Edge cases not exercised live**: DB dying *mid*-fetch (single query — psycopg2 raises,
  same handler as T1); `REPORT_MD` directory unwritable (would raise at open → exit 1, tmp
  guard intact); `--days` very large (traced: folds fit, honest STOP path as in T9 — not run
  against 1000d explicitly).
- **Side effects**: none — this pass ran read-only probes plus redirected `/tmp` reports;
  the committed calibration report is byte-identical to HEAD; the only file added is this
  result file.
- **Choices I am not 100% of**: severity of F1 (MED vs LOW) — I chose MED because limb (a)
  is a gate limb and the proxy/proper p gap was 0.087 vs 0.208 on real data; it does not
  change this run's verdict.

---

## 8. Evidence commands

```bash
python3 /root/.hermes/scripts/probability_matrix.py --selfcheck          # PASS (21 asserts)
python3 /root/.hermes/scripts/probability_matrix.py calibrate --days 90 --folds 5
#   -> GATE: STOP | (a)=FAIL (b)=INCONCLUSIVE (LOW-COVERAGE) (c)=FAIL (d)=PASS
git diff -- brain/analysis/probability-matrix-calibration.md              # empty (byte-identical)
python3 /tmp/bughunt_recompute.py                                        # independent recompute, all match
python3 /tmp/bughunt_failure_modes.py                                    # 9 failure-mode cases, all fail-closed
git show --stat 037ea1ce 631f9289                                        # 2 files each
```
