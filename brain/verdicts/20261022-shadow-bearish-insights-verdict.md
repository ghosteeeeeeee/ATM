# Independent Verdict — 20261022 Shadow Bearish Insights

**Auditor:** own-conclusions (fresh read, no priming)
**Audited:** `reports/20261022-shadow-bearish-insights.md`
**Data source:** `brain/shadow_trades.db` — queried directly, all numbers below come from my own SQL
**Audit time:** 2026-10-22 (~20:00 UTC). DB was still being written during the audit (grew 11,919 → 11,931 rows; Oct-22 rows arrive with ~5 min lag). Small drift vs the report is expected and observed; all report tables reproduce to within that drift.

**Method:** closed=1 AND first_exit_pnl_pct IS NOT NULL (n≈10,810; the report's tables sum to ~10,737, same population). Both GROSS (`first_exit_pnl_pct` ≡ `gross_pnl_pct`, verified: 0 differing rows) and NET (`net_pnl_pct` = gross − fee 0.04% − slippage 0.10%, shadow_trader.py:1242) were computed for every claim. Wilson CIs, two-proportion z-tests, and t-tests computed inline.

---

=== INDEPENDENT VERDICT ===

## Claim 1: SHORT dominates (+531.9%, WR 55.6% vs LONG −171.8%, WR 47.0%)

**Verdict: PARTIAL**

**Evidence:**
- Reproduces on GROSS basis: SHORT n=6,310, WR 55.7%, total +544.8%, avg +0.0863%; LONG n=4,500, WR 47.0%, total −173.5%, avg −0.0385%. (Report: +531.9%/−171.8% — drift consistent with live DB growth.)
- WR difference is statistically real: z=8.93, p=4.2e-19. SHORT avg > 0 gross: t=8.02, p<0.001. LONG avg < 0: t=−3.27.
- **NET of the system's own cost model (0.14%/trade), BOTH sides lose:** SHORT −338.6% (avg −0.054%), LONG −803.5% (avg −0.179%). Whole book: −1,142%. The report never mentions `net_pnl_pct` exists.
- **Date concentration:** Oct 22 alone contributes +383.5% = **70% of the entire SHORT gross total**. Excluding the top 3 SHORT days (Oct 12, 18, 22 — 3 of 13 trading days): SHORT flips to **−191.6% gross, WR 47.0%** while LONG is +9.4%, WR 50.0%. The dominance headline is a 3-day phenomenon. Excluding only Oct 22: SHORT +161.3% (WR 51.2%) vs LONG −16.1% — much weaker but still directional.
- The asymmetry direction is credible for a bear market; the magnitude and "crushing it" framing are not robust.

**Confidence: HIGH**

---

## Claim 2: squeeze_cross SHORT is best signal (WR 81.5%, +172.2%)

**Verdict: PARTIAL (numbers exact, but it is a 1-day sample)**

**Evidence:**
- Reproduces exactly: n=594, WR 81.5%, gross +173.6%, avg +0.292%. Net +90.5% (avg +0.152%) — **genuinely net-positive**, one of only a few net-positive books in the DB. Significance vs other SHORTs: z=13.29, p=2.7e-40. Wilson CI for WR: [78.2%, 84.4%].
- **100% of squeeze_cross trades (both directions) are dated 2026-10-22 only** (SHORT n=936 rows / 594 closed; LONG n=214 rows / 123 closed). The signal was deployed that day. There is zero out-of-sample, zero cross-regime evidence.
- The LONG-side contrast reproduces (n=123, WR 35.0%, gross −43.2%) — but same single day, so the "best SHORT / worst LONG = perfect bear-market example" framing compares two same-day samples of a brand-new signal.
- It is also 45% of Oct 22's entire SHORT gross total (+173.6 of +383.5), i.e. the top claim and the concentration problem compound.

**Confidence: HIGH (that numbers are right); LOW (that the ranking generalizes — 1 day of data)**

---

## Claim 3: hmacd SHORT MFE/MAE ratio 13.90 (MFE +9.288%, MAE −0.668%)

**Verdict: PARTIAL — numbers reproduce exactly, interpretation is wrong**

**Evidence:**
- Reproduces exactly: n=105, mean MFE=9.288, mean MAE=−0.668, ratio of means=13.90. Ratio of MEDIANS is 8.77 (mean skewed by 13 trades with MFE>15%).
- **The MFE/MAE are not measured over the trade's hold.** shadow_trader.py:1183 loads a fixed **24h candle window** (`entry_ts .. entry_ts+86400`) and lines 1246–1253 compute MFE/MAE as max(highs)/min(lows) over ALL loaded candles, regardless of when the exit engine fired. Proof in data: 40 hmacd LOSERS have MFE 5.3–18.0% on holds of 0–13 minutes (e.g. pnl −1.095%, MFE 17.49%, hold=0m). "Goes up 9.3%, down 0.7%" is not what the trade experiences — median hold is 11 minutes.
- The paper excursion was never captured: realized avg +0.052% gross, **gross total +5.4%, NET total −9.3%**. The signal loses money after costs. WR 61.9%.
- Sample is also nearly single-day: 104 of 105 trades on Oct 12 (Oct 11 has 1).
- A 13.90 MFE/MAE on 24h-window excursions with a 11-min median hold and negative net PnL does not support "top priority signal."

**Confidence: HIGH**

---

## Claim 4: SHORT wins in ALL volatility regimes except FLAT

**Verdict: PARTIAL**

**Evidence:**
- Reproduces on gross: SHORT UNKNOWN +252.3% (WR 82.6%), HIGH +166.8%, EXTREME +102.7%, NORMAL +23.2%, FLAT −0.2% (n=73).
- **"UNKNOWN" is not a regime — it is a data artifact.** 100% of UNKNOWN rows are dated 2026-10-22 and consist of exactly three signals deployed that day (squeeze_cross n=594, support_resistance n=156, bollinger_squeeze_short n=81) whose context carries `vol_regime='UNKNOWN'`. The best-performing "regime" is really "signals deployed today," which overlaps entirely with Claim 2's one-day sample.
- "Regime doesn't matter" is contradicted by the report's own table: avg PnL varies 12x across regimes (+0.304% UNKNOWN vs +0.024% NORMAL).
- **NET:** only UNKNOWN stays positive (+136%); HIGH ≈ −132%, EXTREME ≈ −222%, NORMAL ≈ −110% net. On the system's cost model, SHORT loses in every real regime.
- FLAT n=73 — too small to carry the "except FLAT" exception.

**Confidence: HIGH**

---

## Claim 5: CONFLUENCE-EXPIRY gate is HURTING SHORT (blocking +278.5%)

**Verdict: DISAGREE**

**Evidence:**
- The gross number reproduces: blocked SHORT n=5,001 (report 4,987), WR 52.3%, gross +284.0%.
- **NET, the blocked set loses −416.1%.** Under the system's own fee+slippage model, the gate SAVED the book ~417% by not taking these trades. Exempting SHORT from this gate — the report's #1 recommendation — is on this data a −417% expected move.
- **The gate is selecting, not just blocking.** PASSED shorts: n=1,197, WR 71.3%, avg +0.2054% gross, **net +78.3% (avg +0.065%)** — one of the only net-positive books in the DB. BLOCKED shorts: avg +0.0585% gross, net −0.0815%. The gate passes trades earning 3.5x more per trade and blocks marginal ones. "HURTING" inverts the gate's actual function.
- **Concentration:** Oct 12 (+220.8%) + Oct 18 (+132.0%) = +352.8% of the +284.0% total. The other 11 days sum to **−68.8%**. The claim is 2 days.
- **Counterfactual validity:** 8,810 of 9,496 blocked rows have decision=EXPIRED — signals the system explicitly deemed non-actionable (confluence never arrived / signal expired). Simulating fills at signal-time prices on expired signals is the same look-forward counterfactual structure the sibling report (`20261022-confluence-window-analysis.md`) is described in the report's own references as "debunked."
- The CTX-GATE "HURTING" verdicts rest on n=56 (SHORT) — not meaningful.

**Confidence: HIGH**

---

## Claim 6: PUMP LONG is the only strong LONG signal (WR 75.3%, +40.3%)

**Verdict: PARTIAL (strongest LONG book, yes; "only strong signal" no)**

**Evidence:**
- Reproduces exactly: n=77, WR 75.3%, gross +40.3%, avg +0.524%. **Net +29.6%** — it is the only meaningfully net-positive LONG token with n≥30 (next: HYPER +3.4%, DOGE +1.2%). Wilson CI [64.6%, 83.6%].
- It is a TOKEN, not a signal. The report's own text ("the only strong LONG **signal**") conflates the two. Drivers: ichimoku_long (n=48, WR 79.2%, +23.0%) and hh_hl_breakout_long (n=8, 100%, +17.5%).
- "Only strong" is overstated: DOGE LONG WR 67.3% (n=55), SYRUP LONG 62.0% (n=50) — smaller but comparable; by signal, oversold_bounce_long WR 68.9% (n=61).
- Concentration: 52 of 77 trades are Oct 20–21. Still, unlike claims 2–4 this one survives the net test, which is the most that can be said for any LONG finding here.

**Confidence: MEDIUM-HIGH**

---

## Claim 7: Overbought SHORT works (WR 61.0% at RSI > 70)

**Verdict: PARTIAL (win-rate claim yes, money claim no)**

**Evidence:**
- Reproduces: n=388, WR 61.1%, CI [56.1%, 65.8%]. Monotonic WR decline as RSI falls (61.1 → 58.4 → 54.5 → 50.6 → 50.0 → 47.6) — a real, orderly pattern.
- Statistically significant: vs RSI 40–50 z=3.52, p=0.0004; vs all other SHORTs z=2.20, p=0.028.
- **But avg PnL at RSI>70 is +0.0387% gross — BELOW the SHORT average (+0.0863%) and below the 30–40 (+0.0709%) and 50–60 (+0.0697%) bands.** Higher WR comes with smaller wins: RSI>70 shorts win more often but earn less per trade.
- **NET: −0.101%/trade** — worse than every band except 40–50. All six SHORT RSI bands are net-negative. "The edge is at the extremes" holds for win rate only, not for expectancy.

**Confidence: HIGH**

---

## Claim 8: Winners hold longer (3–8h = +1.167% avg for SHORT)

**Verdict: PARTIAL — table reproduces exactly; the inference is selection-on-outcome**

**Evidence:**
- Reproduces exactly: WIN 3–8h n=316 avg +1.1673%; LOSS <15m n=690 avg −0.7296%; losers >8h n=17 avg −0.1909%.
- This table CONDITIONS ON OUTCOME then observes hold time — and hold time is determined by the exit engine's reaction to the price path. Trades that go strongly favorable trail out slowly (trail_sl/atr_trail = long holds); trades that reverse get stopped fast. "Winners hold longer" is largely mechanical, not a discoverable edge. You cannot "extend hold time for profitable SHORTs" (recommendation #8) because profitability is unknown at hold-time-setting time.
- The honest unconditional view: <15m n=1,506 avg −0.014% gross/−0.154% net; 15–60m n=2,643 −0.021%/−0.161%; 1–3h +0.198%/+0.058%; **3–8h n=500 +0.558% gross/+0.418% net** (best bucket, survives costs); >8h n=60 +0.423%/+0.283%. Fast exits (<1h, 66% of trades) are the loss engine. That is a real observation, but it is about the SL/exit side, not about "letting winners run" — and it is already partially the subject of the referenced SL-sweep report.
- The "losers >8h only −0.191%" reassurance rests on n=17.

**Confidence: HIGH**

---

## Overall Assessment

**The report's arithmetic is honest — I reproduced every table to within live-DB drift. The failure mode is interpretation and omitted context, in four systemic ways:**

1. **Everything is GROSS.** `first_exit_pnl_pct` ≡ `gross_pnl_pct` exactly. The DB's own `net_pnl_pct` (fee 0.04% + slippage 0.10% = 0.14%/trade, hardcoded in shadow_trader.py:1242) turns the entire book from +371% to **−1,142%**. SHORT flips −338.6%, LONG −803.5%. The only net-positive books in the whole DB: passed-gate SHORT (+78.3%), squeeze_cross SHORT (+90.5%), PUMP LONG (+29.6%), 3–8h hold bucket (+209.1%). Every "boost / allocate 2:1 / exempt from gate" recommendation is gross-based, and several reverse sign net.
2. **Temporal concentration / no out-of-sample.** Oct 22 = 70% of SHORT gross. Remove 3 of 13 days (Oct 12, 18, 22) and SHORT is −191.6% with WR BELOW LONG's. squeeze_cross, bollinger_squeeze_short = 100% Oct 22. hmacd = 99% Oct 12. "UNKNOWN regime" = 100% Oct 22. Four of the report's headline findings are the same 1–3 days seen through different group-bys.
3. **Selection-on-outcome / invalid counterfactuals.** Claim 8 conditions on outcome (tautological). Claim 5 treats fills on decision=EXPIRED signals as an actionable counterfactual — the identical structure the report's own sibling analysis is labeled "debunked" for.
4. **MFE/MAE misinterpretation.** MFE/MAE are computed over a fixed 24h window (shadow_trader.py:1183, 1246–1253), not the hold — provable from losers with 17% "MFE" on 0-minute holds. Ratios like 13.90 describe the token's next-day range, not the trade.

Where the report is genuinely right and useful: SHORT-vs-LONG direction asymmetry is statistically real on gross (p=4e-19) and consistent with the bear regime; PUMP LONG is the one LONG finding that survives net; squeeze_cross SHORT is net-positive; the RSI→WR monotonicity is real; and the passed-gate SHORT book (+78.3% net, WR 71.3%) is the actual crown jewel — which the report's own framing obscures by labeling the gate that produced it "HURTING."

## Critical Issues Found

- **C1 (critical):** Report presents only gross PnL; `net_pnl_pct` reverses the book's sign and Claim 5's recommendation by −417%.
- **C2 (critical):** Claim 5's #1 recommendation (exempt SHORT from CONFLUENCE-EXPIRY) would, on the system's cost model, add a net-losing, 3.5x-lower-quality trade set; the gate currently produces the best net-positive book in the DB.
- **C3 (major):** squeeze_cross ("best signal") has exactly one day of data; boosting allocation on it is unvalidated.
- **C4 (major):** hmacd "monster" is net −9.3% and its MFE/MAE is a 24h-window artifact, not trade excursion.
- **C5 (major):** "UNKNOWN regime" is a deployment-day data artifact being reported as a market regime.
- **C6 (minor):** Report header says "11,919 shadow trades" but all tables use ~10,737 (closed with pnl) — population never stated.
- **C7 (minor):** Daily table (section 2) shows 7 of 13 days without saying so; internal n inconsistency for squeeze_cross (589 vs 580 between sections 3 and 5).
- **Sideways find:** `mfe_4h`/`mae_4h` columns are 100% NULL across all 10,719 closed rows — dead columns or a broken backfill; and `signal_id` on Oct-22 rows contains text values (`shadow_20261022200028_SAGA`) in an INTEGER column (SQLite tolerates it, but anything doing numeric comparisons on signal_id will silently misbehave).

## Recommendations

1. **Re-run this report on `net_pnl_pct`** before any allocation change. If 0.10% slippage is considered too pessimistic, publish a fee-only sensitivity (0.04%): SHORT = +292% gross-of-slippage, LONG = −353% — the point is the report must show the cost assumption, not silently pick the most favorable column.
2. **Do NOT exempt SHORT from CONFLUENCE-EXPIRY** on this data. Instead, promote the finding that PASSED shorts (n=1,197, WR 71.3%, net +78.3%) are the healthiest book — and investigate what the gate is correctly filtering, rather than calling it harmful.
3. **Add per-signal date-coverage requirements to signal ranking** (e.g. min 5 distinct days before a signal may be called "best"). Label squeeze_cross/bollinger_squeeze_short/hmacd as "1-day, unvalidated" in any ranking table.
4. **Fix or relabel MFE/MAE** in shadow_trader.py: compute over the actual hold (entry_ts → first_exit_ts), or rename the columns to `window_mfe_24h` so ratios are not read as trade properties. Recompute Claim 3's conclusion after.
5. **Backfill `vol_regime` for Oct-22 signals** or exclude UNKNOWN from regime tables entirely.
6. **Require an out-of-sample split** (derive on days 1–10, verify on days 11–13) in any "insights" report before recommendations are made — on this data the top-3-day exclusion would have flipped two of the seven "What's Working" items.
7. Worth keeping from the report: PUMP LONG protection, RSI-extreme win-rate observation (as WR, not expectancy), and the fast-exit (<1h) loss-engine observation — each survives net and should feed the SL/exit work rather than the allocation work.

**Verdict summary:** 0 AGREE-as-stated, 6 PARTIAL, 1 DISAGREE (Claim 5), with Claim 3's interpretation and Claim 5's actionable conclusion rejected outright. The report is a competent gross-PnL description of 1–3 unusual trading days; it is not yet a basis for allocation or gate changes.
