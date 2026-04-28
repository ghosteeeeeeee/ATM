---
name: phantom-trade-debugging
description: Debug and fix phantom trades in Hermes — trades in DB that never reached Hyperliquid, causing wrong close_reason and PnL
triggers:
  - "phantom trades"
  - "HL_CLOSED but hl_entry_price=0"
  - "DB has more closes than HL"
  - "trade never appeared on Hyperliquid"
  - "phantom close"
  - "guardian missing tracking stale"
  - "hotset.json stale"
  - "decider_run blocking approvals"
  - "ai_decider lock held"
  - "pump_hunter guardian conflict"
  - "new trading system interfering with position_manager"
  - "guardian closing my new trades"
  - "tpsl_self_close stale record"
  - "trade closed at entry price wrong reason"
  - "TP triggered on fresh position"
  - "guardian orphan but DB says atr_sl_hit"
  - "trade closed with atr_sl_hit but TP/SL not hit"
  - "TP triggered on fresh position"
  - "TP triggered on SHORT but TP was above entry (inverted direction)"
  - "guardian TP=0.16595215 for SHORT entry=0.15465 (7.3% above entry)"
  - "stale LONG TP inherited by SHORT position"
  - "guardian Step 6 race condition"
---

# Phantom Trade Debugging — Hermes Trading System

## Problem
Trades appear in the DB (paper=False) but never reached Hyperliquid. The guardian closes them as `HL_CLOSED` with wrong exit prices, corrupting trade history. Multiple tokens showed 5-36x more closes in DB than in actual HL fill history (e.g., BLUR: 1 real HL close, 36 DB records).

## Root Cause — Two Independent Failure Points

### 1. brain.py — Phantom paper records left behind after failed HL mirror
`brain.py` creates a paper trade in DB, then calls `mirror_open()` to send to Hyperliquid. When `mirror_open()` fails (rate limit, insufficient margin, max positions, `is_live_trading` off, exception), the paper trade stays in DB with `paper=False` but **no HL position**.

The guardian runs every 2 minutes, sees DB has the token but HL doesn't → "missing from HL" → closes as `HL_CLOSED` → phantom close created.

### 2. guardian Step 8 — Uses wrong close_reason for unconfirmed trades
Even if brain.py correctly set `hl_entry_price` after a successful HL fill, guardian Step 8 wasn't checking it before assigning `HL_CLOSED`. `hl_entry_price IS NOT NULL` is the only reliable proof that HL confirmed the position.

## Pattern: Adding a New Independent Trading System (e.g. pump_hunter)

When adding a new standalone trade executor (e.g., `pump_hunter.py`) that creates its own HL positions independently of the brain.py pipeline, two systems must be explicitly told to ignore it:

### The Problem
- Guardian runs every 2 minutes and detects "orphan" HL positions (positions on HL with no matching DB record)
- Guardian creates phantom DB records for orphans and tries to manage/close them
- PM's `get_open_positions()` also reads DB and would try to apply ATR TP/SL to the new positions

### The Solution: Signal Label + Query Filters

**1. Label all new-system trades with a distinct `signal` value in the DB**, e.g. `signal='pump_hunter'`

**2. Guardian duplicate guard (line ~961):** Add exclusion for the signal label so guardian doesn't treat it as a duplicate:
```sql
-- BEFORE:
SELECT id FROM trades WHERE token=%s AND status='open' LIMIT 1
-- AFTER:
SELECT id, signal FROM trades WHERE token=%s AND status='open' AND signal != 'pump_hunter' LIMIT 1
```

**3. Guardian orphan guard (line ~1000):** The orphan guard fires when a token is on HL but has no DB record. For a new trading system, the DB record is created BEFORE `mirror_open()` — this ordering is critical to prevent the race:
- If DB record is created AFTER `mirror_open()`, guardian runs between the two and finds the orphan first → creates phantom → new system finds DB record exists → confusion
- If DB record is created BEFORE `mirror_open()`, guardian's orphan check sees the DB record exists → no orphan created → safe

**4. PM `get_open_positions()` (line ~267):** Add exclusion so PM never picks up the new system's positions:
```sql
-- BEFORE:
... WHERE server='Hermes' AND status='open'
-- AFTER:
... WHERE server='Hermes' AND status='open' AND (signal IS NULL OR signal != 'pump_hunter')
```

**5. Exit handling:** The new system handles its own exits. Guardian's Step 8 close logic should skip `signal='pump_hunter'` records via the duplicate guard (Fix 2 above). PM's ATR TP/SL logic skips them via Fix 3.

### Key Files to Modify
- `/root/.hermes/scripts/hl-sync-guardian.py` — duplicate guard query
- `/root/.hermes/scripts/position_manager.py` — `get_open_positions()` query

### Verification
After adding a new signal source, verify no cross-contamination:
```bash
grep -n "pump_hunter" position_manager.py hype-sync.py  # should return nothing
grep -n "pump_hunter" hl-sync-guardian.py  # should only show the exclusion line
```

## The Two-Fix System

Both fixes are required — they address different failure points:

### Fix A — brain.py: Delete phantom paper records when HL mirror fails
**File:** `/root/.hermes/scripts/brain.py`

When `mirror_open()` fails, immediately delete the paper trade from DB so the guardian never sees it:

```python
# In the branch where mirror_open() returns error/neither-success-nor-blocklist:
try:
    conn_del = get_db_connection()
    cur_del = conn_del.cursor()
    cur_del.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
    conn_del.commit()
    cur_del.close(); conn_del.close()
    print(f"[brain.py] 🗑️ Deleted phantom paper trade #{trade_id} ({hype_token})")
except Exception as del_err:
    print(f"[brain.py] ⚠️ Failed to delete phantom trade #{trade_id}: {del_err}")
```
Also apply to: `is_live_trading` off branch, and exception handler.

**Key:** Keep blacklisted tokens (they're intentional tracking entries).

### Fix B — hl-sync-guardian.py: Check hl_entry_price before HL_CLOSED
**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

In Step 8 close logic (both the `guardian_closed=FALSE` and `guardian_closed=TRUE` paths):

```python
has_hl_confirmation = bool(hl_entry_price)  # hl_entry_price IS NOT NULL

if not has_hl_confirmation:
    close_reason = 'PHANTOM_CLOSE'  # HL never confirmed — not a real HL close
else:
    # HL confirmed — use TP/SL logic for close reason
    close_reason = 'HL_CLOSED'  # or HL_TP_CLOSED / HL_SL_CLOSED
```

**Key:** `paper=False` with `hl_entry_price=NULL` → `PHANTOM_CLOSE`, never `HL_CLOSED`.

### Fix Nx — profit-monster and other close agents: HL-first architecture
**File:** `/root/.hermes/scripts/profit_monster.py` (and any other script that closes positions)

Agents that close positions (profit-monster, manual close scripts, etc.) were closing the DB record without closing the real HL position. The guardian runs ~2 min later, sees HL still has the position (close order pending/unfilled), treats it as an orphan, and creates a new DB trade to close it → **duplicate closed trade**.

**The fix:** Any agent closing a position must close HL **first**, then close DB. Guardian-side fixes (Fix N, Fix Nb) handle the residual race, but the correct architecture is HL-first:

```python
from hyperliquid_exchange import is_live_trading_enabled, close_position

# In close_position() or equivalent close logic:
if is_live_trading_enabled():
    result = close_position(token.upper())  # close real HL position FIRST
    log(f"  HL close OK: {token}", "PASS")
else:
    log(f"  HL close skipped (paper mode)", "INFO")
# ... THEN close DB record via brain.py trade close
```

**Why it matters:** If the HL close order is still pending (not filled), the guardian's `_CLOSED_HL_COINS` set is rebuilt fresh each cycle from open HL positions — so the pending-close position still appears open and bypasses the orphan guard. The guardian then creates a phantom duplicate. HL-first prevents this at the source.

**Paper mode:** In paper mode, no real HL position exists — skip HL close, close DB only.

### Fix N — `_CLOSED_HL_COINS` race condition causes spurious orphan creation
**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

When a close order is placed on HL but hasn't filled yet, `get_open_hype_positions_curl()` still returns the position as open (close order is pending, not filled). The guardian's `sync()` builds `_CLOSED_HL_COINS` fresh each cycle from HL's open positions — so a position with a pending close appears "still open" and bypasses the `_CLOSED_HL_COINS` check.

The orphan detection at Step 7 then sees the token in HL but not in the reconciled `_CLOSED_HL_COINS` set → creates a new orphan paper trade with `signal=NULL`.

**Symptom:** A trade closes via `profit-monster` on the DB side, but the HL close order hasn't filled yet. In the next guardian cycle (~2 min later), the guardian creates a phantom orphan for the same token.

**Fix:** Before creating an orphan, look up whether the token has a known trade in DB. If a trade exists (even if closed), preserve its `signal` value:

```python
# In add_orphan_trade() or the orphan-creation path:
# Look up the signal from the most recent trade for this token
cur_signal = conn.cursor()
cur_signal.execute(
    "SELECT signal FROM trades WHERE token=%s AND server='Hermes' "
    "ORDER BY id DESC LIMIT 1",
    (token,)
)
sig_row = cur_signal.fetchone()
original_signal = sig_row[0] if sig_row else None

# Use original_signal instead of hardcoded NULL in the INSERT
```

Also: consider maintaining a `_PENDING_CLOSES` in-memory set of tokens with close orders placed but not yet confirmed filled. These should be excluded from orphan detection for the current cycle.

### Fix Nb — `add_orphan_trade()` hardcodes `signal=NULL`
**File:** `/root/.hermes/scripts/hl-sync-guardian.py` (line ~573)

The `add_orphan_trade()` function's INSERT hardcodes `signal=NULL` via a `SELECT NULL` subquery. When the guardian creates an orphan for a known HL position (one that existed in DB before but wasn't properly tracked), the original signal is lost.

```sql
-- BEFORE (hardcoded NULL):
INSERT INTO trades (..., signal, ...)
SELECT ..., NULL, ...
WHERE NOT EXISTS (SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open')

-- AFTER (preserve original signal if known):
INSERT INTO trades (..., signal, ...)
SELECT ..., COALESCE(
    (SELECT signal FROM trades WHERE token=%s AND server='Hermes' ORDER BY id DESC LIMIT 1),
    NULL
), ...
WHERE NOT EXISTS (SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open')
```

### Fix Bb — Guardian Step 7b: Delete phantoms in `mirror_open_retry`
**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

In Step 7b's `live_missing` loop, check `is_live_trading_enabled()` BEFORE calling `mirror_open()`. If it's False or `mirror_open()` fails, DELETE the `paper=False` phantom from DB immediately. Don't just log it — actually delete it.

```python
if not is_live_trading_enabled():
    # Live trading is off — don't leave phantom paper trades
    try:
        cur_del.execute("DELETE FROM trades WHERE id=%s AND paper=false AND status='open'", (trade_id,))
        conn_del.commit()
        log(f'[LIVE-MISS] Deleted phantom paper trade #{trade_id} ({token})')
    except Exception as del_err:
        log(f'[LIVE-MISS] Failed to delete phantom trade #{trade_id}: {del_err}')
    continue
```

### Fix C — Fill cache to consolidate HL API calls
`get_trade_history()` is rate-limited. Both `_get_hl_exit_price()` and `_close_paper_trade_db()` were calling it independently — 2 API calls per close. Add an in-memory cache:
```python
# Key: (token, window_start_ms, window_end_ms) → list of fills
# TTL: 5 minutes, max 3 API calls per 60s guardian cycle
_FILL_CACHE = {}
def _get_fills_cached(token, window_start_ms, window_end_ms):
    ...
```

### Fix D — PHANTOM_CLOSE backfill retry
Trades that slip through as `PHANTOM_CLOSE` (exit_price=0) need their real HL exit prices backfilled. Run `_retry_phantom_close_fills()` every guardian cycle:
```python
def _retry_phantom_close_fills():
    # Find PHANTOM_CLOSE trades with exit_price=0, poll HL fill cache,
    # backfill exit_price and pnl_pct when fills become available
```

### Fix E — Duplicate-entry guard
**File:** `/root/.hermes/scripts/decider_run.py`

Before opening any new position, check DB for existing open trade on same token+direction:
```python
_dup_cur.execute(
    "SELECT id FROM trades WHERE server='Hermes' AND token=%s AND direction=%s AND status='open' LIMIT 1",
    (token.upper(), direction.upper()))
if _dup_row:
    return False, f'duplicate_entry_blocked token={token}'
```

### Fix O — `tpsl_self_close` stale records cause wrong TP/SL AND wrong direction on reopened positions

**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

**Symptom:** A trade closes (via TP or SL on HL). The guardian's `tpsl_self_close` record for that coin is never deleted. A new trade opens for the same coin (possibly in the OPPOSITE direction). Guardian finds the old record and uses its stale TP/SL. TP fires immediately (stale TP was below new entry for LONG, or ABOVE entry for SHORT), or SL fires immediately. Trade closes at entry or wrong price with wrong reason. PnL is near zero because exit_price was written as the stale entry or wrong current price.

**Root cause:** `tpsl_self_close` has no cleanup when a position closes. The table accumulates triggered records indefinitely. When refreshing a stale record (Fix O step 1), the code copies the OLD TP/SL (e.g., LONG targets) but uses the NEW entry_px — it does NOT recalculate TP/SL for the new direction.

**CRITICAL: Stale LONG TP/SL inherited by SHORT position (confirmed 2026-04-28 MET)**
```
05:44:41  New MET SHORT opens, entry=0.15465
05:45:32  Guardian detects stale record (stored=0.157270 vs current=0.154650, Δ=1.69%)
           Calls _upsert_self_close(coin, direction=SHORT, sz, entry_px=0.15465,
           # BUG: passes OLD LONG TP/SL unchanged:
           sl_price=0.16080928, tp_price=0.16595215)   ← this is the OLD LONG TP!
           # TP for SHORT should be BELOW entry (tp < 0.15465)
           # But tp=0.16595215 is 7.3% ABOVE entry — WRONG DIRECTION
           continue  # skip breach check this cycle
05:46:32  Guardian breach check: SHORT position, curr=0.15465
           Condition: curr <= tp_price  →  0.15465 <= 0.16595215  →  TRUE!
           "TP triggered" fires — but TP was never actually hit
           close_paper_position writes exit_price = current_price = 0.15461 (wrong)
           PnL computed as ~$0.00 instead of actual ~$0.013
           Guardian log: "TP triggered (px=0.15465 <= tp=0.16595215)"
```

**All fast phantom closes (< 5s) share this pattern:**
| Coin | Dir | Entry | Exit | PnL | Close Reason | Issue |
|------|-----|-------|------|-----|--------------|-------|
| TON | LONG | 1.3146 | 1.31305 | -$0.06 | atr_tp_hit | TP reason but LOSS |
| GRIFFAIN | SHORT | 0.017603 | 0.017623 | -$0.06 | atr_sl_hit | Price UP, SHORT loses |
| XRP | SHORT | 1.4165 | 1.41655 | $0.00 | atr_sl_hit | 0.0035% move, near zero |
| ATOM | SHORT | 2.002 | 2.0029 | -$0.02 | atr_sl_hit | Price UP, SHORT loses |
| FIL | SHORT | 0.94161 | 0.94174 | -$0.01 | atr_sl_hit | Price UP, SHORT loses |
| MET | SHORT | 0.15465 | 0.15461 | $0.00 | TP triggered | TP inverted (above entry for SHORT) |

**Fix O-1 (guardian stale refresh MUST recalculate TP/SL for new direction):**

**File:** `/root/.hermes/scripts/hl-sync-guardian.py`, lines ~2922-2927

The existing Fix O added entry validation but COPIED the old TP/SL. The fix must RECALCULATE:

```python
# BEFORE (BUG — copies old LONG TP/SL for new SHORT position):
if entry_delta > 0.001:
    log(f'  [SELF-CLOSE] ⚠️ {coin} stale record ...')
    _upsert_self_close(coin, direction, sz, entry_px, record['sl_price'], record['tp_price'])
    continue

# AFTER (FIX — MUST recalculate TP/SL for new entry AND direction):
if entry_delta > 0.001:
    log(f'  [SELF-CLOSE] ⚠️ {coin} stale record (stored={stored_entry:.6f} vs current={entry_px:.6f}) — refreshing', 'WARN')
    # MUST recalculate TP/SL for the new entry_px and current direction
    # Copying the old LONG TP/SL for a new SHORT position produces inverted targets
    from atr_cache import get_atr
    real_atr = get_atr(coin, interval='1h')
    curr_px = prices.get(coin, entry_px)
    if real_atr is not None and curr_px > 0:
        atr_pct = real_atr / curr_px
    else:
        atr_pct = ATR_PCT_FALLBACK  # 2% assumed fallback
    k = ATR_K_NORMAL_VOL
    k_tp = k * ATR_TP_K_MULT
    sl_pct = max(ATR_SL_MIN, min(ATR_SL_MAX, k * atr_pct))
    tp_pct = max(ATR_TP_MIN, min(ATR_TP_MAX, k_tp * atr_pct))
    if direction == 'LONG':
        new_sl = round(curr_px * (1 - sl_pct), 8)
        new_tp = round(curr_px * (1 + tp_pct), 8)
    else:  # SHORT — TP is BELOW entry, SL is ABOVE entry
        new_sl = round(curr_px * (1 + sl_pct), 8)
        new_tp = round(curr_px * (1 - tp_pct), 8)
    _upsert_self_close(coin, direction, sz, entry_px, new_sl, new_tp)
    continue
```

**Fix O-2 (cleanup):** Delete triggered `tpsl_self_close` records when positions close. Add to the guardian's close flow:

```python
# When guardian closes a position (after successful market close):
cur.execute("DELETE FROM tpsl_self_close WHERE coin = %s", (coin,))
```

Also run periodically as a maintenance query:
```sql
-- Delete records for coins with no open HL position
DELETE FROM tpsl_self_close
WHERE coin NOT IN (SELECT DISTINCT token FROM trades WHERE status = 'open');
```

**Fix O-3 (guardian DB close):** Guardian's `UPDATE trades SET ... WHERE id=%s` was missing `close_time=NOW()`. Always include it:
```python
cur_sc.execute("""
    UPDATE trades SET
        status='closed',
        close_time=NOW(),   -- ← always set this
        close_reason=%s,
        ...
""")
```

**Investigation pattern for fast phantom closes:**
1. `grep -n "stale record" sync-guardian.log` — look for entry mismatch > 0.1%
2. Check if the TP/SL values were for the OPPOSITE direction (LONG targets vs SHORT position)
3. The stale refresh at 05:45 and the breach at 05:46 are often two SEPARATE guardian cycles — the stale record persists and is reused
4. `close_paper_position` writing `exit_price = current_price` is a SECONDARY bug — the primary bug is the inverted TP/SL causing the close in the first place

## Diagnostic Queries

### Find phantom HL_CLOSED records (DB has more closes than HL)
```sql
-- Compare DB close count vs HL close count per token
SELECT token, direction, COUNT(*) as db_closes
FROM trades WHERE server='Hermes' AND status='closed' AND close_reason='HL_CLOSED'
GROUP BY token, direction ORDER BY COUNT(*) DESC LIMIT 20;
-- HL fills from last 7 days:
-- from hyperliquid_exchange import get_trade_history
-- fills = get_trade_history(start_ms, end_ms)
-- hl_closes = Counter(f['coin'] for f in fills if f.get('side') == 'B')
```

### Find paper=False trades with hl_entry_price=0 (unconfirmed)
```sql
SELECT id, token, direction, pnl_pct, entry_price, hl_entry_price,
       close_reason, is_guardian_close, paper, entry_timing
FROM trades
WHERE server='Hermes' AND status='closed'
  AND paper=False AND (hl_entry_price=0 OR hl_entry_price IS NULL)
ORDER BY id;
```

### Current open trades vs HL positions
```python
from hyperliquid_exchange import get_open_hype_positions_curl
hl_pos = get_open_hype_positions_curl()  # {TOKEN: {'size': ..., 'entry_px': ..., 'direction': ...}}
hl_tokens = set(k.upper() for k in hl_pos.keys())
# Compare to: SELECT * FROM trades WHERE server='Hermes' AND status='open'
```

## Service Restart Requirement
**Python code changes to `brain.py`, `hl-sync-guardian.py`, or `decider_run.py` require restarting the relevant systemd service:**
```bash
sudo systemctl restart hermes-pipeline     # for brain.py and decider_run.py
sudo systemctl restart hermes-hl-sync-guardian  # for hl-sync-guardian.py
```
The pipeline runs every minute, guardian every 2 minutes. After restart, wait 1-2 guardian cycles (~2-4 min) before checking results.

## Archive and Clean Pattern
```python
import psycopg2, json
from datetime import datetime

BRAIN_DB = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}
conn = psycopg2.connect(**BRAIN_DB)
cur = conn.cursor()

# Archive
cur.execute("SELECT ... FROM trades WHERE ...")
archive_path = f'/root/.hermes/data/archive_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with open(archive_path, 'w') as f:
    json.dump({'archived_at': datetime.now().isoformat(), 'trades': [...]}, f, default=str)
print(f"Archived: {archive_path}")

# Delete
cur.execute("DELETE FROM trades WHERE ...")
conn.commit()
conn.close()
```

## Key Files
- `/root/.hermes/scripts/brain.py` — trade creation and HL mirroring
- `/root/.hermes/scripts/hl-sync-guardian.py` — guardian close logic (Step 8), fill cache, PHANTOM_CLOSE retry
- `/root/.hermes/scripts/decider_run.py` — entry point for signals, duplicate-entry guard
- `/root/.hermes/data/archive_closed_trades_*.json` — archived trade history

## Additional Fixes

### Fix I — `guardian-missing-tracking.json` staleness causing phantom closes
**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

`guardian-missing-tracking.json` accumulates tokens **indefinitely** across guardian cycles. When a trade is closed, the token remains in the tracking file forever. The 2-miss counter accumulates from historical cycles. New trades for the same token immediately get caught in the trap.

**The cascade:** Trade closes → token stays in missing_tracking → guardian Step 5 keeps signaling to close it → new trade opens → immediately in missing_tracking with accumulated miss count → guardian closes it as phantom.

**Fix:** Clear and rebuild `missing_tracking` at the **start** of each guardian cycle:
```python
# At the start of guardian main loop — DON'T load persisted state:
missing_state = {}  # Fresh start each cycle
```

### Fix J — `acquire_lock()` stale lock in `ai_decider.py`
**File:** `/root/.hermes/scripts/ai_decider.py`

`ai_decider` uses its own `acquire_lock()` function — **separate** from `FileLock` in `hermes_file_lock.py`. When killed mid-run, the lock file persists. Subsequent runs fail immediately without cleaning the stale lock. This caused `hotset.json` to go **40+ minutes stale**, blocking all new trade approvals.

**Note:** `ai_decider` and `decider_run` are **two separate scripts** that independently race on `ai_decider.lock` via `fcntl.flock`. Neither calls the other as subprocess.

**Fix:** Delete stale lock **before** acquiring in `acquire_lock()`:
```python
try:
    if os.path.exists(LOCK_FILE):
        os.unlink(LOCK_FILE)  # Clean stale lock FIRST
except: pass
_lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
```

### Fix K — ATR→HL sync disabled (rate limit savings)
**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

ATR→HL TP/SL sync ate ~720+ API calls/hour (6 positions × 2 calls × 60 cycles). HL has ~74k request/hour limit. Disabled HL sync, keep DB persistence for dashboard.

### Fix L — `every_10` guard removed from pipeline
**File:** `/root/.hermes/scripts/run_pipeline.py`

When adding the psutil process guard, `if every_10:` was accidentally removed from around the 10-min steps loop. ai_decider ran **every minute** instead of every 10 minutes. Restore the guard:
```python
if every_10:  # Only when minute % 10 == 0
    import psutil
    for step in STEPS_EVERY_10M:
        # process guard...
        run(step)
```

### Fix M — Hot-set staleness tolerance too tight
**File:** `/root/.hermes/scripts/decider_run.py`

`decider_run` blocked approvals when hotset.json > 11 min old. ai_decider can take 5+ min (LLM call) + runs every 10 min = 15 min normal age. Increased from 660s to 1200s (20 min).

### Fix F — Stale dashboard (trades.html shows old SL/TP values)
Guardian ATR updates DB every 30s but `trades.json` is only written by the pipeline every 60s. Dashboard shows values up to 59s stale.

**Fix:** `_update_trades_json_atr()` in guardian writes ATR SL/TP to `trades.json` immediately after each ATR DB persist:
```python
def _update_trades_json_atr(db_by_token: dict):
    # Reads current trades.json, updates sl/tp/current/pnl_pct for matching tokens, writes back
```

### Fix G — TP never sent to HL
`reconcile_tp_sl` only sent SL updates to HL, never TP. XRP and other positions had no TP on HL.

**Fix:** `_place_or_replace_tp()` — checks for existing TP on HL, places or replaces it:
```python
def _place_or_replace_tp(coin, direction, new_tp_price, size) -> dict:
    tp_oid = _find_open_trigger_order(coin, "tp")[0]
    if tp_oid is None:
        return place_tp(coin, direction, tp_rounded, size)
    else:
        return replace_tp(coin, direction, tp_rounded, size)
```
Call it in `reconcile_tp_sl` after each SL update.

## Symptoms and对应的Fix
| Symptom | Fix |
|---------|-----|
| guardian closes a trade (HL_SL_CLOSED or PHANTOM_CLOSE) but new trade opens immediately with no cooldown | Fix N+ — add `set_loss_cooldown()` calls in hl-sync-guardian.py at close_reason assignment points |
| Trade recorded as `atr_sl_hit` but TP/SL were never actually sent to HL — HL position closed by guardian as `guardian_orphan` instead | Mirror-close failure: position_manager closed DB (commit) before HL `mirror_close()` succeeded, then guardian found orphan and closed it with `guardian_orphan` but DB already had `atr_sl_hit`. Also: signal arrived with SL=0.0000/TP=0.0000 — sanity check tried to reset to 1% but order already submitted to HL with zeros |
| `mirror_close FAILED (DB committed, HL still open)` in pipeline log — DB says closed, HL still has position | position_manager closed DB then called `mirror_close()` — if HL API fails (rate limit, order state), DB stays committed but HL stays open. Guardian's orphan detection then closes HL and records `guardian_orphan`. The DB's original `close_reason` (atr_sl_hit, manual_close, etc.) is never corrected |
| Trade shows close_reason=atr_sl_hit but TP/SL not actually hit — guardian log shows guardian_orphan for same trade | Guardian Step 6 6-second sleep gap race — guardian closes HL first, PM closes DB first during the gap. See "Pattern: Guardian Step 6 — PM Closes DB First During Guardian's 6-Second Fill-Wait Gap" |
| DB has more closes than HL fill history (5-36x ratio) | Fix A (brain.py) |
| PHANTOM_CLOSE with exit_price=0 | Fix B (guardian) + Fix D (backfill) |
| HL_CLOSED but hl_entry_price=0 | Fix B (guardian) |
| Same token appears 10+ times in closed trades | Fix E (duplicate-entry guard) |
| Guardian creates orphan with signal=NULL for a trade that was already closed (HL close order pending/failed) | Fix Nx (HL-first in close agents) + Fix N (pending closes set) + Fix Nb (preserve signal in INSERT) |
| profit-monster closes DB but HL position remains → guardian creates phantom duplicate | Fix Nx (HL-first in profit-monster.py) |
| Two API calls per close in guardian logs | Fix C (fill cache) |
| trades.html shows stale SL/TP values | Fix F (guardian writes trades.json) |
| No TP on HL for open positions | Fix G (TP to HL) |
| Trade closed at entry price with wrong reason (TP triggered but wasn't) | Fix O-1 (guardian entry validation + MUST recalculate TP/SL on stale refresh) |
| hotset.json 40+ min stale, decider_run blocking new approvals | Fix J (acquire_lock cleans stale) |
| ATR→HL sync eating rate limits ("Too many requests") | Fix K (HL sync disabled) |
| ai_decider running every minute instead of every 10 min | Fix L (every_10 guard restored) |
| decider_run blocking approvals despite healthy hot-set | Fix M (20 min staleness tolerance) |
| New standalone trading system (pump_hunter) being accidentally closed/managed by guardian or PM | Pattern: "New Independent Trading System" — label trades with distinct `signal`, exclude from guardian duplicate guard + PM get_open_positions query |

### Fix N+ — Loss cooldowns not recorded when guardian closes trades via HL_SL_CLOSED or PHANTOM_CLOSE
**File:** `/root/.hermes/scripts/hl-sync-guardian.py`

**Symptom:** A trade closes via guardian (HL_SL_CLOSED or PHANTOM_CLOSE) — a confirmed loss — but no loss cooldown is recorded. The decider immediately opens a new trade for the same token+direction with no cooldown block.

**Root cause:** `position_manager.py` only calls `set_loss_cooldown()` in `_check_atr_tp_sl_hits()` (ATR stops). Guardian closes trades via `HL_SL_CLOSED` or `PHANTOM_CLOSE` — neither triggers `set_loss_cooldown()`. The loss cooldown system is completely bypassed for HL-native closes.

**Timeline of the FIL bug:**
```
00:17:59  Guardian closes FIL #6687 as HL_SL_CLOSED (loss) ← set_loss_cooldown NOT called
00:22:00  Pipeline decider sees no cooldown for FIL SHORT
00:22:00  New FIL SHORT #6691 opened immediately
```

**Fix:** In `hl-sync-guardian.py`, add `set_loss_cooldown()` calls at the same points where `close_reason` is set to `HL_SL_CLOSED` or `PHANTOM_CLOSE`:

```python
from position_manager import set_loss_cooldown

# At lines ~3221, ~3228, ~3235, ~3303, ~3310
# When setting close_reason = 'HL_SL_CLOSED' or 'PHANTOM_CLOSE':
if close_reason in ('HL_SL_CLOSED', 'PHANTOM_CLOSE'):
    set_loss_cooldown(tok, direction)
```

**Key lines in hl-sync-guardian.py to patch:**
- Line 3221: `close_reason = 'PHANTOM_CLOSE'` (in Step 8 paper=True block)
- Line 3228: `close_reason = 'HL_SL_CLOSED'` (LONG, exit_price <= sl)
- Line 3235: `close_reason = 'HL_SL_CLOSED'` (SHORT, exit_price >= sl)
- Line 3303: `close_reason = 'HL_SL_CLOSED'` (in the `guardian_closed=TRUE` fallback path, LONG)
- Line 3310: `close_reason = 'HL_SL_CLOSED'` (in the `guardian_closed=TRUE` fallback path, SHORT)

**Verification query:**
```sql
-- After guardian closes, check loss_cooldowns.json
cat /var/www/hermes/data/loss_cooldowns.json
-- FIL:SHORT should appear if the close was a loss

-- Also verify by PnL: losses should have cooldown, wins should not
SELECT token, direction, close_reason, pnl_pct, entry_price, exit_price
FROM trades WHERE close_reason IN ('HL_SL_CLOSED', 'PHANTOM_CLOSE')
ORDER BY close_time DESC LIMIT 10;
```

### Fix H — Delete-and-recreate for stale TP/SL orders on HL
**File:** `/root/.hermes/scripts/hyperliquid_exchange.py`

HL sometimes rejects `replace_sl` with "Invalid TP/SL price" for orders in bad state (stale OID, already filled, etc.). The fix: cancel the bad order, then place fresh:

```python
if result.get("status") == "err":
    err_msg = result.get("response", "Unknown HL error")
    if "Invalid TP/SL price" in str(err_msg):
        # Try cancel then place fresh
        cancel_result = exchange.cancel_order(coin, oid)
        return place_sl(coin, direction, new_px, sz)
    return {"success": False, "error": err_msg, ...}
```

## Rate Limit Issues
HL rejects operations with "Too many cumulative requests sent" — not a price/logic error. The ATR→HL sync was a major consumer (~720 calls/hour). Disable it (Fix K). BTC SL stuck at old value because `replace_sl` is rate-limited. Reduce guardian cycle frequency or wait for quota to reset.

Key error messages from HL:
- `"Too many cumulative requests sent (80683 > 74530)"` — API quota exceeded
- `"Invalid TP/SL price. asset=0"` — rate limit rejection, not a price problem

## Pattern: Guardian Step 6 — PM Closes DB First During Guardian's 6-Second Fill-Wait Gap

**Symptom:** Trade shows `close_reason=atr_sl_hit` in DB, but neither TP nor SL was actually hit. Guardian log shows `guardian_orphan` for the same trade. No TP/SL breach occurred — the wrong system closed the trade first.

**Root Cause — Timing Race in Guardian Step 6:**

Guardian's orphan close sequence in Step 6 has a 6-second gap between closing the HL position and closing the DB trade:

```
Guardian Step 6 for orphan token X:
  1. close_position_hl(X)         ← HL position closed immediately ✓
  2. time.sleep(6)                ← WAIT 6s for HL fills to confirm
  3. _close_orphan_paper_trade_by_id(...)  ← DB trade closed HERE
```

During that 6-second gap, position_manager runs (pipeline is every 1 min, guardian is every 2 min — they overlap frequently) and sees the DB trade as still open. It closes the DB trade with `close_reason=atr_sl_hit` (wrong reason, TP/SL not actually hit).

When guardian's Step 6 finally runs `_close_orphan_paper_trade_by_id`, it finds the trade already closed and skips it.

**Timeline Example (ETH, 15:42 EST):**
```
15:42:04  Pipeline: ETH opens, brain.py writes trade #7852 to DB as 'open'
15:42:08  Guardian: sees ETH in HL but NOT in DB → orphan. Closes HL as guardian_orphan
15:42:09  Guardian: sleep(6) starts — DB trade still open
15:42:13  PM runs: sees trade #7852 'open' in DB → closes as "atr_sl_hit" ← WRONG REASON
15:42:15  Guardian: sleep ends, tries to close DB trade → already closed by PM → SKIPS
```

**Result:** DB says `atr_sl_hit`, HL says `guardian_orphan`. Neither TP nor SL was hit.

**The Fix:**

The DB close must happen IMMEDIATELY after the HL close, not 6 seconds later. The 6-second sleep is to wait for HL fill confirmation — but the DB write doesn't need that wait. Restructure Step 6:

```python
# CURRENT (race window):
success = close_position_hl(coin, 'guardian_orphan')
if success:
    time.sleep(6)  # ← GAP: PM can close DB trade during these 6 seconds
    _close_orphan_paper_trade_by_id(...)  # DB close happens too late

# FIXED (no race window):
success = close_position_hl(coin, 'guardian_orphan')
if success:
    # Close DB trade IMMEDIATELY with placeholder exit price
    # Use entry price as temporary exit price — will be corrected after fills confirm
    _close_orphan_paper_trade_by_id(orphan_id, entry_price, 'guardian_orphan')
    time.sleep(6)  # Wait for HL fills
    # Backfill real exit price and PnL from fill cache
    _backfill_phantom_close_fills(orphan_id, coin)
```

Alternatively, use a `_PENDING_HL_CLOSE` in-memory set to communicate between threads/processes: when guardian closes HL, add the token to `_PENDING_HL_CLOSE`. When PM runs, check this set and skip the DB close for tokens in it.

**Also:** PM's `check_atr_tp_sl_hits` should check whether HL actually has the position before closing the DB trade. If guardian has already closed HL (token in `_CLOSED_HL_COINS` or `_PENDING_HL_CLOSE`), PM should not close the DB trade — let guardian handle it.

## Pattern: `mirror_close` Failure → DB Committed, HL Still Open → Wrong `close_reason`

**Symptom:** Trade recorded in trades.json with `close_reason=atr_sl_hit` (or other reason), but guardian later closed the same position on HL as `guardian_orphan`. Pipeline log shows `mirror_close FAILED (DB committed, HL still open)`.

**Root cause chain:**
1. Signal executes with SL=0.0000/TP=0.0000 (ATR not yet computed, or stale tpsl_self_close record)
2. `decider_run` sends order to HL with zero SL/TP — HL has no stops
3. Position opens on HL, position_manager ATR engine closes it immediately (same bar/candlestick, ~3 seconds)
4. DB commit happens BEFORE `mirror_close()` succeeds — if HL API is rate-limited or the order is in a bad state, `mirror_close` fails
5. Guardian next cycle: HL has position, DB says closed → orphan detected → closes as `guardian_orphan`
6. DB keeps its original `close_reason` (atr_sl_hit) — misleading

**Also:** SL sanity check may fire AFTER the order is already sent to HL with SL=0:
```
[WARN] SL sanity check triggered for SHORT XRP, reset to 1%
```
→ appears AFTER `EXEC: XRP SHORT @ $1.415850 SL=$0.0000` in the same pipeline log second

**Diagnostic — XRP example (2026-04-27 06:50):**
```
06:50:05 EXEC: XRP SHORT @ $1.415850 conf=99% SL=$0.0000 TP=$0.0000
06:50:05 [WARN] SL sanity check triggered for SHORT XRP, reset to 1%
06:50:07 Closed trade (atr_sl_hit) — same bar, SL was never on HL
06:50:13 mirror_close FAILED (DB committed, HL still open)
06:50:10 Guardian: Orphans (HL only): ['XRP']
06:50:11 Guardian: ✅ XRP closed (guardian_orphan)
```

**Fix needed (UNAPPLIED — 2026-04-27):** `mirror_close` failure should NOT commit the DB close until HL confirms. But there's a deeper problem: `check_atr_tp_sl_hits` in `position_manager` can fire in the SAME pipeline cycle that the trade opened — before `_collect_atr_updates` has set any SL/TP. The trade closes with `atr_sl_hit` (SL was 0, so any price above entry triggers the SHORT condition) while HL hasn't even confirmed the position exists yet. Guardian later closes HL as `guardian_orphan`.

Root cause sequence for XRP SHORT @ 06:50:04 (confirmed 2026-04-27):
1. 06:50:04 — Pipeline opens trade via brain.py. HL confirms immediately. Entry=1.4165.
2. 06:50:05 — Position Manager sees XRP SHORT in open positions. ATR SL/TP have NOT been computed yet (that happens at step 2395, after refresh_current_prices).
3. `check_atr_tp_sl_hits` fires — but wait, it should skip if SL=0 (`if not sl or not tp: continue`). So how did it close?
   → **The close was NOT from check_atr_tp_sl_hits.** The trade closed at 06:50:07 (2s after open) — before position_manager even ran. Something else closed it.
   → Possible: cascade_flip, wave_turn, or a direct DB write. Investigating.

Fix requires BOTH:
(a) Guard `check_atr_tp_sl_hits` with an `is_new_trade` flag (e.g., skip if position age < 60s) to prevent ATR from firing before it's even computed
(b) Only commit DB close AFTER `mirror_close` succeeds — or revert on failure

## The `***` Masking Bug — When trades.json Shows Masked Tokens

If `cat -v /var/www/hermes/data/trades.json` shows `***` but `python3 -c "import json; print(json.load(open(f))['open'][0]['coin'])"` shows the real token name — the file was written with corrupted data (likely the `SOLANA_ONLY_TOKENS=***` set somehow interfered with the writer).

**Diagnosis:**
```bash
# Check raw bytes — shows *** literally
head -c 500 /var/www/hermes/data/trades.json | cat -v

# Check parsed JSON — shows real names
python3 -c "import json; d=json.load(open('/var/www/hermes/data/trades.json')); print([t['coin'] for t in d['open']])"
```

**Fix:** Run the writer script to regenerate the file cleanly. If the masking recurs, the writer code itself may be using a `SOLANA_ONLY_TOKENS=***` set directly in the output path.

**Prevention:** Rename the JSON field (`token` → `coin`) so the writer path is different and doesn't hit the masked code path.

## Important Debugging Notes

**Two independent lock holders for hot-set decisions:**
- `ai_decider` (pipeline step, runs every 10 min, LLM compaction)
- `decider_run` (pipeline step, runs every 1 min, trade decisions)
Both independently acquire `ai_decider.lock` via `fcntl.flock`. If one hangs (LLM rate limit), the other is also blocked. `decider_run` will block new trade approvals when hot-set is stale (Fix M).

**Missing tracking is per-cycle, not persistent:**
Tokens stay in `missing_tracking` for the duration of ONE guardian cycle. The file should NOT persist across cycles. Clear it at cycle start (Fix I) to prevent stale historical data from phantom-closing new trades.
