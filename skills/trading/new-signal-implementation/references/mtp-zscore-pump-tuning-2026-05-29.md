# mtp-zscore tuning for multi-leg pump moves

## Core problem
mtp-zscore with tight Z bounds (Z_MAX=3.0 or 5.0) and high Z_MIN (2.0) misses the START of multi-leg pump moves. When a coin rips, the z-score is already extended — it gets rejected by Z_MAX. At the onset of a new leg, the 20-bar z-score is only +1.29 — below Z_MIN=2.0.

## SNX case (May 28, 15:25–18:30 UTC)
- Token: SNX
- Move: 0.295 → 0.320 (+8.7% over ~3h, choppy with legs)
- First real leg start: 16:24, price 0.30008
- z20 at 16:24:27: only +1.29 (below Z_MIN=2.0)
- z10 at 16:24:43: +2.23 (crossed Z_MIN threshold)
- Fire time with Z[2.0,8.0] + LB=20/40/60 + 3/3 + CROSSING: 16:24:43 (16s late)
- Fire time with Z[1.5,8.0] + LB=10/20/40 + 3/3: 16:24:43

## Key findings
1. **Z_MAX=3.0 or 5.0 causes rejection paradox**: extended moves hit z=5–8, get rejected even though direction is clear
2. **Z_MIN=2.0 + 20-bar lookback = too slow**: at move start, short zscore hasn't accumulated enough
3. **Shorter short lookback (10 bars) helps**: z10 crosses Z_MIN=2.0 at move start while z20 still at 1.29
4. **Z_MIN=1.5 on short period works better**: lets the fast period fire as soon as momentum starts
5. **CROSSING detector is valuable but only if Z_MIN isn't too high**

## Recommended baseline for pump detection
```
LB_SHORT = 10   (was 14)
LB_MID   = 20   (was 50)  
LB_LONG  = 40   (was 150)
Z_SHORT_MIN = 1.5  (was 2.0) — short period only
Z_MID/Z_LONG_MIN = 2.0
Z_MAX = 8.0     (was 3.0)
MIN_AGREE = 3
```

This catches SNX at 16:24:43 (16 seconds after move start), 46 fires over 4.5h window, all same direction.

## Choppy period behavior
With these params on SNX 15:00–18:30:
- Fires through 14:33–15:46 chop where z10 briefly elevated: ~20 fires in chop vs ~26 in the actual move
- Adding short-period CROSSING (z10 must cross Z_MIN, not just be above it) reduces chop fires

## Quick backtest recipe
```python
import sqlite3, datetime, statistics
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute("SELECT timestamp, price FROM price_history WHERE token='SNX' AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC",
    (int(datetime.datetime(2026,5,28,14,0,0).timestamp()), int(datetime.datetime(2026,5,28,18,30,0).timestamp())))
rows=cur.fetchall()
closes=[r[1] for r in rows]; times=[r[0] for r in rows]
def zscore(v):
    if len(v)<2: return None
    m=statistics.mean(v); s=statistics.stdev(v)
    return None if s==0 else (v[-1]-m)/s
for i in range(50, len(closes)):
    zs=zscore(closes[i-10:i]); zm=zscore(closes[i-20:i]); zl=zscore(closes[i-40:i])
    votes=[('+' if z>0 else '-') for z in [zs,zm,zl] if z is not None and 1.5<=abs(z)<=8.0]
    if len(votes)==3 and len(set(votes))==1:
        print(datetime.datetime.fromtimestamp(times[i]).strftime('%H:%M'), closes[i])
```

## DB schema reminder
- `signals_hermes.db` → `price_history`: timestamps in **seconds** (not ms)
- `candles.db` → `candles_1m`: timestamps in **seconds**
- Always check MAX(timestamp) before backtesting