# Phantom Executed Signal — 2026-05-19

## Symptoms
AAVE, AVAX, NEAR, SUSHI, BRETT opened and closed on HL in <10 seconds. Guardian created orphan records with WRONG entry prices (market close price, not actual HL entry). Local trades.html has no record. PostgreSQL `trades` table has no entry.

## Root Cause Chain — 6 Parts

### Part 1: is_live_trading_enabled() returned False even when file said True
`hyperliquid_exchange.py` `is_live_trading_enabled()` returned `hermes_constants.LIVE_TRADING_ENABLED` (hardcoded `False`) instead of reading `hype_live_trading.json`.

decider_run passes `--real` flag → `is_live_trading_enabled()` returns False → brain.py prints `❌ REJECTED: X — live_trading is DISABLED` → returns `None`.

decider_run logged `→ ENTERED` anyway (RC=0 but no trade ID check), marks signal EXECUTED.

### Part 2: decider_run marked signal EXECUTED before brain.py ran
`mark_signal_executed()` called BEFORE `execute_trade()` fires brain.py.
If brain.py fails → rollback fires but `sig_id=None` → rollback SQL `WHERE signal_id=%s` with NULL → matches nothing → signal stuck EXECUTED=1.

### Part 3: decider_run required RC=0, not trade ID confirmation
`decider_run.py` treated RC=0 as success (returned True, signal stays EXECUTED).
brain.py exits `None` (not RC=1) when `is_live_trading_enabled()` is False.
FIXED: decider_run now requires `✅ trade #N` in brain.py stdout before marking signal EXECUTED.

### Part 4: Compactor purged EXECUTED signals without verifying DB trade exists
FIXED: `_purge_executed_signals()` now cross-checks PostgreSQL; signals without a corresponding trade are restored to PENDING.

### Part 5: Compactor phantom detection queried only closed trades
`WHERE close_time >= NOW() - INTERVAL '2h'` missed open trades (close_time IS NULL), misclassifying active open trades as phantom.
FIXED: removed the `close_time` filter, now queries `SELECT id FROM trades WHERE token=%s LIMIT 1`.

### Part 6: sig_id=None rollback failure is non-fatal
`rollback_signal_executed(token, direction, signal_id=None)` has `WHERE signal_id=%s` — NULL never matches.
FIXED: decider_run now tries `mark_signal_executed(token, direction, 'APPROVED', signal_id=None)` as fallback (token+direction match, no signal_id filter).
ALSO: sig_id=None legacy hot-set entries now log CRITICAL warning.

## Diagnostic
```bash
# Check for phantom EXECUTED signals (no corresponding PostgreSQL trade)
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, decision, signal_id, trade_id, created_at FROM signals WHERE decision='EXECUTED' ORDER BY created_at DESC LIMIT 10"

# Then check if any have a corresponding trade
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT token, direction, status FROM trades WHERE token IN ('AAVE','AVAX','NEAR','SUSHI','BRETT')"

# Check guardian orphan records
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT id, token, entry_px, exit_px, pnl_usdt, pnl_pct, guardian_closed, created_at FROM trades WHERE guardian_closed=true ORDER BY created_at DESC LIMIT 5"
```

## Fixes Applied (2026-05-19)
1. `hyperliquid_exchange.py:239` — `is_live_trading_enabled()` now reads `_load_flags().get("live_trading", False)`
2. `decider_run.py` — signal marked EXECUTED only AFTER brain.py confirms `✅ trade #N`
3. `signal_compactor.py` — purge cross-checks PG for any trade (open or closed)
4. `decider_run.py` — sig_id=None token+direction fallback rollback + CRITICAL log warning
5. `brain.py` — DEBUG print added at entry: `print(f"[brain.py] DEBUG is_live_trading_enabled() = {is_live_trading_enabled()}")`

## Recovery for Existing Phantom Signals
Compactor's next purge cycle (within 1h) will detect phantom EXECUTED signal, find no corresponding PostgreSQL trade, and restore it to PENDING. No manual intervention needed.

## Key Lesson
Python exceptions in subprocess calls go to stderr, NOT to subprocess stdout. When brain.py fails via RC=1 with empty stderr, check `/root/.hermes/logs/pipeline.err.log` for the actual traceback.