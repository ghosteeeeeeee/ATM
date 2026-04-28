---
name: tp-multiplier-debug
description: Debug anomalous tp_multiplier values in Hermes trades
triggers:
  - tp_multiplier wrong
  - why is TP so wide
  - PENGU tp_multiplier
  - investigate SL/TP params
---

# TP/SL Debug — One Shot

## When
User asks why a TP or SL is wrong, or why tp_multiplier is anomalous.

## Correct Path

### Step 1: Query the trade directly (no logs, no guessing)

```python
import psycopg2
conn = psycopg2.connect(
    host='/var/run/postgresql', database='brain',
    user='postgres', password='Brain123'
)
c = conn.cursor()
c.execute('''
    SELECT token, direction, entry_price, stop_loss, target,
           leverage, tp_multiplier, atr_managed, entry_atr_14,
           sl_distance, sl_group, regime, signal, open_time
    FROM trades
    WHERE token='PENGU' AND status='open'
''')
row = c.fetchone()
print(row)
```

### Step 2: Key indicators to look for

| Field | Normal | Anomaly |
|-------|--------|---------|
| `tp_multiplier` | 1.0–1.5 | 10 = bad |
| `entry_atr_14` | populated | None = no ATR at entry |
| `atr_managed` | True | — |
| `sl_distance` | 0.5–2.0% | 0.0 = not set |

### Step 3: If tp_multiplier=10 or entry_atr_14=None

The guardian likely hit a code path where:
- `momentum_stats` was None → `_atr_sl_k_scaled` returned k=1.0 default
- BUT something set tp_multiplier=10 separately

Search these files for tp_multiplier assignments:
```bash
grep -rn "tp_multiplier" /root/.hermes/scripts/
grep -rn "tp_mult" /root/.hermes/scripts/
```

## PENGU case (Apr 28 05:10)
```
PENGU LONG | entry=0.010039 | SL=0.009879 | target=0.010248
tp_multiplier=10 ← WRONG (should be ~1.25)
entry_atr_14=None ← no ATR at entry
atr_managed=True
signal=trend_purity+
```
This means: at entry, no ATR data existed, guardian used defaults, and somehow tp_multiplier got set to 10 instead of the normal k×1.25.

## Never do this again:
- Don't grep logs first — query the DB directly
- Don't search scripts for "tp_multiplier =" — it may be set via a different variable name or computed inline
- The answer is always in the `trades` table of the `brain` DB
