---
name: signal-audit-debug
description: Debug why Hermes signals fire incorrectly, excessively, or not at all — trace signal history, price data quality, and silent failures
tags: [hermes, signals, debug, trading]
---

# Signal Audit & Debug Skill

## Context
Hermes signal scripts (`/root/.hermes/scripts/*.py`) — debug why signals fire incorrectly or excessively.

## Investigation Workflow

### Step 1: Get the Raw Signal History
```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute("""
    SELECT created_at, price, source, decision, signal_type
    FROM signals WHERE token=? ORDER BY created_at
""", (TOKEN,))
```
Analyze: are signals EXECUTED, EXPIRED, REJECTED? Same-direction signals repeating?

### Step 2: Get the Actual Price Data Used by the Signal
```python
conn2 = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur2 = conn2.cursor()
cur2.execute('''
    SELECT timestamp, price FROM price_history
    WHERE token=? ORDER BY timestamp DESC LIMIT N
''', (TOKEN,))
rows = cur2.fetchall()
```
Check:
- Are timestamps distinct or duplicate? Duplicates inflate bar count
- Large gaps between timestamps (>2min)? Gaps cause EMA/SMA instability
- Does data exist for the signal's claimed fire time?

### Step 3: Find the Signal Generator Source
```bash
grep -rn "signal_type\|SOURCE_\|source=" /root/.hermes/scripts/*.py | grep -i TOKEN_OR_SIGNAL_NAME
```
Map signal_type/source string to the exact file and function.

### Step 4: Check for Silent Import/Call Failures
Functions that `except Exception: return []` silently swallow errors. Check:
- Does `set_cooldown()` actually exist in `signal_schema`?
- Correct table/column names used?
- Double-subquery pattern correct for ascending order?

### Step 5: Check Cooldown Mechanism
```python
# Does set_cooldown exist?
from signal_schema import set_cooldown  # raises ImportError silently if missing

# Check loss cooldown file
import json
with open('/root/.hermes/data/loss_cooldowns.json') as f:
    print(json.load(f))

# Check recent trades log
with open('/var/www/hermes/data/recent_trades.json') as f:
    data = json.load(f)
    print(data.get('TOKEN', []))
```

## Key Findings from ORDI gap-300 Audit

### Bug 1: Missing `set_cooldown` — Silent Failure
- `gap300_signals.py` imports `set_cooldown` from `signal_schema`
- `signal_schema.py` never defines it → `NameError` at import
- `except Exception` in `scan_gap300_signals` catches it silently
- 118 ORDI gap-300 signals fired with ZERO cooldown blocks

### Bug 2: Gapped Price Data → Phantom Crossings
- ORDI: 23,207 entries, 1,075 timestamp gaps >2min (999 >10min)
- EMA(300) on gapped data is unreliable → gap re-crosses 0.05% repeatedly
- Only 4 legitimate crossings in 10h, but 118 signals fired

## DB Paths
| DB | Path | Notes |
|----|------|-------|
| signals_runtime | `/root/.hermes/data/signals_hermes_runtime.db` | signals table |
| price_history | `/root/.hermes/data/signals_hermes.db` | live 1m prices |
| candles | `/root/.hermes/data/candles.db` | candles_1m, stale ~44min, volume only |
| loss_cooldowns | `/root/.hermes/data/loss_cooldowns.json` | guardian loss cooldown |
| recent_trades | `/var/www/hermes/data/recent_trades.json` | recent trade log |
