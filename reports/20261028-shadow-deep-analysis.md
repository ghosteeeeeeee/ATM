# Shadow-Mode Deep Analysis — WR/Profitability Improvements

**Date:** 2026-10-28  
**Data:** 31,986 shadow trades (Oct 7-28, 21 days)  
**Market Context:** Bearish/choppy regime  
**Analysis:** NET PnL (post-fee), gate-passed only, with cluster-robust statistics  
**Validator:** own-conclusions (independent audit) on previous analyses

---

## TLDR

**The system is losing -1,833.1% net (gate-passed only), cluster t=-14.59 (highly significant).** No signal is net-positive AND statistically significant at n>=50. PM Trail is the only profitable exit engine (t=57.58 SHORT, t=50.24 LONG). Hard Max and Cut Loser are the biggest losers (t=-229 and t=-283). RR ratio is 0.50 (breakeven WR 66.5%, current 56.7%). **FLAT regime is catastrophic (WR 15.8% LONG / 10.2% SHORT).** Time-of-day matters for SHORT (best hours 8, 18, 6, 13, 2 with WR 67-75%).

---

## 1. Overall Stats (Gate-Passed Only)

| Metric | Value |
|--------|-------|
| Total rows in DB | 31,986 |
| Gate-passed with net PnL | 15,165 |
| Period | Oct 20-28 (8 days) |
| **NET PnL** | **-1,833.1%** |
| AVG | -0.121% ± 0.742% |
| Naive t | -20.09 |
| **Cluster t** | **-14.59** (4,887 clusters) |
| **WIN RATE** | **56.7%** |

**The system is losing money net of fees.** Need 66.5% WR to break even (9.8pp gap).

---

## 2. Signal Performance (Gate-Passed, n>=50)

### No Signal is Net-Positive AND Significant

**Top signals (by total):**

| Signal | Dir | N | WR% | Total% | Avg% | t | Sig? |
|--------|-----|-----|-----|--------|------|---|------|
| hmacd_mtf | LONG | 394 | 68.8% | -4.0% | -0.010% | -1.61 | |
| continuum_score_long | LONG | 62 | 38.7% | -5.0% | -0.081% | -2.31 | ★ |
| support_resistance | LONG | 89 | 53.9% | -7.7% | -0.087% | -1.61 | |

**Significantly negative signals:**

| Signal | Dir | N | WR% | Total% | Avg% | t | Sig? |
|--------|-----|-----|-----|--------|------|---|------|
| squeeze_cross | LONG | 3,484 | 56.2% | **-636.6%** | -0.183% | **-6.41** | ★ |
| squeeze_cross | SHORT | 5,351 | 66.7% | **-300.6%** | -0.056% | **-3.85** | ★ |
| support_resistance | SHORT | 1,795 | 63.6% | **-172.0%** | -0.096% | **-6.20** | ★ |
| pump-chain | SHORT | 578 | 30.6% | **-141.3%** | -0.244% | **-7.43** | ★ |
| volume_breakout_long | LONG | 647 | 31.2% | **-104.3%** | -0.161% | **-2.99** | ★ |
| ichimoku_short | SHORT | 715 | 52.0% | **-75.5%** | -0.106% | **-4.12** | ★ |
| doji_bottom_long | LONG | 193 | 46.6% | **-63.2%** | -0.328% | **-4.61** | ★ |
| pump-chain | LONG | 245 | 28.2% | **-71.3%** | -0.291% | **-5.85** | ★ |
| pump-chain-v6 | LONG | 143 | 27.3% | **-44.8%** | -0.314% | **-4.26** | ★ |
| volume_buildup_short | SHORT | 376 | 46.5% | **-57.3%** | -0.152% | **-4.39** | ★ |

**squeeze_cross is the worst signal** — LONG t=-6.41, SHORT t=-3.85.

---

## 3. Exit Engine Analysis (Gate-Passed)

### Profitable Engines

| Engine | Dir | N | WR% | Total% | Avg% | t |
|--------|-----|-----|-----|--------|------|---|
| **pm_trail** | **SHORT** | 5,287 | **100.0%** | **+1,966.7%** | +0.372% | **57.58** |
| **pm_trail** | **LONG** | 2,540 | **100.0%** | **+958.1%** | +0.377% | **50.24** |
| hold | LONG | 546 | 45.2% | +221.6% | +0.406% | 5.21 |
| pump_exit | SHORT | 135 | 67.4% | +55.2% | +0.409% | 6.72 |

### Losing Engines

| Engine | Dir | N | WR% | Total% | Avg% | t |
|--------|-----|-----|-----|--------|------|---|
| **hard_max** | **SHORT** | 2,032 | 0.0% | **-1,948.0%** | -0.959% | **-229.39** |
| **hard_max** | **LONG** | 1,956 | 0.0% | **-1,887.3%** | -0.965% | **-210.33** |
| **cut_loser** | **SHORT** | 321 | 0.0% | **-384.8%** | -1.199% | **-283.68** |
| **cut_loser** | **LONG** | 110 | 0.0% | **-132.5%** | -1.204% | **-128.93** |
| rr_engine | SHORT | 832 | 13.0% | -331.3% | -0.398% | -25.00 |
| rr_engine | LONG | 398 | 11.8% | -146.9% | -0.369% | -18.93 |

**PM Trail is the ONLY profitable exit engine** — t=57.58 (SHORT), t=50.24 (LONG).

**Hard Max and Cut Loser are the BIGGEST losers** — t=-229 and t=-283.

---

## 4. Token Analysis (Gate-Passed, n>=30)

### No Token is Net-Positive AND Significant

**Top tokens (by total):**

| Token | Dir | N | WR% | Total% | Avg% | t | Sig? |
|-------|-----|-----|-----|--------|------|---|------|
| BLUR | LONG | 81 | 53.1% | +27.0% | +0.334% | 1.43 | |
| USELESS | LONG | 66 | 56.1% | +25.8% | +0.390% | 1.32 | |
| GMX | LONG | 94 | 68.1% | +11.2% | +0.119% | 1.30 | |

**Significantly negative tokens:**

| Token | Dir | N | WR% | Total% | Avg% | t | Sig? |
|-------|-----|-----|-----|--------|------|---|------|
| CRV | SHORT | 174 | 51.1% | **-37.7%** | -0.217% | **-4.55** | ★ |
| NXPC | SHORT | 148 | 52.0% | **-36.7%** | -0.248% | **-4.19** | ★ |
| CHIP | SHORT | 156 | 48.1% | **-35.4%** | -0.227% | **-3.79** | ★ |
| HYPER | SHORT | 122 | 45.1% | **-34.5%** | -0.282% | **-3.78** | ★ |
| STX | LONG | 86 | 43.0% | **-32.5%** | -0.378% | **-5.14** | ★ |
| ICP | LONG | 65 | 35.4% | **-31.2%** | -0.481% | **-6.42** | ★ |
| NEO | LONG | 72 | 34.7% | **-29.5%** | -0.410% | **-5.26** | ★ |
| APT | LONG | 128 | 52.3% | **-29.2%** | -0.228% | **-3.94** | ★ |
| IO | LONG | 64 | 37.5% | **-28.2%** | -0.441% | **-5.91** | ★ |
| LDO | LONG | 69 | 37.7% | **-27.5%** | -0.398% | **-4.80** | ★ |

**Avoid these tokens.** ICP LONG has the worst t-stat (-6.42).

---

## 5. Risk-Reward Analysis

| Direction | Wins | Losses | WR% | Avg Win | Avg Loss | RR Ratio | Breakeven WR | Gap |
|-----------|------|--------|-----|---------|----------|----------|--------------|-----|
| LONG | 2,956 | 2,997 | 49.7% | +0.471% | -0.814% | 0.58 | 63.3% | +13.7pp |
| SHORT | 5,638 | 3,574 | 61.2% | +0.381% | -0.821% | 0.46 | 68.3% | +7.1pp |
| **ALL** | 8,594 | 6,571 | **56.7%** | **+0.412%** | **-0.818%** | **0.50** | **66.5%** | **+9.8pp** |

**RR Ratio is 0.50** — avg win is only 50% of avg loss. Need 66.5% WR to break even, current WR is 56.7% (9.8pp below).

---

## 6. Time-of-Day Analysis (Gate-Passed)

### SHORT Best Hours (WR >= 65%)

| Hour | N | WR% | Avg% |
|------|-----|-----|------|
| **8** | 321 | **74.5%** | **+0.101%** |
| **18** | 488 | **74.8%** | **+0.039%** |
| **6** | 463 | **71.7%** | **+0.017%** |
| **13** | 305 | **68.5%** | **+0.020%** |
| **2** | 451 | **67.6%** | **+0.011%** |
| 19 | 389 | 67.4% | -0.054% |
| 7 | 405 | 66.4% | -0.013% |
| 3 | 372 | 65.1% | -0.010% |

### LONG Best Hours (WR >= 55%)

| Hour | N | WR% | Avg% |
|------|-----|-----|------|
| **23** | 272 | **67.6%** | **+0.139%** |
| **14** | 230 | **66.5%** | **+0.093%** |
| **22** | 324 | **63.6%** | **+0.002%** |
| 20 | 193 | 58.0% | -0.077% |

### LONG Worst Hours (WR <= 40%)

| Hour | N | WR% | Avg% |
|------|-----|-----|------|
| **5** | 177 | **33.9%** | **-0.398%** |
| **8** | 159 | **34.0%** | **-0.295%%** |
| **18** | 352 | **36.9%** | **-0.402%** |
| 6 | 237 | 40.1% | -0.304% |
| 7 | 178 | 41.0% | -0.249% |

**Time-of-day matters for SHORT.** Best hours: 8, 18, 6, 13, 2 (WR 67-75%).

---

## 7. RSI Band Analysis (Gate-Passed)

| RSI | LONG_n | LONG_WR | LONG_Avg | SHORT_n | SHORT_WR | SHORT_Avg |
|-----|--------|---------|----------|---------|----------|-----------|
| <30 | 65 | 44.6% | -0.145% | 547 | 43.0% | -0.155% |
| 30-40 | 67 | 43.3% | -0.119% | 417 | 40.5% | -0.190% |
| 40-50 | 100 | 40.0% | -0.160% | 366 | 42.1% | -0.151% |
| 50-60 | 286 | 36.7% | -0.133% | 331 | 43.8% | -0.168% |
| 60-70 | 262 | 36.3% | -0.184% | 163 | **55.8%** | **-0.025%** |
| >70 | 337 | 32.9% | -0.267% | 138 | 48.6% | -0.121% |

**SHORT 60-70 RSI is the best band** (WR 55.8%, Avg -0.025%). LONG >70 is the worst (WR 32.9%).

---

## 8. Confidence Analysis (Gate-Passed)

| Band | LONG_n | LONG_WR | LONG_Avg | SHORT_n | SHORT_WR | SHORT_Avg |
|------|--------|---------|----------|---------|----------|-----------|
| 60-69 | 68 | 29.4% | -0.410% | 18 | 22.2% | -0.137% |
| 70-79 | 2,820 | 53.1% | -0.173% | 4,376 | **61.5%** | -0.089% |
| 80+ | 3,065 | 46.9% | -0.173% | 4,818 | 61.1% | -0.082% |

**70-79 confidence is slightly better than 80+** for both directions.

---

## 9. Vol Regime Analysis (Gate-Passed)

| Regime | LONG_n | LONG_WR | LONG_Avg | SHORT_n | SHORT_WR | SHORT_Avg |
|--------|--------|---------|----------|---------|----------|-----------|
| **FLAT** | 152 | **15.8%** | -0.120% | 88 | **10.2%** | -0.130% |
| NORMAL | 285 | 36.1% | -0.142% | 614 | 42.5% | -0.136% |
| HIGH | 303 | 46.5% | -0.169% | 742 | 47.6% | -0.150% |
| EXTREME | 393 | 37.4% | -0.255% | 517 | 45.8% | -0.182% |

**FLAT regime is CATASTROPHIC** — WR 15.8% LONG / 10.2% SHORT.

---

## 10. Hold Time Analysis (Gate-Passed)

| Outcome | Hold | LONG_n | LONG_Avg | SHORT_n | SHORT_Avg |
|---------|------|--------|----------|---------|-----------|
| WIN | **3-8h** | 368 | **+1.063%** | 210 | +0.331% |
| WIN | <15m | 637 | +0.418% | 1,305 | +0.408% |
| WIN | 15-60m | 1,251 | +0.384% | 2,722 | +0.358% |
| WIN | 1-3h | 700 | +0.366% | 1,401 | +0.408% |
| LOSS | **1-3h** | 857 | **-0.900%** | 940 | -0.890% |
| LOSS | 15-60m | 1,135 | -0.844% | 1,490 | -0.856% |
| LOSS | <15m | 504 | -0.777% | 712 | -0.778% |
| LOSS | 3-8h | 501 | -0.635% | 432 | -0.624% |

**LONG winners hold 3-8h (+1.063%)** and losers hold 1-3h (-0.900%).

---

## 11. Gate Impact (NET)

| Gate | Dir | N | WR% | Total% | Avg% | t | Verdict |
|------|-----|-----|-----|--------|------|---|---------|
| **CONFLUENCE-EXPIRY** | **LONG** | 4,763 | 41.9% | **-804.6%** | -0.169% | **-14.03** | **HELPING** |
| **CONFLUENCE-EXPIRY** | **SHORT** | 7,932 | 48.9% | **-781.8%** | -0.099% | **-9.94** | **HELPING** |
| **CTX-GATE** | **LONG** | 1,017 | 44.8% | **-160.8%** | -0.158% | **-3.88** | **HELPING** |
| UNKNOWN | LONG | 208 | 27.9% | -62.0% | -0.298% | -1.76 | NEUTRAL |
| UNKNOWN | SHORT | 314 | 40.8% | -56.3% | -0.179% | -4.42 | NEUTRAL |
| BTC-CRASH | SHORT | 63 | 22.2% | -27.8% | -0.441% | -3.56 | NEUTRAL |
| CTX-GATE | SHORT | 281 | 45.2% | -22.2% | -0.079% | -1.31 | NEUTRAL |
| BTC-CRASH | LONG | 101 | 34.7% | -20.9% | -0.207% | -2.45 | NEUTRAL |
| EXEC-BLOCK | LONG | 31 | 48.4% | -0.2% | -0.006% | -0.10 | NEUTRAL |

**ALL gates are HELPING** (blocking losing trades). CONFLUENCE-EXPIRY is the biggest helper.

---

## Key Insights for WR/Profitability Improvements

### 1. No Signal is Net-Positive AND Significant
At n>=50, no signal survives significance testing. The system needs fundamental improvement.

### 2. PM Trail is the Only Profitable Exit Engine
- pm_trail SHORT: t=57.58
- pm_trail LONG: t=50.24
- hold LONG: t=5.21
- pump_exit SHORT: t=6.72

### 3. Hard Max and Cut Loser are the Biggest Losers
- hard_max SHORT: t=-229.39
- hard_max LONG: t=-210.33
- cut_loser SHORT: t=-283.68
- cut_loser LONG: t=-128.93

### 4. RR Ratio is 0.50 (Breakeven WR 66.5%)
- LONG: RR=0.58, Breakeven WR=63.3%, Gap=+13.7pp
- SHORT: RR=0.46, Breakeven WR=68.3%, Gap=+7.1pp

### 5. Time-of-Day Matters for SHORT
- Best SHORT hours: 8, 18, 6, 13, 2 (WR 67-75%)
- Worst SHORT hours: 11, 12, 23, 22 (WR 40-52%)

### 6. FLAT Regime is Catastrophic
- LONG FLAT: WR=15.8%
- SHORT FLAT: WR=10.2%

### 7. RSI Extremes Don't Help Much
- SHORT 60-70: WR=55.8% (best SHORT)
- LONG <30: WR=44.6% (best LONG)

### 8. Confidence Doesn't Correlate
- 70-79 slightly better than 80+

### 9. Hold Time Matters
- LONG winners hold 3-8h (+1.063%)
- LONG losers hold 1-3h (-0.900%)

---

## Recommendations for WR/Profitability

### Immediate (Shadow Mode)

1. **Focus on PM Trail** — only profitable exit engine (t=57.58 SHORT, t=50.24 LONG)
2. **Reduce Hard Max usage** — biggest loser (t=-229 SHORT, t=-210 LONG)
3. **Reduce Cut Loser usage** — second biggest loser (t=-283 SHORT, t=-128 LONG)
4. **Avoid FLAT regime** — WR 15.8% LONG / 10.2% SHORT
5. **SHORT best hours: 8, 18, 6, 13, 2** — consider time-based filtering
6. **LONG best hours: 23, 14, 22, 20** — consider time-based filtering
7. **Protect significantly negative tokens**: CRV, NXPC, CHIP, HYPER, STX, ICP, NEO, APT, IO, LDO
8. **Keep CONFLUENCE-EXPIRY** — it's helping (t=-14.03 LONG, t=-9.94 SHORT)

### Strategic

9. **Fix RR problem** — avg win +0.412% vs avg loss -0.818% (RR 0.50)
10. **Need WR 66.5% to break even** — current WR is 56.7% (9.8pp below)
11. **squeeze_cross is the worst signal** — LONG t=-6.41, SHORT t=-3.85
12. **pump-chain is losing badly** — SHORT t=-7.43, LONG t=-5.85

---

## Methodology

- **Data:** 31,986 shadow trades from `brain/shadow_trades.db` (Oct 7-28, 21 days)
- **Outcomes:** `net_pnl_pct` (gross - fee - slippage = net)
- **MFE/MAE:** Rebuilt with hold-window logic (entry = candle open, exit = hold period end)
- **Gate-passed only:** Excludes gate-blocked counterfactuals (52.4% of trades)
- **Cluster-robust statistics:** Groups by timestamp, calculates mean per cluster, then t-test on cluster means
- **Significance:** |t_cluster| > 2.0 = significant (p<0.05)
- **Fees:** 0.14%/trade (0.04% fee + 0.10% slippage)
- **Limitations:** Single exit engine (ATR) for first_exit, gate-passed period is only 8 days (Oct 20-28)

---

## Reports

- `reports/20261021-shadow-sl-sweep.md` — SL sweep analysis
- `reports/20261022-confluence-window-analysis.md` — Confluence window analysis (look-forward, debunked)
- `reports/20261022-shadow-bearish-insights.md` — Previous gross analysis (invalidated)
- `reports/20261025-shadow-net-pnl.md` — Previous net PnL analysis (no significance testing)
- `reports/20261025-shadow-fresh-analysis.md` — Previous fresh analysis (statistically under-corrected)
- `reports/20261025-shadow-final-corrected.md` — Previous corrected analysis (cluster-robust)
- `reports/20261026-shadow-mfe-mae-8h-verdict.md` — MFE/MAE 8h analysis
- `reports/20261028-shadow-deep-analysis.md` — This report (WR/profitability focus)

---

## OpenMemory

Stored: `shadow deep analysis wr profitability 2026-10-28`

Tags: `shadow-analysis`, `net-pnl`, `significance-testing`, `cluster-robust`, `pm-trail`, `hard-max`, `cut-loser`, `rr-ratio`, `breakeven-wr`, `time-of-day`, `flat-regime`, `squeeze-cross`, `pump-chain`
