# Independent Audit — "Home-Run Trade" Quantitative Analysis (2026-10-08)

Auditor: independent verification agent. All numbers recomputed from scratch via raw SQL
against `psql host=/var/run/postgresql dbname=brain user=postgres`, table `trades`.
No analysis script or output was trusted or reused. Stats via scipy 1.17.1.

Window definition used throughout (as specified):
`status='closed' AND paper='f' AND pnl_pct IS NOT NULL AND close_time > now() - interval '90 days'`
Baseline run at 2026-10-08 20:09 UTC returned exactly **3364 trades / 64 HR / 1670 winners**,
reproducing the claim's baseline. NOTE: the window is live — by 20:18 UTC the same query returned
3366 trades (new trades closing mid-audit). The claim's snapshot was not time-pinned; small
count drift (e.g. LONG 1942→1944) is expected and immaterial.

"HR" = pnl_pct >= 10 (defined on the pnl_pct column — see NEW CONCERNS #2 on what that column means).

---

## CLAIM A — HR inventory: **AGREE** (with one structural caveat)

| Item | Claim | Mine | Verdict |
|---|---|---|---|
| Total 90d trades | 3364 | 3364 | ✅ |
| HR count | 64 | 64 | ✅ |
| HR % of all trades | 1.9% | 64/3364 = 1.90% | ✅ |
| Winners | 1670 (3.8% HR) | 1670 with pnl_pct>0; 64/1670 = 3.83% | ✅ |
| Range | 10.1%–47.5% | 10.0696–47.5348 | ✅ |
| Span | Aug 21 – Oct 8 | 2026-08-21 08:53 → 2026-10-08 18:56 | ✅ |
| ≥20% tier | 22 | 22 | ✅ |
| Wilson 95% CI | [1.5%, 2.4%] | [1.49%, 2.42%] | ✅ |

Caveat (does not change the arithmetic, changes the interpretation): the 1512 window trades that
closed **before Aug 21 contain ZERO HRs** (max pnl_pct 3.14%). The 1.9% base rate blends a
structurally-zero era with the live era. Post-Aug-21: 64/1854 = **3.45%, Wilson [2.71%, 4.38%]**.
For forward-looking expectations the post-era rate is the honest number. Also 36 zero-pnl rows are
counted as non-HR — correct and defensible.

SQL: standard window + `pnl_pct>=10`; per-week histogram of totals/HRs; min/max(pnl_pct);
`percentile_cont(0.5)` etc.

## CLAIM B — Signal concentration: **PARTIAL** (counts exact; 3 of 5 p-values era-contaminated)

Counts and raw Fisher p reproduce **exactly**:

| Signal | Claim | Mine (count/rate) | Raw Fisher (mine) | Era-matched Fisher/CMH (mine) |
|---|---|---|---|---|
| pump-chain+ | 13/138=9.4%, p<1e-4 | 13/138=9.42% | p=1.15e-6 | **CMH week-stratified OR 2.69, p=4.8e-5 — survives** |
| hl_copy_trader | 12/79=15.2%, p<1e-4 | 12/79=15.19% | p=1.48e-8 | in-era (Aug21-25) OR 4.61, **p=0.0018** — still real, but not <1e-4 |
| ct-hot+ | 7/99=7.1%, p=0.0024 | 7/99=7.07% | p=0.00243 | in-era (traded only Aug 15-24): OR 1.72, **p=0.19 ns** |
| volume-breakout-long+ | 3/24=12.5%, p=0.010 | 3/24=12.50% | p=0.00999 | in-era (Sep17-Oct5): OR 5.73, **p=0.029** (n=3, fragile) |
| pullback-entry- | 5/120=4.2%, p=0.076 | 5/120=4.17% | p=0.0762 | in-era (Sep6-22): OR 1.03, **p=0.56 — exactly baseline** |

The claimed p-values compare each signal against the WHOLE book including 1512 pre-Aug-21 trades
that are structurally incapable of being HRs (and, for the Aug-era signals, against a book whose
era base rate was already ~3.7%). Era-matching kills ct-hot+ and pullback-entry- entirely,
halves hl_copy_trader's significance, and confirms pump-chain+ is genuinely ~2.7x baseline odds
even after week-stratification. Base rate 1.9% confirmed. Multiple comparisons: ~66 signals have
≥10 trades; Bonferroni threshold 7.6e-4 — only pump-chain+ (and hl_copy_trader on raw, not
era-matched) survives.

hl_copy_trader date span: **CONFIRMED traded only 2026-08-21 04:32 → 2026-08-25 10:27** (79 trades).
It is **stale** — no trades in the ~6 weeks since. ct-hot+ is also stale (last trade Aug 24).

## CLAIM C — Direction/leverage/vol splits: **PARTIAL** (rates reproduce; EXTREME p is inflated ~30x)

| Split | Claim | Mine | Fisher/CMH (mine) |
|---|---|---|---|
| LONG | 50/1942=2.6% | 50/1944=2.57% | two-sided p=0.0009 (claim 0.0008) ✅ |
| SHORT | 14/1422=1.0% | 14/1422=0.985% | ✅ |
| 5x | 58/1905=3.0% | 58/1905=3.04% | one-sided p=2.0e-9 ✅ |
| 3x | 6/1458=0.4% | 6/1460=0.41% | ✅ (also 1 trade at 1x, 0 HR) |
| EXTREME | 32/991=3.2%, p=0.0005 | 32/993=3.22% | vs raw rest p=0.0004 ✅ reproduces — **but** |
| EXTREME adjusted | — | — | vs rest **excluding 613 NULL-regime trades** (all legacy signals, 0 HRs): p=0.0145; week-stratified CMH: **p=0.015, ~30x weaker than advertised** |
| HIGH | 1.5% ns | 13/871=1.49% | ns ✅ |
| NORMAL | 2.1% ns | 18/861=2.09% | ns ✅ |

The volatility_regime NULL bucket (613 trades, 0 HRs, all pre-Sep-2 legacy signals like
tl_break/inv-accel) sits inside the claim's "rest", mechanically boosting EXTREME's contrast.
Direction and leverage rates are as claimed — but see CLAIM D / bias-hunt #2 on leverage being
signal-confounded.

## CLAIM D — Case-control signature: **PARTIAL** (all reported numbers reproduce; the interpretation is confounded)

Reconstructed the design myself: 64 HRs vs **879** non-HR controls on the same 20 strategies,
open_time ≥ Aug 21 (claim's 871 differs only by live-window drift). Results:

| Feature | Claim | Mine | Verdict |
|---|---|---|---|
| entry_rsi_14 | HR 61.3 (n=32) vs 52.0 (n=293), p=0.014 | HR mean 61.30 (n=32) vs 52.21 (n=297), MW p=0.0166 | ✅ reproduces |
| entry_bb_position | 0.62 vs 0.49, p=0.031 | 0.62 vs 0.49, p=0.0368 | ✅ reproduces |
| leverage | 4.81 vs 4.18, p<1e-4, only Bonferroni survivor | 4.81 vs 4.18, MW p=1.4e-6 (Fisher 5x-vs-3x OR 6.4, p=1.8e-7) — survives 0.00357 | ✅ statistically |
| meta rsi_14 | 52.1 vs 51.8, p=0.84 | 52.14 vs 51.77, p=0.833 | ✅ |
| btc_regime | chi2 p=0.65 | chi2=4.196, dof=6, **p=0.650** | ✅ exact |
| RSI coverage | 32/64 HRs | 32/64 | ✅ exact |

Adversarial findings that undercut the interpretation:
- **Leverage does NOT hold within the biggest signal**: pump-chain+ 5x 9/76 (11.8%) vs 3x 4/64
  (6.25%), Fisher **p=0.20, ns**. In the matched pool the effect is largely between-signal:
  all-5x signals (hl_copy_trader 78/79 at 5x, ct-hot+ 55/99 at 5x) supply 19/64 HRs while
  3x-heavy signals supply almost none. Strategy matching does not remove this because the
  matched signals contain mixed 3x/5x variants. "Leverage is THE feature" is a signal-mix artifact.
- **RSI does NOT hold within-signal either**: within pump-chain+ only, HR 77.3 (n=11) vs control
  72.5 (n=63), p=0.32; within LONG-only post-Sep-16, p=0.17. The pooled RSI gap ≈ "pump-chain+
  entries are high-RSI", i.e. signal identity, not a within-signal entry discriminator.
- Raw `entry_atr_14` looked significant (p=1e-4) but is a token-price scale artifact; normalized
  ATR% (atr/price) is ns (p=0.077). If the original tested raw ATR among its "14 features", one of
  its Bonferroni-surviving features would have been garbage.

## CLAIM E — Post-entry mechanics: **AGREE** (all census numbers exact; one labeling caveat)

| Item | Claim | Mine |
|---|---|---|
| Exits | 48 atr_sl_hit / 7 profit-monster-trail / 4 atr_trail_hit / 5 other | 48 / 7 / 4 / 5 (HARD_SL_FAILED, stale_exit, trail_sl, atr_tp_hit, guardian_hard_sl) ✅ exact |
| Median hold | 159 min | 9533.2 s = 158.9 min ✅ |
| Mean hold | 200 min | 12021.4 s = 200.4 min ✅ |
| Range | 1–890 min | 58.4 s – 53395.6 s = 1.0–890 min ✅ exact |
| MAE | 94% <1%, median 0.26% | 60/64 = 93.8% with abs(MAE)<1%, median abs 0.262% ✅ |
| Time-of-day | no concentration | chi2 uniformity p=0.86 ✅ |
| Weekly | 19 (wk Aug17) → 3-4/wk late Sep | 19,7,6,11,11,3,3,4 ✅ endpoints — but non-monotonic (11/wk in Sep7 and Sep14 weeks) |

Caveats: (a) "92% trail-family" counts the 48 `atr_sl_hit` exits as trail-family; literal trail
exits are 12/64 (19%) unless the ATR stop is treated as trailing — a labeling choice, not a data
error. (b) The "no time-of-day concentration" and hold stats assume independence, but 30% of HRs
fall in one week and several are the same episode re-traded (see NEW CONCERNS #4). (c) MAE is an
UNLEVERAGED price move (see NEW CONCERNS #2) — "MAE <1%" ≈ "<5%" at 5x.

## CLAIM F — Cited trades: **PARTIAL** (all fields verified; one open-time error)

**15984 CRV — fully verified ✅**: Hermes-pump-chain+ LONG, pnl_pct **+42.3397%**, exit_reason
atr_trail_hit, open **2026-10-07 22:17:44**, close 2026-10-08 01:21:41. entry_price 0.35971,
exit_price 0.39017 → price +8.468% × 5x leverage = 42.34% ✅ internally consistent. leverage 5,
size $11.10, pnl_usdt +$0.94, vol EXTREME, duration 11036 s (184 min), MAE 0.014%,
entry_rsi_14 82.38. Metadata present: rsi_14 52.17 (signal-time), bb_position 1.144, z_score 2.576,
btc_score 47.3, speed_percentile 93.2, staleness 1.25 min, btc_regime RANGING_BEAR, wave accelerating.

**15990 IMX — verified except open time ⚠️**: pump-chain+ LONG, +10.7695%, stale_exit, entry
0.17271 → exit 0.17643 = +2.154% × 5x = 10.77% ✅. leverage 5, size $22.10, pnl_usdt +$0.48,
vol EXTREME, duration 1717 s (29 min), MAE 0.394%, entry_rsi_14 89.67. Metadata present
(z 2.386, speed 49.1, staleness 3.15 min, btc_regime TRANSITIONING).
**Actual open time = 2026-10-08 18:27:46, NOT "18:5x".** 18:56:24 is the CLOSE time — the claim
committed exactly the close/execution confusion documented in AGENTS.md. Also odd: metadata says
`is_stale: false` yet the exit reason is `stale_exit`.

## BIAS HUNT

**1. Era artifact?**
- *hl_copy_trader*: YES, largely. It lived 4 days (Aug 21–25 — span confirmed), dead ~6 weeks.
  In its era the rest of the book already ran 3.7% HR (7/187); its era-matched edge is OR 4.6,
  p=0.0018 — real but the headline p<1e-4 is inflated ~4 orders of magnitude by the
  zero-HR pre-era in the "rest".
- *pump-chain+*: NO, not purely. Weekly HR rate (by open_time): 0/3, 1/56, 8/42 (17.8%),
  1/20, 1/10, 2/7. The Sep 18–21 cluster (FOGO/INJ/AVAX/JUP/AVAX/ETC/ADA/JUP → 7 of 13 HRs)
  inflates the 9.4%, but excluding it: 5/87 = 5.7% vs 1.6% same-days rest, p=0.014; and
  week-stratified CMH OR 2.69, p=4.8e-5. Note FIL's +22% HR on Sep 21 was
  volume-breakout-long+, not pump-chain+. pump-chain+ first traded Sep 6 — the signal has never
  existed outside this era, so its "signal" and its "era" are not fully separable, but the
  week-stratified test is the best available adjustment and it holds.

**2. Leverage within pump-chain+**: 5x 9/76 = 11.8% vs 3x 4/64 = 6.25%, Fisher OR 2.0, **p=0.20 ns**.
Leverage does NOT hold within the biggest signal. It is confounded with signal identity
(hl_copy_trader is 99% 5x, ct-hot+ 56% 5x; the 3x-heavy signals produced 6 HRs among ~1460 trades).
Do not act on the leverage "finding".

**3. entry_rsi_14 cliff**: The claim of "100% NULL before Sep 16" is not exactly right — July had
partial coverage (8/38/143, then 129/415 in the Jul-27 week), then a blackout Aug 3–Sep 13
(0% except 87/233 in the Aug-17 week), then full coverage from the Sep-14 week onward. Within the
case-control era it is effectively NULL until ~Sep 14. Of the 64 HRs only **32** have RSI
(14 from the Aug-21–23 recording window + 18 opened post-Sep-16). The gap **survives** on
post-Sep-16-only controls: HR 64.5 (n=18) vs ctrl 51.75 (n=236), MW p=0.019 — same direction,
slightly larger magnitude, still marginal and still NOT Bonferroni-surviving, and still ns within
pump-chain+ (p=0.32).

**4. Other checks**:
- No exact duplicates: no two rows share token+open_time. SOL×6 are 6 distinct trades, but 4 are
  hl_copy_trader re-entries into the SAME SOL Aug 21–22 episode; AVAX×2 and JUP×2 hit within ~16h
  on Sep 19–20. The 64 HRs are not 64 independent market events (pseudo-replication).
- 36 zero-pnl rows exist and are counted as non-HR — correct.
- 39 paper trades in the window, all properly excluded.
- Window is not snapshot-pinned; totals drift minute-to-minute (3364→3366 during this audit).
- Compound strategy strings (e.g. `accel-300-v2-long,volume-breakout-long+`, which contains one HR)
  are counted as their own signals — consistent between claim and my recount.

## NEW CONCERNS

1. **Economic significance ≈ 0.** Post-Aug-21 realized `pnl_usdt` summed across ALL 1854 closed
   live trades = **−$8.94**. The 64 "home runs" sum to **+$28.32** (median size $11.10, max $22.10;
   CRV earned $0.94, IMX $0.48). Any HR-driven strategy decision must be re-derived at realistic size.
2. **pnl_pct convention changed at the Aug 21 boundary.** Pre-era pnl_pct = unleveraged
   (≈ pnl_usdt/amount, mean abs diff 0.074); post-era pnl_pct = price move × leverage (verified:
   CRV 8.468%×5 = 42.34). Also `mfe_pct`/`mae_pct` are unleveraged price moves while `pnl_pct` is
   leveraged — they are not comparable scales (CRV: pnl_pct 42.3, mfe_pct 9.9). The "0 HRs in 1512
   pre-era trades" is therefore at least partly measurement change, not behavior, and the claim's
   MAE statements understate leveraged adverse excursion ~5x.
3. **Pseudo-replication.** 4 SOL re-entries = one episode; AVAX/JUP double-hits; 19/64 HRs (30%)
   in the single week of Aug 17–23 (the hl_copy_trader/ct-hot+ debut). Effective independent event
   count is materially below 64; every p-value in the analysis is optimistic.
4. **30% of the HR inventory came from two signals that stopped trading ~6 weeks ago**
   (hl_copy_trader dead since Aug 25, ct-hot+ since Aug 24). Any "home-run template" built on them
   may be untradeable forward.
5. Minor: IMX metadata `is_stale:false` but exit `stale_exit`; two signals' stale death is itself
   unexplained and worth a pipeline check.

## OVERALL: **USE WITH CAVEATS**

- Safe to use as-is: Claim A inventory, Claim E mechanics census, Claim F (after fixing IMX's open
  time to 18:27:46), and the pump-chain+ concentration (robust to week-stratification).
- Use only with the era-adjusted numbers in this report: Claims B and C (ct-hot+, pullback-entry-,
  hl_copy_trader's p<1e-4, and EXTREME's p=0.0005 do not survive era/coverage adjustment).
- **Do NOT use Claim D's "home-run signature" for any decision.** Both headline features (leverage,
  entry RSI) fail within-signal tests; they are signal-mix artifacts. RSI/BB are directionally
  interesting at best (p≈0.02 pooled, ns within signal).
- Recompute any forward-looking base rate on post-Aug-21 (3.45%) or post-Sep-16 data, and re-derive
  everything after position sizes leave the $11–22 regime.

All SQL/scripts used are reproducible from this report; raw exports at /tmp/cc_data.tsv,
/tmp/atr_data.csv, /tmp/pc_weekly.tsv (session-local).
