# HL Fill Filter `side=='B'` Bug — 2026-06-10 Fix

## Summary
Four locations used `side=='B'` to detect close fills, silently dropping ALL LONG close fills.
HL fill schema: `side='A'` = LONG closes, `side='B'` = SHORT closes.

## The Four Affected Locations

### 1. hl-sync-guardian.py:881 `_poll_close_fills_once`
```python
# WRONG
fills = [f for f in fills_raw if f.get('side') == 'B']
# RIGHT
fills = [f for f in fills_raw if 'Close' in str(f.get('dir', ''))]
```

### 2. hl-sync-guardian.py:509 (phantom backfill)
```python
# WRONG
close_fills = [f for f in fills if f.get('side') == 'B']
# RIGHT
close_fills = [f for f in fills if 'Close' in str(f.get('dir', ''))]
```

### 3. backfill_hl_pnl.py:52+119
```python
# WRONG
fills = [f for f in fills if f.get('side') == 'B']
# RIGHT
fills = [f for f in fills if 'Close' in str(f.get('dir', ''))]
```

### 4. backfill_orphan_hl_prices.py:71-72
```python
# WRONG
fills = [f for f in fills if f.get('side') == 'B']
# RIGHT
fills = [f for f in fills if 'Close' in str(f.get('dir', ''))]
```

## Why `side=='B'` Is Wrong

HL fill response schema:
```json
{"sz": "0.16", "px": "63.57", "side": "B", "dir": "Close Short"}
{"sz": "0.16", "px": "63.532", "side": "A", "dir": "Open Short"}
```

- LONG close fills: `side='A'`, `dir='Close Long'`
- SHORT close fills: `side='B'`, `dir='Close Short'`

Using `side=='B'` as a close-fill filter only captures SHORT closes. All LONG closes are silently dropped.

## Same Bug Fixed Previously

The same bug was fixed in `_close_paper_trade_db` (line ~2523) on 2026-04-19, but the other four locations were missed.

## Impact on 2026-06-11

These missing fills caused 2 AAVE + 2 AVNT trades to not be recorded in PostgreSQL `trades` table.

## Verification Query
```sql
-- Check if hyperliquid_trades has any data (it should be populated by the mirroring path)
SELECT COUNT(*) FROM hyperliquid_trades;  -- currently 0 rows — hyperliquid_trades is a DEAD PATH

-- Actual mirroring happens through guardian orphan-close writes to PostgreSQL 'trades' table
-- The guardian log at /root/.hermes/logs/sync-guardian.log is the authoritative record
```