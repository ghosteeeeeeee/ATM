# RSI Signal Backtest Skill

## Purpose
Compare signal quality with and without RSI components using PostgreSQL brain database.

## Usage
```bash
python3 /root/.hermes/scripts/rsi_backtest.py
```

## What It Does
1. Loads all closed Hermes trades with signals from PostgreSQL
2. Classifies signals by RSI content
3. Computes win rate, avg PnL, total PnL, expectancy, Sharpe-like for each group
4. Compares key combos: `hzscore,pct-hermes,vel-hermes` vs `hzscore,pct-hermes,rsi-hermes`
5. Breaks down by direction (LONG/SHORT) and by close reason

## Key Metrics
- **WR (Win Rate):** % of trades with pnl_pct > 0
- **Avg:** mean pnl_pct across all trades in the group
- **Total:** sum of pnl_pct (proxy for $)
- **Expectancy:** win_rate * avg_win - loss_rate * abs(avg_loss)
- **Sharpe:** expectancy / std_dev (higher = better risk-adjusted)

## Current Results (2026-04-14, 794 trades)
```
Signal                                  N     WR       Avg    Total
hzscore,pct-hermes,vel-hermes (NO RSI)  167  58.1%  +0.099%  +$16.58
hzscore,pct-hermes,rsi-hermes (RSI)      52  44.2%  -0.092%   -$4.77

HAS RSI (any):    62 trades  WR=38.7%  Avg=-0.105%  Total=-$6.50
NO RSI (signal): 732 trades  WR=50.1%  Avg=+0.021%  Total=+$15.69
```

## Conclusion
RSI degrades signal quality in every combo. Adding RSI to any hzscore+pct combo drops win rate and avg PnL.

## Files
- Script: `/root/.hermes/scripts/rsi_backtest.py`
- Data: PostgreSQL `brain` database, `trades` table

## Database Query
```sql
SELECT token, direction, signal, pnl_pct, close_reason, leverage,
       entry_price, stop_loss, entry_timing
FROM trades
WHERE server = 'Hermes' AND status = 'closed'
  AND signal IS NOT NULL AND signal != ''
  AND pnl_pct IS NOT NULL
```
