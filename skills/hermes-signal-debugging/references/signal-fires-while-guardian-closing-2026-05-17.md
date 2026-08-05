# Signal Fires While Guardian Closing Same Token

**Date:** 2026-05-17
**Symptom:** ATOM SHORT closed at loss on HL → no cooldown recorded → signal fires again 81 seconds later at 10:05:26. Guardian closing marker was active but signal_compactor didn't see it.

---

## Root Cause Chain

```
HL position opens (no DB record — INSERT failed or orphan guard blocked)
    ↓
HL closes position (no DB record to close → no cooldown set)
    ↓
Guardian writes closing marker (orphan close path, lines 3598)
    ↓
signal_compactor runs → _get_open_tokens() → PostgreSQL has NO record → returns {}
    ↓
ATOM not in open_tokens → signal passes through → pipeline fires ATOM SHORT #2
```

**Why `_get_open_tokens()` returned {}:** It only checks PostgreSQL. When `brain.py add_trade()` INSERT failed silently, there was no DB record for the first ATOM trade. `_get_open_tokens()` query returns nothing. Guardian's orphan guard (lines 1150-1154) blocks the guardian from creating a DB record for orphan HL positions — so no record was ever created.

**Why closing marker didn't help:** `_get_open_tokens()` didn't check `guardian-closing-markers.json`. It only saw PostgreSQL.

---

## Fix F Applied — `_get_open_tokens()` Defense-in-Depth

signal_compactor.py lines ~76-120:

```python
def _get_open_tokens() -> set:
    # PostgreSQL check (existing)
    tokens = {row[0] for row in cur.fetchall()}
    
    # DEFENSE-IN-DEPTH: Also check guardian closing markers
    guardian_closing = set()
    closing_file = '/root/.hermes/data/guardian-closing-markers.json'
    try:
        if os.path.exists(closing_file):
            with open(closing_file) as f:
                data = json.load(f)
            guardian_closing = {k.lower() for k in data.get('tokens', {})}
            if guardian_closing:
                log(f"[OPEN-POS-FILTER] Guardian closing markers active: {sorted(guardian_closing)}")
    except Exception as e:
        log(f"[WARN] Could not read guardian closing markers: {e}", 'WARN')
    
    if guardian_closing:
        tokens = tokens | guardian_closing  # union — treat guardian-closing as open
    
    return tokens
```

**Effect:** Even if PostgreSQL has no record (orphan case), a token with an active closing marker is treated as "open" and blocked from getting new signals.

---

## Why Guardian Closing Marker Exists

`_save_closing_marker(token, trade_id=None)` is called in `hl-sync-guardian.py` at line 3598 BEFORE `close_position_hl(coin, 'guardian_orphan')`. This is the race-condition protection: signal_compactor and decider_run check the marker file to know "guardian is actively closing this token — don't fire new signals."

The marker is cleared by `_clear_closing_marker(token)` when the orphan close completes (line 3632) or after fill polling confirms HL position is gone.

---

## Related Bugs

| Bug | Symptom |
|-----|---------|
| zscore-pump direction (`z = -z`) | Positive z triggered SHORT instead of LONG — counter-trend signals |
| `close_paper_position()` no PnL% in reason | `is_loss` never fires, cooldown skipped |
| STALE_ROTATION missing `_record_loss_cooldown` | Loss through stale rotation never recorded |
| Brain.py silent INSERT failure | Orphan HL position has no DB record, triggers this chain |

---

## Diagnostic Commands

```bash
# Check active guardian closing markers
cat /root/.hermes/data/guardian-closing-markers.json | python3 -m json.tool

# Check PostgreSQL open tokens
psql -h 10.60.68.154 -p 5432 -U postgres -d brain -c \
  "SELECT token, direction, entry_price, open_time FROM trades WHERE status='open';"

# Find tokens in closing markers but not in PostgreSQL
python3 -c "
import json
with open('/root/.hermes/data/guardian-closing-markers.json') as f:
    markers = set(json.load(f).get('tokens', {}).keys())
import psycopg2
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute(\"SELECT LOWER(token) FROM trades WHERE status='open'\")
pg_tokens = {r[0] for r in cur.fetchall()}
print('In closing markers but not in PostgreSQL:', markers - pg_tokens)
print('In closing markers:', markers)
"
```