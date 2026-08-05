# brain.py add_trade() INSERT Debug — 2026-05-09

## The Bug

PostgreSQL INSERT in `brain.py` `add_trade()` has **42 expressions for 41 columns**.

```python
# Line 485 — VALUES line
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#  41 × %s placeholders + NOW() = 42 expressions total

# Line 472-484 — Column list (41 columns)
INSERT INTO trades (token, direction, amount_usdt, entry_price, exchange, strategy, paper,
    stop_loss, target, server, status, open_time,  ← NOW() fills open_time
    signal, confidence, token_address, pnl_usdt, pnl_pct,
    sl_distance, trailing_activation, trailing_distance, trailing_phase2_dist,
    leverage, experiment, flipped_from_trade, flip_variant,
    hl_entry_price, highest_price, lowest_price,
    signal_z_score, signal_rsi_14, signal_macd_hist, signal_macd_value, signal_macd_signal,
    signal_momentum_state, signal_z_score_tier,
    signal_decision, signal_leverage, signal_created_at,
    test_sl_variant, test_timing_variant, test_trailing_variant)
# 41 columns
```

**`NOW()` counts as 1 expression, not a placeholder.** So 41 `%s` + 1 `NOW()` = 42 expressions against 41 columns → `INSERT has more expressions than target columns`.

## History

- **Old code (c91e3ee)**: 25 columns, 24 `%s` + NOW() = 25 expressions → **balanced, worked**
- **New code (d31692f)**: 41 columns, 41 `%s` + NOW() = 42 expressions → **mismatch, broken**
- **Commit d31692f change**: Added 16 new columns (`hl_entry_price`, `highest_price`, `lowest_price`, `signal_*`, `test_*`) but only added `%s` placeholders for them, not an extra one

## How to Diagnose

```python
with open('brain.py', 'rb') as f:
    content = f.read()
start = content.find(b'INSERT INTO trades')
end = content.find(b'RETURNING id', start) + len(b'RETURNING id')
block = content[start:end]
vals_line = block[block.find(b'VALUES'):block.find(b'RETURNING')]
placeholders = vals_line.count(b'%s')
now_count = 1 if b'NOW()' in vals_line else 0
col_count = block[:block.find(b'VALUES')].decode().count(',') + 1  # rough count
print(f"Placeholders: {placeholders}, NOW(): {now_count}, Total: {placeholders+now_count}")
```

## The Fix

Remove **one** `%s` placeholder from the VALUES line (line 485).

Which one depends on which column maps to `None` in the tuple. The tuple has values for:
`token, direction, amount_usdt, entry_price, exchange, strategy, paper, stop_loss, target, server, 'open', signal, confidence, address, 0, 0, sl_distance, trailing_activation, trailing_distance, trailing_phase2_dist, leverage, experiment, flipped_from_trade, flip_variant, hl_entry, highest, lowest, signal_z_score, signal_rsi_14, signal_macd_hist, signal_macd_value, signal_macd_signal, signal_momentum_state, signal_z_score_tier, signal_decision, signal_leverage, signal_created_at, test_sl_variant, test_timing_variant, test_trailing_variant`

That's 41 tuple values. The VALUES has 41 placeholders + NOW() = 42 expressions. Remove one placeholder (the one mapped to `test_trailing_variant` which is `None`).

## Failure Signature in Logs

```
[brain.py] RC=1 stdout=[brain.py] ✔ no duplicate open in PostgreSQL for LTC
[brain.py] → mirror_open(LTC, LONG, entry_price=58.7975, leverage=5)
[HYPE Mirror] OPEN LONG 0.18 LTC @ signal=$58.835500 → HL_fill=$58.838000 (1 fill)
[brain.py] ❌ FAILED: stderr=(empty)
⚠️ ROLLBACK FAILED: sig#797986 already claimed by another process
```

`stderr=empty` means the INSERT error was caught by `except Exception` and printed to stdout via `print()`, not stderr.

## archive-trades.py Compatibility

`add_trade()` is called by `archive-trades.py` at line 501. The fix must not break that call path. archive-trades.py fetches the actual column list dynamically:

```python
def get_pg_columns(conn_pg):
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='trades' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
```

The PostgreSQL `trades` table has **96 columns** (confirmed via `information_schema.columns`). brain.py only writes 41 of them. This is fine — the other columns get default/NULL values.

## Key PostgreSQL Truths

- `NOW()` is a SQL function, counts as 1 expression in VALUES
- `RETURNING id` is part of the INSERT statement, not a separate expression
- Expression count = `%s` placeholders + any functions (NOW(), NOW()+interval, etc.)
- Always verify INSERT with a test before deploying — `psycopg2.FeatureNotSupported` or "more expressions than target columns"