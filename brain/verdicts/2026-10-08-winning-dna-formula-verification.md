# Independent Verification: "Winning DNA Formula" Plan (v3)

**Date:** 2026-10-08
**Auditor:** Independent subagent (fresh read, own queries — nothing trusted from the plan or prior analyses)
**Target:** `/root/.hermes/plans/winning-dna-formula.md`
**Data:** PostgreSQL `brain`.`trades`, window `close_time >= now() - 30 days` (832 closed trades, 431W / 392L, WR 51.8%)

---

## OVERALL VERDICT: PARTIAL — DO NOT IMPLEMENT AS WRITTEN

**Credit where due:** every number in the plan reproduces to the decimal from the database.
The analysis is numerically honest (unlike attempts 3–4 documented in
`brain/lessons/2026-10-08-winning-dna-failure.md`). The problem is not the arithmetic —
it is the **inference**. Of the 6 headline claims: **1 DISAGREE outright, 3 DISAGREE as
"winning DNA" (the numbers are real, the interpretation is wrong), 2 PARTIAL.** Of the 4
implementation phases: 1 is contradicted by the full population, 1 is already shipped,
1 would block positive-expectancy trades, and 1 inverts sign out-of-cohort.

---

## METHODOLOGY RECONSTRUCTION (how I reproduced their cohorts)

The plan states "Top 20 winners / Top 20 losers, same period, same signals" without defining
the cohorts. After brute-force search I recovered the exact definitions — **all plan numbers
reproduce exactly under these:**

- **Winners (W20):** `status='closed' AND pnl_pct > 0 AND close_time >= now()-interval '30 days'`
  ORDER BY `pnl_pct DESC` LIMIT 20 → 13 LONG/7 SHORT, entry RSI avg 60.9, duration avg 277 min,
  signal RSI avg 55.0, speed 61.6, exits 14 atr_sl_hit / 3 atr_trail_hit / 1 trail_sl /
  1 profit-monster-trail / 1 HARD_SL_FAILED, leverage 18×5x+2×3x, vol regime 12E/5H/3N — **all exact**.
- **Losers (L20):** same window, `pnl_pct < 0`, **restricted to trades whose exact `signal`
  string appears in W20's signal set**, ORDER BY `pnl_pct ASC` LIMIT 20 → 5 LONG/15 SHORT,
  RSI avg 51.1 (range 21.2–93.9), duration avg 119 (range 15–548), speed 55.9,
  signal RSI avg 47.0 (range 24.1–97.8), exits 18 atr_sl_hit + 2 rr_engine_resistance — **all exact**.

**Two hidden facts the plan never discloses:**

1. **The loser cohort is not "the top 20 losers."** It is the top 20 losers *after dropping
   6 worse losers* whose signal strings weren't in the winner set (IMX breakout-long+ −11.1%,
   AVAX mover- −9.3%, ZEN breakout-long+ −8.8%, ATOM open_skies −8.0%, ICP composite −7.9%,
   ENA composite −7.8%). **5 of those 6 dropped losers are LONG.** This single undisclosed
   filter is what turns the loser cohort from 10L/10S (raw top-20) into the headline
   "75% SHORT". See Claim 1.
2. **RSI stats rest on 14 of 20 trades per cohort** (6 NULLs each; `entry_rsi_14` is populated
   for only 67% of the window). "Signal RSI" is not the `signal_rsi_14` column (populated in
   only 36/892 rows) — it is `_signal_metadata->>'rsi_14'`. Neither substitution is disclosed.

Also: every "median" in the plan is `sorted(x)[n//2]` (upper-middle order statistic), not the
true median. Real medians: winner RSI 62.6 (plan: 63.0), winner duration 254 (plan: 259),
**loser RSI 46.9 (plan: 51.6 — inflated by 4.7 points)**, loser duration 58 (plan: 63).
Each sliver favors the thesis.

---

## CLAIM-BY-CLAIM VERDICTS

=== INDEPENDENT VERDICT ===
**Claim: "Winners are LONG-biased" (65% LONG vs losers 75% SHORT)**
**Verdict: DISAGREE** (as winning DNA; the counts themselves reproduce)
**Evidence:**
- Plan cohorts reproduce: W20 13L/7S, L20 5L/15S, Fisher p=0.025.
- **Against raw top-20 losers (no signal filter): 13L/7S vs 10L/10S, p=0.523.** The "SHORT-biased
  losers" exists only after the undisclosed same-signals filter drops 5 LONG losers.
- **Full population: winners 59.4% LONG vs losers 58.7% LONG, Fisher p=1.000.** Zero effect.
- Direction is collinear with signal name (`+`/`-` suffix). Within the two pump-chain twins the
  **LONG signal wins LESS often: pump-chain+ WR 46.9% (n=98) vs pump-chain- WR 53.2% (n=141)**.
  The plan's own winner cohort is 11/20 pump-chain+ — the single weakest major signal by win rate.
- Phase 4 ("favor LONG signals") is therefore not just unsupported — the population data points
  the other way.
**Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Overbought entries work" (entry RSI 60.9 vs 51.1)**
**Verdict: PARTIAL**
**Evidence:**
- Reproduces (60.9 vs 51.1) — but on n=14 vs 14 (6 NULLs each). **Not significant in the plan's
  own cohorts: t-test p=0.284, Mann-Whitney p=0.223.**
- Full population: winners 56.4 vs losers 51.9, **p=0.013 (t) / 0.016 (MW)** — a small (~4.5 point)
  real effect exists. It is the only headline claim with genuine population support.
- Stability is mixed: 1st half of window 60.2 vs 57.3 **p=0.395 (no effect)**; 2nd half 55.1 vs
  50.3 p=0.025. Effect driven by recent weeks.
- Filter test of the proposed Phase 1 (`LONG + entry_rsi >= 55`, full window): kept 240 trades
  WR 55.0% expectancy **+0.761%**; blocked 123 trades WR 52.8% expectancy **+0.146%**. The filter
  raises per-trade expectancy but **discards a positive-expectancy block** (~9% of total LONG
  expectancy) — it is not "blocking losers." And the plan's own winners include RSI 13.1 and 28.5.
- Consistent with the previously noted defensible finding (RSI 50–70 confluence, 59% vs 44%),
  but this plan's evidence for it (n=20 extremes) does not demonstrate it.
**Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Winners last 2.3x longer" (277 vs 119 min)**
**Verdict: PARTIAL** — descriptively true, causally meaningless
**Evidence:**
- Reproduces exactly; highly significant (p=0.001 t / 0.000 MW). Full population too (156 vs
  120 min, p=0.006).
- But this is **selection-on-outcome by construction**: "top 20 winners by PnL%" are trades that
  rode, and the deepest losers are trades that died fast — the sorting *defines* the duration
  gap. The deeper you cut into losers by severity, the shorter their duration gets (raw top-20
  losers avg 77 min → same-signals losers avg 119 min once the fastest-dead losers with
  unmatched signals are swapped out... the number moves purely with cohort depth).
- The plan itself concedes it is "an OUTCOME, not a pre-entry condition." Correct — and therefore
  it is not DNA, not a filter, and not evidence for anything except "losers get stopped."
**Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Signal RSI 40–73 = in motion, not exhausted" (55.0 vs 47.0)**
**Verdict: DISAGREE** (as stated evidence)
**Evidence:**
- Reproduces on the cohorts (55.0 n=17 vs 47.0 n=18; ranges 40.0–72.9 vs 24.1–97.8 exact).
  Cohort significance is marginal at best (MW p=0.046, **t p=0.115**).
- **Full population: winners 52.4 vs losers 52.2, p=0.880.** There is no population-level
  separation on this variable at all. The tight 40–73 winner range is classic in-sample range
  fitting on 17 points (of course the extreme-PnL winners' 17 RSI values fall in a band;
  so would many other bands chosen after the fact).
- **Anomaly worth flagging honestly:** a *separate* test I ran of the 40–73 band on the full
  window (metadata rsi_14) shows keep n=509 WR 53.8% expectancy +0.52% vs outside n=219 WR
  46.1% expectancy **−1.02%**. That is suggestive — but it was not the plan's evidence, it is
  in-sample, and it must be (a) validated out-of-sample and (b) collision-checked against the
  RSI_MIN/RSI_MAX gates already in signal_compactor before anyone touches code.
**Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Winners are faster" (speed percentile 61.6 vs 55.9)**
**Verdict: DISAGREE**
**Evidence:**
- Reproduces, but **p=0.496 (t) / 0.394 (MW)** — indistinguishable from noise at n=20.
- **Full population reverses the sign: winners 49.3 vs losers 51.3 (winners slightly SLOWER,
  p=0.287).** W20's 61.6 is a top-20 selection artifact (all winners average 49.3).
- Filter test (Phase 3, full window): SPEED>=50 keeps 425 trades WR 49.4% / +0.158%; the
  "slow" block is WR 55.5% / +0.090%. At SPEED>=65: kept WR 52.7% vs blocked 52.2%. Favoring
  fast coins would systematically **de-prioritize the higher-win-rate half** for no expectancy gain.
**Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Trailing stops let winners run" (25% of winners vs 0% of losers)**
**Verdict: PARTIAL** — true description, circular as DNA, already shipped as Phase 2
**Evidence:**
- Reproduces: W20 has 5/20 trailing exits (atr_trail_hit ×3, trail_sl ×1, profit-monster-trail ×1);
  L20 has 0.
- **The 0% is mechanically guaranteed, not a trait.** A trailing stop can only fire *after price
  has moved into profit far enough to arm; a trade that goes straight to its stop can never exit
  via trail. Comparing "exit reason" between top-20 winners and bottom-20 losers measures the
  exit machinery's logic, not the trade's DNA. In the full window the claim doesn't even hold:
  **47 of 392 losers (12%) exited via trailing mechanisms** (46 profit-monster-trail, 1
  atr_trail_hit) — they trailed, then gave the profit back.
- **Trailing is already the dominant winning exit:** profit-monster-trail n=227, WR 79.7%,
  avg +1.727% — 45% of all 431 winning exits already trail. Phase 2 ("use trailing stop as
  primary exit") re-proposes shipped behavior — exactly the failure mode item #3 of the
  project's own lesson file warns about. (`trailing_activated` column is dead — 0/832 —
  a data-quality bug worth fixing on its own.)
**Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Winners prefer EXTREME volatility regime" (60% of winners)**
**Verdict: DISAGREE**
**Evidence:** Base rate of the window is ~40% EXTREME. Full population: winners 168/431 (39.0%)
vs losers 162/392 (41.3%), chi2 p=0.227. The 60% figure is a top-20 artifact. **Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "5x leverage is the sweet spot; no losers use 10x"**
**Verdict: DISAGREE (vacuous)**
**Evidence:** There is exactly **ONE 10x trade in the entire 30-day window** (381×3x, 450×5x,
1×10x). "No losers use 10x" compares 0 vs ~1. Winners' 5x share (55%) ≈ population base rate
(54%), chi2 p=1.000. No information content. **Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Winners spread across ALL BTC regimes"**
**Verdict: AGREE (as a null finding)**
**Evidence:** Reproduces (7 RANGING / 3 BEAR_TREND / 2 each of BULL_TREND, RANGING_BEAR,
TRANSITIONING; 4 missing metadata — plan silently computes percentages over 16–20 without
saying which). Cohorts p=0.928; full population p=0.127. There is genuinely no BTC-regime
signal here. Fine basis for *not* building regime blocks. A null result is not "winning DNA." **Confidence: HIGH**

=== INDEPENDENT VERDICT ===
**Claim: "Winners can be in falling wave phase" (35%)**
**Verdict: PARTIAL (harmless)**
**Evidence:** Cohort diff p=0.515. Full population p=0.055 with a mild *accelerating* edge
(winners 45.5% accelerating vs losers 44.6%... falling: 35.0% vs 40.1%). True that falling
waves are not a death sentence; weak as a reason to affirmatively allow anything. **Confidence: HIGH**

---

## SELECTION BIAS (question 5) — CONFIRMED, AND QUANTIFIED

Top-20-by-PnL% selection on *both* sides is selection-on-outcome. The tell is how far W20
diverges from the population it would supposedly teach us to trade:

| Trait | W20 (top-20 winners) | ALL 431 winners | Verdict |
|---|---|---|---|
| Speed percentile | 61.6 | **49.3** | vanishes, reverses |
| EXTREME vol regime | 60% | **39%** | vanishes |
| 5x leverage | 90% | **55%** | vanishes |
| LONG share | 65% | **59%** | vanishes |
| Entry RSI | 60.9 | **56.4** | shrinks to ~4.5 pts |

A filter derived from W20 would act on the whole distribution, where most of its "DNA" does
not exist. Correct alternative: **ALL winners vs ALL losers** (I ran it: n=823) plus
out-of-sample/holdout weeks — which is what surfaced the two genuinely defensible items:
a small entry-RSI effect and the (separately testable) signal-RSI band.

## CONFOUNDING (question 6) — CONFIRMED

- **Time period:** every L20 loser opened **Sep 8 – Sep 24**; W20 winners span **Sep 9 – Oct 7**.
  The worst same-signal losers all come from the first half + the Sep-21 week (WR 40.2%) —
  a bad market week, not a trade trait. Weekly WR swings 57.3% → 39.0% → 55.3% → 39.0%.
- **Signal mix:** direction is fully determined by signal; the cohort contrast is a restatement
  of "which signals' losers were kept," not an independent direction effect (see Claim 1).
- **Non-independence:** W20 repeats AVAX/ADA/JUP (×2 each); L20 repeats DOT (×3), LINK, IMX (×2);
  5 tokens (ENA, ONDO, FIL, ETC, AVAX) appear on *both* sides. Effective n well below 20.
- **Missing data:** 6/20 NULL entry-RSI in each cohort, unacknowledged; `signal_rsi_14` column
  unusable (36/892) — metadata substituted silently.

## BOTTOM LINE

The plan is the most competently executed of the winning-DNA iterations — it reproduces, and it
even self-flags duration as an outcome. But it still fails the project's own 8-point checklist:
selection-on-outcome (top-20 both sides), no p-values in the plan, one undisclosed cohort filter
doing enormous hidden work, missing-data substitution, in-sample range fitting (40–73),
re-proposing shipped work (trailing exits), and no out-of-sample validation. Its four
implementation phases reduce to: one contradicted by data (LONG bias), one already live
(trailing), one that blocks positive expectancy (RSI>55), one that inverts (speed>50).

**Recommendation: do not implement Phases 1–4 as written.** The only survivors worth further
(independent, out-of-sample, collision-checked) work: **entry-RSI/RSI-band confluence** — which
this plan did not actually prove, but which my population tests keep showing is the sole
variable with any real separation — and the standing lesson conclusion: **fix payoff ratio /
loss management, not signal DNA.**

**Confidence: HIGH** (all claims re-derived from live queries; cohort definitions reverse-engineered
and matched to the plan's published numbers exactly; significance computed on both cohorts and
full population; filters tested prospectively on the full window).

*Reproduction queries: cohort SQL as documented in Methodology section; all tests run 2026-10-08
against `brain.trades` (832 closed trades in window).*
