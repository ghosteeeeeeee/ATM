# Guardian Closing Marker Permanent Block Bug — 2026-05-08

## Symptom
Token (2Z, BLUR, BERA, etc.) permanently blocked in `decider_run` with:
```
SKIP: 2Z — guardian closing in progress (race guard)
```
HL shows NO open position, but `guardian-closing-markers.json` still has the token entry with `trade_id: null`.

## Root Cause Chain

1. Guardian detects orphan HL position (HL has position, no DB record)
2. `_save_closing_marker(coin)` writes marker to `guardian-closing-markers.json` — `trade_id=None`
3. `close_position_hl(coin)` **SUCCEEDS** — HL position is gone
4. Guardian sleeps 6s → polls HL fills via `_close_orphan_paper_trade_by_id()`
5. Fill polling fails (HL fills not yet in `user_fills_by_time`, or no DB record found) → returns `False`
6. Line 3637: `"Orphan close incomplete for {coin} — keeping closing marker active"` — marker NOT cleared
7. Next guardian cycle: token not in `hl_pos` → not in `missing` → guardian does nothing
8. Marker stays forever → `_is_guardian_closing()` always `True` → token never executes

## The Core Bug

Marker cleanup is **coupled to fill-polling success**, but HL close has already confirmed the position is gone.

```
close_position_hl(coin)  →  SUCCEEDS (HL position gone)
        ↓
_fill_polling_ returns False (no fill data yet or no DB record)
        ↓
if close_ok: _clear_closing_marker(coin)  ← NEVER runs
        ↓
Marker stays forever
```

Fill data is for recording the **exit price in the DB**, not for the marker state.

## The Orphan Creation Block Makes It Worse

Lines 3638-3678 create a guardian_orphan record with `trade_id = lev * 1000000`, then call `_close_orphan_paper_trade_by_id(orphan_id)` where `orphan_id` is the auto-increment DB id.

The function queries `WHERE id = %s` — finds the record — but fill polling fails → returns `False` → marker stays.

This block **bypasses the ORPHAN GUARD** at line 1145 (which already `continue`s cleanly). It's dead code that creates phantom records.

## The Fix

When `close_position_hl()` returns `True` → **always** call `_clear_closing_marker()` immediately, BEFORE fill polling:

```python
# CORRECT — marker cleared immediately after HL confirms close
success = close_position_hl(coin, 'guardian_orphan')
if success:
    _clear_closing_marker(coin)  # ALWAYS clear — HL confirmed close
    time.sleep(6)  # Wait for fills to propagate
    # Then do fill polling for DB record — marker already clear
    _close_orphan_paper_trade_by_id(...)
```

## Emergency Unblock

Manually remove token from closing markers:

```python
import json
path = '/root/.hermes/data/guardian-closing-markers.json'
with open(path) as f: data = json.load(f)
for token in ['2Z', 'BLUR', 'BERA', 'ENS', 'OG']:
    data['tokens'].pop(token, None)
with open(path, 'w') as f: json.dump(data, f, indent=2)
print('Cleared stale markers')
```

## Detection

- `trade_id: null` in `guardian-closing-markers.json` = marker created but orphan INSERT/fill polling failed
- All 48 stale markers from May 6-8 have `trade_id: null`
- Pipeline log shows `SKIP: {token} — guardian closing in progress (race guard)` for tokens that have no HL position

## Files Involved

- `hl-sync-guardian.py` lines 3600-3680 — orphan close path with conditional marker cleanup
- `hl-sync-guardian.py` lines 367-401 — `_save_closing_marker`, `_clear_closing_marker`, `_load_closing_markers`
- `decider_run.py` lines 120-136 — `_is_guardian_closing()` reads marker file, blocks execution
- `decider_run.py` lines 1591-1596 — execution gate that calls `_is_guardian_closing()`