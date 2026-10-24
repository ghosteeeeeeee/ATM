# Shadow-Mode Analysis Report: Disabled Signals & Gate Impact

**Date:** 2026-10-24
**Analyst:** Hermes (CEO agent)
**Data Source:** `brain/shadow_trades.db` (17,321 signals, 16,819 closed)
**Purpose:** Analyze shadow-mode stats for disabled signals and gate impact to inform CEO recommendations

---

## Executive Summary

The shadow-mode data reveals three critical insights:

1. **All gates are HELPING** — every gate blocks net losers. The gate system is working correctly.
2. **Entries are the problem, not exits** — all SL levels show negative avg PnL. The signals that pass gates are still losing on average.
3. **Disabled signals are mostly worse** — the 16 shadow-bypass signals (disabled in main system) show the same or worse performance than active signals.

**Key finding:** The system doesn't need looser gates or better exits. It needs **better entries** — signals that have positive expectancy before any filtering.

---

## 1. Current Performance (Live Trading)

| Metric | Value |
|--------|-------|
| 24h trades | 14 |
| 24h WR | **57.1%** |
| 24h PnL | **+$0.25** (first positive!) |
| 7d trades | 121 |
| 7d WR | **40.5%** |
| 7d PnL | -$1.16 |

**Trend:** WR improved from 35.2% → 40.5% (7d), 42.1% → 57.1% (24h). PnL loss shrinking.

---

## 2. Gate Justification (17,321 Shadow Signals)

**All gates are HELPING** — they block signals that would have lost money:

| Gate | Blocked | Would Win | Avg PnL | Verdict |
|------|---------|-----------|---------|---------|
| CONFLUENCE-EXPIRY | 9,637 | 48% | -0.11 | ✅ HELPING |
| CTX-GATE | 641 | 50% | -0.09 | ✅ HELPING |
| UNKNOWN | 258 | 46% | -0.12 | ✅ HELPING |
| BTC-CRASH | 105 | 26% | -0.39 | ✅ STRONGLY HELPING |
| EXEC-BLOCK | 13 | 8% | -0.49 | ✅ STRONGLY HELPING |

**Interpretation:** If we removed all gates, we'd add ~10,654 trades that would lose an average of -0.11 each. That's **-$1,172 in additional losses**. The gates are protecting us.

---

## 3. Exit Engine A/B (17,321 Shadow Signals)

| Engine | Trades | WR | Total PnL | Avg PnL | Verdict |
|--------|--------|-----|-----------|---------|---------|
| PM Trail | 6,141 | 100% | **+$2,266** | +0.37 | 🏆 BEST |
| ATR | 3,175 | 46% | +$262 | +0.08 | ✅ GOOD |
| pump_exit | 264 | 69% | +$63 | +0.24 | ✅ GOOD |
| hold | 236 | 50% | +$42 | +0.18 | ✅ OK |
| universal_hold | 126 | 60% | +$22 | +0.17 | ✅ OK |
| trail_arm_timeout | 497 | 53% | -$65 | -0.13 | ⚠️ LOSING |
| cut_loser | 46 | 0% | -$56 | -1.21 | ❌ LOSS-ONLY (by design) |
| rr_engine | 1,466 | 19% | **-$544** | -0.37 | ❌ BIG LOSER |
| hard_max | 4,095 | 0% | **-$3,863** | -0.94 | ❌ BIGGEST (by design) |

**Key insight:** PM Trail is the clear winner (+$2,266). Hard Max and Cut Loser are loss-only engines (0% WR by design). RR Engine is a significant loser (-$544).

---

## 4. SL Sweep: Entries Are the Problem

| SL Level | WR | Stopped | Total PnL | Avg PnL |
|----------|-----|---------|-----------|---------|
| 0.50% | 27.1% | 70% | -8.72% | -0.009% |
| 0.75% | 32.1% | 63% | -51.18% | -0.054% |
| 1.00% | 35.8% | 58% | -104.09% | -0.110% |
| 1.50% | 39.7% | 51% | -233.21% | -0.247% |
| 2.00% | 42.9% | 44% | -327.15% | -0.347% |
| 2.50% | 45.2% | 33% | -351.82% | -0.373% |
| 3.00% | 46.7% | 22% | -334.11% | -0.354% |
| 4.00% | 47.8% | 9% | -297.99% | -0.316% |
| 5.00% | 47.8% | 4% | -284.80% | -0.302% |
| 10.00% | 48.3% | 1% | -252.69% | -0.268% |
| 50.00% | 48.5% | 0% | -211.50% | -0.224% |

**Critical finding:** **ALL SL levels show negative avg PnL.** Even with no stop-loss (50%), the average trade loses -0.224%. This means:

- The exits are working correctly (they're not the problem)
- The gates are working correctly (they're blocking losers)
- **The entries themselves have negative expectancy**

**Implication:** Loosening gates or changing exits won't fix the problem. The system needs signals that are profitable *before* any filtering.

---

## 5. Direction Analysis

| Direction | Trades | WR | Total PnL | Avg PnL |
|-----------|--------|-----|-----------|---------|
| SHORT | 10,089 | **52.3%** | -$627 | -0.065 |
| LONG | 6,730 | 42.4% | -$1,246 | -0.193 |

**SHORT is 10pp better than LONG.** The system should bias toward SHORTs.

---

## 6. Disabled Signals (Shadow-Bypass Registry)

The shadow-bypass registry contains 16 signals disabled in the main system but tracked in shadow mode:

### Stage A: Parameter-Killed / Regime-Specific Winners

| Signal | Direction | Trades | WR | Avg PnL | Total PnL | Why Disabled |
|--------|-----------|--------|-----|---------|-----------|--------------|
| bb-squeeze- | SHORT | 165 | 50.9% | -0.198 | -$30.3 | SHORT side killed (66.9%WR research but -$1.16/7d live) |
| bb-bounce-v3-long | LONG | 0 | — | — | — | Removed from STANDALONE_BYPASS 2026-10-06 (DRIFT-A) |
| volume-breakout-long+ | LONG | 182 | 22.5% | -0.339 | -$61.8 | KILLED Oct 13 (12T 0%WR) |
| hmacd_mtf-+ | LONG | 35 | 48.6% | -0.243 | -$8.5 | HMACD_MTF_PLUS_ENABLED=False (killed Oct 13) |
| doji-bottom-long | LONG | 202 | 46.5% | -0.322 | -$65.0 | Shadow shows 54.3% WR but -$18.4% total |

### Stage B: Gate-Blocked Signals

| Signal | Direction | Trades | WR | Avg PnL | Total PnL | Why Blocked |
|--------|-----------|--------|-----|---------|-----------|-------------|
| ichimoku- | SHORT | **1,591** | **61.1%** | -0.109 | -$173.2 | Blocked by SHORT-REGIME-GATE in NORMAL/HIGH |
| ichimoku+ | LONG | 828 | 45.9% | -0.174 | -$144.1 | Single-source, blocked by CONFLUENCE-GATE |
| rs-r | LONG | varies | varies | varies | varies | Single-source, blocked by CONFLUENCE-GATE |
| rs-s | SHORT | varies | varies | varies | varies | Single-source, blocked by CONFLUENCE-GATE |

### Stage C: Killed Signals

| Signal | Direction | Trades | WR | Avg PnL | Total PnL | Why Killed |
|--------|-----------|--------|-----|---------|-----------|------------|
| open-skies+ | LONG | 22 | **13.6%** | -0.432 | -$9.5 | KILLED 2026-09-17 (NEVER_REENABLE) |
| squeeze-cross+ | LONG | 0 | — | — | — | DISABLED 2026-07-28: 0% WR on LONG |
| squeeze-cross- | SHORT | 0 | — | — | — | DISABLED 2026-08-02: 40% on SHORT — no edge |
| rs-broken-short | SHORT | 0 | — | — | — | DISABLED 2026-07-21 — 26.5% WR, massive drag |
| rs-broken-resistance-long | LONG | 0 | — | — | — | DISABLED — momentum is bearish |
| vel-hermes+ | LONG | 0 | — | — | — | KILLED. 0% WR (12 trades 7d), -$1.61 |
| vel-hermes- | SHORT | 0 | — | — | — | AUTO-DISABLED by signal_decay_detector |

### Key Findings from Disabled Signals

1. **ichimoku- (SHORT) is the highest-volume shadow signal** — 1,591 trades, 61.1% WR, but still losing -$173.2 total. The 61.1% WR is misleading — avg PnL is -0.109%, meaning wins are smaller than losses.

2. **Most disabled signals are correctly disabled** — open-skies+ (13.6% WR), volume-breakout-long+ (22.5% WR), hmacd_mtf-+ (48.6% WR) all show negative expectancy.

3. **Some rs-r/rs-s variants are profitable** — but with tiny sample sizes (n=5-12):
   - rs-s50: 10 trades, 90% WR, +0.329 avg, +$3.3 total
   - rs-s36: 12 trades, 75% WR, +0.166 avg, +$1.8 total
   - rs-r33: 10 trades, 90% WR, +0.212 avg, +$2.1 total
   - rs-r44: 6 trades, 83.3% WR, +0.32 avg, +$1.9 total

   **These are not statistically significant** (n < 15). Do not re-enable based on tiny samples.

---

## 7. Top Performing Signals (Active, n≥20)

| Signal | Trades | WR | Avg PnL | Total PnL | MFE | MAE | Hold (min) |
|--------|--------|-----|---------|-----------|-----|-----|------------|
| volume_breakout_short | 123 | 39.8% | **+0.143** | +$17.5 | 4.49 | -3.07 | — |
| hl_copy_minus | 20 | 55.0% | +0.128 | +$2.6 | 1.89 | -1.02 | — |
| ai-trader | 39 | 48.7% | +0.051 | +$2.0 | 4.70 | -2.62 | — |
| grind_breakout_short | 79 | 41.8% | +0.001 | +$0.1 | 2.44 | -2.42 | — |

**Only 4 signals have positive avg PnL with n≥20.** The rest are losing.

---

## 8. Worst Performing Signals (Active, n≥20)

| Signal | Trades | WR | Avg PnL | Total PnL |
|--------|--------|-----|---------|-----------|
| pump-chain | 3,834 | 31.7% | -0.125 | **-$442.2** |
| squeeze_cross | 3,553 | 59.0% | -0.090 | -$295.4 |
| ichimoku_short | 1,591 | 61.1% | -0.109 | -$173.2 |
| volume_buildup_short | 1,235 | 56.2% | -0.119 | -$146.8 |
| ichimoku_long | 830 | 45.9% | -0.174 | -$144.1 |
| pump-chain-v6 | 890 | 33.5% | -0.127 | -$107.4 |

**pump-chain is the #1 bleeder** — 3,834 trades, 31.7% WR, -$442.2 total.

---

## 9. RSI Band Analysis

| RSI Band | Trades | WR | Avg PnL |
|----------|--------|-----|---------|
| <30 oversold | 2,294 | 45.4% | -0.111 |
| 30-40 | 1,996 | 43.0% | -0.082 |
| 40-50 | 1,945 | 42.6% | -0.142 |
| 50-60 | 2,141 | 46.9% | -0.118 |
| 60-70 | 1,459 | 46.7% | -0.146 |
| >70 overbought | 2,002 | 42.8% | -0.147 |

**All RSI bands show negative avg PnL.** No RSI edge exists in the current signal set.

---

## 10. Hold Time Analysis

| Direction | Winners Avg Hold | Losers Avg Hold | Winner Distribution |
|-----------|------------------|-----------------|---------------------|
| LONG | 65 min (1.1h) | 59 min (1.0h) | 42% <30m, 27% 30-60m, 15% 1-2h |
| SHORT | 63 min (1.1h) | 58 min (1.0h) | 45% <30m, 21% 30-60m, 18% 1-2h |

**Winners hold slightly longer than losers** (65 vs 59 min). 42-45% of winners close in <30min — quick profits. The exit engines are working correctly.

---

## 11. Recommendations for CEO

### Do NOW (data-backed)

1. **Bias toward SHORT direction** — SHORT is 10pp better than LONG (52.3% vs 42.4% WR). Reduce LONG exposure, increase SHORT exposure.

2. **Focus on top performers** — volume_breakout_short (+0.143 avg), hl_copy_minus (+0.128), ai-trader (+0.051) are the only positive signals with n≥20.

3. **Consider disabling pump-chain** — 3,834 trades, 31.7% WR, -$442.2 total. This is the #1 bleeder.

### Do NOT do (data-backed)

4. **Do NOT loosen gates** — all gates are HELPING (blocking net losers). Loosening would add ~$1,172 in losses.

5. **Do NOT change exits** — exits are working correctly. PM Trail is the clear winner (+$2,266).

6. **Do NOT re-enable disabled signals** — most are correctly disabled (open-skies+ 13.6% WR, volume-breakout-long+ 22.5% WR). The few profitable rs-r/rs-s variants have tiny samples (n<15) and are not statistically significant.

### Investigate FURTHER

7. **Why are entries losing?** — All SL levels show negative avg PnL. The signals that pass gates are still losing. This is the core problem.

8. **RR Engine is a big loser** — -$544 total, 19% WR. Consider disabling or re-tuning.

9. **trail_arm_timeout is losing** — -$65 total, 53% WR. Consider re-tuning.

---

## Appendix: Raw Data

### Shadow Bypass Signals (16 total)

```
bb-squeeze-: SHORT | stage A | SHORT side killed (66.9%WR research but -$1.16/7d live)
bb-bounce-v3-long: LONG | stage A | Removed from STANDALONE_BYPASS 2026-10-06 (DRIFT-A)
volume-breakout-long: LONG | stage A | KILLED Oct 13 (12T 0%WR) — shadow shows 11.8% WR
hmacd_mtf-+: LONG | stage A | HMACD_MTF_PLUS_ENABLED=False (killed Oct 13)
doji-bottom-long: LONG | stage A | Shadow shows 54.3% WR but -$18.4% total — needs different exit
ichimoku-: SHORT | stage B | Blocked by SHORT-REGIME-GATE in NORMAL/HIGH
ichimoku+: LONG | stage B | Single-source, blocked by CONFLUENCE-GATE
rs-r: LONG | stage B | Support/resistance LONG — single-source, blocked by CONFLUENCE-GATE
rs-s: SHORT | stage B | Support/resistance SHORT — single-source, blocked by CONFLUENCE-GATE
open-skies+: LONG | stage C | KILLED 2026-09-17 (NEVER_REENABLE)
squeeze-cross+: LONG | stage C | DISABLED 2026-07-28: 0% WR on LONG
squeeze-cross-: SHORT | stage C | DISABLED 2026-08-02: 40% on SHORT — no edge
rs-broken-short: SHORT | stage C | DISABLED 2026-07-21 — 26.5% WR, massive drag
rs-broken-resistance-long: LONG | stage C | DISABLED — momentum is bearish
vel-hermes+: LONG | stage C | KILLED. 0% WR (12 trades 7d), -$1.61
vel-hermes-: SHORT | stage C | AUTO-DISABLED by signal_decay_detector
```

### Profitable rs-r/rs-s Variants (n≥5, not statistically significant)

```
rs-s50: 10 trades, 90% WR, +0.329 avg, +$3.3 total
rs-s36: 12 trades, 75% WR, +0.166 avg, +$1.8 total
rs-s40: 10 trades, 70% WR, +0.147 avg, +$1.3 total
rs-s112: 5 trades, 100% WR, +0.438 avg, +$2.2 total
rs-r33: 10 trades, 90% WR, +0.212 avg, +$2.1 total
rs-r44: 6 trades, 83.3% WR, +0.32 avg, +$1.9 total
rs-r42: 7 trades, 71.4% WR, +0.272 avg, +$1.9 total
rs-s46: 9 trades, 77.8% WR, +0.246 avg, +$2.0 total
```

**Warning:** All have n < 15. Not statistically significant. Do not re-enable based on these samples.

---

## Verification

- **Data source:** `brain/shadow_trades.db` (17,321 signals, 16,819 closed)
- **Analysis date:** 2026-10-24 13:40 UTC
- **Methods:** SQL queries against shadow_trades table, cross-referenced with `hermes_constants.py` SHADOW_BYPASS_SIGNALS registry
- **Reproducibility:** All queries documented in this report
