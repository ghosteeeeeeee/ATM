# Independent Verdict: System-Wide Exit Asymmetry Report

**Auditor:** Independent (fresh read, no priming — all numbers re-derived from live SQL)
**Audited report:** `/root/.hermes/reports/exit-asymmetry-deep-dive-2026-10-31.md`
**Date:** 2026-10-31 (DB clock 17:18 UTC — same day as report compile, so the rolling 30d window is comparable)
**Sources:** PostgreSQL `brain` DB `trades` (108 cols) + SQLite `/root/.hermes/data/signals_hermes_runtime.db`
**Method:** Every claim re-run as raw SQL. Window used: `close_time > NOW() - INTERVAL '30 days' AND status='closed' AND pnl_usdt IS NOT NULL` (779 trades, MIN close_time in window = 2026-10-01 17:51).

**Overall: APPROVE WITH CHANGES.** The descriptive core is overwhelmingly accurate (6/10 claims verified exact to the decimal). Two material errors must be fixed before the CEO acts on it: (1) the headline net is **−$3.21, not −$0.26** (12× understated), and (2) the §3 "0.35% SL" simulation has the **loser-side logic inverted** — corrected, it actually *supports* a shadow-mode trial of tighter stops, opposite the report's ambivalent framing.

---

## Claim Verification

### Claim 1: "779 closed trades, 30d window"
Verdict: **AGREE**
Actual: `COUNT(*) = 779` — exact. DB `NOW()` = 2026-10-31 17:18 (matches report compile date, so the rolling window is comparable). MIN(close_time) in window = 2026-10-01 17:51; MAX = 2026-10-31 16:51. Total closed trades in DB ever: 6,214 (window is a clean subset). Window logic is correct.

### Claim 2: "Winners 364T avg +2.83% MFE 1.11% MAE 0.23%, Losers 415T avg −2.69% MFE 0.33% MAE 0.58%"
Verdict: **AGREE**
Actual: Winners 364T, avg pnl_pct +2.832%, MFE 1.114%, MAE 0.226% (WR 46.7%). Losers 415T, avg pnl_pct −2.687%, MFE 0.332%, MAE 0.584% (53.3%). All exact. Derived ratios also check out: MFE ratio 3.35x (report "3.4x" ✓), MAE ratio 2.58x ("2.5x" ✓), winners MFE/MAE 4.93 ("4.9x" ✓), losers 0.57 ("0.57x" ✓). Avg leverage 4.28/4.38 ✓ ("~equal"). Avg duration computed from open→close: 83 min winners / 74 min losers ✓ exact.

### Claim 3: "hard_max_loss: 148T 0%WR −$17.95"
Verdict: **AGREE**
Actual: 148T, 0 winners, SUM(pnl_usdt) = −$17.95 — exact. Also matches report's supporting stats: avg pnl_pct −3.751%, MFE 0.139%, MAE 0.704%.

### Claim 4: "profit-monster-trail: 246T 100%WR +$15.74"
Verdict: **PARTIAL**
Actual: The *winners-only slice* is exactly 246T, +$15.74, avg +1.992% ✓. BUT the exit type overall is **271T at 90.8% WR, +$15.29** — 25 of these trades lost money (−$0.45 total). The "100% WR" is an artifact of the report's winner-only cut in the "Profit Exits" table; the exit itself is not loss-free. Same pattern for atr_trail_hit: table shows "31T 100% +$7.51" but overall it is 38T at 81.6% WR, +$7.46 (7 losers). Valid descriptive cut, but the 100% labels overstate exit reliability.

### Claim 5: "Net: +$34.31 − $34.57 = −$0.26"
Verdict: **DISAGREE (material error)**
Actual:
- By trade sign: winners 364T = **+$34.13**, losers 415T = **−$37.34**, zero-PnL 6T = $0.00 → **NET = −$3.21**.
- By exit-group sign: positive groups 395T = +$31.25, negative groups 378T = −$34.46 → **NET = −$3.21** (consistent).
The report's subtotals reconcile with neither definition: its profit table (340T, +$34.31) sums winner-only slices but even that undercounts (actual winner-only total = 364T +$34.13; its "Other (11 types) 23T +$4.31" is actually 11 types / 47T / +$4.13). Its loss table (370T, −$34.57) sums exit-groups but is actually 378T / −$34.46 (its "Other (8 types) 21T −$1.33" is actually 7 types / 29T / −$1.24). 340 + 370 = 710 ≠ 779 — 69 trades unaccounted. The −$0.26 headline is an artifact of mixing two aggregations that each net to −$3.21 alone. **The true 30d net loss is −$3.21, 12× worse than reported.**

### Claim 6: "Winners cluster at low MAE: 141/364 dip less than 0.10%"
Verdict: **AGREE**
Actual: 141 winners with pnl_usdt>0 AND mae_pct<0.10 — exact. Full MAE band table also reproduced exactly (losers/winners): 0–0.10: 33/141, 0.10–0.25: 41/98, 0.25–0.50: 97/77, 0.50–0.75: 100/34, 0.75–1.00: 103/11, 1.00+: 35/1. (Band sums 409/362 vs 415/364: 8 trades have NULL mae_pct — negligible, doesn't skew.)

### Claim 7: "260/415 losers (62.7%) never showed 0.30% profit"
Verdict: **AGREE**
Actual: 260 losers with mfe_pct<0.30 — exact (138 in 0–0.10 + 122 in 0.10–0.30). MFE band table reproduced exactly (losers/winners): 0–0.10: 138/2, 0.10–0.30: 122/8, 0.30–0.50: 80/67, 0.50–1.00: 51/170, 1.00+: 18/116. Report's "286/364 winners (78.6%) showed 0.50%+" ✓ (170+116=286).

### Claim 8: "A SL at 0.35% would cut ~124 losers and spare ~279 winners"
Verdict: **DISAGREE (logic inverted on the loser side)**
Actual: A 0.35% stop triggers on trades whose MAE reaches 0.35%:
- **CUT: 296/415 losers (71.3%)** — MAE≥0.35, actual PnL −$26.34. (The report's "~124 cut" are actually the losers with MAE<0.35 — 113 of them — whom the SL would **never touch**; they keep their losses. The report counted the wrong side of the distribution.)
- **CUT: 79/364 winners (21.7%)** — MAE≥0.35, +$6.50 forgone. (The report's "~40 winners in the 0.25–0.35 zone cut" is also inverted: those are spared; the actually-cut winners sit in the 0.50%+ bands.)
- **SPARED: 283/364 winners (77.7%)** ✓ consistent with the report's "~279".
- 8 trades have NULL MAE (kept as-is).
Simulation (per-trade, SL loss = 0.35% × amount_usdt): spared trades keep +$23.03; MAE≥0.35 trades forced to −$17.63 (vs −$26.34 actual); → **simulated net ≈ +$5.50 vs actual −$3.21 → ~+$8.7 improvement per 30d, before fees/slippage.** Direction is the OPPOSITE of the report's "overlap kills it" framing — the corrected numbers make tightening *more* attractive, not less.
Caveats (why it stays fragile, not a green light): (a) the report's own §6 finding that recorded MAE under-records the true adverse move (15/28 volume-buildup losers) means a real SL would trigger on *more* trades than 375 — including possibly more winners; (b) fees/slippage on the additional exits are not modeled; (c) in-sample 30d. Ship in shadow mode per the automatic-implementation pattern, not live.

### Claim 9: "MFE/MAE < 1.0 signals are structurally losing"
Verdict: **PARTIAL**
Specific ratios re-derived — all match: hmacd_mtf-+ 0.59 (8T, −$0.46) ✓, volume-buildup+ 0.56 (5T, −$0.21) ✓, trend-ride+ 0.58 (7T, −$0.18) ✓, pump-chain+ 3.08 (report 3.07, rounding; 97T, +$1.99) ✓, pump-chain- 3.15 (65T, +$0.46) ✓, continuum-trend+ 2.04 ✓.
The *generalization* has counterexamples in the same window: `continuum_engine` (ratio 0.08 but +$0.08 profitable), `hl_copy_trader` (ratio 2.00 but −$0.20 losing), `volume-breakout-long+` (1.88 but −$0.20), `r2v2-long3` (1.03 but +$0.56). Additionally MFE/MAE is a *post-hoc outcome descriptor measured on the same 30d window* — not a validated predictive gate — and the three named "structurally losing" signals have n=5–8. Useful as a backtest diagnostic, but "regardless of WR" and "would have prevented deployment" are overstatements at this sample size.

### Claim 10: "1,445 volume-buildup signals, 70 executed (4.8%)"
Verdict: **PARTIAL**
Actual: `signals` table has exactly **1,445** rows with signal_type='volume_buildup_short' ✓. But:
- Date range is **2026-10-17 → 10-31**, not "Oct 11–31" (the signals table starts 2026-10-17).
- Decision split is **EXPIRED 1,445 / PENDING 0**, not "1,443 / 2".
- All 1,445 signals are **SHORT**; the 70 PostgreSQL volume-buildup trades are 65 SHORT + 5 LONG — the 5 LONG did not come from these signals (signal_history shows earlier volume_buildup_long activity). Same-window conversion is **57 short trades / 1,445 = 3.9%** (65/1,445 = 4.5% over 30d). The headline "4.8%" mixes directions and windows.
- Note: the SQLite `signals.executed` flag is NOT trade execution (1443/1445 have executed=1 with decision=EXPIRED/"compaction_stale_10min" — it is a compaction-processing flag). The report correctly avoided it and cross-referenced PG trades instead.

---

## Critical Findings

1. **[MATERIAL] Headline net PnL wrong (Claim 5):** report says −$0.26; actual sum(pnl_usdt) over the same 779 trades = **−$3.21** (winners +$34.13 / losers −$37.34). Cause: mixed aggregations (winner-only profit table vs exit-group loss table; 340+370=710≠779). Every per-row exit figure in both tables is individually correct — only the subtotals/net are broken. The problem is 12× bigger than the report tells the CEO.
2. **[MATERIAL] Claim 8 simulation inverted:** the ~124 losers "cut" are actually the low-MAE losers the SL would never touch. Correct: 296 losers + 79 winners cut, 283 winners + 113 losers spared. Corrected simulation is modestly **positive** (~+$8.7/30d before costs) — the report's framing ("overlap exists, no clean separation") undersells the upside and misstates the mechanism. Keep the overlap warning (79 winners genuinely get killed) but fix the numbers and direction.
3. **[PRESENTATION] "Profit Exits — 100% WR" is a cut artifact:** profit-monster-trail overall = 271T 90.8% WR (25 losers); atr_trail_hit = 38T 81.6% (7 losers). Label tables as "winning trades by exit reason" or show true exit-level WR.
4. **[MINOR] Claim 10 window mixing:** 1,445 SHORT-only signals (Oct 17–31) vs 70 trades of both directions (30d). Report "Oct 11–31" start date and "EXPIRED 1,443/PENDING 2" split are both wrong (actual 1445/0).
5. **[MINOR] Claim 9 overreach:** named ratios all correct, but "MFE/MAE <1.0 structurally losing / >2.0 structurally winning" has 4 counterexamples in-window, is in-sample, and rests on n=5–8 for the named signals.
6. **[MINOR] Rounding-level diffs:** volume-buildup losers avg −3.68% (report −3.72), MFE 0.19 (report 0.21) — immaterial; all other §6 volume-buildup figures exact (70T/60%WR/−$0.70; winners 42T +2.08% MAE 0.20; SHORT 65T 63.1% −$0.49; LONG 5T 20% −$0.21; max winner MAE 0.76 ✓; min loser MAE 0.09 ✓; HIGH regime 18T 77.8% +$0.37 ✓ exact).
7. **[NEW OBSERVATION — not in report] System-wide regime dependency inverts the volume-buildup pattern:** system-wide 30d — EXTREME 307T +$0.76 (WR 39.7%), NORMAL 255T −$1.05, **HIGH 175T −$3.20 (WR 53.7% — worst PnL despite highest WR)**, FLAT 36T +$0.20, NULL 6T +$0.08. The report's only regime claim was volume-buildup-specific (only HIGH profitable) and that is exact — but system-wide, HIGH is the *bleed* regime and EXTREME the *best*. Worth its own deep dive before any regime-conditional changes.
8. **Data-quality notes:** 7 NULL mfe_pct / 8 NULL mae_pct trades (incl. guardian_orphan, no_sl_tp, one NULL exit_reason) — negligible skew but they silently drop out of all band analyses. `fees` column is a JSON text blob, not numeric — will silently break naive SUM(fees) queries.

## Additional Checks (as requested)

1. **30d window correct?** ✓ DB clock 2026-10-31 17:18 = report date; MIN close_time in window 2026-10-01 17:51. (Rolling window — re-running later shifts all counts; re-verify before acting on day N+1.)
2. **NULL mfe/mae skew?** 7 NULL mfe / 8 NULL mae / 0 NULL pnl_pct — negligible; band tables match the report exactly.
3. **Regime dependency?** volume-buildup claim exact (HIGH 18T 77.8% +$0.37 only profitable; NORMAL 27T 48.1% −$0.66; EXTREME 25T 60% −$0.41). System-wide it inverts — see Finding 7.
4. **trail_arm_timeout 47T 31.9% WR −$1.00?** ✓ EXACT.
5. **atr_sl_hit 117T 0.9% WR −$9.79?** ✓ EXACT (116 losers + 1 winner; avg pnl_pct −2.737%, MAE 0.524%).
6. **Section 7 shadow data:** signal_outcomes verified — volume-buildup- 65T 64.6% −$0.19 (report 63%), volume-buildup+ 5T 20% −$0.22 ✓, volume-breakout-long+ 36T 41.7% −$0.01 ✓, volume-breakout-short- 4T 0% −$0.47 ✓.

## Recommendation

**APPROVE WITH CHANGES.**

Approve: the exit-asymmetry diagnosis itself is solid and reproducible — winner/loser profiles, MAE/MFE distributions, exit-level breakdowns, per-signal ratios, and the volume-buildup section all re-derive exactly. The prioritized recommendations (tighten hard_max_loss, evaluate atr_sl_hit, trail activation, MFE/MAE backtest screen, disable volume-buildup LONG) remain directionally supported.

Required before CEO acts:
1. Fix headline net: **−$3.21, not −$0.26** (and reconcile the 340/370 subtotals to 364/415 or re-label tables).
2. Fix §3 Claim 8: correct the cut/spare counts (296 losers + 79 winners cut; 283 winners spared) and state the corrected simulation is net-positive (~+$8.7/30d pre-costs) — which strengthens, not weakens, the case for a **shadow-mode** 0.35–0.50% MAE stop trial (ship via automatic-implementation staggered rollout; account for the MAE under-recording issue flagged in §6 before enforcing).
3. Re-label "100% WR" profit exits with true exit-level WR (profit-monster-trail 90.8%, atr_trail_hit 81.6%).
4. Correct Claim 10 wording: 1,445 SHORT signals Oct 17–31, 65 short trades, ~4.5% conversion; not "Oct 11–31 / 70 / 4.8%".
5. Soften Claim 9 to "diagnostic, in-sample, small-n" and note the counterexamples before using MFE/MAE as a deployment gate.
6. New: investigate the system-wide regime inversion (HIGH bleeds −$3.20 despite 53.7% WR; EXTREME earns +$0.76) — it contradicts the volume-buildup-specific regime story and may matter more than several listed fixes.

*All figures independently re-derived via live SQL on 2026-10-31 17:18–17:35 UTC. Reproduce with the queries implied in each claim section.*
