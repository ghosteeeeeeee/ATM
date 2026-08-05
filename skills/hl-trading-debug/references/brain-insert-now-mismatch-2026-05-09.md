# brain.py INSERT — NOW() Expression vs Placeholder Mismatch
**Date:** 2026-05-09
**Severity:** Critical (live trading broken — all HL fills leave orphan positions)

## Symptom
HL fills succeed. PostgreSQL trades table never records the trade. Guardian closes orphan within 3-17 seconds.

## Log Signature
```
[brain.py] RC=1 stdout=[brain.py] ✔ no duplicate open in PostgreSQL for LTC
[brain.py] → mirror_open(LTC, LONG, entry_price=58.7975, leverage=5)
[HYPE Mirror] OPEN LONG 0.18 LTC @ signal=$58.835500 → HL_fill=$58.838000 (1 fill)
[brain.py] ❌ FAILED: stderr=(empty)
⚠️ ROLLBACK FAILED: sig#797986 already claimed by another process
```
`stderr=empty` because the INSERT error is caught by `except Exception` and printed to stdout via `print()`, not to stderr.

## Root Cause
`add_trade()` in `brain.py` line 485: VALUES clause has **41 `%s` placeholders + 1 `NOW()` function = 42 expressions**. Column list (line 472-484) has **41 columns**. PostgreSQL rejects: `INSERT has more expressions than target columns`.

Historical context:
- **Old code (c91e3ee)**: 25 columns, 24 `%s` + NOW() = 25 expressions → **balanced ✓**
- **New code (d31692f)**: 41 columns, 41 `%s` + NOW() = 42 expressions → **mismatch ✗**
- Commit d31692f added 16 new signal/price columns but only added `%s` placeholders for them, creating the off-by-one

## Byte-Level Diagnostic
```python
with open('/root/.hermes/scripts/brain.py', 'rb') as f:
    content = f.read()
idx = content.find(b'INSERT INTO trades')
returning = content.find(b'RETURNING id', idx)
block = content[idx:returning]
print(block.decode('utf-8', errors='replace'))
# Count: placeholders = block.count(b'%s'); now_count = 1 if b'NOW()' in block else 0
# Total expressions = placeholders + now_count; must equal column count
```

## Correct Fix
**Remove one `%s` placeholder from the VALUES line (line 485).**

The VALUES line already has 41 placeholders. The `NOW()` function fills the `open_time` column (position 12) — that's correct. The bug is one extra placeholder somewhere in the 41.

The tuple has 40 pre-NOW() values + 1 `test_trailing_variant=None` = 41 items. Remove the placeholder for `test_trailing_variant` since its value is `None`.

**Simpler fix**: Change line 485 from:
```python
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,...%s)
```
to remove one `%s` before or after NOW(), matching the column that maps to `None`.

## 3-Way Position Comparison
```python
import sqlite3, psycopg2, sys
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl
from _secrets import BRAIN_DB_DICT

hl = get_open_hype_positions_curl()
conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn_pg.cursor()
cur.execute("SELECT token, direction FROM trades WHERE status='open'")
pg_open = {r[0]: r[1] for r in cur.fetchall()}

print("HL open:", set(hl.keys()))
print("PG open:", set(pg_open.keys()))
print("In HL but not PG:", set(hl.keys()) - set(pg_open.keys()))
```

## Archive Compatibility
8 signal-indicator columns MUST remain in INSERT: `signal_momentum_state`, `signal_z_score_tier`, `signal_decision`, `signal_leverage`, `signal_created_at`, `test_sl_variant`, `test_timing_variant`, `test_trailing_variant`. `archive-trades.py` reads them from PostgreSQL at lines 232-238.