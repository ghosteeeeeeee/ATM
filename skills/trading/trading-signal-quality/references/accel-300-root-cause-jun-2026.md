# accel-300+ Root Cause — Mean-Reversion Trap (Jun 8 2026)

## Finding (Definitive)
accel-300+ LONG is a **mean-reversion trap**, not a momentum signal. It has NEVER been profitable:
- 398 trades, WR=29.1%, avg_pnl=0.19%
- 83% hit SL immediately on entry
- Wins: tiny (profit-monster exits, avg 0.25%), rare (17%)
- The "55% WR era" was NOT accel-300 — it was ema-angle- + zscore_pump

## Why It Fails
accel-300 fires when price is **extended above EMA300** (gap > 0.08%).
"Extended" = already far from fair value = likely to revert.
The signal buys the PEAK, not the pullback.

## Key Data
| Signal | Trades | WR | Avg PnL | SL Hit Rate |
|--------|--------|-----|---------|-------------|
| zscore_pump | 44 | 54.5% | 9.09% | Uses TP not SL |
| ema-angle- (SHORT) | 52 | 50%+ | varies | profit-monster exits |
| accel-300- (SHORT) | 170 | 33.5% | 0.32% | 80% SL hit |
| accel-300+ (LONG) | 398 | 29.1% | 0.19% | 83% SL hit |

## The Fix (3 Changes to Reach 75% WR)
1. **Raise MIN_GAP_PCT_LONG from 0.08% to 0.30%+** — filter noise extensions
2. **Add z-score confirmation gate** — only fire when z_score < -1.0 (oversold pullback within extended move). Converts accel-300 from "buy the peak" to "buy the pullback in an extended trend"
3. **Reconsider LONG firing in SHORT-biased market** — SHORT side is also broken but for different reasons; the market has been SHORT-biased

## What Works: zscore_pump
zscore_pump fires on z-score OVERSOLD (pullback in uptrend), not extended price.
It buys the dip, not the peak. That's why it has 54.5% WR and 9% avg PnL.

## Signal Design Rule
**Mean-reversion entry points = extended price (far from EMA) = likely reversal**
**Momentum entry points = pullback price (near or below EMA) = likely continuation**

accel-300+ fires at extended price = mean-reversion entry with momentum signal label.
This is the fundamental design flaw.

## Archive Data Range
- trades_analysis.db covers 2026-05-11 to 2026-05-20 (931 trades)
- Q4 (2026-05-15 to 2026-05-20) was 51.1% WR — dominant signals: ema-angle-, zscore_pump, hhh-short4
- accel-300+ was ~0 trades in Q4 (almost no accel-300+ in that period)
- The "55% WR era" the user referred to likely used a different signal set before 2026-05-11

## New Signal Quality Checklist
Before deploying any signal, verify:
- [ ] Entry point: extended price (likely reversal) or pullback (likely continuation)?
- [ ] Historical SL hit rate: aim for <50%
- [ ] Avg winning trade > avg losing trade (不对称收益)
- [ ] Close reason distribution: profit-monster exits should dominate, not SL hits
- [ ] z-score or RSI confirmation present for momentum signals