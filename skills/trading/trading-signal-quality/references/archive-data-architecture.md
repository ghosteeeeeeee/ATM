# Archival & Data Architecture

*Consolidated from `archive-trade-signal-join` skill (archived 2026-05-22).*

## The Atomic Capture Problem

Trades and signals were archived independently with no join key. When analyzing which signals fired for which winners, ~54% of trades had no signal data:
- Signals → `signals_YYYY-MM.jsonl.gz`
- Trades → `trades_archive_*.json`
- Post-hoc time matching only worked when signals happened to be captured

Additionally, `brain.py:add_trade()` stored only `signal` (combo_key) and `confidence` — none of the actual indicator values.

## PostgreSQL Signal Columns (Atomic Capture at Entry)

New trades capture full signal context via 13 new columns in `brain.trades`:

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

`decider_run.py` passes hotset signal values at the `execute_trade()` call site.

## Preferred: JSONB Catch-All Instead of Per-Signal Columns

Per-signal columns are deprecated. The d31692f INSERT bug (42 expressions for 41 columns) silently broke ALL live trading for a full day.

New signals should use JSONB catch-all columns:
```sql
ALTER TABLE trades ADD COLUMN _signal_metadata JSONB;
ALTER TABLE trades ADD COLUMN _exp_metadata    JSONB;
```

See `new-signal-implementation` skill, section 7 for full architecture.

## PostgreSQL Connection
- Host: `/var/run/postgresql` (Unix socket)
- DB: `brain`, User: `postgres`

## Archive Locations
- Trades JSON: `/root/.hermes/archive/trades/trades_archive_YYYY-MM-DD.json.gz`
- Signals JSON: `/root/.hermes/archive/signals/signals_YYYY-MM.jsonl.gz`
- Analysis SQLite: `/root/.hermes/archive/trades_analysis.db`

## archive-trades.py Modes

| Flag | Action |
|------|--------|
| `--dry-run --limit N` | Preview N trades, no file/DB touch |
| `--apply` | Archive closed → gzip JSONL + append to SQLite |
| `--rebuild-db` | Wipe trades_analysis.db, rebuild from all JSON archives |

**CRITICAL: No DELETE from PostgreSQL.** `--apply` is append-only (safe to run on live system).

## archive-trades.py has NO systemd timer

Runs manually via `--apply` but NOT on any systemd timer. This causes `trades_analysis.db` to go stale.

**Fix:** Run `python3 archive-trades.py --apply` manually or add a systemd timer.

## Key Bug History (archive-trades.py)

| Bug | Symptom | Fix |
|-----|---------|-----|
| `direction` missing from `SQLITE_TRADE_COLS` | 195 trades with `direction=NULL` | Recovered from gzip JSON archives |
| `hl_notional_usdt` missing from 3 locations | Column dropped, no HL notional data | Added to ADD_COLUMNS, CREATE TABLE, SQLITE_TRADE_COLS |
| `db_is_new` guard blocked signal append | Signals stopped appending on incremental runs | `INSERT OR IGNORE` |
| Boolean not SQLite INTEGER compatible | `True`/`False` rejected | `_int_safe()` conversion |
| JSONB `dict` not serialized | `str(dict)` produces Python repr | `json.dumps(dict)` via `_json_safe()` |

## WR Data Lives in PostgreSQL

`_get_token_wr()` in signal_compactor queries PostgreSQL (`brain.trades`, 7-day window).
`archive-trades.py --apply` does NOT delete from PostgreSQL, so WR data stays available.

## Verify INSERT Column Balance After Any `add_trade()` Change

`brain.py`'s `add_trade()` INSERT had a 42 expressions for 41 columns mismatch that silently broke all live trading. `NOW()` in SQL counts as 1 expression, not a placeholder.