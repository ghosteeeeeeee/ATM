# accel-300: Actual Bugs Found — June 2026

**Audit note**: The original version (485 lines, git SHA `098caa4`) is the ONLY version that ever existed. There was no separate "patched version" with CHOP filter/cross_back/EMA angle — that was a false memory from earlier session context. All fixes described below are on the actual 485-line version.

---

## Bug 1: Stale Detection Bar — SIGNALS FIRE ON OLD DATA

**File**: `/root/.hermes/scripts/signals/accel_300.py`, lines 191-310

**Problem**: The loop iterates ALL bars from `PERIOD+LOOKBACK` to `len(closes)-1` and returns the **first** passing bar. `bars_since_cross` is measured relative to detection bar `i`, not the latest bar. A bar from 4 hours ago can have `bars_since_cross=1` (cross was at i-1, just one bar before detection), passing the stale gate. But from the latest bar, that cross is 354 bars old.

**Example (ME)**: Signal at i=344 (13:37:23) with `bars_since_cross=1` → stale gate passes. But from latest bar (18:02), cross is 354 bars old. Price is above EMA300 but signal fires SHORT.

**Fix** (line 286):
```python
bars_from_latest = len(closes) - 1 - i
if bars_from_latest > 10:
    continue
```

**Verification**:
```python
from signals.accel_300 import detect_accel_300, _get_1m_prices
prices = _get_1m_prices('ME', lookback=700)
result = detect_accel_300('ME', prices)
# Before fix: LONG at i=344, bars_from_latest=354
# After fix: None (stale blocked)
```

---

## Bug 2: Condition 1 Blocks Sustained Trends (pre-fix state)

**Problem**: `if current_above and not was_below_recently: continue` — if price crossed EMA 442 bars ago and stayed below, `was_below_recently=False` within LOOKBACK=30 bars → blocked.

**Fix**: Fallback cross_bar detection (walk backward to find sequence start, not most recent bounce). Conditional stale gate — only apply to primary crosses, not fallbacks.

---

## EMA Calculation — Verified Correct

Standard EMA: `k=2/(300+1)=0.0066445183`, `EMA=price*k + prev*(1-k)`. First valid at index 299 (SMA warmup). Verified against manual calculation — correct.

---

## DB Paths

- `/root/.hermes/data/signals_hermes.db` → `price_history` table (live 1m prices, used by `_get_1m_prices`)
- `/root/.hermes/data/signals_hermes_runtime.db` → `signals` table (signal history)
- `/root/.hermes/data/candles.db` → `candles_1m` (backfill/analysis only)

---

## Testing Pattern

```python
from signals.accel_300 import detect_accel_300, _get_1m_prices, _ema_series

prices = _get_1m_prices('ME', lookback=700)
closes = [p['price'] for p in prices]
ema = _ema_series(closes, 300)
assert ema[-1] is not None

result = detect_accel_300('ME', prices)
# Verify detection bar staleness:
n = len(closes)
for i in range(300+30, n-1):
    gap = (closes[i] - ema[i]) / ema[i] * 100
    if abs(gap - result['gap_pct']) < 0.001:
        bars_from_latest = n - 1 - i
        print(f'Detection bar i={i}, bars_from_latest={bars_from_latest}')
        break
```