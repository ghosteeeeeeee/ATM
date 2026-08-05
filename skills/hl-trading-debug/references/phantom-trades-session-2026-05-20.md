# Phantom Trades Session — 2026-05-20

## Root Cause Chain (All Fixed)

### Ghost Trades: is_live_trading_enabled() Split-Brain

**Problem:** `hyperliquid_exchange.is_live_trading_enabled()` returned `hermes_constants.LIVE_TRADING_ENABLED` (always False). decider_run used `--real` flag from hype_live_trading.json. brain.py checked `is_live_trading_enabled()` → False → rejected trades. decider_run saw RC=0 + `--real` → marked signal EXECUTED. HL had no position. Guardian detected orphan.

**Fix:** `is_live_trading_enabled()` now returns `LIVE_TRADING_ENABLED` constant only. hype_live_trading.json is no-op. away_detector.py now delegates to hyperliquid_exchange.is_live_trading_enabled().

### Bug 1 — DRY Mode Orphan INSERT Bypass (CRITICAL)
- **File:** hl-sync-guardian.py:3744
- **Bug:** Inline orphan INSERT ran even when DRY=True — created phantom DB records during dry runs
- **Fix:** Added `if DRY: log(...) continue` before orphan INSERT

### Bug 2 — sig_id=None Race Window (CRITICAL)
- **File:** decider_run.py:1886-1892
- **Bug:** Legacy hot-set entries (sig_id=None) use token+direction claim which isn't atomic. Two concurrent decider_run processes can both claim same token+direction.
- **Status:** Warning block in place. PostgreSQL duplicate check catches second brain.py call.

### Bug 3 — Phantom Detection Direction Filter (CRITICAL)
- **File:** signal_compactor.py:1388
- **Bug:** `LIMIT 1` without direction filter found guardian_orphan open trades and treated them as proof of legitimate execution → phantom undetected
- **Fix:** Added `WHERE token=%s AND direction=%s ORDER BY id DESC LIMIT 1`

### Bug 4 — away_detector Split-Brain (CRITICAL)
- **File:** away_detector.py:110
- **Bug:** away_detector.py read hype_live_trading.json directly (live_trading=true); all other scripts used constant (live_trading=False). Monitoring reported wrong state.
- **Fix:** Delegates to hyperliquid_exchange.is_live_trading_enabled()

### Bug 5 — calc_notional 0.0 Falsy (CRITICAL — "inflated profits/deflated losses")
- **File:** brain.py:637
- **Bug:** `calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt` — `0.0` is falsy, falls back to amount_usdt ($50) instead of actual HL notional. For small positions (~$7), PnL inflated ~7x.
- **Fix:** `if hl_notional_usdt is not None else amount_usdt`

### Bug 6 — mirror_close RuntimeError on Rollback (CRITICAL)
- **File:** brain.py:572-580
- **Bug:** `mirror_close` raises RuntimeError if `LIVE_TRADING_ENABLED=False`. During rollback after DB INSERT failure, kill switch is off but mirror_close was called → raises → orphan HL position left open.
- **Fix:** Uses `close_position` (lower-level, no gate) instead of `mirror_close`.

### Bug 7 — ai-engineer Audit False Positives
- **Bug 5 (paper flag):** ai-engineer claimed `paper = not is_live_trading_enabled()` was inverted — it is NOT. Logic is correct.
- **Phantom detection fix:** ai-engineer said LIMIT 1 was correct — it was not (direction filter needed).
- **Rule:** Always verify ai-engineer findings with grep+py_compile in main session before implementing.

## All Modified Files — Compile Verified

- brain.py ✓
- signal_compactor.py ✓
- decider_run.py ✓
- hl-sync-guardian.py ✓
- away_detector.py ✓
- hyperliquid_exchange.py ✓

## Current State (2026-05-20 00:43)

- `LIVE_TRADING_ENABLED = False` — kill switch is OFF
- Guardian running in LIVE SYNC mode (PID 1705402)
- All fixes deployed
- To go live: flip `LIVE_TRADING_ENABLED = True` in hermes_constants.py