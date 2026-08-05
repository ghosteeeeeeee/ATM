# accel-300 Direction Inversion — Jun 2026

## The Symptom
- AVNT SHORT trade: price above EMA300 → signal fired SHORT (wrong — should be LONG)
- AAVE LONG trade: price below EMA300 → signal fired LONG (wrong — should be SHORT)
- Signals were profitable but direction is inverted from what chart shows

## Root Cause Analysis

**Code is correct.** The direction logic in `detect_accel_300` at line 250:
```python
direction = 'LONG' if current_above else 'SHORT'
```
where `current_above = price > ema_val` — this is mathematically correct.

### Verified at Signal Time

| Token | Signal Time | Price | EMA300 | Price vs EMA | Code Direction | DB Direction |
|-------|-------------|-------|--------|--------------|----------------|--------------|
| AVNT | 10:28:45 | 0.10729 | 0.10518 | ABOVE | LONG | SHORT |
| AAVE | 11:06:50 | 60.5685 | 61.22 | BELOW | SHORT | LONG |

Code computes LONG for AVNT and SHORT for AAVE. DB has the opposite.

### Data Is Clean
- price_history has no gaps in the signal windows (confirmed zero gaps >60s)
- `_get_1m_prices` fetches from `signals_hermes.db` correctly
- `_ema_series` computation is correct (standard EMA, no bugs)
- `detect_accel_300` iterates from `PERIOD+LOOKBACK` to `len(closes)-1` — fires at newest bar

### The Contradiction
The current `accel_300.py` code could NOT have produced these signals given the price_history data at signal time. The code would have written the OPPOSITE direction.

**Possible explanations:**
1. The signals were generated at a moment when price_history data showed a different price/EMA relationship than what the chart shows now
2. There is a separate code path that writes signals with the opposite direction (checked — none found; `scan_accel_300_signals` is the only writer)
3. The `_get_1m_prices` data was populated differently at signal time (but user insists price_history is populated every minute)

## Key Files
- `/root/.hermes/scripts/signals/accel_300.py` — signal detection (correct)
- `/root/.hermes/scripts/accel_300_signals.py` — OLD version, identical detection logic
- `/root/.hermes/scripts/signal_compactor.py` — reads direction from DB, does NOT modify it
- signals_hermes_runtime.db — signals table: `id, token, direction, signal_type, source, price, created_at`

## Diagnostic Commands
```bash
# Trace signal direction at a specific bar
cd /root && python3 -c "
import sys, sqlite3, datetime
sys.path.insert(0, '/root/.hermes/scripts')
from signals.accel_300 import _ema_series, PERIOD, LOOKBACK
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute('''SELECT timestamp, price FROM price_history WHERE token=? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 700''', (token, signal_ts))
bars = list(reversed([(r[0], r[1]) for r in cur.fetchall()]))
closes = [b[1] for b in bars]
ema = _ema_series(closes, PERIOD)
newest_i = len(closes) - 1
price_above = closes[newest_i] > ema[newest_i]
direction = 'LONG' if price_above else 'SHORT'
print(f'At {datetime.datetime.fromtimestamp(bars[newest_i][0]).strftime(\"%H:%M:%S\")}: price={closes[newest_i]:.6f}, EMA={ema[newest_i]:.6f}, direction={direction}')
"
```

## Lessons
- User insisted data is clean; went in circles looking for gaps — stop challenging data assertions when user has confirmed
- "Stay focused on accel_300.py" — don't spiral into signal_compactor, signal_schema, etc.
- When code logic is verified correct and DB has wrong values, the issue is temporal: data was different at signal generation time
- The `_log` function in accel_300.py writes to `signals.log` — binary file, not readable by grep. Need `strings` or `zcat` to decode