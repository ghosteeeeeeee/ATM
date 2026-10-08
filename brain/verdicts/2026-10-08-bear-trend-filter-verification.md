# Independent Verdict: BEAR_TREND + Falling Wave Filter

**Date:** 2026-10-08
**Auditor:** Independent verification agent (fresh read — plan, constants, code, DB all read from scratch)
**Artifact verified:** `/root/.hermes/plans/bear-trend-falling-filter.md` (v3)
**Method:** Re-derived every number from PostgreSQL `brain.trades` directly. No number in this document is copied from the plan; all were re-computed via SQL + scipy (`/tmp/stats_audit.py`, `/tmp/audit_670.psv`).

---

## OVERALL VERDICT: **PARTIAL**

The **descriptive statistics reproduce almost perfectly** — 12 of 14 numeric claims matched to the decimal. That is unusual and to the plan author's credit.

However, **the validation methodology contains a fatal flaw** (the "3rd out-of-sample period" is the full in-sample dataset relabeled), the effect **fails multiple-comparison correction** (adjusted p=0.39), the claimed **interaction is itself not statistically significant**, the **wave-phase table does not reproduce at all**, and the stated **time period is wrong by 11 days**.

The filter is *plausible and cheap*, and the PnL effect is statistically robust — but it is **not the proven +1.6% WR edge the plan presents it as**. Ship it to **shadow mode only**, exactly as the plan's own step 1 prescribes. Do not enable it expecting a validated win-rate improvement.

---

## Claim-by-claim

### 1. Core filter effect — AGREE (HIGH)

> "Block 53 trades (8% of total), remove $2.48 in losses, WR 48.5% → 50.1%"

Reproduced exactly on the 670-trade universe (win = `pnl_usdt > 0`):

| Group | n | Wins | WR | PnL | Avg/trade |
|---|---|---|---|---|---|
| BLOCKED (BEAR_TREND + falling) | 53 | 18 | **34.0%** | **-$2.48** | -$0.0468 |
| ALLOWED | 617 | 309 | **50.1%** | -$0.08 | -$0.0001 |
| OVERALL | 670 | 327 | 48.8% | -$2.56 | — |

- 53 blocked ✓, 34.0% ✓, -$2.48 ✓, 50.1% post-filter ✓, 8% of total ✓ (53/670 = 7.9%)
- Overall WR: plan 48.5%, mine 48.8% (327/670). A 2-trade drift consistent with the DB having moved since the plan was written. Immaterial.
- Notes: 29 of 670 trades are zero-PnL and count as losses under `>0`. Under `>=0`, blocked = 41.5% vs allowed = 54.1% — **the gap survives every win definition I tried.**
- The blocked group's -$2.48 is nearly the *entire* sample's -$2.56 loss. Post-filter the book goes to -$0.08.

### 2. BTC regime breakdown — AGREE (HIGH)

> "BULL_TREND 55% vs BEAR_TREND 42%"

Exact match. BULL_TREND 55.2% (n=174, +$0.04) vs BEAR_TREND 41.6% (n=161, -$2.29); 13pp gap ✓. RANGING_BULL 53.3%/+$0.69 ✓, RANGING 53.2%/+$0.16 ✓, TRANSITIONING 45.6%/-$1.47 ✓, RANGING_BEAR 35.3%/+$0.31 ✓. Significance: z=-2.09, **p=0.036**.

### 3. Wave-phase table — DISAGREE (HIGH confidence in my numbers)

> "'falling' has 47% WR and loses $3.16"

**Does not reproduce under any universe I could construct.**

| Wave | Plan WR / PnL | Mine — 670-universe | Mine — full 1252 wave universe |
|---|---|---|---|
| decelerating | 61.8% / +$0.94 | 61.0% / +$1.00 (n=41) | 58.9% / +$0.73 (n=90) |
| bottoming | 56.8% / +$0.96 | 58.8% / +$1.27 (n=68) | 57.1% / +$1.00 (n=126) |
| accelerating | 50.4% / +$1.55 | 49.7% / +$0.69 (n=310) | 51.0% / -$1.78 (n=520) |
| **falling** | **46.8% / -$3.16** | **43.7% / -$4.77 (n=245)** | **51.4% / -$4.98 (n=504)** |
| neutral | *(omitted)* | 16.7% / -$0.75 (n=6) | 58.3% / -$0.41 (n=12) |

The plan also silently drops `neutral`. The *direction* of the claim holds (falling is the worst-profitable wave), but the plan **understates the loss** (-$3.16 claimed vs -$4.77 actual). This table appears to come from a calculation I cannot reproduce — treat all its numbers as unreliable. It does not change the filter decision (the combination cell, §1, reproduces exactly), but it is a reproducibility failure.

### 4. Combined cell — AGREE on numbers, DISAGREE on interpretation (HIGH)

BULL_TREND+decelerating 66.7%/+$0.08 ✓, BULL_TREND+falling 59.4%/+$0.39 ✓, BEAR_TREND+decelerating 46.2%/-$0.21 ✓, BEAR_TREND+falling 34.0%/-$2.48 ✓ — all exact.

**But the "combination" story does not hold statistically:**

- Within BEAR_TREND: falling 34.0% (n=53) vs non-falling 45.4% (n=108) → **p=0.168** (not significant)
- Within falling: BEAR_TREND 34.0% (n=53) vs other regimes 46.4% (n=192) → **p=0.107** (not significant)

The cell is the worst of a grid, not a demonstrated interaction. Blocking *all* `falling` would kill profitable cells (BULL_TREND+falling 59.4%, RANGING_BULL+falling 72.7%), so the plan's surgical choice is defensible on PnL grounds — but "BEAR_TREND + falling" is not a proven worse-than-its-parts combination.

### 5. SHORT direction — AGREE (HIGH)

> "SHORT signals in BEAR_TREND + falling have only 29% WR"

Exact: SHORT blocked n=31, **29.0%**, -$1.88 | allowed n=214, 46.3%, -$3.10 ✓
LONG blocked n=22, 40.9%, -$0.60 | allowed n=403, 52.1%, +$3.02 ✓

### 6. Signal breakdown — AGREE on numbers, caveat on n (HIGH / LOW power)

| Signal | Plan | Mine |
|---|---|---|
| pullback-entry- | 18.2% (n=11) blocked / 50.0% (n=78) | **18.2% (n=11) / 50.0% (n=78)** ✓ |
| pump-chain- | 20.0% (n=10) / 47.7% (n=86) | **20.0% (n=10) / 47.7% (n=86)** ✓ |
| pump-chain+ | 33.3% (n=6) / 46.8% (n=77) | **33.3% (n=6) / 46.8% (n=77)** ✓ |

All exact. But n=6–11 → 95% CIs span ~±30pp. These are anecdotes, not evidence.

### 7. BTC score sub-analysis — AGREE (HIGH)

20-40 bucket: 9.1% (n=11), -$0.81 ✓ | <20 bucket: 40.5% (n=42), -$1.67 ✓ — exact. n=11 caveat applies to the 9.1% figure.

---

## Validation methodology — the fatal flaw

### 8. "Pattern holds across 3 out-of-sample periods" — DISAGREE (HIGH)

**Period 3 is not Sep 28 – Oct 8. It is the full 670-trade dataset, relabeled.**

The plan's Period 3 reports "BLOCKED: 53, ALLOWED: 617" — identical to the full-sample counts in §1 (the plan itself tags it "(original)"). The **true** Sep 28 – Oct 8 slice is:

| True Sep 28 – Oct 8 | n | WR | PnL |
|---|---|---|---|
| BLOCKED | **16** | 37.5% | -$0.45 |
| ALLOWED | **265** | 52.5% | +$0.71 |

So there are only **two** distinct sub-periods, and **all three "periods" are overlapping slices of the same in-sample data**. Nothing was tested out-of-sample.

Verified sub-periods (mine vs plan — small drift from live data):

| Period | Plan | Mine |
|---|---|---|
| P1 "Sep 1-15" | blk 11 / 9.1% / -$1.42; allowed 120 / 57.5% / +$1.51 | blk 12 / 8.3% / -$1.56; allowed 121 / 57.9% / +$1.73 |
| P2 Sep 16-30 | blk 31 / 41.9% / -$0.38; allowed 298 / 45.0% / -$2.40 | blk 30 / 43.3% / -$0.24; allowed 301 / 44.9% / -$2.85 |

Note P2 is nearly a coin flip (43.3% vs 44.9%, $0.24 saved) — the plan presents it as "pattern holds" without comment.

**No true out-of-sample data exists.** `btc_regime` first appears **2026-09-12** (see §11), so the pre-Sep-12 data cannot be tested at all. I ran the only valid forward split available (derive Sep 12-24, test Sep 25 – Oct 8):

- DERIVE: blocked n=34, 32.4% | allowed n=345, 48.1%
- TEST: blocked n=19, **36.8%** (-$0.38) | allowed n=272, **52.6%** (+$1.36)
- Effect persists directionally (+$0.38 saved) but **p=0.18, n=19 — not significant**

### 9. Weekly breakdown / Sep 21 backfire — AGREE (HIGH)

| Week (Mon) | Blocked | Allowed | Works? |
|---|---|---|---|
| Sep 7 | 20.0% (n=5) / -$0.45 | 63.8% (n=58) / +$1.90 | ✅ |
| Sep 14 | 26.3% (n=19) / -$1.62 | 51.1% (n=186) / +$2.33 | ✅ |
| **Sep 21** | **46.2% (n=13) / +$0.04** | **35.2% (n=108) / -$5.02** | ❌ **backfire confirmed** |
| Sep 28 | 41.7% (n=12) / -$0.30 | 55.5% (n=211) / +$1.47 | ✅ |
| Oct 5 | 25.0% (n=4) / -$0.15 | 40.7% (n=54) / -$0.76 | ✅ |

"Works 4/5 weeks" ✓ and "Sep 21 backfire" ✓ — both reproduce (plan: 46.2% vs 34.5%; mine 46.2% vs 35.2%; tiny drift). In the Sep 21 week the blocked group was **flat-positive** while everything else crashed -$5.02 — the filter would have removed the only profitable cohort that week. The backfire itself is noise (p=0.44), but so is any single week in this sample.

---

## Statistical significance — my own calculations (scipy 1.17.1)

**Blocked vs allowed WR:** z = -2.253, **two-tailed p = 0.0243**; Fisher exact **p = 0.0310**, OR = 0.513.
95% CI blocked WR: **[21.5%, 48.3%]** (n=53) — enormous, overlaps the allowed band.

**Per-trade PnL:** mean -$0.0468 vs -$0.0001. Welch t **p=0.0077**; Mann-Whitney (blocked < allowed) **p=0.038**. Bootstrap (10k): improvement **+$2.48, 95% CI [+0.95, +4.06]**, P(>0)=99.9%. **The PnL effect is real and robust.**

**Multiple comparisons — the killer:** I enumerated all 27 regime×wave cells; 16 have n≥10. Ranked by p:

```
BEAR_TREND    falling     n=53  34.0%  p=0.0243  <-- THE PROPOSED FILTER
TRANSITIONING falling     n=59  35.6%  p=0.0335  <-- equally good, never mentioned
RANGING       bottoming   n=12  75.0%  p=0.0670
BULL_TREND    falling     n=64  59.4%  p=0.0753
...
```

- Best raw p = 0.0243; **Bonferroni-adjusted = 0.388 → NOT significant**
- `TRANSITIONING + falling` (n=59, 35.6% WR, p=0.034) is a *statistically indistinguishable* alternative the plan never considered — the signature of best-of-grid selection, not discovery.
- 7 of 16 cells have WR<50% — consistent with a coin-flip null plus noise.

**Loss concentration:** blocked group is not driven by one disaster — 31/53 trades negative, worst single trade -$0.34, 5 worst = -$1.21 of -$2.48. Median blocked -$0.030 vs median allowed +$0.010. Broad-based, which is mildly reassuring.

---

## Time period misstatement — DISAGREE (HIGH)

> "Time period: Sep 1 - Oct 8, 2026 (5 weeks)"

**False.** `btc_regime` first appears in the DB at **2026-09-12 00:16**. Coverage by week:

| Week | Trades | With btc_regime | % |
|---|---|---|---|
| Aug 31 | 319 | **0** | 0.0% |
| Sep 7 | 331 | 63 | 19.0% |
| Sep 14 | 205 | 205 | 100% |
| Sep 21 | 122 | 121 | 99.2% |
| Sep 28 | 228 | 223 | 97.8% |
| Oct 5 | 59 | 58 | 98.3% |

The real window is **Sep 12 – Oct 8 (~26 days, 3.7 weeks)**, not 5 weeks. The plan's "Sep 7" weekly bin contains only Sep 12–13 trades. 594 of 1264 in-window trades are silently excluded for lacking metadata. "Block 53 trades (8% of total)" = 8% of the *covered* universe; it is 4.2% of all in-window trades. Going forward this matters little (coverage is now ~100%), but the "5 weeks" framing inflates the apparent sample duration by ~40%.

---

## Filter collisions & existing implementations

**No pre-existing BEAR_TREND filter — AGREE.** `grep -r "BEAR_TREND" scripts/` → only `continuum_context.py` (the definition, lines 164/176/330). `BEAR_TREND_FALLING_FILTER_ENABLED` does not exist in `hermes_constants.py`. Nothing is being re-proposed as shipped work.

**No direct collision with SHORT_CONTINUUM — AGREE, with a warning.** SHORT_CONTINUUM blocks SHORT at `score > 60` (`hermes_constants.py` constants, enforced at `signal_compactor.py:2860`); this filter blocks at `score <= 35` (+ linreg BEAR + falling). Bands don't overlap. **But** combining them leaves the 35–60 band fully open, and that band is the *worst* SHORT band in the data:

| SHORT band | n | WR | PnL |
|---|---|---|---|
| ≤35 (this filter removes only 31) | 151 | 43.0% | -$2.14 |
| **35–60 (remains allowed)** | **47** | **40.4%** | **-$2.73** |
| >60 (SHORT_CONTINUUM blocks) | 47 | 51.1% | -$0.11 |

This is exactly the "trapping trades in the worst band" pattern from the 2026-10-08 lesson. Not a blocker here (the filter only removes a subset of ≤35), but **the 35–60 SHORT band should be the next analysis.**

**Partial functional overlap with CONTINUUM-BLOCK** (`signal_compactor.py:2684-2716`): LONGs are already blocked during bearish structure *unless the coin is rising*. The 22 blocked LONGs are therefore trades that **sneaked past the existing gate via the coin-rising override** during BEAR_TREND+falling. This slightly *strengthens* the case (they are precisely the override-abuse trades), but it also means the LONG-side marginal benefit is smaller than the raw numbers suggest.

---

## Implementation feasibility — PARTIAL

Feasible, but the plan's snippet is **not drop-in**. The gates live inside `run_compaction` (~line 2837). At that point **neither `btc_regime` nor `wave_phase` is in scope** — `_btc_ctx_cached` is only built later (lines 3105–3108) and passed into `_score_signal` (line 3189, whose body ends at 2079). The existing SHORT_CONTINUUM gate solves this by querying `continuum.db` directly (2848–2852); the same pattern is used for context at 2784–2785 (`get_btc_trend_context()` → `['regime']`) and for wave_phase at 3087–3094 (`token_speeds`).

Required work (~15–20 lines, not 10): fetch regime via `get_btc_trend_context()` or a `continuum_states` query, fetch wave_phase from `token_speeds`, then apply the gate. **Fail-open on missing data** — the plan's Risk 3 mitigation is correct and mandatory: `wave_phase` is absent on ~1% of trades and defaults to `'neutral'` in some paths, which must NOT be conflated with `falling`.

Also flag for the constants comment: the plan quotes the docstring "BEAR_TREND: score <40", but the actual code (`continuum_context.py:170-176`) requires **`score <= 35` AND `linreg in (BEAR, LEAN_BEAR)` AND `|momentum| <= 0.6`** (momentum>0.6 returns TRANSITIONING first). Comment should state the real rule.

---

## Bottom line

| Claim | Verdict | Confidence |
|---|---|---|
| 53 blocked / 34.0% WR / -$2.48 / allowed 50.1% | **AGREE** | HIGH |
| WR 48.5% → 50.1% | **AGREE** (48.8% by my count; drift) | HIGH |
| BULL 55% vs BEAR 42% | **AGREE** (exact) | HIGH |
| "falling" 47% WR / -$3.16 | **DISAGREE** (actual 43.7% / -$4.77) | HIGH |
| BEAR+falling is a real *combination* effect | **DISAGREE** (p=0.107–0.168) | MEDIUM |
| SHORT = 29% WR | **AGREE** (exact) | HIGH |
| pullback-entry- 18.2% blocked | **AGREE** (exact, n=11) | HIGH (n low) |
| Holds across 3 out-of-sample periods | **DISAGREE** (Period 3 = full sample) | HIGH |
| Works 4/5 weeks, Sep 21 backfire | **AGREE** | HIGH |
| BTC 20-40 = 9.1% | **AGREE** (exact, n=11) | HIGH (n low) |
| No collision with SHORT_CONTINUUM | **AGREE** (flag 35–60 trap band) | MEDIUM |
| Period = "Sep 1 – Oct 8, 5 weeks" | **DISAGREE** (Sep 12 start, 26 days) | HIGH |
| Statistically significant | **PARTIAL** (p=0.024 raw; p=0.39 Bonferroni) | HIGH |
| Implementation snippet is ready | **PARTIAL** (needs data fetch at gate site) | HIGH |

**Recommended action:** Approve **shadow-mode logging only** (plan's step 1), for a minimum of 2–3 weeks, since no genuine out-of-sample data exists yet. Frame the expected edge honestly as *"worst-of-16-cells, nominally significant (p=0.024), fails multiple-comparison correction (p=0.39), robust PnL effect but immaterial in dollars (avg position $13.57), n=53 gives a ±13pp CI on blocked WR."* Do **not** record "+1.6% WR improvement" as a validated expectation. Do **not** enable live until a forward sample confirms it. Fix the plan's Period 3 label, wave-phase table, and time-period statement before it is used to justify enabling.

---

## Sideways findings

1. **`_signal_metadata` coverage gap (MEDIUM)** — `btc_regime` is stamped only from 2026-09-12 onward while `wave_phase` covers 1252/1264 in-window trades. Any regime-based analytics silently drops the first 11 days of September. Consider backfilling regime or hard-failing such analyses.
2. **Wave-phase table unexplained (MEDIUM)** — the plan's §2 numbers match no reproducible universe. Whoever produced it should re-run and reconcile; an unreproducible table in a plan is exactly the failure mode AGENTS.md warns about.
3. **35–60 SHORT trap band (MEDIUM)** — worst SHORT band (40.4%, -$2.73) and it is the only band left open above 35 once SHORT_CONTINUUM + this filter combine. Warrants its own analysis.
4. **Stale docstring (LOW)** — `continuum_context.py:164` says "BEAR_TREND: score <40" but code enforces `score <= 35`. Cosmetic, but it propagated into the plan's constants comment.
5. **Position sizes (INFO)** — avg `amount_usdt` $13.57 (range $11.10–$22.10) on this universe, so "$2.48 saved" is a rounding error in cash terms. The value of this filter is the WR signal, not the dollars.

*All figures independently re-computed from `brain.trades`. Reproduction: `/tmp/stats_audit.py` + `/tmp/audit_670.psv`.*
