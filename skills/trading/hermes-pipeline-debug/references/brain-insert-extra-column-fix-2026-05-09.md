# Brain.py INSERT Fix — How to Identify the Extra Column
**Date:** 2026-05-09

## The Systematic Debugging Approach

When `brain.py`'s `add_trade()` INSERT has a column/expression mismatch:

1. **Read the INSERT block byte-level** (see `hl-trading-debug/references/brain-insert-now-mismatch-2026-05-09.md`)
2. **Count placeholders vs columns** — always confirms mismatch direction
3. **Compare against `archive-trades.py`** to understand which columns are canonical

## Key Insight from archive-trades.py Comparison

`archive-trades.py` uses `get_pg_columns()` to dynamically fetch ALL 96 PostgreSQL columns from `information_schema.columns`. The INSERT in `brain.py` only writes 41 of them — this is fine, other columns get NULL/default.

But the 41-column INSERT in brain.py was designed to match what `archive-trades.py` expects to read. The 8 signal-indicator columns (`signal_z_score`, `signal_rsi_14`, etc., `test_sl/timing/trailing_variant`) MUST stay — they're what `archive-trades.py` reads.

## How to Determine Which Column Was Added

Comparing old vs new INSERT:

**Old (c91e3ee) — balanced:**
```
Columns: token, direction, amount_usdt, entry_price, exchange, strategy, paper,
         stop_loss, target, server, status, open_time,
         signal, confidence, token_address, pnl_usdt, pnl_pct,
         sl_distance, trailing_activation, trailing_distance, trailing_phase2_dist,
         leverage, experiment, flipped_from_trade, flip_variant
= 25 columns, 24 %s + NOW() = 25 expressions ✓
```

**New (d31692f) — broken:**
```
Added 16 columns: hl_entry_price, highest_price, lowest_price,
                  signal_z_score, signal_rsi_14, signal_macd_hist,
                  signal_macd_value, signal_macd_signal, signal_momentum_state,
                  signal_z_score_tier, signal_decision, signal_leverage,
                  signal_created_at, test_sl_variant, test_timing_variant,
                  test_trailing_variant
= 41 columns, 41 %s + NOW() = 42 expressions ✗
```

The **16 new columns** were added but only 16 `%s` placeholders added — making it 41 placeholders instead of 40. The `NOW()` fills `open_time` (no placeholder for it), so the count is:
- Columns: 25 old + 16 new = 41
- Placeholders: 24 old + 16 new = 40 (before `NOW()`)
- `NOW()` = 1 expression
- Total expressions: 40 + 1 = 41 ✓ SHOULD BE

But VALUES line shows 41 placeholders, not 40. So **one placeholder was accidentally duplicated** during the expansion.

## The Fix

Remove one `%s` placeholder from the VALUES line. The duplicated column is whichever maps to a tuple value of `None`.

**Test fix before deploying:**
```python
# In brain.py working directory
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()
# Use 40 placeholders + NOW() = 41 expressions for 41 columns
query = "INSERT INTO trades (col1,col2,...,col41) VALUES (" + ",".join(["%s"]*40) + ",NOW()) RETURNING id"
try:
    cur.execute(query, [f'test_{i}' for i in range(40)])
    print("FIXED: 40 placeholders + NOW() = 41 expressions works")
    conn.rollback()
except Exception as e:
    print(f"Still broken: {e}")
    conn.rollback()
cur.close()
conn.close()
```