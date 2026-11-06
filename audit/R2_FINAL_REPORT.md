# Independent Audit — Round-2 claims R2a / R2b (`backtest_atr60_momentum.py`)

**Auditor:** adversarial re-computation from raw `candles.db` + `continuum.db`.
No code imported from the audited script: indicators via TA-Lib (0.6.8), events /
direction rules / outcomes / baselines / half split / all statistics re-implemented
from the claim text in `audit/r2_verify.py` (outputs `audit/r2_verify_out.txt`) and
`audit/r2_addendum.py` (`audit/r2_addendum_out.txt`).

**Script audited:** `/root/.hermes/scripts/backtest_atr60_momentum.py` (1,521 lines,
mtime 2026-11-06 06:16). Author's own fresh runs reproduced in parallel:
`audit/r2/author_full.txt`, `author_half1.txt`, `author_half2.txt`, `author_cont.txt`.

**Data pinned:** live rolling 30-day `candles_1m` (pruned every minute, round-1
finding still applies). My window 2026-10-07 06:39 → 11-06 06:39 UTC, ~20–40 min
shifted from the claim's run → exact reproduction impossible; tolerance = window
drift. This turned out to be ±0.01 on headline numbers.

---

## 1. Per-claim verdicts

| # | Claim | Verdict | My independently computed numbers |
|---|---|---|---|
| R2a-1 | Full-window pooled ev−state @1440m: 15m+4h agree **+0.773** [+0.548,+1.009] 10/2 n=2198 | **CONFIRMED** | **+0.773** iid CI **[+0.549,+0.998]**, **10/2**, n=**2193** (claim n=2198 = drift). Absolute ev: mean **+0.721%**, WR **58.7%**, n=2193 (claim +0.723 / 58.8% / 2198). |
| R2a-2 | ema_15m +0.462 [+0.283,+0.637] 10/2 | **CONFIRMED** | **+0.466** [+0.296,+0.638], **10/2** |
| R2a-3 | ema_1h +0.548 [+0.372,+0.722] 10/2 | **CONFIRMED** | **+0.545** [+0.364,+0.719], **10/2** |
| R2a-4 | macd_1h +0.574 [+0.393,+0.747] 10/2 | **CONFIRMED** | **+0.575** [+0.410,+0.742], **10/2** |
| R2a-5 | slope6_1h +0.381 [+0.203,+0.557] 10/2 | **CONFIRMED** | **+0.382** [+0.202,+0.552], **10/2** |
| R2a-6 | STRICT@15m +0.413 [+0.134,+0.684] 9/3 | **CONFIRMED (within drift)** | **+0.393** [+0.116,+0.669], **9/3** (author's own fresh run: +0.354 — this small-n row is the most window-drift-sensitive, see bug B3) |
| R2a-7 | macd_5m −0.177 [−0.352,+0.005] 3/9 | **CONFIRMED (within drift)** | **−0.174** [−0.349,+0.003], **2/10** (one coin flips at the boundary) |
| R2a-8 | OOS **first** half: 15m+4h +0.493 [+0.133,+0.855] sig; macd_1h +0.632; slope6_1h +0.335; ema_15m +0.302; others n.s.; none significantly negative | **CONFIRMED under claim's iid CI** | 15m+4h **+0.455** [+0.109,+0.812]; macd_1h **+0.634**; slope6_1h **+0.333**; ema_15m **+0.280** [+0.023,+0.528]; ema_1h +0.092 n.s.; macd_5m −0.138 n.s. — all match |
| R2a-9 | OOS **second** half: 15m+4h +0.961 [+] 11/1; macd_1h +0.528 11/1; slope6_1h +0.446 10/2; ema_15m +0.648 10/2; ema_4h +0.475 sig; macd_5m −0.253 sig (2/10) | **CONFIRMED** | +0.976 [+0.659,+1.290] **11/1**; +0.536 **11/1**; +0.453 **10/2**; +0.656 **10/2**; ema_4h **+0.477** [+0.246,+0.708]; macd_5m **−0.242** [−0.483,−0.001] **2/10** |
| R2a-10 | "significant positive in **both** halves" (day-block scrutiny) | **PARTIAL** | True under the claim's iid event bootstrap. **Day-cluster bootstrap**: first half **[−0.45,+1.36] includes 0**, day sign-flip **p=0.068** one-sided (16 days) → not significant; second half [+0.14,+1.73], **p=0.026** → significant. Full window survives everything (below). |
| R2a-11 | 60m ≈ 0/negative everywhere; 240m first-half pos, second n.s. | **CONFIRMED** | 60m: every rule |diff| ≤ 0.044, all CIs span 0, both halves. 240m first half: 15m+4h +0.243 [+0.095,+0.399] sig, macd_1h +0.187 sig, 2 borderline; second half only ema_1h sig (+0.154) → "mixed" as claimed. |
| R2b | cont_50 @ BTC $60 events 24h WR **34.0–35.6%**, means −0.26…−0.42, ev−state CIs include 0; cont55+1h **25.0%** | **CONFIRMED (exact)** | cont_50: n=100, WR **34.0%**, mean **−0.421%** (claim 34.0% / −0.42 — exact); cont_55 **34.7%** / −0.403; cont55+1h-agree **25.0%** (exact); ev−state **+0.064** CI **[−0.271,+0.394]** ∋ 0. Author's own run: +0.064 [−0.266,+0.388] — identical. |

All 12 coins, ≥6 required for (a): per-coin table computed for 15m+4h agree,
ema_15m, macd_1h on **all 12** (`r2_verify_out.txt` §per-coin). Pooled signs match
claim exactly (10/2 for the three headline rules). Equal-weighted per-coin mean
diffs are smaller than pooled but same sign: 15m+4h **+0.535**, ema_1h +0.386,
macd_1h +0.285, ema_15m +0.220, slope6_1h +0.171, macd_5m −0.104.

---

## 2. Lookahead / construction audit — PASS (no lookahead found)

| Check | Where | Result |
|---|---|---|
| HTF direction uses only completed bars | `_last_completed_idx` `:903-908` | k = last bar with `bar_ts+iv ≤ t`, t = event-bar **open** → HTF bar closed **≥60 s before the entry price** (event close). Conservative, not lookahead. Alt convention (completed by entry time) changes diffs by ≤0.01 (sens. 2: 15m+4h +0.784 vs +0.773). |
| Continuum score ≤ event time | `score_at` `:1167-1169` | `bisect_right(cts, t)-1` → last score with ts ≤ t. No lookahead. Entry-time variant (t+60): WR 37.0% — still bad. |
| State baseline excludes event bars | `pooled_ceo` `:1368`, `continuum_study` `:1233` | ✓ `i not in ev_set` |
| Half split = each coin's own midpoint, applied to events AND both baselines | `:1323-1328` (ev, base), `:1361-1370` (state) | ✓ `(ts[0]+ts[-1])/2` per coin; state recomputed within half; equivalent to script semantics (verified by reproducing first/second-half numbers to ±0.02) |
| Sign test counts coins where ev mean > state mean | `:1403-1415` | ✓ (my counts match claim: 10/2, 11/1, 9/3) |
| Event definition: ATR(14) Wilder cross-up through 0.076%, hysteresis re-arm <0.9× | `find_events` `:161-177` | ✓ talib ATR ≡ script tv_atr (round-1 max diff 0); my counts per coin (BTC 106, SOL 239, … FOGO 817) |
| Outcomes from event-bar close, exact ts horizon | `outcomes` `:196-215` | ✓ entry = event close; horizon bar close = entry + h minutes exactly. Gap fallback now requires `jj > i` (`:206-210`) — round-1 bug 2.2 (`or`-falsy-0) **fixed** |
| Binomial two-sided p | `:376-378` | ✓ round-1 bug 2.1 **fixed** (`binom_p_ge(n_e - k, n_e)`) |
| `--pct` default | `:1478` | ✓ now 0.076 (round-1 issue 2.9 fixed) |

---

## 3. Bugs found (current working copy, file:line)

**B1 (medium) — `continuum_study` state baseline is NOT hourly spaced —
`scripts/backtest_atr60_momentum.py:1230-1235`.**
```python
last_s = -10**18                       # :1230
for i in range(len(ts) - 15):
    if (atr[i] is not None and atr[i] >= threshold
            and i not in ev_set and ts[i] - last_s >= 3600):
        state_idx.append(i)            # :1234  <-- last_s NEVER updated
```
`last_s` stays −10¹⁸ → the `≥3600 s` condition is always true → state = **every**
non-event ATR≥$60 bar. Measured: **n=6002 vs 156** if hourly (as claimed).
`pooled_ceo` does it correctly at `:1371`. Effect on R2b: point diff +0.064 (buggy)
vs +0.156 (hourly, CI [−0.272,+0.644]) — **both include 0, conclusion unchanged**;
the buggy CI is too narrow (6,000 overlapping 24h windows treated as iid), which
biases *toward* significance and still didn't reach it. Severity: medium (claim
describes "hourly spaced" state; this function doesn't do it).

**B2 (medium) — event-level iid bootstrap is anti-conservative for every
"significant" statement — `:1382-1392` (`_diff_ci`), also `:1264-1273`, `:264-276`.**
Events are heavily clustered: pooled **median 137 events/day** (max 205), inter-event
gap **p10 = 9 minutes**, 24 h outcome windows overlap, and the 12 coins are one
market. Claim CI for 15m+4h [+0.548,+1.009] (width 0.46) vs my **day-cluster
bootstrap [+0.151,+1.343]** (width 1.19, ~2.6× wider, 30 UTC-day clusters,
cross-coin correlation preserved). The halves' significance is what breaks: first
half iid [+0.109,+0.812] → day-cluster **[−0.45,+1.36]**.

**B3 (medium) — state hourly grid is anchored on the first candidate inside the
rolling window — `:1363-1371`.** Every minute the 30-day head prunes, the first
candidate changes and the **entire hourly state sample re-phases**. Observed live:
STRICT@15m state mean **−0.260 (claim) → −0.240 (my run, +6 min) → −0.201 (author
run, +10 min)** → the printed ev−state row moved 0.413 → 0.393 → 0.354 within ~10
minutes of DB drift, without any code change. Within-window phase offsets (0/15/30/
45 min) are stable (±0.01), so big-n rows are safe; small-n rows (STRICT, cont_*)
carry ±0.05 unreported uncertainty. Same family as round-1 issue 2.5.

**B4 (low) — horizon-dependent survivorship persists — `outcomes` `:196-215`.**
Bars whose forward ts is past data end silently drop (n 2271→2257→2193 across
60/240/1440). Affects ev and state alike → diff not materially biased; reporting
should state n per horizon (it does).

**B5 (low) — `load_candles` still doesn't filter `is_closed` — `:49-56`**
(round-1 2.8 persists). Newest bar can be partial; events are ≥15 bars from the
end, so no impact here.

**B6 (low) — `|base` is still an index-grid sample — `:1322`** (round-1 2.5).
Tested all 60 phases: ev−base @1440 = **+0.629…+0.684** (15m+4h), +0.341…+0.388
(ema_15m), +0.479…+0.526 (macd_1h) → phase noise does **not** threaten the result.

**B7 (low) — sign test assumes independent coins, no min-n — `:1403-1415`.**
PUMP contributes **3 observations** to the 1440m cell yet its −0.578 counts the
same as FOGO's 496 observations. 10/2 one-sided p=0.019 is nominal only (crypto
beta → effective p larger). Day-block nulls supersede it.

**B8 (informational) — data quality:** PUMP has **8 events total** (3 usable at
1440m) — round-1 already flagged n=7; GMX/IMX/GALA/SAND have 38–61 % flat
synthetic bars contaminating ATR (round-1). Excluding all four **raises** the
headline diff to +0.979 → contamination does not manufacture the effect.

**Suspicions checked and CLEARED:** (i) `STRICT`/`ema_4h` keys colliding across the
5m/15m/1h passes — `store` is **local to each `pooled_ceo` call** (`:1302`), so each
pass prints its own row; not a bug. (ii) in-progress HTF bars — `_load_htf` doesn't
filter `is_closed`, but `_last_completed_idx`'s time condition excludes any bar that
hasn't ended. (iii) round-1 bugs 2.1/2.2/2.9 are fixed (see §2).

---

## 4. Null tests (rule **15m+4h agree**, full window, 1440m, ev−state = +0.773)

| Null / CI | Result | p |
|---|---|---|
| iid event bootstrap (claim method, 4000 rnd) | [+0.536, +1.005] | — |
| **Day-cluster bootstrap** (30 UTC-day clusters, all coins resampled together) | **[+0.151, +1.343]** excludes 0 | — |
| **Day-paired sign-flip** (mean day diff +0.749, 30 days both-present) | — | **p₁=0.0073, p₂=0.0153** |
| **Circular TIME-shift** (common Δ across coins, preserves cross-coin alignment + event clustering, 4000) | — | **p₁=0.0027** |
| **Circular shift WITHIN each coin's high-ATR sequence** (conditions on ATR≥thr, per-coin offsets, 4000) | — | **p₁=0.0092** |
| Halves, day-cluster / sign-flip | first **[−0.449,+1.362]** p₁=0.068 (16 days); second [+0.137,+1.735] p₁=0.026 | first n.s. |

Day-cluster CIs @1440 full window for the other headline rules (all exclude 0):
ema_15m [+0.057,+0.881], ema_1h [+0.058,+1.011], macd_1h [+0.238,+0.921],
slope6_1h [+0.054,+0.703], 1h+4h [+0.077,+1.127], 5m+4h [+0.153,+1.175],
ema_5m [+0.017,+0.670]. **Not** excluding 0: STRICT@15m [−0.052,+0.814],
ema_4h [−0.021,+0.811], macd_5m [−0.383,+0.009] (negative).

**Robustness battery (all hold):** unspaced state (every non-event high-ATR bar,
n=172k) → diff **+0.931**, day CI [+0.202,+1.595]; hourly state at 4 grid phases
→ +0.764…+0.775; excl. flat-bar coins → +0.979; excl. PUMP → +0.767;
BTC/SOL/SUI/TAO only → +0.453; equal-weighted per-coin → +0.535; exact-ts outcomes
(no gap fallback) → +0.775; HTF-completed-by-entry-time → +0.784.

---

## 5. Multiplicity judgment

Round 2 tests ≈ 16 rules × 3 horizons × 3 windows (full/first/second) ≈ **144
pooled cells**, on top of round 1's sweep (6 thresholds × 12 directions × 5 HTF
rules × …). At iid α=0.05 that's ~7 expected false positives — and indeed ~8 rows
are "significant" at 1440m-full. **However the observed pattern is not what
selection noise looks like:**

- all 5 *trend-structure* rules (EMA20/50 at 15m/1h, 1h slope, ±4h agreement) are
  positive with **10/12 coin signs**, day-cluster CIs excluding 0 — they are
  correlated variants of one hypothesis, not 5 independent lottery tickets;
- the structure across horizons is coherent and falsifiable in advance:
  **≈0 at 60 m, +0.14 at 240 m, +0.77 at 1440 m**, and the one *negative* rule
  (macd_5m, short-TF momentum) is negative in both the full window and the second
  half — an artifact process does not produce an ordered horizon profile plus a
  correctly-signed negative control;
- three *orthogonal* nulls (day sign-flip, common-Δ circular shift, high-ATR
  circular shift) each reject at p = 0.003–0.015 for the headline rule; Bonferroni
  over ~6 effectively independent trend-rule variants → p ≈ 0.02–0.09.

**But two caveats keep this from "confirmed live edge":**
1. The hypothesis family was *generated on this same 30-day window* (round 1 →
   round 2). The "OOS halves" test temporal stability, **not** out-of-sample
   replication — both halves were visible when the hypothesis was formed. Effect
   size is therefore almost certainly inflated (winner's curse).
2. Effective sample for inference is **30 days**, not 2,193 events. First-half
   day-block p=0.068 shows the margin. Selection-adjusted, honest uncertainty is
   roughly "p ≈ 0.01–0.05, magnitude likely overstated by 30–50 %".

**Verdict on multiplicity:** the specific pattern is *plausibly real*, not a
multiple-comparison artifact — but the backtest alone cannot size it.

---

## 6. R2b fairness — no bug unfairly tanks the continuum

- Score alignment correct (last ts ≤ event ts, `:1167-1169`); staleness at events:
  **median 16 s, p90 27 s**, only **1/110** events stale >300 s (excluding it:
  WR 34.3 % — unchanged).
- Sampling granularity irrelevant: looking up at entry time (ts+60) → WR 37.0 %;
  exact-ts-only outcomes → 34.0 % (identical).
- The B1 state bug (B1 above) does **not** drive the refutation: corrected hourly
  state → diff +0.156 CI [−0.272,+0.644] ∋ 0, same conclusion.
- Context the claim omits (does not rescue the score): cont_50 direction was bad
  **everywhere** this window — hourly grid WR **45.1 %** (n=683), high-ATR state
  **36.1 %** (n=5375), events **34.0 %** — i.e. events are *no worse than state*
  (ev−state n.s.), and the score added nothing at ATR spikes. BTC fell −10.5 % over
  the window; at events the score was 76×SHORT/34×LONG, and the 24 LONG calls lost
  −1.25 % on average (that's where −0.42 comes from); direction-neutral 24 h fwd at
  events = −0.18 %, WR 50 % — BTC went nowhere after BTC-$60 ATR events, the score
  just picked the losing side.
- Caveat: the inverted mapping gives WR **66.0 %** (mirror of 34 %) — a post-hoc
  contrarian reading of the same 100 events. Do **not** believe it without a
  forward test.

**R2b verdict: CONFIRMED** as stated (numbers exact, no bug, fair test of the
CEO's ≥50→LONG mapping), with the note that the 34 % is a property of the score
direction in this window generally (45 % on all hours), not something specific to
ATR events.

---

## 7. Overall verdict — is this worth a shadow signal?

**The finding is SOUND as a descriptive conditional statistic and worth building a
shadow signal on — it is NOT yet a validated edge, and must not be sized from this
backtest.**

Why sound:
1. Every headline number reproduces independently to ±0.01 with my own code
   (window drift accounts for the rest), and the author's fresh runs agree — the
   claims are honest recomputations.
2. **No lookahead anywhere**; construction details (state excludes events, own-
   midpoint halves on ev+both baselines, sign test definition, completed-bar HTF)
   all check out; round-1 bugs 2.1/2.2/2.9 fixed.
3. The effect survives **three orthogonal clustering-aware nulls** (p=0.003–0.015),
   day-cluster CIs, state-grid phase variation, contaminated-coin exclusion,
   equal-weighting, exact-ts outcomes, and an alternative HTF convention; the
   60 m ≈ 0 / 240 m small / 1440 m large horizon profile and the negative
   macd_5m control argue against artifact.

Why not yet tradeable:
1. Hypothesis generated on the same rolling window it was "validated" on — the
   OOS halves are stability checks, not true out-of-sample; day-level n=30; first
   half alone is p=0.068 day-block; ~144 round-2 cells plus the round-1 sweep.
2. Execution realism: fill at the event bar's own **close** (zero latency), no
   fees/slippage, 24 h holding period, no edge at 60 m (whipsaw) — you only get
   paid if you catch the cross *and* hold; state baseline ≈ 0 means "being in
   high-vol with the trend" earns nothing — the cross itself must be informative.
3. `candles_1m` is a rolling 30-day window — the claim can never be re-verified
   historically; forward collection is the only true test that remains possible.

**Recommended shadow spec:** rule = `15m+4h agree` (largest, most robust: +0.77
pooled / +0.53 equal-weighted / day CI [+0.15,+1.34]); trigger = ATR(14,1m) crosses
up through 0.076 % of price with 0.9 hysteresis; direction = EMA20>EMA50 on
completed 15 m **and** completed 4 h agree; entry = event bar close; horizon 24 h;
log event **and** ATR-state counterfactual daily; require ≥30 forward days with a
day-block CI excluding 0 (and both signs across halves) before considering any
size. Treat `macd_5m` negative and STRICT/ema_4h day-CIs-including-0 as evidence
the family is trend-structure, not momentum — do not ship the momentum variants.

---

### Files written
- `audit/r2_verify.py` — independent full re-implementation + null tests (+R2b)
- `audit/r2_verify_out.txt` — its raw output
- `audit/r2_addendum.py` — robustness addenda (state variants, halves×horizons,
  coin composition, grid phases, continuum staleness/inversion)
- `audit/r2_addendum_out.txt` — its raw output
- `audit/r2/author_full.txt`, `audit/r2/author_half1.txt`,
  `audit/r2/author_half2.txt`, `audit/r2/author_cont.txt` — the audited script's
  own fresh runs (reproduction check)
- `audit/R2_FINAL_REPORT.md` — this report
