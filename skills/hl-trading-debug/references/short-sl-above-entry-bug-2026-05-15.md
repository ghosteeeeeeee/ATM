# SHORT SL Above Entry Bug — 2026-05-15 (recurring)

## Same Bug as FIL (2026-05-14), Three Open Positions

Three open SHORT positions show identical pattern (DB query 07:00 UTC):

| Token | Direction | Entry | SL | SL% from entry | lowest_price |
|-------|-----------|-------|-----|----------------|--------------|
| TAO | SHORT | 302.750 | 303.365 | +0.20% above | 301.256 (tracked) |
| 2Z | SHORT | 0.100350 | 0.101052 | +0.70% above | 0 (NOT tracked) |
| ZK | SHORT | 0.017633 | 0.017756 | +0.70% above | 0 (NOT tracked) |

**All three SHORT SLs are ABOVE entry.** For a SHORT, SL must be BELOW entry (price falls = profit). Above entry = loss direction.

## Root Cause

`position_manager._collect_atr_updates()` lines 1653-1654:
```python
if is_new_trade or _in_profit:
    new_sl = round(_entry * (1 + effective_sl_pct), 8)  # SL ABOVE entry
```
When `lowest_price=0` (not yet tracked) AND trade is in profit, ref_price falls back to `_entry`, so `new_sl = _entry × (1 + k·ATR%)` → SL above entry for SHORT.

Line 1601 fallback for SHORT when `_peak_low = 0`:
```python
ref_price = _peak_low if _peak_low > 0 else (current_price if (current_price and float(current_price) > 0) else _entry)
```
When `current_price` is also None/0 (at cycle start), falls back to `_entry` → SL above entry.

## Key Diagnostic

```python
# Check if lowest_price is 0 for any open SHORTs (the bug trigger)
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='')
cur = conn.cursor()
cur.execute("SELECT token, direction, entry_price, stop_loss, lowest_price FROM trades WHERE status='open' AND direction='SHORT' AND CAST(lowest_price AS FLOAT)=0")
for r in cur.fetchall(): print(r)
conn.close()
# If rows returned → bug is active for those tokens
```

## Fix

Line 1601 — when `lowest_price=0` for SHORT, use `current_price` as ref_price (not `_entry`):
```python
ref_price = _peak_low if _peak_low > 0 else (current_price if (current_price and float(current_price) > 0) else _entry)
```
This places SL below current price for profitable SHORTs with no price history yet.

Also lines 1653-1654: for new/profit SHORTs with `lowest_price=0`, use `current_price` as anchor for `new_sl`:
```python
if is_new_trade or _in_profit:
    # Use current_price not _entry so SL starts BELOW current price (correct for SHORT)
    new_sl = round(current_price * (1 + effective_sl_pct), 8)
```

## Related

- Same pattern as FIL SHORT (2026-05-14) — `references/fil-short-initial-sl-bug-2026-05-15.md`
- HL TP/SL orders on Hyperliquid: `position_manager._execute_atr_bulk_updates()` calls `place_bulk_orders()` — source of ZK's HL SL order identified during 2026-05-15 session