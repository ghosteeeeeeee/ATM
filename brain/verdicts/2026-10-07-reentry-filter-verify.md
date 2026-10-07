# Independent Verdict: Pump-Chain SHORT Re-Entry Filter

**Auditor:** fresh-eyes subagent (no priming from prior analysis)
**Date:** 2026-10-07
**Source:** PostgreSQL brain DB, `trades` table, `signal LIKE 'pump-chain%' AND direction='SHORT'`
**Method:** pulled all 140 rows, grouped by (token, direction), sorted by `open_time`, computed `gap_hours` = open-to-open gap from previous trade in group, applied filters, recomputed every claimed number from scratch. Cross-checked close-to-open gap (no material difference at 48h; small difference at 168h, noted below).
**Raw data:** `/root/.hermes/audit/pumpchain_short_trades.json`, `/root/.hermes/audit/pumpchain_short_sequences.json`

## Dataset facts (verified)

- 140 pump-chain SHORT trades, all `status='closed'`, 140 distinct ids, date range 2026-09-09 → 2026-10-07
- pnl > 0: **71** ($9.17) · pnl < 0: **61** (-$9.46) · pnl == 0: **8** (breakeven) · **Total PnL = -$0.29 exactly**
- 42 first trades (no prior trade on token+direction), 98 re-entries
- Note on convention: the claims count breakeven trades as "losses" (71+69=140, not 71+61). This is internally consistent across all claims and the $ amounts are unaffected (BE contribute $0), but a reader could easily misread "catches 16 losses" as 16 real losing trades. **The real counts are: 48h filter catches 13 real losses + 3 BE; 168h filter catches 20 real losses + 4 BE.**

---

## Claim-by-claim verdicts

### Claim 1: "After a winning trade on the same token+direction, the next trade loses 72% of the time"

**Verdict: DISAGREE** (direction correct, magnitude overstated)

**Evidence:**
- After ANY win → next trade: n=59, W=26 L=28 BE=5 → loss rate **47.5%** (all trades) / 55.9% (BE counted as loss) / 51.9% (BE excluded). Not 72%.
- 1st WIN → 2nd trade only: n=26, W=8 L=15 BE=3 → loss rate **57.7%** (all) / **69.2%** (BE as loss) / 65.2% (BE excluded). Closest figure to the claim, still not 72%.
- I tested every natural definition I could construct: token+dir grouping, token-only grouping, both directions included, BE-as-loss/BE-excluded/BE-as-win, gap<48h and gap<168h subsets, and historical cutoffs from 2026-09-15 through 2026-10-07. **No definition yields 72%.** The only configuration that lands near 72%/28% is requiring the first win to be ≥ $0.20 (n=11, 72.7% loss / 27.3% WR) — an unstated, cherry-picked threshold on a tiny sample.
- Historical cutoffs for 1st-WIN→2nd: loss rate ranged 60.0%–69.2% across all cutoffs. Never 72%.

**Confidence: HIGH** that 72% is not reproducible; the true figure is ~69% (1st-WIN→2nd, BE-as-loss) or ~52% (any-win→next).

---

### Task item 6: "is the '1st WIN → 2nd trade 28% WR' claim correct?"

**Verdict: DISAGREE**

**Evidence:** 1st-WIN→2nd trade: 8W/15L/3BE out of n=26 → **WR = 30.8%** (BE as non-win) or **34.8%** (BE excluded from denominator). Not 28%. No natural definition or historical cutoff reproduces 28%.

**Confidence: HIGH**

**Important nuance the original analysis missed:** the bad re-entry edge is NOT specific to re-entries after wins.
- Re-entries after a WIN: 26W/28L/5BE → WR **44.1%**
- Re-entries after a LOSS: 15W/18L/1BE → WR **44.1%**
- First trades on a token: 28W/12L/2BE → WR **66.7%** (PnL +$2.38)
- All re-entries: 43W/49L/6BE → WR **43.9%** (PnL -$2.67); Fisher p=**0.0147** vs first trades

**The re-entry itself is toxic, not the prior win.** Prior-trade outcome does not predict the next trade's outcome at all (44.1% vs 44.1%). What does predict it: whether it's the first trade on the token, and the *size* of the prior win (see recommendation).

---

### Claim 2: "Re-entry filter (block when gap < 48h after WIN): kills 13 wins ($0.99), catches 16 losses ($2.02), NET=+$1.03, WR improvement +1.6%"

**Verdict: AGREE** (all dollar figures exact; "16 losses" = 13 real + 3 BE; WR delta matches rounded convention)

**Evidence (recomputed from scratch):**
- Blocked: 29 trades (prev WIN, open-to-open gap < 48h)
- Killed wins: **13**, sum = **$0.99 exact** ✓
- Caught non-wins: **16** = 13 real losses (**$2.02 exact** ✓) + 3 breakevens ($0)
- NET = 2.02 − 0.99 = **$1.03 exact** ✓
- WR: baseline 71/140 = 50.71% → filtered 58/111 = 52.25% → **+1.54pp exact**; claim's "+1.6%" matches 52.3 − 50.7 with each WR rounded to 1 decimal first. Consistent.
- Gap-definition sensitivity: close-to-open gap gives an identical blocked set at 48h (29 trades, same kills/catches) — prev trades are short-lived relative to 48h.

**Statistical caveat (not part of the claim, but material):** blocked trades win 50.0% (13W/13L) vs kept 54.7% (58W/48L) → **Fisher exact p = 0.67 — NOT significant.** The filter's PnL edge comes from loss-magnitude asymmetry (blocked avg win +$0.076 vs blocked avg loss -$0.155), not from win-rate difference. Temporal split: Sept NET +$0.97 (holds), Oct NET +$0.06 (n=24 trades, effectively neutral).

**Confidence: HIGH** on arithmetic; **MEDIUM** that the edge is real (p=0.67).

---

### Claim 3: "Re-entry filter (block when gap < 168h after WIN): kills 20 wins ($2.02), catches 24 losses ($3.15), NET=+$1.13, WR improvement +2.4%"

**Verdict: AGREE** (all dollar figures exact; "24 losses" = 20 real + 4 BE)

**Evidence:**
- Blocked: 44 trades (prev WIN, open-to-open gap < 168h)
- Killed wins: **20**, sum = **$2.02 exact** ✓
- Caught non-wins: **24** = 20 real losses (**$3.15 exact** ✓) + 4 breakevens
- NET = 3.15 − 2.02 = **$1.13 exact** ✓
- WR: 51/96 = 53.13% vs 50.71% → **+2.41pp**; claim's "+2.4%" matches rounded convention (53.1 − 50.7). ✓
- Gap-definition sensitivity: close-to-open gap at 168h blocks 45 trades (20W $2.02, 21L $3.40, NET=+$1.38) — slightly different from the claim, confirming the claim used **open-to-open** gap.

**Statistical caveat:** blocked trades win 50.0% (20W/20L) vs kept 55.4% (51W/41L) → **Fisher p = 0.58 — NOT significant.** Temporal split: Sept NET +$1.21 (holds), Oct NET **-$0.08** (8 blocked trades, filter slightly harmful in October).

**Confidence: HIGH** on arithmetic; **MEDIUM-LOW** that the edge is real (p=0.58, negative out-of-period).

---

### Claim 4: "Baseline SHORT: 71W 69L (50.7% WR) PnL=$-0.29"

**Verdict: AGREE** (with convention caveat)

**Evidence:** 71 pnl>0, 61 pnl<0, 8 pnl==0, total PnL = **-$0.29 exact** ✓. 71/140 = **50.71% ≈ 50.7%** ✓. The "69L" counts the 8 breakeven trades as losses. Strict losses = 61; strict WR excluding BE = 53.8%. The claim's numbers are internally consistent and the PnL is exact.

**Confidence: HIGH**

---

### Claim 5: "The filter catches losses like APT -$0.10, INJ -$0.27, BCH -$0.12, ENA -$0.25, KAS -$0.32"

**Verdict: AGREE**

**Evidence:** all five verified in the 48h filter's blocked set with exact amounts:
| Token | pnl | gap from prev WIN | prev win | in 48h filter? |
|---|---|---|---|---|
| APT | -$0.10 | 12.1h | +$0.53 | ✓ |
| INJ | -$0.27 | 28.7h | +$0.29 | ✓ |
| BCH | -$0.12 | 4.8h | +$0.18 | ✓ |
| ENA | -$0.25 | 1.7h | +$0.13 | ✓ |
| KAS | -$0.32 | 4.5h | +$0.06 | ✓ |

**Confidence: HIGH**

---

### Claim 6: "The filter kills wins like DYDX +$0.45, ACE +$0.22, CASHCAT +$0.13"

**Verdict: PARTIAL**

**Evidence:**
| Token | pnl | gap from prev WIN | killed by 48h filter? | killed by 168h filter? |
|---|---|---|---|---|
| ACE | +$0.22 | 13.9h | ✓ | ✓ |
| CASHCAT | +$0.13 | 10.6h | ✓ | ✓ |
| DYDX | +$0.45 | **62.5h** | **✗ (62.5h > 48h)** | ✓ |

ACE and CASHCAT are killed by both filters. **DYDX +$0.45 is only killed by the 168h filter** — the 48h filter lets it through. If "the filter" means the 48h filter, DYDX is a wrong example. (Note also ACE prev win was only +$0.01 and DYDX prev win only +$0.03 — these are re-entries after *tiny* wins, which is exactly what a size-based filter would NOT block.)

**Confidence: HIGH**

---

## Recommended filter

**Block re-entries on the same token+direction when the previous trade was a WIN ≥ $0.10 — regardless of time gap.** (No gap threshold at all.)

| Metric | Claimed 48h | Claimed 168h | **Recommended (prevWIN ≥ $0.10)** |
|---|---|---|---|
| Trades blocked | 29 | 44 | **29** |
| Wins killed ($$) | 13 ($0.99) | 20 ($2.02) | **9 ($0.66)** |
| Losses caught ($$) | 13 ($2.02) | 20 ($3.15) | **18 ($3.01)** |
| Breakevens blocked | 3 | 4 | **2** |
| **NET PnL** | **+$1.03** | **+$1.13** | **+$2.35** |
| Baseline WR → filtered | 50.7% → 52.3% | 50.7% → 53.1% | **50.7% → 55.9% (+5.2pp)** |
| Resulting book PnL | +$0.74 | +$0.84 | **+$2.06** |
| Fisher p (blocked vs kept WR) | 0.67 | 0.58 | **0.019** |
| Oct out-of-period NET | +$0.06 | -$0.08 | **+$0.41** |

**Why this beats the claimed filters:**
1. **Doubles the NET** (+$2.35 vs +$1.03/+1.13) while killing only 9 wins ($0.66) — the claimed filters' time threshold is the wrong conditioning variable.
2. **Only candidate with statistical significance** (p=0.019). Blocked trades win 33.3% (9W/18L) vs kept 59.0% (62W/43L).
3. **Leave-one-token-out robust:** NET ranges +$1.60 to +$2.03 across every single-token removal — the edge is not one lucky token.
4. **Smooth threshold decay** (not knife-edge overfitting): $0.10 → NET +$2.35, $0.15 → +$1.93, $0.20 → +$1.21, $0.30 → +$0.41.
5. **Mechanically sensible:** the claimed filters let through big-win re-entries at long gaps that lose badly (ACE -$0.33 @ 224h, GOAT -$0.30 @ 184h, LTC -$0.25 @ 178h, BLUR -$0.20 @ 98h) while blocking small-win re-entries that mostly win (ALGO +$0.04/+$0.10 chains, BTC +$0.09/+$0.06, ATOM +$0.06/+$0.04). **Prior-win size predicts re-entry outcome; prior-win timing does not.**

**Deeper structural finding (stronger than any single filter):** first trades on a pump-chain SHORT token+direction win **66.7%** (PnL +$2.38); re-entries win **43.9%** (PnL -$2.67); Fisher **p=0.0147**. The whole book's problem is re-entries, period. The recommended filter is a magnitude-based proxy for this; the purest version ("never re-enter the same token+direction after the first pump-chain SHORT") nets +$2.67 but blocks 98/140 trades — impractical, though worth monitoring as a shadow metric.

**Mandatory caveats before any deployment:**
- **This is in-sample optimization on n=140 trades with ~$10 of total PnL.** The dollar amounts are trivially small; a single different exit could flip the ranking.
- The recommended filter was found by scanning thresholds on the same data used to evaluate it — overfitting risk is real. The smooth decay and LOO robustness mitigate but do not eliminate it.
- October out-of-period sample is only 24 trades; the filter stayed PnL-positive (+$0.41) and improved kept WR (37.5% → 42.1%) but this is weak evidence.
- **Recommendation: adopt as paper-trade/shadow filter first. Do not deploy live on this evidence alone.** Collect ≥30 days of forward data before trusting the edge.
- Compatible with the AGENTS.md philosophy ("no blanket regime kills") — this is a same-token re-entry cooldown, not a regime kill.

---

## Sideways findings

1. **Data quality:** `trade_id` is NULL/0 for all 140 pump-chain SHORT trades (`COUNT(DISTINCT trade_id) = 0`). The `id` column works, but anything keying off `trade_id` will silently break for this signal family. Severity: low-medium; suggested fix: backfill or stop relying on `trade_id` for pump-chain rows.
2. **The claimed filters' time thresholds are actively counterproductive:** blocking gap<48h after a win kills 13 mostly-small wins (ALGO/BTC/ATOM/CASHCAT re-entry chains that collectively made +$0.99) while missing the long-gap big-win re-entries that lose the most. If any re-entry filter is deployed, use prior-win SIZE, not time gap.
3. **8 breakeven trades** (CC, JUP, APT, BIGTIME, AZTEC, GOAT, IOTA, GRASS — all `atr_sl_hit`/`pump_exit_*`/`hard_sl`/`atr_trail_hit` exits at $0.00) are being counted as losses in all the claims. Not wrong per se, but every "loss rate" quoted in the claims is ~3–5pp inflated by this convention.
4. **ENA rapid-fire:** 3 SHORT trades on ENA within 1.5h on 2026-09-11 (18:49 W, 20:31 L, 20:39 W) — the 20:31 re-entry opened 8 minutes after the 18:49 win closed. No overlapping positions found anywhere in the dataset (verified), but this is the kind of spam re-entry the filter family should target.

---

## Summary table

| # | Claim | Verdict | Confidence |
|---|---|---|---|
| 1 | "After a WIN, next trade loses 72%" | **DISAGREE** — actual 69.2% (1stWIN→2nd, BE-as-loss) or 47.5% (any-win→next) | HIGH |
| 2 | 48h filter: 13W/$0.99, 16L/$2.02, NET+$1.03, +1.6% WR | **AGREE** — all figures exact ("16 losses"=13 real+3 BE; p=0.67 ns) | HIGH (arithmetic) / MEDIUM (edge) |
| 3 | 168h filter: 20W/$2.02, 24L/$3.15, NET+$1.13, +2.4% WR | **AGREE** — all figures exact ("24 losses"=20 real+4 BE; p=0.58 ns) | HIGH (arithmetic) / MEDIUM-LOW (edge) |
| 4 | Baseline 71W 69L 50.7% PnL -$0.29 | **AGREE** — exact (69L includes 8 breakevens; PnL -$0.29 exact) | HIGH |
| 5 | Filter catches APT/INJ/BCH/ENA/KAS losses | **AGREE** — all five exact in 48h blocked set | HIGH |
| 6 | Filter kills DYDX/ACE/CASHCAT wins | **PARTIAL** — ACE+CASHCAT ✓ both filters; DYDX only killed by 168h filter (62.5h gap) | HIGH |
| 6b | "1st WIN → 2nd trade 28% WR" | **DISAGREE** — actual 30.8% (BE as non-win) / 34.8% (BE excluded) | HIGH |

**Bottom line:** the claimed filter numbers are arithmetically flawless — every dollar figure reproduces to the cent. What does not survive scrutiny is (a) the 72%/28% headline stats, which are not reproducible from this data under any natural definition, and (b) the implicit claim that the filters have edge: neither passes statistical significance (p=0.67, p=0.58), and the 168h filter was slightly *harmful* in October. A size-based filter (block re-entries after wins ≥ $0.10, any gap) dominates both claimed filters on every metric and is the only candidate with p<0.05 — but even that rests on 140 trades and ~$2 of edge, so it should be paper-traded, not deployed.
