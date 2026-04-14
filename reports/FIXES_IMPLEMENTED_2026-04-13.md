# Hermes Tracking Table Fixes — 2026-04-13

## Summary

Implemented 3 call-site fixes to wire up the tracking tables in the Hermes trading system.
All fixes verified: modules load without syntax errors.

---

## Fix 1: decider-run.py — Cooldown Enforcement ✅ DONE

**File:** `/root/hermes-v3/hermes-export-v3/decider-run.py`

### Change 1a: Import new functions (line 9)
```python
from signal_schema import init_db, get_approved_signals, mark_signal_executed, is_cooldown_active, record_cooldown_start
```

### Change 1b: Cooldown check BEFORE trade open (after win cooldown, ~line 522)
Added check using `is_cooldown_active()` from signal_schema:
```python
# Check cooldown_tracker — block same token+direction after a close
if is_cooldown_active(token, direction):
    log(f'SKIP: {token} {direction} in cooldown (cooldown_tracker)')
    skipped += 1
    continue
```

### Change 1c: Record cooldown AFTER trade close (close_position function, ~line 465)
After a trade closes via `close_position()`, records cooldown using `record_cooldown_start()`:
```python
if row:
    trade_dir = row[1]
    log(f'CLOSED: {token} {reason} (trade #{row[0]})')
    try:
        record_cooldown_start(token, trade_dir, duration_minutes=30)
    except Exception as cd_err:
        log(f'CLOSE cooldown record error: {cd_err}')
    return True
```
Note: `direction` is now fetched from the DB (RETURNING clause) since it's not a function parameter.

### Test Result
```
decider-run OK
```

---

## Fix 2: ai_decider.py — Record Decisions ✅ DONE

**File:** `/root/hermes-v3/hermes-export-v3/ai_decider.py`

### Change 2a: Import record_decision (line 23)
```python
from signal_schema import (
    init_db, get_pending_signals, get_latest_price,
    approve_signal, update_signal_decision, set_cooldown, get_cooldown,
    compute_all_indicators, get_price_history,
    price_age_minutes, DB_PATH, record_decision
)
```

### Change 2b: After YES/NO/WAIT decisions in decide_signal (~lines 430-480)
Added `record_decision()` call after each YES, NO, and WAIT branch, with error handling:
```python
try:
    record_decision(
        token=token,
        direction=direction,
        decision=decision,
        confidence=confidence,
        entry_price=price,
        exchange='hyperliquid',
        reason=excerpt,
        regime=regime
    )
except Exception as rd_err:
    log(f'record_decision error: {rd_err}', 'WARN')
```

All three decision branches (YES/NO/WAIT) now call `record_decision()` with:
- `token`, `direction`, `decision` (YES/NO/WAIT)
- `confidence`, `entry_price`, `exchange='hyperliquid'`
- `reason` (excerpt from LLM response)
- `regime` (market regime at time of decision)

### Test Result
```
ai_decider OK
```

---

## Fix 3: position_manager.py — PnL in signal_outcomes ✅ DONE

**File:** `/root/.hermes/scripts/position_manager.py`

### Change 3a: Import record_signal_outcome (line 19)
```python
from signal_schema import record_signal_outcome
```

### Change 3b: Call signal_schema.record_signal_outcome with actual PnL (~line 1053)
After `_record_ab_close()`, added call to `record_signal_outcome()` from signal_schema with real PnL:

```python
# Use net_pnl (after fees) as the authoritative PnL for the outcomes table
actual_pnl_usdt = net_pnl if net_pnl is not None else pnl_usdt_val
actual_pnl_pct = (actual_pnl_usdt / amount_usdt * 100) if amount_usdt > 0 else pnl_pct
try:
    record_signal_outcome(
        token=token,
        direction=direction,
        pnl_pct=round(actual_pnl_pct, 4),
        pnl_usdt=round(actual_pnl_usdt, 4),
        signal_type=signal_type or 'decider',
        confidence=confidence
    )
except Exception as rso_err:
    print(f"[Position Manager] record_signal_outcome error (non-fatal): {rso_err}")
```

The PnL used is `net_pnl` (after Hyperliquid fees), which is the most accurate PnL figure.
`record_signal_outcome` from signal_schema uses `pnl_usdt` to determine WIN/LOSS (is_win = pnl_usdt > 0).

### Test Result
```
position_manager OK
```

---

## Constraints Respected

- Live trading path NOT broken — all changes are additions/wrappers
- No modifications to `hype_live_trading.json` or `_FLIP_SIGNALS`
- All DB writes wrapped in try/except with error logging
- Skips/rejections due to cooldowns are logged
- All modules import cleanly without syntax errors

---

## Tracking Tables Wired

| Table | Written By | Status |
|-------|-----------|--------|
| `decisions` | ai_decider.py (record_decision) | ✅ DONE |
| `cooldown_tracker` | decider-run.py (record_cooldown_start) | ✅ DONE |
| `cooldown_tracker` | decider-run.py (is_cooldown_active check) | ✅ DONE |
| `signal_outcomes` | position_manager.py (record_signal_outcome) | ✅ DONE |
