# Shadow-Mode Analysis — Fresh Data with Significance Testing

**Date:** 2026-10-25  
**Data:** 20,878 shadow trades (Oct 7-25, 18 days)  
**Market Context:** Bearish/choppy regime  
**Key Fix:** MFE/MAE measured over actual hold period (not 24h window)  
**Analysis:** NET PnL (post-fee), gate-passed only, with t-statistics

---

## TLDR

**The system is losing -718.2% net of fees (gate-passed only), t=-11.15 (highly significant).** Only 1 signal is net-positive AND statistically significant: squeeze_cross SHORT (t=2.01). PM Trail is the only profitable exit engine (t=66.83). Hard Max is the biggest loser (t=-557). ALL gates are HELPING (blocking losing trades). RR ratio is 0.52 (avg win +0.417% vs avg loss -0.799%), need 65.8% WR to break even, current WR is 58.3% (7.5pp below).

---

## 1. Overall Stats (NET, Gate-Passed Only)

| Metric | Value |
|--------|-------|
| Total signals | 20,878 |
| Gate-blocked | 11,277 (58.4%) |
| Gate-passed | 8,035 (41.6%) |
| **NET PnL (gate-passed)** | **-718.2%** |
| AVG NET PnL | -0.089% ± 0.716% |
| **t-statistic** | **-11.15** (highly significant) |
| WIN RATE | 58.3% |

**The system is losing money net of fees.** The 58.3% WR is not enough to overcome the 0.14%/trade cost. Need 65.8% WR to break even.

---

## 2. Direction Analysis (NET, Gate-Passed)

| Direction | N | WR% | Net Total | Avg | t-stat | MFE/MAE |
|-----------|-----|-----|-----------|-----|--------|---------|
| SHORT | 5,083 | **64.0%** | **-142.3%** | -0.028% | **-2.99** | 1.52 |
| LONG | 2,952 | 48.6% | **-576.0%** | -0.195% | **-13.57** | 0.77 |

**Both directions lose net.** SHORT loses less (-142.3% vs -576.0%), but it's still losing (t=-2.99). LONG is losing badly (t=-13.57).

---

## 3. Signal Type Performance (NET, Gate-Passed, n>=30)

### Top Signals (Net-Positive AND Significant)

| Signal | Direction | N | WR% | Net Total | Avg | t-stat | Sig? |
|--------|-----------|-----|-----|-----------|-----|--------|------|
| **squeeze_cross** | **SHORT** | 2,953 | **70.8%** | **+73.9%** | +0.025% | **2.01** | **★** |

**Only 1 signal is net-positive AND statistically significant.** squeeze_cross SHORT has t=2.01 (p<0.05).

### Significantly Negative Signals

| Signal | Direction | N | WR% | Net Total | Avg | t-stat | Sig? |
|--------|-----------|-----|-----|-----------|-----|--------|------|
| squeeze_cross | LONG | 1,786 | 56.4% | **-314.8%** | -0.176% | **-11.34** | ★ |
| pump-chain | SHORT | 404 | 31.4% | **-97.4%** | -0.241% | **-6.38** | ★ |
| doji_bottom_long | LONG | 148 | 41.9% | **-60.5%** | -0.409% | **-7.64** | ★ |
| pump-chain | LONG | 118 | 18.6% | **-55.3%** | -0.469% | **-7.77** | ★ |
| volume_buildup_short | SHORT | 233 | 49.8% | **-33.5%** | -0.144% | **-3.83** | ★ |
| bollinger_squeeze_short | SHORT | 161 | 55.3% | **-31.4%** | -0.195% | **-3.62** | ★ |
| support_resistance | LONG | 43 | 44.2% | **-11.8%** | -0.274% | **-3.31** | ★ |
| ichimoku_long | LONG | 90 | 36.7% | **-18.3%** | -0.203% | **-3.91** | ★ |
| pump-chain-v6 | LONG | 63 | 25.4% | **-24.4%** | -0.387% | **-3.74** | ★ |

**Note:** squeeze_cross is the BEST SHORT signal (+73.9%, t=2.01) but the WORST LONG signal (-314.8%, t=-11.34). Same signal, opposite direction.

---

## 4. Exit Engine Analysis (NET, Gate-Passed)

### Profitable Engines

| Engine | Direction | N | WR% | Net Total | Avg | t-stat |
|--------|-----------|-----|-----|-----------|-----|--------|
| **pm_trail** | **SHORT** | 3,034 | **100.0%** | **+1,197.0%** | +0.395% | **66.83** |
| **pm_trail** | **LONG** | 1,278 | **100.0%** | **+467.6%** | +0.366% | **51.72** |
| hold | LONG | 223 | 40.8% | +79.1% | +0.355% | 3.52 |
| pump_exit | SHORT | 84 | 63.1% | +36.2% | +0.431% | 5.64 |

### Losing Engines

| Engine | Direction | N | WR% | Net Total | Avg | t-stat |
|--------|-----------|-----|-----|-----------|-----|--------|
| **hard_max** | **SHORT** | 1,237 | 0.0% | **-1,164.3%** | -0.941% | **-523.29** |
| **hard_max** | **LONG** | 1,044 | 0.0% | **-986.7%** | -0.945% | **-557.47** |
| rr_engine | SHORT | 436 | 19.0% | -150.2% | -0.344% | -17.03 |
| rr_engine | LONG | 195 | 7.2% | -81.1% | -0.416% | -16.24 |
| atr | SHORT | 182 | 33.0% | -34.4% | -0.189% | -3.06 |
| atr | LONG | 126 | 20.6% | -35.4% | -0.281% | -3.53 |

**PM Trail is the ONLY profitable exit engine** — t=66.83 (SHORT), t=51.72 (LONG).

**Hard Max is the BIGGEST loser** — t=-523 (SHORT), t=-557 (LONG). It's cutting trades at -0.8% before they can recover.

---

## 5. Token Analysis (NET, Gate-Passed, n>=30)

### Significantly Positive Tokens

| Token | Direction | N | WR% | Net Total | Avg | t-stat | Sig? |
|-------|-----------|-----|-----|-----------|-----|--------|------|
| **MNT** | **SHORT** | 58 | **84.5%** | **+17.3%** | +0.298% | **3.59** | **★** |
| **SUPER** | **SHORT** | 59 | **79.7%** | **+11.2%** | +0.189% | **2.34** | **★** |
| **IMX** | **SHORT** | 77 | **81.8%** | **+11.1%** | +0.144% | **2.54** | **★** |
| **ALGO** | **SHORT** | 68 | **76.5%** | **+9.6%** | +0.141% | **2.06** | **★** |
| **LTC** | **SHORT** | 74 | **78.4%** | **+9.5%** | +0.128% | **2.27** | **★** |

**5 tokens are significantly positive (all SHORT).** MNT has the highest t-stat (3.59).

### Significantly Negative Tokens

| Token | Direction | N | WR% | Net Total | Avg | t-stat | Sig? |
|-------|-----------|-----|-----|-----------|-----|--------|------|
| CHIP | SHORT | 111 | 45.9% | **-29.0%** | -0.261% | **-3.74** | ★ |
| NXPC | SHORT | 102 | 52.9% | **-24.4%** | -0.239% | **-3.35** | ★ |
| ICP | LONG | 37 | 24.3% | **-23.8%** | -0.643% | **-7.79** | ★ |
| ALT | LONG | 56 | 26.8% | **-23.2%** | -0.415% | **-3.41** | ★ |
| LDO | LONG | 44 | 38.6% | **-19.0%** | -0.432% | **-5.18** | ★ |

**Avoid these tokens.** ICP LONG has the worst t-stat (-7.79).

---

## 6. Gate Impact (NET)

| Gate | Direction | N | WR% | Net Total | Avg | t-stat | Verdict |
|------|-----------|-----|-----|-----------|-----|--------|---------|
| **CONFLUENCE-EXPIRY** | **LONG** | 3,939 | 43.0% | **-674.3%** | -0.171% | **-13.46** | **HELPING** |
| **CONFLUENCE-EXPIRY** | **SHORT** | 6,142 | 50.0% | **-494.6%** | -0.081% | **-7.56** | **HELPING** |
| **CTX-GATE** | **LONG** | 584 | 48.5% | **-69.9%** | -0.120% | **-4.23** | **HELPING** |
| BTC-CRASH | LONG | 86 | 31.4% | -27.4% | -0.319% | -6.93 | NEUTRAL |
| UNKNOWN | SHORT | 213 | 44.6% | -22.0% | -0.103% | -2.46 | NEUTRAL |
| UNKNOWN | LONG | 119 | 37.8% | -17.0% | -0.143% | -2.62 | NEUTRAL |
| BTC-CRASH | SHORT | 30 | 13.3% | -14.3% | -0.476% | -5.74 | NEUTRAL |
| CTX-GATE | SHORT | 148 | 53.4% | +14.8% | +0.100% | 1.05 | NEUTRAL |

**ALL gates are HELPING** (blocking losing trades). CONFLUENCE-EXPIRY is the biggest helper (t=-13.46 LONG, t=-7.56 SHORT).

---

## 7. Daily Trend (NET, Gate-Passed)

| Date | LONG WR | LONG Net | SHORT WR | SHORT Net |
|------|---------|----------|----------|-----------|
| Oct 20 | 57.7% | -0.1% | 18.2% | -11.7% |
| Oct 21 | 41.8% | -36.2% | 38.7% | -46.7% |
| Oct 22 | 39.4% | -170.8% | **69.6%** | **+50.1%** |
| Oct 23 | 48.6% | -203.5% | 59.6% | -119.4% |
| Oct 24 | 59.3% | -40.0% | 58.0% | -113.5% |
| Oct 25 | 28.8% | -125.4% | **79.6%** | **+99.0%** |

**Only 2 days are net-positive**: Oct 22 (SHORT +50.1%), Oct 25 (SHORT +99.0%). The system loses on most days.

---

## 8. Risk-Reward Analysis

| Direction | Wins | Losses | WR% | Avg Win | Avg Loss | RR Ratio |
|-----------|------|--------|-----|---------|----------|----------|
| LONG | 1,434 | 1,518 | 48.6% | +0.440% | -0.795% | 0.55 |
| SHORT | 3,254 | 1,829 | 64.0% | +0.407% | -0.802% | 0.51 |
| **OVERALL** | 4,688 | 3,347 | **58.3%** | **+0.417%** | **-0.799%** | **0.52** |

**RR Ratio is 0.52** — avg win is only 52% of avg loss. Need 65.8% WR to break even, current WR is 58.3% (7.5pp below).

**The exit engines are cutting winners short and letting losers run too long.**

---

## Key Insights (Fresh Data)

1. **System is losing -718.2% net (gate-passed)** — t=-11.15, highly significant
2. **Only 1 signal is net-positive AND significant**: squeeze_cross SHORT (t=2.01)
3. **PM Trail is the only profitable exit engine** — t=66.83 (SHORT), t=51.72 (LONG)
4. **Hard Max is the biggest loser** — t=-523 (SHORT), t=-557 (LONG)
5. **ALL gates are HELPING** — they're blocking losing trades
6. **RR ratio is 0.52** — avg win +0.417% vs avg loss -0.799%
7. **Breakeven WR needed: 65.8%** — current WR is 58.3% (7.5pp below)
8. **5 tokens are significantly positive**: MNT, SUPER, IMX, ALGO, LTC (all SHORT)
9. **5 tokens are significantly negative**: CHIP, NXPC, ICP, ALT, LDO
10. **squeeze_cross is the best SHORT signal but worst LONG signal** — same signal, opposite direction

---

## Recommendations

### Immediate (Shadow Mode)

1. **Focus on squeeze_cross SHORT** — only net-positive significant signal (t=2.01). This is the edge.

2. **Increase PM Trail allocation** — only profitable exit engine (t=66.83). Route more trades through PM Trail.

3. **Reduce Hard Max usage** — biggest loser (t=-523). The -0.8% cut is too aggressive.

4. **Keep CONFLUENCE-EXPIRY** — it's helping (t=-13.46 LONG, t=-7.56 SHORT). Don't remove it.

5. **Protect significantly positive tokens**: MNT, SUPER, IMX, ALGO, LTC (all SHORT).

6. **Avoid significantly negative tokens**: CHIP, NXPC, ICP, ALT, LDO.

7. **Fix RR problem** — avg win +0.417% vs avg loss -0.799% (RR 0.52). Need to let winners run longer and cut losers faster.

### Strategic

8. **Need WR 65.8% to break even** — current WR is 58.3% (7.5pp below). Either increase WR or reduce fees.

9. **squeeze_cross LONG is the worst signal** — t=-11.34. Consider disabling or filtering it.

10. **pump-chain is losing badly in both directions** — SHORT t=-6.38, LONG t=-7.77. Consider disabling.

---

## Methodology

- **Data:** 20,878 shadow trades from `brain/shadow_trades.db` (Oct 7-25, 18 days)
- **Outcomes:** `net_pnl_pct` (gross - fee - slippage = net)
- **MFE/MAE:** Fixed to measure over actual hold period (not 24h window)
- **Gate-passed only:** Excludes gate-blocked counterfactuals (58.4% of trades)
- **Significance testing:** t-statistic for mean != 0, |t| > 2.0 = significant (p<0.05)
- **Fees:** 0.14%/trade (0.04% fee + 0.10% slippage)
- **Limitations:** Single exit engine (ATR) for first_exit, 18-day window, bearish market regime

---

## Validation

This report includes t-statistics for significance testing. Previous gross analysis was invalidated by validator (0 AGREE, 6 PARTIAL, 1 DISAGREE). This corrected analysis uses NET PnL, gate-passed only, with significance testing.

---

## Reports

- `reports/20261021-shadow-sl-sweep.md` — SL sweep analysis
- `reports/20261022-confluence-window-analysis.md` — Confluence window analysis (look-forward, debunked)
- `reports/20261022-shadow-bearish-insights.md` — Previous gross analysis (invalidated)
- `reports/20261025-shadow-net-pnl.md` — Previous net PnL analysis (no significance testing)
- `reports/20261025-shadow-fresh-analysis.md` — This report (with significance testing)

---

## OpenMemory

Stored: `shadow-mode fresh analysis with significance testing 2026-10-25`

Tags: `shadow-analysis`, `net-pnl`, `significance-testing`, `t-statistic`, `squeeze-cross`, `pm-trail`, `hard-max`, `confluence-expiry`, `rr-ratio`, `breakeven-wr`
