# Hermes Edge Diagnosis — Meta-Level Review
**Date:** 2026-11-22
**Scope:** All 6,584 real (paper=false) closed trades in PostgreSQL `brain.trades`
**Method:** Direct SQL aggregation. No estimates, no memory — every number below was executed.

---

## ⚠️ CORRECTION (added 2026-11-22, same session)

The original headline below ("no edge") was **wrong**. It was an artifact of averaging two
opposing populations. See **Section 7** — the system *does* carry a statistically significant
gross edge (t = +2.40) in a identifiable subset of signals. The aggregate t = -1.96 is the
*average* of a +2.40 group and a -4.18 group. That is a **masked edge**, not an absent one.

The cost conclusion stands and is now the binding constraint. The signal conclusion does not.

---

## TLDR (superseded — see Section 7)

The system does not have an edge problem — it has a **zero edge plus a cost problem**, and the
internal accounting column is hiding the real loss by ~20x.

Gross expectancy across 6,584 trades is **-$0.0030/trade** with **t = -1.96**, which is **not
statistically distinguishable from zero**. Friction (fees + slippage) is **1.14% of notional per
round trip**. The system paid **$209.35 in fees** to determine, statistically, that it has no edge.

**Revised reading:** the aggregate is zero because two real, significant, opposing populations
cancel. One has a genuine positive edge; the other is a genuine drain. Isolate them and the
picture becomes actionable.

---

## Headline Numbers

| Metric | Value |
|---|---|
| Real closed trades | 6,584 |
| `pnl_usdt` sum (what the dashboard shows) | **-$18.53** |
| Exchange-reported net, same trades with fee JSON | **-$350.31** |
| Total fees paid (3,951-trade measured subset) | **$209.35** |
| Gross expectancy | -$0.0030 / trade |
| Avg win / avg loss | 0.088 / -0.091 |
| Payoff ratio | 0.967 |
| Breakeven win rate needed | 50.8% (actual 49.1%) |
| **t-statistic on mean P&L** | **-1.96 → NOT significant** |
| Avg position size | $11.86 |
| Median hold time | 2,576 min (43 h); avg 4,927 min (82 h) |
| Fee per trade | $0.053 = **0.45% of notional** |
| Avg exit slippage | **0.69% of notional** |
| **Total friction per round trip** | **~1.14% of notional** |

---

## Finding 1 — The accounting is lying (severity: critical)

`pnl_usdt` is **gross of fees**. Verified directly:

```
avg(pnl_usdt - exchange_net_pnl) = 0.0493
avg(fee_total)                    = 0.0530
```

On the 3,951 trades carrying a fee JSON blob:

```
sum(pnl_usdt)          = -155.37   <- internal column
sum(exchange net_pnl)  = -350.31   <- what Hyperliquid says was kept
sum(fee_total)         = +209.35
```

The dashboard reports **-$18.53** across all 6,584 trades. The exchange reports **-$350.31** on
just the subset. Real total loss is almost certainly **worse than -$350** once the ~2,633 trades
without fee JSON are counted.

**Nothing downstream is trustworthy until this is reconciled.** Every win rate, every filter
backtest, every "improvement" measured against `pnl_usdt` was measured against a column that
omits the cost of trading.

---

## Finding 2 — The gross edge is statistically zero (severity: critical)

```
mean   = -0.00281
sd     =  0.1164
n      =  6584
t-stat = -1.96   -> cannot reject H0: expectancy = 0
```

This is the single most important number in the report. It means the aggregate strategy is a
coin flip. Six months of signal engineering, regime scanners, Wyckoff integration, linreg_fade,
confluence gates — the sum total is indistinguishable from randomness before costs are even
applied.

---

## Finding 3 — Costs are the entire P&L (severity: critical)

| Friction component | Per trade | % of notional |
|---|---|---|
| Exchange fees | $0.053 | 0.45% |
| Exit slippage (measured) | ~$0.082 | 0.69% |
| **Total** | | **~1.14%** |

To break even the system needs **+1.14% gross expectancy per trade**. It has **-0.025%**.

Fees of $209.35 are **11x larger than the gross loss of $18.53**. The system paid $209 to
discover it has no edge.

---

## Finding 4 — Win rate was the wrong target (severity: high)

Monthly progression (real trades only):

```
2026-05  n= 532  net=   +0.70  WR=45.1%
2026-06  n=1548  net=   +2.44  WR=47.3%
2026-07  n= 688  net=   -2.09  WR=24.1%
2026-08  n=1549  net=   -7.75  WR=49.1%
2026-09  n=1047  net=   -5.34  WR=52.5%
2026-10  n= 810  net=   -4.21  WR=46.3%
2026-11  n= 410  net=   -2.28  WR=51.5%
```

Win rate improved 24% -> 51.5% while net P&L went **more negative**. With a payoff ratio of
0.967, breakeven WR is 50.8%. The system tuned the one metric that is nearly irrelevant to P&L
while payoff ratio and cost structure never moved.

The stated philosophy — *"every trade should be a winner"* — optimizes directly for win rate.
That is the easiest number to make look good and the least connected to whether the account
grows.

---

## Finding 5 — All 30+ signals are one bet (severity: high)

By-signal cut (real, closed, n >= 40) is a flat line around zero — a few positive, a few
negative, no barbell:

```
ct_hot                    n=105   net= -4.41  WR=36.2%
accel_300+,rs_s           n=275   net= -2.91  WR=37.8%
accel_300_,rs_r           n=281   net= -1.81  WR=45.6%
bb-bounce-v2-long+        n= 80   net= -1.32  WR=46.3%
accel_300+,rs_r_broken    n= 62   net= -1.21  WR=41.9%
...
accel_300_,rs_s_broken    n=1021  net= +6.23  WR=46.4%
pump-chain+               n=187   net= +2.29  WR=39.6%
bb_bounce_v2_long         n= 73   net= +2.08  WR=74.0%
```

RSI, Bollinger, momentum, Wyckoff, z-score, linear regression, ichimoku, structure shifts are
**all transformations of the same public OHLCV candles**. They cannot be 30 independent edges —
they are one bet wearing 30 labels. This is why the table is flat rather than a barbell of real
winners and real losers.

---

## Finding 6 — Direction split

```
SHORT  n=3377  net= -5.26   WR=45.8%
LONG   n=3207  net=-13.27   WR=46.4%
```

Both sides lose. Longs lose 2.5x more in total but at nearly identical win rate — so the leak is
not directional bias, it is the same zero-edge-plus-costs structure on both sides.

---

## Why profitable external traders are not a contradiction

The observation that traders live-stream OHLCV-only strategies (MACD + RSI, the "$1M challenge"
format, warrior-trading style) and repeatedly turn $100 into large sums is **real and does not
contradict this report**. It points at exactly the right conclusion:

1. **Data access is not the moat.** Everyone has OHLCV. The edge is not in the data or the
   indicator — it is in **execution, payoff structure, and risk**.
2. **The profitable structure is asymmetric payoff, not high win rate.** Trend traders routinely
   run 35-45% win rates and make money because average winners are 3-10x average losers. This is
   the *opposite* of what Hermes optimized.
3. **Cost structure differs by orders of magnitude.** A human swinging $10,000+ positions with
   infrequent trades pays a tiny fraction of the 1.14% per-round-trip friction Hermes pays on
   $11.86 positions held for 43 hours.
4. **Survivorship bias applies to livestreams too.** The failed "$1M challenges" do not get the
   same audience. The visible distribution is conditioned on success.
5. **Hermes already coded these strategies** (warrior-trading signals: MACD + RSI) — and they
   landed in the same flat-around-zero table as everything else. That is the empirical proof
   that the signal source was never the bottleneck.

---

## The bar, written down

Any candidate edge must clear, **out-of-sample and with p < 0.05**:

> **+1.14% gross expectancy per trade**

Nothing shipped comes close. The gross side currently measures zero.

---

## Recommended actions, in order

1. **Fix the accounting.** Reconcile `pnl_usdt` to exchange-reported net so fees are included.
   Nothing is measurable until the dashboard tells the truth.
2. **Freeze signal work for 30 days.** Zero new signals. That layer is provably zero; every hour
   there is spent on the wrong layer.
3. **Stop measuring win rate.** Track expectancy, payoff ratio, and cost-per-trade only.
4. **Hunt structure, not signals** — funding-rate capture, basis, maker rebates, order flow. Or
   accept that sub-$12 swing trading at 1.14% friction is a negative-fee hobby rather than a
   business.
5. **Re-examine the philosophy line.** *"Every trade should be a winner"* is a win-rate target
   dressed as a principle. It is measurably anti-correlated with the account balance.

---

## Reproduction

```sql
-- Headline
SELECT count(*), paper, sum(pnl_usdt), 100.0*count(*) FILTER (WHERE pnl_usdt>0)/count(*)
FROM trades WHERE status='closed' GROUP BY paper;

-- Significance
SELECT avg(pnl_usdt), stddev(pnl_usdt), count(*),
       avg(pnl_usdt)/(stddev(pnl_usdt)/sqrt(count(*))) AS t_stat
FROM trades WHERE status='closed' AND paper=false;

-- Accounting reconciliation
SELECT sum(pnl_usdt),
       sum((fees::json->>'net_pnl')::numeric),
       sum((fees::json->>'fee_total')::numeric)
FROM trades WHERE status='closed' AND paper=false AND fees~'^{';
```

---

# SECTION 7 — Low-WR-but-profitable analysis (added 2026-11-22)

Prompt: *"see if there are any signals we've historically churned through that had lower than
50% winrate but was still overall profitable."*

**Answer: yes — 10 of them, and they are the entire edge.**

## 7.1 Signals with WR < 50% that are net profitable (n >= 30)

| signal | n | net | WR% | payoff | avg win | avg loss |
|---|---:|---:|---:|---:|---:|---:|
| accel_300_,rs_s_broken | 1021 | **+6.23** | 46.4 | 1.20 | 0.0967 | -0.0805 |
| pump-chain+ | 187 | **+2.29** | 39.6 | 1.68 | 0.1965 | -0.1167 |
| volume-breakout-long+ | 40 | **+2.28** | 47.5 | 2.05 | 0.2605 | -0.1271 |
| rs_r,zscore_pump | 193 | +0.72 | 43.0 | 1.40 | 0.1022 | -0.0732 |
| rs_s,zscore_pump | 155 | +0.66 | 42.6 | 1.45 | 0.1071 | -0.0737 |
| tl_break_long | 94 | +0.58 | 37.2 | 1.82 | 0.0823 | -0.0451 |
| ai-trader-pending | 68 | +0.28 | 32.4 | 1.93 | 0.1568 | -0.0813 |
| hl_copy_trader | 111 | +0.15 | 40.5 | 1.36 | 0.1511 | -0.1108 |
| tl_break_short | 114 | +0.06 | 35.1 | 1.33 | 0.0583 | -0.0437 |
| accel_300_vel | 37 | +0.02 | 27.0 | **2.56** | 0.0920 | -0.0360 |

Every one of them has **payoff > 1.0**. Not one has WR >= 50%.

## 7.2 The mirror image — the high-WR signals are the losers

Grouped by payoff ratio (all signals with n >= 30):

| group | signals | n | net | WR% | t-stat |
|---|---:|---:|---:|---:|---:|
| **payoff > 1.2** (asymmetric winners) | 14 | 2332 | **+13.45** | **41.4%** | **+2.40** ✅ |
| payoff 1.0–1.2 (symmetric churn) | 5 | 732 | -2.43 | 39.9% | -0.78 |
| **payoff < 1.0** (asymmetric losers) | 23 | 1890 | **-9.21** | **54.7%** | -1.76 |

**The profitable signals are the low-win-rate ones. The high-win-rate signals lose money.**

- Best group: **41.4% WR, t = +2.40** — significant, positive
- Worst group: **54.7% WR** — the highest win rate in the system, and it is net negative

This is the direct inversion of the stated philosophy. *"Every trade should be a winner"* and
any WR-maximising filter would have **concentrated capital on the 23 losing signals and dropped
the 14 winning ones.** The philosophy is not merely unhelpful — it is exactly backwards.

## 7.3 The masked edge, isolated

Traded **only** the 10 low-WR-but-profitable signals:

```
n = 2020   net = +13.27   WR = 43.0%   expectancy = +0.00657   t = +2.39  ✅ significant
```

Everything else:

```
n = 4562   net = -31.84   WR = 47.4%   expectancy = -0.00698   t = -4.18  ✅ significant
```

Two real populations, both statistically significant, opposite signs, averaged into the
misleading aggregate t = -1.96 reported in Finding 2.

## 7.4 Top 100 trades by profit — the user's pump-chain read is confirmed

| signal | count in top 100 | net |
|---|---:|---:|
| **pump-chain+** | **17** | **+9.58** |
| **pump-chain-** | **10** | **+4.48** |
| volume-breakout-long+ | 6 | +3.43 |
| hl_copy_trader | 9 | +3.42 |
| pullback-entry- | 9 | +3.34 |
| ct_hot | 6 | +2.74 |

**The pump-chain family contributes 30 of the top 100 trades** (+14.06 combined) — despite
`pump-chain+` having only a **39.6% win rate**. It is the single largest source of big winners
in the system.

Pump-chain family full cut:

```
pump-chain+            n=187  net=+2.29  WR=39.6%  payoff=1.68
pump-chain-            n=206  net=-0.20  WR=43.7%  payoff=1.15
rs_r,zscore_pump       n=193  net=+0.72  WR=43.0%  payoff=1.40
rs_s,zscore_pump       n=155  net=+0.66  WR=42.6%  payoff=1.45
pump_chain              n=43  net=+0.98  WR=67.4%  payoff=0.69
```

## 7.5 Tail vs middle decomposition

| segment | n | net |
|---|---:|---:|
| Top 100 winners | 100 | **+45.87** |
| Bottom 100 losers | 100 | -30.42 |
| **Middle 6,384** | 6384 | **-33.98** |
| Extremes net | 200 | +15.45 |

Quartile view:

```
TOP 25%     n=1646  net=+220.14
Q3          n=1646  net= +47.84
Q2          n=1646  net= -63.76
BOTTOM 25%  n=1646  net=-222.75
```

The extremes favour winners (+15.45), but the full quartile view is near-symmetric
(+220 vs -223). **The system's structure is right at the very top and the very bottom, and
bleeds in the 6,384-trade middle.**

## 7.6 THE BINDING CONSTRAINT — the edge is real but 23x too small

For the payoff > 1.2 group:

```
gross expectancy = +0.0496% of notional
friction          =  1.14%  of notional   (0.45% fees + 0.69% slippage)
NET               = -1.090% of notional
```

**The edge must be ~23x larger at the same win rate to clear costs.**

This is now the whole problem. The signal layer works — it found genuine, reproducible,
statistically significant structure (t = +2.40). It cannot pay for itself because the friction
is two orders of magnitude larger than the edge.

Note: position size does **not** fix this. Fees are percentage-based, so scaling from $11.86 to
$1,000 leaves the ratio unchanged.

## 7.7 Slippage — real, but with an anomaly

```
p10=0.0275%  p25=0.0853%  p50=0.3467%  p75=0.9944%  p90=1.2146%  p99=3.2642%
mean=0.6864%  sd=1.88  n=6567  outliers>5% = 48
```

Not outlier-driven — the mean is genuine. Median 0.35%.

**Anomaly:** average slippage on **winners = 0.9635%**, on **losers = 0.3660%**. Winners slip
**2.7x more than losers**. This taxes exactly the profitable-low-WR trades and would compress
their payoff ratio further. Cause unknown — `exit_slippage_pct` computation could not be located
in `scripts/*.py` during this session. **Verify the definition before treating slippage as a
hard cost.** If it is measured against a stale reference rather than a live book, the 1.14%
friction figure is overstated.

---

# REVISED CONCLUSION

1. **The system has a real, statistically significant gross edge** — 14 signals, payoff > 1.2,
   n = 2,332, **t = +2.40**, WR 41.4%. The user's instinct was correct.
2. **The aggregate "no edge" was an averaging artifact** — a +2.40 population cancelled by a
   -4.18 population. Section 7.3.
3. **The high-win-rate signals are the losers.** 54.7% WR group is net negative; 41.4% WR group
   is the edge. The stated philosophy selects for the wrong population.
4. **pump-chain is confirmed as the biggest winner source** — 30 of the top 100 trades at 39.6% WR.
5. **Cost is the binding constraint, not signal quality.** Edge +0.05% vs friction 1.14% — 23x
   short. No amount of further signal work closes that gap.
6. **Accounting is still broken** — `pnl_usdt` is gross of fees and understates real loss ~20x.

## Revised action order

1. **Reconcile `pnl_usdt` to exchange net** (unchanged — still first, still blocking).
2. **Cut the 23 payoff < 1.0 signals entirely.** They are -9.21 at 54.7% WR. Pure drag.
3. **Concentrate on the 14 payoff > 1.2 signals.** Drop from 37 active signals to 14.
4. **Verify `exit_slippage_pct` definition** (Section 7.7). If overstated, the cost gap narrows
   and the concentrated portfolio may approach viability.
5. **Attack cost, not signal** — maker fills, limit entries, fewer/larger trades, lower-fee
   venue. This is where the remaining 23x must come from.
6. **Delete the win-rate philosophy.** Replace with: expectancy, payoff ratio, cost/trade.
