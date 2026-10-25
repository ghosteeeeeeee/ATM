# Independent Verdict — Shadow-Mode NET PnL Report

**Auditor:** independent (fresh read, no priming beyond the report itself)
**Date:** 2026-10-25
**Report audited:** `reports/20261025-shadow-net-pnl.md`
**Data source:** `brain/shadow_trades.db` (opened directly, all numbers below re-derived by my own SQL)
**Method:** every claim re-queried from scratch; statistical significance (t-tests, 95% CI, multiple-comparison checks) computed independently; MFE/MAE fix verified in source code (`scripts/shadow_trader.py`).

---

## Data reality check (what the DB actually contains)

- Table `shadow_trades`: **19,064 rows total; 18,429 closed; 17,556 with non-NULL `net_pnl_pct`** (the analysis set).
- 873 rows are `closed=1` but have NULL net/gross pnl and no `first_exit_engine` (decisions EXPIRED/SHADOW_BYPASS/PENDING) — excluded from every table in the report. 635 rows are not closed at all.
- `created_at` spans 2026-10-07 → 10-25; **trades exist on only 15 calendar days** (Oct 8–10 empty). `closed_at` spans only Oct 20–25 (bulk backfill), so any day-bucketing must use `created_at` (the report appears to do so — its daily numbers reproduce).
- `net_pnl_pct = gross_pnl_pct − 0.14` verified on every row (0 mismatches). PnL is unleveraged price-move % (`leverage_used` never enters pnl). Summing per-trade % assumes equal sizing per trade — it is a synthetic metric, not a portfolio return.
- **61.2% of the analysis rows (10,751 of 17,556) are `gate_blocked=1`** — counterfactual trades that were BLOCKED and never executed. Only 6,805 rows represent signals that passed the gates.

---

=== INDEPENDENT VERDICT ===

## Claim 1: System losing -1,938% net
**Verdict: PARTIAL**
**Evidence:** The headline number reproduces **exactly**: SUM(net) = **-1,938.18%**, AVG = -0.1104%/trade, WR = 51.16% (8,982/17,556). The loss is highly significant (t = -18.7, 95% CI [-0.122, -0.099]). Fee arithmetic verified: gross total +519.7% − 17,556×0.14% = -1,938.2%. Sign is robust — even with **zero** slippage the system still loses (-182.6% at fee-only 0.04%); breakeven all-in cost is 0.030%/trade.
**However — two material problems:**
1. **The total mixes blocked counterfactuals with traded signals.** 10,751 of the 17,556 rows are gate-blocked hypotheticals. The set that actually "traded" (gate_blocked=0, n=6,805) lost **-657.4%** (-0.097%/trade, t=-11.3). The report's own §7 treats blocked-trade losses as *savings* ("CONFLUENCE-EXPIRY is HELPING"), yet folds the same -1,280.7% of blocked-trade losses into the -1,938% headline. The system as configured ran -657%, not -1,938%. The headline contradicts the report's own gate section.
2. "17,556 signals, all closed" is inaccurate (19,064 signals, 18,429 closed, 873 closed rows silently excluded for NULL pnl).
**Confidence:** HIGH on the arithmetic; the *interpretation* ("the system loses -1,938%") is misleading — see Critical Issues.

## Claim 2: Only 3 signals are net-positive
**Verdict: PARTIAL**
**Evidence:** The three named cells reproduce **exactly**: squeeze_cross SHORT +39.02% (n=2,471, WR 69.9%), pump-chain-v6 SHORT +26.81% (n=162, WR 42.6%), volume_breakout_short +17.54% (n=123, WR 39.8%).
**But:** (a) "only 3" is factually wrong — **17 signal×direction cells are net-positive** (11 with n≥5: hh_hl_breakout_long +10.4, hl_copy_minus +8.2, wyckoff_distribution +7.0, etc.). The defensible statement is "only 3 with n≥100."
(b) **None of the 3 is statistically significant**: squeeze_cross SHORT avg +0.0158%, t=**1.14**, 95% CI [-0.011%, +0.043%]; pump-chain-v6 SHORT t=1.57 (CI crosses 0); volume_breakout_short t=1.22 (CI crosses 0). With **69 signal cells tested**, having 3 tops by total is exactly what selection-on-outcome produces under a true mean of ~0.
(c) volume_breakout_short is **100% gate-blocked** (all 123 rows gate_blocked=1 — it never actually trades), so recommendation #1 ("focus on these signals") is partly moot. Same for hmacd_mtf (0 of 105 passed).
**Confidence:** HIGH.

## Claim 3: PM Trail is the only profitable exit engine
**Verdict: PARTIAL**
**Evidence:** Numbers reproduce exactly: pm_trail SHORT +1,755.7% (n=4,553), LONG +827.4% (n=2,306), WR 100.0%.
**But two findings the report misses:**
1. By the report's own table, **atr SHORT (+243.6%), pump_exit SHORT (+87.9%), hold LONG (+65.2%), universal_hold SHORT/LONG (+17.9%/+3.9%) are also net-positive** — pm_trail is only the only engine positive in *both* directions. "Only profitable exit engine" is false as written.
2. **The 100% WR is structural, not skill.** Code verification (`shadow_trader.py:652-711`): the PM Trail simulator only activates after price has already moved ≥ `activate_pct` in favor (`current_pnl >= activate_pct`, line 687), and exits at peak ± trail distance — it can exit *only* in profit by construction. Any trade that never reaches activation falls to a loss-side engine. Exit-engine attribution therefore splits trades by *which price path they happened to take* — pure selection-on-outcome. "PM Trail is profitable" ≈ "trades that went up are attributed to PM Trail."
**Confidence:** HIGH.

## Claim 4: Hard Max is the biggest loser
**Verdict: PARTIAL**
**Evidence:** Numbers reproduce exactly: hard_max SHORT -2,376.5% (n=2,523), LONG -1,763.2% (n=1,861), WR 0.0%. Descriptively it is the biggest negative cell — AGREE on that.
**But:** 0% WR is definitional — hard_max is the -0.8% stop-loss (`hard_max_loss`, exits between -1.33% and -0.79% in the data); by design it fires only on losing trades. And the causal claim "It's cutting trades at -0.8% before they can recover" is **not measured anywhere** — first-exit attribution cannot say what those trades would have done without the stop. Recommendation #3 ("reduce Hard Max usage") rests on an untested counterfactual.
**Confidence:** HIGH on numbers, HIGH that the causal interpretation is unsupported.

## Claim 5: CONFLUENCE-EXPIRY is HELPING
**Verdict: PARTIAL**
**Evidence:** Numbers reproduce: CONFLUENCE-EXPIRY blocked trades — LONG n=3,831 sum -655.8%, SHORT n=5,771 sum -489.1% (total -1,144.9% hypothetical losses avoided). Directionally, blocked trades did simulate negative, so blocking them "helped" vs taking them.
**But the effect is statistically indistinguishable from random blocking:**
- Blocked avg = -0.1191%/trade vs Passed avg = -0.0966%/trade. Diff = -0.0225%, **t = -1.93, p ≈ 0.054** — not significant at 95%.
- CONFLUENCE-EXPIRY blocked avg (-0.1192%) vs overall population avg (-0.1104%): **t = -0.89** — the gate is selecting barely-worse-than-random trades.
- The gate blocks **61% of all signals**. Any random subset of that size would "avoid" roughly the same -0.11%/trade. The report's verdict table also self-contradicts: text says "ALL gates are HELPING" while its own table labels CTX-GATE SHORT (blocked +15.6% — a gate that *cost* money) as NEUTRAL.
**Confidence:** HIGH.

## Claim 6: PUMP LONG is the best token (net +26.4%, WR 69.1%)
**Verdict: AGREE (descriptive) — with multiplicity caveat**
**Evidence:** Reproduces exactly: PUMP LONG n=97, WR 69.07%, net +26.43%, avg +0.272%/trade. It is #1 by net total among the 162 token cells (n≥5). It is also the only top cell with nominal significance: **t = 3.15, 95% CI [+0.103%, +0.442%]**.
**Caveat:** 162 token cells were screened; a Bonferroni-corrected threshold would be ~t>3.6, so it does not survive strict family-wise correction — though it is the strongest candidate in the dataset and worth forward-testing. Runner-ups (BANANA SHORT t=1.88, BLUR SHORT t=1.13) are not significant.
**Confidence:** MEDIUM-HIGH.

## Claim 7: squeeze_cross SHORT is the best signal (net +39.0%, WR 69.9%)
**Verdict: PARTIAL**
**Evidence:** Reproduces exactly (n=2,471, WR 69.93%, net +39.02%, avg +0.0158%/trade) and it is #1 by net total among signal cells.
**But:** the per-trade edge is tiny and **not statistically distinguishable from zero: t = 1.14, 95% CI [-0.011%, +0.043%]**. A +39% cumulative total spread over 2,471 trades is +0.016%/trade — a fraction of one rounding-level of the 0.14% cost assumption. Calling it "the best signal" is fine as an observed ranking; treating it as a verified keeper edge (recommendation #1) is not supported. It also happens to be the one big signal the gates never block (all 2,471 passed), so its noise-level edge flows straight into the live system.
**Confidence:** HIGH.

## Claim 8: ALL regimes are net-negative
**Verdict: AGREE**
**Evidence:** All 8 non-UNKNOWN regime cells reproduce exactly (e.g., SHORT HIGH -205.8%, LONG EXTREME -359.3%, etc.). The report excludes UNKNOWN per methodology; I checked the excluded cells — UNKNOWN LONG -404.3% (n=1,914) and UNKNOWN SHORT -0.05% (n=3,494, effectively zero). Including them changes nothing: no regime cell is positive. Robust.
**Confidence:** HIGH.

## Claim 9: Only 3 days net-positive in 18 days
**Verdict: PARTIAL**
**Evidence:** The report's daily table reproduces exactly (by `created_at`). Per-direction-day, there are 4 positive direction-days across 3 dates: Oct 12 SHORT +132.5%, Oct 18 LONG +9.0% & SHORT +36.5%, Oct 22 SHORT +111.2%.
**But:** by **combined daily PnL** (LONG+SHORT), only **Oct 18 (+45.5%)** — plus a 7-trade stub Oct 7 (+1.3%) — was net-positive. Oct 12 overall was **-7.4%** and Oct 22 overall was **-168.1%**. So "3 days net-positive" overstates it; the more accurate statement is "1 meaningful day out of 15 was net-positive." Also "18 days" is wrong — trades exist on only 15 days (Oct 8–10 have zero trades). The negative conclusion is directionally even stronger than the report claims.
**Confidence:** HIGH.

## Claim 10: MFE/MAE now measured over actual hold period
**Verdict: AGREE (code-verified) — with one unreproducible sub-table**
**Evidence:** Verified in `scripts/shadow_trader.py` lines 1244–1262: candles are filtered to `[entry_ts, exit_ts]` (`hold_candles = [c for c in candles if entry_ts_val <= c[0] <= exit_ts]`) before MFE/MAE are computed. The fix is correct — the old 24h-window behavior is gone. MFE/MAE sign conventions and the direction-level averages (SHORT MFE +2.821/MAE -1.919, LONG +1.898/-2.634) reproduce exactly.
**Residual caveats:** (a) fallback to the full 24h window if `hold_candles` is empty; (b) `exit_ts` defaults to entry+24h if an engine result lacks it; (c) the 303 `no_exit` "hold" rows get NULL MFE/MAE and are silently dropped from MFE tables.
**Unreproducible:** §5's specific table does not reproduce from the current DB under any natural filter I tried. Its hmacd_mtf SHORT row (n=64, WR 37.5%, MFE 9.54, MAE -1.096, ratio 8.70, avg -0.442%) vs actual DB (n=105, WR 61.9%, MFE 9.288, MAE -0.668, ratio 13.9, avg -0.088%). Same direction (high ratio, negative expectancy) but the numbers cannot be re-derived — likely a stale snapshot or an undocumented filter. This is a violation of the reproducibility rule.
**Confidence:** HIGH on the fix; LOW on §5's table.

---

## Overall Assessment

The report is **arithmetically excellent and methodologically weak**. Essentially every number in sections 1–4, 6–9, 11 reproduces to the decimal from my own queries — far better than the previous gross analysis. The MFE/MAE hold-period fix is real and verified in code. The core directional conclusion — **the shadow system loses money net of a realistic 0.14% round-trip cost, in every direction, regime, and nearly every day** — is robust and highly significant (t=-18.7), and the sign survives even a zero-slippage assumption.

But the report's *interpretive* layer repeatedly commits the exact sin it corrected: selection-on-outcome. PM Trail's 100% WR and Hard Max's 0% WR are definitional consequences of which exit fires first, not evidence about engine quality. "Only 3 net-positive signals" and "best token/signal" are top-of-list picks from 69 and 162 cells screened — and not one of the three signals clears t=1.96 (PUMP LONG comes closest at t=3.15). The gate "HELPING" conclusion fails a two-sample test (p≈0.054 vs passed trades; t=0.89 vs random). And the -1,938% headline silently includes -1,281% of losses from trades the system itself blocked — the system as configured lost -657%.

## Critical Issues Found

1. **Double-counting of blocked trades (most important).** -1,938% includes -1,280.7% from 10,751 gate-blocked counterfactuals. §1 says "the system is losing -1,938%" while §7 counts those same losses as savings. Realized-system figure: **-657.4% (n=6,805)**. Both numbers should always be shown, clearly separated.
2. **Exit-engine attribution is selection-on-outcome.** pm_trail can only fire in profit (code-verified, `shadow_trader.py:687`); hard_max only fires on losses. "PM Trail good / Hard Max bad" is a description of trade outcomes, not engine quality. Recommendations #2 and #3 (route more trades through PM Trail, reduce Hard Max) are causally unsupported and potentially dangerous — removing the -0.8% stop exposes trades to unbounded loss.
3. **No significance testing anywhere.** squeeze_cross SHORT (the flagship keeper signal) has t=1.14; CI spans zero. pump-chain-v6 SHORT and volume_breakout_short likewise. 69 signal cells and 162 token cells were screened with no multiplicity correction.
4. **§5 (MFE/MAE patterns table) is unreproducible** — hmacd row in particular (n=64/WR 37.5% vs actual n=105/WR 61.9%). Report cannot claim "fixed MFE/MAE" and ship a table its own data doesn't generate.
5. **"Only 3 net-positive days" overstates positives** — combined-day PnL was positive on only 1 meaningful day (Oct 18). Also "18 days" should be "15 trading days."
6. **"Only 3 net-positive signals" is false as stated** — 17 cells are positive; the qualifier is sample size, which should be said.
7. **33% of SHORT trades (3,516) have NULL `rsi_14`** and are silently dropped from the RSI table (I confirmed the report's <30 bucket matches only after excluding NULLs). Untouched by the report; worth surfacing in any RSI-based decision.
8. **873 closed rows excluded for NULL pnl** (EXPIRED/SHADOW_BYPASS/PENDING with no exit engine) — unquantified selection risk; direction unknown.
9. **CTX-GATE SHORT blocked +15.6%** — a gate that *cost* money on that slice; the text "ALL gates are HELPING" contradicts the report's own table.
10. **Fee-model sensitivity:** conclusions ride on the flat 0.14% (0.04 fee + 0.10 slippage) assumption applied to unleveraged moves. Sign is robust (breakeven all-in cost is 0.030%/trade), but the *magnitude* (-1,938% vs, say, -1,061% at half slippage) is assumption-driven and should be presented as a range.

## Recommendations

1. **Reissue headline as two numbers:** realized (gate-passed) system PnL **-657.4%** and counterfactual-if-all-signals-taken **-1,938%**. Never blend them.
2. **Delete causal exit-engine language.** Report exit-engine splits as descriptive only. Any claim about PM Trail vs Hard Max value requires a counterfactual simulation (what do the hard_max-stopped trades do if the stop is wider/moved to PM Trail?) — e.g., re-run the trade set through alternative exit configs, which the shadow infrastructure already computes per-engine (`exit_*_json` columns exist but only first-fire is analyzed).
3. **Add t-stats/CIs to every "net-positive" claim** and state the number of cells screened. None of the 3 signals survives; PUMP LONG (t=3.15) is the only cell worth a forward paper-trade test.
4. **Fix or remove §5** — regenerate from current DB with a documented filter.
5. **State "1 meaningful positive day of 15"** and "17 positive cells, 3 with n≥100" — accurate framings that strengthen, not weaken, the report's bearish conclusion.
6. **Quantify the excluded 873 rows** (even a bounds check: if all were wins vs all losses, how much changes?) and the NULL-rsi_14 third.
7. **Run a breakeven-cost sensitivity table** (slippage 0.05/0.10/0.15%) so readers see the conclusion's robustness instead of trusting one assumption.
8. The strongest actionable finding in the whole dataset is negative and clean: **expectancy -0.110%/trade (avg loss -0.754% × 48.8% vs avg win +0.504% × 51.2%)** — the loss-cutting is fine (losers exit <15m at -0.80%), the winners are too small. The RR problem, not the fee problem, is the primary bug; the fee just makes it undeniable.

*All queries reproducible from `brain/shadow_trades.db`; SQL used is embedded in the audit session of 2026-10-25.*
