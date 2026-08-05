# mirror_close Rollback Silent Fail — brain.py line 515

## The Bug

When PostgreSQL INSERT fails after `mirror_open()` succeeds, brain.py tries to rollback the HL position:

```python
# brain.py lines 513-521
try:
    from hyperliquid_exchange import mirror_close
    mc = mirror_close(hype_token)   # ← WRONG: missing `direction`
    if mc and mc.get('success'):
        print(f"[brain.py]    ✅ HL rollback succeeded for {hype_token}")
    else:
        print(f"[brain.py]    ⚠️ HL rollback returned: {mc}")
except Exception as mc_err:
    print(f"[brain.py]    ⚠️ HL rollback failed: {mc_err} — {hype_token} may be orphaned on HL!")
```

`mirror_close()` signature:
```python
def mirror_close(token: str, direction: str, exit_price: float = None) -> dict:
```

The call is missing the `direction` argument. This causes the rollback to fail silently (no exception raised, just a bad return), leaving the HL position open with no DB record — a phantom orphan.

## Impact

- HL position stays open after failed DB INSERT
- Guardian detects orphan → closes HL position
- PostgreSQL never gets the trade record
- User sees "trade opened on HL but no trace in DB"

## Fix

```python
# Correct:
mc = mirror_close(hype_token, direction)
```

But note: at the point of the rollback, `direction` is available as a variable in the calling scope (the `add_trade()` function receives it as a parameter).

## Diagnostic

If a trade hits this bug, you won't see it in PostgreSQL. Check HL history directly:
```bash
# Find trades that were opened and closed within minutes with no DB record
grep "EXEC.*LONG\|EXEC.*SHORT" /root/.hermes/logs/pipeline.log | grep -E "BERA|ENS|OG|LINEA|LAYER|BRETT|SNX|ORDI"
```
If the EXEC logs show the trade fired but PostgreSQL has no record, this rollback bug is the likely cause.