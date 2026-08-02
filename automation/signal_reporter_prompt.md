# Signal Performance Reporter

You are analyzing signal performance for the Hermes trading system. Run every 6 hours.

## Step 1: Query Signal Outcomes (last 6h and 24h)

```sql
-- Signal type performance (last 6h)
SELECT signal_type, direction, COUNT(*) trades, SUM(is_win) wins,
       ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) wr,
       ROUND(SUM(pnl_pct), 2) total_pnl,
       ROUND(AVG(pnl_pct), 3) avg_pnl
FROM signal_outcomes 
WHERE created_at > datetime('now', '-6 hours')
GROUP BY signal_type, direction 
HAVING COUNT(*) >= 2
ORDER BY total_pnl DESC;

-- Signal type performance (last 24h)
SELECT signal_type, direction, COUNT(*) trades, SUM(is_win) wins,
       ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) wr,
       ROUND(SUM(pnl_pct), 2) total_pnl,
       ROUND(AVG(pnl_pct), 3) avg_pnl
FROM signal_outcomes 
WHERE created_at > datetime('now', '-24 hours')
GROUP BY signal_type, direction 
HAVING COUNT(*) >= 3
ORDER BY total_pnl DESC;
```

Run against: `data/signals_hermes_runtime.db`

## Step 2: Identify Winners and Losers

### Losers (candidates for disabling)
Flag signals that meet ALL of these criteria:
- WR < 30% (over 5+ trades)
- Total PnL < -2%
- Active for > 24h (not just bad luck)

### Winners (candidates for boosting)
Flag signals that meet ALL of these criteria:
- WR > 55% (over 5+ trades)
- Total PnL > 0
- Consistent across timeframes

### Marginal (watch list)
- WR 30-50% with small sample size
- Mixed results across directions

## Step 3: Check Signal Enabled Status

```python
from hermes_constants import (
    TL_BREAK_ENABLED, BOLLINGER_SQUEEZE_ENABLED,
    ACCEL_300_ENABLED, INVERSE_ACCEL_300_ENABLED,
    # ... etc
)
```

Compare performance against enabled/disabled status.

## Step 4: Recommendations

For each signal, recommend:
- **KEEP** — performing well, leave enabled
- **DISABLE** — performing poorly, should be disabled
- **WATCH** — needs more data before decision
- **TUNE** — params need adjustment (not signal itself)

## Step 5: Report Format

```
=== Signal Performance Report ===
Period: Last 6h | 24h

WINNERS (WR > 55%, PnL > 0):
| Signal | Dir | 6h WR | 6h PnL | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|--------|---------|--------|

LOSERS (WR < 30%, PnL < -2%):
| Signal | Dir | 6h WR | 6h PnL | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|--------|---------|--------|

MARGINAL (30-50% WR):
| Signal | Dir | 6h WR | 6h PnL | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|--------|---------|--------|

DISABLED BUT GOOD:
| Signal | Dir | Last WR | Last PnL | Recommendation |
|--------|-----|---------|----------|----------------|

RECOMMENDATIONS:
1. [ACTION] Signal X — reason
2. [ACTION] Signal Y — reason
```

## Step 6: Check for Signal Inversions

```sql
-- Check for direction mismatches (signal_type says LONG but direction is SHORT)
SELECT token, signal_type, direction, is_win, pnl_pct, created_at
FROM signal_outcomes 
WHERE created_at > datetime('now', '-24 hours')
AND (
    (signal_type LIKE '%long%' AND direction = 'SHORT')
    OR (signal_type LIKE '%short%' AND direction = 'LONG')
)
ORDER BY created_at DESC LIMIT 20;
```

If inversions found, flag as critical issue.

## Key File Paths
- Signal outcomes: `data/signals_hermes_runtime.db`
- Constants: `scripts/hermes_constants.py`
- Trading log: `automation/trading_log.md`
- Health report: append findings to `automation/signal_report.md`
