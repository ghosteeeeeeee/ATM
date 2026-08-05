# accel-300 Data Staleness Root Cause (2026-06-05)

## Symptom
All threshold changes (regime, stale cross, chop filter) were applied correctly.
`run(prices)` returned 0 signals despite conditions appearing to pass for BLZ and other tokens.
No signals in signals.json for 3+ hours despite market conditions that should fire.

## Root Cause
`_get_1m_prices()` reads from `price_history` table in `signals_hermes.db`.
This table was **8.7 days stale** — last update 2026-06-05, ~208 hours old.
The 120-second freshness gate on line 134 returned `[]` for every token,
causing ALL signal generation to return empty results — regardless of threshold values.

## Diagnosis Steps
```python
# Check price_history staleness
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute("SELECT MAX(timestamp), (strftime('%s','now') - MAX(timestamp))/3600 as age_hours FROM price_history")
print(c.fetchone())  # (>200 hours = stale)

# Check candles_1m freshness (live alternative)
c.execute("SELECT MAX(ts), (strftime('%s','now') - MAX(ts))/60 as age_min FROM candles_1m LIMIT 1")
print(c.fetchone())  # Should be <5 min
```

## Fix Applied
1. `_get_1m_prices()` data source: `price_history` → `candles_1m`
2. Freshness gate: 120s → 300s (5 min tolerance for slow-updating tokens)
3. CLI entry point (bottom of accel_300.py): also updated to use `candles_1m`
4. Docstring updated to reflect new data source

## Key Thresholds Changed (in accel_300.py, not hermes_constants)
- Regime slope: 0.02 → 0.10 → 0.03 (% per bar, 20-bar lookback)
- Regime lookback: 50 bars → 20 bars (captures recent momentum, not slow 50-bar avg)
- Stale cross: `bars_since_cross > 10` → `> 40` bars
- Chop filter: cross_gap ±0.25→±0.18, ema_angle ±0.10→±0.07, avg_gap_mag ±1.2→±0.9

## Lesson
When signal generation returns 0 results after threshold changes — and market conditions
visibly pass all checks — always verify the data pipeline is live before changing thresholds further.
Data staleness can mimic over-tightened logic. Check `price_history` age first.

## Files Modified
- `/root/.hermes/scripts/signals/accel_300.py` — `_get_1m_prices()` data source switch, 5 patches total
- `/root/.hermes/data/signals_hermes.db` — `price_history` (stale), `candles_1m` (live)