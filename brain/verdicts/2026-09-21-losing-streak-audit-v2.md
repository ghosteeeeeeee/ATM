# 🔍 Independent Audit: Sep 21 Losing Streak Analysis

**Auditor:** Independent (fresh analysis, no prior conclusions trusted)  
**Date:** 2026-09-21  
**Data Sources:** PostgreSQL trades (brain DB), continuum.db (BTC states), candles.db  

---

## Executive Summary

The original analysis contains **significant factual errors** and **questionable methodology**. Several claims are directly contradicted by the data. The most critical issue is that **only 17.3% of all LONG trades** have BTC continuum data (continuum.db only covers Sep 4–21), creating severe temporal bias. Additionally, the claim of "8 losing LONGs" is factually wrong—there are either 5 (opened Sep 21), 7 (closed Sep 21), or 11 (Sep 20–21 combined).

**Verdict Summary:**
- CLAIM 1: **DISAGREE** — Factual error, wrong count, wrong pattern
- CLAIM 2: **PARTIAL** — Directional truth, exact numbers wrong
- CLAIM 3: **DISAGREE** — Contradicted by data (depends on score source)
- CLAIM 4: **DISAGREE** — Contradicted by data
- CLAIM 5: **DISAGREE** — Opposite of what data shows
- CLAIM 6: **PARTIAL** — BB >1.0 is danger, >0.8 is not
- CLAIM 7: **PARTIAL** — Directionally true, tiny sample (N=12)
- CLAIM 8: **PARTIAL** — Direction correct, exact numbers off
- CLAIM 9: **PARTIAL** — Filter removes 2 trades, minimal improvement
- CLAIM 10: **DISAGREE** — Data contradicts "pumps in downtrend" narrative

---

## Methodology

### Data Matching
- **Trades table:** 5,183 total live trades, 2,262 LONG closed trades
- **Continuum.db:** BTC states from Sep 4 to Sep 21 (18 days), 1m timeframe only
- **Matched dataset:** 391 LONG trades (17.3% of all LONG trades) with BTC continuum state within ±5 minutes of trade open time
- **RSI/BB sources:** Two sources available — `signal_metadata.rsi_14` (signal detection time) and `trades.entry_rsi_14` (trade execution time). They often differ significantly (e.g., CC trade: 32.6 vs 74.6). Analysis used `signal_metadata` values by default; cross-checked with entry values.

### Key Limitation
The continuum.db only covers Sep 4–21, so **82.7% of all trades are excluded** from BTC state analysis. This creates a narrow 18-day window that may not represent the full system behavior.

---

## Trade Count Discrepancy

The original analysis references "8 losing LONGs on Sep 21." Actual counts:

| Filter | Count |
|--------|-------|
| LONG losers opened on Sep 21 | **5** |
| LONG losers closed on Sep 21 (some opened earlier) | **7** |
| LONG losers opened Sep 20–21 | **11** |

**None of these equal 8.** The fundamental premise of the analysis is based on an incorrect count.

### The 11 Losing LONGs (Sep 20–21)

| ID | Token | PnL | BTC EMA300 | Token RSI* | Token BB* | BTC Score | Signal |
|----|-------|-----|-----------|------------|-----------|-----------|--------|
| 15554 | CHIP | -$0.15 | AT | 75.6 | 1.15 | 23.9 | pump-chain+ |
| 15555 | BABY | -$0.32 | AT | 77.8 | 0.90 | 28.3 | pump-chain+ |
| 15557 | CC | -$0.16 | BELOW | 32.6 | 0.90 | 4.6 | pump-chain+ |
| 15566 | COMP | -$0.15 | AT | 62.5 | 0.73 | 18.4 | pump-chain+ |
| 15572 | WLFI | -$0.15 | ABOVE | 33.3 | 0.72 | 94.0 | doji-bottom-long |
| 15576 | HEMI | -$0.13 | ABOVE | 75.0 | 1.02 | 21.1 | pump-chain+ |
| 15578 | HYPER | -$0.17 | ABOVE | 66.7 | 0.83 | 100.0 | volume-breakout-long+ |
| 15581 | ALGO | -$0.15 | ABOVE | 68.8 | 0.90 | 40.1 | pump-chain+ |
| 15582 | HEMI | -$0.15 | ABOVE | 69.2 | 1.06 | 75.5 | pump-chain+ |
| 15584 | KAS | -$0.02 | ABOVE | 61.6 | 0.87 | 90.8 | bb-bounce-v3-long+ |
| 15585 | CAKE | -$0.18 | ABOVE | 19.2 | 0.86 | 89.9 | pump-chain+ |

*\*RSI/BB from signal_metadata (signal detection time)*

---

## Claim-by-Claim Verification

### CLAIM 1: "All 8 losing LONGs share BTC EMA300=ABOVE, RSI>70, BB>0.6"

**Verdict: ❌ DISAGREE**

- There are 11 losing LONGs (not 8)
- Only **7** have BTC EMA300=ABOVE (not all)
- Using signal_metadata RSI: only **1** out of 11 matches all 3 criteria (HEMI #15576)
- Using entry_rsi_14: about **6** match BTC EMA300=ABOVE + RSI>70 + BB>0.6
- 4 losers have BTC EMA300=AT or BELOW — they were NOT buying above EMA300

**The "all 8" claim is factually wrong on both the count and the pattern.**

---

### CLAIM 2: "BTC Score 60-80 = sweet spot for LONG (64.8% WR, +$4.83)"

**Verdict: ⚠️ PARTIAL**

Using signal_metadata btc_score:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| 60–79 | 40 | **70.0%** | **+$1.06** |
| Overall | 391 | 57.8% | +$2.17 |

Using continuum state_score:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| 60–79 | 60 | **70.0%** | **+$3.31** |
| Overall | 391 | 57.8% | +$2.17 |

**Assessment:** The directional claim is TRUE — BTC Score 60–80 does outperform. However:
- Claimed 64.8% WR → Actual 70.0% (off by 5.2 pp)
- Claimed +$4.83 → Actual +$1.06 (metadata) or +$3.31 (state_score). The +$4.83 is not reproducible from either source.
- N=40–60 is modest but adequate for directional signal.

---

### CLAIM 3: "BTC Score >80 = overextension (44.9% WR, -$2.40)"

**Verdict: ❌ DISAGREE**

Using signal_metadata btc_score:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| 80+ | 45 | **57.8%** | **+$1.24** |

Using continuum state_score:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| 80+ | 90 | **46.7%** | **-$2.81** |

**Assessment:** With the metadata btc_score, 80+ trades are PROFITABLE at 57.8% WR — directly contradicting the claim. With state_score, the claim is closer to truth (46.7% WR, -$2.81), but still off from the claimed numbers. The claim depends entirely on which "BTC Score" metric was used, and the analysis doesn't specify. This is a critical ambiguity.

---

### CLAIM 4: "RSI 55-70 = sweet spot for LONG (63.6% WR, +$2.60)"

**Verdict: ❌ DISAGREE**

Using signal_metadata rsi_14:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| 55–59 | 28 | 71.4% | +$3.24 |
| 60–64 | 54 | 46.3% | -$0.54 |
| 65–69 | 32 | 43.8% | -$0.91 |
| **55–69 combined** | **114** | **51.8%** | **+$1.79** |

Using entry_rsi_14:
| Bucket | N | WR |
|--------|---|-----|
| 55–59 | 8 | 87.5% |
| 60–64 | 11 | 54.5% |
| 65–69 | 14 | 57.1% |
| **55–69 combined** | **33** | **63.6%** |

**Assessment:** With entry_rsi_14, 55–69 does show 63.6% WR (matching the claim exactly!) — but with only N=33, this is a small sample. With signal_metadata RSI, the 55–70 bucket shows only 51.8% WR. The claim's exact number appears to come from `entry_rsi_14`, but the sample size is too small for confidence.

---

### CLAIM 5: "RSI >70 drops WR by 20+ points (41.2% WR)"

**Verdict: ❌ DISAGREE — OPPOSITE OF DATA**

Using signal_metadata rsi_14:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| >70 | 101 | **63.4%** | +$0.40 |
| Overall | 391 | 57.8% | +$2.17 |

Using entry_rsi_14:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| >70 | 39 | **51.3%** | +$1.18 |

**Assessment:** With signal_metadata RSI, >70 trades perform **BETTER** than average (63.4% vs 57.8% overall). The claim says WR drops to 41.2% — this is **completely opposite** to what the data shows. Even with entry_rsi_14, >70 shows 51.3% which is below average but nowhere near 41.2%.

**The claim that RSI >70 is dangerous is contradicted by the data.**

---

### CLAIM 6: "BB Position >0.8 = danger zone (37.5% WR)"

**Verdict: ⚠️ PARTIAL — Danger starts higher than claimed**

Using signal_metadata bb_position:
| Bucket | N | WR | Total PnL |
|--------|---|-----|-----------|
| 0.6–0.79 | 107 | 56.1% | +$1.60 |
| 0.8–0.99 | 114 | 60.5% | +$1.13 |
| **1.0+** | **48** | **43.8%** | **-$0.44** |

**Assessment:** BB 0.8–0.99 shows **60.5% WR** — perfectly healthy. The danger zone is actually **BB ≥1.0** (43.8% WR, N=48). Setting the filter at >0.8 would incorrectly block 114 good trades (60.5% WR) to catch the 48 bad ones. The correct threshold is >0.95 or >1.0.

---

### CLAIM 7: "BTC LinReg=BULL = only 25% WR for LONG"

**Verdict: ⚠️ PARTIAL — Direction true, but tiny sample**

| LinReg | N | WR | Total PnL |
|--------|---|-----|-----------|
| BULL | **12** | **33.3%** | -$0.63 |
| LEAN_BEAR | 139 | 59.7% | +$1.79 |
| LEAN_BULL | 174 | 56.9% | -$0.40 |
| NEUTRAL | 64 | 60.9% | +$1.56 |

**Assessment:** BULL does underperform at 33.3% WR (claimed 25%). However, **N=12 is dangerously small** — the 95% CI is [13.8%–60.9%], meaning this could easily be random. LEAN_BEAR and NEUTRAL actually perform best, which is counterintuitive. With N=12, this claim has insufficient evidence.

---

### CLAIM 8: "BTC Phase CALM best (59.2%), RECOVERY worst (51.0%)"

**Verdict: ⚠️ PARTIAL — Direction correct, numbers off**

| Phase | N | WR | Total PnL |
|-------|---|-----|-----------|
| CALM | 140 | **62.9%** | **+$2.17** |
| DECLINING | 153 | 54.2% | +$1.51 |
| RECOVERY | 98 | **56.1%** | **-$1.51** |

**Assessment:** CALM is best (62.9% WR, +$2.17), RECOVERY is worst in PnL (-$1.51 despite 56.1% WR). Direction is correct. Numbers differ: claimed CALM=59.2% → actual 62.9%; claimed RECOVERY=51.0% → actual 56.1%. RECOVERY's low PnL despite decent WR suggests the wins are small and losses are large — a meaningful finding worth exploring further.

---

### CLAIM 9: "Recommended: Block LONG when RSI>75, BB>0.85, BTC Score 20-40"

**Verdict: ⚠️ PARTIAL — Technically correct but trivially small impact**

Trades matching ALL three "danger" criteria: **2 trades**, 0% WR, -$0.47 total PnL.
- CHIP (15554): -$0.15
- BABY (15555): -$0.32

After filter:
- Trades removed: 2 (0.5% of dataset)
- WR improvement: 57.8% → 58.1% (+0.3 pp)
- PnL improvement: $2.17 → $2.64 (+$0.47)

**Assessment:** The filter is technically sound — both filtered trades were losers. But it removes only 2 out of 391 trades. This is not a meaningful filter. A filter that blocks 0.5% of trades is not worth implementing.

The individual components are mixed:
- RSI >75 alone: 64.3% WR (actually ABOVE average — filter would HURT)
- BB >0.85 alone: 53.9% WR (slightly below average)
- BTC Score 20-40 alone: 44.0% WR (below average)

Only the combination captures the losers, but each individual criterion fails as a standalone filter.

---

### CLAIM 10: "System is buying pumps in a downtrend — token pumps but BTC structure bearish"

**Verdict: ❌ DISAGREE**

**BTC Regime × Token RSI cross-tabulation:**

| BTC Regime | Token RSI | N | WR | Avg PnL |
|------------|-----------|---|-----|---------|
| BEAR_TREND | HIGH(>70) | 7 | 57.1% | +$0.080 |
| BEAR_TREND | LOW(≤70) | 15 | 40.0% | -$0.062 |
| BULL_TREND | HIGH(>70) | 15 | 73.3% | +$0.027 |
| BULL_TREND | LOW(≤70) | 32 | 65.6% | +$0.040 |
| RANGING | HIGH(>70) | 7 | 71.4% | +$0.079 |
| RANGING | LOW(≤70) | 25 | 48.0% | -$0.005 |

**Key findings contradicting the claim:**
1. In BEAR_TREND, high-RSI trades (57.1%) actually **outperform** low-RSI trades (40.0%) — the opposite of "buying pumps in downtrend"
2. Overbought tokens (RSI>70, BB>0.8) in bearish BTC (EMA300=BELOW/AT): **66.7% WR, +$1.27** — these trades are PROFITABLE
3. The system performs worst when BTC is BEAR_TREND and token RSI is LOW (40.0% WR) — meaning it's not the pump buys that fail in downtrends, it's the dip buys

**The "buying pumps in downtrend" narrative is not supported by the data.**

---

## Critical Methodology Issues

### 1. Temporal Bias (SEVERE)
Only 391 out of 2,262 (17.3%) LONG trades have BTC continuum match. The continuum.db covers Sep 4–21 only, excluding all pre-Sep-4 trades. All statistical claims are based on this narrow 18-day window. The pre-Sep-4 period may have very different BTC conditions.

### 2. RSI Source Confusion (MODERATE)
The trades table `entry_rsi_14` and signal_metadata `rsi_14` are often very different:
- CC (15557): entry=74.6 vs signal=32.6
- WLFI (15572): entry=84.6 vs signal=33.3
- CAKE (15585): entry=71.8 vs signal=19.2

This happens because RSI is measured at different times (signal detection vs trade execution). The original analysis doesn't specify which source was used, and the numbers change dramatically.

### 3. Small Sample Sizes (SEVERE for some claims)
| Bucket | N | Significance |
|--------|---|-------------|
| BTC LinReg=BULL | 12 | 🔴 CRITICAL — 95% CI: 13.8%–60.9% |
| RSI 55–59 (metadata) | 28 | ⚠️ Marginal |
| RSI 80+ | 26 | ⚠️ Marginal |
| BTC Score 0–19 | 18 | ⚠️ Marginal |

### 4. "BTC Score" Ambiguity
The analysis uses "BTC Score" without specifying which metric. There are at least two:
- `signal_metadata.btc_score` — computed at signal time
- `continuum_states.state_score` — composite continuum score

These give very different results for the 80+ bucket (57.8% vs 46.7% WR), making the "overextension" claim dependent on which metric is used.

### 5. Confounding: Signal Type
The Sep 20–21 losers are heavily concentrated in `pump-chain+` (8 out of 11 losers). This signal type has only 50.7% WR overall (67 trades). The losses may be a signal quality issue, not a BTC state issue. A proper analysis should control for signal type.

---

## What the Data ACTUALLY Shows

### Real Performance Patterns (N≥30, statistically meaningful):

1. **BTC EMA300=BELOW is actually best for LONGs:** 64.3% WR (N=84) vs ABOVE at 53.1% (N=128). Buying dips works better than buying breakouts.

2. **BTC Score 60–79 is genuinely strong:** 70.0% WR across both score sources (N=40–60).

3. **BB >1.0 is a genuine danger zone:** 43.8% WR (N=48) — this is real and actionable.

4. **CALM phase outperforms:** 62.9% WR (N=140) — consistent finding.

5. **pump_chain signal has 68.3% WR** (N=41) — the original pump signal is strong. The newer `pump-chain+` variant has only 50.7% (N=67) — possibly overfitted.

6. **slow_grind, coiled_spring, trend_purity+, open-skies+ signals underperform** — all below 50% WR with N≥10.

---

## Recommendations

1. **Do NOT implement the recommended filter from Claim 9.** It removes only 2 trades and is not statistically meaningful.

2. **DO implement a BB >0.95 or >1.0 filter.** This is the most robust finding (N=48–98, genuine underperformance).

3. **Investigate pump-chain+ vs pump_chain signal quality.** The newer variant underperforms the original by 18 pp — may need tuning or retirement.

4. **Extend continuum.db coverage** to at least 30 days before making BTC-state-dependent claims. Current 17.3% coverage is insufficient.

5. **Standardize RSI source.** Pick one (recommend entry_rsi_14 for consistency) and use it everywhere.

6. **Separate BTC LinReg=BULL analysis** — with only N=12, the 33.3% WR could easily be noise. Need 3x more data before drawing conclusions.

---

*Report generated from independent analysis. All SQL queries run against live PostgreSQL and SQLite databases. No claims were trusted — every number verified from raw data.*
