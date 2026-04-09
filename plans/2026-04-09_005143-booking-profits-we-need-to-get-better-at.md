# Plan: ATR TP/SL Auto-Update + HL Closed-Position Detection

## Goal
Fix the broken ATR TP/SL lifecycle so that:
1. SL/TP are **always** ATR-based (no stale static values)
2. SL/TP **auto-update every minute** on HL
3. When HL closes a position via TP/SL, the **DB is updated** with correct exit reason
4. Pipeline continues uninterrupted

---

## Root Cause Analysis

### Problem 1: No 1-minute ATR SL/TP cron
- `run_pipeline.py` (which calls `position_manager` with ATR-based SL/TP updates) runs via `hermes-pipeline.timer` every **10 minutes** — not every minute
- `position_manager` step (lines 1061+) computes ATR-based SL/TP and pushes to HL
- 10-minute intervals are too slow; SL/TP need to trail price every minute

### Problem 2: Guardian Step 8 skips phantom paper trades
- `hl-sync-guardian.py` Step 8 (lines ~2588-2592): when a trade is **missing from HL** (HL closed it via TP/SL), the guardian **skips** it with `"externally closed"` warning
- Paper trades that exist in DB but not on HL are treated as "expected" (paper=True skip) — but the DB is **never updated** to mark them closed
- `hl-sync-guardian.service` (systemd) is **NOT running**; only `hype-paper-sync.timer` is active
- `hype-paper-sync.py` is a simpler sync script — it does NOT handle closed-position detection or update the DB

### Problem 3: `_HL_TICK_DECIMALS` wrong for CAKE and TRB
- CAKE: was 6, HL accepts max **4 decimals** (1.4374 works, 1.43744 fails) → fixed to 4
- TRB: was 6, HL accepts max **3 decimals** (14.934 works, 14.9342 fails) → fixed to 4
- This was causing CAKE/TRB SL/TP to fail with "Order has invalid price" — now fixed

### Problem 4: No exit reason tracking for HL-triggered closes
- When HL closes a position via TP or SL, the DB should record `close_reason='HL_TP_CLOSED'` or `close_reason='HL_SL_CLOSED'`
- Currently: DB never updated when HL closes a position (guardian skips)

---

## Fixes Applied During Investigation

### Fix 1: `_HL_TICK_DECIMALS` corrected
File: `hyperliquid_exchange.py`
- CAKE: 6 → 4 (verified: 1.4374 works, 1.43744 fails)
- TRB: 6 → 3 (verified: 14.934 works, 14.9342 fails)

### Fix 2: `_hl_tick_round` float precision
File: `hyperliquid_exchange.py`
- Old: `Decimal.normalize()` could shift trailing digits (e.g. 1.445 → 1.4449999)
- New: `ROUND_HALF_UP` quantization returns clean float — verified mod-1e-6 ≈ 0

### Fix 3: All live positions synced with correct SL/TP
- Pushed fresh ATR-based SL/TP to HL for: CAKE, TRB, ETH, LINK, PENDLE, ENS
- Updated paper DB `stop_loss` and `target` for all live positions

---

## Remaining Fixes

### Fix 4: Create `hermes-atr-sl-updater.timer` (1-minute cron)
**File:** `/etc/systemd/system/hermes-atr-sl-updater.timer` + `.service`

The ATR SL/TP updates need to run **every minute**, not every 10 minutes.

```
# hermes-atr-sl-updater.timer
[Unit]
Description=Hermes ATR SL/TP Updater — every 1 minute
[Timer]
OnBootSec=30
OnCalendar=*:*:00   # every minute at second 0
Unit=hermes-atr-sl-updater.service
[Install]
WantedBy=timers.target
```

Service runs `run_pipeline.py` but only the `position_manager` step actually does SL/TP updates. However, the full pipeline is fine to run every minute (it's lightweight).

**Validation:** After creating, run `systemctl daemon-reload && systemctl enable --now hermes-atr-sl-updater.timer` and verify with `systemctl list-timers`.

---

### Fix 5: Fix Guardian Step 8 to close phantom paper trades with proper reason
**File:** `hl-sync-guardian.py` around lines 2588-2600

**Current (broken) logic:**
```python
# Paper trades missing from HL → skip (DB never updated)
if t.get('paper') == True:
    continue  # ← BUG: never closes the paper trade in DB
```

**Fix:** When a paper trade is missing from HL:
1. Get exit price from HL fills (via `_get_hl_exit_price`)
2. Determine if it was TP or SL (from HL fills or price comparison)
3. Call `_close_paper_trade_db(trade_id, tok, exit_price, 'HL_TP_CLOSED')` or `'HL_SL_CLOSED'`

**Approach:** Add a new helper `_close_paper_trade_missing_hl()` that:
- Fetches HL fills for the token to determine actual exit price
- Determines exit reason: if exit_price >= TP → `HL_TP_CLOSED`, if exit_price <= SL → `HL_SL_CLOSED`, else `HL_POSITION_CLOSED`
- Calls `_close_paper_trade_db` with appropriate reason
- Sets `guardian_closed=TRUE` before closing to prevent double-close

**Also:** Start `hermes-hl-sync-guardian.service` so it runs continuously:
```
systemctl enable --now hermes-hl-sync-guardian.service
```

---

### Fix 6: Handle NIL and AAVE phantom positions
These trades were opened on HL (fills confirmed), then closed by static TP. The DB still shows them as open because:
- Guardian skipped them (paper=True)
- `guardian_closed=FALSE` means they're still "open" in DB

**Action:** Manually update their `guardian_closed` flag or close them with `HL_TP_CLOSED` reason using the actual fill prices.

Current HL fill prices:
- NIL SHORT: entry=0.035012, TP was hit at ~0.033881 (from fills)
- AAVE SHORT: entry=91.787, TP was hit at ~89.803 (from fills)

---

### Fix 7: Update `hype_live_trading.json` if needed
If live trading is enabled, the guardian should be aware. Check current state and ensure the flag is correct.

---

## Files to Change

1. **`/etc/systemd/system/hermes-atr-sl-updater.timer`** — new file
2. **`/etc/systemd/system/hermes-atr-sl-updater.service`** — new file
3. **`/root/.hermes/scripts/hl-sync-guardian.py`** — Step 8 fix + exit reason tracking
4. **`/root/.hermes/scripts/position_manager.py`** — (no changes needed, already correct)
5. **`/root/.hermes/scripts/hyperliquid_exchange.py`** — already patched (_HL_TICK_DECIMALS + _hl_tick_round)

---

## Verification Steps

1. **Verify ATR SL/TP is updating every minute:**
   - Check `systemctl list-timers | grep atr-sl-updater`
   - Watch HL open orders change after each minute

2. **Verify phantom trades are closed in DB:**
   - `SELECT token, status, close_reason FROM trades WHERE token IN ('NIL','AAVE','CFX','LAYER') AND status='open';`
   - After guardian fix: should return 0 rows

3. **Verify close_reason is set correctly:**
   - After HL-triggered close: `SELECT close_reason FROM trades WHERE token='ETH' ...`
   - Should be `HL_TP_CLOSED` or `HL_SL_CLOSED`, not `MANUAL_CLOSE`

4. **Verify new positions are closed correctly when HL TP/SL hits:**
   - Monitor `sync-guardian.log` for "Step8 closing" entries
   - Monitor `pipeline.log` for ATR updates

---

## Risks and Tradeoffs

- **Risk:** Running pipeline every minute might hit rate limits on HL API. Mitigation: the pipeline has internal rate limiting; `position_manager` is lightweight (no signal_gen).
- **Risk:** Guardian closing trades while decider is simultaneously opening new ones. Mitigation: guardian has `_CLOSED_THIS_CYCLE` dedup and 30s cooldowns.
- **Open Question:** Should we detect TP vs SL from HL fills? The fills only show the trigger price, not which order type. We can infer from: if exit_price >= TP → TP hit, if exit_price <= SL → SL hit.
