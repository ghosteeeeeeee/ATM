# Guardian / Position Manager Race Condition Fix (2026-06-01)

## Problem

When guardian detects an orphan HL position (token on HL with no DB record), it:
1. Writes closing marker to `guardian-closing-markers.json` 
2. Calls `market_close()` on HL
3. Inserts guardian_orphan paper trade into DB
4. Clears closing marker

But `position_manager.check_atr_tp_sl_hits()` had **no knowledge of this**. It would check ATR hits on the same token in the same cycle and fire a parallel `close_paper_position()` call — both paths trying to close the same trade.

This was a root cause of some sub-10-second `atr_sl_hit` closes: guardian was mid-close, position_manager also closed the token and labeled it `atr_sl_hit`.

## Fix Applied (2026-06-01)

**File:** `position_manager.py` — added `_is_closing_marker_active(token)` guard in `check_atr_tp_sl_hits()`

```python
# Guardian closing marker path (same as hl-sync-guardian.py)
_GUARDIAN_CLOSING_FILE = '/root/.hermes/data/guardian-closing-markers.json'

def _is_closing_marker_active(token: str) -> bool:
    """Check if guardian is currently closing this token — skip ATR check if so."""
    try:
        with FileLock('guardian_closing'):
            with open(_GUARDIAN_CLOSING_FILE) as f:
                data = json.load(f)
        return token.upper() in data.get('tokens', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return False
```

In `check_atr_tp_sl_hits()`, before checking any ATR hit:

```python
# GUARDIAN CLOSING GUARD: if guardian is mid-close on this token,
# skip ATR check — guardian owns the close, don't dual-close
if _is_closing_marker_active(token):
    continue
```

## How It Works

- Guardian writes marker BEFORE `market_close()` — so position_manager sees it immediately
- Uses same `FileLock('guardian_closing')` as guardian to avoid read/write races
- Both processes read the same JSON file at the same path
- Position_manager cycle runs every ~60s via cron — may or may not overlap with guardian cycle

## Issue #1 — Still Open: _load_closing_markers Race (root cause)

The fix above protects position_manager's read, but the race still exists WITHIN hl-sync-guardian.py itself. `hl-sync-guardian.py:395-402`:

```python
def _load_closing_markers() -> dict:
    """Load the current closing markers dict."""
    try:
        with open(_GUARDIAN_CLOSING_FILE) as f:
            data = json.load(f)   # NO LOCK — race here
        return data.get('tokens', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
```

Callers in hl-sync-guardian.py:
- `_save_closing_marker()` line 371 — reads first, then acquires lock only for write
- `_clear_closing_marker()` line 386 — reads first, then acquires lock only for write
- `_is_closing_marker_active()` line 404-406 — no lock at all

If guardian is mid-write (FileLock held, JSON half-flushed), any of these reads gets corrupt JSON. The fix: wrap the read in `_load_closing_markers()` itself with `FileLock('guardian_closing')` — that fixes all callers at once.

## Issue #2 — Still Open: NaN Crash at sync_pnl_from_hype:1476

**Precise crash mechanism (verified 2026-06-01):**

`hl-sync-guardian.py:1476`:
```python
curr_price_hl = float(pos_data.get('currentPrice', prices.get(token, entry)) or prices.get(token, entry) or entry)
```

If HL returns `"NaN"`, `null`, or any non-numeric string for `currentPrice`, `float("NaN")` raises `ValueError` and crashes the entire `sync_pnl_from_hype` function. Lines 1485-1486 (defensive float coercion) are **after** the crash point — they never execute.

**Cascade:** one bad position → entire sync_pnl_from_hype aborts → ALL positions get zero current_price updates → `check_atr_tp_sl_hits()` reads stale prices → false `atr_sl_hit` on ALL tokens in that cycle.

**Fix needed:** Safe float conversion of currentPrice BEFORE the crash point — e.g. a try/except or `math.isnan()` guard on the raw value extracted from `pos_data.get('currentPrice')`.

## Files Changed

- `/root/.hermes/scripts/position_manager.py` — lines 364-408 (added `_is_closing_marker_active()` + guard in `check_atr_tp_sl_hits()`)