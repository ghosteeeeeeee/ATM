# BRIEF: T forwards the edge diagnosis + today's discussion — "propose ideas" (2026-11-22)

## T's instruction (verbatim intent)
"Summarize our current discussion for the CEO. I want it to take a look at this as well
(this is important stuff), and **propose ideas.**"
→ Primary input: **`brain/2026-11-22_hermes-edge-diagnosis.md`** (431 lines, read in FULL —
it contains its own correction/Section 7; do not act on superseded sections). Secondary input:
today's discussion arc below. Deliverable: synthesis + a concrete idea list T can act on.

## The diagnosis doc — what it claims (spot-check every number yourself)
- **Accounting broken:** `pnl_usdt` is gross; internal sum −$18.53 (6,584 trades) vs
  exchange-reported **−$350.31** (3,951 fee-JSON subset); fees $209.35 in subset →
  "nothing downstream is trustworthy until reconciled".
- **MASKED EDGE (Section 7, the correction):** payoff>1.2 group = **14 signals, n=2,332,
  +$13.45, WR 41.4%, t=+2.40 significant** vs payoff<1.0 group = 23 signals, n=1,890,
  −$9.21, WR 54.7%, t=−1.76. **High-WR signals are the losers; low-WR signals ARE the edge.**
  Traded alone: the 10 low-WR-but-profitable signals = +$13.27, t=+2.39.
- **pump-chain confirmed as top-winner source:** 30 of top-100 trades, +$14.06 combined
  (pump-chain+ n=187 +$2.29 at 39.6% WR) — T's instinct validated.
- **THE BINDING CONSTRAINT:** edge +0.0496% of notional vs friction **1.14% RT**
  (0.45% fees + 0.69% slippage) → **23× too small**; size cannot fix (percentage-based).
- **Slippage anomaly:** mean 0.69%, median 0.35%, winners slip 0.96% vs losers 0.37% (2.7×);
  `exit_slippage_pct` computation "could not be located" → **verify before treating as hard cost**.
- **Revised action order:** ① reconcile accounting ② cut the 23 payoff<1.0 signals ③ concentrate
  on the 14 ④ verify slippage definition ⑤ attack cost (maker fills, limit entries, fewer/larger,
  lower-fee venue) ⑥ **"delete the win-rate philosophy"** (replace with expectancy/payoff/cost).

## Today's discussion arc (the other input)
1. **TP-vs-trail study CLOSED NO SHIP** (built `scripts/tp_vs_trail_sim.py`, engine validated
   byte-equal to jup's own main): A3 hybrid TP vs trail = **+$0.02 vs +$1.00 bar**; the 1.0% TP
   fires 3/142 because pm-trail exits first; pure-TP arms −$4.07/−$4.86 lose to trail −$3.41;
   all sensitivities NOT MET. Trail stays the exit engine.
2. **Flip-signs theory (T):** mirror all trades, "we always hit SL". Ruled with arithmetic:
   gross flips, fees don't (−$0.0209/trade → −$0.0079); the pc- fade ALREADY tested it live
   (gross +$0.13, net −$0.21). Fixed TP+SL = rr-sims (−255 worst-arm) + ride_it full-book
   sign-reversal — banned.
3. **Mirror analysis of the last 10 losing LONGs (T's exact request):** same entry/exit-time
   flipped = 9/10 positive, **−$0.70 → +$0.29** (selection-on-outcome, disclosed) — BUT
   mirroring ALL 91 longs = **worse (−$1.15 → ≈−$1.47)**: the 41 winners (+$2.89) invert into
   −$2.89 and eat the gain. 4/10 died at prearm_lock (BE-lock firing as designed).
4. **Payoff program state:** stop-tighten scope REVERTED to 2 sources 11-20 (registered revert) ·
   prearm ENFORCE live since 11-20 (built new flag — enforcement didn't exist) · HML 7d ~17/−$2.04
   (targets <15/−2.00) · win-capture collector verified · net-PnL KPIs shipped (Phase 0) ·
   notional gated on net/trade >0 (−$0.010) · brake counterfactual accruing (n≥30 bar) ·
   margin-vs-leave brake option parked with T.

## Reconciliations the CEO must do (this is the synthesis T wants)
1. **The friction numbers conflict:** doc says 1.14% RT (0.45% fees + 0.69% slippage) vs our
   fee-only 0.106–0.109% RT used in every verdict since 11-16. Hypotheses to check: (a) BUG-099
   fee inflation (pre-8/22 JSON ~10×) contaminating the doc's $209.35/0.45% — recompute fees on
   post-8/22 trades only; (b) slippage measured vs stale reference (the doc's own warning + our
   shipped `exit_slippage_pct` PG column from 11-16 — the doc couldn't locate the computation;
   it exists now, run the real distribution on the shipped column); (c) if slippage is real at
   0.69%, the 23× gap stands and EVERY prior verdict's "fee hurdle" framing was understating
   costs by ~10×. Rule which friction number is TRUE and restate the binding constraint.
2. **The goal-metrics conflict:** our goal dashboard targets **non-jup fleet WR ≥55%** — the
   diagnosis proves the 54.7% WR group is the net-negative population (−$9.21). The goal metric
   may be optimizing for the LOSERS. Rule: restructure the goal metrics around expectancy/
   payoff/cost (the doc's item 6) with a concrete new metric set + baselines, OR defend WR.
3. **The 23-signal cut vs "no blanket kills":** cutting 23 signals at once IS a blanket action.
   Propose the bar-based path: which signals die immediately on already-pre-registered bars
   (check the registry — several may already have NO-SHIP/FAIL reads), which need a cut-bar
   first, and the revert path. Also: does "cut" mean ENABLED=False per signal or a denylist?
   (House: flags, not code removal.)
4. **Accounting reconciliation next step:** Phase 0 shipped net_pnl from fee JSON — the doc asks
   for EXCHANGE-net reconciliation (pnl_usdt vs fees JSON net_pnl, both directions, BUG-099
   window split). Spec it (is it a script? a dashboard field? a one-time report?).
5. **The philosophy line:** the doc says "Every trade should be a winner" is "exactly backwards"
   (it would select the 54.7%-WR losers). That's T's non-negotiable line — he's now read the
   doc too. Propose the REFRAMED principle for T's approval (one sentence, keeps his intent —
   "every trade should be a winner" can survive as: winners by expectancy, not by hit-rate),
   but do NOT unilaterally edit AGENTS.md philosophy.
6. **Cost attack (the doc's item 5):** our speed mandate vs maker/limit entries (fill-risk) —
   what's actually available at $12 notional on HL (fee tiers, maker rebates, limit-entry
   feasibility with 10-min signal staleness)? One honest feasibility note, no hand-waving.
7. **Idea list for T** (he asked for ideas): ranked $/time, each with owner + bar + revert,
   integrating: the 14-signal concentration, the slippage verification, the goal-metric
   restructure, cost attack, and anything the diagnosis raises that our stack hasn't covered.
Constraints: no blanket kills without bars, protected flags, net-of-fees + CI, token-day dedup,
flag polarity, speed mandate, fold framework intact. Read-only consult — rulings + idea list only.
