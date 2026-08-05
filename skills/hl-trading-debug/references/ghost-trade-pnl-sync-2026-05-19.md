# Ghost Trade / Phantom Signal Debug — 2026-05-19

## What happened

AAVE, AVAX, NEAR, SUSHI, BRETT were opened and closed on Hyperliquid in rapid succession (~10s each) with no corresponding PostgreSQL records. Guardian created orphan records with WRONG entry prices (close price, not actual entry).

`signals.json` showed `decision=EXECUTED` for AAVE — signal consumed but no trade recorded.

## Root cause chain (4-part cascade)

### Step 1 — Signal marked EXECUTED before brain.py runs
`decider_run.py` line 1869 calls `mark_signal_executed()` BEFORE `execute_trade()` fires brain.py. If brain.py fails, rollback fires but matches nothing when `sig_id=None`.

### Step 2 — brain.py RC=0 but no 'trade #' in stdout = silent DB failure
brain.py prints `✅ trade #N` to stdout ONLY after successful DB INSERT. Previously decider_run treated ANY RC=0 as success — including when DB INSERT failed silently and all output went to stderr.

**FIX (decider_run.py):**
```python
if result.returncode == 0:
    for line in result.stdout.split('\n'):
        if 'trade #' in line.lower():
            tid = line.lower().split('trade #')[1].split()[0]
            if tid == 'none':
                return False, f'brain.py rejected: ...'
            return True, f'trade #{tid}'
    # RC=0 but no 'trade #' found in stdout — DB INSERT failed silently.
    # Do NOT mark signal EXECUTED — return failure so decider_run retries.
    log(f'  [brain.py] ⚠️ RC=0 but no trade ID in stdout — treating as failure.')
    return False, f'brain.py RC=0 but no trade ID in stdout'
```

### Step 3 — Compactor purges EXECUTED signals without verifying DB trade exists
`_purge_executed_signals()` deleted signals where `decision='EXECUTED'` regardless of whether a corresponding PostgreSQL trade existed. Phantom signals (marked EXECUTED, no DB record) were permanently lost.

**FIX (signal_compactor.py):** `_purge_executed_signals()` now:
1. Fetches all old EXECUTED signals
2. For each one, checks PostgreSQL for a corresponding recent trade
3. If no trade found → restores signal to PENDING instead of deleting
4. Only deletes signals that have a confirmed DB trade record

### Step 4 — sig_id=None rollback skipped silently
`rollback_signal_executed(token, direction, signal_id=None)` used `WHERE signal_id=%s` — NULL never matches. Signal stuck `executed=1` permanently.

**FIX:** decider_run now also tries `mark_signal_executed(token, direction, 'APPROVED', signal_id=None)` as fallback (token+direction match, no signal_id filter).

## Changes made

| File | Change |
|------|--------|
| `decider_run.py` | Import `DEFAULT_TRADE_SIZE_USDT` from hermes_constants; brain.py success check requires `✅ trade #N` in stdout |
| `signal_compactor.py` | `_purge_executed_signals()` cross-checks PostgreSQL before deleting; restores phantom signals to PENDING |

## Files modified
- `/root/.hermes/scripts/decider_run.py` — lines ~709-731, ~137-140
- `/root/.hermes/scripts/signal_compactor.py` — lines ~1331-1428

## Compile verified
```bash
cd /root/.hermes/scripts
python3 -m py_compile decider_run.py signal_compactor.py && echo "ALL COMPILE OK"
```
Result: ALL COMPILE OK

## Key diagnostic commands
```bash
# Check signals DB for phantom executed signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, decision, signal_id, created_at FROM signals WHERE decision='EXECUTED' ORDER BY created_at DESC LIMIT 10"

# Check PostgreSQL for recent trades
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"SELECT id, token, status, close_time FROM trades WHERE token IN ('AAVE','AVAX','NEAR','SUSHI','BRETT') ORDER BY id DESC LIMIT 10\")
for r in cur.fetchall(): print(r)
"

# Check HL for open positions
cd /root/.hermes/scripts && python3 -c "
from hyperliquid_exchange import get_open_hype_positions_curl
p = get_open_hype_positions_curl()
for t,d in p.items(): print(t, d.get('direction'), 'sz=', d.get('size'))
"
```

## Historical data corruption note
AAVE #10205 and AVAX #10206 guardian_orphan records have wrong entry prices (close price instead of actual HL entry). These are historical records from before the fix. PnL for those specific trades is corrupted. Not automatically fixed — requires manual DB update if historical accuracy matters.