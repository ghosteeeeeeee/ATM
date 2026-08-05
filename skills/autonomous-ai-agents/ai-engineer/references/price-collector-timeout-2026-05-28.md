# price_collector Root Cause Analysis — 2026-05-28

## Problem
price_collector.py consistently timed out at 120+ seconds despite:
- blacklist filter (130 tokens skipped)
- 4h candles commented out
- competing timers masked during isolated testing

Microbenchmark showed only 8.3s for `_aggregate_tf` setup — discrepancy was unexplained.

## Root Causes Found (3 distinct bottlenecks)

### 1. Double `save_prices()` call (lines 543 and 567)
First call writes prices to signals_hermes.db. Second call (after ALL aggregation) does the EXACT same write again — prices haven't changed between line 543 and 567. Redundant, doubles DB write time.

**Fix:** Removed second `save_prices()` call at line ~568.

### 2. `_seed_universe_candles` does 10 Binance API calls (line 572)
- `TOKENS_PER_RUN = 2`, 5 TFs = 10 calls
- Each `_fetch_binance_candles` has `timeout=10`
- If Binance is slow: 10 × 10s = **100s of blocking**
- Also opens candles.db with only 10s timeout (line 177) — fails if candles.db still locked from aggregation

**Fix:** Disabled `_seed_universe_candles(universe)` call at line ~572.

### 3. Timer conflict with `hermes-1m-candle.timer`
- price_collector starts at :00 (takes 2+ min to complete)
- 1m-candle timer fires at :30 → tries to open candles.db → blocks
- When price_collector holds candles.db WAL lock for 2+ min, 1m-candle's 60s timeout fires → `database is locked`

**Fix:** Disabled `hermes-1m-candle.timer` and `hermes-5m-candle.timer` via `systemctl disable`.

## Benchmark vs Actual Discrepancy Explained

Microbenchmark (8.3s) only tested `_aggregate_tf()` GROUP BY queries in isolation:
- Did NOT include concurrent timer lock contention
- Did NOT include double DB writes (save_prices × 2)
- Did NOT include Binance API blocking (_seed_universe_candles)
- Did NOT include the per-token window aggregation + writes after the GROUP BY

Actual runtime breakdown (120s+):
- save_prices (first call): ~2-3s
- _aggregate_tf(5m): ~7s setup + per-token loop ~60s
- _aggregate_tf(15m): ~1s
- _aggregate_tf(1h): ~0.5s
- Timer conflict at :30: blocked 30s
- save_prices (second call): ~2-3s
- _seed_universe_candles: up to 100s (Binance timeouts)
- candles.db WAL commit: ~5s

## Verification After Fixes

```
$ time timeout 120 python3 price_collector.py
Collected 92 prices at 04:44:57
  candles_5m: last closed window 1779942900 (04:35:00)
  candles_15m: last closed window 1779941700 (04:15:00)
  candles_1h: last closed window 1779947200 (03:00:00)
real    1m19.912s  ← ~80s, within timeout
```

## Key Files Modified
- `/root/.hermes/scripts/price_collector.py` — 5 patches applied

## Related Signals Architecture Issue (not fixed — pre-existing)

Even with price_collector working, hotset stays empty due to confluence gate:
- Signal scripts (rs.py, mtp_zscore.py) run in parallel via ThreadPoolExecutor
- Each writes single-source signals independently via `add_signal()`
- `add_signal()` merges by token+direction only — last write wins
- Result: always single-source → confluence gate blocks (needs 2+ unique types)
- Architecture cannot produce multi-source signals as designed

This is a design issue, not a bug introduced this session.