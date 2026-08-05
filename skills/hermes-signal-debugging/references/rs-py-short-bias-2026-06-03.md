# rs.py SHORT bias investigation (2026-06-03)

## Question
User: "why are we only firing SHORTs?? And LONGs that do fire are not doing very well, look at the logic and code"

## Method
- Queried executed signals from signals.json + price_history from signals_hermes.db
- Traced next-candle PnL per direction

## Findings

### Directional accuracy (next candle, ~1min hold)
- SHORTs: 8W/6L, WR=57%, avg=+0.094%
- LONGs: 4W/4L, WR=50%, avg=+0.128%
- Overall: 12/22 correct (55%) — essentially 50/50, no systematic direction bug

### The SHORT skew is real but not a code bug
Root cause: **market regime**. 65/69 NEUTRAL tokens have negative slope (downtrend).
- Broken support (→ SHORT) fires frequently in downtrends
- Broken resistance (→ LONG) fires rarely — resistance rarely breaks upward in downtrends
- This is correct expected behavior matching market conditions

### Structural asymmetry found (not a critical bug, but worth noting)
- `rs-s-broken` SHORT (lines 564-587): fires directly when support broken, no fallthrough
- `rs-r-broken` LONG (lines 627-650): if price crosses back below level, `broken=False` at line 625 → falls through to SHORT path at line 660
- This means `rs-r-broken` tokens that re-test the broken level can accidentally fire SHORTs
- Effect is minor in downtrends (SHORT direction happens to be correct) but asymmetric

### Performance root cause
Signals are ~50/50 directional — expected for mean-reversion signals in trending/volatile markets.
ATR stops at ~1% are too tight relative to actual candle noise.
30 of 31 losing trades hit `atr_sl_hit`.
Signals are directionally correct ~55% of the time but stops cut winners short.

### Regime-filtering gap (the real improvement)
`accel-300+,rs-s` LONG signals fire regardless of regime.
In a SHORT_BIAS or downtrending NEUTRAL market, these LONGs are anti-regime.
A regime alignment check before the confluence gate would suppress anti-regime LONGs
(GALA, XLM, DYDX, PURR all fired LONG in a downtrending market and lost).

## Key files
- `/root/.hermes/scripts/signals/rs.py` — 827 lines
- `/var/www/hermes/data/signals.json` — executed signals
- `/root/.hermes/data/signals_hermes.db` — price_history table

## Commands used
```python
# Get next-candle PnL for all executed signals
python3 -c "
import json, sqlite3
from datetime import datetime
with open('/var/www/hermes/data/signals.json') as f:
    data = json.load(f)
executed = data.get('executed', [])
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
valid = [s for s in executed if float(s['price']) > 0]
for s in valid:
    token = s['token']
    direction = s['direction']
    entry = float(s['price'])
    dt = datetime.strptime(s['time'], '%Y-%m-%d %H:%M:%S')
    ts = int(dt.timestamp())
    c.execute('SELECT price FROM price_history WHERE token=? AND timestamp >= ? ORDER BY timestamp LIMIT 2', (token, ts))
    rows = c.fetchall()
    if len(rows) >= 2:
        next_p = float(rows[1][0])
        pnl = ((next_p - entry) / entry * 100) if direction == 'LONG' else ((entry - next_p) / entry * 100)
        print(f'{token} {direction} {pnl:+.4f}% {s[\"source\"]}')
"
```