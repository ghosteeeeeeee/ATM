# DB/HL Reconciliation Bug — Trade Data Quality Issues
**Created:** 2026-04-14 18:00
**Status:** FIXES APPLIED — brain.py now deletes phantom paper trades at source, guardian marks unconfirmed closes as PHANTOM_CLOSE
**Focus:** Trades not making it to HL correctly; closed trades have wrong exit prices; duplicate entries; unusable data for analysis

---

## Problem Statement (from T)

> "The db and HL reconcile, there are still many trades that are either not making it to HL and being recorded in the db anyway, and the ones from HL that are closed are not done so correctly leaving us with unusable data for future analysis."

---

## Current Data Quality Issues (from DB analysis)

### Issue 1: Exit Price = Current Price (67 trades)
**Symptom:** `exit_price = current_price` (market price at time of query, not actual HL fill price)
**Root cause:** `_get_hl_exit_price()` in `hl-sync-guardian.py` polls `get_trade_history()` up to 3 times with 2s delay, then falls back to `fallback` param (current market price). When HL fills don't propagate within 6 seconds, guardian uses market price instead of actual fill price.
**Impact:** PnL is approximately correct but NOT the actual realized PnL. Makes backtesting unreliable.

### Issue 2: PHANTOM_CLOSE — Exit Price = 0 (5 trades)
**Symptom:** `exit_price = 0`, `pnl_pct = 0`, `close_reason = PHANTOM_CLOSE`
**Trades:** EIGEN LONG (ID=5161), SKY LONG (5162), LINK LONG (5164), XRP LONG (5165), BERA SHORT (4904)
**Root cause:** Guardian detects HL position gone but cannot find HL fill data after 3 polling attempts (6 seconds). Falls back to `fallback = 0.0` → `exit_price = 0`.
**Impact:** PnL = 0 for these trades. Total reported PnL is wrong by ~$0.92 (BERA -0.92%, EIGEN 0%, SKY 0%, LINK 0%, XRP 0%).

### Issue 3: Zero-PnL Trades (67 trades)
**Symptom:** `pnl_pct = 0` but trade is closed with a real close_reason (not PHANTOM_CLOSE)
**Examples:** LAYER SHORT (0%), TIA SHORT (0%), NOT SHORT (profit-monster 0%), many `histogram_zero_cross` entries
**Root cause:** `exit_price = entry_price` (unchanged) when the position was closed with essentially no price movement. These may be legitimate 0% moves but suggests the guardian is closing positions at stale prices.

### Issue 4: Duplicate PROVE Entries (12 trades for same token)
**Symptom:** PROVE has 12 closed trades all with slightly different entry prices (0.220-0.225)
**Pattern:**
- ID=4679, 4687, 4690, 4988, 5059, 4970, 5051, 5020, 5048, 5076 — all SHORT with entry ~0.221
- ID=5215 — SHORT with entry 0.2254, close_reason=atr_sl_hit
- ID=5362 — SHORT with entry 0.2254, close_reason=guardian_orphan
**Root cause:** System keeps re-entering the same token without properly closing the previous position first. The guardian's orphan close (`_close_paper_trade_db`) or the HL→paper reconciliation (`reconcile_hype_to_paper`) is not properly closing existing positions before new entries.
**Impact:** Multiple simultaneous positions on the same token, capital inefficiency, confusing P&L.

### Issue 5: guardian_orphan Closes with Wrong Exit Price
**Symptom:** `close_reason = guardian_orphan`, `is_guardian_close = True`, but `exit_price = current_price` (market price, not HL fill)
**Example:** MET SHORT (ID=5372) — exit=0.1359, current=0.1359, pnl=-0.295%
**Root cause:** `guardian_orphan` closes happen when paper has position but HL doesn't. Guardian closes at current market price but may not be getting the actual fill price.

### Issue 6: Entry Prices for ORPHAN_PAPER Trades
**Symptom:** 17 `ORPHAN_PAPER` trades with avg PnL = +1.436% (highest avg of any group)
**These are:** Trades that were in paper DB but HL never had the position. Guardian closed them. The +1.436% avg suggests these were profit targets hit before the guardian could reconcile.

---

## Root Cause Analysis

### Primary Root Cause: HL Fill Propagation Delay
The `_get_hl_exit_price()` function in `hl-sync-guardian.py` (lines 612-635):
```python
def _get_hl_exit_price(token: str, fallback: float = 0.0) -> float:
    for attempt in range(3):
        time.sleep(2)  # Only waits 6 seconds total
        fills = get_trade_history(...)
        # Only considers side='B' (close) fills
        if token_closes:
            return wavg_exit
    return fallback  # Returns market price or 0.0
```

**Problem:** HL fills can take up to 5 minutes to appear in `user_fills_by_time` (per BUG-16 comment in code). The guardian only polls for 6 seconds. When fills don't appear, it uses market price as exit.

**BUG-16 fix already attempted:** Changed lookback from 120s to 300s, but still only polls 3 times with 2s delay = 6 seconds total. The lookback window is 300s but if the fill hasn't propagated yet, the window is still empty.

### Secondary Root Cause: No Gap Detection Between HL and Paper
The reconciliation (`reconcile_hype_to_paper`) only handles:
1. HL position exists + paper doesn't → create orphan trade and close it
2. Paper position exists + HL doesn't → close paper as orphan
3. Both exist → update paper with HL data

But it does NOT handle:
- HL had a position, it closed, but paper never knew about it → PHANTOM_CLOSE
- Paper had a position, it was closed, but HL already closed it earlier → needs to find the HL fill

### Tertiary Root Cause: Token Re-Entry Without Close
When a new signal comes for a token that already has an open position, the system either:
1. Opens a second position (duplicate entries like PROVE)
2. Or the pipeline's signal→trade logic doesn't check for existing open positions

---

## Proposed Fix Plan

### Fix 1: Increase HL Fill Polling Window (High Priority)
**File:** `hl-sync-guardian.py`, `_get_hl_exit_price()` (line 612)

**Change:**
1. Increase polling from 3×2s = 6s to 15×10s = 150s (2.5 minutes)
2. This gives HL fills time to propagate without blocking the main loop excessively
3. Keep the 300s lookback window

```python
def _get_hl_exit_price(token: str, fallback: float = 0.0, timeout: int = 150) -> float:
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        time.sleep(10)  # Poll every 10s
        fills = get_trade_history(...)
        if token_closes:
            return wavg_exit
        log(f'  Fill poll attempt {attempt} — no close fills yet for {token}', 'WARN')
    log(f'  No HL close fills found for {token} after {timeout}s — using fallback', 'FAIL')
    return fallback
```

**Risk:** Increases guardian cycle time. Mitigation: run in background thread.

### Fix 2: Persistent Fill Cache (Medium Priority)
**File:** New table `hl_fill_cache` in PostgreSQL `brain` database

**Purpose:** Cache HL fills as they arrive, store exit prices for tokens that have closed. The guardian writes fills it sees, and subsequent queries can find them.

**Schema:**
```sql
CREATE TABLE hl_fill_cache (
    token TEXT, side TEXT, px REAL, sz REAL, closed_pnl REAL,
    fill_time TIMESTAMP, cached_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (token, side, fill_time)
);
```

**Usage:** When `_get_hl_exit_price` can't find fills immediately, check the cache first.

### Fix 3: Fix PHANTOM_CLOSE Exit Prices (High Priority)
**File:** `hl-sync-guardian.py` — add a retry mechanism for PHANTOM_CLOSE trades

**Change:** Add a `phantom_close_retry` table that tracks PHANTOM_CLOSE trades and retries HL fill lookup in subsequent guardian cycles. When fills finally arrive, update the trade record.

```python
# In guardian main loop:
# Check for any PHANTOM_CLOSE trades that can be updated
cur.execute("SELECT id, token FROM trades WHERE close_reason='PHANTOM_CLOSE' AND exit_price=0")
for trade_id, token in cur.fetchall():
    hl_exit = _get_hl_exit_price(token, fallback=0.0, timeout=60)
    if hl_exit > 0:
        # Update the PHANTOM_CLOSE trade with real exit price
        update_trade_exit(trade_id, hl_exit)
```

### Fix 4: Prevent Duplicate Entries (PROVE problem) (High Priority)
**File:** `hl-sync-guardian.py`, `reconcile_hype_to_paper()` or pipeline signal logic

**Change:** Before opening a new position for a token that already has an open paper trade:
1. Check if the token already has an open position in the DB
2. If yes, close the existing position first (at market or via HL fill)
3. Then open the new position

This requires understanding where the duplicate entries come from:
- If from the pipeline/guardian creating orphan trades → fix the orphan flow
- If from the ai_decider opening new positions → add dedup check

### Fix 5: Verify exit_price for guardian_orphan (Medium Priority)
**File:** `hl-sync-guardian.py`, `_close_paper_trade_db()` (line 1788)

**Change:** `guardian_orphan` closes should also try to get HL exit price. Currently they use `exit_price` passed in (which may be market price). Add HL fill lookup:

```python
def _close_paper_trade_db(trade_id, token, exit_price, reason):
    # Try to get HL exit price first
    hl_exit = _get_hl_exit_price(token, fallback=exit_price, timeout=30)
    # Use HL exit if available, otherwise use provided exit_price
```

---

## Files to Modify

| File | Change |
|------|--------|
| `hl-sync-guardian.py` | Fix 1, 3, 4, 5 — HL fill polling, PHANTOM_CLOSE retry, orphan handling |
| PostgreSQL `brain` | Fix 2 — add `hl_fill_cache` table |

---

## Testing / Validation

1. **Before Fix:** Run query showing exit_price issues
   ```sql
   SELECT token, close_reason, exit_price, current_price,
          CASE WHEN exit_price = current_price THEN 'BAD-FALLBACK' ELSE 'OK' END as quality
   FROM trades WHERE server='Hermes' AND status='closed'
   ORDER BY close_time DESC LIMIT 20
   ```

2. **After Fix:** Re-run query, should show much fewer fallback exits

3. **PHANTOM_CLOSE retry:** After fix deployed, PHANTOM_CLOSE trades should get real exit prices within 1-2 guardian cycles

4. **PROVE duplicates:** After fix, no token should have more than 1 open position at a time

---

## Open Questions

1. **Why does PROVE have 12 closed trades?** Is the system entering multiple positions, or is there a specific condition triggering re-entry?
2. **What is the actual HL fill for PHANTOM_CLOSE trades?** Can we look up the fill history manually for EIGEN/SKY/LINK/XRP/BERA to get the real exit prices?
3. **Is the 5-minute propagation delay documented by Hyperliquid?** Are there API options to get fills faster?
4. **Should we switch from polling to WebSocket fills?** Hyperliquid may have a WebSocket API for real-time fill notifications.

---

## Relevant Code Locations

- `hl-sync-guardian.py` line 612: `_get_hl_exit_price()` — the core HL fill lookup
- `hl-sync-guardian.py` line 570: `_poll_hl_fills_for_close()` — same pattern, 3×2s polling
- `hl-sync-guardian.py` line 1788: `_close_paper_trade_db()` — closes paper trades with exit_price calc
- `hl-sync-guardian.py` line 1934: `_close_orphan_paper_trade_by_id()` — closes specific orphan by ID
- `hl-sync-guardian.py` line 652: `reconcile_hype_to_paper()` — main reconciliation
- `hl-sync-guardian.py` line 469: `add_orphan_trade()` — creates orphan paper trade
