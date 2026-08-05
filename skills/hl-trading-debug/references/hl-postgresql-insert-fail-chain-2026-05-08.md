# HL PostgreSQL Insert Fail Chain (2026-05-08)

## Symptom
ENS/OG/BERA/LINEA/LAYER/BRETT/SNX/ORDI open on HL but have zero PostgreSQL records.
Guardian auto-closes them as orphans within seconds.

## Root Cause Chain

```
Signal fires for BERA → accel-300+ only (1 source) → confluence gate BLOCKS
                                          ↓
But BERA somehow executes on HL → PostgreSQL INSERT fails → no record
                                          ↓
Guardian detects orphan (HL has, DB no) → writes closing marker → closes HL
                                          ↓
Orphan INSERT → trade_id=3000000 COLLISION with PURR → FAILS
                                          ↓
Closing marker NOT cleared → token blocked forever in decider_run
```

## Four Breaking Changes (May 6-8 uncommitted)

### 1. `_is_guardian_closing()` race guard — decider_run.py lines 1583-1595
```python
if _is_guardian_closing(token):
    log(f'SKIP: {token} — guardian closing in progress (race guard)')
    mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
    skipped += 1
    continue
```
Guardian writes closing marker BEFORE closing HL position. Marker only clears if
`_close_orphan_paper_trade_by_id` returns True (requires orphan DB record to exist).
Since orphan INSERT fails (trade_id collision), marker never clears → token
permanently blocked in decider_run.

### 2. Stale orphan check — brain.py lines 420-440
```python
if orphan_row:
    print(f"[brain.py] {token} has stale orphan trade #{oid} ... rejecting")
    return None
```
Rejects if DB has `status='open'` AND `hl_entry_price IS NULL OR = 0`. If a ghost
record exists (INSERT partially succeeded then rolled back), future signals blocked.

### 3. HOTSET_ENABLED bypass — decider_run.py lines 1367-1422
```python
if not HOTSET_ENABLED:
    log('  [HOTSET BYPASS] Processing all pending signals directly')
    # executes ANY pending signal without hot-set survival rounds filter
```
If HOTSET_ENABLED=False (or unset), bypasses the hot-set entirely. Any pending signal
can execute without passing through the survival rounds/filter system.

### 4. Guardian orphan INSERT collision — hl-sync-guardian.py lines 3661
```python
int(lev * 1000000)  # trade_id from HL leverage encoding
```
PURR (leverage 3) → trade_id=3000000. Guardian tries to INSERT BERA/LINEA/LAYER/SNX
with trade_id=3000000 → `duplicate key violates trades_trade_id_key` → INSERT fails →
closing marker never cleared.

## The Missing Step (HL-first but no PG record)

Confluence gate blocks single-source signals. But BERA somehow executes on HL anyway.
The execution flow must be:

```
signal_compactor → get_pending_signals() → decider_run → execute_trade()
                                                    ↓
                                          brain.py trade add --real
                                                    ↓
                                          mirror_open() on HL → SUCCEEDS
                                                    ↓
                                          PostgreSQL INSERT → SILENTLY FAILS
                                                    ↓
                                          HL position exists, no DB record → guardian orphan
```

The missing piece: how does single-source `accel-300+` reach `execute_trade()` when
confluence gate blocks it? Either:
- `decider_run` reads directly from PENDING (not hot-set), bypassing confluence gate
- GOOD_STANDALONE_SIGNALS bypass is partially working
- `_signal_type_key()` name mismatch prevents bypass from working (dead code)

## Fix Priority

1. **P0**: Remove `_is_guardian_closing()` race guard from decider_run — it blocks
   tokens permanently with no recovery path
2. **P0**: Clear `guardian-closing-markers.json` (48 stale entries)
3. **P1**: Fix guardian orphan INSERT — use `ON CONFLICT DO NOTHING` or fresh trade_id
4. **P2**: Restore stale orphan check behavior (was working before May 6)
5. **P3**: Investigate HOTSET_ENABLED bypass — should require explicit flag to disable

## Diagnostic

```bash
# Check stale closing markers
cat /root/.hermes/data/guardian-closing-markers.json | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(f'{len(d)} markers')
for k,v in list(d.items())[:3]: print(f'  {k}: {v}')
"

# Check PostgreSQL for orphan tokens
psql 'host=/var/run/postgresql dbname=brain user=postgres' -t -c "
SELECT token, status, hl_entry_price, trade_id FROM trades
WHERE token IN ('ENS','OG','BERA','LAYER','BRETT','LINEA','ORDI','SNX');
"

# Check HL positions (should be empty — guardian closed all)
python3 -c "
import sys; sys.path.insert(0,'/root/.hermes/scripts')
from hyperliquid import Hyperliquid
h = Hyperliquid()
positions = h.user_state().get('accountSummaries', [])
for p in positions:
    coin = p.get('coin','')
    pos = p.get('position',{})
    sz = float(pos.get('szi', 0))
    if sz != 0: print(f'{coin}: {sz}')
"
```