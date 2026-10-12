# Independent Verdict: SHORT RSI Habitat Spec
Date: 2026-10-12
Auditor: own-conclusions (fresh eyes, no priming)

Audited: `/root/.hermes/plans/short-rsi-habitat-spec.md`
Method: Reproduced every query against PostgreSQL (`dbname=brain`) myself, read the actual
enforcement code in `signal_compactor.py` / `decider_run.py` / `hermes_constants.py`, and
checked pipeline logs. No number below is taken from the spec.

---

## Actual Data Findings

### Q1 — Reproduced the spec's query exactly. The table is REAL.

The spec's table reproduces byte-for-byte. This is a genuine, reproducible result:

| fam | band | n | WR | pnl |
|-----|------|---|----|-----|
| grind | 25-35 | 6 | 50.0% | −0.10 |
| grind | 35-45 | 7 | 14.3% | −0.72 |
| grind | 45-55 | 5 | 40.0% | −0.28 |
| hzscore | 25-35 | 5 | 60.0% | −0.03 |
| other | **<25** | **105** | **58.1%** | **+0.39** |
| other | 25-35 | 97 | 51.5% | −1.54 |
| other | 35-45 | 97 | 45.4% | −3.09 |
| other | 45-55 | 83 | 50.6% | −0.86 |
| other | 55-65 | 48 | 50.0% | −0.60 |
| other | 65-75 | 43 | 53.5% | −0.64 |
| other | 75+ | 19 | 47.4% | −0.99 |
| pump-chain | <25 | 8 | 50.0% | −0.81 |
| pump-chain | 25-35 | 9 | 44.4% | +0.01 |
| pump-chain | 35-45 | 27 | 48.1% | −0.37 |
| pump-chain | **45-55** | **41** | **48.8%** | **+0.15** |
| pump-chain | 55-65 | 19 | 42.1% | −0.07 |
| pump-chain | 65-75 | 9 | 66.7% | +0.01 |
| pump-chain | 75+ | 5 | 0.0% | −0.22 |

Coverage: 662 of 778 SHORT closed trades (85.1%) have a usable meta `rsi_14`. The `HAVING >= 5`
filter hides 130 trades in sub-5 cells.

**Reproducibility: PASS. Statistical validity: FAIL.**

Exact binomial p-values (H0: WR=50%) and Wilson 95% CIs, all computed by me:

| cell | n | WR | p(WR=50%) | 95% CI | pnl |
|------|---|----|-----------|--------|-----|
| other<25 (60d) | 104 | 57.7% | 0.141 | [48.1, 66.7] | +0.38 |
| other<25 **(last 30d)** | 17 | 41.2% | 0.629 | [21.6, 64.0] | **−0.53** |
| accel<25 (60d) | 55 | 49.1% | 1.000 | [36.4, 61.9] | +0.57 |
| pump-chain 45-55 | 41 | 48.8% | 1.000 | [34.3, 63.5] | +0.15 |
| pump-chain 40-45 | 19 | 63.2% | 0.359 | [41.0, 80.9] | **+0.48** |
| pump-chain 35-45 | 27 | 48.1% | 1.000 | [30.7, 66.0] | −0.37 |
| grind (all) | 21 | 33.3% | 0.189 | [17.2, 54.6] | −1.16 |

**No cell in the spec reaches p<0.05. Every single "habitat" claim is statistically
indistinguishable from a coin flip.** This is exactly the failure mode AGENTS.md warns about
("All habitat filters were p=0.18–0.29").

### Q2 — The "other <25" edge is NOT a general pattern. It is one signal.

Breaking down `other<25` (31 distinct signal strings):

```
accel_300_v                32T  59.4% WR  +1.25   <-- 30.5% of trades, 320% of the pnl
ichimoku_,r2_trend_short    4T 100.0% WR  +0.32
[r 22 signal strings with n=1, all 100% WR, +0.01 to +0.12 each — pure noise combos]
r2_trend_short              4T  75.0% WR  -0.03
accel_300_v2_short         10T  30.0% WR  -0.10
bb_bounce_short             3T  66.7% WR  -0.06
```

`accel_300_v` alone is +$1.25. The **entire rest of `other<25` sums to −$0.86.** The
headline "+$0.39 band edge" does not exist without a single signal inside it.

Concentration: top-1 = 30.5% of n, top-3 = 50.5%, HHI = 0.129. And 22 of 31 strings are
single-trade 100%-WR cells — the band is padded with noise.

### Q3 — Isolated accel vs non-accel inside `other<25`

| slice | n | WR | pnl |
|-------|---|----|-----|
| ALL other<25 | 104 | 57.7% | +0.38 |
| **EXCL accel\*** | 49 | **67.3%** | **−0.19** |
| ONLY accel\* | 55 | 49.1% | +0.57 |

Note the inversion: the non-accel population has a *higher* win rate (67.3%) but *negative*
PnL. The +$0.39 headline is entirely size-asymmetry from `accel_300_v`, not a win-rate edge.

`accel_300_v` full band grid (this is the real "habitat", and it is not <25):

```
<25     55T  49.1%  +0.57      45-55   4T  25.0%  +0.05
25-35   36T  47.2%  +0.08      55-65   5T  60.0%  +0.10
35-45   23T  30.4%  -0.55      65-75   2T   0.0%  -0.08
```

Its WR at <25 is 49.1% — below coin flip. The band "works" only via payout asymmetry.

### Q4 — Meta RSI data quality: 14.9% missing, and the missing ones were the winners

- SHORT closed 60d: **778**
- With usable meta `rsi_14`: **662 (85.1%)**
- Missing/invalid: **116 (14.9%)**

Missing-RSI trades by signal: `pullback-entry-` 26, `pump-chain-` 25, `wave_catcher` 11,
plus cascade/mover/accel/r2_trend variants.

**Outcome by RSI availability:**

| subset | n | WR | pnl |
|--------|---|----|-----|
| has_rsi | 662 | 50.0% | **−10.14** |
| missing_rsi | 116 | 48.3% | **+2.80** |

The entire RSI-keyed analysis is conditioned on the *losing* population. Any habitat rule
derived from meta-RSI trades excludes the profitable segment by construction.

### Q5 — SHORT_RSI_HARD_FLOOR enforcement is real and heavy

Code verified:
- `signal_compactor.py:3961–3981` — approval-time `[SHORT-RSI-HARD-FLOOR]`, computes RSI from
  `candles_5m` closes with an **ad-hoc 14-period formula** (not Wilder smoothing).
- `decider_run.py:1144–1147` — detection/live hard floor, **no bearish override**, plus
  **fail-closed**: both live and detect RSI `None` ⇒ SKIP (line 1150–1151).
- `decider_run.py:2035–2037` — exec-time `[EXEC-RSI-HARD-FLOOR]`, fail-closed if exec RSI
  unavailable (line 2029).
- `hermes_constants.py:905` — `SHORT_RSI_HARD_FLOOR = 45`, raised 25→45 on 2026-10-07.
- `hermes_constants.py:899` — a *separate* `SHORT_RSI_CEILING = 65` already exists.

Log evidence (log covers only 2026-10-02→10-12; no August logs exist):

| day | EXEC-RSI-HARD-FLOOR blocks (raw, lines double-logged → ~half real) |
|-----|------|
| 10-03 | 2 |
| 10-05 | 14 |
| 10-06 | 23 |
| **10-07** (floor raised) | **78** |
| 10-09 | 45 |
| 10-10 | 28 |

Approval-time blocks: **1,071** in the compressed 10-02→10-10 log, **2,166 on 2026-10-12
alone**. Top blocked tokens: BTC (276), CHIP (199), CFX (155), FIL (124), APT (119).
Caveat: approval blocks are per-minute re-evaluations of the same candidate set, not unique
opportunities — real distinct blocks are on the order of ~30–50/day.

### Q6 — Temporal bias: the <25 edge is an August artifact and has fully reversed

`<25` SHORT trades by month (all families):

| month | n | WR | pnl |
|-------|---|----|-----|
| 2026-08 | 75 | 62.7% | **+0.92** |
| 2026-09 | 35 | 45.7% | **−1.29** |
| 2026-10 | 8 | 37.5% | **−0.34** |

`accel<25` by month: Aug +1.12 → Sep −0.21 → Oct −0.34. Same reversal.

30d vs 30–60d split for `other<25`:

| window | ALL | EXCL accel | ONLY accel |
|--------|-----|-----------|-----------|
| last 30d | 17T 41.2% **−0.53** | 9T 44.4% −0.19 | 8T 37.5% −0.34 |
| 30–60d | 87T 60.9% +0.91 | 40T 72.5% +0.00 | 47T 51.1% +0.91 |

**The profitable band is entirely in the 30–60d (i.e. August) window. In the last 30 days it
is negative on every slice.** Re-proposing to unblock it is out-of-sample failure in real time.

---

## Claim Verification

### Claim 1: "pump-chain SHORT habitat = RSI 45-55 (41T, 48.8% WR, +$0.15)"
**Verdict: PARTIAL**
- Actual: 41T / 48.8% / +$0.15 — the numbers reproduce exactly.
- But WR is **48.8%, below coin flip**, p=1.000, CI [34.3, 63.5]. The +$0.15 comes from
  payout asymmetry in 41 trades, not a win-rate edge. Calling this a "habitat" (implying a
  directional edge) is not supported; it is at best "not harmful".
- Claimed: habitat + "floor correctly placed". The number is right; the inference is not.

### Claim 2: "other signals habitat = RSI <25 (105T, 58.1% WR, +$0.39)"
**Verdict: DISAGREE**
- Actual: numbers reproduce (105T/58.1%/+$0.39), but
  1. **Concentration**: `accel_300_v` = 32T/+$1.25; everything else in the band = **−$0.86**.
  2. **Reversal**: Aug +0.92 / Sep −1.29 / Oct −0.34; last 30d = 17T 41.2% **−0.53**.
  3. **Significance**: p=0.141 (60d), p=0.629 (30d). Neither significant.
  4. **Category error**: "other" is **83 distinct signal strings, 492T, −$7.33 aggregate**.
     It contains `pullback-entry-` (93T −1.50), `bb_bounce_short` (65T −0.44),
     `ema300_dip_short` (23T −1.48), `macd_div` (32T −0.12) — signals with opposite
     personalities. A shared "habitat" for this bucket is not a finding.
- Claimed: a general habitat for a coherent signal family. Not true on any reading.

### Claim 3: "grind SHORT loses everywhere"
**Verdict: PARTIAL**
- Actual: 21T total, 33.3% WR, −$1.16; all three visible bands negative (−0.10 / −0.72 / −0.28).
- Directionally supported, but **n=21, p=0.189** — not statistically established. "Loses
  everywhere" is a stronger statement than 21 trades can carry.
- Note: leaving grind on the default floor of 45 does not help — its 45-55 band is also
  negative (5T, 40%, −0.28). The spec's handling is harmless but not evidence-driven.

### Claim 4: "current floor of 45 blocks the profitable <25 band for other signals"
**Verdict: DISAGREE**
- Actual (true part): the floor does block it. After 2026-10-07, **1 of 17** SHORT trades
  with meta RSI has RSI<45. Enforcement is confirmed active and heavy (Q5).
- Actual (false parts):
  1. The band is **not currently profitable** — it reversed negative in September and stays
     negative in the last 30 days (Q6). The spec is trying to recapture an August effect.
  2. **The spec's own proposal does not unblock "other" at all.** `SHORT_RSI_HABITATS` has no
     entry for `other`, `pullback-entry-`, `accel_300_v`, `bb_bounce_short`, or
     `ema300_dip_short`. Under the spec's design rule 4 ("not found ⇒ default floor 45"),
     every one of those signals keeps the exact same 45 floor. The problem is diagnosed and
     then not fixed for the population it was diagnosed in.
  3. `accel_300_v`'s standalone bypass is disabled and marked `NEVER_REENABLE`
     (`hermes_constants.py:3261`), so the historical path its <25 trades used no longer exists.

### Claim 5: "pump-chain floor at 45 is correctly placed (blocks the negative 35-45 band)"
**Verdict: DISAGREE — the stated justification is factually inverted**
- Actual, splitting the spec's own 35-45 bucket:

| band | n | WR | pnl |
|------|---|----|-----|
| 35-40 | 8 | 12.5% | **−0.85** |
| **40-45** | **19** | **63.2%** | **+0.48** |
| 45-55 | 41 | 48.8% | +0.15 |

  `40-45` is **the best pump-chain band in the entire table** — better than the claimed
  45-55 "sweet spot" on both WR (63.2% vs 48.8%) and PnL (+0.48 vs +0.15). And it is recent:
  **last 30d 40-45 = 18T, 61.1% WR, +$0.44** (i.e. almost the whole band is fresh data).
- The negative band is `35-40`, not `35-45`. The `HAVING`-free but coarse 10-point bucketing
  in Q1 masked this.
- Irony: the spec's proposed `pump-chain: (40, 70)` happens to match the data — but for a
  reason the spec explicitly denies ("40 buffer for exec drift" vs "floor 45 is correctly
  placed"). Both statements cannot be true. The data says the real edge is 40-45, so a min
  of 40 is *data-driven*, and the 45-55 "sweet spot" framing is wrong.

### Claim 6: "the proposed bands in the spec are reasonable"
**Verdict: REJECT**
Checked each proposed family against actual 60d SHORT data (no `HAVING` filter):

| family | spec band | actual 60d SHORT data |
|--------|-----------|------------------------|
| pump-chain | (40, 70) | Supported (see Claim 5) |
| volume-breakout | (30, 75) "needs more data" | **1 trade total** (25-35, +0.10) |
| volume-buildup | (30, 75) "needs more data" | **0 trades** |
| ai-trader | (25, 70) "needs more data" | **1 trade total** (45-55, −0.14) |
| hzscore | (20, 70) | 10 trades across 5 bands, all ≈0 (−0.14/−0.03/−0.04/+0.02/+0.28) |
| **range-reversion** | **(15, 65)** | **0 trades — no data at all** |
| **spike-exhaustion** | **(10, 50)** | **0 trades — no data at all** |
| rs | (20, 70) | 15T, but see mis-mapping below |
| grind | unlisted ⇒ 45 | 21T 33.3% −1.16 |

Two families (`range-reversion`, `spike-exhaustion`) get **aggressive, specific minima of 15
and 10 — a 30–35 point loosening of a hard safety floor — with literally zero trades of
evidence.** These are not derived from anything. Meanwhile `volume-buildup` (0 trades) is at
least honest with "needs more data". The two most dangerous entries in the dict carry no
caveat at all.

**Family mapping is also broken.** The spec's `CASE '%rs-%'` does not select an `rs` signal:
it catches confluence strings like `accel-300-breakout,rs-r130` and `pump-chain-,rs-r54`
(accel/pump-chain combos classified as "rs"). Meanwhile the *actual* common mean-reversion
string `rs_r` (74T, 52.7%, −0.43) does **not** match `'%rs-%'` and therefore falls into
`other` — meaning `rs: (20, 70)` would apply to the wrong signals and the real `rs_r`
population would silently keep the default floor of 45. Same class of bug: `pump_chain`
(underscore) also falls through to `other` because the CASE only tests `pump-chain`.

---

## Risks Not Mentioned in Spec

1. **Measurement mismatch (fatal to the band design).** The bands are derived from
   `_signal_metadata->>'rsi_14'` = **detection-time** RSI. But `decider_run.py:1131/1198`
   enforces on **live/exec-time** RSI (`_ctx_gate_get_rsi`). Per `trade_watchdog.py:214,1070`,
   pre-fix median |diff| between the two was **~13 points**. The spec's "±5 point buffer"
   mitigation is calibrated against a 13-point median drift — roughly 2.5× too small — and
   the spec never acknowledges that its evidence RSI and its enforcement RSI are different
   measurements.

2. **`entry_rsi_14` no longer exists as an independent check (DRIFT-E).** `feature_recorder.py:142-146`
   and `hl-sync-guardian.py:2551` (fix dated 2026-10-10) made `entry_rsi_14` **prefer/copy
   `_signal_metadata.rsi_14`**. I verified: all 662 SHORT trades with both values have
   **mean|diff| = 0.00, max|diff| = 0.00** — they are the same number. So (a) DRIFT-E magnitude
   can no longer be measured from the trades table at all, and (b) any past analysis using
   `entry_rsi_14` before 2026-10-10 used a late/wrong-TF value and should be re-derived from
   meta. The spec cites DRIFT-E as a risk but then proposes bands that cannot be validated
   against it.

3. **Three different RSI definitions in the live path.** `signal_compactor.py:3966-3979`
   computes RSI from 15 `candles_5m` closes with an ad-hoc average (no Wilder smoothing);
   `decider_run.py` uses live RSI from `_ctx_gate_get_rsi`; the analysis uses meta `rsi_14`.
   Adding per-signal bands multiplies the surface without first reconciling these. A band min
   of 15 evaluated against the compactor's ad-hoc 5m RSI is not the same rule as the one the
   data supported.

4. **Re-proposing deliberately reverted work.** The spec's "Bear-structure override: relax min
   by 10" directly contradicts two standing decisions: `decider_run.py:1142` ("HARD FLOOR
   first — no bearish override") and `hermes_constants.py:905` ("No bearish override"), both
   set 2026-10-06/07 after real leaked trades (IMX entry_rsi=14.47, HBAR 24.30 on 2026-10-05,
   see `decider_run.py:1148-1149`). This is re-shipping reverted work — exactly the
   "check existing implementations / don't re-propose shipped work" trap.

5. **Unreconciled collision with the existing ceiling.** `SHORT_RSI_CEILING = 65` and
   `SHORT_RSI_HARD_CEILING` already enforce maxima, with their own exec-time checks
   (`decider_run.py:2049-2076`). The spec's per-signal maxima (`spike-exhaustion` max=50,
   `range-reversion` max=65) are never reconciled with these. Two independent max rules will
   disagree; the spec is silent on which wins.

6. **Survivorship bias — the blocked population's outcomes are unobservable.** All 118 `<25`
   SHORT trades predate 2026-10-07. Since the raise, essentially none exist. The ~30–50/day
   trades the floor blocks today (BTC/CHIP/CFX/FIL/APT at RSI 26–44) can never show a PnL.
   Relaxing the floor would trade into exactly the falling-knife set the floor was raised to
   stop, and the spec's +$0.39 estimate assumes blocked trades behave like August trades.

7. **Analysis-base selection bias.** 14.9% of SHORT trades lack meta RSI and that subset was
   **+$2.80** vs −$10.14 for the subset the entire analysis is built on. Any habitat derived
   only from RSI-tagged trades is derived from the losing population.

8. **Success metrics are stale/wrong.** Spec claims "SHORT trades/day currently ~0-2, target
   3-5". Actual: **3.0/day (last 7d), 5.4/day (14d), 8.3/day (30d)**; since the 10-07 floor
   raise: 18T over 6.0d = **3.0/day**. The stated baseline is wrong and the target is already
   met. "WR currently ~40%" is closer (44.0% at 30d, 28.6% at 7d). Shipping against a false
   baseline makes the success metric unfalsifiable.

9. **Fail-closed path must be preserved.** `decider_run.py:1150-1151` SKIPs when both RSI
   sources are `None`, and `:2029` fail-closes when exec RSI is unavailable. A per-signal
   lookup that returns "no band found ⇒ allow" or that skips when RSI is missing reopens the
   2026-10-05 leak. The spec's implementation steps do not mention this invariant.

10. **No log coverage of the "profitable" era.** Logs exist only for 2026-10-02→10-12. There
    is no way to verify what the floor blocked during August — when the alleged edge existed —
    so block-rate claims cannot be back-checked against the profitable window.

---

## Overall Assessment

# REJECT

**Reasoning:**

The spec passes the one test the author controlled (reproducibility — Q1 reproduces exactly)
and fails every test that matters.

1. **The core evidence is an August artifact that has reversed.** The `<25` band was +$0.92
   in August, −$1.29 in September, −$0.34 in October. In the last 30 days it is negative on
   every slice (17T, 41.2%, −$0.53). Unblocking it today means trading a *reversed* edge.

2. **The headline finding is one signal, not a family.** `accel_300_v` contributes +$1.25
   inside a +$0.39 band; the other 30 signal strings sum to −$0.86. And `accel_300_v`'s own
   WR at <25 is 49.1% — the band "pays" only through payout asymmetry.

3. **Nothing in the spec is statistically significant.** Every cell is p=0.14 to p=1.00 with
   CIs spanning 50%. This is the documented repeat failure ("habitat filters were p=0.18–0.29").

4. **The diagnosis is inverted on the one claim that could have been actionable.** Claim 5
   says 40-45 is negative; it is the *best* pump-chain band (19T, 63.2%, +$0.48, and 30d
   18T/61.1%/+$0.44). The real bad band is 35-40.

5. **The proposal does not fix the problem it describes.** No `other`/`pullback-entry-`/
   `accel_300_v` entry exists, so under the spec's own default rule those signals keep the
   45 floor. Meanwhile the two most aggressive entries (`range-reversion` min=15,
   `spike-exhaustion` min=10) have **zero trades** of supporting data — a 30–35 point loosening
   of a hard safety floor justified by nothing.

6. **The evidence RSI and the enforcement RSI are different measurements** (~13pt median
   drift per `trade_watchdog.py`), and the spec's ±5 buffer is calibrated against a 13pt
   drift. The design is built on a mismatch it never acknowledges.

7. **It re-proposes the bear-structure override that was deliberately removed** on 2026-10-06/07
   after real leaked trades, and collides unreconciled with the existing
   `SHORT_RSI_CEILING`/`SHORT_RSI_HARD_CEILING`.

**What I would approve today, separately, with its own validation:**

- **`pump-chain` min 45 → 40.** This is the one data-supported change, and notably the spec
  argues for it while citing the wrong justification. 40-45 = 19T, 63.2% WR, +$0.48 (60d) and
  18T, 61.1% WR, +$0.44 (last 30d — i.e. current, not August). Ship it as a single isolated
  change with shadow logging, not as part of a habitat framework.
- **Delete `range-reversion`, `spike-exhaustion`, `volume-buildup`, `volume-breakout`,
  `ai-trader`, `hzscore`, `rs` from the dict.** Zero or ~1 trade of evidence each, plus the
  `rs`/`rs_r`/`pump_chain` string-mapping bug that would apply bands to the wrong signals.
- **Fix the family `CASE` mapping before any of this is re-derived** (`rs_r` → its own family,
  `pump_chain` underscore, accel combos not counted as `rs`) and re-run Q1. The current
  buckets are contaminated.
- **Do not touch the bear-structure override or the fail-closed paths.**
- If the `other<25` idea is pursued at all, it must be re-tested on **September+October data
  only** (where it is currently −$0.53) and on the non-accel population (−$0.19) — both of
  which fail. There is presently no version of this edge that survives out-of-sample.
