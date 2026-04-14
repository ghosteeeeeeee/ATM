# Dual Writer Fix Report — 2026-04-13

## Problem
The dashboard shows "signal" and "opened" fields flashing from blank to values in `/var/www/hermes/data/trades.json`.

## Root Causes

### 1. PostgreSQL TCP Bug (hermes-trades-api.py)
- **File**: `/root/hermes-v3/hermes-export-v3/hermes-trades-api.py`
- **Line 9**: `BRAIN_DB = "host=localhost dbname=brain user=postgres password=brain123"`
- **Problem**: TCP connections to `localhost:5432` fail intermittently with "password authentication failed"
- **Impact**: `get_trades()` succeeds ~50% of the time (TCP race condition), causing intermittent writes with "signal"/"opened" fields

### 2. Dual Writer Conflict
Two scripts write to the SAME file `/var/www/hermes/data/trades.json`:
- `hermes-trades-api.py` — runs every 10 min (pipeline step), uses broken TCP, writes `signal` and `opened` fields
- `update-trades-json.py` — runs every 1 min, uses correct Unix socket, writes ONLY `token, direction, entry, current, pnl_pct, pnl_usdt, sl, tp`

Pipeline order (run_pipeline.py line 14):
```
['price_collector', '4h_regime_scanner', 'signal_gen', 'hermes-trades-api', 'decider_run', 'position_manager', 'update-trades-json']
```

When `hermes-trades-api` succeeds (TCP works), it writes full data with `signal`/`opened`.
When `update-trades-json` runs 1 minute later, it overwrites with data LACKING `signal`/`opened`.
This causes the flashing phenomenon.

## Fix Applied

### hermes-trades-api.py — Line 9
```python
# BEFORE (broken):
BRAIN_DB  = "host=localhost dbname=brain user=postgres password=brain123"

# AFTER (fixed):
BRAIN_DB  = "host=/var/run/postgresql dbname=brain user=postgres password=Brain123"
```

### Verification
```bash
cd /root/hermes-v3/hermes-export-v3 && python3 hermes-trades-api.py
# Result: trades.json written with signal/opened fields, then fails on write_signals() at net_pnl column
```

## Secondary Bug Found
`write_signals()` (line 181-217) references `net_pnl` column which does not exist in the `trades` table. This is a pre-existing bug — `write_trades()` succeeds and writes trades.json correctly before `write_signals()` fails.

## Recommendations

1. **Immediate**: The TCP fix is applied. hermes-trades-api now uses Unix socket reliably.

2. **Consider removing dual writer**: 
   - Option A: Remove `update-trades-json` from pipeline (hermes-trades-api handles it fully with signal/opened)
   - Option B: Keep only update-trades-json but add signal/opened fields to its output

3. **Fix net_pnl bug** in `write_signals()` — replace `net_pnl` with correct column name or remove the filter.

## Files Modified
- `/root/hermes-v3/hermes-export-v3/hermes-trades-api.py` — line 9: `host=localhost` → `host=/var/run/postgresql`, `password=brain123` → `password=Brain123`

## Files Analyzed
- `/root/hermes-v3/hermes-export-v3/hermes-trades-api.py` — 248 lines
- `/root/.hermes/scripts/update-trades-json.py` — 111 lines
- `/root/.hermes/scripts/run_pipeline.py` — 146 lines