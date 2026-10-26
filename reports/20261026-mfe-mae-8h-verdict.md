# MFE/MAE 8h Analysis — Last 100 Trades (Verdict Report)

**Date:** 2026-10-26 · **Directive:** T — "look at the last 100 trades, their MFE/MAE data
over 8 hours since opened, how many were stopped early with a bigger move following our
exit, and what we'd need to survive the MAE if there was a bigger MFE — be thorough,
re-verify everything"
**Raw output:** `reports/20261026-mfe-mae-8h-last100.md` · **Script:** `analysis/mfe_mae_8h.py`
(committed, deterministic, read-only) · **Independent audit:** `brain/verdicts/` (own-conclusions)

**TLDR:** Re-verified 96/100 trades (3× reproducible runs + 5 independent raw-SQL spot
checks — including GRASS +12.5% and WLD +10.1% outliers, both real, not data gaps).
**74% of in-window exits were followed by a bigger move** (median foregone 1.83pp; $18.40
gross foregone vs +$0.75 realized at micro sizes). The "survive the MAE" answer: **SL
≥ ~1.2% + CUT_LOSER coupled to ~−6% at 5x (or drop to ≤3x)** — the coupled trial the CEO
deferred after the SL sweep.

---

## Method

- Window = [open_time, open_time + 8h] for every trade regardless of exit.
- Extremes from the **union of candles_1m + candles_5m** (candles.db) — handles partial
  windows with gaps.
- fav_at_exit from trade prices; fav_after = best entry-based favorable level among
  candles **starting at/after** exit (the exit-minute straddle candle is included by
  code — audit's strict variant showed 0 classification flips either way).
- *Bigger move followed* (v2) = fav_after ≥ max(fav_at_exit, 0) + T.
- 96/100 analyzed. **Amended per own-conclusions audit:** the 4 skipped (DOT/BLUR/INJ/ALT)
  were **not data gaps** — they were the 4 NEWEST trades whose 8h windows had not finished
  elapsing at run time (candle counts = elapsed window minutes, minute-exact). ~10 more
  partial-window trades were silently INCLUDED (only RENDER flagged). Findings hold on the
  auditor's CLEAN n=88 fully-elapsed cohort (73% at T=0.3).
- HML cap in price terms = 4% account / leverage (CUT_LOSER_PNL = −4%).

## 1. Exit-reason census (n=96)

| Exit rule | n | wins | PnL |
|---|---:|---:|---:|
| profit-monster-trail | 40 | 37 | **+$2.37** |
| hard_max_loss (HML) | 11 | 0 | −$1.36 |
| atr_sl_hit | 10 | 0 | −$0.59 |
| ugb_pt | 9 | 6 | +$0.24 |
| trail_arm_timeout | 9 | 2 | −$0.20 |
| hard_sl / stale / max-hold / manual / rr / atr-trail | 17 | 6 | −$0.53 |

## 2. Stopped early + bigger move after exit

**94 exits inside the window** (2 held past 8h): 52 profitable / 42 stopped-out.

| Threshold (beyond capture) | Count | winners giving up tail / losers it went without us |
|---|---|---|
| ≥0.2pp | 76/94 (81%) | 47 / 29 |
| **≥0.3pp** | **70/94 (74%)** | **44 / 26** |
| ≥0.5pp | 61/94 (65%) | 38 / 23 |

- **Stopped-out 42:** 26 (62%) would have been ≥+0.3% post-exit; **18 (43%) ≥+1.0%**;
  **10 (24%) ≥+2.0%** — 1 in 4 stops followed by a ≥2% move our way within 8h.
- **Winners:** 24/52 gave up ≥1pp of tail after exit.
- **Magnitude:** median foregone **1.83pp**, p75 2.81pp, p90 4.08pp, max 13.24pp.
- **Dollars (today's ~$11–33 notionals):** foregone gross $19.15 vs realized $0.75 net →
  **$18.40 gap across 70 trades** — scales linearly with size.
- By exit rule @T=0.3: profit-monster-trail 35, HML 7, ugb_pt 7, atr_sl 7,
  arm-timeout 6, hard_sl 3, other 5.
- Split-half stability: older 34/47 vs newer 36/47.

## 3. What we'd need to survive the MAE for the bigger MFE

Cohort MFE ≥0.8% in 8h: **n=64** (40 with MFE ≥1.5%).

| Requirement | Value |
|---|---|
| MAE before the peak (p50 / p75 / p90) | **0.57% / 1.17% / 1.62%** price (max 4.76%) |
| Actual per-trade SLs (p50 / p75) | 0.73% / 2.30% — **exit-time snapshot: stop_loss is trailing-rewritten during the trade (63/65 atr_managed)**, not necessarily the stop in force pre-peak |
| What kills first today (5x → HML = 0.8% price) | **AMENDED per audit:** raw counts SL 24/64 · HML 13/64 **overlap 9–10 (partition never computed; true SL-first ≈19, HML-first ≈8)** · survivable **36–51 of 64** (36 with exit-snapshot stops; 51 with initial 1.5% stops: SL-first 0, HML-first 14) |
| Max leverage keeping HML (−4% acct) intact | p50 MAE → **≤7x** · p75 → **≤3.4x** · p90 → **≤2.5x** |
| Peak timing | p50 **~4.6h** after open, p75 ~6.7h (vs soft-trail 2h, max-hold 1–2h — time exits structurally can't reach an 8h peak) |

**Scenario — whole cohort, upper bound** (non-stopped ride to peak, gross of fees):

| Stop + coupled HML @5x | Scenario gross | Stops hit | Worst single |
|---|---|---|---|
| actual (as traded, net) | **+$1.68** | — | — |
| SL 0.80% + CUT_LOSER 4% | +$9.61 | 23/64 | −$0.18 |
| SL 1.17% + CUT_LOSER 5.8% | +$12.95 | 15/64 | −$0.26 |
| SL 1.62% + CUT_LOSER 8.1% | +$16.35 | 6/64 | −$0.18 |

## 4. The answer — what would we need

1. **SL floor ~0.6–0.8%** — today's p50 SL (0.73%) covers only ~half the required MAE.
2. **Survive the p75 ride (1.17%): either ≤3x leverage under the current −4% HML, or
   couple CUT_LOSER −4%→≈−6% with the wider SL.** At 5x, HML caps the stop at 0.8% —
   anything wider is dead code (same finding as the CEO SL-sweep verdict).
3. This data **supports running the coupled CUT_LOSER + ATR_SL shadow trial** the CEO
   deferred — as a shadow, not a live flip. Exits genuinely protect too: 42 stopped
   losers include real saves; UGB backtest baseline was −7.24pp *without* exits.
4. Time-based exits (soft-trail 2h, max-hold) are structurally incompatible with peaks
   that arrive p50 ~4.6h — flag for the same trial.

## Verification appendix (THE PATTERN checklist)

- **Reproducible:** 3 full runs identical **given the same cohort — determinism, not
  stability**: the cohort is re-selected via NOW() each run, so trades age in/out between
  runs (ALT's "candle drift" 235→238 was its still-elapsing window, per audit).
- **Independent spot checks** (separate raw-SQL code path): BTC ugb_pt fav_after 0.95 vs
  0.97 ✓ · ZRO MAE_to_peak 4.76 ✓ · DYDX 1.97 ✓ · WLD 10.07 and GRASS 12.50 reconcile
  arithmetically (entry-base = cap + exit-base; both 480/480 candles — moves are real;
  auditor re-verified 0 gaps, peaks hours after exit).
- **Self-audit caught a definition bug** (v1 counted stopped-out losers on trivial ticks);
  v1 numbers discarded, v2 used throughout.
- **Split-half:** 34/47 vs 36/47 — present in both halves. No formal p-value claimed:
  "exit before the 8h max" is near-tautological; the load-bearing stats are magnitudes
  and the loser-continuation tail.
- **Caveats:** closed trades only (open-position survivorship); mixed windows (see amended
  method note — 4 unfinished + ~10 truncated, only RENDER flagged); fav/MFE gross of fees;
  scenario 4b exits at peak → upper bound (auditor: also assumes an entirely different exit
  rule than PM-trail, gross-vs-net mixed); cohort conditioned on MFE≥0.8% (T's premise —
  outcome-selection if treated as policy); **foregone p90 tail is unstable at n≈70
  (4.08 vs audit's 3.64 — single-trade rank flip; median/p75/max stable)**.

## Independent audit (own-conclusions skill) — COMPLETED

- **Verdict file:** `brain/verdicts/20261026-mfe-mae-8h-own-conclusions.md`
- **Auditor's own code:** `analysis/audit_own_mfe_mae.py` (from scratch, 3 cohort variants:
  FULL n=99 / MATCHED / CLEAN n=88 fully-elapsed; second code path raw-SQL spot checks)
- **Result: AGREE on 7 claims (2,3,5,7,8,10,11), PARTIAL on 4 (1,4,6,9), DISAGREE: none.**
  Headline reproduces: 73–74% bigger-move-after-exit; loser-tail tiers 26/23/18/10 exact;
  GRASS/WLD outliers real on 480/480 gap-free candles; leverage math exact against live
  HML=−4%/lev; amount_usdt confirmed notional (median residual $0.002); scenario reproduces
  (+9.52/24 vs +9.61/23; 15/15 and 6/6 stops exact).
- **Amendments applied to this report (as demanded):** claim-1 framing (recency ≠ data
  loss) and claim-6 SL attribution (trailing-rewritten stops; overlapping kill sets;
  survivable quoted as **36–51**, not 36). p90 instability and determinism-vs-stability
  noted above.
- **New ticket from audit:** **BUG-065** — `HML_VOL_ATR_MULT` EXTREME-regime vol-floor in
  `position_manager.py:3747-3759` is dead code (capped to the account limit, then
  re-compared to itself → the widening can never fire), while
  `hermes_constants.py:736`'s comment still promises it. No impact on this report's math.
- **Bottom line upheld:** the coupled CUT_LOSER + wider-SL shadow-trial recommendation
  stands.
