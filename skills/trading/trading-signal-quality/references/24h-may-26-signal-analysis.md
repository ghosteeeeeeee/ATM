# 24h Signal Analysis — May 26, 2026

## Database Connections

- PostgreSQL `brain`: `psql -h /var/run/postgresql -U postgres -d brain`
- SQLite runtime: `/root/.hermes/data/signals_hermes_runtime.db`
- Connection: `psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')`

## Query Templates

### PostgreSQL — Last 24h closed trades
```sql
SELECT token, direction, entry_price, exit_price, pnl_pct, pnl_usdt,
       close_reason, signal, open_time, close_time, confidence, leverage
FROM trades
WHERE close_time >= NOW() - INTERVAL '24 hours' AND status = 'closed' AND close_time IS NOT NULL
ORDER BY close_time DESC;
```

### PostgreSQL — Duration analysis
```sql
SELECT token, pnl_pct, open_time, close_time, close_reason,
       ROUND(EXTRACT(EPOCH FROM (close_time - open_time))/60, 1) as dur_min
FROM trades
WHERE close_time >= NOW() - INTERVAL '24 hours' AND status = 'closed'
ORDER BY pnl_pct DESC;
```

### SQLite — Runtime signals (last 24h)
```sql
SELECT token, direction, source, z_score, confidence, created_at
FROM signals
WHERE created_at >= datetime('now', '-24 hours')
ORDER BY created_at DESC;
```

### SQLite — Signal outcomes with PnL
```sql
SELECT token, direction, signal_type, is_win, pnl_pct, confidence
FROM signal_outcomes
WHERE closed_at >= datetime('now', '-24 hours')
ORDER BY pnl_pct DESC;
```

## Key Findings — May 26 24h Snapshot

| Metric | Value |
|--------|-------|
| Total trades | 36 |
| Winners | 16 (44%) |
| Losers | 20 (56%) |
| Net P&L | -$0.03 (essentially flat) |
| Win rate by close reason | profit-monster: 16W/0L; atr_sl_hit: 0W/19L |

## RS Level Number — Best Discriminator Found

RS levels are numbered in age order (1=oldest, higher=newer).

| RS Level Bucket | Trades | Win Rate |
|---|---|---|
| <100 (oldest) | 6 | **83%** |
| 100-300 | 10 | **70%** |
| 300-600 | 8 | 38% |
| 600-1000 | 3 | **0%** |
| 1000-2000 | 5 | **0%** |
| >2000 | 4 | 25% |

Winners avg RS level: **417** | Losers avg RS level: **1218**

Extract RS level from signal string:
```python
import re
m = re.search(r'rs-[sr](\d+)', 'rs-s95,zscore-pump+')  # returns 95
```

## Time-of-Day — 7-Day Pattern

```
GOOD:    02:00 UTC (90%), 06:00 UTC (67%), 10:00 UTC (67%), 14:00 UTC (68%)
AVOID:   15:00-16:00 UTC (25-28%), 11:00 UTC (0%), 00:00 UTC (25%)
NEUTRAL: All other hours (36-52%)
```

US afternoon (13:00-18:00 UTC) is consistently choppy. 24h specifically showed 0W/9L in 13:00-18:00 window.

## What DID NOT Predict Winners

1. **Confidence** — losers avg 91.1, winners avg 87-90. Completely inverted.
2. **Confluence count** — all 36 trades had 2+ signals, no pattern.
3. **Z-score magnitude** — winners had z range -3.71 to +4.97, losers -4.61 to +4.97. Identical.
4. **Direction** — SHORTS: 8W/11L (42%), LONGS: 8W/9L (47%). Almost even.

## Constants Change Proposals

### High Priority (RS Level Filter) — blocks 0% WR RS levels
```python
# hermes_constants.py additions:
RS_MAX_LEVEL_FOR_WEAK_MOMENTUM = 1000   # block RS levels >1000 when |z| < 3.5
RS_DECIDER_MIN_TOUCHES         = 500     # was 300 — minimum 500 touches for valid level
```

### Medium Priority (Session Filter) — blocks US afternoon chop
No constant change possible — needs time-of-day gate in signal_compactor or decider_run:
```python
hour_utc = datetime.utcnow().hour
if hour_utc in (15, 16):
    return None  # block new entries during US afternoon
```

### Low Priority (zscore threshold for SHORT)
```python
ZSCORE_PUMP_THRESHOLD = 3.5  # was 3.0 — SHORT already fires at |z| >= 3.5 (60% WR vs 40% at 3.0)
```