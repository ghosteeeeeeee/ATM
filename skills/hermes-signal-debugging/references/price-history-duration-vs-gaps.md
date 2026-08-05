# price_history: Duration vs Gaps — Two Different Stale Problems

## Two Distinct Stale Data Problems

### Problem A: Data Gaps (Already Documented)
`price_history` has missing bars — token went minutes without updates. When fresh data arrives, the jump looks like a real price gap. Signal fires in wrong direction. **Solution**: bar-gap guard + adaptive threshold.

### Problem B: Insufficient Duration (NEW — 2026-05-13)
`price_history` is continuous (no missing bars) but too SHORT in total duration. The EMA(300) warmup only has 2.5 months of data instead of the 6-12 months needed for true convergence. The EMA itself is fundamentally wrong.

## 2026-05-13 Case Study

All losing trades entered when price was 1.3-3.8% BELOW EMA300 (per chart), but accel-300 fired LONG anyway. Signal log shows gap values of only 0.1-0.3% — far smaller than what a real EMA cross would produce.

**Investigation**:
- `price_history` for NEAR: starts March 2, 2026 — only ~2.5 months of history
- `candles.db` candles_1m: same data (March 2 start), not the issue
- EMA(300) warmup: needs ~1500 bars minimum for convergence; 700 bars for warmup
- With only 2.5 months, the 700-bar lookback pulls bars from early March — completely missing the actual trend behavior that should inform the EMA

**Why tiny gaps fired**: The EMA was wrong by 1-4% because it was calculated on insufficient history. Price was technically "above" the wrong EMA value by only 0.1-0.3% — triggering MIN_GAP_PCT=0.10.

## Key Diagnostic

```python
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()

for token in ['NEAR', 'BRETT', 'BERA', 'ATOM']:
    c.execute("SELECT MIN(ts), MAX(ts), COUNT(*) FROM price_history WHERE token=?", (token,))
    row = c.fetchone()
    start, end, count = row
    duration_days = (end - start) / 86400 if end and start else 0
    print(f"{token}: {count} bars, {duration_days:.0f} days ({start} to {end})")
    # EMA300 needs ~1500 bars minimum for convergence
    # 700-bar warmup = 9.7 hours — only useful if data goes back months
```

## Key Distinction

| | Data Gap (A) | Insufficient Duration (B) |
|---|---|---|
| Missing bars | YES | NO (continuous) |
| Total duration | Any | < 3 months |
| EMA correct? | No (frozen at last value) | No (wrong convergence) |
| Gap values in log | Large (1%+) | Tiny (0.1-0.3%) |
| Root cause | Rate limit / partial updates | Data source too shallow |

## Fix

Use `candles.db` (full Binance OHLCV history) for EMA calculations, NOT `price_history`. candles.db has complete 1m/5m/15m/1h/4h data going back to token launch.

For signal generation, the price source should be:
1. `candles.db` candles_1m for EMA(300) and price velocity
2. `price_history` ONLY for short-term (last 20-50 bars) confirmation

## Also: Two Parallel accel_300 Code Paths

| Path | File | MIN_GAP_PCT | PERSISTENCE_BARS | Running on May 13 |
|------|------|-------------|-----------------|-------------------|
| Old | `/root/.hermes/scripts/accel_300_signals.py` | 0.10 | 3 | YES |
| New | `/root/.hermes/scripts/signals/accel_300.py` | 0.20 | 2 | Commit de86b7c same day |

The old version (0.10, 3 bars) was live during the bad trades. Both paths may be active depending on which runner (`signal_gen.py` vs `signals_runner.py`) is executing.

## Staleness Check Bug

`detect_accel_300` uses `time.time()` (current wall clock) in its price age check — NOT the historical signal timestamp. This makes back-testing historical signals impossible (all appear "stale" at current time). Cannot fix without passing historical ts as argument.
