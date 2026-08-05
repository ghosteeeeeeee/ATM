# zscore-pump Full-Universe Backtest (2026-05-28)

## Status: READY TO RUN — backtest not yet executed

## Script Location
`/root/.hermes/scripts/backtest_zscore_pump_full.py` (v4 — pre-computed z-score architecture)

## Run Command
```bash
cd /root/.hermes/scripts && python3 -u backtest_zscore_pump_full.py > /root/.hermes/data/zscore_pump_backtest.log 2>&1
```

## Architecture (v4)
Pre-compute z-arrays once per (token, lookback), sweep thresholds on cached numpy arrays.

- **Lookbacks tested:** [30, 50, 75, 100, 150, 200]
- **Thresholds tested:** [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
- **Directions:** LONG, SHORT
- **Horizon:** 4h (240 bars)
- **Cooldown:** 20 bars
- **Universe:** 110 tokens (230 minus SHORT_BLACKLIST and LONG_BLACKLIST)

## Performance Numbers
| Scope | Naive (v1) | Pre-computed (v4) |
|-------|-----------|-------------------|
| Per LB/token | ~82s | ~0.63s |
| Full universe | ~89 min | ~7 min |

## Database
- Path: `/root/.hermes/data/candles.db`
- Table: `candles_1m` (NOT `ohlcv_1m`)
- Columns: `id, token, ts, open, high, low, close, volume`
- ts is seconds-since-epoch (NOT milliseconds)
- Query: `SELECT close FROM candles_1m WHERE token = ? ORDER BY ts ASC`

## Key Finding from Timing Test (BTC only)
All 6 lookbacks for BTC (60k bars) completed in 3.8s.
Estimated 110 tokens: 414s = 6.9 minutes for full universe.

## Current Production Constants (zscore-pump)
```php
ZSCORE_PUMP_THRESHOLD      = 3.0;
ZSCORE_PUMP_LOOKBACK       = 150;
ZSCORE_PUMP_COOLDOWN_BARS  = 20;  // memory says 20, code may have 5 — VERIFY
```

## Output
- Raw results: `/root/.hermes/data/zscore_pump_backtest_raw.json`
- Log: `/root/.hermes/data/zscore_pump_backtest.log`

## Expected Results Format (matching mtp-zscore backtest)
```json
[
  {"token": "BTC", "lookback": 30, "threshold": 1.5, "direction": "LONG",
   "fires": 1235, "wins": 618, "losses": 617, "wr": 50.0},
  ...
]
```