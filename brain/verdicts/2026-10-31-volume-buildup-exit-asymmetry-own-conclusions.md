# Independent Verdict: volume-buildup Exit Asymmetry Report

**Auditor:** independent (fresh, from-scratch verification — no trust in report numbers)
**Date:** 2026-10-31
**Report audited:** `/root/.hermes/reports/volume-buildup-exit-asymmetry-2026-10-31.md`
**Sources queried directly:** PostgreSQL `brain.trades` (70 live closed volume-buildup trades) + SQLite `signals_hermes_runtime.db` (`signals`, `signal_outcomes`)

**Bottom line:** The report's *descriptive* statistics are accurate — I reproduced claims 1, 2, 3, 4, 6, 7 to the decimal from live SQL. But the *prescriptive* core — the flagship "0.50% SL is safe, cuts ALL losers, keeps ALL winners, breakeven 26%" — is **overstated and factually wrong on its key number.** Max winner MAE is **0.76%**, not ~0.50%; the separation at 0.50% is **not clean** (2 winners killed, 4 losers spared), and the MAE metric itself **under-reports true adverse excursion**, so a SL-trigger model built on it is unreliable. Breakeven is **19.4%**, not 26%. Directionally the report has a point (SL is too wide vs winner MAE); the specific 0.50% recommendation must be corrected before acting.

---

## Claim Verification

### Claim 1: "70 live closed trades, 60% WR, −$0.70 total PnL"
**Verdict: AGREE**
- Actual: 70 trades, 42 winners (60.0%), SUM(pnl_usdt) = −$0.7000. All `paper=false`.
- Confirmed 70 is the **complete** live set (no older volume-buildup trades excluded).
- Claimed: 70, 60%, −$0.70. ✓ Exact match.

### Claim 2: "profit-monster-trail: 43T 98% WR +$2.39"
**Verdict: AGREE**
- Actual: 43 trades, 42 winners (97.7% ≈ 98%), +$2.39, avg PnL% +1.99, avg MFE +0.84, avg MAE +0.21.
- Claimed: 43, 98%, +$2.39. ✓ (Note: 1 of the 43 is actually a *loss* — "captures ALL 42 winners" is right, but it is not a clean 43/43.)
- Full exit-type table in report §1 reproduces exactly (hard_max_loss 11/−$1.25, cut-loser 8/−$1.13, stale_exit 2/−$0.38, atr_sl_hit 3/−$0.26, ugb_pt 3/−$0.07). ✓

### Claim 3: "Winner avg MAE = 0.20%, Loser avg MAE = 0.89%"
**Verdict: AGREE**
- Actual: winner MAE 0.1987% (≈0.20%), loser MAE 0.8862% (≈0.89%). Winner MFE 0.8433, loser MFE 0.1920.
- Winner avg PnL% +2.0775 (≈+2.08 ✓); loser avg PnL% **−3.6801** vs claimed −3.72 (0.04pp rounding diff — immaterial).
- Claimed MAE figures: ✓. The 0.20% is an **AVERAGE**, not a max — see Claim 5/10 where the report itself conflates the two.

### Claim 4: "SL averages 2.09% from entry"
**Verdict: AGREE**
- Actual: AVG(|entry−SL|/entry×100) = **2.0853%**; range 0.3529%–2.5001%; n=70 (0 NULL stop_loss).
- Claimed: 2.09%, range 0.35–2.50. ✓ Exact.

### Claim 5: "A SL at 0.50% would cut ALL losers but keep ALL winners" — **THE KEY CLAIM**
**Verdict: DISAGREE**
- Actual **max winner MAE = 0.7627%** (> 0.50%). Actual **min loser MAE = 0.0930%** (< 0.50%).
- There **IS overlap.** Concrete counts:
  - **2 winners have MAE > 0.50%** → a 0.50% SL would **kill** them (MAE 0.7627% PnL +2.67% +$0.06; MAE 0.7425% PnL +0.50% +$0.02).
  - **4 losers have MAE < 0.50%** → a 0.50% SL would **NOT** stop them (they exited via ugb_pt / hard_max_loss before reaching 0.50% recorded adverse). Two of them still lost big (−4.70% and −1.88% PnL).
- The claim's premise ("avg loser MAE 0.89% > 0.50% ⇒ cuts ALL") is a logical error: an *average* above 0.50% does not mean *every* loser is above 0.50%. Four are not. Same for winners: an *average* 0.20% below 0.50% does not mean every winner is below — two are not.
- **The clean separation the report asserts does not exist in the data.**

### Claim 6: "Only 6/28 losers ever showed 0.3%+ profit"
**Verdict: AGREE**
- Actual: losers with MFE≥0.3 = **6**; ≥0.5 = **1**; ≥1.0 = **0**; avg loser MFE 0.1920. n=28.
- Claimed: 6/28, 1/28, 0/28. ✓ Exact.

### Claim 7: "LONG side: 5T 20% WR −$0.21"
**Verdict: AGREE (but n=5 is not actionable)**
- Actual (PostgreSQL): LONG 5 trades, 1 winner (20%), −$0.21. ✓
- Confirmed **5 is all we have** — shadow `signal_outcomes` also shows exactly 5 LONG rows. 5 trades carry **no statistical weight**; the report's "disable LONG" recommendation happens to be reasonable but is not supported by n=5.

### Claim 8: "1,444 total signals fired, 1,443 EXPIRED, 70 executed"
**Verdict: PARTIAL**
- Actual (`signals` where source LIKE '%volume-buildup%'):
  - **Total = 1,445** (report says 1,444 — off by one).
  - Decision: **EXPIRED 1,443** ✓, **PENDING 2** — there is **no "SKIPPED"** decision in the data (report's "1 SKIPPED" is wrong; it's 2 PENDING).
  - `executed` flag sums to **1,441**, NOT 70. The "70 executed" figure is **not** the executed flag — it equals the row count of `signal_outcomes` / live closed trades. The report conflates two different "executed" semantics without flagging it.
- EXPIRED count ✓; the other three numbers (total, SKIPPED, executed) are wrong or mislabeled. The 4.9% execution-rate framing (70/1444) survives only if you accept 70 = shadow-outcome count.

### Claim 9: "Breakeven WR with 0.50% SL drops to ~26%"
**Verdict: DISAGREE**
- Using the report's **own stated inputs** (avg winner +2.08%, avg loser −0.50%): breakeven = 0.50 / (2.08 + 0.50) = **19.4%**, not 26%.
- **Leverage does NOT change breakeven WR** — it scales both winner and loser equally, so the ratio is scale-invariant. The report's implicit "leverage is why it's 26%" reasoning does not hold; 19.4% is correct regardless of leverage.
- 26% is not reproducible from the report's numbers. (You only reach ~26% by pairing a −0.72% loser with +2.08%, or ~49% by treating the loser as −2.0% leverage-inclusive while (inconsistently) leaving the winner at +2.08%. None is internally consistent.)
- The *direction* (breakeven falls well below the actual 60% WR) is right — but it rests on the false premise that the 0.50% SL keeps all winners (Claim 5). Since it kills 2 winners and spares 4 losers, the "actual 60% = strongly positive" conclusion is **not reliable** as stated.

### Claim 10: "Winner MAE max is ~0.50%, 0.50% SL is safe" — most critical
**Verdict: DISAGREE**
- Actual **MAX winner MAE = 0.7627%** — **not ~0.50%.** P95 winner MAE = 0.4758%.
- The report's §9 risk line "Winner MAE max is ~0.50%, 0.50% SL is safe with 0.30% buffer" is **false on both counts**: the max is 0.76% (so a 0.50% SL cuts at least 2 winners), and the "buffer" is actually **negative** (0.50 − 0.76 = −0.26%).
- No version of "0.50% is safe for all winners" is supported. At best, ~95% of winners stay under 0.48%; the tail does not.

---

## Critical Claim 5 Analysis

**Is the 0.50% SL safe for winners? What's the actual max winner MAE?**

No — and **0.7627%**.

1. **Two real winners dip past 0.50%** (max 0.7627%, second 0.7425%). Under a 0.50% SL these become losses. The report's own risk assessment ("max is ~0.50%, safe with 0.30% buffer") directly contradicts the actual data — the max is 0.76%, and there is no buffer.

2. **Four losers never reach 0.50% recorded MAE**, so a 0.50% SL would not fire on them; they'd keep bleeding via their real exits (one still lost −4.70%). "Cuts ALL losers" is false.

3. **MAE is an unreliable SL-trigger proxy.** In **15 of 28 losers**, recorded `mae_pct` is *less* than the trade's final adverse move `|pnl_pct|/leverage` (e.g. −7.10% at 5x = −1.42% raw adverse, but recorded MAE only 1.107%; −4.70%/0.42% recorded MAE). If MAE under-states how far price actually went against the entry, then a real 0.50% SL would trip **more often** than a MAE-snapshot model predicts — killing more winners than the 2 identified. The MAE column is not a faithful record of true max adverse excursion, which undermines the whole "winner MAE 0.20% ⇒ SL at 0.50% never fires on winners" argument.

4. **Counterfactual (directional only, heavily caveated):** Using recorded MAE as the SL trigger and `pnl_pct = −0.50 × leverage` for stopped trades, a 0.50% SL flips total from ≈ **−15.8% to ≈ +25.2%** (pnl_pct sum) and WR from 60% → ~57% (40 kept winners / 70). This *directionally* supports "tightening helps," **but** it is computed on the same under-reported MAE field, so treat it as an upper bound, not a forecast. The honest read: tightening the SL from 2.09% is *plausible* as an improvement; the precise 0.50% level and "safe for all winners" claim are **not** established.

**Verdict on the key claim: FALSE as stated.** There is MAE overlap on both sides (2 winners killed, 4 losers spared), and the underlying MAE metric is unreliable. Any live 0.50% SL must be shipped in shadow mode with a real backtest, not on this MAE snapshot.

---

## Additional Checks

1. **NULL skew:** None. `mae_pct`, `mfe_pct`, `pnl_pct`, `stop_loss` all have **0 NULLs** across the 70 trades. Averages are clean.
2. **14d window:** Correct. MIN open 2026-10-12 02:33, MAX 2026-10-31 14:19; 14 distinct trading days; 70 trades is the complete live set (no truncation). Daily WR matches (Oct 25 = 6/6 = 100%; Oct 30 = 10/15 = 67%).
3. **Regime dependency — the report is WRONG to claim robustness.** By `volatility_regime`:
   - NORMAL: 27T, 13W (48%), **−$0.66** (largest bucket, net negative)
   - EXTREME: 25T, 15W (60%), −$0.41
   - HIGH: 18T, 14W (78%), **+$0.37** (only profitable regime)
   The report's §9 "works in both trending and choppy periods" is day-based, not regime-based, and is **contradicted** by the regime split. The signal only makes money in HIGH regime and bleeds in NORMAL (its most common regime). This is a material omission.
4. **LONG side:** Exactly 5 trades (both PG and shadow confirm). n=5 — statistically meaningless; "disable" is defensible but not evidence-driven.
5. **Source-consistency flag:** Shadow `signal_outcomes` SHORT PnL = −$0.19 but PostgreSQL SHORT PnL = −$0.49. The report mixes shadow and PG figures across sections without flagging the accounting difference. Not an error per se, but noted.
6. **Minor prose slips:** report §1 says "other 5 exit types account for all 28 losers" — actually 27 (1 loser sits inside profit-monster-trail); the table itself is correct.

---

## Recommendation

**APPROVE WITH CHANGES.**

The report is well-sourced and its *descriptive* analytics are trustworthy (claims 1, 2, 3, 4, 6, 7 reproduce exactly; exit-type/leverage/position-size/duration tables all check out). The diagnosis — "exits are asymmetric, SL is too wide relative to winner MAE" — is directionally sound.

But the **prescriptive core is not ready to act on.** Before Priority 1 (0.50% SL) ships:

1. **Correct the key number:** max winner MAE is **0.76%**, not ~0.50%; remove the false "0.30% safe buffer" line. Acknowledge **2 winners would be killed** and **4 losers would not be cut** — the separation is not clean.
2. **Fix breakeven math:** 0.50/(2.08+0.50) = **19.4%**, not 26%; state explicitly that leverage does not change breakeven.
3. **Flag MAE unreliability:** MAE under-reports true adverse in >50% of losers — a MAE-snapshot SL simulation is an optimistic upper bound. Do a genuine backtest (or ship the SL in **shadow mode** via the `automatic-implementation` stagger pattern) before enforcing.
4. **Drop or rework the "no regime dependency" claim:** NORMAL regime (the largest bucket) is −$0.66 / 48% WR. Any SL change should be evaluated per-regime, and the regime-robustness line in §9 should be removed.
5. **Fix Claim 8 numbers:** 1,445 total (not 1,444), 2 PENDING (not 1 SKIPPED), and clarify "70 executed" = shadow outcomes, not the `executed` flag (which is 1,441).

Priority 3 (keep profit-monster-trail) and Priority 2 (LONG is too small to trust — n=5) are fine. Priority 4 (evaluate rr_engine) is reasonable. **Priority 1 must not be enforced live on this evidence.**
