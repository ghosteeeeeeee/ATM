# Winning DNA Report — What Makes Great Trades

**Date:** 2026-10-08
**Data:** Top 100 winning trades by PnL% + 81 losers in same period (Oct 1-8)
**Analysis DB:** `/root/.hermes/data/winning_trades_analysis.db`

## ⚠️ CRITICAL METHODOLOGY WARNING

**This report initially contained survivorship bias** — analyzing only winners without comparing to losers. That analysis produced misleading conclusions (e.g., "pump-chain+ is the best signal" when it actually loses 80% of the time). The corrected analysis below compares winners vs losers to identify what's truly predictive.

**Lesson:** You can't identify "winning DNA" by only looking at winners. Every signal has winners AND losers — the question is what makes the winners different from the losers of the SAME signal.

## Key Findings (Corrected: Winner vs Loser Comparison)

### 1. Signal Win Rates (What Actually Matters)

| Signal | Winners | Losers | Win Rate | Assessment |
|--------|---------|--------|----------|------------|
| volume-breakout-long+ | 4 | 8 | **33.3%** | Best, but small sample |
| hl_copy_trader | 16 | 41 | 28.1% | Consistent, high volume |
| open_skies | 2 | 7 | 22.2% | Small sample |
| pump-chain+ | 14 | 53 | **20.9%** | ⚠️ Loses 80% of time |
| ct_hot | 8 | 44 | 15.4% | ⚠️ Loses 85% of time |
| pullback-entry- | 10 | 57 | 14.9% | ⚠️ Loses 85% of time |

**Reality check:** pump-chain+ produces big winners (+18.9% avg) but loses 4 out of 5 trades. It's not a "winning signal" — it's a high-variance signal that occasionally catches monster moves.

### 2. Volatility Regime: EXTREME is Slightly Better, But Still Losing

| Regime | Winners | Losers | Win Rate |
|--------|---------|--------|----------|
| FLAT | 1 | 3 | 25.0% |
| **EXTREME** | **48** | **337** | **12.5%** |
| NORMAL | 29 | 264 | 9.9% |
| HIGH | 22 | 293 | 7.0% |

**EXTREME has the best win rate (12.5%)** but still loses 87.5% of the time. It's not "king" — it's just less bad than HIGH (7.0%).

### 3. RSI: The Overbought Myth Debunked

| RSI Bucket | Total | Winners | Losers | Win Rate |
|------------|-------|---------|--------|----------|
| **> 85** | 25 | 5 | 20 | **20.0%** |
| **50-70** | 106 | 18 | 88 | **17.0%** |
| 30-50 | 118 | 11 | 107 | 9.3% |
| < 30 | 701 | 61 | 640 | 8.7% |
| **70-85** | 58 | 5 | 53 | **8.6%** |

**Initial claim was wrong.** RSI >85 has 20% win rate (best), but RSI 70-85 has 8.6% (worst). There's no linear "overbought is good" relationship. The sweet spot is RSI 50-85 (moderately overbought), not extreme overbought.

### 4. Direction: LONG Has Edge

| Direction | Winners | Losers | Win Rate |
|-----------|---------|--------|----------|
| **LONG** | 70 | 552 | **11.3%** |
| SHORT | 30 | 356 | 7.8% |

LONG trades win 45% more often than SHORT. This aligns with the philosophy: "Every pump is a LONG opportunity."

### 5. BTC Phase: Data Quality Issue Found

**CRITICAL FINDING**: `market_phase` is missing from 97-100% of trades in the last 14 days. Only `btc_score` is reliably written to metadata.

| Date | Trades | Has market_phase | Has btc_score |
|------|--------|------------------|---------------|
| Oct 7 | 13 | 0 (0%) | 13 (100%) |
| Oct 6 | 12 | 0 (0%) | 12 (100%) |
| Oct 5 | 32 | 1 (3%) | 32 (100%) |

**This is a bug in the metadata writer.** The BTC phase analysis in the initial report was based on pre-computed data in `winning_trades_analysis.db`, which cannot be validated against raw PostgreSQL metadata.

**Cannot draw conclusions about BTC phase or EMA300 position until metadata writer is fixed.**

## What The Winners Look Like (Survivorship Bias Warning)

The top 100 winners by PnL% share these characteristics, BUT these conditions also produce many losers:

| Characteristic | Winner Profile | But Also... |
|---------------|----------------|-------------|
| Signal | pump-chain+ (14%) | 53 losers with same signal |
| Volatility | EXTREME (48%) | 337 losers in EXTREME |
| RSI | >85 (5% of winners) | 20 losers with RSI >85 |
| Leverage | 5x (83%) | 620 losers with 5x |
| Exit | atr_sl_hit (74%) | This is just the default SL |

**Key insight:** The winners don't have a secret formula. They're just the 11% of trades that happened to work out. The "DNA" is mostly noise, not signal.

## Recommendations

Based on the corrected analysis:

1. **Don't chase "winning DNA"** — the winners don't have a reliable formula. Focus on improving overall win rates, not replicating outlier winners.

2. **LONG bias is justified** — 11.3% win rate vs 7.8% for SHORT. Align with the philosophy: "Every pump is a LONG opportunity."

3. **RSI 50-85 sweet spot** — moderately overbought entries have the best win rate (17-20%). Consider a range filter, not a ceiling.

4. **EXTREME volatility is OK** — 12.5% win rate vs 7-10% for other regimes. Don't filter it out, but don't expect miracles.

5. **pump-chain+ is high-variance** — big winners but 80% loss rate. Use small position sizes to survive the droughts between winners.

6. **Fix BTC phase metadata extraction** — currently missing from comparison table. Need this data before drawing BTC structure conclusions.

## What Not To Do

- ❌ Don't build a "Winning DNA" signal based only on winner characteristics
- ❌ Don't raise RSI ceiling to 95+ expecting overbought entries to always win
- ❌ Don't assume EXTREME volatility = guaranteed winners
- ❌ Don't copy winner parameters without checking their actual win rates

## Data Quality Issues

### 1. Survivorship Bias (Fixed)
Initial analysis only looked at winners, not losers. Corrected by comparing winners vs losers in same time period.

### 2. Missing BTC Metadata (Unresolved)
- `market_phase` missing from 97-100% of trades in PostgreSQL
- Only `btc_score` is reliably written
- BTC phase data in `winning_trades_analysis.db` cannot be validated
- **Cannot trust BTC phase conclusions until this is fixed**

### 3. Small Sample Sizes
- RSI > 85: only 5 winners
- volume-breakout-long+: only 4 winners
- open_skies: only 2 winners
- Many "patterns" may be statistical noise

### 4. Time Period Limitation
Analysis covers Oct 1-8, 2026 (7 days). Too short to be statistically significant.

## Bottom Line

**The "Winning DNA" is mostly survivorship bias.** The top 100 winners don't share a reliable formula — they're just the ~11% of trades that happened to work out. The corrected analysis shows:

- No signal has >35% win rate
- EXTREME volatility is slightly better, but still loses 87.5% of the time
- RSI 50-85 is the sweet spot, not extreme overbought
- LONG has a real edge (11.3% vs 7.8% WR)

**Recommendation:** Don't build a signal based on winner characteristics. Instead, improve overall win rates by understanding what makes ALL trades fail, not what makes the few winners succeed.
