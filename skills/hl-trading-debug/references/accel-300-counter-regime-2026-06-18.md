# accel-300 Fires SHORT on Counter-Regime Data

**Date:** 2026-06-18
**Confirmed Cases:** SKY SHORT `accel-300-,rs-r74` (June 18 20:13 EDT), XMR SHORT `accel-300-,rs-s-broken` (June 19 01:17 UTC)
**Status:** ACTIVE

## SKY SHORT — Confirmed Counter-Regime Fire

Signal `accel-300-,rs-r74` executed at 20:13 EDT (00:13 UTC June 19).

### EMA300 Verification

Calculated from 481 SKY 1m candles fetched from HL API:

| Time (EDT) | Price | EMA300 | Gap |
|---|---|---|---|
| 20:10 | 0.057296 | 0.056880 | +0.73% |
| 20:13 | 0.057355 | 0.056889 | +0.82% |
| 20:14 | 0.057527 | 0.056893 | +1.11% |

Price was consistently ABOVE EMA300. `accel-300-` fired SHORT anyway.

### Data Gap in price_history

`signals_hermes.db` price_history for SKY: 33-minute gap (22:50–23:23 UTC) covering the signal window. accel-300 computed phantom gap_pct from stale data.

## Diagnostic

```bash
python3 -c "
import sqlite3, time, datetime
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
token = 'SKY'
c.execute('SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM price_history WHERE token=?', (token,))
cnt, mn, mx = c.fetchone()
print(f'{token}: {cnt} rows, newest: {datetime.datetime.fromtimestamp(mx)}, age: {(time.time()-mx)/60:.0f}min')
"
```

## Fix

In `accel_300.py`, add after fetchall: if `len(rows) < LOOKBACK_1M - 10`, return [] (insufficient data).
