# brain.py INSERT — VALUES / _params Count Verification (2026-05-20)

## Verified Facts

### SQL INSERT Structure (from brain.py lines 599-613)

**Columns (44 total):**
```
1   token
2   direction
3   amount_usdt
4   entry_price
5   exchange
6   strategy
7   paper
8   stop_loss
9   target
10  server
11  status
12  open_time          ← uses DEFAULT in VALUES (no param)
13  signal
14  confidence
15  token_address
16  pnl_usdt
17  pnl_pct
18  sl_distance
19  trailing_activation
20  trailing_distance
21  trailing_phase2_dist
22  leverage
23  experiment
24  flipped_from_trade
25  flip_variant
26  hl_entry_price
27  hl_notional_usdt
28  highest_price
29  lowest_price
30  signal_z_score
31  signal_rsi_14
32  signal_macd_hist
33  signal_macd_value
34  signal_macd_signal
35  signal_momentum_state
36  signal_z_score_tier
37  signal_decision
38  signal_leverage
39  signal_created_at
40  test_sl_variant
41  test_timing_variant
42  test_trailing_variant
43  _signal_metadata
44  _exp_metadata
```

**VALUES line (line 613):**
- Correct: `VALUES (%s×10, DEFAULT, %s×33)` — 10 %s before DEFAULT + DEFAULT + 33 %s = 44 items, 43 %s placeholders
- Wrong (original): 44 %s (all as placeholders, no DEFAULT keyword) — caused IndexError
- Wrong (intermediate bad fix): added `None` placeholder at wrong position (shifted subsequent columns)

### _col_map Structure (lines 521-568)

43 entries mapping column number → (col_num, col_name, value). Excludes open_time (handled by DEFAULT).
Params built as: `_params = [row[2] for row in _col_map]` — 43 items.

### Why psycopg2 raised IndexError

When `_params` has 43 items and SQL has 44 placeholders, the 44th placeholder gets no binding → psycopg2 raises `IndexError: tuple index out of range`. This is caught by the except block at line 616, which rolls back the transaction. The HL position has already been opened (line 450 `mirror_open` happens before the INSERT at line 598), so the rollback orphans the position.

## signal_compactor.py Line 843 Crash

```python
c.execute(sql, token, direction, side, amount, price, lev, strategy, server, now, now)
```

`sqlite3.Cursor.execute()` takes **at most 2 arguments**: `(sql, params)`. The call passes 11 positional arguments. Every `signal_compactor` run crashes here → hot-set never compacts → no new signals reach `decider_run`. **Primary pipeline blocker.**

## Debug Code Added to brain.py

Lines 519-585 added `_col_map` debug list + param/VALUES count validation before every INSERT attempt. Outputs:
```
[brain.py] DEBUG _col_map has 43 entries → 43 params (44 cols incl open_time DEFAULT)
[brain.py] DEBUG SQL VALUES items: 44 (10 %s + DEFAULT + 33 %s = 44)
```

## What WAS Wrong (Historical)

1. Original VALUES had 44 %s placeholders + NOW() as string literal — 44 placeholders for 43 params (open_time's NOW() had no param)
2. Patch attempt 1: changed to 44 %s + DEFAULT (still 44 placeholders, wrong count)
3. My fix (None at line 525): placed `None` placeholder at WRONG position in _params, shifting all subsequent columns — made it worse
4. Final correct fix: VALUES = `10×%s + DEFAULT + 33×%s` = 43 %s + 1 DEFAULT; _col_map = 43 entries (no open_time); params = 43 items

## Close Trade Bug (Already Patched)

UPDATE at line 755 originally had `WHERE id = %s` with no `status='open'` guard — vulnerable to double-close. Fixed to `WHERE id = %s AND status = 'open'`.