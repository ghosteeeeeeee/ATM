# Bug-Hunter Verdict — Shadow MFE/MAE + Final Corrected Report

**Date:** 2026-10-25
**Verifier:** bug-hunter (independent, ran all queries/code — no numbers taken on trust)
**Files checked:**
- `/root/.hermes/scripts/shadow_trader.py`
- `/root/.hermes/brain/shadow_trades.db` (live DB — still being appended to while verified)
- `/root/.hermes/reports/20261025-shadow-final-corrected.md`

---

## === BUG-HUNTER VERDICT ===

### Fix 1 (MFE/MAE code): PASS
**Evidence:**
- `shadow_trader.py:1248` comment reads `# FIX 2026-10-25: Only use candles during the ACTUAL HOLD PERIOD,` — grep for `FIX 2026` returns **only** this line; no `FIX 2026-10-22` remains anywhere in the file.
- Hold-period filter present at `:1253-1257`:
  ```
  entry_ts_val = candles[0][0]
  exit_ts_val  = first_result.get('exit_ts', entry_ts_val + 86400)
  hold_candles = [c for c in candles if entry_ts_val <= c[0] <= exit_ts_val]
  ```
- Entry price at `:1191` is `entry_price = candles[0][1]  # open of first candle`. Grep for `context.price` / `ctx['price']` in the file: **zero hits**. MFE/MAE computed at `:1261-1266` from `entry_price` + `hold_candles` highs/lows.
- `mfe_pct`/`mae_pct` have exactly **one** writer (`:1279`) — no leftover 24h-window code path.

### Fix 2 (dead columns): PASS
**Evidence:**
- Schema comment at `shadow_trader.py:159-160`:
  `-- mfe_4h/mae_4h are DEAD COLUMNS (100% NULL, never written to)` / `-- Kept for schema compatibility; actual MFE/MAE is in mfe_pct/mae_pct`
- DB check: `SELECT COUNT(*) WHERE mfe_4h IS NOT NULL` = **0**, `mae_4h IS NOT NULL` = **0**, out of 22,064 rows. 100% NULL confirmed.

### Fix 3 (MFE/MAE data): PASS
**Evidence:**
- Population: `mfe_pct`/`mae_pct` non-null on **20,383 of 20,384** closed-with-net rows (99.995%; the single NULL is `first_exit_engine='hold'` — the no-engine-fired branch, which never sets MFE).
- Sign sanity: MFE > 0 on **18,535 (91.2%)**, MAE < 0 on **17,858 (87.6%)** — correct orientation (favorable positive, adverse negative).
- Magnitude sanity: MFE range `[-1.61, +47.35]`, MAE range `[-41.74, +1.40]`. Rows with |MFE|>50% = **0**, |MAE|>50% = **0**, MFE>100% = **0**, MAE<-100% = **0** → no wrong-entry-price signature.
- **Empirical proof the rebuild used the hold window, not 24h** (recomputed 150 random rows from `candles.db` using the same code path):
  - median |stored − recomputed| = **0.068 pp (hold window)** vs **1.852 pp (24h window)**
  - mean |diff| = 0.135 vs 2.794; within 0.1 pp: **63.3% (hold)** vs **18.0% (24h)**
  - hold-window is closer than 24h on 116/150 rows → stored values are hold-window values.
- Report MFE/MAE ratio column reproduces: SHORT 0.544/0.368 = **1.48** ✓, LONG 0.546/0.438 = **1.25** ✓.

### Fix 4 (cluster statistics): **FAIL**
**Evidence:**
- ✓ Cluster-robust t is used throughout and is reproducible: gate-passed headline `t_cluster = -10.75` over **2,703 clusters** (group-by `created_at`, t-test on cluster means) — I recomputed exactly **-10.75 / 2,703 clusters**. Every table row (engines, signals, gates, directions) reproduced to the printed precision.
- ✓ Number of clusters reported: `| **Cluster-robust t** | **-10.75** (2,703 clusters) |` (report line 29) and methodology line 208.
- ✗ **Naive t is never reported.** grep for `naive|uncorrected|plain t|non-cluster|iid` across `20261025-shadow-final-corrected.md` (and the prior `20261025-shadow-fresh-analysis.md`): **zero matches**. Every table has only a `t_cluster` column; no uncorrected/iid t appears anywhere in the report or in `scripts/shadow_mode_analysis.py`.
- For reference, the naive (iid) t for the headline is **-11.66** (cluster-robust -10.75) — the report gives the reader no way to see the design-effect correction.

### Fix 5 (period): PASS
**Evidence:**
- Report line 5: `**Period:** Oct 7-25, 2026 (all trades) / Oct 20-25, 2026 (gate-passed only)`; line 25 `Gate-passed | 8,702 (42.9%, Oct 20-25)`; lines 211 & 221 repeat "gate-passed period is only 6 days (Oct 20-25)" and "Period corrected — gate-passed is Oct 20-25 … not Oct 7-25".
- DB ground truth: gate-passed rows span **`2026-10-20 20:40:11` → `2026-10-25 16:20:29`** = Oct 20-25 ✓. All rows span `2026-10-07 20:00:12` → Oct 25 ✓.
- Gate-passed count = **8,702** at report time ✓ (8,755 now — live growth only).

### Fix 6 (reconcile): PASS
**Evidence:**
- Report states all three: 22,024 total (lines 4, 22, 204, 222), 20,298 closed with net PnL (lines 4, 23, 217, 222), 8,702 gate-passed (lines 25, 222).
- DB at verification: closed-with-net = **20,298 → 20,384**, gate-passed = **8,702 → 8,755**, gate-blocked = **11,596 → 11,629** (both grew while I watched — the shadow trader is live). The report's snapshot reconciles exactly: 11,596 + 8,702 = **20,298** ✓; gate-passed share 8,702/20,298 = **42.9%** ✓, blocked 57.1% ✓.
- Total rows 22,024 vs 22,064 now = +40 new rows written after the report (report mtime 21:20, DB max `created_at` 21:20:38 and climbing) — drift, not an error.

### Fix 7 (report accuracy): PASS
**Evidence (every number recomputed from the DB with the report's own methodology):**
| Report claim | Recomputed | Match |
|---|---|---|
| NET PnL (gate-passed) -781.0% | -781.0 | ✓ |
| AVG -0.090% ± 0.718% | -0.0898, sd 0.7179 | ✓ |
| Cluster t -10.75 (2,703 clusters) | -10.75, 2703 | ✓ |
| WR 58.2% (5,065 W / 3,637 L) | 58.2%, 5065/3637 | ✓ |
| Avg win +0.419 / avg loss -0.798 / RR 0.52 / breakeven 65.6% | 0.419 / -0.798 / 0.517 / 65.6% | ✓ |
| SHORT 5,421 / 62.6% / -255.4% / -0.047 / t -7.03 | identical | ✓ |
| LONG 3,281 / 50.9% / -525.7% / -0.160 / t -9.24 | identical | ✓ |
| pm_trail SHORT 3,171 / +1,236.6 / t 55.26; LONG 1,457 / +537.1 / t 39.45 | identical | ✓ |
| hard_max SHORT 1,366 / -1,285.3 / t -242.61; LONG 1,109 / -1,048.9 / t -265.39 | identical | ✓ |
| squeeze_cross LONG 1,935 / -309.3 / t -6.81; hmacd_mtf LONG 229 / +1.9 / t -1.06 | identical | ✓ |
| Gate table (CONFLUENCE-EXPIRY LONG 3,985 / -683.6 / -12.59 …) | identical for all 8 listed rows | ✓ |

**Overall: FAIL** (single required criterion — naive t — unmet)

**Issues Found:**
1. **[Major] Naive (iid) t-statistic is missing** from the report. Cluster-robust t and cluster count are present and correct, but the spec for Fix 4 requires *both* naive and cluster-robust t. Headline naive t = **-11.66** vs cluster -10.75.
2. **[Minor] One closed row has NULL `mfe_pct`/`mae_pct`** — `first_exit_engine='hold'` (no-engine-fired branch at `shadow_trader.py:1291-1302` doesn't compute MFE/MAE). 1 of 20,384 rows.
3. **[Minor] ~9% of rows violate strict excursion inequalities** (LONG: 639 rows with MFE < gross, 2,753 with MAE > gross; SHORT: 1,263 / 3,833). Magnitudes are small (median ~0.12 pp, max 4.63 pp) — consistent with the rebuild's candle window / exit_ts differing slightly from the original closure run, **not** the wrong-entry-price bug (which would show 100%+ gaps). Worth a footnote; does not change any conclusion.
4. **[Trivial] Gate table (§6) omits EXEC-BLOCK** (n=9 SHORT + 7 LONG = 16 rows) — table sums to 11,579 vs stated 11,596 blocked. Unlabelled implicit n>=30 filter.
5. **[Info] DB is live** — total rows moved 22,024 → 22,064 during verification; report counts are a correct snapshot of generation time, not stale numbers.

**Recommendations:**
1. Add a `t_naive` column (or a "Naive t / Cluster t" pair) to §1-§6 tables and to the Key Insights — at minimum add to §1: `Naive t = -11.66, Cluster-robust t = -10.75 (2,703 clusters)` so readers can see the correction. This is the only blocking item.
2. In `shadow_trader.py` no-engine-fired branch, compute `hold_candles` MFE/MAE too (or explicitly document why 'hold' rows have no excursion data).
3. Add a methodology footnote: "MFE/MAE recomputed at rebuild time; ~9% of rows differ from original closure price by ≤0.1-4.6 pp due to candle-window alignment."
4. Label the n>=30 filter on §6 gate table, or add the EXEC-BLOCK row.
5. Re-run this verification after the shadow trader stops writing, so counts are frozen.

---

**Reproducibility:** every figure above came from live `sqlite3` queries against `brain/shadow_trades.db` + `data/candles.db` and direct reads of `shadow_trader.py`; the hold-vs-24h discrimination test is rerunnable from the methodology described in Fix 3's evidence.
