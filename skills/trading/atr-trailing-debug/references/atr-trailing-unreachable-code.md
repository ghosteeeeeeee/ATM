---
name: atr-trailing-unreachable-code
description: Debug why ATR trailing SL isn't tightening despite peaks being initialized — root cause is unreachable code in refresh_current_prices() where a 'continue' statement skips the entire peak tracking block for positions that HAVE HL data.
tags:
  - hermes
  - atr
  - trailing-sl
  - bug
  - position-manager
  - unreachable-code
created: 2026-04-26
---

# ATR Trailing SL — Unreachable Code Bug in refresh_current_prices

## Symptom
A SHORT position is in profit (price has fallen since entry), but the ATR SL stays at the entry-based level and never tightens. DB shows `lowest_price = entry` (never updated). For ATOM SHORT:
- Entry: 2.0205, current: 2.0184 (price fell = SHORT in profit)
- SL: 2.025229 (should be tightening toward 2.0184)
- `lowest_price` in DB: 2.0205 (never updated from entry)

## Root Cause
In `position_manager.py`, `refresh_current_prices()` has a `continue` at line 2178 that exits the loop body **before** the peak tracking block (lines 2219–2260) is reached — for any position that HAS HL data.

```python
# position_manager.py ~line 2131-2278 (refresh_current_prices)
for pos in positions:
    hl_data = hl_positions.get(token)   # ATOM: has HL data
    if hl_data:
        # ... compute PnL, persist to DB ...
        continue   # ← LINE 2178: EXIT BEFORE PEAK TRACKING BLOCK

    # ── Below is UNREACHABLE for any position with HL data ──
    # ── HL position data available — use authoritative PnL + peak tracking ──
    if hl_size <= 0 or hl_entry <= 0:
        continue
    ...
    existing_high = float(pos.get('highest_price') or 0) or 0  # 0
    existing_low  = float(pos.get('lowest_price')  or 0) or 0  # entry
    new_high = max(existing_high, cur_price)   # SHORT: tracks PEAK
    new_low  = min(existing_low, cur_price)     # SHORT: tracks TROUGH
    pos['highest_price'] = new_high
    pos['lowest_price']  = new_low
    # Persist to DB via db_cur.execute(UPDATE trades SET highest_price=..., lowest_price=...)
```

Because HL data IS available for ATOM, the `continue` at 2178 fires and the peak tracking block is never executed. The `highest_price`/`lowest_price` fields are read from DB but never updated at runtime.

## Investigation Steps
1. Check DB: `SELECT token, highest_price, lowest_price FROM trades WHERE token='ATOM' AND status='open'`
   - If `highest_price=0` and `lowest_price=entry` → peak not updating
2. Check HL API: `python3 -c "from hyperliquid_exchange import get_open_hype_positions; print(get_open_hype_positions())"`
   - If HL has the position with size > 0 → HL data IS available
3. Check pipeline log for `[Position Manager] No HL position data available`:
   - If absent → HL data was found, but unreachable code blocked peak update
4. Check if `_collect_atr_updates` uses `ref=entry` → confirms peak not updating

## The Fix
The `continue` at line 2178 must be removed so the peak tracking block runs for positions with HL data. The `continue` was likely added to skip the legacy fallback path below, but that block is now the primary peak-tracking path.

Alternatively: move the peak tracking logic INTO the `if hl_data:` block so it runs regardless of the continue.

## Verification After Fix
After the fix, as price falls for a SHORT:
```
Entry: 2.0205, current: 2.0184
ATR: 0.0047 (0.23%), k=1.0
_peak_low: 2.0184 (updated from price fall)
new_SL = round(2.0184 × (1 + 0.0023), 8) = 2.02307  ← tightened from 2.0252
```

## Related vs. Existing Skills
- `atr-trailing-sl-peak-initialization`: Covers DB-level peak initialization on trade creation (brain.py, guardian, position_manager runtime fallback)
- `atr-trailing-sl-in-profit`: Covers ATR floor gotcha and SHORT TP ref_price bug
- **This skill**: Covers runtime peak update being unreachable due to early `continue`

All three are needed for complete ATR trailing SL coverage.

## Prevention
When adding peak tracking or any per-cycle update logic inside `refresh_current_prices()`, ensure there is no `continue` between the HL data check and the update block. A `continue` that exits the loop early for the HL-data path will silently disable all downstream updates.
