# ZScore Momentum Tuner Bug — Root Cause & Fix

**Bug:** Sweep always produced "Tuned 0 tokens" — running since Apr 12, 2026 (~35 failed runs).

## Root Cause

`get_all_token_prices()` used a **2-minute staleness cutoff**:
```python
cutoff = int(time.time()) - 120  # only gets last 2 minutes
cur.execute("SELECT token, price FROM price_history WHERE timestamp > ?", (cutoff,))
```
This returns 1-2 bars per token. The sweep needs 70+ bars minimum to backtest (MAX_LOOKBACK=60 + 10). Every token gets filtered out → "Tuned 0 tokens".

Meanwhile, `get_price_history()` (used by signal generation) fetches by **count**, no time cutoff — signal generation works fine.

The 2-min cutoff was a freshness guard for signal generation, applied incorrectly to sweep's data fetch.

## The Fix

**`get_all_token_prices_full()`** — no time cutoff, fetches by count:
```python
c2.execute("""
    SELECT price FROM (
        SELECT price, timestamp FROM price_history
        WHERE token = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ) sub
    ORDER BY timestamp ASC
""", (token, lookback_bars))
```

**Freshness gate in `run_sweep()`** — after loading data, check if 80%+ of tokens have >= 60 bars. If insufficient data, skip sweep entirely, **keep existing params** (do nothing). The old behavior was: always run, produce 0 tokens, overwrite tuner DB with nothing.

```python
all_prices = get_all_token_prices_full(lookback_bars=MAX_LOOKBACK * 4)
sufficient = sum(1 for p in all_prices.values() if len(p) >= 60)
total = len(all_prices)
if sufficient < total * 0.8:
    print("[zscore_momentum] Insufficient data for sweep. Keeping existing params.")
    return {}
```

**Key insight:** "Freshness" for sweep means "sufficient historical depth for backtesting", not "recent bars within 2 minutes". The price_history table gets ~1 bar/min/token updated live. In 2 minutes you get 2 bars — not enough. But historical data going back days/weeks is available and correct. The freshness check for sweep should verify bar count sufficiency, not recency.

## Performance

- `get_all_token_prices_full()`: 0.5s for 191 tokens, 191 individual queries at ~0.8ms each
- Full sweep (191 tokens × 286 param combos): ~6 min
- Old broken function: 0.4s but returned 2 bars/token → useless

## Verification

```bash
python3 /root/.hermes/scripts/zscore_momentum.py --sweep
```

Should show:
```
[zscore_momentum] Loading full price history for sweep...
[zscore_momentum] 191/191 tokens have >= 60 bars (need 80%: 153)
  0G: lookback=58, thresh=2.5, WR=94.4%, avg_pnl=0.48%, n=18
  ...
Sweep complete. Tuned N tokens.
```

## Related

- zscore_pump.py reads from same tuner DB (token_best_zscore_config) — tuning feeds signal generation
- signal_gen.py uses `get_price_history()` (count-based, correct) vs sweep's old `get_all_token_prices()` (time-cutoff, broken)