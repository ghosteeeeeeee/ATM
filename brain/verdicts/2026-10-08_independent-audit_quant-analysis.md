# VERDICT — Independent audit of 2026-10-08 quantitative analysis (Hermes)

Auditor: independent verification agent (own SQL/scipy from scratch; analysis script+output NOT trusted).
DB: psql host=/var/run/postgresql dbname=brain user=postgres, now()=2026-10-08 19:43 UTC.
All artifacts: /root/.hermes/audit/ (window30.csv, verify_claim4.py, verify_claims4b_5.py, probe_splits.py).

Window used for every 30d figure: `status='closed' AND paper='f' AND pnl_pct IS NOT NULL AND close_time > now() - interval '30 days'` → exactly 819 rows (matches analysis). 90d → 3365 rows, 40 signals with n>=20 (both match).

## CLAIM 1 — AGREE (exact)
n=819, winners=432, WR=52.75%, avg winner +3.739%, avg loser -3.807%, MEDIAN winner +2.213%, MEDIAN loser -3.824%, median payoff ratio 0.579≈0.58. Total 30d net = +$0.64 (breakeven).
SQL: `SELECT count(*), count(*) FILTER (WHERE pnl_pct>0), round(100.0*count(*) FILTER (WHERE pnl_pct>0)/count(*),2), avg(pnl_pct) FILTER (WHERE pnl_pct>0), avg(pnl_pct) FILTER (WHERE pnl_pct<=0), percentile_cont(0.5) WITHIN GROUP (ORDER BY pnl_pct) FILTER (WHERE pnl_pct>0), percentile_cont(0.5) WITHIN GROUP (ORDER BY pnl_pct) FILTER (WHERE pnl_pct<=0) FROM trades WHERE <window>;`

## CLAIM 2 — PARTIAL (numbers exact; "never-win" label wrong)
Reproduced exactly: hard_max_loss 70 / 0%WR / -$9.31; cut-loser-CL-T1 25 / 0% / -$3.11; hard_sl 46 / 34.8% / -$3.17; profit-monster-trail 227 / 79.7% / +$12.08; atr_sl_hit 321 / 49.8% / -$2.54. Aggregate of the 3 named families = 141 trades = 17.2% of 819, sum -$15.59 ✓.
ERROR in analysis: hard_sl is NOT a never-win family (16 winners, 34.8%). True 0%-WR families include cut-loser-MAE-GUARD (5T, 0%WR, -$0.50) which was omitted → true never-win = 100 trades (12.2%), -$12.92.
SQL: `SELECT exit_reason, count(*), 100.0*count(*) FILTER (WHERE pnl_pct>0)/count(*), sum(pnl_usdt) FROM trades WHERE <window> GROUP BY exit_reason ORDER BY count(*) DESC;`

## CLAIM 3 — AGREE (but formulations are mixed — see NEW CONCERNS)
Winners (mean of per-trade ratios pnl_pct/(mfe_pct*leverage)): overall 46.8% (claim 47%), profit-monster-trail 52.1% (52%), atr_sl_hit 39.7% (40%). Underlying: avg winner realized +3.74% vs mfe×lev +7.64% (claim 3.75/7.68 — trivial drift).
Losers (ratio of means): -3.82% realized vs -4.11% mae×lev → -93.2% (claim 93%; sign cosmetic — mae_pct stored positive).
SQL: `SELECT avg(pnl_pct), avg(mfe_pct*leverage), 100.0*avg(pnl_pct/(mfe_pct*leverage)) FROM trades WHERE <window> AND pnl_pct>0 AND mfe_pct>0;` (+ per exit_reason IN ('profit-monster-trail','atr_sl_hit'); losers: pnl_pct<=0, mae_pct>0.)

## CLAIM 4 — PARTIAL (headline exact; median-split sub-claim IRREPRODUCIBLE)
Headline: winners avg RSI 56.527 vs losers 51.882 (claim 56.5/51.9), Welch p=0.0107 (0.011), Mann-Whitney p=0.0137 (0.014), fails Bonferroni 0.05/14=0.00357 ✓.
All other p's reproduce: direction chi2 p=0.905, volatility_regime p=0.246, btc_regime p=0.142, speed_percentile p=0.285, z_score MW p=0.310, leverage p=0.584, staleness p=0.833. bb_position (the "aside"): 0.588 vs 0.514, p=0.013 ✓ significant as parenthetically implied.
Split at median open_time (2026-09-20 17:26): MY halves = +2.73 gap p=0.42 (first), +4.96 gap p=0.020 (second). Claim's +5.5/+3.9 p≈0.08/0.10 matches NO split I tried (cut dates Sep 16→Sep 30 scanned; meta rsi_14 variant gives NO effect at all, gap +0.31 p=0.81). Sign-consistency (+/+) holds; magnitudes and "neither half significant" do NOT (my second half IS significant, p≈0.02).
HIDDEN DATA CLIFF FOUND: entry_rsi_14 is 100% NULL for all trades closing before 2026-09-16. The "30d" RSI test actually covers 22 days (538/819 rows), split 129 vs 409 across the halves.
SQL: `SELECT count(*) FILTER (WHERE close_time<'2026-09-16' AND entry_rsi_14 IS NOT NULL) FROM trades WHERE <window>;` → 0.

## CLAIM 5 — AGREE (all figures exact)
40 signals n>=20 in 90d; Bonferroni 0.05/40=0.00125. bb-bounce-v2-long+ n=106 WR68.9% binom p=0.000128 — ONLY positive significant. inv-accel-300- n=98 WR32.7% p=0.000770; inv-accel-300+ n=77 WR27.3% p=0.000082 — significant negative. ct-hot+ n=99 WR38.4% sum -$4.07, ran 2026-08-15..24, binom p=0.0265 NOT significant ✓. pump-chain+ 138/54.3%/+$4.26 ✓. volume-breakout-long+ 24/66.7%/+$3.04 ✓.
Robustness: bb-bounce stays significant vs population WR 0.5275 (p=0.00088); stable by month (Sep 67.0% n=97, Oct 88.9% n=9) but only +$1.76 total.
SQL: `SELECT replace(strategy,'Hermes-',''), count(*), count(*) FILTER (WHERE pnl_pct>0) FROM trades WHERE status='closed' AND paper='f' AND pnl_pct IS NOT NULL AND close_time > now()-interval '90 days' GROUP BY strategy HAVING count(*)>=20;` + scipy.stats.binomtest(wins,n,0.5).

## CLAIM 6 — AGREE
Top-25 all-time (live, closed, by pnl_pct): atr_sl_hit 20/25 = 80% ✓; rest = atr_trail_hit×2, trail_sl×1, HARD_SL_FAILED×1, atr_tp_hit×1 ✓. 30d population atr_sl_hit share 39.2% ✓ (all-time share 52.7% — baseline choice inflates the contrast). Descriptive only, as claimed. (Amusement: ct-hot+, claim 5's "biggest bleed", owns 4 of the top-25 winners.)

## CLAIM 7 — AGREE (fully verified; also defense-in-depth beyond the analysis)
hermes_constants.py L885 SHORT_RSI_HARD_FLOOR = 45 ✓, L889 OVERSOLD_SHORT_RSI_MAX = 35 ✓.
decider_run.py: import L1063; hard-blocks L1082-1085 (live RSI + detect RSI, explicit "no bearish override" — the bearish-structure override sits BELOW the hard floor and is unreachable for it); fail-closed when both RSI sources None (~L1090, Oct-5 fix); exec-time re-check L1935-1943. Also mirrored in brain.py L373-388 and signal_compactor.py L3639-3660 (OVERSOLD check).
Timing caveat: HARD_FLOOR raised 25→45 only on 2026-10-07 04:38 UTC (commit 5cd2a9f2); OVERSOLD_SHORT_RSI_MAX=35 present since ≥2026-09-26. The 30d evidence was mostly generated under floor=25. Finding = re-proposing shipped work ✓, but "45" specifically is ~2 days old.

## CLAIM 8 — PARTIAL (daily sums exact; causal story overstated)
Daily hard_max_loss sums (close_time): Oct1 -$1.02 ✓, Oct2 -$1.44, Oct3 -$1.77 ✓, Oct4 -$1.49, Oct5 -$1.43, Oct6 -$0.96 ✓, Oct7 -$0.61 ✓, Oct8 -$0.47 (partial, 19:43 UTC) ✓ — all five claimed values reproduce.
BUT: CUT_LOSER_PNL -1.00→-1.50 committed Oct 7 17:17 UTC (a907babd) — 6 of Oct 7's 8 HML trades CLOSED BEFORE it; Oct 7's improvement predates the fix. Earlier lev-aware HML fix (aed0aa36, Oct 7 01:55) already cut magnitude ~-4.4%→~-1.5%. HML per-trade severity: Oct 7 avg -1.92%, Oct 8 avg -3.92% (severity BACK to pre-fix level; HML_VOL_ATR_MULT widened thresholds — improvement is frequency only). HML share of daily closes: Oct 7 62%, Oct 8 43% — still above the <40% goal. ≥6 other changes landed Oct 7-8 (pump-chain+ LONG killed, pump-chain-v5 LONG disabled, EXTREME block revert, LONG RSI 70→85, BTC momentum threshold) — attribution not identifiable from 5 points of n=3-13 trades/day.

## Bias sanity checks
- Paper trades: 9 paper closes exist in the 30d range; paper='f' excludes them all. Zero paper rows survive the filter. No bias.
- pnl_pct IS NOT NULL: drops 0 rows (0 of 5575 live-closed are NULL). No bias. pnl_usdt/leverage/mfe_pct/mae_pct/volatility_regime also 0 NULLs in window.
- exit_reason fragmentation (30d, full list, n DESC): atr_sl_hit 321, profit-monster-trail 227, hard_max_loss 70, hard_sl 46, rr_engine_resistance 37, pump_exit_dead_money 26, cut-loser-CL-T1 25, rr_engine_support_br 13, atr_trail_hit 11, rr_engine_support_tp 9, HL_CLOSED 6, cut-loser-MAE-GUARD 5, hard_tp 5, UNIVERSAL_MAX_HOLD 4, trail_sl 4, pump_exit_momentum 3, stale_exit 2, HARD_SL_FAILED 2, atr_tp_hit 1, rr_engine_resistance_break 1, (empty) 1. Headline families have NO label variants (no hard_max_loss_xxx). Secondary near-duplicates exist (rr_engine_resistance vs _break; rr_engine_support_br vs _tp; cut-loser-CL-T1 vs -MAE-GUARD; 1 empty) but only in n≤37 groups.
- REAL fragmentation is in strategy labels (90d): 506 distinct labels incl. combo names ("bb_bounce+,range_finder+" 53T, "accel-300-,rs-s-broken" 42T…). The bb-bounce family alone is split across 8 labels (395 trades). Per-signal n's undercount families.

## NEW CONCERNS
1. entry_rsi_14 recording began 2026-09-16 (100% NULL before). "30d" RSI claims cover 22 days; the split-robustness test is lopsided by construction (129 vs 409 trades). Meta `_signal_metadata.rsi_14` shows NO winner/loser effect (gap +0.31, p=0.81) — the effect exists only in the column; possible feature-regime artifact, needs re-check after 30d of uniform recording.
2. Claim 4's split figures (+5.5/+3.9, p≈0.08/0.10) are irreproducible under every split I tried; my second half is significant (p≈0.02). Reconcile before citing the robustness claim.
3. Claim 3 mixes formulations: winners = mean of per-trade capture ratios, losers = ratio of means. Consistent avg-of-ratios for losers = -217% (not -93%); consistent ratio-of-means for winners = 48.9%/57.8%/45.0% (not 47/52/40). "Stops roughly hold" survives only ratio-of-means.
4. 30d total live net = +$0.64 on 819 trades — system is breakeven; hard_max_loss (-$9.31) is 15x the entire net.
5. Claim 8 attribution confounded (see claim); also HML per-trade severity worsened Oct 8 (-3.92% avg) by design of HML_VOL_ATR_MULT — monitor.
6. Claim 5's negative signals are stale (inv-accel-300± stopped Aug 1-2; ct-hot+ Aug 24) — no live action; the one actionable positive (bb-bounce-v2-long+) is +$1.76 total dollars.
7. pnl_usdt fee-inclusion not verified (fees column is free text); all dollar figures inherit that assumption.
8. bb_position (L881 aside) is itself significant (p=0.013) and correlated with RSI — if a Bonferroni family is chosen post hoc, the "14 variables" denominator should be documented.

## OVERALL — USE WITH CAVEATS
Safe to use: Claims 1, 2 (numbers), 3, 5, 6, 7 — all reproduce. Do NOT use unamended: Claim 4's median-split robustness statement (irreproducible + hidden 22-day coverage) and Claim 8's post-fix efficacy narrative (fix landed mid-day after 6/8 trades; severity back up; confounders). Fix the "three never-win families" mislabel (hard_sl wins 34.8%; cut-loser-MAE-GUARD omitted). Re-run the split analysis after 2026-10-16 so both window halves have uniform entry_rsi_14 coverage.
