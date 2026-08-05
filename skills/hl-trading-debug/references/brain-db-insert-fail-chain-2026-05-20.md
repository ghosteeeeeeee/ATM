# Brain.py INSERT Params Mismatch — FIXED 2026-05-20

## Root Cause (Final): Missing `signal_leverage` in _params tuple

brain.py `add_trade()` INSERT has **44 `%s` placeholders** in VALUES but `_params` had **43 items**. Python `IndexError` fires during `execute()` — PostgreSQL never saw the query.

**Two-stage bug discovery:**

**Stage 1 (earlier patch):** `exp_metadata` appeared twice in `_params`:
```
Line 533: json.dumps(exp_metadata) if exp_metadata else '{}',
Line 534: exp_metadata)   ← DUPLICATE bare dict, no json.dumps
```
Removing the duplicate reduced `_params` 44→43. But the mismatch persisted.

**Stage 2 (this session):** `signal_leverage` is a named parameter of `add_trade()` (line 343) received but **never appended to `_params`**. Column-to-param mapping after removing the duplicate:

| Col | Column | Got | Should be |
|-----|--------|-----|-----------|
| 37 | `signal_decision` | `signal_decision` ✅ | `signal_decision` |
| 38 | `signal_leverage` | `signal_created_at` ❌ NULL | `signal_leverage` |
| 39 | `signal_created_at` | `test_sl_variant` ❌ 'rs-s20' | `signal_created_at` |
| 44 | `_exp_metadata` | NULL ❌ | `json.dumps(exp_metadata)` |

PostgreSQL accepted the undersized tuple silently — INSERT logged "trade #N confirmed" but row was garbage.

**Fix:** Insert `signal_leverage,` into `_params` between `signal_decision` and `signal_created_at`. Now 44 params = 44 placeholders.

## Why This Was Hard to Catch

1. `LIVE_TRADING_ENABLED=False` gate fires FIRST (line ~405) — returns None before INSERT is reached. When False, the INSERT code path is never reached. The 3 corrupted DB rows (token=NULL/'X', status=NULL) predate this bug.
2. PostgreSQL silently accepts undersized tuple — no error, no rollback, just NULL填充 last placeholder.
3. Two separate fixes were needed: (a) remove duplicate `exp_metadata`, then (b) add missing `signal_leverage`.

## The 3 Corrupted DB Rows

PostgreSQL trades table had 3 garbage rows: `(id 10211, token='X', status=NULL, server='Tokyo')` and `(10212, NULL, NULL, ...)` / `(10213, NULL, NULL, ...)`. Not from this bug — pre-exist from earlier failed INSERTs or manual testing.

## Debug Output in brain.py

```python
print(f"[brain.py] DEBUG param count: {len(_params)}")
vals_count = vals_line.count('%s')
print(f"[brain.py] DEBUG INSERT: {len(_params)} params, VALUES has {vals_count} placeholders, diff={len(_params)-vals_count}")
if len(_params) != vals_count:
    print(f"[brain.py] DEBUG ❌ MISMATCH! params={len(_params)} vals={vals_count}")
```

## Exception Handler (PostgreSQL errors now surfaced)

```python
try:
    cur.execute(query, tuple(_params))
except Exception as e:
    if hasattr(e, 'pgcode'):
        print(f"[brain.py] PostgreSQL error code={e.pgcode} detail={e.pgdiag.message}")
    print(f"[brain.py] DB INSERT FAILED: {type(e).__name__}: {e} | param_count={len(_params)}")
    raise
```

## Failure Chain (when LIVE_TRADING_ENABLED=True)

```
decider_run: brain.py subprocess → mirror_open() → HL position LIVE
brain.py: PostgreSQL INSERT → FAILS IndexError (params/placeholders mismatch)
brain.py: rollback() → "ROLLBACK FAILED: sig#XXXX already claimed"
brain.py: close_position() → "no open position for X" (race against HL consistency)
brain.py: sys.exit(1) → orphan HL position LEFT OPEN
guardian: next cycle sees orphan → closes it immediately
```

## Trades That Hit This (2026-05-20 afternoon, before fix)

| Time | Token | Signal | Result |
|------|-------|--------|--------|
| 14:59:17 | OP LONG | rs-s880,zscore-pump+ 98% | INSERT failed → orphan → guardian closed |
| 14:59:38 | XRP LONG | rs-s780,zscore-pump+ 92% | same |
| 15:00:38 | AAVE LONG | rs-s1365,zscore-pump+ 88% | same |
| 15:00:57 | LINEA LONG | rs-s1016,zscore-pump+ 87% | same |