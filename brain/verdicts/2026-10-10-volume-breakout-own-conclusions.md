# Independent Verdict: volume-breakout-long Analysis
Date: 2026-10-10
Auditor: own-conclusions (fresh eyes, no priming)

All numbers below were produced by running actual SQL against PostgreSQL
(`dbname=brain user=postgres`) and `/root/.hermes/data/continuum.db`, and by
reading the actual source files. No number is carried over from the brief.

---

## Actual Data Findings

### Q1 — Daily performance, last 14 days (verified)

```
day          trades  wins       pnl   avgRSI(entry_rsi_14)
2026-09-29        2     2   +1.02      60.0
2026-10-01        1     1   +0.82      63.6
2026-10-02        2     2   +0.48      61.9
2026-10-03        1     0   -0.11      55.7
2026-10-05        1     0   -0.27      48.2
2026-10-09        4     4   +0.72      63.7
2026-10-10        7     0   -0.97      69.3
```

Full history (38 trades, 2026-09-12 → 2026-10-10), weekly:

```
2026-09-07   1T 1W  +0.15
2026-09-14  15T 10W +0.62
2026-09-21   4T 2W  +0.62
2026-09-28   6T 5W  +2.21
2026-10-05  12T 4W  -0.52
ALL          38T 22W +3.08  (57.9% WR)
```

By volatility_regime (30d = all 38 trades):

```
EXTREME  19T 13W  +3.56   (68.4%)
HIGH     10T  3W  -0.79   (30.0%)
NORMAL    9T  6W  +0.31   (66.7%)
```

### Q2 — Oct 9 vs Oct 10 trade details (verified)

```
token   open_time              pnl     mfe%     mae%   exit_reason      rsi(entry)
BABY    2026-10-09 21:19:46  +0.30   1.5602   0.0148  stale_exit        51.67
ZEN     2026-10-09 22:21:46  +0.12   1.2099   0.0252  stale_exit        65.52
SEI     2026-10-09 22:57:43  +0.12   1.3434   0.2277  stale_exit        70.43
YGG     2026-10-09 23:01:57  +0.18   5.6200   0.0514  atr_trail_hit     67.09
BABY    2026-10-10 02:09:47  -0.17   0.5914   0.6199  hard_max_loss     72.73
BLUR    2026-10-10 05:17:46  -0.38  -0.0262   0.6029  hard_max_loss     72.82
PURR    2026-10-10 05:21:38  -0.07   0.9843   0.4706  atr_sl_hit       100.00
PUMP    2026-10-10 07:41:27  -0.03   1.0191   0.6079  atr_sl_hit        51.11
WCT     2026-10-10 08:48:36  -0.06  -0.0070   0.6490  hard_max_loss     70.13
AIXBT   2026-10-10 08:51:28  -0.12   0.0415   0.6458  hard_max_loss     62.83
YGG     2026-10-10 17:09:52  -0.14   0.3717   0.6934  atr_sl_hit        55.35
```

Winners MAE: 0.0148 – 0.2277. Losers MAE: 0.4706 – 0.6934. Ranges match the
claim exactly.

### Q3 — `btc_regime` extracted from `_signal_metadata`

```
BABY  2026-10-09 +0.30  RANGING_BULL    (score 60.5, linreg_bias +0.25)
ZEN   2026-10-09 +0.12  BEAR_TREND      (score 25.5, linreg_bias -0.25)
SEI   2026-10-09 +0.12  RANGING_BULL    (score 63.5, linreg_bias +0.125)
YGG   2026-10-09 +0.18  RANGING_BULL    (score 64.4, linreg_bias +0.125)
BABY  2026-10-10 -0.17  RANGING_BULL    (score 53.7)
BLUR  2026-10-10 -0.38  RANGING_BULL    (score 62.0)
PURR  2026-10-10 -0.07  RANGING_BULL    (score 50.0)
PUMP  2026-10-10 -0.03  TRANSITIONING   (score 44.3)
WCT   2026-10-10 -0.06  RANGING_BULL    (score 50.5)
AIXBT 2026-10-10 -0.12  RANGING         (score 49.3)
YGG   2026-10-10 -0.14  TRANSITIONING   (score 74.7)
```

**`RANGING_BULL` appears 3× among winners AND 4× among losers.** The
`btc_regime` label does not separate winners from losers at all. There is no
`ema300_position` key anywhere in `_signal_metadata` — only `btc_regime`,
`btc_score`, `btc_linreg_bias`, `btc_trend_bias`.

### Q4 — BTC continuum state, Oct 9 vs Oct 10 (DECISIVE)

`continuum_states` contains **only timeframe='1m'** (no 5m rows — first query
returned empty until corrected).

Daily dominant states:
- **Oct 9:** BTC oscillated. ABOVE EMA300 dominated 02:00–08:00 and 12:00–14:00
  UTC. During the actual trade window (21:00–23:00) it was **AT**:
  `21:00 AT×111/BELOW×9`, `22:00 AT×91/BELOW×29`, `23:00 AT×120`.
- **Oct 10:** AT EMA300 every hour of the day (with negligible ABOVE blips).

Per-trade join to the nearest BTC continuum row at `open_time` (age ≤ 24s):

```
token   open_time              pnl    ema300  linreg     phase
BABY    2026-10-09 21:19:46  +0.30    AT      LEAN_BULL  DECLINING
ZEN     2026-10-09 22:21:46  +0.12    AT      LEAN_BEAR  DECLINING
SEI     2026-10-09 22:57:43  +0.12    AT      LEAN_BULL  DECLINING
YGG     2026-10-09 23:01:57  +0.18    AT      LEAN_BULL  DECLINING
BABY    2026-10-10 02:09:47  -0.17    AT      LEAN_BULL  CALM
BLUR    2026-10-10 05:17:46  -0.38    AT      LEAN_BULL  DECLINING
PURR    2026-10-10 05:21:38  -0.07    AT      LEAN_BULL  CALM
PUMP    2026-10-10 07:41:27  -0.03    AT      LEAN_BEAR  DECLINING
WCT     2026-10-10 08:48:36  -0.06    AT      LEAN_BULL  RECOVERY
AIXBT   2026-10-10 08:51:28  -0.12    AT      LEAN_BULL  CALM
YGG     2026-10-10 17:09:52  -0.14    AT      LEAN_BULL  DECLINING
```

**All 11 trades — 4 winners and 7 losers — had `ema300_position = 'AT'` at
open time. There is zero separation.**

### Q5 — Performance by BTC `ema300_position` at trade open (90d, all 38 trades)

```
ema300  trades  wins   WR%      pnl
   AT      23    11   47.8   +1.7600
ABOVE      15    11   73.3   +1.3200
BELOW       0     0     -    +0.0000
TOTAL      38    22   57.9   +3.0800
```

Fisher exact, AT (11/23) vs ABOVE (11/15): **p = 0.18** — not significant.
The AT bucket is **still net positive (+$1.76)**. The signal never fires when
BTC is BELOW EMA300 (its own long conditions require strength).

### Systemic check — ALL signals, 60d, by BTC `ema300_position` at open

```
ema300  trades  wins   WR%       pnl
   AT      903   460   50.9    -0.78
ABOVE      741   376   50.7    -8.58
BELOW      698   361   51.7    -2.49
NONE         7     7   100.0   +0.36
```

`AT` is the **least-bad** bucket system-wide. Win rates are essentially
identical (50.9 / 50.7 / 51.7). BTC `ema300_position` is not a meaningful
discriminator for the book as a whole.

---

## Claim Verification

### Claim 1: "Oct 9: 4T 4W +$0.72, avg RSI 63.7"
**Verdict: AGREE**
Actual: 4 trades, 4 wins, +$0.7200, avg `entry_rsi_14` = 63.7. Exact match.

### Claim 2: "Oct 10: 7T 0W −$0.97, avg RSI 69.3"
**Verdict: AGREE (with data-quality caveat)**
Actual: 7 trades, 0 wins, −$0.9700, avg `entry_rsi_14` = 69.3. Exact match.
Caveat: the RSI average is inflated by PURR's `entry_rsi_14 = 100.00`, which is
a 1m-RSI artifact (see S1/S4 below). Using the signal-time 5m RSI from
`_signal_metadata.rsi_14`, Oct 10 averages **64.8** vs Oct 9's **62.6** — the
"elevated RSI" gap narrows from +5.6 to +2.2.

### Claim 3: "Winners had MAE 0.01–0.23%, losers had MAE 0.47–0.69%"
**Verdict: AGREE on the numbers, DISAGREE on the implied causation**
Actual: winners MAE 0.0148–0.2277, losers MAE 0.4706–0.6934. Both ranges match
exactly.
But the separation is **circular**. Losers exited via `hard_max_loss` /
`atr_sl_hit` with stops at roughly 0.47–0.69%, so a loser's MAE is bounded
below *by the stop itself*. Winners that never touched their stop have low MAE
by construction. MAE here is an outcome-contaminated variable — it restates
"losers hit stops" and has no forward-looking predictive content. Do not build
an entry filter on it.

### Claim 4: "BTC was ABOVE EMA300 on Oct 9, AT EMA300 on Oct 10"
**Verdict: DISAGREE — factually wrong at trade time**
Actual: **every one of the 11 trades (winners and losers) had
`ema300_position = 'AT'` at its open time**, verified against the nearest
continuum row ≤ open_time (ages 0–24s). BTC was ABOVE EMA300 on Oct 9 only
*earlier in the day* (02:00–08:00, 12:00–14:00 UTC), when this signal fired no
trades. By the time the 4 winning trades opened (21:19–23:01 UTC) BTC had
already fallen back to AT. The claimed discriminator does not exist in the
data.

### Claim 5: "The signal has NO BTC trend filter"
**Verdict: AGREE**
Read `volume_breakout.py` in full (269 lines). The only gates are: volume
≥ 2.0× 20-bar average, 3-bar price momentum direction, RSI(14) > 50 (long) /
< 50 (short), close vs 20-SMA, cooldown 60m, blacklists, enabled flags, and
open-position/recent-trade skips. No BTC price, EMA300, regime, or continuum
reference anywhere.
One nuance worth stating precisely: `signal_compactor.py` *does* read BTC
continuum state, but only as a **bypass** — the LONG-RSI-CEILING check is
waived when BTC linreg is BULL/LEAN_BULL and EMA300 is ABOVE/AT
(`signal_compactor.py:3909–3927`). That makes the system *more* permissive when
BTC is strong, the opposite direction from the proposed filter.

### Claim 6: "The vol gate blocks in HIGH regime but not based on BTC trend"
**Verdict: AGREE**
`volatility_gate_v2.py` contains, for volume-breakout-long:
- `('HIGH', 'Volume'): 0.0` — family block (line 307)
- `('NORMAL', 'Volume'): 0.0` — family block (line 296)
- `('HIGH', 'volume-breakout-long'): 0.0` and `('HIGH', 'volume_breakout_long'): 0.0`
  — per-signal overrides added 2026-10-10 (lines 433–434)
- `('NORMAL', 'volume_breakout_short'): 1.0` (line 379)
- EXTREME keeps access via `REGIME_SIGNALS['EXTREME']` (lines 196–198)

There is no BTC-trend/ema300 key anywhere in the gate. The gate is purely
volatility-regime-driven.

### Claim 7: "volume-breakout-long was a star signal that broke"
**Verdict: PARTIAL**
- "Star": overstated. 38 trades over 4 weeks totalling +$3.08 is a modest,
  thin signal, not a star.
- "Broke": the 0/7 day *is* unusual against its own baseline. P(0 wins in 7 |
  p=0.579) = **0.0023** (p=0.0078 at p=0.5). So October 10 was genuinely
  anomalous in the raw numbers.
- However, the anomaly **largely dissolves once regime is controlled**. The 7
  losses = 4 HIGH (−$0.73) + 3 EXTREME (−$0.24). HIGH is the signal's
  documented weak habitat (10T, 30% WR, −$0.79 over 30d): 0 wins in 4 HIGH
  trades at p=0.30 gives **p = 0.24** — not significant. EXTREME is its best
  habitat (13/19, 68.4%): 0 wins in 3 gives **p = 0.03**, marginal at n=3.
- Trend: profitable four straight weeks (W1 +0.15, W2 +0.62, W3 +0.62,
  W4 +2.21), then −0.52 this week. One bad week on n=12 is not a structural
  break.

---

## Additional Checks

### 1. Was the RSI ceiling change (95→85) responsible?
**No.** Commit `20c0afb7` landed at **07:44:28 UTC on 2026-10-10**. Only 3 of
the 7 losing trades opened after it (WCT 08:48 RSI 70.13, AIXBT 08:51 RSI
62.83, YGG 17:09 RSI 55.35) — all below **both** 85 and 95, so the change had
no filtering effect on them. No Oct 10 trade had signal-time 5m RSI above 85
(max was BABY at 81.82). Lowering a ceiling makes the filter *more*
restrictive; it cannot create new losses. PURR's `entry_rsi_14 = 100.00` is a
1m artifact — its signal-time 5m RSI was 68.71, so the ceiling would not have
touched it either.

### 2. Was the VOLUME_BREAKOUT_PLUS_ENABLED kill/re-enable cycle responsible?
**Only marginally — 14% of the damage.** Timeline:
- `20c0afb7` 07:44 — RSI ceiling 95→85
- `92e37ddd` 09:20:36 — KILL ("3T 0W last hour"), by which point 5 of 7 losers
  (−$0.83) had already opened
- `764a5ad9` 12:25:12 — CEO re-enable
- Only **one** trade opened after re-enable: YGG 17:09, −$0.14

So 86% of the day's loss happened *before* the kill, and the kill window
(09:20–12:25) saw no signals anyway — it prevented nothing. The re-enable cost
$0.14. The cycle is not the cause.

### 3. Is the MFE/MAE data reliable?
**Population: yes.** 38/38 trades have non-NULL `mfe_pct` and `mae_pct`
(zero missing). Columns are consistently written.
**Interpretation: no** — see Claim 3, the MAE winner/loser split is
definitional, not causal.
**But a real data-quality problem exists elsewhere:** `entry_rsi_14` (trades
table) and `_signal_metadata.rsi_14` disagree on **10 of 11** recent trades,
sometimes wildly:

```
token   entry_rsi_14  meta.rsi_14
PURR       100.00        68.71
YGG        55.35         22.22
BABY       72.73         81.82
ZEN        65.52         72.73
```

These are two different computations at two different moments (1m RSI vs 5m
RSI at detection). Any RSI analysis must name which column it used.

### 4. Do other signals also fail when BTC is at EMA300 — systemic issue?
**No.** Across all signals, 60d: AT 903T 50.9% −$0.78; ABOVE 741T 50.7%
−$8.58; BELOW 698T 51.7% −$2.49. `AT` is the least-bad bucket and win rates are
statistically indistinguishable. Whatever is happening to volume-breakout-long
is not a BTC-at-EMA300 phenomenon.

---

## Root Cause Assessment

**The BTC-trend theory is not supported. It is actively contradicted by the
data.**

1. All 11 Oct 9–10 trades were at `ema300_position = 'AT'` — zero separation
   between winners and losers (Q4).
2. The AT bucket is net **positive** (+$1.76 over 90d); blocking it destroys
   positive expectancy (Q5).
3. Fisher p = 0.18 — the AT-vs-ABOVE win-rate gap is not significant.
4. System-wide, AT outperforms ABOVE (Q5 systemic).
5. The `btc_regime` labels don't separate either — `RANGING_BULL` sits in both
   the winning and losing groups (Q3).

**What actually explains October 10:**

- **HIGH-regime concentration (primary, already fixed).** 4 of 7 losses were
  in HIGH, the signal's documented weak habitat (30d: 10T, 30% WR, −$0.79).
  The `('HIGH', 'volume-breakout-long'): 0.0` override added 2026-10-10 already
  blocks these. Over Oct 9–10 that block nets +$0.19 (saves $0.73 of HIGH
  losers, forgoes $0.54 of HIGH winners) — correct but marginal.
- **Ordinary variance in the best habitat.** The 3 remaining EXTREME losses
  (−$0.24) are in EXTREME, where the signal is 13/19 and +$3.56 over 30d. 0/3
  at p=0.03 on n=3 is noise-scale.
- **Small sample.** n=7 for the whole "pattern." The raw 0/7 is significant
  (p=0.002) but collapses to p=0.24 once the known HIGH-regime factor is
  controlled — i.e., the known regime effect explains most of it.
- **The MAE pattern is an artifact**, not a mechanism (definitional circularity
  with stop distance).

The correct reading is: *the signal's HIGH-regime leak was real, it bit on
Oct 10, and the HIGH block shipped the same day already addresses it.* No new
BTC filter is warranted by this evidence.

---

## Risks of Proposed Fix (BTC `ema300_position` filter)

1. **It would have blocked all 4 Oct 9 winners** (+$0.72) — the very trades the
   analysis presents as proof the signal works. Because all 11 trades were AT,
   a "block AT" filter blocks everything.
2. **It destroys positive expectancy.** AT is +$1.76 over 90d for this signal.
   Removing it turns a +$3.08 signal into roughly +$1.32 with fewer trades and
   no reliability gain.
3. **Severe overfitting.** The filter is derived from 11 trades across 2 days,
   with Fisher p = 0.18. This is selection-on-outcome of exactly the kind
   AGENTS.md warns about.
4. **Habitat collapse / filter collision.** No trade has ever fired with BTC
   BELOW EMA300, so "block AT" leaves only the ABOVE subset (15 trades/90d,
   ~11 per month). Combined with the existing HIGH block, entry windows could
   become nearly unreachable — the documented trap where two BTC-band filters
   collide and trap trades.
5. **It fights an existing upstream mechanism.** `signal_compactor.py`'s
   LONG-RSI-CEILING *bypasses* overbought blocks when BTC is bullish
   (linreg BULL/LEAN_BULL + EMA300 ABOVE/AT). A new filter blocking AT would
   directly oppose that bypass, producing contradictory gating where the same
   trade is simultaneously "permitted because BTC is fine" and "blocked because
   BTC is at EMA300."
6. **Wrong-sign systemic evidence.** The book-wide data says AT is *better*
   than ABOVE. A filter justified as "AT is dangerous" is backwards on the
   aggregate data.

---

## Sideways Findings (see something, say something)

- **S1 — Data quality (medium):** `entry_rsi_14` and `_signal_metadata.rsi_14`
  disagree on 10/11 recent volume-breakout trades (PURR 100 vs 68.71; YGG 55.35
  vs 22.22). Two different RSI sources/timestamps. *Fix:* standardize on the
  signal-time 5m value (`_signal_metadata.rsi_14`) for analytics, or rename the
  columns to make the source explicit (`entry_rsi_1m`, `entry_rsi_5m`).
- **S2 — Internally inconsistent rationale (medium):**
  `hermes_constants.py:895` states "95 let BABY@81.82 through → hard_max_loss
  −$0.17. 85 blocks only the exhausted zone." But **81.82 < 85**, so an 85
  ceiling would *not* block BABY@81.82. The stated justification does not match
  its own arithmetic. *Fix:* correct the comment and re-evaluate whether 85 is
  the right value, since the cited motivating trade still passes.
- **S3 — Stale comment (low):** `volatility_gate_v2.py:433` cites "30d HIGH 8T
  25%WR −$0.69" while the current 30d HIGH figure (and the comment at line 307)
  is 10T / 30% WR / −$0.79. One of the two comments is a stale snapshot.
- **S4 — Misleading stored RSI (medium):** PURR's `entry_rsi_14 = 100.00` comes
  from the 1m RSI (no-loss window), while its actual signal-time 5m RSI was
  68.71. Any "overbought entry" diagnosis keyed on `entry_rsi_14` will produce
  false positives. See S1.
- **S5 — Silent fail-open on a safety filter (low-medium):** the
  LONG-RSI-CEILING and SPIKE-FILTER RSI blocks in `signal_compactor.py`
  (~3909–3931, ~4006–4040) are wrapped in `try/except Exception: pass`. A DB
  error or import failure silently disables the overbought block with no log.
  *Fix:* log the exception at minimum.

---

## Overall Assessment

# REJECT

Reject the proposed BTC `ema300_position` filter. The reasoning chain fails at
its foundation: **Claim 4 is factually wrong.** All 11 trades in the analysis
— winners and losers alike — had BTC at `ema300_position = 'AT'` at trade open.
The claimed ABOVE-vs-AT split between Oct 9 and Oct 10 does not exist in the
continuum data. Consequently there is no discriminator to build a filter on:
blocking AT would have blocked the 4 winning trades the analysis uses as its
evidence of the signal's quality, and the AT bucket is net positive (+$1.76 /
90d, Fisher p=0.18 against ABOVE).

Claims 1, 2 and 3 reproduce exactly, but Claim 3's MAE separation is
definitional (losers hit their stops) and carries no predictive content, and
Claim 2's RSI figure is inflated by a 1m-RSI artifact. Claim 7 is overstated:
0/7 is significant raw (p=0.002) but falls to p=0.24 once the known HIGH-regime
weakness is controlled — meaning the already-shipped
`('HIGH', 'volume-breakout-long'): 0.0` override is the actual, sufficient
answer.

**Recommended actions:**
1. Keep the existing HIGH-regime block. Do not add a BTC ema300 filter.
2. Monitor 7 days and re-evaluate with n ≥ 15 before any further change.
3. Fix S1/S4 (RSI column provenance) before any future RSI-based analysis — the
   current `entry_rsi_14` values are unreliable.
4. Fix S2 (the 85-ceiling rationale is arithmetically wrong as written).
5. Do not treat MAE as an entry-quality signal (Claim 3) — it is circular with
   stop distance.
