---
name: gap-filling-price-collector
description: Fix silent time-series gaps in polled API price collection using carry-forward backfill with INSERT OR IGNORE collision safety
triggers:
  - price collector missing minutes
  - 429 rate limit gaps in time series
  - INSERT OR IGNORE skipping rows
  - stale/ghost bars in EMA SMA signals
---

# Skill: Gap-Filling Price Collection with Carry-Forward

## When to Use This

Any time-series price collection system that fetches from an API on a schedule (e.g., every 60s) and uses `INSERT OR IGNORE` or `INSERT OR REPLACE` to handle collisions. If the API returns a rate-limit error (429) or times out, the collection cycle is silently skipped — gaps appear in the time series with no indicator that data is missing.

This pattern is especially relevant for:
- Hyperliquid `allMids()` price collection
- Any cryptocurrency exchange REST API polled on a schedule
- Systems where `INSERT OR IGNORE` is used for "at-most-once" semantics

## The Core Problem

```
T+0:00   Collection succeeds  →  writes price P0 at ts=T
T+1:00   429 rate limit       →  nothing written (minute missing)
T+2:00   Collection succeeds  →  writes price P2 at ts=T+120
```

Result: The timeline jumps from T to T+120. `price_history` has no row at T+60. Downstream signals (EMA/SMA crossover, RSI, MACD) read this as a flat/zero-return bar or as a discontinuity. The gap is invisible to the collection system — `INSERT OR IGNORE` silently accepts the collision-free write at T+120.

The gap is only detectable by checking `MAX(timestamp)` for each token vs. the expected current time.

## The Fix: Gap-Filling with Carry-Forward

### Algorithm

1. **Before the insert loop**, batch-fetch `MAX(timestamp)` for all tokens in one query:
   ```sql
   SELECT token, MAX(timestamp) FROM price_history WHERE token IN (?,?,...) GROUP BY token
   ```

2. **After writing the current price** (INSERT OR IGNORE at `now`):
   ```python
   prev_ts = last_ts.get(sym_upper)
   if prev_ts is not None:
       gap_seconds = now - prev_ts
       if gap_seconds > 75:  # Missed at least one full cycle
           for t in range(prev_ts + 60, now, 60):
               c.execute(
                   'INSERT OR IGNORE INTO price_history(token, price, timestamp) VALUES(?, ?, ?)',
                   (sym_upper, price, t)
               )
   ```

3. **Gap threshold**: `> 75s` (not `> 60s`). Normal network jitter or a collection that runs at T+58 vs T+60 should not trigger backfill. 75s = 1 full cycle + 15s tolerance.

4. **Carry-forward price**: The *current* price is used for backfill bars (not the previous price). This is technically forward-fill from the API's perspective — the API returns the current price, and we use it to fill gaps backward in time. Rationale: if the price moved significantly during the gap, using the last known price (previous bar) would create a false flat/zero-return bar at the wrong price level. Using current price keeps the price series at a plausible level. The error introduced is bounded (worst case: one bar at the wrong price), vs. creating an invisible discontinuity in the EMA/SMA. Acceptable tradeoff for gap-300 which only cares about bar presence for continuity.

### Write Ordering: Current Price First

If the backfill hits a rate-limit (429) mid-batch:
- The transaction rolls back
- If current price was written LAST → entire transaction rolls back → current price lost
- If current price was written FIRST → current price is already committed → only backfill is lost

**Solution**: Write current price to `price_history` BEFORE attempting backfill rows. Wrap all in one transaction.

### Collision Safety

`INSERT OR IGNORE` uses the PRIMARY KEY or UNIQUE constraint. If a row already exists at that (token, timestamp), it is silently skipped. This means:
- If the pipeline ran twice in one minute (overlapping runs), the second run's insert at the same timestamp is ignored
- If backfill hits a row that was partially written by a previous run, it is silently skipped
- No overwriting of existing data

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| First collection ever (no prev_ts) | No backfill attempted |
| Normal 60s gap | No backfill (gap=60s ≤ 75s) |
| 1 missed cycle (121s gap) | 1 backfill bar at prev_ts+60 |
| N missed cycles (60×N+1 s gap) | N backfill bars |
| Backfill hits 429 | Only backfill rolls back; current price committed |
| Current price hits 429 | Nothing written; next cycle handles gap |
| Duplicate run (same ts) | `INSERT OR IGNORE` silently skips |

## Implementation Location

For Hermes: `/root/.hermes/scripts/signal_schema.py` → `upsert_prices_from_allMids()`

The function is called by `price_collector.py` every minute via systemd timer. The gap-fill logic is in the DB write function so it covers ALL callers automatically.

## Verification

```python
# Check a token for newly backfilled bars
sqlite3 /root/.hermes/data/signals_hermes.db "
  SELECT timestamp, datetime(timestamp,'unixepoch'), price 
  FROM price_history 
  WHERE token='BTC' 
  ORDER BY timestamp DESC 
  LIMIT 5"
```

## Key Empirical Finding

The systematic 121s gaps from HL rate limits are **invisible to gap-300's own gap detection**:
- gap-300 uses `BAR_GAP_THRESHOLD = max(150, mean + 3*std)` — typically 150s floor
- Observed systematic gaps: 121s (one missed collection cycle)
- 121s < 150s threshold → gap-300 never flags its own data as having gaps
- But the data is still degraded: ~175 missing bars in 700-bar windows, mean bar gap = 45.4s (vs expected 60s)
- Fix is in price collection (this skill), NOT in gap-300's gap detection

## Signals Affected

All signals that read from `price_history`:
- `gap300_signals.py` (EMA/SMA crossover)
- `zscore_momentum`
- RSI, MACD (from locally-aggregated candles)

With gap-filling:
- Timelines are continuous (no 121s jumps)
- EMA/SMA are computed over truly contiguous bars
- Gap-crossing signals have clean data

## Pitfalls

- **Do NOT use previous price for backfill** — carry-forward current price is safer (no look-ahead). However, for very large gaps (N>10), the price may have changed substantially. Acceptable tradeoff.
- **Do NOT write backfill before current price** — a 429 mid-batch would roll back everything including the current price.
- **Do NOT use `INSERT OR REPLACE`** for backfill — it would overwrite existing data if a partial write happened.
- **Threshold must be > 60s** to avoid false triggers on normal jitter. 75s is empirically chosen (1 cycle + 15s tolerance).
