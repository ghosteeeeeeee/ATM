# Trade Audit Workflow

How to trace a live trade back to its signal math and validate conditions at creation time.

## Step 1 — Trade Details from PostgreSQL

```bash
psql -h /var/run/postgresql -U postgres -d brain \
  -c "SELECT token, direction, entry_price, size, leverage, status, open_time, signal, confidence FROM trades WHERE token IN ('BLUR','IMX') AND status='open' ORDER BY open_time;"
```

Note: `signal_created_at` column is EMPTY — trade table doesn't track when signal was originally created.

## Step 2 — Execution Time from Pipeline Log

```bash
grep -a "EXEC.*BLUR\|EXEC.*IMX" /root/.hermes/logs/pipeline.log | tail -5
```

Each EXEC line has both pipeline timestamp and brain.py execution timestamp.

## Step 3 — Signal Math Detail at Execution Time

Signal detail lines appear in the signal_runner output block (~5 lines before the EXEC line):
```
LONG -accel-300 BLUR  conf=70% gap=0.443% growth=0.417% bars_since_cross=10 [accel-300+]
```

Format: `LONG -accel-300 TOKEN conf=70% gap=X.XXX% growth=X.XXX% bars_since_cross=N [accel-300+]`
Note: leading dash in "LONG -accel-300" (not "LONG accel-300+").

## Step 4 — Validate Against Script Thresholds

accel_300.py params (tightened 2026-05-11):
- MIN_GAP_PCT = 0.20% — gap must be >= this (abs value for SHORT)
- MIN_GAP_GROWTH_PCT = 0.05% — gap growth must be >= this
- bars_since_cross must be 1-10 (not 0, not >10)
- bars 1-3: gap_growth alone sufficient
- bars 4-10: requires marginal acceleration (delta_last > delta_prev)

## Step 5 — Regime Context

```bash
psql -h /var/run/postgresql -U postgres -d brain \
  -c "SELECT token, slope_4h, regime_4h, trend, regime_15m, updated_at FROM momentum_cache WHERE token IN ('BLUR','IMX','DASH','COMP');"
```

Compare direction vs regime_4h:
- LONG_BIAS + uptrend = regime-consistent LONG
- NEUTRAL = neutral regime
- LONG_BIAS + uptrend for a SHORT = counter-regime (allowed per T's rules, but highest risk)

## Step 6 — Confluence Check

Multi-source: `accel-300+,rs-s478` — two source tags.  
Single-source: just `accel-300+` (violation if in hot-set).

## Key Paths

| Item | Path |
|------|------|
| Pipeline log | /root/.hermes/logs/pipeline.log (~2.6M lines, ~204MB) |
| Brain DB | /var/run/postgresql, dbname=brain, no password (socket) |
| Trades table | brain.trades — column is `token` (not `symbol`) |
| momentum_cache | regime_4h, slope_4h, trend, regime_15m per token |
| Hotset | /var/www/hermes/data/hotset.json (NOT /root/.hermes/hot-set.json) |
| accel_300.py | /root/.hermes/scripts/signals/accel_300.py |
| rs.py | /root/.hermes/scripts/signals/rs.py |

## Known Data Gaps

- `signal_created_at` in brain.trades is always NULL — cannot measure signal-to-execution lag from DB alone
- Use pipeline log timestamps for signal age measurement
