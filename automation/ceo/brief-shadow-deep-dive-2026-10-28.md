# CEO Consult: Shadow Data Deep Dive — Signal/WR/Profitability Improvements

## Context

T asked for a deep dive into our shadow data (100x more data than previously available) to find improvements for signals, winrate, and profitability. We now have 31,986 shadow trades (Oct 7-28, 21 days) with full context data, exit engine simulations, and gate impact analysis.

**Full report:** `reports/20261028-shadow-deep-analysis.md` (commit `382c8132`)  
**Analysis scripts:** `/tmp/shadow_deep_analysis.py`, `/tmp/shadow_net_fresh.py`  
**Previous reports:** `reports/20261025-shadow-final-corrected.md`, `reports/20261026-shadow-mfe-mae-8h-verdict.md`

---

## Key Findings (31,986 signals)

### 1. Overall Stats (Gate-Passed Only)

| Metric | Value |
|--------|-------|
| Total rows in DB | 31,986 |
| Gate-passed with net PnL | 15,165 |
| Period | Oct 20-28 (8 days) |
| **NET PnL** | **-1,833.1%** |
| AVG | -0.121% ± 0.742% |
| Cluster t | **-14.59** (4,887 clusters) |
| **WIN RATE** | **56.7%** |
| Breakeven WR needed | **66.5%** (gap: 9.8pp) |

**The system is losing money net of fees.** Need 66.5% WR to break even.

### 2. No Signal is Net-Positive AND Significant

At n>=50, no signal survives significance testing (|t_cluster| > 2.0).

**Top signals (by total):**

| Signal | Dir | N | WR% | Total% | t | Sig? |
|--------|-----|-----|-----|--------|---|------|
| hmacd_mtf | LONG | 394 | 68.8% | -4.0% | -1.61 | |
| continuum_score_long | LONG | 62 | 38.7% | -5.0% | -2.31 | ★ |
| support_resistance | LONG | 89 | 53.9% | -7.7% | -1.61 | |

**Significantly negative signals:**

| Signal | Dir | N | WR% | Total% | t | Sig? |
|--------|-----|-----|-----|--------|---|------|
| squeeze_cross | LONG | 3,484 | 56.2% | **-636.6%** | **-6.41** | ★ |
| squeeze_cross | SHORT | 5,351 | 66.7% | **-300.6%** | **-3.85** | ★ |
| support_resistance | SHORT | 1,795 | 63.6% | **-172.0%** | **-6.20** | ★ |
| pump-chain | SHORT | 578 | 30.6% | **-141.3%** | **-7.43** | ★ |
| volume_breakout_long | LONG | 647 | 31.2% | **-104.3%** | **-2.99** | ★ |
| ichimoku_short | SHORT | 715 | 52.0% | **-75.5%** | **-4.12** | ★ |
| doji_bottom_long | LONG | 193 | 46.6% | **-63.2%** | **-4.61** | ★ |
| pump-chain | LONG | 245 | 28.2% | **-71.3%** | **-5.85** | ★ |
| pump-chain-v6 | LONG | 143 | 27.3% | **-44.8%** | **-4.26** | ★ |
| volume_buildup_short | SHORT | 376 | 46.5% | **-57.3%** | **-4.39** | ★ |

**squeeze_cross is the worst signal** — LONG t=-6.41, SHORT t=-3.85.

### 3. Exit Engine Analysis

**Profitable Engines:**

| Engine | Dir | N | WR% | Total% | t |
|--------|-----|-----|-----|--------|---|
| **pm_trail** | **SHORT** | 5,287 | **100.0%** | **+1,966.7%** | **57.58** |
| **pm_trail** | **LONG** | 2,540 | **100.0%** | **+958.1%** | **50.24** |
| hold | LONG | 546 | 45.2% | +221.6% | 5.21 |
| pump_exit | SHORT | 135 | 67.4% | +55.2% | 6.72 |

**Losing Engines:**

| Engine | Dir | N | WR% | Total% | t |
|--------|-----|-----|-----|--------|---|
| **hard_max** | **SHORT** | 2,032 | 0.0% | **-1,948.0%** | **-229.39** |
| **hard_max** | **LONG** | 1,956 | 0.0% | **-1,887.3%** | **-210.33** |
| **cut_loser** | **SHORT** | 321 | 0.0% | **-384.8%** | **-283.68** |
| **cut_loser** | **LONG** | 110 | 0.0% | **-132.5%** | **-128.93** |
| rr_engine | SHORT | 832 | 13.0% | -331.3% | -25.00 |
| rr_engine | LONG | 398 | 11.8% | -146.9% | -18.93 |

**PM Trail is the ONLY profitable exit engine** — t=57.58 (SHORT), t=50.24 (LONG).

**Hard Max and Cut Loser are the BIGGEST losers** — t=-229 and t=-283.

### 4. Token Analysis

**No token is net-positive AND significant at n>=30.**

**Significantly negative tokens:**

| Token | Dir | N | WR% | Total% | t | Sig? |
|-------|-----|-----|-----|--------|---|------|
| CRV | SHORT | 174 | 51.1% | **-37.7%** | **-4.55** | ★ |
| NXPC | SHORT | 148 | 52.0% | **-36.7%** | **-4.19** | ★ |
| CHIP | SHORT | 156 | 48.1% | **-35.4%** | **-3.79** | ★ |
| HYPER | SHORT | 122 | 45.1% | **-34.5%** | **-3.78** | ★ |
| STX | LONG | 86 | 43.0% | **-32.5%** | **-5.14** | ★ |
| ICP | LONG | 65 | 35.4% | **-31.2%** | **-6.42** | ★ |
| NEO | LONG | 72 | 34.7% | **-29.5%** | **-5.26** | ★ |
| APT | LONG | 128 | 52.3% | **-29.2%** | **-3.94** | ★ |
| IO | LONG | 64 | 37.5% | **-28.2%** | **-5.91** | ★ |
| LDO | LONG | 69 | 37.7% | **-27.5%** | **-4.80** | ★ |

### 5. Risk-Reward Analysis

| Direction | WR% | Avg Win | Avg Loss | RR Ratio | Breakeven WR | Gap |
|-----------|-----|---------|----------|----------|--------------|-----|
| LONG | 49.7% | +0.471% | -0.814% | 0.58 | 63.3% | +13.7pp |
| SHORT | 61.2% | +0.381% | -0.821% | 0.46 | 68.3% | +7.1pp |
| **ALL** | **56.7%** | **+0.412%** | **-0.818%** | **0.50** | **66.5%** | **+9.8pp** |

**RR Ratio is 0.50** — avg win is only 50% of avg loss.

### 6. Time-of-Day Analysis

**SHORT Best Hours (WR >= 65%):**

| Hour | N | WR% | Avg% |
|------|-----|-----|------|
| **8** | 321 | **74.5%** | **+0.101%** |
| **18** | 488 | **74.8%** | **+0.039%** |
| **6** | 463 | **71.7%** | **+0.017%** |
| **13** | 305 | **68.5%** | **+0.020%** |
| **2** | 451 | **67.6%** | **+0.011%** |

**LONG Best Hours (WR >= 55%):**

| Hour | N | WR% | Avg% |
|------|-----|-----|------|
| **23** | 272 | **67.6%** | **+0.139%** |
| **14** | 230 | **66.5%** | **+0.093%** |
| **22** | 324 | **63.6%** | **+0.002%** |
| 20 | 193 | 58.0% | -0.077% |

**LONG Worst Hours (WR <= 40%):**

| Hour | N | WR% | Avg% |
|------|-----|-----|------|
| **5** | 177 | **33.9%** | **-0.398%** |
| **8** | 159 | **34.0%** | **-0.295%** |
| **18** | 352 | **36.9%** | **-0.402%** |

**Time-of-day matters for SHORT.** Best hours: 8, 18, 6, 13, 2 (WR 67-75%).

### 7. RSI Band Analysis

| RSI | LONG_WR | SHORT_WR |
|-----|---------|----------|
| <30 | 44.6% | 43.0% |
| 30-40 | 43.3% | 40.5% |
| 40-50 | 40.0% | 42.1% |
| 50-60 | 36.7% | 43.8% |
| 60-70 | 36.3% | **55.8%** |
| >70 | 32.9% | 48.6% |

**SHORT 60-70 RSI is the best band** (WR 55.8%). LONG >70 is the worst (WR 32.9%).

### 8. Confidence Analysis

| Band | LONG_WR | SHORT_WR |
|------|---------|----------|
| 60-69 | 29.4% | 22.2% |
| 70-79 | **53.1%** | **61.5%** |
| 80+ | 46.9% | 61.1% |

**70-79 confidence is slightly better than 80+** for both directions.

### 9. Vol Regime Analysis

| Regime | LONG_WR | SHORT_WR |
|--------|---------|----------|
| **FLAT** | **15.8%** | **10.2%** |
| NORMAL | 36.1% | 42.5% |
| HIGH | 46.5% | 47.6% |
| EXTREME | 37.4% | 45.8% |

**FLAT regime is CATASTROPHIC** — WR 15.8% LONG / 10.2% SHORT.

### 10. Hold Time Analysis

| Outcome | Hold | LONG_Avg | SHORT_Avg |
|---------|------|----------|-----------|
| WIN | **3-8h** | **+1.063%** | +0.331% |
| WIN | <15m | +0.418% | +0.408% |
| LOSS | **1-3h** | **-0.900%** | -0.890% |
| LOSS | 15-60m | -0.844% | -0.856% |

**LONG winners hold 3-8h (+1.063%)** and losers hold 1-3h (-0.900%).

### 11. Gate Impact

| Gate | Dir | N | Total% | t | Verdict |
|------|-----|-----|--------|---|---------|
| **CONFLUENCE-EXPIRY** | **LONG** | 4,763 | **-804.6%** | **-14.03** | **HELPING** |
| **CONFLUENCE-EXPIRY** | **SHORT** | 7,932 | **-781.8%** | **-9.94** | **HELPING** |
| **CTX-GATE** | **LONG** | 1,017 | **-160.8%** | **-3.88** | **HELPING** |

**ALL gates are HELPING** (blocking losing trades).

---

## Recommendations

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

## Questions for CEO

1. **Should we implement time-based filtering?** SHORT best hours (8, 18, 6, 13, 2) have WR 67-75%, while worst hours have WR 40-52%. This is a significant edge.

2. **Should we avoid FLAT regime?** WR 15.8% LONG / 10.2% SHORT is catastrophic. A FLAT regime block could save significant losses.

3. **Should we reduce Hard Max / Cut Loser usage?** These are the biggest losers (t=-229, t=-283). PM Trail is the only profitable engine.

4. **Should we filter out significantly negative tokens?** 10 tokens have t < -3.78, totaling -315.6% in losses.

5. **Should we fix the RR problem?** Current RR is 0.50 (breakeven WR 66.5%). The exit engines are cutting winners short and letting losers run.

6. **Should we focus on specific signals?** No signal is net-positive AND significant at n>=50. The system needs fundamental improvement.

7. **Priority vs existing trials?** We have wider SL trial (FAILING), extended time trial (FAILING), CONTRARIAN-LIVE (0 trades), coupled SL trial (Nov 3). Should this work wait or run in parallel?

---

## Constraints

- 31,986 shadow trades (Oct 7-28, 21 days)
- Gate-passed only: 15,165 trades (Oct 20-28, 8 days)
- Net PnL (post-fee): 0.14%/trade (0.04% fee + 0.10% slippage)
- Cluster-robust statistics: |t| > 2.0 = significant (p<0.05)
- Single exit engine (ATR) for first_exit
- Existing trials: wider SL (FAILING), extended time (FAILING), CONTRARIAN-LIVE (0 trades), coupled SL (Nov 3)
- Live system: 7d WR ~50%, -$0.47
- CEO standing rule: "Do NOT loosen HML... Fix entry quality and exit trailing instead"

---

## Full Report

`reports/20261028-shadow-deep-analysis.md` (commit `382c8132`)
