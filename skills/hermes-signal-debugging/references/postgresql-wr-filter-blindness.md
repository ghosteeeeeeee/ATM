# archive-trades.py --apply Deletes PostgreSQL WR Data

## The Incident

On 2026-05-11, `archive-trades.py --apply --rebuild-db` was run to archive 361 closed trades and build the analysis SQLite DB.

This deleted 361 rows from `brain.trades` in PostgreSQL — the sole source of truth for win-rate (WR) calculations used by both signal_compactor and decider_run.

## Consequence: WR Filter Became Blind

```
PostgreSQL before --apply: 361 closed trades, 73 unique tokens
PostgreSQL after --apply:  2 closed trades (0G SHORT, CAKE LONG), open positions only

_get_token_wr() queries PostgreSQL:
  → finds 0-2 trades for any token
  → returns (50.0, 0) — passes WR filter (count 0 < 3 threshold)
  → ALL tokens pass, including historically losing ones
```

Tokens like ASTER (47% WR, 15 trades), ETHFI (47% WR, 15 trades), BRETT (46% WR, 13 trades) — all previously blocked by the WR gate — now passed because their trade history was deleted from PostgreSQL.

## Why the Analysis DB Alone Can't Fix It

`/root/.hermes/archive/trades_analysis.db` has all 361 archived trades with correct WR data. But signal_compactor's `_get_token_wr()` queries PostgreSQL, not the analysis DB. The WR filter became a dead letter.

## The Fix (Not Yet Implemented)

Modify `_get_token_wr()` in signal_compactor.py to query the analysis SQLite DB as a fallback when PostgreSQL returns insufficient data:

```python
def _get_token_wr(token, direction):
    # Query PostgreSQL first (has open positions)
    # Fall back to analysis SQLite DB for historical closed trades
```

Alternatively: never delete from PostgreSQL. Archive-only mode preserves PostgreSQL as the system of record.

## Monitoring Command

```bash
# Check PostgreSQL trade counts
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT token, COUNT(*) as cnt, 
          SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
   FROM trades WHERE status='closed' 
   GROUP BY token ORDER BY cnt DESC LIMIT 20;"
```