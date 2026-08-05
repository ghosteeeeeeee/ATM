# brain.py INSERT — 44 params / 44 placeholders (FIXED + VERIFIED 2026-05-20)

## Root Cause

`brain.py` INSERT was failing with `IndexError: tuple index out of range` on every trade. The HL position opened but no DB record existed, creating orphaned phantom positions.

Two separate bugs combined:

1. **VALUES line had 45 `%s`** — one extra placeholder. psycopg2 would bind param[43] to position 44 (0-indexed: params[43]→position 45), exceeding the 44-item tuple → IndexError.

2. **`open_time` was missing from `_col_map`** — column 12 was `signal` but the VALUES had 44 positions with no slot 12 param. The shift meant every subsequent value landed in the wrong column.

## Fix Applied (lines 519–607)

### `_col_map` (lines 523–569): 44 entries, col 1–44

```
Col 12: open_time = 'now'          ← was missing, now explicit param
Cols 13–44: signal through _exp_metadata (all shifted +1)
```

### `VALUES` line (line 602): 44 `%s` (was 45)

```python
# BEFORE (45 %s — WRONG):
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,...45 total ...)

# AFTER (44 %s — CORRECT):
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,...44 total ...)
```

## Verification Command (Byte-Level)

```python
with open('brain.py', 'rb') as f:
    content = f.read()
# Find VALUES near flip_variant
idx = content.rfind(b'flipped_from_trade, flip_variant')
chunk = content[idx:idx+500]
vals_idx = chunk.find(b'VALUES')
vals_line = chunk[vals_idx:chunk.find(b'\n', vals_idx)]
print(f"%s count: {vals_line.count(b'%s')}")  # Must be 44
print(f"Items: {len(vals_line.split(b','))}")  # Must be 44
```

## Live psycopg2 Test (trade_id=10219 confirmed)

```python
from _secrets import BRAIN_DB_DICT
import psycopg2

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

sql = """INSERT INTO trades (token, direction, amount_usdt, entry_price,
  exchange, strategy, paper, stop_loss, target, server, status, open_time,
  signal, confidence, token_address, pnl_usdt, pnl_pct,
  sl_distance, trailing_activation, trailing_distance,
  trailing_phase2_dist, leverage, experiment,
  flipped_from_trade, flip_variant,
  hl_entry_price, hl_notional_usdt,
  highest_price, lowest_price,
  signal_z_score, signal_rsi_14, signal_macd_hist,
  signal_macd_value, signal_macd_signal,
  signal_momentum_state, signal_z_score_tier,
  signal_decision, signal_leverage, signal_created_at,
  test_sl_variant, test_timing_variant, test_trailing_variant,
  _signal_metadata, _exp_metadata)
VALUES (44 × %s)
RETURNING id"""

params = (
  'TESTCOIN','LONG',50.0,1.0,'Hyperliquid','Hermes-test',False,
  0.99,1.01,'Hermes','open',
  'now',          # ← open_time (col 12)
  'test-signal',81.5,None,0.0,0.0,
  0.01,0.005,0.01,0.015,2,None,
  0,'signal-flip',    # ← flipped_from_trade, flip_variant
  1.0,100.0,           # ← hl_entry_price, hl_notional_usdt
  1.0,0,               # ← highest_price, lowest_price
  1.2,45.0,0.001,0.5,0.4,
  'bullish','tier_2','ENTER_LONG',2,'2026-05-20T20:00:00',
  None,None,None,
  '{}','{}'
)  # 44 items

cur.execute(sql, params)
tid = cur.fetchone()[0]
conn.commit()
# SELECT confirmed all columns correct: trade_id=10219
cur.execute("DELETE FROM trades WHERE id=%s", (tid,))
conn.commit()
```

## Live Trading Verified (2026-05-20 — 5 real trades)

```
DB open trades: 5
  id=10224 token=ANIME dir=SHORT entry=0.00434000 hl_entry=0.00434000 open=2026-05-20 20:25:47
  id=10223 token=AAVE  dir=SHORT entry=88.69000000 hl_entry=88.69000000 open=2026-05-20 20:25:37
  id=10222 token=ADA   dir=SHORT entry=0.24968000 hl_entry=0.24968000 open=2026-05-20 20:25:27
  id=10221 token=ASTER dir=SHORT entry=0.69264000 hl_entry=0.69264000 open=2026-05-20 20:25:17
  id=10220 token=BSV   dir=SHORT entry=15.01500000 hl_entry=15.01500000 open=2026-05-20 20:25:07
```

sync-guardian confirms: `Orphans (HL only): none` | `Missing (DB only): none` — perfect mirror.
Position Manager: `Open: 5 | Closed: 0 | Adjusted: 0`.

## Key Lesson

**Visual counting of triple-quoted multi-line Python strings is always wrong.** The VALUES line appears as one line in the source file but the actual bytes contain embedded newlines from how the string is laid out across lines 588–602. Always use byte-level inspection. Same applies to `_params` tuples spanning multiple lines with continuation — use actual execution or a depth-tracking parser, never line-of-sight counting.

## signal_compactor.py Line 843 — NOT a Bug

Previous session reported a crash at line 843 (`TypeError: execute expected at most 2 arguments, got 11`). Audit confirmed: `row[11]` indexes `hotset_entries` (not `cur.fetchall()` of a 2-column SELECT). Different variable, different data structure. No crash found there. Previous report was misdiagnosed.