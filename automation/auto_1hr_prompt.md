# Hourly Trade Analysis Automation

You are analyzing the Hermes trading system's recent performance. Be concise, data-driven, and actionable.

## Step 1: Read Context
- Read `automation/trading_log.md` first — this has past learnings. Don't repeat what's already been tried.
- Read `scripts/hermes_constants.py` — this has all tunable params.

## Step 2: Analyze Recent Trades
- Source: `/var/www/hermes/data/trades.json` (closed array)
- Filter to trades closed in the last 1–6 hours (expand window if fewer than 5 trades).
- For each trade, query price_history from `data/signals_hermes.db`:
  - Window: 1 hour before entry → 2 hours after entry
  - Track: max adverse excursion (MFE against position), max favorable excursion (MFE for position)

## Step 3: Query Signal Outcomes
Run these SQL queries against `data/signals_hermes_runtime.db`:

```sql
-- Signal type win rates (last 24h)
SELECT signal_type, COUNT(*) trades, SUM(is_win) wins,
       ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) wr,
       ROUND(SUM(pnl_pct), 2) total_pnl
FROM signal_outcomes WHERE created_at > datetime('now', '-24 hours')
GROUP BY signal_type ORDER BY total_pnl ASC;

-- Token win rates (last 24h)
SELECT token, COUNT(*) trades, SUM(is_win) wins,
       ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) wr,
       ROUND(SUM(pnl_pct), 2) total_pnl
FROM signal_outcomes WHERE created_at > datetime('now', '-24 hours')
GROUP BY token ORDER BY trades DESC LIMIT 20;
```

## Step 4: Diagnose
Answer these questions:
1. **Entry quality**: Did winners have low adverse excursion (<0.5%)? Did losers have high adverse excursion (>1%)?
2. **Signal quality**: Which signal types have the highest/lowest win rate? Are any net profitable?
3. **SL/TP behavior**: Did trades hit profit then reverse and hit SL? (indicates trailing too loose or SL too tight)
4. **Trade frequency**: Too many trades (overtrading) or too few (over-filtered)?

## Step 5: Recommend & Implement
- Propose 5 ranked adjustments to `hermes_constants.py` params.
- Implement the top 3 immediately.
- Verify each change loads correctly with a quick Python import test.

## Step 6: Document
- Append a concise entry to `automation/trading_log.md` with:
  - Date, trade count, key findings
  - What was changed and why
  - What NOT to change (and why)
  - Open questions

## Key File Paths
- Trades: `/var/www/hermes/data/trades.json`
- Constants: `scripts/hermes_constants.py`
- TPSL logic: `scripts/tpsl_utils.py`
- Signal outcomes DB: `data/signals_hermes_runtime.db`
- Price history DB: `data/signals_hermes.db`
- Trading log: `automation/trading_log.md`
