# Archive Data Architecture Reference

*Originally from `archive-trade-signal-join` skill. Preserved here after consolidation into `hermes-hot-set`.*

## Key Properties

- **No DELETE from PostgreSQL** — `--apply` archives to gzip JSONL and appends to SQLite only. PostgreSQL is never modified. Safe to run on live system.
- **Idempotent** — `INSERT OR IGNORE` skips duplicates. JSON per-file deduplication. Re-running produces zero new rows.
- **Append-only SQLite** — existing rows never modified or deleted. Schema migrates forward via `ALTER TABLE`.

## Modes

| Flag | Action |
|------|--------|
| `--dry-run --limit N` | Preview N trades, no file/DB touch |
| `--apply` | Archive closed → gzip JSONL + append to SQLite |
| `--rebuild-db` | Wipe trades_analysis.db, rebuild from all JSON archives |

## Archive Format

**New (2026-05-12+):** gzip JSONL — one JSON object per line
```
trades_archive_2026-05-12.json.gz
{"id":9452,"token":"TON","direction":"SHORT","pnl_usdt":0.13,...}
{"id":9451,"token":"ME","direction":"SHORT","pnl_usdt":0.03,...}
```

**Old (pre-2026-05-12):** dict-wrapped `{"archived_at","source","count","columns","trades":[...]}` — `analyze_archive_trades.py` reads this format only.

## Idempotency Implementation

```python
# JSON: per-file in-memory dedup
written_ids: set[int] = set()
for rec in records:
    if rec['id'] in written_ids:
        continue
    written_ids.add(rec['id'])
    f.write(json.dumps(rec) + '\n')

# SQLite: INSERT OR IGNORE (primary key = id)
cur.execute('INSERT OR IGNORE INTO trades VALUES (' + ','.join(['?']*N) + ')', vals)
# OR IGNORE silently skips rows where id already exists
```

## Schema Migration

On each run, diffs `PRAGMA table_info(trades)` against full 98-col list and runs `ALTER TABLE trades ADD COLUMN colname` for each missing column. Handles existing DBs with old 62-col schema without data loss.

## Key Bugs Fixed (2026-05-12)

| Bug | Symptom | Fix |
|-----|---------|-----|
| `direction` missing from `SQLITE_TRADE_COLS` | 195 trades inserted with `direction=NULL` | Recovered from gzip JSON archives |
| Missing `trailing_activated`, `test_*_variant` cols | Schema mismatch on existing DB | Added to migration block |
| Boolean not SQLite INTEGER compatible | `True`/`False` rejected by INTEGER columns | `_int_safe()` conversion |
| JSONB `dict` not serialized | `str(dict)` produces Python repr | `json.dumps(dict)` via `_json_safe()` |

## Data Sources

| Store | Location | Purpose | Modified by `--apply`? |
|-------|----------|---------|------------------------|
| PostgreSQL `brain.trades` | Live DB | System of record, open positions, WR data | NO |
| gzip JSONL | `/root/.hermes/archive/trades/trades_archive_YYYY-MM-DD.json.gz` | Immutable archive | Append-only |
| SQLite | `/root/.hermes/archive/trades_analysis.db` | Analysis queries | Append-only |

## SQL to Add Signal Columns to PostgreSQL

```sql
ALTER TABLE trades ADD COLUMN signal_z_score REAL;
ALTER TABLE trades ADD COLUMN signal_rsi_14 REAL;
ALTER TABLE trades ADD COLUMN signal_macd_hist REAL;
ALTER TABLE trades ADD COLUMN signal_macd_value REAL;
ALTER TABLE trades ADD COLUMN signal_macd_signal REAL;
ALTER TABLE trades ADD COLUMN signal_momentum_state TEXT;
ALTER TABLE trades ADD COLUMN signal_z_score_tier TEXT;
ALTER TABLE trades ADD COLUMN signal_decision TEXT;
ALTER TABLE trades ADD COLUMN signal_leverage INTEGER;
ALTER TABLE trades ADD COLUMN signal_created_at TIMESTAMPTZ;
ALTER TABLE trades ADD COLUMN test_sl_variant TEXT;
ALTER TABLE trades ADD COLUMN test_timing_variant TEXT;
ALTER TABLE trades ADD COLUMN test_trailing_variant TEXT;
```