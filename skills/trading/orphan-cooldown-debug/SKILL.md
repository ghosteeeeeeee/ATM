---
name: orphan-cooldown-debug
description: Debug Hermes trading system when a token re-enters immediately after closing at a loss. Traces cooldown writes through guardian orphan paths, decider check paths, and hot-set bypass paths.
---
# Orphan Cooldown Debug — Hermes Trading System

## Symptom
A token re-enters the market immediately (< 60s) after closing at a loss. No cooldown appears to be in effect.

## Debugging Sequence

### Step 1: Check all cooldown stores simultaneously
```python
import json, time, psycopg2, sys
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import BRAIN_DB_DICT, get_cooldown

# Check all 3 stores
try:
    with open('/root/.hermes/data/loss_cooldowns.json') as f:
        d = json.load(f)
    for k,v in d.items():
        exp = v.get('expires') if isinstance(v, dict) else v
        print(f"loss_cooldowns.json: {k} expires={time.ctime(exp)}")
except: print("loss_cooldowns.json: empty")

try:
    with open('/root/.hermes/data/signal_cooldowns.json') as f:
        print(f"signal_cooldowns.json: {json.load(f)}")
except: print("signal_cooldowns.json: empty/missing")

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("SELECT token, direction, expires_at, reason FROM signal_cooldowns WHERE expires_at > NOW()")
for r in cur.fetchall():
    print(f"PostgreSQL: {r}")
conn.close()

# Direction-specific check (critical: no direction = check both)
print(f"get_cooldown('BCH', 'LONG'): {get_cooldown('BCH', 'LONG')}")
print(f"get_cooldown('BCH'):         {get_cooldown('BCH')}")  # no direction
```

### Step 2: Identify which close path was used
```bash
grep "TOKEN.*Close\|close.*TOKEN\|orphan" /root/.hermes/logs/sync-guardian.log
```
Close reasons: `HL_CLOSED`, `atr_sl_hit`, `guardian_orphan`, `cascade_flip`, `hard_sl`, `HOTSET_BLOCKED`, `ORPHAN_PAPER`

### Step 3: Trace the exact cooldown write path for that close reason

| Close Reason | Function | Writes Cooldown? | Key Bug |
|---|---|---|---|
| `HL_CLOSED` (guardian missing) | `_close_paper_trade_db` line ~2394 | ✅ Yes (both JSON + PG) | was missing PG write before 2026-04-22 |
| `atr_sl_hit` | `position_manager._record_signal_outcome` | ✅ Yes (PG only, before 2026-04-22) | `is_loss_cooldown_active` didn't check PG |
| `guardian_orphan` (DB record exists) | `_close_orphan_paper_trade_by_id` | ✅ Yes | cooldown was inside `else` branch |
| `guardian_orphan` (true orphan, no DB record) | `_close_orphan_paper_trade_by_id` | ❌ **SKIPPED** — UPDATE hits 0 rows, dedup fires, `else` branch skipped | **Root cause bug** |
| `cascade_flip` | `position_manager` | ✅ Yes | |
| Manual close | varies | depends on path | |

### Step 4: Check decider's cooldown read path
```bash
grep -n "is_loss_cooldown_active\|get_cooldown\|loss_cooldown" /root/.hermes/scripts/decider_run.py | head -20
```
- `decider_run.py` line ~1507: `is_loss_cooldown_active(token, direction)` — checks `loss_cooldowns.json` only (primary) with PostgreSQL fallback added 2026-04-22
- `signal_gen.py` line ~2383: `get_cooldown(token)` — checks PostgreSQL via `signal_schema.get_cooldown`

### Step 5: Check hot-set bypass
```bash
grep -n "cooldown\|get_cooldown" /root/.hermes/scripts/signal_compactor.py | head -20
grep -n "cooldown\|get_cooldown" /root/.hermes/scripts/signal_gen.py | grep -i "hotset\|cooldown" | head -20
```
Tokens can re-enter NOT through decider but through hot-set bypass:
- `signal_compactor` Step 9 filter: must check `get_cooldown()` before adding to hot-set ✅
- `_filter_safe_prev_hotset`: must check `get_cooldown()` before preserving tokens ✅
- `signal_gen.is_confluence_approved` (line ~2133): reads hotset.json directly without cooldown check — confluence signals bypass hot-set filtering

## Key Bug Pattern: Cooldown Inside Conditional Branch

**Pattern:** Cooldown write placed inside an `if cur.rowcount == 0` dedup branch, making it conditional on whether the UPDATE found a row.

**Bad pattern:**
```python
if cur.rowcount == 0:
    log("already closed, skipping")
    conn.rollback()
    # ❌ Cooldown write is MISSING here — true orphans silently bypass
else:
    conn.commit()
    if not is_win:
        _record_loss_cooldown(token, direction)  # Only reached if DB record existed
```

**Correct pattern:**
```python
if cur.rowcount == 0:
    log("already closed, skipping (true orphan)")
    conn.rollback()
    # ✅ Always record for true orphans
    if not is_win:
        _record_loss_cooldown(token, direction)
else:
    conn.commit()
    if not is_win:
        _record_loss_cooldown(token, direction)

# ✅ Outcome recording always fires
_record_trade_outcome(...)
```

**Also:** `_record_trade_outcome` dedup uses `token+direction+pnl` (not trade_id alone). For true orphans where no DB record exists, the dedup won't protect against missing the outcome — the cooldown write should NOT be inside the dedup if-block.

## Verified Fix Locations (as of 2026-04-22)
- `hl-sync-guardian.py` `_close_orphan_paper_trade_by_id`: cooldown written in BOTH `rowcount==0` and `else` branches, plus PostgreSQL write in both
- `hl-sync-guardian.py` `_close_paper_trade_db`: cooldown written (both JSON + PG) for all loss closes
- `signal_schema.py` `is_loss_cooldown_active`: checks JSON first, then PostgreSQL fallback
- `signal_schema.py` `get_cooldown`: checks JSON → PG → legacy JSON
- `signal_compactor.py` Step 9 filter: `get_cooldown()` check before adding to hot-set
- `signal_compactor.py` `_filter_safe_prev_hotset`: `get_cooldown()` check before preserving tokens
- `position_manager.py` `_record_signal_outcome`: PostgreSQL cooldown write on loss
- `position_manager.py` `is_loss_cooldown_active`: JSON + PostgreSQL dual check
