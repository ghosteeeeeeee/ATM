# Pump-Chain+ Exit Analysis — 2026-09-21

## Problem Statement

pump-chain+ trades are being stopped out too early, then the price recovers after we're out.

## Missed Opportunities (Last 13 Trades)

| Token | Exit | Peak After | Missed | What Happened |
|-------|------|------------|--------|---------------|
| ALGO | -1.4% | +6.0% | **+7.4%** 🚨 | Stopped out, then pumped |
| HEMI | -1.4% | +3.9% | **+5.3%** 🚨 | Stopped out, then pumped |
| CAKE | -1.6% | +1.0% | **+2.6%** ⚠️ | Stopped out, then recovered |
| NOT | -1.8% | +0.2% | **+2.0%** | Stopped out, barely recovered |
| FIL (volume-breakout) | +4.4% | +4.2% | -0.2% | ✅ Good exit — caught the move |

## pump-chain+ Performance (Last 30 Days)

| Metric | Value |
|--------|-------|
| Total trades | 69 |
| Wins | 32 (46.4%) |
| Avg PnL | +$0.04 |
| Avg PnL % | +1.55% |

### Exit Reasons
| Exit | Trades | WR | Avg PnL |
|------|--------|-----|---------|
| atr_sl_hit | 57 | 45.6% | +$0.03 |
| profit-monster-trail | 5 | 80.0% | +$0.08 |
| rr_engine | 5 | 40.0% | +$0.10 |

## Analysis

### Why Ride-It Wouldn't Fix pump-chain+

1. **46.4% WR** — more than half the entries are bad
2. **Wider SL = bigger losses on bad entries** — currently losing -1.4% to -1.6%, would lose -2.5% to -3.5% with ride_it
3. **The problem is ENTRY QUALITY, not exit management** — bad entries get stopped out because they're bad, not because the SL is too tight

### Why Ride-It Works for volume-breakout

1. **Better signal quality** — volume-breakout fires fewer but higher-conviction trades
2. **Delayed spikes** — the signal predicts moves that happen hours later
3. **Wide SL survives the wait** — ride_it's 2x ATR SL survives the pre-spike dip

### The Tradeoff

| Approach | Good Entries | Bad Entries |
|----------|-------------|-------------|
| Current (tight SL) | Stopped out early, miss recovery | Small loss, cut fast |
| Ride-It (wide SL) | Survive dip, catch recovery | Bigger loss, hold longer |

## Recommendation

1. **Keep pump-chain+ on pump_exit** — don't switch to ride_it
2. **Keep volume-breakout on ride_it** — already done
3. **Improve pump-chain+ entry filters** — the problem is bad entries, not exits

### Entry Filter Ideas for pump-chain+

- **BTC trend alignment** — only LONG when BTC is bullish (already have directional bias)
- **Volume confirmation** — require volume spike at entry
- **RSI filter** — don't enter when RSI > 70 (overbought)
- **Time-of-day filter** — avoid entries during low-liquidity hours
- **Regime filter** — only enter in HIGH/EXTREME (where pump-chain+ has better WR)

## Files

- Ride-It exit spec: `/root/.hermes/plans/ride-it-exit-spec.md`
- Ride-It exit module: `/root/.hermes/scripts/ride_it_exit.py`
- Bug hunter reports: `/root/.hermes/brain/verdicts/ride-it-exit-bug-hunter*.md`
