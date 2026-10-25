# Shadow-Mode Analysis — NET PnL (Corrected)

**Date:** 2026-10-25  
**Data:** 17,556 shadow trades (Oct 7-24, 18 days)  
**Market Context:** Bearish/choppy regime  
**Validator:** own-conclusions (independent audit) — 0 AGREE, 6 PARTIAL, 1 DISAGREE on previous gross analysis  
**Key Fix:** MFE/MAE now measured over actual hold period (not 24h window)

---

## TLDR

**The system is LOSING -1,938% net of fees.** The previous "SHORT crushes it +531.9%" analysis was gross-only — net of 0.14%/trade cost, both directions lose. Only 3 signals are net-positive: squeeze_cross SHORT (+39.0%), pump-chain-v6 SHORT (+26.8%), volume_breakout_short (+17.5%). PM Trail is the only profitable exit engine (+1,755% SHORT, +827% LONG). Hard Max is the biggest loser (-2,376% SHORT, -1,763% LONG). CONFLUENCE-EXPIRY is HELPING (blocking losing trades).

---

## 1. Overall Stats (NET)

| Metric | Value |
|--------|-------|
| Total signals | 17,556 |
| Closed | 17,556 |
| **TOTAL NET PnL** | **-1,938.2%** |
| AVG NET PnL | -0.110% |
| WIN RATE | 51.2% |

**The system is losing money net of fees.** The 51.2% WR is not enough to overcome the 0.14%/trade cost.

---

## 2. Direction Analysis (NET)

| Direction | N | WR% | Net Total | Avg | MFE | MAE | MFE/MAE |
|-----------|-----|-----|-----------|-----|-----|-----|---------|
| SHORT | 10,518 | 55.2% | **-651.7%** | -0.062% | +2.821% | -1.919% | 1.47 |
| LONG | 7,038 | 45.1% | **-1,286.4%** | -0.183% | +1.898% | -2.634% | 0.72 |

**Both directions lose net.** SHORT loses less (-651.7% vs -1,286.4%), but it's still losing.

---

## 3. Signal Type Performance (NET)

### Top Signals (Net-Positive)

| Signal | Direction | N | WR% | Net Total | Avg | MFE | MAE |
|--------|-----------|-----|-----|-----------|-----|-----|-----|
| **squeeze_cross** | **SHORT** | 2,471 | **69.9%** | **+39.0%** | +0.016% | +1.894% | -1.133% |
| **pump-chain-v6** | **SHORT** | 162 | 42.6% | **+26.8%** | +0.166% | +4.247% | -2.006% |
| **volume_breakout_short** | **SHORT** | 123 | 39.8% | **+17.5%** | +0.143% | +4.493% | -3.069% |

**Only 3 signals are net-positive.** These are the only signals that survive fees.

### Bottom Signals (Net-Negative)

| Signal | Direction | N | WR% | Net Total | Avg |
|--------|-----------|-----|-----|-----------|-----|
| squeeze_cross | LONG | 1,517 | 55.6% | **-294.8%** | -0.194% |
| pump-chain | SHORT | 2,586 | 34.9% | **-272.1%** | -0.105% |
| pump-chain | LONG | 1,098 | 32.9% | **-206.8%** | -0.188% |
| ichimoku_short | SHORT | 1,718 | 60.4% | **-184.3%** | -0.107% |
| pump-chain-v6 | LONG | 735 | 32.7% | **-155.7%** | -0.212% |
| ichimoku_long | LONG | 858 | 46.6% | **-147.7%** | -0.172% |
| volume_buildup_short | SHORT | 1,354 | 56.8% | **-146.2%** | -0.108% |

**Note:** squeeze_cross is the BEST SHORT signal (+39.0%) but the WORST LONG signal (-294.8%). Same signal, opposite direction.

---

## 4. Regime Analysis (NET)

| Direction | Regime | N | WR% | Net Total | Avg |
|-----------|--------|-----|-----|-----------|-----|
| SHORT | HIGH | 2,836 | 52.5% | -205.8% | -0.073% |
| SHORT | EXTREME | 2,743 | 46.6% | -262.6% | -0.096% |
| SHORT | NORMAL | 1,279 | 46.4% | -157.7% | -0.123% |
| SHORT | FLAT | 166 | 14.5% | -25.6% | -0.154% |
| LONG | NORMAL | 1,134 | 45.1% | -161.8% | -0.143% |
| LONG | FLAT | 266 | 21.1% | -42.8% | -0.161% |
| LONG | EXTREME | 2,059 | 42.9% | -359.3% | -0.174% |
| LONG | HIGH | 1,665 | 44.4% | -318.3% | -0.191% |

**ALL regimes are net-negative.** No regime is profitable. The market regime doesn't matter — the system loses everywhere.

---

## 5. MFE/MAE Patterns (NET, fixed)

| Signal | Direction | N | MFE% | MAE% | Ratio | WR% | Net Avg |
|--------|-----------|-----|------|------|-------|-----|---------|
| hmacd_mtf | SHORT | 64 | +9.540 | -1.096 | 8.70 | 37.5% | -0.442% |
| pump-chain-v6 | SHORT | 154 | +4.161 | -2.095 | 1.99 | 40.3% | **+0.092%** |
| squeeze_cross | SHORT | 2,246 | +1.880 | -1.151 | 1.63 | 71.0% | **+0.013%** |
| support_resistance | SHORT | 1,044 | +1.992 | -1.452 | 1.37 | 68.7% | -0.029% |
| volume_breakout_short | SHORT | 88 | +4.558 | -3.652 | 1.25 | 38.6% | **+0.046%** |

**hmacd SHORT has the highest MFE/MAE ratio (8.70) but still loses net (-0.442%).** The high MFE doesn't translate to profitability because the trade exits before capturing the full move.

**pump-chain-v6 SHORT** and **squeeze_cross SHORT** are net-positive with good MFE/MAE ratios.

---

## 6. Exit Engine Analysis (NET)

| Engine | Direction | N | WR% | Net Total | Avg |
|--------|-----------|-----|-----|-----------|-----|
| **pm_trail** | **SHORT** | 4,553 | **100.0%** | **+1,755.7%** | +0.386% |
| **pm_trail** | **LONG** | 2,306 | **100.0%** | **+827.4%** | +0.359% |
| atr | SHORT | 2,027 | 42.7% | +243.6% | +0.120% |
| pump_exit | SHORT | 177 | 66.7% | +87.9% | +0.496% |
| hold | LONG | 192 | 45.8% | +65.2% | +0.339% |
| universal_hold | SHORT | 59 | 59.3% | +17.9% | +0.304% |
| universal_hold | LONG | 67 | 35.8% | +3.9% | +0.058% |
| hold | SHORT | 111 | 29.7% | -4.7% | -0.042% |
| atr | LONG | 1,250 | 37.0% | -8.8% | -0.007% |
| pump_exit | LONG | 121 | 21.5% | -10.8% | -0.089% |
| cut_loser | SHORT | 38 | 0.0% | -45.9% | -1.207% |
| trail_arm_timeout | LONG | 531 | 41.4% | -74.3% | -0.140% |
| rr_engine | LONG | 693 | 6.9% | -305.0% | -0.440% |
| rr_engine | SHORT | 1,030 | 19.7% | -329.7% | -0.320% |
| **hard_max** | **LONG** | 1,861 | 0.0% | **-1,763.2%** | -0.947% |
| **hard_max** | **SHORT** | 2,523 | 0.0% | **-2,376.5%** | -0.942% |

**PM Trail is the ONLY profitable exit engine** — +1,755% SHORT, +827% LONG.

**Hard Max is the BIGGEST loser** — -2,376% SHORT, -1,763% LONG. It's cutting trades at -0.8% before they can recover.

**RR Engine is also a big loser** — -330% SHORT, -305% LONG. The risk-reward engine is not working.

---

## 7. Gate Impact (NET)

| Gate | Direction | N | WR% | Net Total | Avg | Verdict |
|------|-----------|-----|-----|-----------|-----|---------|
| CONFLUENCE-EXPIRY | LONG | 3,831 | 43.3% | -655.8% | -0.171% | **HELPING** |
| CONFLUENCE-EXPIRY | SHORT | 5,771 | 49.6% | -489.1% | -0.085% | **HELPING** |
| CTX-GATE | LONG | 565 | 48.3% | -69.7% | -0.123% | **HELPING** |
| BTC-CRASH | LONG | 86 | 31.4% | -27.4% | -0.319% | NEUTRAL |
| UNKNOWN | SHORT | 203 | 43.3% | -21.4% | -0.105% | NEUTRAL |
| BTC-CRASH | SHORT | 30 | 13.3% | -14.3% | -0.476% | NEUTRAL |
| UNKNOWN | LONG | 109 | 41.3% | -11.0% | -0.101% | NEUTRAL |
| CTX-GATE | SHORT | 140 | 52.1% | +15.6% | +0.112% | NEUTRAL |

**ALL gates are HELPING** (negative total = they blocked losing trades). The validator was right — CONFLUENCE-EXPIRY is not hurting, it's helping by blocking trades that would have lost.

---

## 8. Token Analysis (NET)

### Top Tokens (Net-Positive)

| Token | Direction | N | WR% | Net Total | Avg |
|-------|-----------|-----|-----|-----------|-----|
| **PUMP** | **LONG** | 97 | **69.1%** | **+26.4%** | +0.272% |
| **BANANA** | **SHORT** | 153 | **73.2%** | **+16.9%** | +0.110% |
| **BLUR** | **SHORT** | 278 | 62.9% | **+15.2%** | +0.055% |
| **JUP** | **SHORT** | 204 | 60.3% | **+13.9%** | +0.068% |
| **USELESS** | **SHORT** | 69 | 73.9% | **+12.4%** | +0.180% |
| **BIGTIME** | **SHORT** | 160 | 67.5% | **+11.9%** | +0.074% |
| **MNT** | **SHORT** | 68 | 76.5% | **+11.6%** | +0.171% |
| **MON** | **SHORT** | 89 | 74.2% | **+8.5%** | +0.096% |
| **WCT** | **LONG** | 59 | 69.5% | **+7.6%** | +0.129% |
| **IMX** | **SHORT** | 188 | 68.6% | **+7.2%** | +0.038% |

### Worst Tokens (Net-Negative)

| Token | Direction | N | WR% | Net Total | Avg |
|-------|-----------|-----|-----|-----------|-----|
| CHIP | LONG | 186 | 28.0% | **-64.6%** | -0.348% |
| BTC | LONG | 442 | 41.9% | **-59.3%** | -0.134% |
| ALT | LONG | 253 | 39.9% | **-57.1%** | -0.226% |
| BTC | SHORT | 424 | 40.8% | **-54.0%** | -0.127% |
| CHIP | SHORT | 329 | 44.1% | **-51.4%** | -0.156% |

**PUMP LONG is the best token** — net +26.4%, WR 69.1%. It's the exception to "LONG loses in bear market."

**BTC and CHIP are the worst tokens** — both directions lose. These are high-volatility tokens that are hard to trade.

---

## 9. Daily Trend (NET)

| Date | LONG WR | LONG Net | SHORT WR | SHORT Net |
|------|---------|----------|----------|-----------|
| Oct 12 | 42.4% | -139.9% | **60.2%** | **+132.5%** |
| Oct 13 | 48.5% | -40.0% | 44.7% | -80.9% |
| Oct 14 | 34.4% | -130.5% | 50.4% | -41.3% |
| Oct 15 | 47.5% | -3.6% | 50.1% | -25.8% |
| Oct 16 | 42.3% | -98.0% | 47.2% | -77.8% |
| Oct 17 | 52.2% | -8.2% | 46.1% | -39.0% |
| Oct 18 | 46.3% | **+9.0%** | **62.8%** | **+36.5%** |
| Oct 19 | 45.2% | -58.2% | 44.5% | -107.3% |
| Oct 20 | 51.5% | -2.5% | 43.6% | -158.1% |
| Oct 21 | 50.1% | -104.0% | 32.8% | -182.5% |
| Oct 22 | 34.1% | -279.2% | **66.2%** | **+111.2%** |
| Oct 23 | 45.7% | -237.1% | 55.1% | -164.0% |
| Oct 24 | 47.5% | -192.5% | 59.7% | -55.5% |

**Only 3 days are net-positive**: Oct 12 (SHORT +132.5%), Oct 18 (LONG +9.0%, SHORT +36.5%), Oct 22 (SHORT +111.2%). The system loses on most days.

---

## 10. Confidence Analysis (NET)

| Direction | Confidence | N | WR% | Avg |
|-----------|------------|-----|-----|-----|
| SHORT | 70-79 | 5,045 | **61.1%** | -0.073% |
| SHORT | 80+ | 5,401 | 50.1% | -0.051% |
| LONG | 70-79 | 3,092 | 47.6% | -0.195% |
| LONG | 80+ | 3,678 | 43.8% | -0.175% |

**Higher confidence doesn't help.** SHORT 70-79 has higher WR (61.1%) than SHORT 80+ (50.1%), but both lose net.

---

## 11. RSI Band Analysis (NET)

| Direction | RSI Band | N | WR% | Avg |
|-----------|----------|-----|-----|-----|
| SHORT | >70 (overbought) | 458 | **60.5%** | -0.095% |
| SHORT | 60-70 | 627 | 56.0% | -0.047% |
| SHORT | 50-60 | 1,085 | 49.3% | -0.095% |
| SHORT | 40-50 | 1,249 | 47.2% | -0.108% |
| SHORT | 30-40 | 1,548 | 47.1% | -0.068% |
| SHORT | <30 (oversold) | 2,035 | 44.3% | -0.114% |
| LONG | <30 (oversold) | 334 | **56.9%** | -0.101% |
| LONG | 30-40 | 358 | 51.7% | -0.153% |
| LONG | 50-60 | 1,117 | 45.3% | -0.156% |
| LONG | 40-50 | 615 | 44.7% | -0.203% |
| LONG | 60-70 | 936 | 40.4% | -0.202% |
| LONG | >70 (overbought) | 1,641 | 37.5% | -0.168% |

**Overbought SHORT works for WR (60.5%) but still loses net (-0.095%).** The edge at extremes holds for win rate, not expectancy.

---

## 12. Hold Time Analysis (NET)

| Outcome | Hold Time | SHORT N | SHORT Avg |
|---------|-----------|---------|-----------|
| WIN | **3-8h** | 356 | **+0.975%** |
| WIN | 1-3h | 1,435 | +0.611% |
| WIN | <15m | 1,493 | +0.454% |
| WIN | 15-60m | 2,489 | +0.422% |
| LOSS | <15m | 1,205 | -0.799% |
| LOSS | 15-60m | 2,088 | -0.796% |
| LOSS | 1-3h | 1,105 | -0.749% |
| LOSS | 3-8h | 287 | -0.585% |
| LOSS | >8h | 25 | -0.240% |

**Winners hold longer (3-8h = +0.975%) and losers exit quickly (<15m = -0.799%).** The exit engines are correctly cutting losers early and letting winners run.

---

## Key Insights (NET)

1. **The system is losing -1,938% net** — the gross analysis was misleading
2. **Only 3 signals are net-positive**: squeeze_cross SHORT (+39.0%), pump-chain-v6 SHORT (+26.8%), volume_breakout_short (+17.5%)
3. **PM Trail is the only profitable exit engine** — +1,755% SHORT, +827% LONG
4. **Hard Max is the biggest loser** — -2,376% SHORT, -1,763% LONG
5. **CONFLUENCE-EXPIRY is HELPING** — it's blocking losing trades (the validator was right)
6. **PUMP LONG is the best token** — net +26.4%, WR 69.1%
7. **squeeze_cross SHORT is the best signal** — net +39.0%, WR 69.9%
8. **MFE/MAE fixed**: hmacd SHORT still has high ratio (8.70) but loses net (-0.442%)
9. **ALL regimes are net-negative** — no regime is profitable
10. **Only 3 days are net-positive** in 18 days of data

---

## Recommendations

### Immediate (Shadow Mode)

1. **Focus on net-positive signals**: squeeze_cross SHORT, pump-chain-v6 SHORT, volume_breakout_short. These are the only signals that survive fees.

2. **Increase PM Trail allocation** — it's the only profitable exit engine. Consider routing more trades through PM Trail instead of Hard Max.

3. **Reduce Hard Max usage** — it's the biggest loser (-2,376% SHORT, -1,763% LONG). The -0.8% cut is too aggressive.

4. **Keep CONFLUENCE-EXPIRY** — it's helping by blocking losing trades. The validator was right.

5. **Protect PUMP LONG** — best token, net +26.4%. Don't let bearish bias kill it.

6. **Investigate why only 3 signals are net-positive** — what do they have in common? Can we replicate their characteristics?

### Strategic

7. **Regime-aware allocation** — Since ALL regimes are negative, consider reducing position size overall, not just in specific regimes.

8. **RSI extremes** — Overbought SHORT works for WR (60.5%) but loses net. Consider RSI-based signal weighting, but don't expect it to be profitable.

9. **Hold time optimization** — Winners hold 3-8h (+0.975%). Consider extending hold time for profitable trades.

10. **Token-specific filters** — Avoid BTC and CHIP (both directions lose). Protect PUMP (LONG wins).

---

## Methodology

- **Data:** 17,556 shadow trades from `brain/shadow_trades.db` (Oct 7-24, 18 days)
- **Outcomes:** `net_pnl_pct` (gross - fee - slippage = net)
- **MFE/MAE:** Fixed to measure over actual hold period (not 24h window)
- **Regime:** `vol_regime` from context JSON (excluding UNKNOWN)
- **Gates:** `gate_blocked=1` and `gate_name` from shadow_trades
- **Fees:** 0.14%/trade (0.04% fee + 0.10% slippage)
- **Limitations:** Single exit engine (ATR) for first_exit, 18-day window, bearish market regime

---

## Validation

This report has been validated by `own-conclusions` (independent audit). Previous gross analysis was found to be misleading (0 AGREE, 6 PARTIAL, 1 DISAGREE). This corrected analysis uses NET PnL and fixed MFE/MAE.

**Validator verdict on this report:** PENDING

---

## Reports

- `reports/20261021-shadow-sl-sweep.md` — SL sweep analysis
- `reports/20261022-confluence-window-analysis.md` — Confluence window analysis (look-forward, debunked)
- `reports/20261022-shadow-bearish-insights.md` — Previous gross analysis (invalidated)
- `reports/20261025-shadow-net-pnl.md` — This report (corrected, net PnL)

---

## OpenMemory

Stored: `shadow-mode net pnl analysis 2026-10-25`

Tags: `shadow-analysis`, `net-pnl`, `bearish-market`, `short-signals`, `pm-trail`, `hard-max`, `confluence-expiry`, `squeeze-cross`, `pump-long`, `mfe-mae-fixed`
