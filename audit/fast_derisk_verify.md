# Independent Audit — "Fast De-Risk" Counterfactual Backtest (2026-10-08)

**Auditor:** independent verification pass (fresh code, no reuse of the analyst's script or output)
**Subject:** `/root/.hermes/analysis/fast_derisk_backtest_2026-10-08.py` (+ `.out`), proposed rule **T=30min / theta=-0.5%**
**Data re-derived from:** PostgreSQL `brain.trades` (own SQL) + SQLite `/root/.hermes/data/candles.db` `candles_1m` (own queries, read-only)
**Audit code (all in `/root/.hermes/audit/`):** `verify_core.py`, `verify_part2.py`, `verify_part3.py`, `verify_part5.py`, `verify_hml.py`, `verify_hml_diag.py`

> Method note: every number below comes from code executed in this audit. Where my first
> attempt at a statistical null was misspecified (a move-shuffling permutation whose null
> distribution is not centred on zero, mean −$17.9), I discarded it and replaced it with
> two correctly-centred tests (random-minute placebo, random-21-cell selection test); both
> are reported. Two bugs in my own first variant pass (slippage applied to $ instead of
> notional; "next-bar open" as a delay test) were found and fixed — the delay test was
> redone as 1/2/5-bar lags because in a continuous 1m series `open[t+1] == close[t]`
> identically (median diff +0.0000%), making "exit at minute-31 open" a no-op test.

---

## VERDICT SUMMARY

| # | Task | Verdict |
|---|------|---------|
| 1 | Population / coverage / Aug-21 pnl_pct convention | **PARTIAL** — counts reproduce (with one explained DB drift); the convention claim is violated by **4.7%** of trades, creating **6 hidden home runs** |
| 2 | Independent T=30/-0.5 simulation | **AGREE** — exact replication: 179 triggered, +$1.855, h1 +$1.39, h2 +$0.46, 0 HR kills; mechanics hand-verified |
| 3 | Method attack (a–f) | **DISAGREE with the implied robustness** — no lookahead, but the edge is statistically indistinguishable from noise and dies at 8bp of slippage |
| 4 | HML side claim (63/70, median +0.07%) | **DISAGREE** — my recompute: **57/71**, median **+0.166%**; no window/method variant reproduces the claim |
| 5 | Economics | **+$1.85 becomes +$0.70 at 5bp slippage and −$0.46 at 10bp** (breakeven 8.0bp) |

**OVERALL: DO-NOT-PROPOSE.** Not because the backtest is fraudulent — the replication is exact
and the analyst's framing is unusually honest — but because the effect is smaller than its own
noise, is fully consumed by realistic execution costs, and its "safety" rests on a guard that
holds only inside a knife-edge parameter pocket.

---

## TASK 1 — Population, coverage, convention — **PARTIAL**

**My numbers (own SQL, own bucketing):**

| Quantity | Analyst | Audit | Note |
|---|---|---|---|
| Live closed trades opened ≥ 2026-08-21 | 1,854 | **1,855** | fully explained — see below |
| HR (pnl_pct ≥ 10) | 64 | **64** ✓ | |
| Big winners (≥ 5%) | 189 | **189** ✓ | |
| Candle coverage | 1,844 covered / 10 missing | **1,845 / 10** ✓ | missing = trades on tokens with **no** candle rows at all (AR, PONS, +2) |
| HR coverage | 64/64 | **64/64** ✓ | |

**The +1 drift is not an error:** trade **15993 (BANANA)** opened 20:02:00 and closed
**21:06:28** today — after the analyst's script ran (21:01). The analyst's 1,854 was correct
at run time; the population is a moving target and my replication reproduces the headline
cell exactly even with the extra trade.

**pnl_pct convention claim — this is where the claim breaks.** Classifying every trade by
comparing `|pnl_pct| / |price move from entry_price→exit_price|` against its leverage:

- **1,754 / 1,841 (95.3%) leveraged** as claimed ✓
- **69 unlevered-style** (pnl_pct == raw price move, leverage ignored)
- **18 "other"** (matches neither) → **87 trades (4.7%) violate the claimed convention**
- Sign consistency: **0** disagreements between pnl_pct sign and price move ✓
- **Consequence: 6 hidden home runs** — e.g. id 15751 CRV SHORT, raw −4.90% at 5x = +24.5%
  leveraged, but recorded pnl_pct = +4.90, so it is **invisible** to the `pnl_pct >= 10` HR
  guard. Corrected HR set = **70**, not 64.
- **Impact on the verdict: none.** Under the corrected 70-trade HR set the chosen cell still
  has **0 kills**. But the convention claim as stated is wrong for ~1 in 20 trades, and any
  future guard built on `pnl_pct ≥ 10` inherits a silent undercount of home runs.

---

## TASK 2 — Independent T=30 / theta=-0.5 simulation — **AGREE**

Own implementation (checkpoint = first 1m candle whose *close time* ≥ open+30min, i.e. the
first close at-or-after 30 minutes elapsed — independently derived, matches the analyst's
bucketing):

```
trig = 179    delta = +$1.855    h1 = +$1.39    h2 = +$0.46    HR kills = 0
saved (142 eventual losers) = +$8.50    given up (37 winners cut) = -$6.65
actual book (unleveraged $, post-Aug-21) = -$9.10   (analyst: -$9.13 on covered-only 1,844)
```

**Every headline number reproduces to the cent.** Mechanics hand-checked on 8 random
triggered trades — entry price, minute-30 close, recorded exit price and pnl_usdt are all
mutually consistent, e.g.:

- **id 15676 KAS SHORT**: entry 0.038176, min-30 close 0.03848 → −0.80% (trigger); recorded
  exit 0.0387236 → −1.45% adverse; `pnl_usdt` −0.32 = −1.45% × $22.10 notional ✓
- **id 15564 WLD SHORT**: entry 0.4192, min-30 close 0.42231 → −0.74%; actual exit 0.42556
  → −1.53% adverse, pnl_usdt −0.17 ✓

**Fee-neutrality confirmed:** on 6 random trades `pnl_usdt` equals
`(exit_entry)/entry × notional` to the cent, *including* trades that have a populated
`fees` JSON — so fees are indeed excluded from pnl_usdt and the fee-neutral framing holds.

---

## TASK 3 — Method attack

### 3a. Lookahead / price selection — **no fatal lookahead, but no execution headroom either**

- **No time lookahead.** The minute-30 exit price is the first 1m close at-or-after 30 min
  elapsed (verified independently). Entry is mid-minute for most trades; the checkpoint
  lands 29.0–30.0 min after entry. This is fair.
- **"Exit at minute-31 open" is a vacuous test** — in this candle store `open[t+1]` equals
  `close[t]` (median difference **+0.0000%**), so it cannot detect anything. Anyone citing it
  as evidence of robustness is citing a no-op.
- **Real latency tests (exit at the close of bar T+1 / T+2 / T+5):** +$1.76 / +$1.69 / +$1.26.
  At 5 bars the **h2 half turns negative (−$0.15)** — the "positive in both halves" guard
  that justified the pick already fails at ~5 minutes of detection latency.
- **Slippage (applied to notional):** 5bp → **+$0.70 (h2 −$0.30)**; 10bp → **−$0.46**.
  The edge does not survive contact with a real order book (see Task 5).

### 3b. Selection bias — **the +$1.85 is inside the noise floor**

- **Per-trade statistics:** mean delta **+$0.0104**, sd **$0.1202**, n=179 → **t = +1.15, p = 0.25**.
  **Bootstrap 95% CI for the total: −$1.38 … +$4.93** — crosses zero.
- **Concentration:** the **top 10 trades contribute +$1.84 of the +$1.85**. The other 169
  triggered trades sum to **+$0.01**. 128 winners (+$9.15) vs 51 losers (−$7.30).
- **Placebo — random-minute rule (same theta, random minute per trade, 2,000 reps):**
  mean **+$0.82**, sd $1.21, **P(≥ +$1.85) = 0.206**. A *generic* "cut anything down 0.5%
  early" rule already harvests +$0.82 on this book for free; the specific (30, −0.5) choice
  adds about +$1 over that, which is **0.86 standard deviations** of placebo noise.
- **Selection procedure applied to 21 RANDOM cells (2,000 reps, same guard: 0 HR kills +
  both halves positive):** **84.8%** of random 21-cell sweeps contain at least one
  guard-passing cell; the best guard-passing cell of a random search has median **+$1.26**,
  p75 +$1.79, p90 +$2.43, and **P(best ≥ +$1.85) = 0.246**.
  → **About 1 in 4 random parameter searches would produce a "winner" at least as good as
  the proposed one.** The chosen cell is unexceptional.
- **Surface smoothness (theta grid at T=30):** −0.7:+1.29 · −0.6:+2.43 · −0.55:+2.08 ·
  −0.5:+1.85 · −0.45:+1.58 · −0.425:+1.12 · −0.4:+1.27 · −0.35:+1.70 — non-monotone jaggedness
  at the ±$0.5 level, i.e. the surface is noise-dominated.

### 3c. Era stability — **not one week, but not stable either**

| ISO week | W34 | W35 | W36 | W37 | W38 | W39 | W40 | W41 |
|---|---|---|---|---|---|---|---|---|
| trig | 6 | 25 | 32 | 44 | 25 | 20 | 21 | 6 |
| delta $ | −0.02 | +0.67 | +0.78 | −0.34 | −0.43 | +1.09 | −0.16 | +0.26 |

**4 of 8 weeks positive.** Drop the best week (W39) → **+$0.76**. Drop the best token (BLUR)
→ +$1.37. So the +$1.85 is not one week, but roughly **half of it is one week + one token +
ten trades**.

### 3d. Entry-price fidelity — **clean for the triggered set**

`|entry_price − open-minute close|`: median **0.062%**, p90 0.239%, p99 0.681%, max 16.15%
(id 15340 ALT — a hold=0 scalp, **not** in the triggered set). 89 trades exceed 1% deviation,
but only **1 of the 179 triggered trades** does. Entry-price error does not drive the result.

### 3e. Hold logic / double-counting — **airtight, as claimed**

- Minimum hold among the 179 triggered trades = **30.04 min**; **0** triggered trades have
  hold < 30. The `hold ≥ T` gate plus "exit at the first close at-or-after T" guarantees the
  simulated exit always precedes the recorded exit. **No double counting.**
- Trades stopped before T keep their actual outcome — correct by construction.
- Only **2 of 179** have a recorded exit *price* that the market touched earlier in the hold
  (id 14128 HYPE, touch at 1.2m; id 14268 BIGTIME, touch at 26.4m with hold 30.3m). Both are
  wide-band touches of a level the price revisited — not evidence of early exit, but
  id 14268 (hold 30.3m, touch 26.4m) is genuinely marginal.
- 10 triggered trades eventually closed via `hard_max_loss` **after** the checkpoint, so the
  −1.5% account stop could not have removed them beforehand — the interaction the task asked
  about does not bite on this sample.
- **Residual, unmodelled interaction:** the −1.5% stop is on *account* equity; a rule that
  changes the equity path changes what that stop does later. The one-shot replay cannot
  capture that path dependence.

**Latent bug (does not bite here, will bite later):** the analyst's `price_at()` falls back
to the **last close before T** when no candle exists at/after T. For sparse-candle tokens
that silently substitutes a stale price. I verified the fallback is never used at T=30 or
T=120 in this population (my strict "return None" version reproduces both the headline cell
and the baseline exactly), but it is a live hazard for any future sweep over illiquid tokens.

### 3f. Baseline (existing `pump_exit_dead_money`) — the comparison is mis-scoped

I reproduce the analyst's **−$3.84 / 8 HR kills** exactly. Two problems:

1. **Scope bug.** `SIGNAL_EXIT_CONFIG` maps `pump-chain+ → pump_exit` and
   `pump-chain- → rr_engine` (`scripts/hermes_constants.py:1671-1672`). The replay used
   `strategy.startswith('pump-chain')`, which drags in **138 pump-chain− trades that do not
   use this exit at all**. Correct live scope (`pump-chain+` only, n=141):
   **delta = −$2.82, 41 triggered, 6 HR kills** — not −$3.84 / 8. The "baseline to beat" is
   ~$1 less bad and 2 kills fewer than presented.
2. **The "velocity clause protects them" defence does not hold.** The live rule needs
   `profit < 2.0% AND hold > 2h AND vel_fading` (1-minute velocity, direction-aware).
   All four kills I reconstructed were genuinely below +2% at the 2h mark (GRASS +0.65%,
   best in first 2h only +0.78%; FOGO +0.42%, best +0.66%; AVAX +0.50%; ETC −0.22%).
   Checking the actual 1-minute velocity at that mark: **GRASS, AVAX and ETC were already
   "fading" — the live rule would have fired and killed them anyway.** Only FOGO
   (+0.077% 1m velocity) would have been spared. A 1-minute lookback is a near-coin-flip at
   any instant, so across a multi-hour flat stretch it protects almost nothing.
   → The baseline's harm is real, not an upper bound artefact. (It is still true that the
   replay cannot *prove* the live rule fires; the point is that the velocity clause cannot
   be counted on to prevent these kills.)

---

## TASK 4 — HML side claim (63/70 never reached +0.40%, median peak +0.07%) — **DISAGREE**

- **`peak_price` is NULL for 71/71** hard_max_loss trades — the "dead column" claim ✓.
- **Population:** 71 hard_max_loss trades in the trailing 14d (analyst said 70; trade 15993
  BANANA closed 21:06 today, after their run — same drift as Task 1).
- **My candle replay (direction-aware, MAX favourable high/low between open and close):**
  - **57 / 71 never reached +0.40%** (claim: 63/70)
  - **median peak = +0.166%** (claim: +0.07%) — **2.4× the claimed median**
  - **14 trades DID reach +0.40%**, max **+1.13%** (FOGO), plus +1.09% (HYPER), +1.04% (ALGO),
    +1.00% (JUP)
- **Variants tried, none reproducing the claim:** close-only peak → 59/71, median +0.138%;
  excluding the entry candle → median +0.138%; MAX(high) ignoring direction → 43/71,
  median +0.304%; recorded `mfe_pct` column → 59/71, median +0.118%; window anchored on
  open_time vs close_time, 14d/30d, last-70 → 56–57/71, median 0.166–0.181%.
- **Direction of the error matters:** the claim *understates* the peaks, which makes
  hard_max_loss look more hopeless than the data says and strengthens the "kill these
  earlier" narrative. The qualitative point survives (most of these trades never went
  anywhere: median peak +0.17%), but **one in five of them did reach +0.40%**, so "63/70
  never reached +0.40%" overstates the tail case by roughly 2×.

---

## TASK 5 — Economic honesty

| Item | Value |
|---|---|
| Claimed improvement | **+$1.85** |
| Actual book PnL (post-Aug-21, unleveraged $) | **−$9.10** (analyst −$9.13 on covered pop.) |
| Avg position notional | $12.63; triggered trades total **$2,317** of notional |
| Slippage 2bp on 179 exits | cost $0.46 → **net +$1.39** |
| **Slippage 5bp** | cost $1.16 → **net +$0.70** (h2 already **−$0.30**) |
| Slippage 10bp | cost $2.32 → **net −$0.46** |
| **Breakeven slippage** | **8.0bp** on the triggered notional |
| Statistical 95% CI (bootstrap) | **−$1.38 … +$4.93** (p = 0.25) |

Framed against the book, +$1.85 is a +20% swing on −$9.10 — which is exactly why it looks
attractive. But: (i) the confidence interval includes "zero or worse"; (ii) 8bp of round-trip
slippage erases it entirely, and these are alt-market orders executed *at the moment a trade
is failing*, when spreads are widest — 8bp is optimistic, not conservative; (iii) the
proposed rule fires ~25×/week, and detecting a $0.01/trade effect with $0.12/trade
dispersion needs on the order of **10,000 trades**, so no realistic shadow run can confirm it.

---

## FATAL FLAWS

1. **The effect is noise.** t = 1.15, p = 0.25, bootstrap CI −$1.38…+$4.93; **the top 10
   trades are 100% of the edge** (+$1.84 of +$1.85) and the other 169 triggered trades net
   to +$0.01. A result carried entirely by 10 observations out of 1,855 is not a rule.
2. **Selection bias quantified, not hand-waved.** Re-running the analyst's own selection
   procedure (21 random cells + the same 0-HR-kill/both-halves guard) shows **84.8%** of
   random searches yield a guard-passing cell and **P(best random cell ≥ +$1.85) = 0.246**.
   A generic random-minute early-cut placebo already returns **+$0.82 ± $1.21**. The
   specific (30, −0.5) cell is ~0.9 placebo-sigma above the free alternative.
3. **Zero execution headroom.** Breakeven slippage is **8bp**; at 5bp the edge halves to
   +$0.70 and the h2 half goes negative; at 10bp it is negative. The same is true of
   latency: at 5 one-minute bars of detection delay h2 is negative. The "positive in both
   halves" guard that made this cell look safe fails at the first realistic friction.
4. **The 0-HR-kill guard is a knife edge, and the guard is the whole pitch.** The safe
   pocket is **T ∈ {29, 30, 31}** and **theta ∈ [−0.70, −0.45]**: T=28 → 1 HR kill, T=32 →
   1 kill, theta=−0.425 → 2 kills. Each killed home run is worth +$0.26…+$1.78 of realised
   profit — i.e. **14–96% of the entire claimed edge per single kill**. A ±1-minute or
   ±0.07% implementation deviation turns the "safe" rule into a home-run killer.

**Non-fatal but must be corrected before this analysis is reused:**

5. **Baseline mis-scoped:** replayed `startswith('pump-chain')` includes 138 pump-chain−
   trades whose live exit config is `rr_engine`, not `pump_exit`. Live-scope baseline is
   **−$2.82 / 6 kills**, not −$3.84 / 8.
6. **"Velocity clause protects the HRs" is false in practice** — 3 of 4 kills reconstructed
   were already velocity-fading at the 2h mark and would have been killed live anyway.
7. **HML numbers do not reproduce** (57/71 and median +0.166%, vs claimed 63/70 and +0.07%),
   and the discrepancy runs in the direction that supports the narrative.
8. **pnl_pct convention violated by 4.7% of post-Aug-21 trades** (69 unlevered-style + 18
   other), producing **6 hidden home runs** invisible to the `pnl_pct ≥ 10` guard. No impact
   on this cell (still 0 kills at corrected HR=70), but any future guard inherits the flaw.
9. **Latent stale-price bug** in `price_at()` (falls back to the last pre-T close when no
   candle exists at/after T) — harmless on this population, dangerous for sparse tokens.

---

## RECOMMENDATION

**DO-NOT-PROPOSE** — not as a live rule, and not in the "safe to propose in shadow" framing
either.

- The replication is exact and the analyst's honesty about multiple comparisons is real;
  the problem is not integrity, it is **signal-to-noise**: +$1.85 ± ~$3, consumed by 8bp of
  slippage, carried by 10 trades, and licensed only by a guard that is one minute wide.
- A shadow run cannot rescue it: at ~25 triggers/week with $0.12/trade dispersion, validation
  would take years of live data — during which the parameter pocket would be expected to
  drift anyway (4 of 8 weeks are negative today).
- If leadership wants a "cut dead trades faster" initiative, the defensible version is
  **not** a new 30-minute rule but an honest audit of *why* 142 of 179 early-red trades
  survive to lose more (they already have `hard_max_loss`, `cut-loser-CL-T1`,
  `pump_exit_dead_money` — this proposal overlaps those exits rather than replacing them).
  Any successor proposal should be pre-registered on a single cell, tested with execution
  costs ≥ 10bp, and required to clear a bootstrap CI excluding zero.

**Files produced:** this report (`/root/.hermes/audit/fast_derisk_verify.md`) plus the audit
scripts listed at the top. No files outside `/root/.hermes/audit/` were modified.
