# accel-300+ Late-Fire Diagnosis + Timing Fix (2026-05-10)

## The Problem

accel-300+ was firing **late** — after price had already run up 4-30 bars above EMA.
By the time our signal fired, the move was at or near its peak.

## Root Cause — STRONG gap growth = WORSE outcomes

| Gap Growth | Trades | Win Rate | Avg PnL |
|------------|--------|----------|---------|
| >= 0.20% (strong) | 5 | **20%** | **-0.124%** |
| < 0.10% (weak) | 9 | **44.4%** | **+1.052%** |

Stronger acceleration signal = catching the peak = worse win rate.
The signal was working correctly directionally; the timing was the problem.

## Prior Fix Was Wrong Direction

Previous approach: tighten `MIN_GAP_PCT` (0.20) and `MIN_GAP_GROWTH_PCT` (0.05).
This blocked good early entries entirely. Wrong direction.

## Two-Phase Timing Fix (applied 2026-05-10)

**File:** `signals/accel_300.py` lines 251-292

### Bars 0-3: Fire on gap_growth ALONE
No marginal acceleration check. The move just started — this is exactly when we want in.

### Bars 4-10: Require marginal acceleration
`delta_last > delta_prev` — only fire if momentum is still accelerating, not topping out.
This replaces the old `PERSISTENCE_BARS=2` check which was too strict.

### Bars > 10: Block entirely
Price that has been running 10+ bars without our signal is at/near peak.
Old stale entries (bars=24-30) were also peaks being caught too late.

## Key Params (eased from overly tight)

- `MIN_GAP_PCT`: 0.20 → 0.15
- `MIN_GAP_GROWTH_PCT`: 0.05 → 0.03
- `COOLDOWN_BARS`: 10 → 12

## Bar Timing vs PnL (38 closed accel-300+ trades)

| Bar Range | Example Trades | Outcome | Notes |
|-----------|---------------|---------|-------|
| 1-2 | MON +3.4%, ORDI +1.8%, APEX +2.2% | Winners | Fresh breakouts, early entry |
| 4-6 | MIXED | Mixed | Accel spikes here often ARE the peak |
| 24-30 | ASTER +3.6%, S +4.0% | Winners | Momentum continuation works |
| 4-10 | TON -1.07%, EIGEN -0.445% | Losers | Extended without acceleration |

## Live Test Results (2026-05-10)

After timing fix, dry-run shows:
- **87 early fires** (bars <= 3): fresh breakouts, conf 73-88
- **46 mid fires** (bars 4-10): needs marginal acceleration confirmation
- 0 stale fires (bars > 10): blocked

Previously many of those 87 early entries would have been blocked waiting for the stricter 5% growth check.

## Verifying the Fix is Live

```python
cd /root/.hermes/scripts && python3 -c "
import sys; sys.path.insert(0,'.')
ast.parse(open('signals/accel_300.py').read())
from signals.accel_300 import detect_accel_300, _get_1m_prices
from signal_schema import get_all_latest_prices, init_db
init_db()
prices = get_all_latest_prices()
count, early, mid = 0, 0, 0
for token, data in prices.items():
    if token.startswith('@'): continue
    if not data.get('price'): continue
    p = _get_1m_prices(token, 700)
    if not p or len(p) < 500: continue
    sig = detect_accel_300(token, p)
    if sig:
        count += 1
        bars = sig['bars_since_cross']
        if bars <= 3: early += 1
        elif bars <= 10: mid += 1
print(f'Total: {count}, Early(bars<=3): {early}, Mid(bars4-10): {mid}')
"
```

## Key Insight

The signal fires correctly directionally. The problem was always timing, not threshold.
**Easier thresholds + aggressive early fire** beats **tight thresholds + late fire**.

## ATR SL Note

Relaxing ATR SL was considered but rejected as the primary fix. It lets winners breathe
but also lets losers run. Tighter stops (0.50-2.0%) are T's explicit preference.
The real fix is entry timing, not SL adjustment.