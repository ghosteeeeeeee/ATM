# atr60_momentum — Signal Spec + Backtest Verdict (2026-11-06)

## CEO Thesis (verbatim intent)

> BTC 1m chart: when ATR (only input = length 14) crosses ~60, a move in the
> corresponding MACD/RSI momentum direction plays out — a BIGGER move. BTC
> printed a ~6% long and a ~6% short in the prior 24-48h. Expect the same on
> other coins. "Backtest this — it could be a strong signal before big moves."

Two separable claims:
- **C1 (volatility):** ATR↑60 → a bigger-than-usual move follows. (Direction agnostic.)
- **C2 (direction):** momentum direction (MACD/RSI) at the cross predicts the
  direction of that bigger move.

---

## 1. ATR Definition — PINNED ✅

The chart indicator has exactly one input (`length = 14`). That is the
**TradingView / MT4 / TA-Lib built-in ATR**:

```
TR[i]   = max(high-low, |high-prev_close|, |low-prev_close|)
ATR[14] = RMA (Wilder smoothing): atr = (atr*13 + TR) / 14, seeded with SMA of first 14 TRs
```

**Verification:** our implementation vs `talib.ATR(h,l,c,14)` on BTC 1m =
**max abs diff 0.0** (exact). RSI(14) vs `talib.RSI` = 2.8e-14. MACD hist vs
`talib.MACD(12,26,9)` = converges by bar ~200 (max 4.5e-05 after bar 100;
TA-Lib's internal MACD differs slightly from its own EMA12−EMA26); only 1 sign
disagreement (bar 42), before the first event (bar 304) → no event impact.

**Eyeball-check against your chart** (BTC 1m, Wilder ATR vs SMA variant):

| UTC time | close | ATR (Wilder ✓) | ATR (SMA) | RSI14 | MACD hist |
|---|---|---|---|---|---|
| 2026-11-06 04:55 | 75802.0 | **40.78** | 39.92 | 56.6 | -0.61 |
| 2026-11-05 18:56 | 76204.6 | **79.61** | 75.67 | 56.1 | +4.11 |
| 2026-10-29 20:54 (30d ATR max) | 79101.5 | **245.02** | — | — | — |

If your chart's ATR reads ≈40.8 at 04:55 — we are talking about the same ATR.

⚠️ **bug_hunter re-check 2026-11-06 (BUG-087):** rows 2–3 reproduce exactly
from `candles_1m` BTC, but **row 1 does not**: at 2026-11-06 04:55 the DB has
close **75744.01**, ATR **44.08**, SMA **43.22**, RSI **48.1**, MACD hist
**−4.31** — and close `75802.0` appears **nowhere** in the current 30-day
window (no artifact in the repo contains 75802/40.78 either). Use rows 2–3
for the eyeball check; row 1's provenance is unknown.

⚠️ **Definition matters:** SMA-of-TR instead of Wilder produces 277 raw
crossings vs 201, with only **28% event overlap**. If your indicator is an
SMA-based custom, all numbers below must be re-run (`--atr-sm` switch).

---

## 2. Data

- `candles.db → candles_1m`, token BTC: **42,807 bars**, 2026-10-07 → 2026-11-06
  (30 days), one 6.57h gap, no zero-volume rows.
  ⚠️ This table is a **live rolling 30-day window** (pruned by
  `price_collector.py:856-863`) — counts stay ~42,807 by construction, but the
  exact window is only reproducible as-of run time.
  ⚠️ bug-hunter addendum (BUG-089): the every-60th-bar **baseline** is
  *index*-phased, so front-pruning re-phases it — baseline n/digits swung
  552 → 545 → 487 across three runs on 2026-11-06. Event counts stayed stable;
  baseline columns are statistically consistent (±0.02) but not bit-reproducible.
- 25 other tokens carry full 30-day 1m history (SOL, SUI, TAO, PUMP, GALA,
  GMX, IMX, SAND, …) → cross-coin validation set.
  ⚠️ some alts contain flat O=H=L=C synthetic bars (GMX 61%, IMX 57%, GALA 38%
  of bars) which contaminate their ATR — treat alt ATR% results as approximate.

## 3. Backtest Design

- **Event:** ATR₁₄ crosses UP through T (default $60): `ATR_prev < 60 ≤ ATR_now`.
  Declustered: re-arm only after ATR < 54 (0.9 hysteresis). Raw crosses = 201 →
  declustered = 109 → tradeable = **95** (14 skipped where MACD & RSI disagree/flat).
- **Direction at event close:** MACD(12,26,9) hist sign ⟷ RSI(14) >50 sign,
  must agree (48 LONG / 47 SHORT). Also tested 16 alternative direction rules.
- **Entry:** event bar close. Horizons 15m…24h via timestamp lookup (gap-safe).
  Also tested delay 5/15/30 bars and pullback limit fills (0.5/1.0 ATR).
- **Baseline:** every 60th bar, same direction rule, same measurement.
- **Significance:** bootstrap 95% CI (4,000 rounds, fixed seed) + exact binomial.
- Reproduce: `python3 scripts/backtest_atr60_momentum.py --coin BTC --threshold 60
  --sweep --split --variants --htf --movesize --entry --fresh --recent`

## 4. Results

### C1 — "Bigger move" — ✅ descriptive fact, but ⚠️ it is ATR-STATE clustering, not an event edge (independent audit)

Mean |forward move|, events vs random-time baseline (BTC, n=95 vs ~510):

| Horizon | Event | Baseline | Diff | bootstrap CI95 | Verdict |
|---|---|---|---|---|---|
| 1h | 0.413% | 0.248% | **+0.164%** | **[+0.077, +0.264]** | significant |
| 4h | 0.792% | 0.494% | **+0.297%** | **[+0.138, +0.476]** | significant |
| 24h | 1.296% | 1.192% | +0.105% | [−0.169, +0.394] | not significant |

**Clustering-robust recheck** (62/108 event pairs are <4h apart, so outcome
windows overlap and the CIs above are optimistic; thinned both events and
baseline to ≥horizon spacing):

| Horizon | Event n | Baseline n | Diff | CI95 | Verdict |
|---|---|---|---|---|---|
| 1h (non-overlapping) | 77 | 554 | **+0.206%** | **[+0.100, +0.327]** | **still significant** |
| 4h (non-overlapping) | 50 | 134 | +0.169% | [−0.029, +0.396] | not significant (marginal) |

**⚠️ Independent audit reframe — the decisive control** (baseline = minutes
where ATR≥60 but *not crossing*, n=2,856, events excluded):

| Horizon | Event | ATR≥60 state baseline | Verdict |
|---|---|---|---|
| 1h | 0.413% | 0.438% | events **≤** state |
| 4h | 0.789% | 0.819% | events **≤** state |
| 24h | 1.297% | **1.720%** | events well **≤** state |

→ **The crossing event adds ZERO information beyond "ATR is high."** ATR level
explains >100% of the event-vs-random gap; |move| rises monotonically with ATR
quartile (0.14 → 0.20 → 0.24 → 0.39% @1h). This is volatility clustering —
true but trivial: *of course* minutes after a volatility burst have bigger
ranges. Not a tradable edge by itself.

**Cross-coin replication of C1** (per-coin p85 ATR% threshold, non-overlapping
1h windows, 12 coins): **all 12 diffs positive** (+0.16% … +0.57% mean |1h
move| above baseline), **12/12 individually significant** on the fresh
producer run (earlier ad-hoc run: 8/12), sign-test p(12/12) = 0.0002.
Producer: `python3 scripts/backtest_atr60_momentum.py --c1coins` (added after
own-conclusions N5 — the original table had no producer script):

| | BTC | SOL | SUI | TAO | PUMP | GALA | GMX | IMX | SAND | FOGO | COMP | DYM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| diff% | +0.16 | +0.17 | +0.22 | +0.28 | +0.25 | +0.18 | +0.16 | +0.29 | +0.57 | +0.38 | +0.24 | +0.28 |
| sig | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

⚠️ **own-conclusions N4:** the headline event sample is conditioned on
MACD/RSI agreement (agree-events 0.406% vs skipped-crosses 0.248% @1h) — on
ALL crosses the 1h diff is still +0.143 [CI excludes 0], so the fact stands,
but part of the headline magnitude is selection.

→ The **volatility half of the thesis replicates on other coins** (as you
guessed for the "trend"); the direction half does not.

The expansion is real but **decays**: solid at 1h, marginal at 4h, gone by 24h.
Elevated |move| at every threshold in the T=40…100 sweep.

≥3% move within 24h: **18.9%** of events vs **15.7%** baseline (z=0.79,
p=0.43 — not significant; the events do NOT meaningfully raise the odds of a
big move, they only correlate with bigger *average* range at 1h).

### C2 — "Momentum direction predicts direction" — ❌ NOT CONFIRMED

Direction-aligned return (return × direction), BTC:

| Horizon | n | mean | WR>0 | CI95 | p (vs 50%) |
|---|---|---|---|---|---|
| 15m | 95 | **−0.048%** | **32.6%** | [−0.099, +0.005] | **9.2e-04 (negative!)** |
| 30m | 95 | −0.036% | 37.9% | [−0.099, +0.034] | 0.023 (negative) |
| 4h | 93 | +0.165% | 53.3% | [−0.058, +0.407] | 0.60 |
| 24h | **87** | +0.059% | 46.0% | [−0.311, +0.428] | 0.39 |

*(n shrinks with horizon — bars too close to data end are dropped; audit
found the original p=4.25e-04 was 2× understated by an off-by-one in the
binomial — fixed. The 15m/30m negativity survives Bonferroni ×8.)*

- **Entering at the cross close is significantly BAD in the first 15–30 min**
  (WR 33%) — the cross fires at the extreme of a violent candle; price whipsaws
  against you before any follow-through. You are buying the spike.
- 17 direction rules tested (MACD-only, RSI-only, RSI-extremes, 15m return,
  EMA20/50, 1h/4h return, 15m MACD, agreement variants × entry delays):
  **none** produced a 24h CI excluding zero. Best-looking (delay_15: 4h WR
  56.5%) is a post-hoc variant — not claimable.
- Threshold sweep (T=40/50/60/70/80/100): 24h WR = 42.5/42.5/46.0/35.4/38.6/34.4%
  — at no threshold does direction win on average. T=40 is significantly
  *negative* (CI [−0.647, −0.090]) — mean-reverting, i.e. opposite of thesis.
- Time split (15d/15d): IN WR 43.2%, OOS WR 48.8%, both CIs include 0.
- "Fresh expansion" (first cross after ≥4/12/24h quiet): worse — WR 35–43%.

**The one positive:** on BTC, of the 18 events that produced a ≥3% move in 24h,
**14 went in the momentum direction** (binomial one-sided p=0.015) vs baseline
51.2%. This matches the CEO's anecdote… **but it does not replicate:**

### Cross-coin — ❌ DIRECTION DOES NOT TRANSFER (8 coins, ATR% 0.076)

| Coin | n | 24h WR | ≥3% moves: dir/opp |
|---|---|---|---|
| SOL | 206 | 53.5% | 49/47 |
| SUI | 125 | 45.5% | 40/46 |
| TAO | 165 | 49.4% | 54/46 |
| PUMP | 7 | 28.6% | 2/5 |
| GALA | 320 | 50.6% | 128/121 |
| GMX | 461 | 48.5% | 206/186 |
| IMX | 373 | 48.2% | 145/133 |
| SAND | 137 | 48.9% | 48/42 |
| **pooled** | | | **672/626 = 51.8% (coin flip)** |

All 24h CIs include zero. The BTC 14/18 (p=0.015) does not survive
multiplicity (17 direction rules × 6 thresholds were explored) nor
cross-coin replication → almost certainly a fluctuation.

**Fairer retest — per-coin relative threshold** (each coin's ATR% crossing its
OWN 85th percentile, matching BTC's ~14% above-time, 12 coins incl. BTC):

- Pooled 24h direction-aligned WR: **47.9%** (n=1,598) — below coin flip.
- Pooled direction of ≥3% moves: **690/1,361 = 50.7%** — pure coin flip.
- Every coin's 24h CI includes zero. BTC again leans (12/4, p=0.038) but with
  12 coins tested, ≥1 such deviation is expected by chance (~46%).

→ The directional claim fails under both threshold methods (absolute BTC$ and
per-coin percentile).

### Entry timing (direction fixed at cross)

| Scheme | 4h WR | 24h WR | 24h CI95 |
|---|---|---|---|
| at cross close | 53.3% | 46.0% | [−0.311, +0.428] |
| delay 15 bars | 56.5% | 51.7% | [−0.298, +0.475] |
| pullback 1.0 ATR | 58.1% | 48.8% | [−0.205, +0.602] |

All include zero. No entry timing rescues C2.

### Case study: the two moves you saw (last 72h — `--recent` is a fixed 3-day window)

| Move | Window | ATR>60 events around it | Outcome if traded |
|---|---|---|---|
| **PUMP +7.21%** | 11-04 03:08 low 75,736 → 15:17 high 81,196 | events 6h BEFORE start: **SHORT** @77,260 (00:18), **SHORT** @76,171 (02:59, RSI 13.2!) | shorts hit **+6.6% adverse** — signal fired 9 min before the bottom |
| (pump continuation) | during pump | **LONG** @78,486 (13:01), **LONG** @78,618 (14:32) | +3.4% more to the top ✅ |
| **DUMP −7.06%** | 11-05 01:53 high 80,918 → 23:10 low 75,208 | **no fresh cross before start** (ATR already >60 from pump); first SHORT cross 12:43 @79,767 — 11h into the dump | short rode remaining **−5.7%** ✅ |

So your memory is right that both a long and a short "worked" — but the same
rule also printed two shorts **at the exact bottom of the pump** (RSI 13,
oversold → falling-knife short, same failure mode as the BANANA lesson). The
aggregate stats (WR 46% @24h) are exactly this coin flip.

---

## 5b. CEO refinement tests (2026-11-06, round 2)

### Hypothesis R2a: direction = established higher-TF trend (spike accelerates it)

Tested with completed 5m/15m/1h/4h bars only (no lookahead), 12 coins,
ATR% cross 0.076%, **three baselines**: random-time, and the audit's
ATR-state-matched control (high-ATR minutes that aren't crossing).

**Pooled ev−state diff at 24h (direction-aligned %):**

| rule | 5m TF | 15m TF | 1h TF | coin signs |
|---|---|---|---|---|
| multi-TF agree (tf+4h) | +0.66 ✅ | +0.77 ✅ | +0.63 ✅ | 10/2 (p=0.019) |
| EMA trend (tf) | +0.34 ✅ | +0.46 ✅ | +0.55 ✅ | 10/2 (p=0.019) |
| MACD (tf) | −0.18 | +0.04 | +0.57 ✅ | 10/2 |
| STRICT (tf trend + 1m MACD/RSI agree) | +0.25 | +0.41 ✅ | +0.45 ✅ | 9/3 |

- At **60m: null or negative everywhere** (same whipsaw as round 1).
- At **4h: positive** for the agree/EMA/STRICT rules (ev−state CI excludes 0
  for 15m/1h STRICT: +0.17/+0.14).
- Absolute numbers (15m-TF multi-TF agree): 24h WR **58.8%**, mean +0.72% vs
  state 48.8%/−0.05%. STRICT@1h: 52.2%, +0.17% vs state 47.4%/−0.28%.
- **OOS time split: DONE** (the old "pending" note was stale as of the
  bug-hunter pass 2026-11-06) — halves reported in §5/§5c: first half
  day-block p=0.068, second half p=0.026; both halves' ev−state positive
  (+0.455/+0.976 audited, +0.493/+0.961 claimed).
- Interpretation: the ATR spike is the moment when a *lagging* trend signal is
  freshest — mechanism is coherent, but effective n is ~30 days of correlated
  crypto.
- ⚠️ **own-conclusions N1/N3/N6 (2026-11-06 evening):** the headline coin-sign
  test **no longer reproduces — fresh runs give 9/3 (p=0.073), not 10/2
  (p=0.019)** (BTC ev−state = −0.005 tie; rolling-window re-phasing, no code
  change). Effective independent coins ≈ **3.0** (pairwise corr 0.268 → design
  effect), so any coin-sign p is nominal. Day sign test 19/30 = p 0.10; the
  day-block CI only excludes 0 when **paired** ([+0.172,+1.385]; unpaired
  cluster bootstrap [−0.41,+1.98] ∋ 0). Net: **plausibly real conditional
  statistic, not a sized edge — shadow-only, ≥30 forward days, day-blocked CI
  before any size** (auditor #2's recommendation, now better justified).

### Hypothesis R2b: continuum score (<50 short, >50 long) — ❌ REFUTED on BTC

`continuum.db` (213k rows, 30s sampling, Aug→now) as direction at ATR↑60
events, full horizons, three baselines:

> **Reproduce note (BUG-084):** this table was computed against **recorded**
> `continuum.db` scores. Since R2d the script prefers `continuum_replay.db`,
> so a plain `--cont` now prints the R2d-style BTC row (37.8%) instead — use
> **`--cont --cont-db recorded`** for this table. bug-hunter re-run 2026-11-06:
> cont_50 24h 32.7% vs claimed 34.0% (±1 event of window drift, conclusion
> unchanged); **sub-claim "15m/30m ev−state significantly negative" did NOT
> reproduce** — fresh recorded run: −0.031 [−0.10,+0.03] / −0.019
> [−0.11,+0.07], both n.s.

| rule | 24h WR | 24h mean | ev−state @24h |
|---|---|---|---|
| cont_50 | **34.0%** | −0.42% | +0.06 [−0.27, +0.39] null |
| cont_55 (dead zone 45-55) | 34.7% | −0.40% | +0.10 [−0.23, +0.46] null |
| cont55 + 1m MACD/RSI agree | 35.6% | −0.26% | +0.20 [−0.30, +0.67] null |
| cont55 + 1h EMA agree | **25.0%** | −0.83% | +0.06 [−0.33, +0.44] null |

The continuum score is a slow composite — at violent spike moments it lags
into the wrong side (bears the spike bottoms). 15m/30m ev−state significantly
*negative*. One isolated positive cell (cont55+1m @480m, +0.41 [+0.08,+0.81])
among 28 tests = expected false positive.

---

### Hypothesis R2c: FLIPPED continuum (CEO: "previous move was OVER when the new ATR spike occurred" → fade the score) — ✅ direction works, but it's not event-specific

BTC, ATR↑$60 events, `--cont-flip` (state baseline B1 spacing bug fixed):

> **Reproduce note (BUG-084):** use **`--cont-flip --cont-db recorded`** (this
> table is recorded-score based). bug-hunter re-run 2026-11-06 reproduces
> **exactly**: cont_50_flip 67.3%/+0.378 (n=98), cont55_flip+1m 70.8%/+0.719
> (n=24), cont55_flip+1h 48.8%/−0.423 (n=41); state/rand means drift ±0.03
> from rolling-window baseline re-phasing (BUG-089).

| rule @24h | n | ev WR | ev mean | state mean | rand mean | ev−state |
|---|---|---|---|---|---|---|
| cont_50_flip (≥50→SHORT) | 98 | **67.3%** | +0.378% | **+0.534%** | +0.039% | −0.156 [−0.65,+0.34] |
| cont_55_flip (dead zone 45-55) | 93 | 66.7% | +0.357% | +0.477% | +0.057% | −0.120 n.s. |
| cont55_flip + 1m agree | 24 | **70.8%** | +0.719% | +0.368% | +0.010% | +0.350 n.s. (tiny n) |
| cont55_flip + 1h agree | 41 | 48.8% | −0.423% | −0.326% | −0.510% | −0.098 n.s. |

**OOS halves (cont_50_flip @24h):** first half **72.0%** (n=50, mean +0.532),
second half **62.5%** (n=48, mean +0.218) — CEO predicted 60-70%, data landed
there. **Also no first-hour whipsaw:** 15m WR 59.3% / 30m 57.4% (contrarian
entry buys the dip instead of chasing the spike).

**But the honest reading:** ev−state is *negative* (n.s.) — the same flipped
rule at OTHER high-ATR minutes did *better* (+0.53%). Decomposition:

| cont_50_flip @24h | mean dir-aligned |
|---|---|
| random times | +0.04% (rule does nothing) |
| any high-ATR minute (state) | **+0.53%** |
| at the ATR cross (event) | +0.38% |

→ The edge lives in **"fade the continuum direction while volatility is
high"**, not in the crossing event. Statistically this is also the **post-hoc
mirror** of the R2b-refuted rule (auditor: "inverted mapping gives 66% — needs
forward test"); the CEO's mechanism + successful 60-70% prediction give it a
real forward rationale, but same data. BTC-only (continuum.db has no other
tokens), n≈100, so it cannot be cross-coin validated.

**Candidate B (BTC-only):** `cont_fade` — during ATR≥60 (state version) or at
the cross (event version), direction = opposite of continuum score, 24h hold.
Weaker event-specific evidence than `atr_trend_accel`, higher absolute WR.

---

### Hypothesis R2d: per-coin continuum — measure BUILT ✅, direction does NOT transfer ❌

**Deliverable:** `scripts/continuum_replay.py` reconstructs the production
ContinuumEngine score for ANY token (stateful hysteresis/duration/smoothing
replayed over 1m history) → `data/continuum_replay.db`. **Validated on BTC:
Pearson 0.963 / Spearman 0.965 / sign(50) agreement 90.2%** (42,096 pairs vs
recorded continuum.db). All 12 study coins replayed (~42.3k scores each).

**Cross-coin direction at ATR↑ events (12 coins, ev vs ATR-state, 24h):**

| rule | n | abs WR | ev mean | ev−state CI | coin signs | OOS halves |
|---|---|---|---|---|---|---|
| cont_50 (unflipped) | 3,916 | 52.2% | +0.124% | **+0.293 [+0.12, +0.47]** | 9/3 | h1 +0.17 n.s. / h2 **+0.38 sig** 10/2 |
| cont_50_flip | 3,916 | 46.9% | −0.124% | **−0.293 [−0.47, −0.12]** | 3/9 | h2 **−0.38 sig** 2/10 |
| cont_55 | 3,690 | 52.0% | +0.132% | +0.338 [+0.15, +0.52] | 9/3 | h2 +0.40 sig |

**But BTC disagrees with the alts on the absolute direction:**

| BTC (replayed scores, 24h) | n | WR | mean | ev−state |
|---|---|---|---|---|
| cont_50 | 98 | **37.8%** | −0.284% | +0.065 n.s. |
| cont_50_flip | 98 | **62.2%** | +0.284% | −0.065 n.s. |

→ Two problems: (1) **sign inconsistency** — BTC wants the flip (62% vs 38%),
alts weakly want the original (52.2%, ev−state sig 9/3); a fleet-wide rule
cannot be both. (2) even where significant, the alt edge is small (WR 52.2%,
+0.29% ev−state — half the trend-accel edge) and half-dependent (h1 n.s.).
BTC's flip has no event-specific edge at all (ev−state ∋ 0 — it's the
state-level effect from R2c). **Continuum direction is not a usable fleet
measure; `atr_trend_accel` remains the strongest candidate.**

---

## 5. Verdict

| Claim | Status | Evidence |
|---|---|---|
| ATR↑60 → bigger move vs random times (1h) | ✅ descriptive | +0.206% CI [+0.100, +0.327] non-overlapping |
| …but the CROSS adds nothing beyond ATR state | ❌ tautology | events ≤ ATR≥60-state baseline at every horizon (audit) |
| …volatility replicates on other coins | ✅ confirmed | 12/12 coins positive diff, 8/12 sig, p=0.0002 |
| …big (≥3%) moves lean momentum direction (BTC, 30d) | ⚠️ 14/18, p=0.015 | **fails cross-coin + multiplicity** |
| momentum direction (1m MACD/RSI) predicts avg24h direction | ❌ refuted | WR 34–56% everywhere, all CIs include 0 |
| enter at cross close | ❌ refuted | WR 33% at 15m, p≈0.001 (fresh 1.05e-3; whipsaw against) |
| transfers to other coins (1m direction) | ❌ refuted | pooled 51.8% dir on 8 coins |
| **R2a: established-TF trend direction @24h (after spike)** | ✅ **OOS-confirmed (magnitude)** / ⚠️ sign-test unstable | ev−state +0.49/+0.96 both halves sig; coin signs **10/2 p=0.019 → 9/3 p=0.073 fresh** (N1), effective coins ≈3 (N3) |
| **R2b: continuum score <50/>50 direction** | ❌ refuted (BTC) | BTC 24h WR 34-36%, ev−state null |
| **R2c: FLIPPED continuum (BTC)** | ⚠️ works, not event-specific | BTC 67.3% WR (72/62.5 OOS) but ev−state −0.16 n.s. — state-level effect |
| **R2d: per-coin continuum direction** | ❌ does not transfer | alts unflip +0.29 sig 9/3, BTC wants flip 62% — sign inconsistency; measure itself built+validated (ρ=0.96) |

**Bottom line (round 1):** the original thesis is half right as stated —
ATR(14,1m)↑60 marks elevated volatility (trivial: ATR state, not the event),
but 1m MACD/RSI direction at the cross is a coin flip and entering there loses
in the first 15–30 min.

**Bottom line (round 2):** direction must come from the **established
higher-TF trend**, and the payoff horizon is **24h, not 1-4h**. The ATR spike
appears to mark trend *acceleration onset* — same trend rule that LOSES at
random high-ATR minutes wins at crossing minutes (ev−state > 0, both halves;
magnitude verified three ways, though the coin-sign test is unstable per
own-conclusions N1/N3). First-hour whipsaw still applies — any implementation
must survive it.

## 5c. Independent audit #2 (round 2) — R2a & R2b CONFIRMED, with qualifications

Auditor re-implemented everything from scratch (talib + own events/rules/stats,
nothing imported): `/root/.hermes/audit/R2_FINAL_REPORT.md` (commit 45fd5fb4),
code `audit/r2_verify.py` / `audit/r2_addendum.py`.

- **R2a CONFIRMED** — every headline number reproduced ±0.01 (full-window
  15m+4h agree ev−state +0.773 vs claim +0.773; abs WR 58.7% vs 58.8%;
  OOS halves +0.455/+0.976 vs +0.493/+0.961). **Zero lookahead found.**
- **R2b CONFIRMED (exact)** — cont_50 24h WR 34.0%, mean −0.421% exact;
  fairness checks pass (score ≤ event ts, staleness median 16s).
- **Null tests on the key cell (15m+4h agree, +0.773):** iid bootstrap
  [+0.54,+1.00] → **day-cluster [+0.151,+1.343]** (CIs were 2.6× too narrow);
  day sign-flip p=0.0073; circular time-shift p=0.0027; high-ATR-sequence
  shift p=0.0092 — all reject.
- **Qualification:** first-half significance is iid-only (day-block p=0.068);
  second half holds (p=0.026). Hypothesis was generated on this same rolling
  30-day window → the "OOS halves" are stability checks, not true OOS;
  effective n = 30 days; effect size likely inflated.
- **Bugs:** B1 continuum_study state baseline missing `last_s` update (fixed);
  B2 iid bootstrap (use day-block); B3 state grid re-phases on window prune
  (STRICT row drifts ±0.06 on live-DB drift alone). No conclusion flips.
- **Auditor's build recommendation:** shadow signal = `15m+4h agree`, ATR
  cross 0.076%, 0.9 hysteresis, enter event-bar close, hold 24h, log
  ATR-state counterfactual, require ≥30 forward days with day-block CI
  excluding 0 before any size. True OOS is only possible forward — the rolling
  window makes historical re-verification impossible.

---

## 6. Recommendation (pending CEO decision)

Round 1 (original thesis): do **not** ship as a directional entry signal —
it fails the signal-lab quality bar (WR>52%, avg PnL>0.05%).

Round 2 gives one buildable candidate. **Independent audit #2 returned
CONFIRMED** (see 5c), with its build recommendation adopted:

### Candidate: `atr_trend_accel` (shadow first, per add-signal checklist)

- **Event:** ATR(14,1m) crosses up through per-coin threshold (0.076% BTC-eq
  or own-p85), declustered (hysteresis 0.9).
- **Direction:** established multi-TF trend — primary `15m+4h EMA20/50 agree`
  (best OOS consistency); alternates `macd_1h`, `slope6_1h`.
- **Hold:** ~24h (NO edge at 1h — must survive the first-hour whipsaw;
  SL must be wider than the 15-30m adverse excursion).
- **Evidence:** pooled 12-coin 24h WR 58.8% mean +0.72% gross; ev−state
  +0.77 day-block CI [+0.15,+1.34] (iid CI was 2.6× too narrow); 10/12 coin
  signs; day sign-flip p=0.0073, circular-shift p=0.0027; OOS halves hold
  (2nd half day-block p=0.026, 1st half p=0.068); fee drag ~0.1% round trip.
- **Caveats:** hypothesis generated on this same 30-day window (halves =
  stability checks, not true OOS), effective n=30 days, correlated coins,
  effect size likely inflated, first-hour whipsaw, 4h edge weaker than 24h.
- **Auditor's sizing rule:** log ATR-state counterfactual in shadow; require
  ≥30 forward days with day-block CI excluding 0 before any size.

### Other options (unchanged from round 1)

- **A:** `atr-expansion` regime/confluence flag only (uses the confirmed
  volatility fact, not direction) — safe, modest value.
- **B:** shadow-only directional collection for the original 1m-momentum
  thesis (backtest says expect null).
- **C:** drop.

## 7. Reproduce / files

- Backtest: `scripts/backtest_atr60_momentum.py` (deterministic, fixed seeds)
  - round 1: `--coin BTC --threshold 60 --sweep --split --variants --htf
    --movesize --entry --fresh --recent`
  - round 2: `--cont [--cont-flip] [--half first|second]
    [--cont-db recorded|replay]`,
    `--pooled --pct 0.076 [--half first|second] [--tfs 15m]`
    (score source: **replay** = default = R2d tables; **recorded** =
    `continuum.db` = R2b/R2c tables — see BUG-084 notes in §5b)
  - ATR definition sensitivity: `--atr-sm`
- Per-coin continuum: `scripts/continuum_replay.py` — replays the production
  ContinuumEngine pipeline (stateful hysteresis/duration/smoothing) over any
  token's history → `data/continuum_replay.db`. **Validated on BTC: Pearson
  0.963 / Spearman 0.965 / sign(50) agreement 90.2%** vs recorded continuum.db
  (42,096 matched pairs). Replay all 12 coins: `--all`.
- Audit #1 (round 1): `/root/.hermes/audit/FINAL_REPORT.md`, checker
  `/root/.hermes/audit/audit_check.py` — negative findings SOUND, C1 reframe
  adopted, binomial off-by-one fixed.
- Audit #2 (round 2): `/root/.hermes/audit/R2_FINAL_REPORT.md` (commit
  45fd5fb4), `audit/r2_verify.py`, `audit/r2_addendum.py` — R2a/R2b
  CONFIRMED ±0.01, no lookahead, day-block qualifications adopted.
- bug-hunter pass: BUG-082…090 (9 bugs, 8 fixed; `--cont-db recorded|replay`
  restores exact R2b/R2c reproduction; see §7b).
- own-conclusions verdict: `/root/.hermes/brain/verdicts/20261106-2030-verdict.md`
  (commit d3a7a6ff, scripts in `audit/own/`) — spec honest, **no lookahead
  proven mechanically** (prefix recompute, 12 coins, 0 mismatches); adopted
  downgrades: N1 coin-signs 10/2→9/3, N2 **replay scores run +6.55 pts hot vs
  recorded** (27.7% >10 pts off — log this before any replay-based signal goes
  live), N3 effective coins ≈3, N4 conditioning, N6 day-block pairing, N5
  `--c1coins` producer added.

### 7b. bug_hunter re-run spot-check (2026-11-06, BUG-082…089)

Every row re-executed fresh (actual runs, not memory):

| claim | fresh rerun | verdict |
|---|---|---|
| main header raw/dec/trade/skip 201/109/95/14 | 207/110/97/13 | drift (rolling window, disclosed) |
| C1 1h abs-move diff +0.164 CI [+0.077,+0.264] | +0.162 CI [+0.077,+0.262] | ✅ |
| ≥3% moves: 14/18 in direction, p=0.015 | 14/18, p=0.0154 | ✅ exact |
| C2 15m WR 32.6%, p=9.2e-4 | 33.0%, p=1.05e-3 (k=32/n=97) | ✅ binomial verified vs exact fractions; 1 event drift |
| sweep 24h WR 42.5/42.5/46.0/35.4/38.6/34.4 | 42.3/42.5/47.1/35.4/39.7/33.3 | ~✅ drift ≤1.1pp |
| time split IN 43.2% / OOS 48.8% | 39.1% / 56.1% | ⚠️ drift — anchor `ev[0]+15d` moves with window prune |
| R2a pooled 15m+4h agree ev−state +0.77, WR 58.8%, mean +0.72, 10/2 p=0.019 | +0.787, 58.9%, +0.734, 10/2 p=0.019 | ✅ |
| R2d BTC replay rows: cont_50 37.8%/−0.284, flip 62.2%, n=98 | 37.8%/−0.284, 62.2%, n=98 | ✅ exact (replay = default) |
| R2b via plain `--cont` = 34.0% | 37.8% — but 32.7% with `--cont-db recorded` | ❌→✅ source switch, BUG-084 fixed |
| R2c via plain `--cont-flip` = 67.3% | 62.2% — but **67.3% exact** with `--cont-db recorded` | ❌→✅ source switch, BUG-084 fixed |
| replay validation ρ=0.963/0.965, sign 90.2%, n=42,096 | 0.9631/0.9654, 90.1%, n=42,097 | ✅ |
| ATR eyeball rows 2–3 (79.61 / 245.02) | exact | ✅ (row 1 unverifiable — BUG-087) |
| case study events 11-04 00:18/02:59 SHORT, 13:01/14:32 LONG, 11-05 12:43 SHORT | all present, same RSI/ATR | ✅ (window was 72h, not 96h) |
