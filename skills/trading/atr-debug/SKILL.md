---
name: atr-debug
description: Debug ATR issues for Hermes trades — find missing ATR, wrong SL/TP, stale data
triggers:
  - entry_atr_14 is None
  - ATR not found
  - no ATR at entry
  - PENGU ATR
  - ATR debug
---

# ATR Debug — One Shot

## When
User asks about a trade with missing or wrong ATR data, or why SL/TP didn't follow constants.

## Step 1: Check entry_atr_14 in DB

```python
import psycopg2
conn = psycopg2.connect(
    host='/var/run/postgresql', database='brain',
    user='postgres', password='Brain123'
)
c = conn.cursor()
c.execute('''
    SELECT token, entry_price, entry_atr_14, atr_managed,
           stop_loss, target, tp_multiplier, signal, open_time
    FROM trades
    WHERE token='PENGU' AND status='open'
''')
print(c.fetchone())
```

## Step 2: If entry_atr_14 is None

This means the guardian's `_collect_atr_updates` failed to get ATR for this coin at entry time. Check candles.db:

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/candles.db')
c = conn.cursor()
# Check what TF and symbol data exists for this coin
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(c.fetchall())
```

## Step 3: Key findings from PENGU case

- ALL PENGU trades have `entry_atr_14=None`
- ALL PENGU trades have `tp_multiplier=10` (schema default — NOT the guardian setting it)
- `tp_multiplier=10` comes from `schema_brain.sql` line 86: `tp_multiplier numeric DEFAULT 10 NULL`
- The guardian never sets `tp_multiplier` — it uses the DB default of 10
- `atr_managed=True` means guardian thinks it managed ATR, but `entry_atr_14=None` proves no ATR was recorded at entry

## The Real Issue

The `tp_multiplier=10` is a schema artifact, not a guardian-computed value. It's written by `brain.py`'s INSERT which doesn't pass `tp_multiplier`, so PostgreSQL uses the column default of `10`. This field appears in the DB but is NOT used by the guardian for TP computation.

The actual TP/SL ATR math happens in `_collect_atr_updates` in `position_manager.py`. `entry_atr_14=None` means that data wasn't captured at entry — but the guardian recomputes ATR live via `_force_fresh_atr()`.

## `_collect_atr_updates` — How It Actually Works

Located at `position_manager.py` line 1458. Called once per cycle after the main position loop.

**Flow:**
1. Deduplicate tokens — one ATR fetch per unique token via `_force_fresh_atr()`
2. Fetch momentum via `get_momentum_stats(token)` from `signal_gen`
3. Compute `k = _atr_sl_k_scaled(token, direction, atr_pct, speed_pctl, momentum)`
4. `sl_pct = k × atr_pct`
5. `tp_pct = k × ATR_TP_K_MULT × atr_pct`  (ATR_TP_K_MULT = 1.25)
6. Floor to `ATR_SL_MIN_INIT` (0.50%) or `ATR_SL_MIN_ACCEL` (0.20%) depending on phase
7. New trade detection: if `|peak - entry| / entry < 0.001` → use base k (no acceleration squeeze)

**`_force_fresh_atr()`** (line 1281):
1. Try `atr_cache.json` — fresh if < 300s old
2. HL API `candles_snapshot` → compute ATR(14) from 15m candles
3. If HL fails and no cache → Binance public API fallback
4. Save result to `atr_cache.json`

**If ATR is None for a token**: `_collect_atr_updates` skips it entirely (line 1554-1555: `if atr is None: continue`). The trade gets no ATR update.

**PENGU Reality Check (Apr 28 05:10):**
- ATR cache: 0.000126 (1.23%), age 118s — FRESH
- Guardian IS getting ATR via `_force_fresh_atr()`
- `atr_managed=True` in DB = guardian confirmed it's using ATR
- `entry_atr_14=None` = the `entry_atr_14` column wasn't populated at INSERT time — but the guardian recomputes ATR live every cycle, so this column being None doesn't mean ATR wasn't used
- TP target=0.010248 vs entry=0.010039 → that's a 2.08% TP distance — reasonable given ATR=1.23% × k×1.25
- `tp_multiplier=10` in the DB is just the schema default, NOT what the guardian uses

**Bottom line**: The guardian is computing TP/SL correctly from live ATR. The `tp_multiplier=10` in the DB is inert — it's never read by the guardian's ATR math.
