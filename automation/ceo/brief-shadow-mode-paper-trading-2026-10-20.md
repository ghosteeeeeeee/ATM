# CEO Brief: T's Directive — Full Shadow-Mode Paper Trading System

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-20 16:30 UTC
**Priority:** CRITICAL — T is defining a fundamental system architecture change

## T's Direct Words

> "What the system should be doing is 'shadow-mode', collecting stats for every single signal fire, and processing it like it was live trade (with TP/SL set according to the exit engine that is supposed to manage it), collecting all the stats it can, and then getting enough data to confirm whether a trade that would have been killed by xyz gate would have been justified. It costs us nothing, no money at stake and more than enough data to answer questions about which signals work, which gates work etc. We get thousands of signals a day, which are pure noise, which are the 'diamonds in the rough'. The system has to get better, at a standstill right now. Yes we can trade a trending market, but the market does not spend most of its time in a trend. We have multiple exit engines, we could even be running virtual A/B tests to see which exit system is best suited for which signal. We should be collecting all regime, volatility, trend etc. data with the 'fake-trade' so we can use the data we collect to fine-tune everything. The system has to start learning from what works and what doesn't!!!"

## What T Is Asking For

A **comprehensive shadow-mode paper trading system** that:

1. **Processes EVERY signal fire** as if it were a live trade
2. **Sets TP/SL** according to the exit engine that would manage it
3. **Collects all context data**: regime, volatility, trend, RSI, MACD, etc.
4. **Runs virtual A/B tests** on exit engines (which exit works best for which signal)
5. **Answers gate questions**: would a trade killed by Gate X have been profitable?
6. **Costs nothing** — no money at stake, pure data collection
7. **Gets enough data** to fine-tune signals, gates, and exits

## Current State

- **850+ signals/day** detected
- **~17 trades/day** actually executed (2% pass rate)
- **98% of signals expire** without any outcome data
- **No counterfactual data**: we don't know if gated signals would have won
- **System is at a standstill**: 34% WR, -$4/7d, guardrail at 50% size

## What Already Exists (Partial)

1. **Shadow logging**: Some gates have shadow logging (ICHIMOKU-LONG-SHADOW, TEMPORAL-CONFLUENCE-SHADOW)
2. **HML shadow**: Position manager logs corrected thresholds
3. **T-simulator**: FAISS vector search for "what would T say" (74 decisions)
4. **Cell stats**: 697 cells (signal×direction×regime), 55 admitted, 12 tradeable
5. **Signal outcomes table**: Exists in signals DB but only tracks executed trades

## What's Missing

1. **No paper trading engine**: Signals that don't execute have NO outcome data
2. **No counterfactual TP/SL simulation**: We don't know if gated signals would have hit TP or SL
3. **No exit engine A/B testing**: We have multiple exit engines but don't compare them on the same signals
4. **No context enrichment**: Paper trades don't capture regime/volatility/trend data
5. **No gate justification analysis**: We can't answer "would this gated trade have won?"

## The Architecture T Is Describing

```
Signal fires → [GATE CHECK] → PASS → Live trade (real money)
                    ↓
                  BLOCKED → Shadow trade (paper, no money)
                    ↓
              [EXIT ENGINE SIMULATION]
                    ↓
              [CONTEXT ENRICHMENT]
                    ↓
              [OUTCOME RECORDED]
                    ↓
              [A/B TEST COMPARISON]
```

## Key Questions for CEO

1. **How to simulate TP/SL?** We need to replay price data after signal fire to determine if TP or SL would have hit first. This requires:
   - Store signal fire time + price + ATR + SL/TP levels
   - Replay 1m candles forward to determine outcome
   - Run this for EVERY signal, not just executed ones

2. **Which exit engines to A/B test?** We have:
   - ATR-based SL/TP
   - Trailing stop (PM Trail)
   - Profit Monster Trail
   - Hard max loss
   - Stale exit
   - RR Engine resistance break
   - Which combination works best for which signal?

3. **How to store the data?** Options:
   - New `shadow_trades` table in PostgreSQL
   - New `signal_outcomes` table in SQLite (already exists, needs expansion)
   - New JSON files for dashboard visualization

4. **How to run the simulation?** Options:
   - Real-time: simulate as signals fire (requires price replay engine)
   - Batch: run simulation every N minutes on recent signals
   - Hybrid: quick simulation at fire time, detailed replay later

5. **How to visualize the results?** Need:
   - Dashboard showing shadow trade outcomes
   - Gate justification analysis (which gates are blocking winners?)
   - Exit engine A/B comparison
   - Signal quality rankings (which signals work in which regimes?)

## What This Enables

1. **Data-driven gate decisions**: "Gate X blocked 100 trades, 45 would have won → loosen Gate X"
2. **Signal quality rankings**: "Signal Y works 70% in EXTREME, 30% in NORMAL → trade only in EXTREME"
3. **Exit engine optimization**: "Trailing stop works best for pump-chain, ATR works best for bb-bounce"
4. **Regime-specific tuning**: "This signal works in trend, fails in chop → gate it in chop"
5. **Continuous improvement**: System learns from what works, not just what it happens to trade

## Cost/Benefit

**Cost:**
- Development time: ~2-4 hours for basic shadow engine
- Storage: ~1000 shadow trades/day × 90 days = ~90K rows (negligible)
- Compute: Price replay for 1000 signals/day (minimal)

**Benefit:**
- 100x more data than current live-only approach
- Answers questions we currently can't answer
- Enables continuous improvement without risking money
- Breaks the "no trades = no data = no improvement" death spiral

## My Assessment

T is absolutely right. The current system is flying blind — we trade 2% of signals and have no idea if the other 98% would have won or lost. A shadow-mode paper trading system is the highest-leverage investment we can make right now.

This is NOT a "silver bullet" — it's the infrastructure that enables us to find the winning combos T has been asking for. Without it, we're guessing. With it, we're learning.

## Protected Flags

13/13 INTACT. No config changed in this brief.
