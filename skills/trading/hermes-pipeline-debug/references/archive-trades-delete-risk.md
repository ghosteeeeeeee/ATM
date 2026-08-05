# archive-trades.py DELETE Risk — 2026-05-08

## What the Script Does

`archive-trades.py --apply`:
1. Fetches ALL `status='closed'` trades from PostgreSQL `brain.trades`
2. Archives them to `/root/.hermes/archive/trades/trades_archive_YYYY-MM-DD.json.gz`
3. **DELETES those trades from PostgreSQL** (lines 502-510)

```python
# Lines 502-510:
ids = [t['id'] for t in closed_trades]
placeholders = ','.join(['%s' for _ in ids])
cur.execute(f"DELETE FROM trades WHERE id IN ({placeholders})", ids)
deleted = cur.rowcount
conn_pg.commit()
```

## The Danger

If `--apply` runs against a populated `trades` table, it WIPES closed trades from PostgreSQL.
The `update-trades-json.py` reads from that same table:
```python
SELECT ... FROM trades WHERE status='open'   # → empty if all open trades deleted
SELECT ... FROM trades WHERE status='closed' # → empty if all closed trades deleted
```

Result: `trades.json` shows 0 open / 0 closed even though Hyperliquid has live positions.

## archive-trades.py Status (2026-05-08)

- Created: May 8 03:16
- **NOT in git** (`git status` shows it as untracked)
- `git diff HEAD` shows NO changes to it
- `update-git.py` in cron reports it as new/untracked every hour

## When archive-trades.py --apply Would Break Monitoring

1. `archive-trades.py --apply` runs (manually or via cron)
2. All `status='closed'` rows deleted from PostgreSQL
3. `update-trades-json.py` reads empty table → `trades.json` shows nothing
4. Guardian orphan logic sees HL positions with no DB record → closes them
5. Positions that were open on HL are now invisible to the monitoring layer

## Fix

Never run `archive-trades.py --apply` without first verifying:
1. The PostgreSQL `trades` table has a backup or the archived JSON files are complete
2. No open positions exist (or they're migrated to a tracking layer that doesn't depend on `trades` table)
3. The guardian orphan logic won't immediately close positions after the DELETE

If archival is needed:
- Use `archive-trades.py --dry-run` first to see what would be deleted
- Consider using `ON CONFLICT DO NOTHING` in the DELETE, or switching to soft-delete
  (mark rows as `status='archived'` instead of actually deleting)