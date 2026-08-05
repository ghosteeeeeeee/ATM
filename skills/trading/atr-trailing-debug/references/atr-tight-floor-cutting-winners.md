# ATR Floor Too Tight — Cutting Winners Short (2026-05-05)

## Symptom
May 5 data: 90% of trades hit ATR SL. Winners average +0.478% but losers average -0.283%. The stops are so tight they trigger on winning trades before they can run.

## Evidence (128 trades, May 5)
```
SL hit rate:  90% (115/128 trades)
Winners avg: +0.478%
Losers avg:  -0.283%
```

Winners are being stopped out at +0.48% when the system should be holding for +2-4%+ exits.

## Root Cause
`MIN_ATR_PCT=0.50%` floor in `position_manager.py` — SL can't go below 0.50% of price. On volatile coins, a 2% adverse move hits the SL in seconds.

## Current T's ATR params (from memory)
```
MIN_ATR_PCT=0.50%  ← PROBLEM: too tight
MAX_SL=2.0%
MIN_TP=0.75%
MAX_TP=5.0%
k_tp=k×1.25
```

## Recommended Fix
Raise `MIN_ATR_PCT` floor from 0.50% to 1.5%:
```
MIN_ATR_PCT=1.50%  ← floor: SL can't be tighter than 1.5%
MAX_SL=3.0%        ← cap: absolute maximum SL width
```

## Verification Query
```python
import json
with open('/var/www/hermes/data/trades.json') as f:
    d = json.load(f)
closed = d['closed']
losers = [t for t in closed if t.get('pnl_pct', 0) < 0]
near_losers = [t for t in losers if -0.5 < t['pnl_pct'] < 0]
print(f"Losses in 0-0.5% range: {len(near_losers)}/{len(losers)}")
```

If most losers are in the -0.3% to -0.5% range, the ATR floor is too tight — these are winners that got stopped early.
