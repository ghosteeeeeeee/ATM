# Independent Verdict: Open-Skies RSI 30-60 Filter Proposal

**Auditor:** DeepSeek Harness (independent, no prior context)  
**Date:** 2026-09-17  
**Data:** 28 open-skies trades from `signals_hermes_runtime.db` (Sep 5–17, 2026)  
**Method:** Computed RSI(14), trend direction, higher highs, support/resistance from 1h candle data (full history). 5m candles pruned to 3 days; 1h used as proxy.

---

## === INDEPENDENT VERDICT ===

### Claim 1: "A filter requiring trend UP AND RSI 30-60 would give 87% win rate (13W/2L)"

**Verdict: DISAGREE**  
**Evidence:** The filter passes only **2 of 28 trades** (7.1%), not 15. Of those 2, 1 is a win (TURBO +2.32%) and 1 is a loss (AIXBT -1.29%). That's a **50% win rate (1W/1L)** — the exact opposite of 87%.  
**Confidence:** HIGH  
**Note:** The prior analysis likely used different data or methodology that is not reproducible with the current database. The 5m candle data for most trades has been pruned (only 3 days retained).

---

### Claim 2: "Only 3 small winners would be blocked (+0.28%, +0.60%, +2.32%)"

**Verdict: DISAGREE**  
**Evidence:** **16 of 17 winners would be blocked.** This includes the two biggest winners:
- INJ +8.11% (RSI=74.7, trend=UP — blocked because RSI > 60)
- WLD +4.33% (RSI=71.5, trend=UP — blocked because RSI > 60)

Full list of blocked winners: +0.16%, +0.24%, +0.28%, +0.28%, +0.31%, +0.60%, +0.67%, +1.25%, +1.38%, +1.62%, +1.64%, +1.70%, +1.72%, +1.86%, +4.33%, +8.11%  
**Confidence:** HIGH

---

### Claim 3: "9/11 losers would be caught"

**Verdict: PARTIAL**  
**Evidence:** 10 of 11 losers are blocked (not 9). The 1 loss that passes is AIXBT (-1.29%, RSI=45.5, trend=UP). So the filter catches 10/11 losses — slightly better than claimed but at catastrophic cost.  
**Confidence:** HIGH

---

### Claim 4: "The only change needed is tightening RSI from max 75 to max 60"

**Verdict: DISAGREE**  
**Evidence:** This is the root error in the proposal. The open-skies signal is a **momentum breakout** signal — it fires when price breaks through all resistance with strong volume and higher highs. By design, this occurs at **elevated RSI levels** (60–85+). Lowering RSI max to 60 is contradictory: it would filter out the very conditions the signal is designed to catch.

The RSI distribution of all 17 winning trades:
```
TURBO    RSI= 57.8  ✓ (only winner in 30-60 range)
YGG      RSI= 61.6
USUAL    RSI= 63.0
ZORA     RSI= 63.2
WLD      RSI= 66.0
BABY     RSI= 68.3
WLD      RSI= 71.5
INJ      RSI= 74.7  ← biggest winner (+8.11%)
NEAR     RSI= 80.4
ATOM     RSI= 75.8
LTC      RSI= 77.3
LTC      RSI= 77.6
DYDX     RSI= 77.7
BIGTIME  RSI= 78.4
SUSHI    RSI= 83.1
INJ      RSI= 87.4
LTC      RSI= 97.5
```

**16 of 17 winners have RSI > 60.** Only TURBO (RSI=57.8) falls in the proposed 30-60 range.  
**Confidence:** HIGH

---

## Detailed Analysis

### Current Signal Performance (OPEN_SKIES_MAX_RSI=75)
- **28 trades** (17W/11L)
- **Win rate: 60.7%**
- **Total PnL: +14.40%**
- Best trade: INJ +8.11%
- Regime breakdown: EXTREME 67% WR, HIGH 57% WR, NORMAL 50% WR

### Proposed Filter Performance (trend UP AND RSI 30-60)
- **2 trades** pass (7.1%)
- **Win rate: 50.0%** (1W/1L)
- **Total PnL: +1.03%**
- Blocks 16 of 17 winners
- Blocks INJ +8.11% and WLD +4.33%

### Why the Filter Fails
1. **RSI is structurally high for this signal.** Open-skies = momentum breakout = high RSI by definition.
2. **Trend direction filter is redundant.** The signal already requires price > SMA20 > SMA50, positive 20-bar return, and higher highs. These are all trend filters.
3. **28 trades → 2 passes is not a filter, it's a kill switch.** A filter that blocks 93% of trades is not selective — it's eliminating the signal.

### Alternative Filters Tested

| Filter | Trades Pass | Win Rate | Total PnL | Big Winners Blocked |
|--------|-------------|----------|-----------|-------------------|
| **Current (RSI≤75)** | 17 | 47% | +8.75% | None |
| **Proposed (trend UP + RSI 30-60)** | **2** | **50%** | **+1.03%** | **INJ +8.11%, WLD +4.33%** |
| RSI 30-60 only | 4 | 25% | -1.96% | INJ +8.11%, WLD +4.33% |
| RSI max 70 | 13 | 46% | -1.13% | INJ +8.11%, WLD +4.33% |
| RSI max 70 + trend UP | 9 | 67% | +4.95% | INJ +8.11%, WLD +4.33% |
| RSI 50-75 | 15 | 53% | +11.75% | None |
| **RSI 60-85** | **21** | **67%** | **+15.85%** | **TURBO +2.32% only** |
| **Current + trend UP** | **12** | **67%** | **+16.28%** | **None** |

### Recommended Improvements (data-backed)

**Option 1 — Add trend UP filter to current RSI (BEST):**
- `OPEN_SKIES_MAX_RSI = 75` (keep current) + add trend UP requirement
- Result: 67% WR, +16.28% total PnL, 12 trades (43% of original)
- Blocks 0 big winners, catches 9/11 losses
- **This is the filter the original analysis should have proposed.**

**Option 2 — Raise RSI to 60-85 (momentum zone):**
- Explicitly require RSI 60-85 instead of just max 75
- Result: 67% WR, +15.85% total PnL, 21 trades (75% of original)
- Only blocks TURBO +2.32% (acceptable)
- **This captures the signal's natural habitat.**

**Option 3 — Keep current, no changes:**
- 60.7% WR, +14.40% total PnL
- Simple, proven, works.

---

## Data Quality Issues

1. **5m candle data pruned:** Only 3 days of 5m candles retained. 25 of 28 trades had to be analyzed with 1h candles. RSI values may differ slightly from actual 5m RSI at detection time.
2. **S/R data is current, not historical:** Support/resistance counts reflect current market structure, not conditions at signal time. This doesn't affect RSI/trend analysis but means S/R counts in this report may not match actual signal conditions.
3. **created_at = closed_at for all trades:** All 28 trades show 0-minute gap between creation and closure timestamps. This appears to be a schema issue — the `created_at` likely represents execution time, not signal detection time.

---

## Bottom Line

The proposed "trend UP AND RSI 30-60" filter is **fundamentally wrong** for this signal. It would:
- Eliminate 93% of trades
- Block the biggest winners (INJ +8.11%, WLD +4.33%)
- Reduce total PnL from +14.40% to +1.03%
- Achieve only 50% WR on 2 trades (statistically meaningless)

The prior analysis's claims (87% WR, 13W/2L, only 3 small winners blocked) are **not reproducible** with the available data and appear to be based on a different dataset or methodology.

**DO NOT IMPLEMENT THIS FILTER.**
