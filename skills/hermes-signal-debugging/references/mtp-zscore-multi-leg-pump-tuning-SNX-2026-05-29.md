# mtp-zscore tuning: multi-leg pump moves — SNX case study

## The problem
mtp-zscore with tight Z bounds (Z_MAX=3.0 or Z_MAX=5.0) misses the START of multi-leg pump moves. When a coin gaps up or rips, the z-score is already extended — it gets rejected by Z_MAX before it can contribute a vote.

**SNX example (May 28, 15:25–18:30):**
- Move: 0.295 → 0.320 (+8.7%)
- At 16:24 when the leg started: z10=+1.18, z20=+1.29, z40=+1.59
- With Z_MIN=2.0: ALL below threshold → no fire until 16:24:43 (z20 crossed to +2.52, 16 seconds late)
- With Z_MIN=1.5: short period fires correctly, catches the move start

## Key findings from this session

### Finding 1: Z_MAX=3.0 or 5.0 causes rejection paradox
With Z_MAX=3.0, a z-score of 3.2 gets rejected even though it's clearly showing momentum.
- SNX max z10 in window: +2.73 (within Z_MAX=3.0, ok)
- But extended moves in other assets have hit z=5–8, getting rejected by Z_MAX=5.0
- **Fix:** Raise Z_MAX to 8.0. The z-score sign (direction) is what matters; absolute magnitude above a threshold doesn't indicate "too extended to trust."

### Finding 2: Z_MIN=2.0 with 20-bar lookback is too slow for move starts
At the onset of a new leg, the short lookback (20 bars) hasn't had time to accumulate a high z-score.
- SNX at 16:24: z20=+1.29 (below Z_MIN=2.0) → no fire
- Same bar, z10=+2.23 (10-bar lookback, faster response)
- **Fix:** Either lower Z_MIN to 1.5 for the short period, OR use shorter lookback (10 bars) for the short period

### Finding 3: 3/3 requirement with Z[1.5,8.0] 10/20/40 catches SNX
Best config found: `3/3 Z[1.5,8.0] LB=10/20/40`
- Fires at 16:24:43 (16 seconds after move start — acceptable)
- 46 fires over 4.5h window (15:00–18:30)
- All fires in same direction (LONG) — no reversals
- However: fires through chop phase (14:33–15:46) where z10 was elevated briefly

### Finding 4: CROSSING detector reduces noise fires
Original backtest used: `3/3 + CROSSING + Z[2.0,8.0] + LB=20/40/60`
- CROSSING = z must cross Z_MIN threshold (not just be above it)
- This filters out tokens that have been elevated above Z_MIN for a while (meaning the move isn't fresh)
- But with Z_MIN=2.0 + LB=20, SNX couldn't fire at 16:24 because z20 was only 1.29 at the exact start bar

## Recommended parameter ranges for pump detection

| Parameter | Original | Problem | Recommended |
|-----------|----------|---------|-------------|
| LB_SHORT | 14 | Too short for meaningful signal | 10–20 |
| LB_MID | 50 | N/A | 30–40 |
| LB_LONG | 150 | Too long for 1m data | 40–60 |
| Z_MIN | 2.0 | Too high for early move detection | 1.5 (short period) / 2.0 (mid/long) |
| Z_MAX | 3.0–5.0 | Rejects extended momentum | 8.0 |
| MIN_AGREE | 3 | N/A | 3 (keep) |
| CROSSING | No | N/A | Add for short period only |

## Quick backtest recipe for tuning mtp-zscore
```python
import sqlite3, datetime, statistics

conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()

# Target coin and time window
TOKEN = 'SNX'
START = datetime.datetime(2026, 5, 28, 14, 0, 0)
END   = datetime.datetime(2026, 5, 28, 18, 30, 0)
START_TS = int(START.timestamp())
END_TS   = int(END.timestamp())

cur.execute("""
    SELECT timestamp, price FROM price_history
    WHERE token = ? AND timestamp >= ? AND timestamp <= ?
    ORDER BY timestamp ASC
""", (TOKEN, START_TS, END_TS))
rows = cur.fetchall()

closes = [r[1] for r in rows]
times  = [r[0] for r in rows]

def zscore(values):
    if len(values) < 2: return None
    m = statistics.mean(values)
    s = statistics.stdev(values)
    return None if s == 0 else (values[-1] - m) / s

def backtest(closes, times, lb_s, lb_m, lb_l, z_min, z_max, min_agree):
    fires = []
    for i in range(lb_l + 2, len(closes)):
        zs = zscore(closes[i-lb_s:i])
        zm = zscore(closes[i-lb_m:i])
        zl = zscore(closes[i-lb_l:i])
        votes = []
        for z in [zs, zm, zl]:
            if z is None or abs(z) < z_min or abs(z) > z_max: continue
            votes.append('+' if z > 0 else '-')
        if len(votes) >= min_agree and len(set(votes)) == 1:
            fires.append((times[i], closes[i]))
    return fires

# Test config
fires = backtest(closes, times, lb_s=10, lb_m=20, lb_l=40, z_min=1.5, z_max=8.0, min_agree=3)
print(f"Fires: {len(fires)}, first: {datetime.datetime.fromtimestamp(fires[0][0]) if fires else 'none'}")
```

## Interaction with zscore_pump
mtp-zscore and zscore_pump are companion signals. zscore_pump handles the extreme-z (extended) regime while mtp-zscore handles the normalization regime. With Z_MAX raised to 8.0, mtp-zscore now handles both, reducing the need for zscore_pump in strong trends.

## Database note
- `signals_hermes.db` → `price_history` table: timestamps in **seconds**, most recent (~2 min stale)
- `candles.db` → `candles_1m` table: timestamps in **seconds** (divide by 1000 if seeing 1970 dates)
- Always check MAX(timestamp) before running backtests to know data freshness