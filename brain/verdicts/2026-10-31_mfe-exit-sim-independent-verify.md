# Independent audit — "mfe-exit" exit-strategy simulation (fresh eyes)

**Auditor:** independent verifier (own conclusions, no priming from the analyst)
**Date:** 2026-10-31, audit window 18:15–18:46 UTC
**Target claims:** jup_exit_sim.py v4 output + constants comment (MFE_EXIT_*) + position_manager.py §7c comment block
**Protected files:** `scripts/jup_exit_sim.py`, `scripts/hermes_constants.py`, `scripts/position_manager.py` — **read only, not modified** by this audit (they were edited by others *during* the audit: mtime 18:40/18:41 — see F-11).

**Evidence I produced (all under `/root/.hermes/analysis/`):**
`mfe_audit_cohort.py`, `mfe_audit_replay.py` (+`.out`), `mfe_audit_sim_probe.py` (+`mfe_audit_sim_probe.json`),
`mfe_audit_compare.py`, `mfe_audit_forensic.py`, `mfe_audit_handcheck.py` (+`.out`), `mfe_audit_stats.py`.
I wrote my own replay from the rule spec and only *imported* (never edited) `jup_exit_sim` to dump its per-trade exits.

---

## (a) Reproduced? — **NO. The claimed table does not reproduce.**

### What a fresh run of `cd /root/.hermes/scripts && python3 jup_exit_sim.py` actually prints

| row | claim (n=45) | run A 18:15 UTC (n=47) | run B 18:20 UTC (n=48) |
|---|---|---|---|
| pm_actual | **-12.20**, WR 64 | -9.34, WR 66 | -8.33, WR 66 |
| bg | **-68.03** | -63.59 | -55.66 |
| mfe30 | **+29.63**, WR 73 | +31.49, WR 74 | +32.21, WR 74 |
| mfe30a040 | **+27.18**, WR 76 | **+31.49 (identical to mfe30!)** | **+32.21 (identical!)** |
| pmwalk | **+26.37** | +29.47, WR 77 | +31.34, WR 77 |
| pm_mfe30 | **+30.89** | +32.74 | +33.47 |
| pm_mfe30a | **+28.65** | **+32.74 (identical to pm_mfe30!)** | **+33.47 (identical!)** |

Three independent reproduction failures:

1. **n is wrong.** Claim says 45 closed mirror trades; the book had **47** at 18:15 and **48** at 18:20
   (trades 16627/16629/16630 closed during the claim→audit interval; the book grew twice *during this audit*).
2. **The armed rows cannot be produced by the shipped code.** `MFE_EXIT_ARM_PCT = 0.0`
   (hermes_constants.py:2023), so `arm_price = 0.0*100 = 0` and `mfe30a040` **is** `mfe30` — observed
   identical in both runs. The claim's distinct +27.18/+28.65 required temporarily editing the constant to
   `0.004`. The constants comment asserts those numbers as if they were a reproducible artifact; they are not,
   from the committed state.
3. **No run of the delivered artifact reproduces the claimed numbers**, and no candle-cutoff time does either
   (forensic sweep, `mfe_audit_forensic.py`: best reconciliation is T=18:15 → bg -68.09 but mfe30 still +30.27
   vs claimed +29.63; mfe30 never falls below +30.27 at any cutoff ≥16:25).

### Restricting to the claim's own cohort (first 45 by close_time — identified because its pm_actual sums to **-12.20 exactly**, matching the claim)

Independent replay, complete candles, snapshot 18:45 UTC:

| row | claim | my replay (45) | Δ | reproduced? |
|---|---|---|---|---|
| pm_actual | -12.20 / WR 64 | **-12.20 / WR 64** | 0.00 | ✅ exact |
| bg | -68.03 | **-62.93** (was -63.45 @18:25, **-65.34 @18:35**) | +2.6…+5.1, *moving* | ❌ |
| mfe30 | +29.63 / WR 73 | **+30.27 / WR 73** | +0.64 | WR ✅, net ❌ |
| mfe30a040 | +27.18 / WR 76 | **+27.10 / WR 76** (arm 0.40 hardcoded in *my* code) | -0.08 | ≈✅ (only after editing the constant) |
| pmwalk | +26.37 | **+27.12** | +0.75 | ❌ |
| pm_mfe30 | +30.89 | **+31.53** | +0.64 | ❌ |
| pm_mfe30a | +28.65 | **+28.57** | -0.08 | ≈✅ (same constant caveat) |

So: **pm_actual exact; armed rows within 0.08; unarmed mfe rows off by 0.64–0.75 (unexplained, no cutoff time
reconciles them ⇒ almost certainly an earlier iteration of the v4 code produced the claim); bg off by up to 5
and not stable at all.**

### What DID reproduce (credit where due)

* **The engine is correct.** My independently written replay matches the unmodified sim on **288/288
  per-trade exits** (exit price *and* tag), probed by importing `jup_exit_sim` and wrapping `replay_layers`.
* pm_actual comes **straight from DB `pnl_pct`** (jup_exit_sim.py:253 `float(t['pnl_pct'])`), not a replay —
  confirmed: 48/48 rows equal price%×leverage within 0.06; claim's -12.20 for the 45 sums exactly.
* Win-rate claims reproduce exactly (mfe30 73%, mfe30a040 76%, pm_actual 64%).
* Fee arithmetic and ranking claim reproduce (see F-8).
* Direction of the headline ("mfe30 ≫ bg") survives under every convention I tested.

---

## (b) Hand-checks, end-to-end, without touching the sim's code — **3/3 PASS**

Full bar dumps: `analysis/mfe_audit_handcheck.out`. Arithmetic below is hand-verifiable.

**1. Trade 16540 — SOL LONG, entry 97.97 @ 2026-10-30 06:16:30, lev 5 — claim says `mfe_exit` fires → PASS**
* Entry bar (06:15) skipped by the rule; first bar 06:20 high 98.36 → peak = (98.36/97.97−1)×100 = **0.39808 %**.
* Bar 06:25 threshold = 0.7 × 0.39808 = **0.27866 %** → price 97.97 × 1.0027866 = **98.24300**.
* Bar 06:25 opens **98.16 ≤ 98.24300** → already through threshold at open → fill at open **98.16000**.
* PnL = (98.16/97.97 − 1)×100 = **+0.193937 %** × 5 = **+0.9697** → sim/probe per-trade **+0.97** ✅ (floor 97.18624, TP 99.9294 not touched).

**2. Trade 16573 — ETH SHORT, entry 2229.5 @ 2026-10-30 15:51:37, lev 5 — claim says `mfe_exit` fires → PASS**
* Bar 15:55 low 2226.40 → peak fav = (1 − 2226.40/2229.5)×100 = **0.139045 %**.
* Bar 16:00 threshold = 0.7 × 0.139045 = **0.097331 %** → price 2229.5 × (1 − 0.00097331) = **2227.3295**.
* Bar 16:00 opens **2227.42 ≥ 2227.3295** → already past the giveback level (price too *high* for a short) → fill at open **2227.42** (pessimistic, correct: you cannot fill at 2227.33 when the bar opened above it).
* PnL = (1 − 2227.42/2229.5)×100 = **+0.093296 %** × 5 = **+0.4665** → sim/probe **+0.47** ✅

**3. Trade 16564 — HYPE LONG, entry 91.765 @ 2026-10-30 13:39:42, lev 5 — claim says `floor` fires → PASS**
* Floor = CUT_LOSER(−4.00 % **account**) ÷ 5 = **0.8 % of price** → 91.765 × 0.992 = **91.030880**
  (looser ATR SL 91.765×0.975 = 89.470875 is not the binding stop; TP 93.6003).
* Bar 13:40 high 91.96 → peak 0.21250 %. Bar 13:45: prior-peak threshold = 0.14875 % → 91.9015;
  **low 90.95 ≤ 91.030880 → floor hit, checked before the profit layer** → exit **91.030880, tag `floor`**.
* PnL = (91.030880/91.765 − 1)×100 = **−0.800 %** × 5 = **−4.0000** ✅ exactly the strategy table's −4.00.
* ⚠️ Note: in that same bar the mfe threshold (91.9015) was already breached at the open (91.65 → −0.625 %),
  so *live* code polling every 30–60 s would very likely have exited at ≈ −0.63 instead of −4.00. The
  floor-first ordering therefore **costs** mfe30 3.37 points on this trade (conservative vs. the claim, F-5).

---

## (c) Flaw list (severity: 🔴 high / 🟠 medium / 🟡 low / ✅ clean)

**F-1 🔴 Reproducibility / moving target.** The claim is a snapshot of a live, growing book (45 → 48 during
this audit) replayed against a candle table that is being appended every few seconds. Worse: **`is_closed=1`
does not mean closed** — at 18:42 UTC, 28 of 98 *currently-forming* 5m bars were flagged `is_closed=1`
(the newest bar per token is inserted while still forming). Timeout exits therefore read an in-progress
price, so `bg` moves on its own: measured **-63.45 (18:25) → -65.34 (18:35) → -62.93 (18:45)** on the *same*
45 trades. The claimed -68.03 is neither reproducible nor yet a measurable quantity.
*Fix:* freeze cohort ids + a candle snapshot (or `ts+300 <= run_ts`) before quoting any number; fix the
collector to write in-progress bars with `is_closed=0`.

**F-2 🔴 Selection / strawman baseline ("+98 vs bg").** `bg` = floor(−4 % acct) + ATR-TP(+10 % acct) + 12h
timeout. It loses because **33/45 trades (73 %) touch −0.8 % price at some point within 12h** — a baseline
constructed to lose. The system's *real* behaviour is `pm_actual` = **−12.20**, not −68.03. Decision-relevant
delta = **mfe30 − pm_actual = +42.47**, not +97.66: **the headline overstates the improvement by ~2.3×.**

**F-3 🔴 Statistical power / significance.** n=45, **one period** (entries 2026-10-30 06:16 → 2026-10-31 16:00,
≈1.5 days), **4 tokens, HYPE = 23/45 (51 %)**, **14/44 consecutive entries opened within 15 min** (not
independent — the mirror book fires in bursts). In-sample: the exit was designed on this exact book
(constants comment quotes the same 45T numbers). Against the real book the effect is **not significant**
(see (d)).

**F-4 🟠 Time-window truncation.** **8 of 45 trades' open+12h had not elapsed at audit time**
(16606, 16607, 16609, 16612, 16617, 16618, 16623, 16625); 3 of them (16618, 16623, 16625) are `bg` **timeouts whose exit price keeps changing**
with every new bar (+6.52 / +4.47 / +3.27 as of 18:35). `mfe30` has no unfinished timeouts (it exits in
median 8 min), so mfe30 is observable and bg is not ⇒ the *delta* was quoted from an unfinished measurement.
Mitigating: **0 of 45 real closes exceeded 12h** (max actual hold 3.94 h), so the horizon never truncates
`pm_actual`.

**F-5 🟠 Intra-bar / path assumptions — mfe30 net is not robust (measured, n=48, same code):**

| convention | mfe30 net | vs claim |
|---|---|---|
| claim (entry bar skipped, prior-bar peak, floor first) | **+32.21** | chosen convention |
| entry bar **included** | +26.55 | **−5.66** (entry-bar skip flatters mfe30; bg unchanged at −55.66 → inflates the delta) |
| peak from **current** bar | **+17.07** | **−15.14** |
| profit layer **before** floor | +35.59 | +3.38 ⇒ floor-first is *conservative* (mfe never beats floor: threshold > floor always) |
| all three alternatives | +22.10 | −10.11 |

Band **+17.1 … +35.6**. Direction survives every convention; magnitude (and anything sized off it) does not.
The two conventions that flatter the claim are exactly the two the docstring asserts as "standard/conservative"
(prior-bar peak, entry-bar skip). Live code uses **continuous tick peak + 30–60 s polling** — neither sim
convention is a proven model of it (F-9). Additionally, floor-first can never be *optimistic* for mfe-exit and
the prior-bar peak lowers thresholds — so those two are conservative; the net bias of the package is dominated
by the +5.7 entry-bar skip and the −15 current-bar alternative. Net: **not estimable to better than ±9 points**
around +30.

**F-6 ✅ Unit audit — CLEAN (this is where this codebase usually fails).**
* DB `pnl_pct` **is** leveraged: 48/48 rows = price% × `leverage` exactly; **leverage = 5 on 48/48** (mirror trades are 5x ✔).
* `CUT_LOSER_PNL = -4.00` is **account %**; sim divides by leverage → floor = 0.8 % price, and the in-code
  assert (jup_exit_sim.py:283) holds for every trade.
* `compute_atr_sl_pct(1.0) = 0.025`, `compute_atr_tp_pct(1.0) = 0.02` — **fractions** (2.5 %/2.0 %) ✔, used as
  fractions. Minor: the hardcoded `ATR=1.0` is wrong for real ATR<0.02 (SL would be 1.5–2.0 %), but that only
  affects the `atr_cfg`/`rr*` rows — the walker floor (0.8 %) binds first anyway.
* Walker thresholds are unleveraged price %, PnL multiplied by leverage once at the end ✔.

**F-7 🟠 Selection-on-outcome & survivorship — mostly clean, two dings.**
* Cohort **is entry-driven**: all closed `jup_yolo` trades with entry/exit not null; **0** closed trades
  excluded by the NULL filters; `LIKE '%%jup_yolo%%'` ≡ `LIKE '%jup_yolo%'` (both 48); no other `jup`/`mirror`
  signal families exist that the filter misses.
* 🟠 **Right-censoring:** still-open mirror trades are excluded (16621 SOL SHORT, live −0.54 at audit). Its
  walkers say **−3.14** (no positive SHORT peak → both bg and mfe30 time out) → including it would take mfe30
  from +30.27 to ≈ +27.1. Direction: exclusion flatters mfe30 (and bg equally, so the delta is ~unchanged).
* 🟠 **Contamination of the baseline:** `MFE_EXIT_ENABLED = True` **already** — 2 cohort trades were closed *by
  the exit under test* (16629 +1.28, 16630 +0.04), so `pm_actual` partly contains mfe-exit results.

**F-8 ✅ Fee claim — correct order of magnitude and the ranking claim holds.**
HL taker 0.045 % **of notional** per side (matches in-repo `TAKER_FEE = 0.00045`, position_manager.py:1176) →
round trip 0.09 % of notional → ×5 → **0.45 % of margin = 0.45 `pnl_pct` units per trade** ✔.
Because all walker rows have the same n, a uniform −0.45/trade **shifts every row by the same amount** →
rankings *and deltas* are exactly preserved ✔ (claim's "preserves rankings" is true).
**But** mfe30 net of fees = **+10.02 over 45 trades** (+0.22 %/trade on margin) *before slippage*; these are
stop-market fills reacting within seconds, and a realistic 0.05 % price slip (5m granularity, poll lag) costs
another 0.25 %/trade ≈ −11 ⇒ **the edge is ≈ break-even after costs.**
(Limitation: independent web verification of the published HL schedule was unavailable this session —
`web_search` has no API key and stats-api.hyperliquid.xyz returned HTTP 403 — so the fee rate is verified
against the repo's own constant, not against Hyperliquid docs.)

**F-9 🟠 Sim ≠ live semantics (no equivalence proof).** Sim: 5m OHLC, prior-bar peak, floor-first, exact fills
at threshold, no poll latency, no funding. Live (position_manager §7c): continuous `highest_price`/`lowest_price`
peak, `live_pnl <= peak×0.7` (unit-consistent — `compute_live_pnl` is unleveraged ✔), polled on the manager's
cycle, competing with every earlier section in the loop. The live code has already closed 2 trades; there is
no shadow-vs-sim reconciliation of live fills vs simulated fills.

**F-10 🟠 Anachronistic floor parameter (biases *against* the claim — flagging for accuracy).** During the
entire cohort period `CUT_LOSER_PNL` was **−6.00 % account** (reverted to −4.00 only on 2026-10-31); the sim
uses the current −4.00 → floor 0.8 % instead of the in-force 1.2 %. Re-run with −6.00: **bg −70.48,
mfe30 +37.55** — i.e. the true-period parameters make mfe30 look *better*, and bg closer to the claim's −68.
So this flaw does not rescue the claimed table (mfe30 still ≠ +29.63) but it does mean both bg and mfe30 are
parameterised to a rule that was not in force.

**F-11 🟡 Process / governance.** The exit shipped **live the same day, uncommitted, with no shadow period**
(`MFE_EXIT_ENABLED=True`, working-tree-only diff; HEAD has no MFE exit at all) — bypasses the repo's own
`automatic-implementation` shadow→enforce SOP, and its "sim-checked first" provenance is exactly the table
that fails to reproduce. Sideways: `hermes_constants.py` and `position_manager.py` were **edited while this
audit ran** (mtimes 18:40/18:41) — audits of this book need a pinned commit/hash to be meaningful.

**F-12 🟡 Modelling detail (small, unquantified):** no funding fees (bg holds up to 12h, mfe30 exits in
8 min — helps mfe30 slightly), no fee/slippage anywhere in the table, no modeling of the other real exit
engines (`stale_exit` ×2, `cut-loser` ×1, `hard_max_loss` ×1 fired in this cohort but appear in no walker).

---

## (d) Statistics for mfe30 vs bg (my own per-trade values, claim's 45-trade cohort)

```
mfe30   net +30.27  (W32/L12, WR 73%)
bg      net -62.93…-65.34 (W12/L33, WR 27%)   [drifts: -63.45/-65.34/-62.93 at 18:25/18:35/18:45]
pm_actual net -12.20 (W29/L16, WR 64%)

mfe30 − bg        = +95.61 (claim: +97.66)
  sign test       +33 / −10 (2 ties), two-sided p = 0.0006
  iid bootstrap 95% CI      [+30.07, +154.82]
  token-cluster bootstrap   [+10.48, +211.13]   (only 4 clusters — treat as indicative)

mfe30 − pm_actual = +42.47   ← the decision-relevant comparison
  sign test       +28 / −17, two-sided p = 0.1352   NOT significant
  iid bootstrap 95% CI      [−4.05, +87.52]         INCLUDES 0

mfe30 net alone: iid 95% CI [+9.99, +49.48]; token-cluster [+9.83, +53.95]
  net of −0.45/trade fees: point +10.02, 95% CI ≈ [−10.3, +29.2]  → INCLUDES 0
```

**Does "mfe30 beats bg by ~+98" survive?** Numerically yes — I reconstruct **+95.61** with p=0.0006 and a CI
excluding 0 — **but only against the strawman baseline, on unfinished horizons (8/45), in-sample.** Against the
system's real behaviour (`pm_actual`) the improvement is **+42, p=0.135, CI includes 0**, and after fees the
absolute mfe30 net **also** includes 0. **The +98 statistic must not be quoted as evidence for live use.**

---

## (e) Verdict: **REFUTE** (as stated / as a basis for live decisions)

Not a claim that the exit is bad — a claim that **the published results are not reproducible, overstate the
improvement ~2.3×, and do not demonstrate an edge over the real book after costs.**

**What survives (TRUST-level):** the sim engine is correct (288/288 per-trade exits independently matched),
all three hand-checks pass, `pm_actual = -12.20` reproduces exactly, win rates reproduce, units/leverage/floor
math are clean, the fee arithmetic and "uniform fee preserves rankings" claim are correct, and the *direction*
(mfe-exit > floor/TP/timeout stack, and > pm_actual point estimate) holds under every intra-bar convention tested.

**What is REFUTED:**
1. "Reproducible table" — n wrong (45 vs 47/48), bg off by up to 5 and **not stable**, mfe rows off 0.64–0.75
   with no cutoff time that reconciles them, armed rows **not producible** from the shipped constants.
2. "mfe30 beats bg by ~+98" as a decision statistic — strawman baseline, 8/45 unfinished horizons, correct
   comparison is **+42 with p=0.135**.
3. Implied profitability — **net of taker fees ≈ +10/45 trades, CI includes 0; with slippage ≈ break-even.**

### Caveats that must accompany ANY live decision
1. **Do not quote the claimed table or "+98".** Quote the frozen-cohort, fee-inclusive numbers, with a pinned
   commit hash and a candle snapshot (`ts+300 <= run_ts`).
2. **Re-measure only after every cohort trade's open+12h has elapsed** (last entry 2026-10-31 18:17 → after
   2026-11-01 06:17 UTC) and only on a frozen set of trade ids; re-run twice and diff before publishing.
3. **Fix `is_closed` on in-progress 5m bars** (or exclude `ts+300 > now`) — until then every timeout-based
   number (all of `bg`) is a moving target.
4. **Report mfe30 vs `pm_actual` (the real book), not vs `bg`, as the headline**, with p-value and CI; state
   n=45, 1.5 days, 4 tokens, 51 % HYPE, 14/44 entries within 15 min, in-sample design.
5. **Net of fees and a slippage assumption** (≥0.05 %/trade for stop-market fills) — currently ≈ break-even.
6. **Out-of-sample requirement before sizing up:** ≥2 weeks and at least one other signal book; the exit was
   designed on this exact 45-trade book.
7. **Governance:** `MFE_EXIT_ENABLED=True` shipped uncommitted, same-day, without the shadow→enforce rollout —
   recommend reverting to shadow (False) or at minimum logging counterfactuals (what would the other engines
   have done) until items 1–6 exist. The exit has already closed 2 cohort trades, which also contaminates
   `pm_actual` going forward.
8. **No sim↔live equivalence proof:** live uses continuous peaks + polling cadence; quantify live fills vs the
   sim before trusting any magnitude.
9. Re-verify the armed variant by setting `MFE_EXIT_ARM_PCT = 0.004` **in a scratch copy** and documenting the
   run — the constants comment currently cites numbers the shipped code cannot produce.

*Method note: everything above was re-derived from PostgreSQL (brain `trades`) and `data/candles.db` by
scripts I wrote under `/root/.hermes/analysis/`; the analyst's numbers were treated as untrusted and only
compared after my own values existed.*
