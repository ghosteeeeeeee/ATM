# ATR Issues — Disable HL TP/SL Orders + Bulletproof Internal ATR Tracking

## Goal

Disable all HL (Hyperliquid) close/profit TP/SL order placement. The system should **self-manage ATR TP/SL entirely internally** — detect hits via price checks, close positions in the DB, and mirror closes to HL only via emergency market order (not pre-placed TP/SL orders). This removes the broken HL TP/SL close order path that's been causing failures.

---

## Current Architecture

### How ATR TP/SL Works Today

1. **Entry** (`decider_run.py` → `execute_trade`): Trade enters with `sl_pct` and `tp_pct` (ATR-based distances stored in DB)
2. **HL Order Placement** (`brain.py` line ~417): After entry, system places TP and SL trigger orders on HL via `place_tp()` and `place_sl()`
3. **ATR Hit Detection** (`position_manager.py` `check_atr_tp_sl_hits()`): Every cycle, price is checked against SL/TP levels in the DB
4. **Close on Hit** (`position_manager.py` line ~1900): If ATR hit detected → `close_paper_position(trade_id, 'atr_sl_hit'/'atr_tp_hit')` → DB closes + `mirror_close()` tries to close on HL
5. **mirror_close** (`hyperliquid_exchange.py` `close_position()`): Uses `exchange.market_close()` — reduce-only market order to close the HL position

### The Problem

The HL TP/SL order path is **broken and unreliable**:
- HL trigger orders fire late/miss fills in volatile markets
- Phantom positions: HL has positions Hermes thinks are closed (and vice versa)
- `mirror_close` fails partially — DB commits but HL close succeeds only ~60% of the time (BUG-17, BUG-22)
- Stale HL TP/SL orders fire AFTER a position is already closed internally, creating double-close chaos
- The `cancel_all_open_orders` cleanup on ATR hit (line ~969 in position_manager.py) is best-effort and frequently fails

**Evidence:** In the trade archives, `atr_sl_hit` and `atr_tp_hit` are in the BOGUS exclusion list — these closes had corrupted PnL math from HL/DB divergence.

### What Actually Works

- `check_atr_tp_sl_hits()` — **solid**, correctly compares current_price vs SL/TP
- `close_paper_position()` — **solid**, closes DB + mirrors to HL market order
- The internal price-tracking and hit detection is **already bulletproof**

### What Needs to Change

1. **Stop placing TP/SL close orders on HL** — these are the source of all evil
2. **Keep ATR TP/SL levels in DB only** — no HL trigger orders
3. **`check_atr_tp_sl_hits()` remains the execution path** — it already calls `close_paper_position()` which does the DB close + HL mirror
4. **Amplify the internal tracking** — make the internal system more robust so it never misses an ATR hit

---

## Proposed Changes

### Phase 1: Disable HL TP/SL Order Placement (Non-Breaking)

**Files:** `brain.py`, `decider_run.py`, `position_manager.py`

#### 1.1 Remove HL TP/SL order placement from trade entry

In `brain.py` (lines ~415-430), the code that calls `hl_place_sl()` and `hl_place_tp()` after a successful entry should be **commented out or removed**.

```python
# DISABLED (2026-04-10): Don't place TP/SL orders on HL — we self-manage ATR exits internally.
# The HL TP/SL order path is broken (phantom positions, stale orders, missed fills).
# Keeping ATR levels in DB only; check_atr_tp_sl_hits() handles detection + close.
# sl_result = hl_place_sl(hype_token, direction, float(sl_row[0]), float(sz))
# tp_result = hl_place_tp(hype_token, direction, float(sl_row[1]), float(sz)) if sl_row[1] ...
```

**Why not breaking:** If HL TP/SL orders are never placed, there's nothing to cancel when ATR hits. The internal system handles everything.

#### 1.2 Confirm `check_atr_tp_sl_hits()` is the sole ATR execution path

In `position_manager.py` (line ~1900), the ATR hit detection already:
- Detects the hit
- Calls `close_paper_position(trade_id, 'atr_sl_hit'/'atr_tp_hit')`
- Which closes DB + fires `mirror_close()` (HL market order)

This path is **already correct**. No changes needed here — just verify it handles all edge cases.

#### 1.3 Remove stale order cleanup code

The ATR cleanup block in `close_paper_position()` (lines ~967-982) calls `cancel_all_open_orders` on ATR hit — **this becomes unnecessary** if we never place HL TP/SL orders in the first place.

Comment out or remove:
```python
# DISABLED (2026-04-10): No HL TP/SL orders to cancel — we don't place them anymore.
# if reason in ('atr_sl_hit', 'atr_tp_hit'):
#     try:
#         from hyperliquid_exchange import cancel_all_open_orders as _cancel_all
#         cleanup = _cancel_all(hype_token)
#         ...
```

### Phase 2: Bulletproof Internal ATR Tracking

**Files:** `position_manager.py`

#### 2.1 Add redundant price sources to `check_atr_tp_sl_hits()`

Currently the function relies on `current_price` from the position dict. Add fallback price fetching:

```python
def check_atr_tp_sl_hits(open_positions: List[Dict]) -> List[Dict]:
    # ... existing logic ...
    
    # If current_price is missing/stale, try to get fresh price
    if not current_price or current_price <= 0:
        try:
            from hyperliquid_exchange import get_price
            fresh = get_price(token)
            if fresh:
                cur = float(fresh)
        except:
            pass  # keep going with what we have
```

#### 2.2 Log every ATR check cycle

Add logging so we can see every cycle's price vs SL/TP (for debugging why some hits were missed):

```python
# Inside the loop, before the hit check
log(f"  [ATR CHECK] {token} {direction}: price={cur:.6f} SL={sl:.6f} TP={tp:.6f}")
```

#### 2.3 Record ATR levels at entry time with timestamps

When a trade opens, store `atr_sl_price`, `atr_tp_price`, and `atr_checked_at` in the trades DB so we can audit whether the system was checking correctly after-the-fact.

Add columns if needed:
```sql
ALTER TABLE trades ADD COLUMN atr_sl_price REAL;
ALTER TABLE trades ADD COLUMN atr_tp_price REAL;
ALTER TABLE atr_check_log (new table) — timestamp, token, price, sl, tp, hit_detected
```

#### 2.4 Add a heartbeat/last-check timestamp per position

Track when each open position was last checked for ATR hits:

```python
# In the main manage-open-positions loop
for pos in open_positions:
    pos['_last_atr_check'] = datetime.now(timezone.utc)
    # Store back to DB
    cur.execute("UPDATE trades SET last_atr_check = %s WHERE id = %s", 
                (datetime.now(timezone.utc), trade_id))
```

This enables post-mortems: "was the ATR check running every cycle or did it stall?"

### Phase 3: Remove/Disable HL TP/SL Order Utilities

**Files:** `batch_tpsl_rewrite.py`, `hyperliquid_exchange.py`

#### 3.1 batch_tpsl_rewrite.py — disable or make no-op

If this script is cron-scheduled to rewrite HL TP/SL orders, disable the cron. The script should either:
- Become a pure DB-level TP/SL updater (no HL placement), OR
- Be disabled entirely

Check cron:
```bash
crontab -l | grep tpsl_rewrite
# or
systemctl list-timers | grep tpsl
```

#### 3.2 Document that `place_tp()`, `place_sl()`, `place_tp_sl_batch()` are deprecated

Add deprecation warnings to these functions in `hyperliquid_exchange.py`:
```python
def place_tp(coin: str, direction: str, tp_price: float, size: float) -> dict:
    """
    DEPRECATED (2026-04-10): HL TP/SL orders are no longer used.
    ATR TP/SL is managed internally via check_atr_tp_sl_hits().
    This function is kept for emergency manual use only.
    """
```

---

## Files Likely to Change

| File | Change |
|------|--------|
| `brain.py` (~line 415) | Comment out `hl_place_sl()` and `hl_place_tp()` calls |
| `position_manager.py` (~967) | Remove/disable `cancel_all_open_orders` ATR cleanup block |
| `position_manager.py` (~360) | Enhance `check_atr_tp_sl_hits()` with fallback prices + logging |
| `batch_tpsl_rewrite.py` | Disable cron or make no-op |
| `hyperliquid_exchange.py` | Add deprecation warnings to `place_tp/sl` |
| `ATM-Architecture.md` | Update architecture docs to reflect new flow |
| `brain/trading.md` | Document the change |

---

## Step-by-Step Implementation Plan

1. **Read-only audit first** — confirm cron jobs for `batch_tpsl_rewrite.py` and any other TP/SL rewriting
2. **Comment out HL TP/SL placement in brain.py** — entry-side changes only
3. **Remove ATR cleanup block in position_manager.py** — the `cancel_all_open_orders` call
4. **Enhance `check_atr_tp_sl_hits()`** — fallback price, logging, timestamp tracking
5. **Add DB columns** for `atr_sl_price`, `atr_tp_price`, `last_atr_check` (optional but recommended)
6. **Disable cron for batch_tpsl_rewrite** — `crontab -e` or `systemctl disable`
7. **Add deprecation warnings** to `place_tp()`, `place_sl()` in hyperliquid_exchange.py
8. **Update ATM-Architecture.md** to reflect the new flow
9. **Paper test run** — let it run for 1 hour, verify no HL TP/SL orders are being placed
10. **Monitor** — watch for ATR hits being detected and closed correctly

---

## Tests / Validation

### Before
```bash
# Check if HL TP/SL orders are being placed
grep -n "place_tp\|place_sl" /root/.hermes/scripts/brain.py
# Should show commented-out or removed lines

# Check ATR cleanup block
grep -n "cancel_all_open_orders" /root/.hermes/scripts/position_manager.py
# Should be commented out
```

### After
```bash
# Verify no HL TP/SL orders for new trades
# Watch the decider run logs — no "place_tp" or "place_sl" messages

# Force an ATR hit (paper trading):
# Manually set a trade's stop_loss to current price - tiny amount
# Run position_manager check cycle
# Verify trade closes with reason='atr_sl_hit'

# Check DB: no open HL TP/SL orders should exist for paper trades
# (query hyperliquid API if possible)

# Verify ATR check logging:
# Run position_manager and grep for "[ATR CHECK]"
# Should see price vs SL/TP every cycle
```

---

## Risks and Tradeoffs

### Risk: We No Longer Have HL-Side TP/SL Protection
**Impact:** If Hermes stalls (process crash, network outage), a trade could run away without a HL trigger order to catch it.
**Mitigation:** The `hype_live_trading.json` kill switch + guardian process are still active. For extended outages, the guardian's own circuit breakers should fire. Also: the internal ATR check runs every cycle (~30s), so outage window is small.

### Risk: Existing Open Trades Have Stale HL TP/SL Orders
**Impact:** Old trades opened before this change still have HL TP/SL orders on the books.
**Mitigation:** Run `cancel_all_open_orders` once for all currently open tokens to clean up. Then the new system takes over cleanly.

### Risk: `mirror_close()` Still Uses HL Market Order
**Impact:** The market order close in `mirror_close()` could still fail.
**Mitigation:** This is separate from TP/SL orders — it's the final emergency close. BUG-17/22 already addressed this with retry logic. If it fails, `hype-sync` catches it next run.

### Open Question: What About Trailing Stop?
The archives showed **trailing exits are the best performer** (+$37.61 on SHORTs, 62% WR). Is the trailing stop actually removed? Or does `check_atr_tp_sl_hits()` also handle trailing? Need to verify the trailing stop state before making TP/SL changes.

---

## Verification Checklist

- [ ] `brain.py`: HL TP/SL placement commented out
- [ ] `position_manager.py`: ATR cleanup block commented out
- [ ] `check_atr_tp_sl_hits()`: has fallback price + logging
- [ ] `batch_tpsl_rewrite` cron disabled
- [ ] `place_tp/sl`: have deprecation warnings
- [ ] Stale HL orders cleaned up for existing positions
- [ ] ATM-Architecture.md updated
- [ ] 1-hour paper test run completed without HL TP/SL placement
