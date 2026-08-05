# MET Duplicate Open — 2026-06-19

## Timeline

| Time | Event |
|------|-------|
| 15:01:51 | Guardian closes MET SHORT locally (DB trade #12017), calls `market_close` on HL |
| 15:02:54 | `market_close` returns `{'status': 'ok', ...}` (order submitted, not filled). Guardian logs PASS. Fill polling starts. |
| 15:03:30 | Poll 1/6 — no fill |
| 15:04:08 | Poll 6/6 — no fill. Guardian logs `[FAIL] No HL close fills found for MET after 6 polls (30s)`. But closing marker was already set before `market_close` was called. |
| 15:05:11 | Next reconciliation cycle. MET still on HL (fill pending). Guardian sees orphan. Creates **trade #12018** — same entry price, same direction, duplicate of #12017. |
| 15:06:11 | MET falls off HL (fill finally came through). `[STALE-MARKER]` clears the closing marker. |
| 15:11 | Guardian restarted. No MET in HL. |

## Root Cause

**`close_position_hl` returns before fill is confirmed.** HL `market_close` submits a market order and returns `{'status': 'ok'}` immediately — this means HL accepted the order, not that it filled. The fill can take 30-120s during high load. The guardian:

1. Called `market_close` → got `ok` → logged PASS → set closing marker
2. Polled 6 times over 30s → no fill found
3. Gave up → logged FAIL
4. Next cycle: closing marker was cleared (stale check or pending retry cleared) → orphan path triggered → created new DB record

## Secondary Bug (FIXED THIS SESSION)

`close_position_hl` at line ~817:
```python
# Before fix — error treated as success
log(f'  ⚠️ {coin}: unexpected result structure: {str(result)[:200]}', 'WARN')
return True  # BUG: HL {'status': 'err'} hits this branch

# After fix
if isinstance(response_data, dict):
    if 'error' in response_data:
        log(f'  ❌ {coin}: HL API error: {response_data["error"]}', 'FAIL')
        return False
    if response_data.get('status') == 'err':
        err_msg = response_data.get('response', str(response_data))
        log(f'  ❌ {coin}: market_close failed: {err_msg}', 'FAIL')
        return False
```

This fix makes `close_position_hl` properly return `False` when HL returns an error dict (e.g. `'User or API Wallet does not exist'`). Without this fix, ONDO and MORPHO earlier (June 18) had their closes treated as successes even though HL rejected them.

## Fix Applied

1. `close_position_hl` now checks `response_data.get('status') == 'err'` before the statuses parsing
2. Guardian restarted with fix in place

## Diagnostic

If a duplicate open happens again:
```bash
# Check guardian log for duplicate trade_ids
strings /root/.hermes/logs/sync-guardian.log | grep "Created orphan recovery trade" | grep COIN

# Check if close fill ever arrived
strings /root/.hermes/logs/sync-guardian.log | grep "CLOSE FILL\|close fills found" | grep COIN

# Check the closing marker state at the time
cat /root/.hermes/data/guardian-closing-markers.json
```

## Prevention

The real fix would be making `close_position_hl` block until the fill is confirmed (poll inside the function), and keep the closing marker active until fill confirms. Currently the marker is written before the call and the fill polling is a separate loop. This architectural issue will produce more duplicates under load.
