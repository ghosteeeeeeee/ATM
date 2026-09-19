# Ride-It Exit System — Bug Hunter Report

**Auditor:** Bug Hunter Subagent  
**Date:** 2026-09-17  
**Files Audited:**
- `scripts/ride_it_exit.py` (full file, 292 lines)
- `scripts/position_manager.py` (lines 2487–2824 — ride_it integration + surrounding exit pipeline)
- `scripts/hermes_constants.py` (lines 1417–1432 — SIGNAL_EXIT_CONFIG; lines 3447–3482 — RIDE_IT constants)

**Severity Scale:** CRITICAL = money-losing / system-breaking, HIGH = logic error affecting trades, MEDIUM = code quality / edge case, LOW = cosmetic

---

## Bug #1 — CRITICAL: Phase 2 Never Activates (Broken Datetime Parsing)

**Location:** `ride_it_exit.py:201`  
**Severity:** CRITICAL

**Description:**  
The `open_time` field in the `pos` dict is a Python `datetime` object (returned by psycopg2's `RealDictCursor` for a `TIMESTAMPTZ` column — see `position_manager.py:243`). The code treats it as a string:

```python
open_time_str = pos.get('open_time')           # → datetime object
entry_dt = datetime.fromisoformat(open_time_str.replace('+00:00', ''))  # TypeError!
```

`datetime.replace('+00:00', '')` is NOT `str.replace()`. It calls `datetime.replace()` which expects keyword arguments (`tzinfo=...`), not positional strings. This raises `TypeError`, caught by the `except` block at line 204:

```python
except Exception:
    hold_seconds = 0
    hold_hours = 0
```

**Impact:** `hold_seconds` is ALWAYS 0. Therefore:
- **Phase 2 (trail + momentum exit) never activates** — the entire 2h+ trailing system is dead code
- **Max hold time (24h) never fires** — `hold_hours` is always 0, so `0 >= 24` is always False
- Trades stuck in Phase 1 forever: wide ATR SL, no trailing, no momentum exit
- Only the **volume spike override** (time-independent) works as intended

**Fix:**
```python
# Replace lines 200-206 with:
try:
    if isinstance(open_time_str, datetime):
        entry_dt = open_time_str
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
    else:
        entry_dt = datetime.fromisoformat(str(open_time_str).replace('Z', '+00:00'))
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
    hold_seconds = (datetime.now(timezone.utc) - entry_dt).total_seconds()
    hold_hours = hold_seconds / 3600
except Exception:
    hold_seconds = 0
    hold_hours = 0
```

**Note:** The same bug exists in `position_manager.py:2673` (pump_exit time check). That code also does `.replace('+00:00', '')` on a datetime object. Pump_exit's ATR trailing and momentum exit still work (time-independent), but the **dead money time exit** is also broken.

---

## Bug #2 — CRITICAL: SHORT Phase 2 Trail Never Tightens (Inverted Comparison)

**Location:** `ride_it_exit.py:287`  
**Severity:** CRITICAL

**Description:**  
The trailing SL comparison `if new_sl > current_sl` is correct for LONG (higher SL = tighter) but **wrong for SHORT** (lower SL = tighter):

```python
# Phase 2 trail (line 284-290)
if direction == 'LONG':
    peak_price = max(current_price, highest_price)
    new_sl = peak_price - trail_distance
else:
    new_sl = current_price + trail_distance   # e.g., 98 + 1.176 = 99.176

if new_sl > current_sl:   # WRONG for SHORT!
    # For SHORT, current_sl might be 102 (wide). new_sl=99.176 is NOT > 102.
    # Trail never tightens.
```

**Impact:** SHORT positions using ride_it exit get **no trailing SL in Phase 2**. The SL stays at the Phase 1 wide value (up to 2.5% above entry) for the entire trade. If price reverses, the full 2.5% loss is taken instead of a trailed exit.

**Fix:**
```python
if direction == 'LONG':
    peak_price = max(current_price, highest_price)
    new_sl = peak_price - trail_distance
    if new_sl > current_sl:
        _persist_sl(trade_id, new_sl)
        ...
else:
    trough_price = min(current_price, lowest_price if lowest_price > 0 else current_price)
    new_sl = trough_price + trail_distance
    if new_sl < current_sl:  # LOWER = tighter for SHORT
        _persist_sl(trade_id, new_sl)
        ...
```

---

## Bug #3 — CRITICAL: SHORT Volume Spike Trail Never Tightens (Same Inverted Comparison)

**Location:** `ride_it_exit.py:233`  
**Severity:** CRITICAL

**Description:**  
Same inverted comparison in the volume spike override section:

```python
# Spike override (line 227-237)
if direction == 'LONG':
    peak_price = max(current_price, highest_price)
    new_sl = peak_price - trail_distance
else:
    new_sl = current_price + trail_distance

if new_sl > current_sl:   # WRONG for SHORT — same bug as #2
```

**Impact:** The volume spike override — the system's best defense against explosive moves — **does not trail for SHORT positions**. A SHORT trade experiencing a volume spike (price dropping fast, favorable) gets no tight trail to lock in gains.

**Fix:** Same pattern as Bug #2 — use `new_sl < current_sl` for SHORT with `lowest_price` tracking.

---

## Bug #4 — HIGH: Momentum Exit is Direction-Unaware (Exits SHORT When Profitable)

**Location:** `ride_it_exit.py:268-275`  
**Severity:** HIGH

**Description:**  
The momentum exit uses `_get_neg_candle_count()` which counts consecutive candles where price is **dropping** (negative velocity). The exit fires when `neg_candles >= RIDE_IT_MOMENTUM_CANDLES` AND `profit_pct > 0.01`.

For **LONG**: Negative candles = price dropping against us → correct exit signal.  
For **SHORT**: Negative candles = price dropping **in our favor** → exits a winning trade!

```python
neg_candles = _get_neg_candle_count(token, RIDE_IT_MOMENTUM_CANDLES)
if neg_candles >= RIDE_IT_MOMENTUM_CANDLES:
    if profit_pct > 0.01:  # >1% profit
        return {'action': 'EXIT', 'reason': reason}  # Exits SHORT when price is dropping (favorable!)
```

**Impact:** SHORT trades using ride_it exit are prematurely closed when price drops in their favor with 1%+ profit. The system exits winners.

**Fix:**
```python
if direction == 'LONG':
    neg_candles = _get_neg_candle_count(token, RIDE_IT_MOMENTUM_CANDLES)
    should_exit_momentum = neg_candles >= RIDE_IT_MOMENTUM_CANDLES
else:
    # For SHORT, exit when price is RISING (adverse momentum)
    pos_candles = _get_pos_candle_count(token, RIDE_IT_MOMENTUM_CANDLES)
    should_exit_momentum = pos_candles >= RIDE_IT_MOMENTUM_CANDLES

if should_exit_momentum and profit_pct > 0.01:
    return {'action': 'EXIT', 'reason': reason}
```

Needs a new `_get_pos_candle_count()` function (mirror of `_get_neg_candle_count` checking `pct_change > abs(RIDE_IT_MOMENTUM_VEL)`).

---

## Bug #5 — HIGH: Connection Leak in `_persist_sl` (No Finally Block)

**Location:** `ride_it_exit.py:161-172`  
**Severity:** HIGH

**Description:**  
The PostgreSQL connection and cursor are closed inside the `try` block, not in a `finally` block. If `cur.execute()` or `conn.commit()` throws, the connection leaks:

```python
def _persist_sl(trade_id: int, new_sl: float) -> None:
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
        cur = conn.cursor()
        cur.execute("UPDATE trades SET stop_loss = %s WHERE id = %s", (new_sl, trade_id))
        conn.commit()
        cur.close()     # ← Never reached if execute/commit fails
        conn.close()     # ← Never reached if execute/commit fails
    except Exception as e:
        log(f"[RIDE-IT] Persist SL error: {e}", 'WARN')
```

**Impact:** Called potentially every 30 seconds per ride_it trade. Under DB pressure or network issues, leaked connections accumulate. PostgreSQL has a `max_connections` limit — leaked connections could exhaust the pool.

**Fix:**
```python
def _persist_sl(trade_id: int, new_sl: float) -> None:
    conn = None
    cur = None
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
        cur = conn.cursor()
        cur.execute("UPDATE trades SET stop_loss = %s WHERE id = %s", (new_sl, trade_id))
        conn.commit()
    except Exception as e:
        log(f"[RIDE-IT] Persist SL error: {e}", 'WARN')
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if conn: conn.close()
        except Exception:
            pass
```

---

## Bug #6 — HIGH: SQLite Connections Not in Finally Blocks (4 functions)

**Location:** `ride_it_exit.py:50-59, 77-86, 102-111, 132-141`  
**Severity:** HIGH

**Description:**  
All four SQLite helper functions (`_get_atr`, `_get_volume_ratio`, `_get_momentum_velocity`, `_get_neg_candle_count`) close connections inside the `try` block, not in `finally`:

```python
def _get_atr(token, period=14):
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute(...)
        rows = cur.fetchall()
        cur.close()
        conn.close()     # ← Not reached if fetchall/processing fails
        ...
    except Exception as e:
        return 0         # Connection leaked!
```

**Impact:** If `fetchall()` raises (e.g., disk I/O error, DB corruption), the SQLite connection leaks. Over time, this causes "database is locked" errors as leaked connections hold file locks. The CANDLES_DB is shared across the entire pipeline.

**Fix:** Use `try/finally` pattern for all four functions:
```python
def _get_atr(token, period=14):
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute(...)
        rows = cur.fetchall()
        cur.close()
        if len(rows) < period + 1:
            return 0
        # ... process rows ...
        return sum(trs[-period:]) / period
    except Exception as e:
        log(f"[RIDE-IT] ATR error for {token}: {e}", 'WARN')
        return 0
    finally:
        try:
            if conn: conn.close()
        except Exception:
            pass
```

---

## Bug #7 — HIGH: `_persist_sl` Uses Different DB Credentials Than Position Manager

**Location:** `ride_it_exit.py:165`  
**Severity:** HIGH

**Description:**  
`ride_it_exit.py`'s `_persist_sl` uses hardcoded credentials:
```python
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
```

The position_manager uses:
```python
conn = psycopg2.connect(**BRAIN_DB_DICT)  # includes host, dbname, user, password
```

Where `BRAIN_DB_DICT` comes from `_secrets` and includes a password. If PostgreSQL requires password authentication (common in production), the ride_it version will fail silently (caught by except, logged as WARN, SL not persisted).

**Impact:** Trailing SL updates silently fail. The in-memory `pos['stop_loss']` is updated (line 2722 in position_manager), but the DB keeps the old SL. On next pipeline restart, the old wide SL is loaded, undoing all trailing.

**Fix:**
```python
def _persist_sl(trade_id: int, new_sl: float) -> None:
    conn = None
    cur = None
    try:
        from _secrets import BRAIN_DB_DICT
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("UPDATE trades SET stop_loss = %s WHERE id = %s", (new_sl, trade_id))
        conn.commit()
    except Exception as e:
        log(f"[RIDE-IT] Persist SL error: {e}", 'WARN')
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if conn: conn.close()
        except Exception:
            pass
```

---

## Bug #8 — MEDIUM: SHORT Trail Doesn't Track `lowest_price` (Phase 2 + Spike)

**Location:** `ride_it_exit.py:230-231, 284-285`  
**Severity:** MEDIUM

**Description:**  
For LONG, the trail uses `peak_price = max(current_price, highest_price)` — correctly anchoring to the highest point. For SHORT, the trail uses only `current_price`, ignoring `lowest_price` (the nadir):

```python
# Phase 2, line 284-285
else:
    new_sl = current_price + trail_distance  # No lowest_price tracking!
```

Compare with pump_exit in position_manager.py:2613-2614:
```python
lowest_price = float(pos.get("lowest_price", cur))
trough_price = min(cur, lowest_price)  # ← Correctly tracks nadir
```

**Impact:** SHORT trail is anchored to current price, not the lowest point. If price bounces up from the nadir, the trail jumps up with it instead of staying anchored at the lowest point. This loosens the SL prematurely during pullbacks.

**Fix:** Add `lowest_price` to the SHORT path:
```python
else:
    lowest_price = float(pos.get('lowest_price') or current_price)
    trough_price = min(current_price, lowest_price)
    new_sl = trough_price + trail_distance
```

---

## Bug #9 — MEDIUM: `volume-breakout` Bare Variant Missing from SIGNAL_EXIT_CONFIG

**Location:** `hermes_constants.py:1427-1431`  
**Severity:** MEDIUM

**Description:**  
`mover` has a bare variant (`'mover': 'ride_it'`), `pump_chain` has a bare variant (`'pump_chain': 'pump_exit'`), but `volume-breakout` does NOT have a bare variant. Only `volume-breakout+`, `volume-breakout-`, `volume_breakout+`, `volume_breakout-` are mapped.

```python
'volume-breakout+': 'ride_it',
'volume-breakout-': 'ride_it',
'volume_breakout+': 'ride_it',
'volume_breakout-': 'ride_it',
# Missing: 'volume-breakout': 'ride_it'
# Missing: 'volume_breakout': 'ride_it'
```

**Impact:** If a signal fires with source `volume-breakout` (no +/- suffix), the trade falls through to default exit behavior (ATR TP/SL only). The ride_it 2-phase system is not applied.

**Fix:**
```python
'volume-breakout+': 'ride_it',
'volume-breakout-': 'ride_it',
'volume-breakout': 'ride_it',    # bare variant
'volume_breakout+': 'ride_it',
'volume_breakout-': 'ride_it',
'volume_breakout': 'ride_it',    # bare variant
```

---

## Bug #10 — MEDIUM: `RIDE_IT_TP_PHASE1_MULT` Defined But Never Used

**Location:** `hermes_constants.py:3465`, `ride_it_exit.py` (not imported)  
**Severity:** MEDIUM

**Description:**  
`RIDE_IT_TP_PHASE1_MULT = 3.0` is defined in constants but never imported or used in `ride_it_exit.py`. The import block (lines 31-40) doesn't include it. No TP calculation exists in the module.

**Impact:** No functional impact, but the constant suggests a Phase 1 TP was planned and forgotten. If someone later expects ride_it to enforce a 3x ATR TP, it won't.

**Fix:** Either implement Phase 1 TP logic or remove the constant to avoid confusion.

---

## Bug #11 — MEDIUM: Duplicate Imports/Re-parsing in Position Manager Loop

**Location:** `position_manager.py:2559-2560, 2699-2700, 2731-2732`  
**Severity:** MEDIUM

**Description:**  
For EVERY position in the exit loop, the same imports and signal parsing happen 3 times:
```python
signal = str(pos.get("signal", "") or "")          # Lines 2559, 2699, 2731
from hermes_constants import SIGNAL_EXIT_CONFIG, RR_EXIT_ENABLED  # Lines 2560, 2700, 2732
signal_parts = [s.strip() for s in signal.split(',')]            # Lines 2561, 2701, 2733
```

**Impact:** Python caches module imports, so the `from` import is cheap. But `signal.split(',')` and the loop are repeated 3x per position per cycle. With 10 open positions and 30s cycle time, this is 900 unnecessary string operations per minute. Minor performance issue.

**Fix:** Parse `signal` and `signal_parts` once before the exit check blocks, and check exit config once with a lookup:
```python
signal = str(pos.get("signal", "") or "")
signal_parts = set(s.strip() for s in signal.split(','))
# Then check: if signal_parts & RIDE_IT_SIGNALS
```

---

## Bug #12 — MEDIUM: `hold_seconds=0` Puts Trade in Phase 1 With Potential SL Loosening

**Location:** `ride_it_exit.py:246-264`  
**Severity:** MEDIUM

**Description:**  
When datetime parsing fails (Bug #1), `hold_seconds = 0`. This puts the trade in Phase 1 (`0 < 7200`). Phase 1 calculates a new SL and compares against `current_sl`. If the trade already has a tighter SL from another system (e.g., ATR SL at 1.5%), Phase 1 won't loosen it (the `>` / `<` checks prevent that). But if the trade has a very wide SL (e.g., initial market SL at 5%), Phase 1 will tighten to 2.5%.

The issue is that **every call** to `manage_ride_it_exit` re-calculates and potentially re-persists the Phase 1 SL, even if it was already set. This is wasteful but not harmful.

**Impact:** Redundant DB writes every 30s for Phase 1 SL that doesn't change after the first update.

**Fix:** Add a check: if `current_sl` is already within Phase 1 range, skip the persist.

---

## Bug #13 — LOW: `pump_exit` + `ride_it` Can Both Fire on Same Trade

**Location:** `position_manager.py:2556-2726`  
**Severity:** LOW

**Description:**  
If a trade has a comma-separated signal like `"mover+,pump_chain+"`, both `use_pump_exit` and `use_ride_it` would be True. The pump_exit block runs first (line 2556). If pump_exit does a TRAIL_SL (not EXIT), the ride_it block also runs, potentially overriding the SL.

**Impact:** Two exit systems fighting over the same SL value. The last one to write wins. In practice, this is unlikely because signals are typically mapped to one exit system, not both.

**Fix:** Add early exit after pump_exit fires: if `use_pump_exit` is True, skip ride_it. Or use `elif` chain instead of sequential if-blocks.

---

## Bug #14 — LOW: `_get_neg_candle_count` Uses `RIDE_IT_MOMENTUM_VEL` Directly (Not a Parameter)

**Location:** `ride_it_exit.py:150`  
**Severity:** LOW

**Description:**  
```python
if pct_change < RIDE_IT_MOMENTUM_VEL:  # Direct global reference
```

If `_CONSTS_LOADED` is False, `RIDE_IT_MOMENTUM_VEL` would be undefined. The main function returns early when constants aren't loaded (line 186-187), so this function is never called in that case. But it's a latent NameError if the function is ever called independently.

**Fix:** Pass `RIDE_IT_MOMENTUM_VEL` as a parameter, or check `_CONSTS_LOADED` at function entry.

---

## Summary Table

| # | Severity | Location | Bug |
|---|----------|----------|-----|
| 1 | **CRITICAL** | `ride_it_exit.py:201` | Phase 2 never activates — datetime parsing always fails (open_time is datetime, not string) |
| 2 | **CRITICAL** | `ride_it_exit.py:287` | SHORT Phase 2 trail comparison inverted — trail never tightens |
| 3 | **CRITICAL** | `ride_it_exit.py:233` | SHORT spike override trail comparison inverted — same issue |
| 4 | **HIGH** | `ride_it_exit.py:268-275` | Momentum exit direction-unaware — exits SHORT when price drops (favorable) |
| 5 | **HIGH** | `ride_it_exit.py:161-172` | `_persist_sl` connection leak — no finally block |
| 6 | **HIGH** | `ride_it_exit.py:50-59,77-86,102-111,132-141` | SQLite connections not in finally blocks (4 functions) |
| 7 | **HIGH** | `ride_it_exit.py:165` | `_persist_sl` uses different DB credentials — may silently fail |
| 8 | **MEDIUM** | `ride_it_exit.py:230-231,284-285` | SHORT trail doesn't track `lowest_price` |
| 9 | **MEDIUM** | `hermes_constants.py:1427-1431` | `volume-breakout` bare variant missing from SIGNAL_EXIT_CONFIG |
| 10 | **MEDIUM** | `hermes_constants.py:3465` | `RIDE_IT_TP_PHASE1_MULT` defined but never used |
| 11 | **MEDIUM** | `position_manager.py:2559-2732` | Duplicate imports/re-parsing 3x per position per cycle |
| 12 | **MEDIUM** | `ride_it_exit.py:246-264` | Phase 1 SL re-persisted every cycle even when unchanged |
| 13 | **LOW** | `position_manager.py:2556-2726` | pump_exit + ride_it can both fire on same trade |
| 14 | **LOW** | `ride_it_exit.py:150` | `_get_neg_candle_count` uses global constant directly (latent NameError) |

---

## Net Assessment

**The ride_it_exit system is fundamentally broken for its primary purpose.** Bugs #1-#3 mean:
- Phase 2 (the actual trailing + momentum exit system) **never runs**
- SHORT positions get **no trailing at all** (Phase 1 sets wide SL, Phase 2 never tightens)
- The only working components are: Phase 1 SL calculation + volume spike override (LONG only)

**What actually works today:**
- ✅ Phase 1 ATR-based SL (LONG and SHORT) — sets a wide but bounded SL
- ✅ Volume spike override (LONG only) — tight trail on volume spikes
- ❌ Phase 2 trail — dead code (datetime bug) + broken for SHORT (comparison bug)
- ❌ Momentum exit — exits SHORT in the wrong direction
- ❌ Max hold time — dead code (datetime bug)
- ⚠️ SL persistence — may silently fail (credential mismatch) + leaks connections

**Recommended fix priority:**
1. Fix Bug #1 (datetime) — unblocks Phase 2
2. Fix Bugs #2-#3 (SHORT comparison) — makes trail work for SHORT
3. Fix Bug #4 (momentum direction) — stops exiting profitable SHORTs
4. Fix Bugs #5-#7 (connection handling) — prevents leaks and silent failures
5. Fix Bug #8 (lowest_price tracking) — proper SHORT trail anchoring
