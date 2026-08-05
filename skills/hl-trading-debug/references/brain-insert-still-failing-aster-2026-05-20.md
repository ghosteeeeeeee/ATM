# ASTER Incident — INSERT Still Failing Despite Structural Fix (2026-05-20)

## What Happened

At 19:04:17 T enabled live trading (`LIVE_TRADING_ENABLED=True` in hermes_constants.py:24). ASTER SHORT filled on Hyperliquid at 19:04:17 (entry 0.69058, sz=15 ASTER, $10.36 USDC notional).

At 19:05:29 the guardian detected ASTER as an orphan — HL position existed but no PostgreSQL record.

## Evidence

| Source | What it shows |
|--------|--------------|
| HL fills | Open Short @ 0.69058, Close Short @ 0.69006, both confirmed in HL history |
| PostgreSQL | 0 open, 0 closed trades (only 3 legacy garbage rows: ids 10211-10213) |
| guardian.log | "ORPHAN DETECTED: ASTER — brain.py INSERT failed and HL position was left dangling!" |
| guardian.log | Created guardian_orphan trade #10214, closed it with pnl=+0.0753% |
| audit.log | 2x TRADE_OPEN_ATTEMPT for ASTER at 19:04:03 and 19:05:18, no TRADE_OPEN_SUCCESS |

## Why This Matters

All 44-param structural fixes from earlier sessions are in place and compile clean:
- `python3 -m py_compile brain.py` → OK
- 44 params = 44 placeholders (verified)
- `flipped_from_trade`/`flip_variant` swap corrected
- `json.dumps(default=str)` on both metadata calls
- `close_trade` UPDATE has `AND status = 'open'` guard

Yet the INSERT is **still silently failing**. Guardian orphan detection confirms brain.py did NOT write to PostgreSQL.

## Root Cause Hypothesis

**Hypothesis A: brain.py exits RC=0 with no 'trade #' in stdout → decider_run treats as failure, but HL position was opened**

decider_run.py line 713:
```python
result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
log(f'  [brain.py] RC={result.returncode} stdout={result.stdout[:200] if result.stdout else "(empty)"}')
# RC=0 path (line 715+):
if 'trade #' in result.stdout:
    # success path
# RC=0 but no 'trade #' → returns failure (line 729)
```

But brain.py at line 577-578 prints the success message BEFORE the INSERT commits:
```python
print(f"[brain.py] ✅ trade #{trade_id} | {signal} {direction} {token} @ {entry_price}", flush=True)
return None  # ← returns None (falsy) to CLI handler
```

The flow: `add_trade()` → `mirror_open()` → `INSERT` → `conn.commit()` → `print("✅ trade #")`. If `conn.commit()` fails AFTER the print, or if the INSERT fails inside psycopg2 but the print came first, brain.py exits RC=0 with "✅ trade #" in stdout but no row in PostgreSQL.

**Hypothesis B: psycopg2 autocommit=False + connection.close() without commit() → silent rollback**

brain.py uses default `autocommit=False` (psycopg2 default). If `conn.close()` is called anywhere after the INSERT without an explicit `conn.commit()`, the transaction is rolled back. Check brain.py around line 578+ for `conn.close()` without `commit()`.

## Next Debugging Step

1. Read brain.py around the INSERT success path — find `conn.commit()` call and whether it precedes or follows the `print("✅ trade #")`.
2. Check if `conn.close()` without `commit()` exists in the `add_trade` function or its callers.
3. The ASTER incident proves: **HL fill + no DB row = INSERT truly failing**, not a phantom execution. The fix needs to be in brain.py's commit/rollback logic, not in the params tuple.

## Action Items

- [ ] Read brain.py INSERT commit path — find exact order of commit vs print
- [ ] Check for `conn.close()` without `commit()` in `add_trade()` or CLI handler
- [ ] Add `stderr=subprocess.STDOUT` to decider_run.py:713 so brain.py exceptions appear in captured stdout
- [ ] Consider: does `LIVE_TRADING_ENABLED=True` actually propagate to the brain.py subprocess? (subprocess inherits parent env by default, so yes — but verify)

## Files to Check

- `/root/.hermes/scripts/brain.py` — INSERT commit path (search for `commit`, `close`, `conn.`)
- `/root/.hermes/scripts/decider_run.py:713` — add stderr capture
- `/root/.hermes/scripts/hermes_constants.py:24` — LIVE_TRADING_ENABLED=True