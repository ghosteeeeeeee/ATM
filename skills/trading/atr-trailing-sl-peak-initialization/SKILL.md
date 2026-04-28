---
name: atr-trailing-sl-peak-initialization
description: "Debug why ATR trailing SL tightens on losing positions instead of widening — root cause is highest_price/lowest_price peak fields not initialized on trade creation. Three-part fix across brain.py, hl-sync-guardian.py, position_manager.py."
tags:
  - hermes
  - atr
  - trailing-sl
  - bug
  - peak-tracking
  - position-manager
created: 2026-04-25
---

# ATR Trailing SL Peak Initialization Bug

## Symptom
BCH (or any token) open position showing ATR SL moving LOWER as price moves AGAINST the position. For a SHORT from 455.01: SL drops from ~454.5 → 454.37 → 454.15 as price falls from 455.01 → 454.37. This is backwards — a losing SHORT should have a widening (lower) SL, not a tightening one.

## Root Cause
`highest_price` and `lowest_price` fields (peak tracking for trailing SL) were NOT being initialized when trades are created via `add_trade()` in `brain.py`. Only `entry` was set:

- LONG: `highest_price = 0`, `lowest_price = 0` on creation
- SHORT: `highest_price = 0`, `lowest_price = 0` on creation

The trailing SL in `position_manager.py` uses a `max(highest_price, current_price)` pattern:
```python
if direction == "SHORT":
    peak = max(existing_high, current_price)  # Tracks the HIGHEST price
```

When `existing_high = 0` and price immediately drops from entry (e.g., 455.01 → 454.37):
```python
peak = max(0, 454.37)  # peak becomes 454.37 — the losing price, NOT the entry
```

Then on every subsequent tick the peak stays at that losing price, and the SL formula (`peak - k_tp * atr`) gets progressively tighter as price falls against you.

## Three-Part Fix

### Fix 1 — `brain.py` `add_trade()` (INSERT, line ~393-402)
Seed peaks from entry on trade creation:
```python
if direction == "LONG":
    highest_price = hl_entry
    lowest_price = 0.0
elif direction == "SHORT":
    highest_price = 0.0
    lowest_price = hl_entry
cursor.execute("""
    INSERT INTO positions ...
    (coin, direction, entry, ..., highest_price, lowest_price, ...)
    VALUES (?, ?, ..., ?, ?, ...)
""", (coin, direction, hl_entry, ..., highest_price, lowest_price, ...))
```

### Fix 2 — `hl-sync-guardian.py` (line ~1015-1021)
When guardian syncs entry/direction for existing trades, also seed peaks:
```python
if existing_high <= 0 and direction == "SHORT":
    cursor.execute("UPDATE positions SET lowest_price = ? WHERE id = ?",
                   (entry_px, trade_id))
if existing_low <= 0 and direction == "LONG":
    cursor.execute("UPDATE positions SET highest_price = ? WHERE id = ?",
                   (entry_px, trade_id))
```

### Fix 3 — `position_manager.py` ATR trailing loop (line ~2229-2237)
Runtime safety net — if peak is still 0 when ATR loop runs, initialize from entry:
```python
if direction == "SHORT":
    if existing_high <= 0:
        existing_high = entry  # Safety: anchor to entry if never set
    peak = existing_high
    ...
elif direction == "LONG":
    if existing_low <= 0:
        existing_low = entry
    peak = existing_low
    ...
```

## Verification
```sql
SELECT coin, direction, entry, highest_price, lowest_price
FROM positions WHERE status = 'open' AND coin = 'BCH';
```
- SHORT: `highest_price = 0`, `lowest_price = 455.01` (entry)
- LONG: `highest_price = 455.01`, `lowest_price = 0`

## Files Involved
- `/root/.hermes/scripts/brain.py` — `add_trade()` INSERT
- `/root/.hermes/scripts/hl-sync-guardian.py` — guardian sync path
- `/root/.hermes/scripts/position_manager.py` — ATR trailing loop

## Prevention
Any time a new peak-tracking field is added to the positions schema, it MUST be initialized in all three places: `add_trade()`, guardian sync, and the runtime fallback.

## Follow-On Bug C — LONG highest_price never updated (ASYMMETRY BUG, 2026-04-28)

**Symptom**: PENGU LONG `highest_price` stayed frozen at entry price ($0.010039) even as price rose to $0.010201. TP was stuck computing from entry instead of actual peak, resulting in TP=$0.010400 instead of ~$0.010449.

**Root cause** (`position_manager.py` lines ~2283):
```python
elif direction == "LONG":
    new_high = existing_high  # ← BUG: never updates highest_price!
    new_low  = min(existing_low, cur_price)
```

The LONG branch copies `existing_high` directly instead of using `max()`. Combined with the SHORT bug (Bug B), the full asymmetry is:
- SHORT: `new_high = max(existing_high, cur_price)` ✓ but `new_low = existing_low` ✗
- LONG:  `new_high = existing_high` ✗ but `new_low = min(existing_low, cur_price)` ✓

Both directions have independent bugs preventing peak tracking.

**Fix** (applied 2026-04-28):
```python
elif direction == "LONG":
    new_high = max(existing_high, cur_price)  # track peak for LONG trailing
    new_low  = min(existing_low, cur_price)
```

**Verification**:
```sql
SELECT token, highest_price, lowest_price FROM trades WHERE token='PENGU' AND status='open';
-- After fix: highest_price should track actual peak, not entry
```

**Prevention**: Any time asymmetric LONG/SHORT code is written, both branches must be verified independently. Copy-paste errors between branches are a common source of bugs — always check both directions have equivalent update logic.
Even after the three-part initialization fix, ATOM SHORT's `lowest_price` stayed frozen at entry and the SL never tightened. Two independent root causes were found:

### Bug A — Unreachable code: `continue` at line 2178
A `continue` inside the `if hl_data:` block exits the loop before the peak update block runs for any position WITH HL data. This was fixed by moving the `continue` to the `else` branch.

See: `atr-trailing-unreachable-code` skill for full diagnosis and fix.

### Bug B — SHORT branch never updates `new_low` (ASYMMETRY BUG)
**Symptom**: `highest_price` updates correctly (ATOM: 2.0205→2.023), but `lowest_price` stays frozen at entry (2.0205) even as price falls to 2.0184 (SHORT in profit).

**Root cause** (`position_manager.py` lines ~2234-2236): The LONG branch correctly uses `min()` to track new lows, but the SHORT branch leaves `new_low = existing_low` unchanged:

```python
# SHORT branch — WRONG (new_low never updated):
elif direction == "SHORT":
    peak = existing_high
    new_high = max(existing_high, cur_price)   # tracks peak correctly ✓
    new_low  = existing_low                      # ← BUG: never updates!

# LONG branch — correct:
elif direction == "LONG":
    peak = existing_low
    new_high = max(existing_high, cur_price)   # tracks peak correctly
    new_low  = min(existing_low, cur_price)      # ← correct: min() tracks new lows
```

**Why**: The SHORT SL trails DOWN using `ref_price = lowest_price` (profit anchor). If `lowest_price` never goes below entry, the SL reference never improves and the SL stays wide. The asymmetry is:
- LONG: `highest_price` = profit anchor (max), SL trails UP as price rises
- SHORT: `lowest_price` = profit anchor (min), SL trails DOWN as price falls

**Fix** (`position_manager.py` ~line 2236):
```python
# WRONG:
new_low = existing_low

# CORRECT:
new_low = min(existing_low, cur_price)
```

**Verification** (ATOM SHORT after fix, price at 2.0184):
```
new_low  = min(2.0205, 2.0184) = 2.0184
new_SL   = 2.0184 × (1 + 0.00251) = 2.02307
vs prior SL = 2.025607 → SL tightened by 0.00254
```

**Prevention**: When adding asymmetric peak tracking (LONG uses max, SHORT uses min), always write both branches. Copy-paste asymmetry between LONG/SHORT branches is a common source of bugs — verify both directions have equivalent update logic.
