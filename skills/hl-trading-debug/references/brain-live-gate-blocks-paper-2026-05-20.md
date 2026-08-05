# brain.py is_live_trading_enabled() Gate Blocks Paper Trades

**Date:** 2026-05-20  
**Symptom:** PostgreSQL `trades` table has zero open AND zero closed records for all tokens (AAVE, XRP, APEX, etc.). HL fills confirmed via `get_trade_history()` but no DB entry.

**Root Cause:** `is_live_trading_enabled()` at brain.py ~line 405 returns `None` when `LIVE_TRADING_ENABLED=False`, BEFORE any DB INSERT is attempted. The function exits with error message and RC=1. This blocks **all** trades including paper-mode ones — the gate was intended as a live-trading kill switch but inadvertently prevents paper trades from being recorded.

**Contrast with _params mismatch bug:**  
- `_params` mismatch (43 vs 44): Python `IndexError` fires at query execution — INSERT never reaches PostgreSQL. Exception is caught, rollback attempted, RC=1.
- `is_live_trading_enabled()` gate: returns None BEFORE INSERT is built — no exception thrown, no DB interaction at all.

**Test confirming the gate:**
```
$ brain.py trade add TESTCOIN long 50 1.0 --paper --server Hermes ...
RC: 1
STDOUT: [brain.py] DEBUG is_live_trading_enabled() = False
        [brain.py] ❌ REJECTED: TESTCOIN LONG — live_trading is DISABLED
```

**Fix required:** Paper trades must bypass the `is_live_trading_enabled()` gate. Two options:
1. Restructure `is_live_trading_enabled()` to return `True` when `paper=True`
2. Move the paper-mode bypass above the gate in `add_trade()`

**Note:** The `_params` 43-vs-44 mismatch is a separate, second bug that would fire AFTER the gate is lifted — it causes an `IndexError` on INSERT execution.
