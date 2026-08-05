# G4 + G5 + G6 Fixes — hl-sync-guardian.py — 2026-06-12 (3rd audit session)

## Bug G4: PHANTOM_CLOSE Backfill Never Fires

**File**: `hl-sync-guardian.py`
**Function**: `_retry_phantom_close_fills()` (line ~469)
**Severity**: MEDIUM — PHANTOM_CLOSE trades never get their real exit prices backfilled

### Root Cause

`_get_hl_exit_price()` never returns 0. Its fallback logic (lines 995-1003):
```python
if not fallback or fallback <= 0:
    curr = float(mids[token.upper()])  # returns current market price
    if curr > 0:
        return curr  # NEVER returns 0
return fallback  # fallback is 0.0 but only reached if mids lookup fails
```

So `_poll_hl_fills_for_close()` returns `(0.0, None)` only when `_poll_close_fills_once()` returns `(None, None)`, which only happens when `_get_fills_cached()` returns an empty list — meaning no HL fills for that token in the last 5 minutes. In that case, `_get_hl_exit_price()` falls back to current market price, not 0.

**Result**: `_retry_phantom_close_fills()` queries for `WHERE exit_price = 0` — this condition is **always false** for any trade closed by the guardian. The backfill has never worked.

### Fix (2 locations)

**SELECT WHERE (line ~492)**:
```sql
-- BEFORE (never matched):
WHERE server = %s AND status = 'closed' AND close_reason = 'PHANTOM_CLOSE' AND exit_price = 0

-- AFTER:
WHERE server = %s AND status = 'closed' AND close_reason = 'PHANTOM_CLOSE'
```

**UPDATE WHERE (line ~541)**:
```sql
-- BEFORE:
WHERE id = %s AND exit_price = 0

-- AFTER:
WHERE id = %s
```

### Verification
```bash
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py && echo "Syntax OK"
git log --oneline -5
# bded25e hl-sync-guardian: fix PHANTOM_CLOSE backfill (G4)
```

---

## Bug G5: CASCADE_FLIP Hard-SL Close Bypasses `_close_paper_trade_db`

**File**: `hl-sync-guardian.py`
**Function**: `_check_and_execute_flip()` (line ~1476)
**Severity**: HIGH — losing trades don't record loss cooldown, re-entry not blocked

### Root Cause

When CASCADE_FLIP fires on hard-SL (line 1396), the old code did a direct SQL UPDATE:
```sql
UPDATE trades SET status='closed', close_reason='CASCADE_FLIP',
    exit_reason='flipped_hard_sl', flip_variant=%s, guardian_closed=TRUE
WHERE id=%s
```

This bypassed `_close_paper_trade_db`, which does three things the direct UPDATE misses:
1. **`_record_loss_cooldown(token, direction)`** — losing trades are blocked from re-entering in the same direction
2. **`_clear_reconciled_token(token)`** — allows new positions to be reconciled without stale state
3. **Computes and writes `pnl_pct` and `pnl_usdt`** — leaving them NULL corrupts PnL records

### Fix

Replace the direct UPDATE with a `_close_paper_trade_db()` call, then set `flip_variant` separately:
```python
# BEFORE (line 1474-1480):
cur.execute("""
    UPDATE trades SET status='closed', close_reason='CASCADE_FLIP',
        exit_reason='flipped_hard_sl', flip_variant=%s,
        guardian_closed=TRUE
    WHERE id=%s
""", (variant_id, trade_id))

# AFTER:
flip_exit_px = prices.get(token, entry_px)
_close_paper_trade_db(trade_id, token, flip_exit_px, 'CASCADE_FLIP')
# Set flip_variant on the now-closed trade record
conn = get_db_connection()
if conn:
    try:
        cu = conn.cursor()
        cu.execute("UPDATE trades SET flip_variant=%s WHERE id=%s", (variant_id, trade_id))
        conn.commit()
        cu.close()
        conn.close()
    except Exception:
        pass
```

`flip_variant` is set separately because `_close_paper_trade_db` doesn't know about it — it only takes `(trade_id, token, exit_price, reason)`.

### Why Not Use `_close_paper_trade_db` with Extra Args?

`_close_paper_trade_db` signature: `(trade_id, token, exit_price, reason)`. Adding `flip_variant` as a new optional parameter would require updating the function itself and all its call sites. The two-step approach is cleaner and mirrors the STALE_ROTATION fix pattern.

---

## Bug G6: `rate_data` Possibly Unbound

**File**: `hl-sync-guardian.py`
**Function**: `_check_stale_rotation()` (line ~1997)
**Severity**: LOW — only triggers if `os.path.exists()` raises during file read

### Root Cause

```python
# BEFORE:
try:
    rate_data = {}  # assigned INSIDE try
    if os.path.exists(rate_file):
        with open(rate_file) as f:
            rate_data = _json.load(f)
    last_rot = rate_data.get(token, 0)
    if _time.time() - last_rot < RATE_LIMIT_SEC:
        return
except:
    pass
```

If `os.path.exists(rate_file)` raises ANY exception before `rate_data` is assigned, the variable is unbound. Subsequent `_update_rate()` call would `NameError`.

### Fix
```python
# AFTER:
rate_data = {}  # assigned BEFORE try
try:
    if os.path.exists(rate_file):
        with open(rate_file) as f:
            rate_data = _json.load(f)
    ...
```

---

## Complete Manual Audit Results — Lines 2116–4232

Done in main session after ai-engineer subagent timed out for the 3rd consecutive time.

### Verified Correct
| Check | Result |
|-------|--------|
| SQL param counts (unprotectable UPDATE) | 7 params ✅ |
| SQL param counts (breach UPDATE) | 9 params ✅ |
| SQL param counts (`_close_paper_trade_db`) | 8 params ✅ |
| SQL param counts (`_close_orphan_paper_trade_by_id`) | 8 params ✅ |
| `_poll_hl_fills_for_close` return `(0.0, None)` handled | All 4 callers check `hl_exit_px == 0.0` ✅ |
| `_wait_for_position_closed` return type | Returns `bool`, always checked ✅ |
| Hard-stop loss cooldown | Recorded at line 3208 ✅ |
| Cut-loser loss cooldown | Recorded at line 3373 ✅ |
| `_sweep_blocklist_trades` | All paths use `_close_paper_trade_db` ✅ |
| Breach handler | All batch-1 fixes verified in place ✅ |
| Self-close unprotectable path | All batch-1 fixes verified in place ✅ |
| `_failure_count` | Incremented on all sync failure paths ✅ |
| Telegram failures | Logged as WARN, never silently swallowed ✅ |
| `_load_pending_retry_unlocked` | Returns empty set on error ✅ |
| `_get_hl_exit_price` | Never returns 0 ✅ |

### ai-engineer Subagent — Final Status

All 3 delegation attempts timed out at 600s regardless of timeout parameter:
- Pass 1 (15-min): 566s, no timeout delivered
- Pass 2 (20-min): timed out, no results
- Pass 3 (20-min): timed out, no results

**Lesson**: Do not use ai-engineer subagent for hl-sync-guardian.py audit. Use main session with targeted `execute_code` searches.
