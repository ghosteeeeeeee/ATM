# Independent Verdict: Probability Matrix Spec (own-conclusions)

**Auditor:** independent auditor (fresh-eyes; no priming; every file read from scratch, every number below reproduced by my own queries/scripts — `/tmp/audit_pm.py` … `audit_pm4.py`)
**Date:** 2026-11-19
**Spec:** `brain/plans/probability-matrix-spec.md`
**Read completely:** the spec, `brain/context/probability-matrix-context.md`, `brain/summaries/beat-the-market-thorp-kassouf.md`, `scripts/cell_stats.py`, `scripts/correlation_engine.py`, `scripts/streak_analysis.py` (header/conventions), `signal_compactor.py` scoring sections (1197–1295, 2140–2310, 4320–4535, 6085–6130, 6520–6550), `decider_run.py:4740–4815`, both cited verdict files; targeted greps repo-wide; live queries against PostgreSQL `brain.trades` (6,578 rows), `data/signals_hermes_runtime.db` (12,401 signals), `brain/cell_stats.db`, `/var/www/hermes/data/hotset.json`.

---

## 1. Claim: "Repo grep: zero expected_value/EV trading code" (spec §1.1)

**Verdict: AGREE**
**Evidence:**
- `grep -rn "expected_value" --include=*.py` repo-wide → exactly 1 hit: `scripts/auditor_verify.py:43`, a comment `(name, expected_value) — expected False = killed` (test harness, unrelated). Zero EV/`expected_value` in any trading or decision path.
- No Brier/log-loss/reliability code exists anywhere (`grep -rin "brier|log_loss|reliability"` → only two incidental comments). The calibration study is genuinely unbuilt; `brain/transcript-mining/i-gave-jev-control-of-a-trading-bot.md:66` does propose "bucket signals by confidence and measure actual WR per bucket" — citation line number verified exact.
**Confidence: HIGH**
**Notes:** Two honesty caveats, not disagreements: (a) *expectancy* (mean PnL, which is an EV) is computed in analysis scripts (`jup_edge_analysis.py`, `q4_cap_wyckoff_backtest.py`, `linreg_fade_backtest.py`) and — more importantly — `cell_stats.py`'s `tradeable = n≥15 & wr≥0.60 & avg_pnl>0` (line 168/297) is an expectancy test consumed live in `_score_signal` (×1.2). So "no P(win)×payoff product anywhere" is exactly true; "decisions never touch expectancy" would be false. The spec's literal grep claim stands.

## 2. Claim: Confidence inversion — conf 90+ → 49.7% WR n=155; 90+ net −$5.88 vs 70–89 +$5.24, quoted from two verdict files; "final_confidence = product of ~25 hardcoded multipliers (`signal_compactor.py:2270-2294`)" (spec §1.2)

**Verdict: PARTIAL**
**Evidence:**
- **Quotes verified verbatim at the exact cited lines.** `2026-10-08-pump-chain-v6-verdict.md:20` = "Confidence not predictive: 90+ bucket ~155 trades ~50% WR | **AGREE** (n=155, 49.7% WR, −$0.03)" (and :64 shows `conf>=90: n=155 77W WR=49.7% PnL=-$0.03`). `2026-10-14-plan-v3-own-conclusions.md:58` = "90+: 442T **−$5.88**; 70–89: 178T **+$5.24** | ✅ real (confidence inversion confirmed)". Both files say what the spec says they say.
- **My own recompute from `trades` (last 30d, closed, pnl not null, n=648):** `trades.confidence` bands — 90+: n=277, 157W (56.7%), **−$3.00**; 70–89: n=68, 32W (47.1%), **−$0.68**; 50–69: n=112 +$0.03; <50: n=191 −$1.11. The **PnL inversion reproduces** (90+ is the worst band, same sign as the Oct-14 evidence). The **WR inversion does not** — 90+ WR (56.7%) is *higher* than 70–89 (47.1%) today.
- **Mechanism claim is false as written.** `signal_compactor.py:2270-2294` computes `final_score = score × max(∏26 multipliers, floor) × rr_mult` — that is `score`/`penalty_product`, not `final_confidence`. Live `hotset.json` sample: `{confidence: 85.36, final_confidence: 85.36, penalty_product: 0.0656}`. Every writer of `final_confidence` sets it to raw confidence (`signal_compactor.py:4498` `'final_confidence': conf` where `conf = row[3]` = signals.confidence; backfills at :4156/:6956/:7004 copy `confidence`; rescue path :6108 copies `l_conf`). The 26-factor product is applied *separately* at the decider gate: `exec = final_confidence × max(penalty_product, 0.5)` (`decider_run.py:4751-4778`). `final_confidence` is the raw invented 0–100 confidence; the multiplier product is `penalty_product`.
- **n=155 figure is pump-chain-only.** It comes from claim 5 of the pump-chain audit, sample = pump-chain trades 60d (n=260 total); in that sample conf<90 was 43.8% WR vs 90+ 49.7%, Fisher p=0.21 (n.s.) — i.e., on WR the 90+ bucket was *better*, and PnL was ≈0 (−$0.03), not negative. Citing it for "higher confidence currently predicts worse outcomes" overreads it; the plan-v3 −$5.88/+5.24 PnL evidence is the load-bearing citation and it holds.
**Confidence: HIGH** (on quotes, recompute, mechanism); **MEDIUM** on how much the mechanism error matters downstream.
**Notes:** The spec's §4 compares `final_confidence` "as a predictor" — that comparison still works (it's the raw confidence band that inverts on PnL), but the mechanism sentence and the line ref must be corrected, and the n=155 line should be labeled pump-chain-subset/non-significant or dropped in favor of plan-v3's 442/178-trade PnL numbers.

## 3. Claim: `cell_stats.py` = empirical-Bayes shrunk WR per (signal, direction, volatility_regime), K=10, n≥15 admission, live consumer in `_score_signal` (spec §2)

**Verdict: AGREE (with material notes)**
**Evidence:**
- Read `cell_stats.py` in full. Schema `(signal, direction, regime)` where regime = `COALESCE(NULLIF(volatility_regime,''), NULLIF(regime,''), 'UNKNOWN')` (line 80) — matches the spec's axes. `blend = (n·cell + K·prior)/(n+K)` at lines 151/157/277/284, **K=10** (line 42 default; `grep CELL_STATS scripts/hermes_constants.py` → no override, so defaults are live). Tiers: cell n≥15 / blend 10–15 / signal 5–10 / global <5 — n≥15 admission verified.
- Live consumer verified: `signal_compactor.py:2211-2268` — exact-key → source-key → normalized-key lookup, `tradeable → ×1.2`, `n≥15 & wr<0.40 → ×0.5`, fed into the multiplier product at :2276.
- `correlation_engine.py:160-164` `_bayesian_confidence = (10×0.50 + n·wr)/(10+n)` — verified (`PRIOR_WEIGHT=10`, `PRIOR_WIN_RATE=0.50` at :48-49); spec's "reuse prior convention (0.50, K=10)" matches.
- `brain/cell_stats.db` exists (372 KB, computed 2026-11-19T00:20, window 90d): tables `cells` (schema matches spec), `cells_st`, `meta`. 518 cells, 49 admitted (n≥15), 9 tradeable, global WR 0.4977/2,823. **No admitted cell currently has wr 0 or 1 (range 0.25–0.80)**; 29/49 admitted cells have negative avg PnL.
**Confidence: HIGH**
**Notes:** (a) **At the admission tier there is NO shrinkage** — for n≥15, `wr_b = wr_raw` (lines 272-274); the K=10 blend only applies *below* n=15. The spec's "p_win = cell_stats shrunk WR(c) # existing, K=10" is misleading exactly where the matrix operates: p_win will be raw WR. This also creates the log-loss hazard (raw WR can be 0.0000 or 1.0000 at n≥15 in future samples → infinite log-loss; needs clipping). (b) The live consumer reads `wr_raw` and the `tradeable` flag, not `wr_blended` — "already live" is true, "shrunk WR is live" is not. (c) The consumer needs a 3-stage key match because dash-form (`pump-chain+`) and underscore-form (`pump_chain`) keys coexist with different stats (brain_auditor fix, :2221-2252) — "plugs in with zero new fitting" glosses over this known landmine.

## 4. Claim: `_signal_metadata` has 67 distinct keys over last 60 trades (context survey)

**Verdict: AGREE**
**Evidence:** My own PG query: last 60 closed trades with non-empty `_signal_metadata` → 60 rows, **exactly 67 distinct keys**. Reproduced exactly.
**Confidence: HIGH**
**Notes:** Spec calls it a "67-key *detection-time* feature vector" — not all keys are detection-time: `gap_at_entry`, `staleness_minutes`, `rsi_exec`, `coin_regime` are injected at execution (`decider_run.py:6258-6289`), per the survey's own writer list. Cosmetic, but any leakage discipline in P0 should know `final_confidence` (gate-time) and `rsi_exec` are not detection-time. Also: `_signal_metadata.final_confidence` exists in only **1,163 / 2,799 (41.5%)** of 90d closed trades (injected only since ~Oct 25) — relevant to claim 6.

## 5. Claim: Landmines — `signals.effective_confidence` dead (0/12,400 rows, no writer); `SIGNAL_QUALITY_*` 0 code refs (spec §8)

**Verdict: AGREE**
**Evidence:**
- `signals_hermes_runtime.db`: 12,401 rows, `effective_confidence IS NOT NULL` → **0** (spec said 12,400 — off by one, trivial). Repo grep: only 3 read sites, all `signal_schema.py` (:3616, :3617, :3649) + the false comment at :3674; **zero writers** anywhere in `scripts/`. The survey's "comment is false" assessment holds.
- `SIGNAL_QUALITY_*`: only definitions at `hermes_constants.py:641-644` (+ `hermes_constants.py.bak`, README prose). Zero code references — verified by my own grep across `scripts/ config/ web/`.
- Bonus verification: `SCORE_WEIGHTS` — defined `continuum_constants.py:79`, imported `continuum_engine.py:40`, **no other occurrence** → imported-but-unused confirmed.
**Confidence: HIGH**
**Notes:** Both landmines are real and correctly quarantined to the "separate queue" in §8.

## 6. Claim: Design soundness — §3.2 formulas, §4 P0 bar, §6 P1 bar, fatal flaws, duplication (my own judgment)

**Verdict: PARTIAL**
**Evidence:**

**Formulas (§3.2):**
- `ev_usdt = p·mean_win + (1−p)·mean_loss` is mathematically correct — but with p = raw WR over the same window it is **identical to `cell_stats.avg_pnl_raw`**. I verified the identity on 8 admitted cells against my own PG recompute: diff ≤ 1e-4 (e.g. `pump-chain+ LONG EXTREME n=135 wr=0.437 avg_pnl=+0.0248 ev=+0.0248`). The "NEW EV layer" largely re-derives a column that already exists in `cell_stats.db`. Not fatal — but the reuse list misses it, and it means P2's `ev_usdt < 0` block ≈ blocking cells with negative average PnL, which `tradeable`/losing-cell logic already half-encodes.
- `ev_per_risk = ev / max(|mean_loss|, ε)`: when `avg_loss ≈ 0` (breakeven-heavy cells; `pnl_usdt == 0` counts as a loss in cell_stats and is ~4% of sample per `streak_analysis`), the ε floor makes the ratio **unbounded and noise-amplified** (tiny denominator → huge ratio for tiny ev). ε value unspecified (deferred to `hermes_constants.py` — acceptable) but the neighbor test in §7.3 must include the ε floor explicitly.
- `p_win ∈ {0,1}`: handled *implicitly* by the ≥1-win/≥1-loss admission, and no admitted cell is currently at an extreme — but raw WR at n=15 *can* be 0 or 1 in future data, and §4's log-loss then returns ∞. **Clipping (e.g. p ∈ [0.01, 0.99]) is not specified anywhere.** Worse edge case: an **all-loss cell (n≥15, 0 wins)** fails "≥1 win" → `UNCALIBRATED` → P2 explicitly excludes UNCALIBRATED from blocking → **the gate fails open on the worst possible cells**, even though `ev = avg_loss` is perfectly computable there (p=0 makes the `p·avg_win` term vanish). This is a real defect, fail-open in direction.
- **Brier is defined two incompatible ways**: §3.2 says `brier = mean_over_buckets((p_win − observed_WR)²)` (a bucket-level reliability statistic, buckets weighted equally); §4 item 3 says "Brier score and log-loss for p_win vs final_confidence vs baseline 0.5" (which requires the standard **trade-level** mean of `(p−y)²`). These are different metrics with different values; the spec must pick the trade-level definition for model comparison and label the bucketed one as the reliability diagram.

**§4 P0 bar:**
- Structure is good: pre-registered, falsifiable ("or the spec dies here"), seeded bootstrap, OOS limb, reproduce command. **But it is not executable as written:**
  - **Measured coverage (my queries):** on the spec's own split — train = older 60d of the 90d window (1,425 trades, 315 cells, **25 cells n≥15, covering 45.7% of train trades**), test = last 30d (648 trades) — only **46/648 = 7.1%** of test trades fall in a train-admitted cell. Top-2 deciles of 46 trades ≈ 9 trades; `p<0.05` in limb (a) is unreachable. Under a clean split, **P0 dies for a structural reason, not an evidential one.**
  - In-window coverage is much better: most-recent-60d window → 24 admitted cells covering **58.8%** (808/1,374) — the spec's §9 "<50% coverage" worry does **not** materialize in-window; 90d window → 55.1%.
  - The alternative (use the live `cell_stats` 90d store as §3.1 says — "p_win from cell_stats, never refit") covers **457/648 = 70.5%** of test trades, but that store's 90d window *includes the test period* → **the calibration is partly in-sample (look-ahead leakage)**; observed test WR is inside p_win. §3.1 ("never refit") and §4 ("train 60d / test 30d OOS") are in **direct contradiction** and the spec never resolves it.
  - **Root cause the spec misses: signal churn.** `jup_yolo_mirrored` = 0 train trades → **168 test trades (26% of test; first trade 2026-10-30)**; `volume-buildup-` 0→61; `ai-trader-pending` 0→48; `atr-trend-` 0→37. ~46% of recent test trades are in signals absent from the train window. §9 discusses thin cells but not a rotating signal inventory. Relatedly, cell_stats' own **hierarchical backoff (blend/signal/global tiers) is the designed cure for exactly this** — the spec converts it to a hard n≥15 cut + UNCALIBRATED and rejects backoff without argument.
  - **Confidence field not pinned for Brier**: `_signal_metadata.final_confidence` exists on only 41.5% of 90d trades and differs semantically from `trades.confidence` (post-reduction; `decider_run.py:4796-4807` documents 58/58 drift). The survey itself warned "pin `final_confidence` vs `trades.confidence` first" — §4 doesn't.
  - **Brier comparison is apples-to-oranges**: p_win is a fitted 0–1 quantity; "final_confidence (monotonic-transform-free)" never states how 0–100 maps to a probability (conf/100?), and Brier conflates calibration with discrimination — the bar is biased *toward* p_win passing. No discrimination metric (decile monotonicity / AUC) is required for confidence. Also missing: `Brier(p_win) < Brier(0.5 baseline)` — both predictors could beat each other and lose to baseline and still pass.
  - Significance methods unspecified (two-proportion z? Fisher?) and **naive over trades ignores pseudo-replication** — the survey itself mandates `brain/analysis/cluster_t.py` "for any significance claim" (expiry_shadow's 2–3× event duplication); the spec's reuse list omits it.

**§6 P1 pre-registered bar:**
- Limb 1 (`n ≥ 100 EV-evaluated decisions`): counts *signals evaluated*, including signals that never execute. Satisfiable by evaluation volume with zero outcome evidence; outcomes exist only for executed trades (limb 2). Needs "n ≥ 100 **executed** EV-evaluated decisions".
- Limb 2 (`EV-gated subset net PnL ≥ actual by ≥$0.50, no >20% trade-count reduction`): **three loopholes.** (i) *Counterfactual asymmetry*: for trades the gate would *block*, "what actually happened" exists (they were executed — that's the measurable cohort); for signals the gate would *admit* that the live path blocked, no outcome exists (never traded). "admitted/blocked differently" is ill-defined and admits cherry-picking the observable direction. Honest metric: `actual − PnL(gate-blocked executed cohort) ≥ actual + $0.50`, i.e. blocked cohort ≤ −$0.50 — state it. (ii) *No significance requirement*: $0.50 over 14d is far inside this system's noise (current 30d bands swing multiple dollars; plan-v3 weekly swings ±$2+), yet limb 2 has no CI — violating the spec's own §2 THE PATTERN "p-values everywhere" discipline. (iii) *Denominator gaming*: ">20% trade-count reduction" — evaluated subset or all trades? With UNCALIBRATED (~29–41% of trades) outside the gate, the same blocking rate passes or fails depending on denominator.
- Limb 3 (reliability sign on shadow window) and limb 4 (CEO approval, no self-flip) are sound. Registration plumbing verified real: `data/shadow_disposition.json`, `data/checkpoint_registry.json` (read by `checkpoint_watch.py`), `config/hermes-kill-line-shadow.{service,timer}` + `hermes-freq-deviation-shadow.*` all exist — the D5 mirror is available.
- **Observational bias is correctly identified in §9** and correctly routed through shadow-before-enforce. Good.

**Duplication the reuse list overlooks:**
- `cell_stats.cells` already stores per-cell **`mfe_p25/50/75`, `mae_p25/50`** — §5's "report MFE/MAE quantiles per cell" is a SELECT away; §5 instead says "from `_signal_metadata` where present", but `trades.mfe_pct/mae_pct` coverage is **2,782/2,799 (99.4%)** over 90d — `_signal_metadata` is the wrong source. `avg_pnl_raw/avg_pnl_blended` (= expectancy) already stored (see above).
- `brain/analysis/cluster_t.py` — survey marks it *required* for significance claims; absent from §2/§7 reuse.
- `scripts/exit_optimizer_shadow.py` — SL/TP calibrated from MAE/MFE quantiles; adjacent to §5's band/payoff layer (should be acknowledged as prior art, not duplicated).
- `winrate-calculator` / `trade-stats` / `signal-combo-analyzer` skills (survey §8) — not cited.
- Otherwise the reuse list is accurate: no EV code, no second WR store, no RF training (ml_classifier inert), `correlation_engine` prior verified.

**No fatal architectural flaw:** read-only P0, cell_stats as the single WR source, shadow → CEO-gated enforce, flag-default-False, honest death conditions — the skeleton is sound and the landmines are correctly excluded. The flaws are all in measurement definitions and bar wording, which is exactly what pre-build review is for.
**Confidence: HIGH** on all measured numbers (own queries, reproducible); **MEDIUM** on the design-judgment items.

---

## OVERALL

**Verdict: PROCEED-WITH-CHANGES**

The spec's direction is sound (reuse `cell_stats` as the P(win) layer, EV as a thin read-only layer, phased shadow→enforce with pre-registered bars and CEO gate), its evidence citations are real (both verdict quotes verified verbatim at the exact line numbers; landmines and 67-key claims reproduce exactly), and P0 is genuinely risk-free (SELECT-only). But **P0 as written cannot pass honestly** (clean split → 7.1% OOS coverage → bar (a) unreachable; live-store alternative → in-sample leakage), §1.2's mechanism sentence is factually wrong, and the P1 enforce bar has three concrete loopholes. All fixable by wording/protocol changes before any code is built.

### Required changes (concrete)

1. **Resolve the p_win source contradiction (§3.1 vs §4) before build.** State exactly which window computes p_win for calibration. Measured options: (a) train-window-only cells → 7.1% test coverage → P0 dies structurally; (b) live 90d `cell_stats` store → 70.5% coverage but in-sample leakage (store includes the test window) → must be labeled in-sample with OOS only against a frozen snapshot; (c) use cell_stats' own hierarchical backoff (blend/signal/global tiers, `wr_blended`) instead of a hard n≥15 cut → coverage near 100% with tier-reported trust, and revisit §9's "loosening n = overfit trap" (the backoff *is* the empirical-Bayes answer). Pick one; state the expected coverage number from the measurements above.
2. **Define the coverage metric explicitly**: fraction of *test* trades whose cell is admitted *from train data*; keep the <50% LOW-COVERAGE rule against that number (it currently reads 7.1% clean / 45.7% train-window / 58.8% in-window).
3. **Fix §1.2**: `final_confidence` = raw invented confidence (verified in live `hotset.json`: conf = final_confidence = 85.36, penalty_product = 0.066); the 26-factor product at `signal_compactor.py:2270-2294` is `score`/`penalty_product`, applied at `decider_run.py:4751+`. Keep plan-v3's −$5.88/+5.24 as the inversion evidence; label n=155/49.7% as pump-chain-subset (Fisher p=0.21, WR actually higher for 90+ there) or drop it. Note my recompute: 30d PnL inversion reproduces (90+ −$3.00 vs 70–89 −$0.68) but WR does not (56.7% vs 47.1%).
4. **Pin the confidence field for §4's Brier comparison**: `_signal_metadata.final_confidence` exists on only 41.5% of 90d trades and ≠ `trades.confidence` (post-reduction). Specify field, fallback, and the exact sample it runs on.
5. **Fix §3.2**: (i) Brier = mean over **trades** of `(p−y)²`; the bucketed version is the reliability diagram, report separately; (ii) clip p to [0.01, 0.99] before log-loss; (iii) 0-win cells (n≥15, all losses) must NOT be UNCALIBRATED — ev = avg_loss is computable (p=0), otherwise P2 fails open on the worst cells; (iv) note `ev_usdt ≡ cell_stats.avg_pnl_raw` for same-window raw WR — either read the stored column (reuse) or document the window/weighting difference; (v) state ε and neighbor-test the ε floor in `ev_per_risk`.
6. **Harden §4's bar**: add `Brier(p_win) < Brier(baseline 0.5)`; specify the confidence→[0,1] mapping (conf/100) and require the *same* discrimination metric (decile monotonicity or AUC) for both predictors so the comparison isn't fitted-vs-raw; specify the test for limb (a) and make it cluster-robust (`brain/analysis/cluster_t.py` per the survey's own pseudo-replication mandate, or block-bootstrap by day/signal).
7. **Rewrite §6 limb 1–2**: (i) n ≥ 100 **executed** EV-evaluated decisions; (ii) define the counterfactual as `actual PnL − PnL(executed cohort the gate would block) ≥ +$0.50` (admit-side counterfactual is unobservable — state it, don't leave "admitted/blocked differently" open); (iii) add a significance requirement to limb 2 (block-bootstrap CI on the PnL delta excluding 0) — $0.50 over 14d is inside noise and violates the spec's own p-values discipline; (iv) pin the trade-count denominator to **all closed trades in the window** (not the evaluated subset, which UNCALIBRATED trades would game).
8. **Extend §9 risks with signal churn**: ~46% of recent test trades are in signals absent from the train window (`jup_yolo_mirrored` 0→168, first trade 2026-10-30; `volume-buildup-` 0→61; `ai-trader-pending` 0→48; `atr-trend-` 0→37) — cell-n≥15 admission structurally cannot cover rotating inventory; tie the mitigation to change 1's tier choice.
9. **Extend the reuse list**: `cell_stats` per-cell `mfe_p*`/`mae_p*` quantiles + `avg_pnl_*` for §5 (don't read `_signal_metadata` "where present" — `trades.mfe_pct/mae_pct` is 99.4% covered), `brain/analysis/cluster_t.py`, `exit_optimizer_shadow.py` as adjacent prior art, and the `winrate-calculator`/`trade-stats` skills.

**Not required:** no architectural rework, no new phases, no additional hard gates — the shadow→CEO-enforce skeleton, the "bounds before probabilities" layering, and the death conditions are all sound as written.
