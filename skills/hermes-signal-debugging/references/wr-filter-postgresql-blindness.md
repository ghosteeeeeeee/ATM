# WR Filter — PostgreSQL vs Archive SQLite

## The Problem

`_get_token_wr()` in signal_compactor.py queries PostgreSQL `brain.trades` for win/loss data.

After `archive-trades.py --apply --rebuild-db` runs, PostgreSQL has 0-2 closed trades per token → returns `(50.0, 0)` for every token.

## Why (50.0, 0) Always Passes

```python
wr, wr_count = _get_token_wr(token, direction)
# wr=50.0, wr_count=0

gate = (wr < 50 and wr_count >= 3)  # (False and False) = False
```

- `wr < 50` → False (50.0 is not less than 50)
- `wr_count >= 3` → False (0 < 3)
- Combined: False → filter does NOT block

**Every token with 0-2 trades in PostgreSQL passes the WR gate, including historically losing tokens like ASTER (47% WR, 15 trades) and ETHFI (47% WR, 15 trades).**

## Key Insight: (50.0, 0) Is Not a Neutral Score

The fallback `return (50.0, 0)` looks like 50% WR with 0 trades. But with `wr_count=0 < 3`, the gate never fires. This means the WR filter becomes a dead letter when PostgreSQL is emptied.

## The Fix

`_get_token_wr()` needs to query archive SQLite as a fallback:

```python
# /root/.hermes/archive/trades_analysis.db — has all 361 archived trades
# Table: trades (token, direction, pnl, entry_time, etc.)
```

## Monitoring Commands

```bash
# Check PostgreSQL trade counts per token
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT token, COUNT(*) as cnt, 
          SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
   FROM trades WHERE status='closed' 
   GROUP BY token ORDER BY cnt DESC LIMIT 20;"

# Check archive DB
sqlite3 /root/.hermes/archive/trades_analysis.db \
  "SELECT token, COUNT(*) as cnt, 
          SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
   FROM trades GROUP BY token ORDER BY cnt DESC LIMIT 20;"
```

## User Request: Regime Filtering on decider_run

T wants decider_run to filter hot-set tokens based on regime from linear regression of last 100 bars on 1min prices.

This is a separate feature from the WR fix — regime would be a new signal quality layer applied in decider_run.py before live trade entry.