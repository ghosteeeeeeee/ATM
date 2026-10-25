# Independent Verdict — `reports/20261025-shadow-fresh-analysis.md`

**Auditor:** independent fresh-read (no priming from prior analyses)
**Date:** 2026-10-25
**Data source:** `/root/.hermes/brain/shadow_trades.db` (queried directly; DB is LIVE and grew during audit, 20,908 → 20,940 rows)
**Cross-check source:** `/root/.hermes/data/candles.db` (for MFE/MAE), `git log/show` on `scripts/shadow_trader.py`
**Tools:** Python 3, sqlite3, numpy, scipy.stats — every number below was produced by running code, not copied from the report.

---

## Headline

**The report's arithmetic is largely reproducible — but its four most load-bearing conclusions do not survive audit.**

| # | Claim | Verdict |
|---|-------|---------|
| 1 | System losing -718.2% net, t=-11.15 | **AGREE** |
| 2 | Only 1 net-positive significant signal (squeeze_cross SHORT t=2.01) | **PARTIAL** |
| 3 | PM Trail is the only profitable exit engine | **PARTIAL** |
| 4 | Hard Max biggest loser (t=-523 / -557) | **PARTIAL** |
| 5 | ALL gates are helping | **PARTIAL** |
| 6 | RR ratio 0.52 (win +0.417 / loss -0.799) | **AGREE** |
| 7 | Breakeven WR 65.8%, current 58.3% | **AGREE** |
| 8 | 5 tokens significantly positive (MNT/SUPER/IMX/ALGO/LTC) | **AGREE** (numbers) / weak inference |
| 9 | 5 tokens significantly negative (CHIP/NXPC/ICP/ALT/LDO) | **PARTIAL** |
| 10 | squeeze_cross best SHORT / worst LONG | **PARTIAL** |

**Methodology items requested:** t-formula (correct form, wrong inference), survivorship/selection-on-outcome (multiple found), MFE/MAE fix (code correct, data NOT fixed), gate-passed vs all (right primary metric, undisclosed denominator, era-confounded).

---

=== INDEPENDENT VERDICT ===

## Claim 1: System losing -718.2% net (gate-passed), t=-11.15

**Verdict: AGREE**

Evidence (my own query, `WHERE closed=1 AND gate_blocked=0 AND net_pnl_pct IS NOT NULL`):

| Metric | Report | Mine (numpy + scipy `ttest_1samp`) |
|--------|--------|-----------------------------------|
| n | 8,035 | **8,035** ✓ |
| Sum net | -718.2% | **-718.23%** ✓ |
| Mean | -0.089% | **-0.08939%** ✓ |
| SD | 0.716% | **0.71591%** ✓ |
| t | -11.15 | **-11.192** |
| WR | 58.3% | **58.34%** ✓ |

- `net_pnl_pct = gross_pnl_pct - fee_pct - slippage_pct` verified on **all 8,035 rows: 0 mismatches, max deviation 0**. Fee/slippage are constant (0.04 / 0.10) on all 19,312 rows.
- t difference (-11.15 vs -11.19) is explained by rounding: using the report's own displayed values, `-0.089 / (0.716/√8035) = -11.14`. Not an error of substance.
- **Denominator problem:** report states "Total signals 20,878" but its own gate split is 11,277 + 8,035 = **19,312**. Actual DB: 20,940 rows (grew during audit), 20,271 closed, **19,312 with net PnL**. So "20,878" reconciles with nothing — it is an internally inconsistent header number.
- **Period problem:** report says "Oct 7-25, 18 days". The gate-passed sample is **entirely 2026-10-20 → 2026-10-25 (6 days)**. Every trade created before 2026-10-20 has `gate_blocked=1` (6,751 rows, 100%). The report's own §7 daily table only lists Oct 20–25, contradicting its own header.

Confidence: **HIGH**

---

## Claim 2: Only 1 signal is net-positive AND significant — squeeze_cross SHORT (t=2.01)

**Verdict: PARTIAL**

Evidence — the raw numbers reproduce exactly:

- squeeze_cross SHORT: n=2,953, WR **70.8%**, sum **+73.9%**, avg **+0.02503%**, t=**2.014** ✓ (report: 2,953 / 70.8% / +73.9% / +0.025 / 2.01)
- Among signals with n≥30 it **is** the only positive one. Next best is pump-chain-v6 SHORT (n=32, t=0.15). Confirmed.
- All 9 "significantly negative" signals reproduce within ±0.05 t (squeeze_cross LONG -11.35 vs -11.34, pump-chain SHORT -6.37 vs -6.38, doji_bottom_long -7.61 vs -7.64, pump-chain LONG -7.73 vs -7.77, volume_buildup_short -3.82 vs -3.83, bollinger_squeeze_short -3.61 vs -3.62, support_resistance LONG -3.27 vs -3.31, ichimoku_long -3.90 vs -3.91, pump-chain-v6 LONG -3.71 vs -3.74).

**Why only PARTIAL:**

1. **The significance does not survive clustering.** 2,953 trades come from only **381 distinct `created_at` timestamps** (avg 7.7 trades/timestamp; up to 55 trades share one timestamp system-wide). Signals fire in bursts and share market conditions → the i.i.d. assumption behind `t = mean/(s/√n)` is violated. Cluster-robust t on `created_at`:

   | | naive t | cluster t |
   |---|---|---|
   | squeeze_cross SHORT | +2.01 | **+0.76 (NOT significant)** |
   | squeeze_cross LONG | -11.35 | -5.50 |
   | ALL gate-passed | -11.19 | -5.68 |
   | SHORT direction | -2.99 | **-1.27 (NOT significant)** |
   | LONG direction | -13.58 | -8.37 |

2. **The significance does not survive multiple comparisons.** 47 signal×direction groups were tested. Bonferroni critical |t| = **3.28**; expected false positives at |t|>1.96 = **2.35**. squeeze_cross SHORT (2.01) fails.

3. **95% CI = [0.0007%, 0.049%]** — the entire claimed edge is a rounding-width band above zero.

4. "Only 1" requires the n≥30 filter: without it, 3 signals have t>1.96 (two of them n=2, e.g. breakout_pullback_short t=8.49 on 2 trades).

Confidence: **HIGH** (numbers reproduce exactly; the significance label does not hold)

---

## Claim 3: PM Trail is the only profitable exit engine (t=66.83 SHORT / 51.72 LONG)

**Verdict: PARTIAL**

Evidence — the sums reproduce; the "only" is false:

| Engine | Direction | n | WR% | Net sum | Avg | t (mine) | t (report) |
|--------|-----------|---|-----|---------|-----|----------|------------|
| pm_trail | SHORT | 3,034 | 100.0 | +1,196.96 | +0.3945 | **66.62** | 66.83 |
| pm_trail | LONG | 1,278 | 100.0 | +467.58 | +0.3659 | **51.88** | 51.72 |
| **hold** | **LONG** | **223** | **40.8** | **+79.14** | **+0.3549** | **+3.51** | 3.52 |
| **pump_exit** | **SHORT** | **84** | **63.1** | **+36.23** | **+0.4313** | **+5.61** | 5.64 |

- **`hold` LONG (+79.1%, t=3.51) and `pump_exit` SHORT (+36.2%, t=5.61) are both net-positive and significant.** The report's own §4 table lists them under "Profitable Engines" — then the TLDR and Key Insight #3 say PM Trail is "the ONLY profitable exit engine". **The report contradicts itself.**
- The statement is only true if narrowed to *"the only engine profitable in **both** directions"* — which is not what is written, and not what Recommendation #2 ("Route more trades through PM Trail") justifies.
- **Selection-on-outcome (definitional, not causal):** pm_trail WR = **100.0%** and hard_max WR = **0.0%** by construction — a trailing stop only locks in profit, a max-loss cut only fires at max loss. t-stats of +66 and -529 here measure the *definition of the exit*, not its superiority. You cannot route trades "to PM Trail" — the engine fires when the trade is already in profit. This makes Recommendation #2 structurally meaningless as stated.
- Exit-engine t-stats do **not** reproduce: report -523.29/-557.47 for hard_max, mine -529.25/**-587.58**. n and mean match exactly, so their SD differs (see Claim 4).

Confidence: **HIGH**

---

## Claim 4: Hard Max is the biggest loser (t=-523 SHORT, t=-557 LONG)

**Verdict: PARTIAL**

Evidence — biggest loser: **confirmed, by a wide margin**:

| Engine | Direction | n | WR% | Net sum | Avg | t (numpy/scipy) | t (report) |
|--------|-----------|---|-----|---------|-----|----------|------------|
| hard_max | SHORT | 1,237 | 0.0 | **-1,164.32** | -0.9412 | **-529.25** | -523.29 |
| hard_max | LONG | 1,044 | 0.0 | **-986.69** | -0.9451 | **-587.58** | **-557.47** |

- Next-largest loser is rr_engine SHORT at -150.2%. So "biggest loser" is correct — hard_max is ~7.7x worse than the next engine.
- **The t-statistics are not reproducible.** Two independent implementations (numpy `std(ddof=1)` and `scipy.stats.ttest_1samp`) both give **-529.25 / -587.58**. n (1,237 / 1,044), mean (-0.9412 / -0.9451) and sum all match the report exactly — so only the SD differs. The report's LONG value is **5.4% off**. Cross-checked alternatives and none match: gross-based t = -450.5/-500.5; round(net,2) = -519.4/-591.3; population SD = -529.0/-587.3.
- Other engine t's reproduce to ±0.06 (rr_engine -17.03 exact, atr -3.05/-3.52 vs -3.06/-3.53, hold 3.51 vs 3.52, pump_exit 5.61 vs 5.64) — so hard_max specifically is anomalous.
- Same definitional caveat as Claim 3: 0% WR is the *definition* of a max-loss cut. Cluster-robust t = -502.7 / -526.6 — still enormous, but the metric is nearly degenerate (SD ≈ 0.05), which is why t is astronomically large.

Confidence: **HIGH** (conclusion correct; the stated t's are wrong)

---

## Claim 5: ALL gates are HELPING (blocking losing trades)

**Verdict: PARTIAL**

Evidence — aggregate supports it, "ALL" does not:

My full gate table (all 11 gate×direction groups; report shows only 8):

| Gate | Dir | n | WR% | Net sum | Avg | t (mine) | t (report) | Report label |
|------|-----|---|-----|---------|-----|----------|------------|--------------|
| CONFLUENCE-EXPIRY | LONG | 3,939 | 43.0 | -674.31 | -0.1712 | -13.47 | -13.46 | HELPING |
| CONFLUENCE-EXPIRY | SHORT | 6,142 | 50.0 | -494.64 | -0.0805 | -7.51 | -7.56 | HELPING |
| CTX-GATE | LONG | 584 | 48.5 | -69.92 | -0.1197 | -4.22 | -4.23 | HELPING |
| BTC-CRASH | LONG | 86 | 31.4 | -27.39 | -0.3185 | -6.89 | -6.93 | NEUTRAL |
| UNKNOWN | SHORT | 213 | 44.6 | -22.04 | -0.1035 | -2.47 | -2.46 | NEUTRAL |
| UNKNOWN | LONG | 119 | 37.8 | -17.00 | -0.1428 | -2.60 | -2.62 | NEUTRAL |
| BTC-CRASH | SHORT | 30 | 13.3 | -14.29 | -0.4763 | -5.65 | -5.74 | NEUTRAL |
| **CTX-GATE** | **SHORT** | **148** | **53.4** | **+14.79** | **+0.0999** | **+1.05** | **+1.05** | **NEUTRAL** |
| EXEC-BLOCK | LONG | 7 | 14.3 | -3.10 | -0.4426 | -3.22 | — | **OMITTED** |
| EXEC-BLOCK | SHORT | 8 | 0.0 | -4.51 | -0.5640 | **-25.67** | — | **OMITTED** |
| SKIP | LONG | 1 | 0.0 | -0.02 | -0.0161 | n/a | — | **OMITTED** |

**Problems:**

1. **CTX-GATE SHORT blocked trades were net POSITIVE (+14.79%).** Blocking them *cost* 14.79%. The report's own table labels it "NEUTRAL" — so the headline "ALL gates are HELPING" is contradicted by the report's own table (3 HELPING / 5 NEUTRAL / 1 positive-and-blocked).
2. **Three gate rows are missing** from the report's table (EXEC-BLOCK L/S, SKIP L). Minor n, but EXEC-BLOCK SHORT has t=-25.67 and 0% WR — it belongs in a table that claims completeness.
3. **Era confounding (serious):** **6,751 of 11,277 blocked rows (59.9%)** are pre-2026-10-20 backfilled signals, all `decision=EXPIRED`, all `gate_name=CONFLUENCE-EXPIRY`. Meanwhile **100% of pre-Oct-20 trades are blocked and 0% pass**. The "blocked" and "passed" cohorts therefore differ by *era and signal age*, not only by gate decision — so a naive pass/block comparison mixes a gate effect with a period effect.
4. Aggregate is genuinely supportive: blocked cohort n=11,277, sum **-1,312.43%**, avg -0.1164%, t=-15.16 (cluster t=-11.89), vs passed avg -0.0894%. Gates do select the less-bad trades — but both cohorts lose.

Confidence: **HIGH**

---

## Claim 6: RR ratio 0.52 (avg win +0.417% vs avg loss -0.799%)

**Verdict: AGREE**

Evidence: 4,688 wins / 3,347 losses / **0 zero-PnL trades**; WR **58.34%**; avg win **+0.4169%**; avg loss **-0.7985%**; RR = 0.4169/0.7985 = **0.5221**. Direction splits also reproduce (LONG 1,434/1,518 → 48.6%, +0.440/-0.795, RR 0.55; SHORT 3,254/1,829 → 64.0%, +0.407/-0.802, RR 0.51).

Confidence: **HIGH**

---

## Claim 7: Breakeven WR needed 65.8%, current 58.3%

**Verdict: AGREE**

Evidence: BE = `avg_loss / (avg_win + avg_loss)` = 0.7985 / 1.2154 = **65.70%**. Equivalently `1/(1+RR)` = 1/1.5221 = **65.70%**. Report's 65.8% comes from the rounded RR (`1/1.52 = 65.79%`) — a 0.1pp rounding artifact, immaterial. Current WR **58.34%** ✓. Gap: 7.36pp (report says 7.5pp, itself derived from the rounded figures).

Confidence: **HIGH**

---

## Claim 8: 5 tokens significantly positive — MNT, SUPER, IMX, ALGO, LTC (all SHORT)

**Verdict: AGREE** (for the stated list) **— but inference is weak**

Evidence: I tested **all 166 token×direction groups** (143 with n≥30). Exactly **5** have t > 1.96, and they are precisely the five named, all SHORT:

| Token | n | WR% | Net sum | t (mine) | t (report) |
|-------|---|-----|---------|----------|------------|
| MNT | 58 | 84.5 | +17.28 | **3.56** | 3.59 |
| IMX | 77 | 81.8 | +11.08 | **2.52** | 2.54 |
| SUPER | 59 | 79.7 | +11.16 | **2.33** | 2.34 |
| LTC | 74 | 78.4 | +9.45 | **2.25** | 2.27 |
| ALGO | 68 | 76.5 | +9.56 | **2.04** | 2.06 |

- The list is **complete and correct** for positives (no other token-direction is positive at t>1.96, at any n). Report's t's run 0.02–0.03 high — negligible.
- Each token has n = distinct timestamps, so **clustering does not change these t's** (verified: cluster t = naive t for all 5).

**Caveat (why inference is weak):** 166 simultaneous tests → expected **8.3 false positives** at |t|>1.96; Bonferroni critical |t| = **3.62**. **None of the five survives** (MNT at 3.56 is closest). These are candidate observations, not established edges.

Confidence: **HIGH**

---

## Claim 9: 5 tokens significantly negative — CHIP, NXPC, ICP, ALT, LDO

**Verdict: PARTIAL**

Evidence — the five named tokens are genuine (reproduced within 0.1):

| Token | Dir | n | WR% | Net sum | t (mine) | t (report) |
|-------|-----|---|-----|---------|----------|------------|
| CHIP | SHORT | 111 | 45.9 | -28.97 | -3.72 | -3.74 |
| NXPC | SHORT | 102 | 52.9 | -24.42 | -3.34 | -3.35 |
| ICP | LONG | 37 | 24.3 | -23.80 | -7.69 | -7.79 |
| ALT | LONG | 56 | 26.8 | -23.22 | -3.37 | -3.41 |
| LDO | LONG | 44 | 38.6 | -18.99 | -5.12 | -5.18 |

**But "5 tokens are significantly negative" is false — there are 43** token×direction groups with t < -1.96 (n≥30). The report cherry-picked five and omitted materially worse ones:

| Omitted | Dir | n | t |
|---------|-----|---|---|
| **TRX** | LONG | 51 | **-6.46** |
| **IO** | LONG | 31 | -5.00 |
| **CFX** | LONG | 33 | -4.74 |
| **NEO** | LONG | 42 | -4.60 |
| **IMX** | LONG | 35 | -4.52 |
| WLFI | LONG | 82 | -4.06 |
| APT / DOT / STX / AVAX / HYPE ... | LONG | 39–54 | -3.7 to -3.9 |

Note the selection is not "top 5 by |t|" either (TRX LONG at -6.46 is second-worst and is missing) — the basis for choosing these five is unstated. This is **selection-on-outcome**: the same review process that reports only 5 positives (which happen to be all the positives) reports only 5 of 43 negatives. It also hides the asymmetry — the 43 negative token-directions total **-601.41%** versus **+58.54%** for the 5 positives, a **10.3x** larger downside.

Confidence: **HIGH**

---

## Claim 10: squeeze_cross is best SHORT signal but worst LONG signal

**Verdict: PARTIAL**

Evidence:

**"Best SHORT" — holds, but by a rounding-width margin.**
- squeeze_cross SHORT is the only n≥30 SHORT signal with a positive total (**+73.9%**) and positive average (**+0.025%**); next is pump-chain-v6 SHORT at +0.021% (n=32).
- It is *not* the highest-average SHORT signal overall — small-n signals beat it (e.g. breakout_pullback_short avg +0.54% on n=2).
- Its "best" status rests on t=2.014 → **cluster t=+0.76**, i.e. it is not demonstrably better than zero once burst correlation is handled.

**"Worst LONG" — depends entirely on the metric.**

| Metric | squeeze_cross LONG | Worst LONG | squeeze_cross rank |
|--------|--------------------|------------|--------------------|
| Total net | **-314.83%** | squeeze_cross (-314.83) | **1st (worst)** |
| t-stat | **-11.35** | squeeze_cross (-11.35) | **1st (worst)** |
| Avg per trade | -0.176% | pump-chain **-0.469%** | **7th** |

By average loss per trade it ranks behind pump-chain, doji_bottom_long, pump-chain-v6, bollinger_squeeze_long, support_resistance, and pump-chain... i.e. it is a *high-volume* loser, not the worst-per-trade one. The report cites the total and the t-stat without disclosing that per-trade it is middling.

Confidence: **HIGH**

---

# METHODOLOGY AUDIT

## 4. Is the t-statistic formula correct?

**Formula: AGREE. Inference: DISAGREE.**

- The form used is the standard one-sample t: `t = x̄ / (s/√n)`, `s = sample SD (ddof=1)`, tested against 0. **This is the correct formula** for the stated question, and `scipy.stats.ttest_1samp` reproduces it exactly.
- It reproduces the report's direction, signal, gate and token t-stats to **±0.06** — strong evidence the report used the right formula.
- **Exceptions:** hard_max and pm_trail t's do not reproduce (see Claims 3/4). hard_max LONG is 5.4% off despite n, mean and sum matching exactly — their SD must have been computed differently, and I could not reconstruct it from any variant I tested.
- **Three real inference failures:**
  1. **No multiple-comparison correction.** 47 signal tests, 166 token tests, 16 engine tests, 11 gate tests. Bonferroni criticals: **3.28 / 3.62 / 2.96 / 2.84**. The report's stated threshold |t|>2.0 flags expected false positives: ~2.4 of the signal findings and ~8.3 of the token findings could be pure noise.
  2. **Independence is violated.** 8,035 trades arise from only **2,528 distinct signal timestamps across 110 distinct hours**; up to 55 trades share one timestamp. Cluster-robust t (on `created_at`) roughly halves the headline statistics and **kills two headline findings**: squeeze_cross SHORT 2.01 → **0.76**, SHORT direction -2.99 → **-1.27**.
  3. **|t| > 2.0 as the cutoff** is slightly liberal for the smaller groups (for n=30 the true two-sided 0.05 critical value is 2.045).
- Also: an 18-day window described as 6 effective days means any t-stat is a within-regime statistic, not an out-of-sample one.

## 5. Survivorship bias / selection-on-outcome

**Found — five distinct instances:**

1. **959 closed rows silently excluded** (`net_pnl_pct IS NULL`). All are `first_exit_reason='unclosed_no_candles'`, and **all are one token family: KPEPE (230), KBONK (173), KNEIRO (161), KLUNC (156), KFLOKI (137), KSHIB (102)**. 561 of them are gate-passed, so they were dropped from the headline denominator (8,035). This is systematic exclusion by asset family, not missing-at-random — it removes an entire (probably untradeable) segment from the results with no disclosure.
2. **669 rows still open** (`closed=0`, created Oct 22–25) — excluded without mention; report says "all closed", which is false (20,271 of 20,940 are closed).
3. **Selection-on-outcome in the exit-engine table:** pm_trail 100% WR / hard_max 0% WR are definitional artifacts of *which exit fired*, not performance evidence. Building Recommendations #2/#3 on t=+66 / t=-529 is a category error.
4. **Selection-on-outcome in the token tables:** 5 of 166 positives reported as a complete set (correct), but 5 of 43 negatives reported as if complete (incomplete) — and the worst negative (TRX LONG, t=-6.46) omitted.
5. **Era confounding in the gate analysis:** 100% of pre-Oct-20 trades are gate-blocked; the pass and block cohorts are not drawn from the same period (see Claim 5).

## 6. Is the MFE/MAE fix correct?

**Verdict: the CODE fix is correct and verified — but it does NOT apply to the data this report analyzed.**

**What the code does now** (`scripts/shadow_trader.py` lines 1244–1262):
```python
entry_ts_val = candles[0][0]
exit_ts_val  = first_result.get('exit_ts', entry_ts_val + 86400)
hold_candles = [c for c in candles if entry_ts_val <= c[0] <= exit_ts_val]
if not hold_candles:
    hold_candles = candles   # fallback to full window
highs = [h for ts,o,h,l,c in hold_candles]; lows = [...]
```
This is the right idea: slice to the actual hold period.

**When it landed — the comment lies:**
```
$ git show 0cde9c91 -- scripts/shadow_trader.py
commit 0cde9c91fe4f5df72c9c6b7274783e4fe8d045af
Date:   Sun Oct 25 03:28:19 2026 +0000
    automation: hourly analysis 2026-10-25 03:30 — no change (quiet hour, 24h GREEN)
-               highs = [h for ts, o, h, l, c in candles]      # OLD: full 24h window
+               # FIX 2026-10-22: Only use candles during the ACTUAL HOLD PERIOD...
```
- The comment says **2026-10-22**; the commit is **2026-10-25 03:28:19 UTC** — three days later, ~11 hours before this report's data snapshot, and buried in an unrelated commit titled *"automation: hourly analysis … no change"*.
- Prior code (introduced 2026-10-20, `4d2063a8`) was `highs = [h for ... in candles]` over the entire loaded window — i.e. **the 24h window**, exactly as the report describes the bug.

**Empirical verification against `candles.db` (recomputing MFE/MAE from 1-minute candles):**

| Cohort | n sampled | Matches **hold period** | Matches **[entry → close-event time]** | Matches **full 24h** |
|--------|-----------|--------------------------|----------------------------------------|----------------------|
| Closed **before** fix | 400 | **5 (1.3%)** | **297 (74.3%)** | 88 (22.0%) |
| Closed before fix, **gate-passed only** | 400 | 7 (1.8%) | **356 (89.0%)** | 4 (1.0%) |
| Closed **after** fix | 400 | **400 (100%)** | 10 | 3 |

*(post-fix tested two ways: origin = first-candle ts → **400/400 exact**; origin = parsed created_at → 188/400, confirming the code uses `candles[0][0]` as origin)*

Worked example — id 13799, MON SHORT, hold **11 minutes**:
```
stored MFE=1.0009 MAE=-2.1777
  hold window (11 min)      MFE= 0.7196 MAE= -0.0184
  universal_hold/speed_stale MFE= 1.0009 MAE= -2.1777   <== EXACT MATCH
  full 24h                  MFE= 4.1275 MAE= -2.4460
```
Pre-fix rows measure excursion from entry to the **batch close-event time** (~4.5 h later, whenever the 24h window had not yet elapsed), or the **full 24h** for backfilled signals — never the 11-minute hold.

**Scale of the impact:**

| | closed rows | with MFE | gate-passed |
|---|---|---|---|
| Pre-fix (before 2026-10-25 03:28:19) | 18,794 (**92.7%**) | 17,580 | **7,071 (88%)** |
| Post-fix | 1,477 | 1,356 | 964 (12%) |

- Gate-passed pre-fix: mean MFE **1.591**, MAE **-1.338**.
- Gate-passed post-fix: mean MFE **0.552**, MAE **-0.409** — **~3x smaller**, exactly as expected once the window shrinks from ~4.5h to the actual hold.
- The report's §2 "MFE/MAE" column reproduces exactly (ratio of means: SHORT **1.515 → 1.52**, LONG **0.768 → 0.77**) — so the report definitely used these columns, and **88% of them are unfixed**. Post-fix-only ratios would be SHORT 1.831 (n=617), LONG 0.796 (n=347).

**Conclusion:** the fix is real, correct, and 100% verified on rows closed after 2026-10-25 03:28:19 — but it was never applied retroactively, so the report's "Key Fix" claim is **true of the code and false of the data**. Nothing in the report discloses this. Also, `mfe_4h`/`mae_4h` are 100% NULL (0/20,940) — a dead column pair.

## 7. Is gate-passed-only the right approach?

**Verdict: correct as the primary metric — but the report must disclose the denominator, and its gate claim rests on a confounded comparison.**

| Cohort | n | Net sum | Avg | WR% | t (naive) | t (cluster) |
|--------|---|---------|-----|-----|-----------|-------------|
| **Gate-passed** | 8,035 | **-718.23%** | -0.0894 | 58.3 | -11.19 | **-5.68** |
| Gate-blocked | 11,277 | -1,312.43% | -0.1164 | 46.9 | -15.16 | -11.89 |
| **All trades** | 19,312 | **-2,030.66%** | -0.1052 | 51.7 | -18.84 | — |

- Gate-passed **is** the right measure of "what the system actually takes" — it's the only cohort that reflects the live decision, and it is the *less bad* number (avg -0.089 vs -0.116).
- **But the report never states the all-trades figure (-2,030.7%).** Presenting -718.2% as "**the system** is losing" while the system generated 19,312 evaluable trades of which 11,277 were blocked understates total system damage by 2.8x. The honest framing is: *"the system's gate-passed subset lost -718.2%; its full shadow book lost -2,030.7%."*
- **The gate-pass-vs-gate-block contrast is era-confounded** (59.9% of blocked rows are pre-Oct-20 backfilled EXPIRED signals; 0% of pre-Oct-20 trades passed). So it cannot cleanly support "gates are helping" — see Claim 5.
- The right control is a like-for-like comparison within the same period (Oct 20–25 only), reported alongside the all-trades total.

---

# OVERALL ASSESSMENT

**The report is arithmetically competent and statistically under-corrected.** I reproduced its headline sum (-718.23%), mean, SD, WR, RR, breakeven WR, direction splits, all 10 signal rows, all 11 gate rows and all 5 token rows — most to within ±0.06 t. That is a real improvement over the invalidated gross analysis.

**But four of its ten "key insights" fail on audit:**

- **Claim 2 is the most damaging failure.** squeeze_cross SHORT at t=2.01 is the report's single positive finding and the basis of Recommendation #1 ("This is the edge"). It collapses to **t=+0.76** under a defensible clustering correction, fails Bonferroni (critical 3.28), and has a 95% CI of [0.0007%, 0.049%]. There is currently **no demonstrated edge anywhere in the system** — which is a materially different message from "focus on squeeze_cross SHORT."
- **Claims 3 and 4 are selection-on-outcome dressed as findings.** 100%-WR and 0%-WR exits are definitional. They cannot justify "route more trades through PM Trail" or "reduce Hard Max usage" — those engines fire because of where the trade already is. And Claim 3 is *literally* false: `hold` LONG (t=3.51) and `pump_exit` SHORT (t=5.61) are profitable too, as the report's own table shows.
- **Claim 5 contradicts the report's own table** (5 of 8 rows are labelled NEUTRAL, and CTX-GATE SHORT is positive) and omits 3 gate rows entirely.
- **Claim 9 understates the damage by 8.6x** (43 negative token-directions, not 5) while Claim 8's 5 positives are correctly complete — an asymmetric presentation.

**The MFE/MAE "Key Fix" is the report's stated methodological centerpiece and it does not apply to the data.** 88% of gate-passed rows still carry the old close-window/24h measurements; the fix landed 11 hours before the snapshot, under a comment claiming an earlier date, inside a commit titled "no change."

**Critical Issues Found:**

| # | Severity | Issue |
|---|----------|-------|
| 1 | **CRITICAL** | squeeze_cross SHORT (t=2.01) is not significant after clustering by signal timestamp (t=0.76) or multiple-comparison correction (Bonferroni 3.28). The report's only positive finding and Recommendation #1 are unsupported. |
| 2 | **CRITICAL** | MFE/MAE "fix" was committed 2026-10-25 03:28 (comment falsely says 10-22); **88% of gate-passed rows and 92.7% of all rows are pre-fix** and still measure [entry → close-event], not hold period. Report claims the fix as applied. Verified 400/400 post-fix vs 7/400 pre-fix. |
| 3 | **HIGH** | "Oct 7-25, 18 days" is wrong for the headline metric: **all 8,035 gate-passed trades fall in Oct 20–25 (6 days)**; 100% of pre-Oct-20 trades are gate-blocked. Report's own daily table only lists Oct 20–25. |
| 4 | **HIGH** | "Total signals 20,878" reconciles with nothing (actual: 20,940 rows / 20,271 closed / 19,312 with PnL); the report's own gate split sums to 19,312. Header is internally inconsistent. |
| 5 | **HIGH** | Exit-engine conclusions are selection-on-outcome (pm_trail 100% WR, hard_max 0% WR are definitional). Recommendations #2/#3 rest on them. |
| 6 | **HIGH** | Claim 9: 43 token-directions are significantly negative, not 5; worst (TRX LONG t=-6.46) omitted. Selection-on-outcome. |
| 7 | **HIGH** | No multiple-comparison correction across 47–166 simultaneous tests. Expected false positives: ~2.4 (signals), ~8.3 (tokens). |
| 8 | **MEDIUM** | hard_max t-stats unreproducible: report -523.29/-557.47, independent computation **-529.25/-587.58** (n and mean match exactly). |
| 9 | **MEDIUM** | Gate-passed-only headline (-718.2%) never shown alongside all-trades (-2,030.7%) — 2.8x understatement of total system damage. |
| 10 | **MEDIUM** | Claim 5 "ALL gates helping" contradicted by own table (CTX-GATE SHORT blocked +14.79%) and 3 gate rows omitted. |
| 11 | **MEDIUM** | 959 closed rows excluded as `unclosed_no_candles` — all K-prefixed token family (KPEPE/KBONK/KNEIRO/KLUNC/KFLOKI/KSHIB), 561 gate-passed. Systematic, undisclosed. |
| 12 | **MEDIUM** | Report says "all closed" — 669 rows are still open. |
| 13 | **LOW** | Report §2 "MFE/MAE" values (1.52 / 0.77) reproduce exactly but are computed from pre-fix data; post-fix ratios are 1.831 / 0.796. |
| 14 | **LOW** | Breakeven WR 65.8% is a rounded-RR artifact (true 65.70%); gap is 7.36pp not 7.5pp. |
| 15 | **LOW** | `mfe_4h`/`mae_4h` columns are 100% NULL across 20,940 rows — dead schema. |

**Sideways finds (unrelated to the report):**
- **`0cde9c91` hides a substantive code change in a commit titled "automation: hourly analysis … no change".** Any automated commit hygiene/changelog process will miss it. *Severity: MEDIUM — suggested fix: require code-only changes to be committed with a `fix:`/`scripts:` message.*
- **The "FIX 2026-10-22" comment documents a date the fix did not happen.** *Severity: MEDIUM — fix: correct the comment to the real landing date or link the commit hash.*
- **669 open shadow rows dated back to 2026-10-22** — 3 days stale, suggesting `close_events()` is leaving rows behind. *Severity: MEDIUM — worth a `--reclose` sweep and a log check.*

---

# RECOMMENDATIONS

**Add:**

1. **Report cluster-robust t-statistics** (cluster on `created_at`, or on day) beside naive t. Two headline claims flip: squeeze_cross SHORT 2.01→**0.76**, SHORT direction -2.99→**-1.27**. At minimum state the independence assumption and the 2,528-timestamp / 110-hour effective sample size.
2. **Multiple-comparison correction.** Report Benjamini-Hochberg FDR alongside raw p, and state how many tests were run (47 signals, 166 tokens, 16 engines, 11 gates). Under Bonferroni **no token survives** (crit 3.62; MNT 3.56).
3. **Both denominators, every time:** gate-passed -718.2% (n=8,035) **and** all trades -2,030.7% (n=19,312), with the 19,312 denominator stated.
4. **Period disclosure in the headline:** "Oct 20–25, 6 days" for gate-passed; "Oct 7–25" only for the blocked cohort. Fix the 20,878 header number or drop it.
5. **Re-run MFE/MAE after a `--reclose` sweep** so all rows use the fixed code, then restate §2. Report the pre-fix/post-fix split explicitly (currently 88% / 12% of gate-passed).
6. **A like-for-like gate comparison** restricted to Oct 20–25, excluding the 6,751 backfilled `EXPIRED` rows — the current comparison is era-confounded.
7. **The full negative-token list (43)** next to the 5 positives, ranked by t, so the asymmetry is visible.
8. **Exit-engine analysis that isn't definitional:** compare engines on the *same* trades (e.g. what would pm_trail vs hard_max have done on the identical entry), not on disjoint subsets selected by which engine happened to fire.
9. **Out-of-sample / split-period check.** 6 effective days in a single bearish regime cannot support "this is the edge." Split Oct 20–22 vs Oct 23–25 and require the sign to hold.
10. **Disclosure of exclusions:** the 959 `unclosed_no_candles` K-token rows and the 669 still-open rows.

**Change:**

11. **Withdraw Recommendation #1** ("Focus on squeeze_cross SHORT — this is the edge"). Under clustering it is indistinguishable from zero.
12. **Withdraw or re-derive Recommendations #2 and #3.** You cannot "route trades through PM Trail" — it fires only after profit exists; "reduce Hard Max usage" needs a counterfactual on identical trades, not a t-stat on a definitional subset.
13. **Rewrite Key Insight #3** — PM Trail is the only engine profitable *in both directions*; `hold` LONG and `pump_exit` SHORT are also profitable and significant (the report's own table says so).
14. **Rewrite Key Insight #5** — "most gates block losing trades; CTX-GATE SHORT blocks profitable ones (+14.8%) and should be reviewed; EXEC-BLOCK and SKIP rows were omitted."
15. **Rewrite Key Insight #9** — "43 token-directions are significantly negative (CHIP/NXPC/ICP/ALT/LDO among them); 5 are positive."
16. **Reconcile the hard_max t-statistics** before republishing — document the exact formula and sample that produced -523.29/-557.47, or replace with -529.25/-587.58.
17. **Correct the `FIX 2026-10-22` comment** and stop shipping code changes inside commits labelled "no change."

**Bottom line:** the system is losing money net of fees — that conclusion is solid and reproducible (cluster t = -5.68, still clearly significant). Everything the report says about *where the edge is* (squeeze_cross SHORT, PM Trail allocation, positive tokens) is either definitional, uncorrected for multiple comparisons, or collapses under a clustering correction. No actionable edge has been demonstrated.

---

*Auditor's note: all figures above were produced by executing queries against `shadow_trades.db`, `candles.db` and git history during this audit. No number was taken from the report on trust; report values are shown alongside mine for comparison only.*
