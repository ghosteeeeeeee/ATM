# accel-300: Stale Detection Bar Bug — June 2026

## The Bug

`detect_accel_300` loop iterates ALL bars from `PERIOD+LOOKBACK` to `len(closes)-1` and returns the **first** passing bar. The stale gate (`bars_since_cross > 10`) measures bars_since_cross relative to the **detection bar i**, not the latest bar.

**Result**: A bar from 4 hours ago (i=344, 13:37:23) can pass all conditions with `bars_since_cross=1` because the EMA cross was at bar i-1 (one bar before detection). The stale gate passes. But from the latest bar (18:02), that cross is **354 bars old**.

**Signal fires with stale data** even though the stale gate says `bars_since_cross=1`.

## Reproduction

```python
# ME at 17:27:07 (signal created), price_history latest was 17:22:59
# Loop returns first passing bar at i=344 (13:37:23)
# bars_since_cross = 344 - 343 = 1  ← passes stale gate (1 < 10)
# bars_from_latest = 698 - 344 = 354 ← actual staleness
```

## The Fix

Add absolute stale gate at line 286 of `/root/.hermes/scripts/signals/accel_300.py`:

```python
bars_from_latest = len(closes) - 1 - i
if bars_from_latest > 10:
    continue
```

Detection bar must be within 10 bars of the latest bar — no stale signals.

## Verification

```python
from signals.accel_300 import detect_accel_300, _get_1m_prices
prices = _get_1m_prices('ME', lookback=700)
result = detect_accel_300('ME', prices)
# Before fix: LONG at i=344 (13:37:23), bars_from_latest=354
# After fix: None (stale signal blocked)
```

## EMA Calculation — Verified Correct

Standard EMA formula: `k = 2/(period+1)`, `EMA = price*k + prev_ema*(1-k)`. First valid EMA at index 299 (SMA warmup of first 300 bars). Verified against manual calculation at indices 299, 300, 350, latest — all match.

## DB Paths

- `/root/.hermes/data/signals_hermes.db` — price_history table (live 1m prices, used by `_get_1m_prices`)
- `/root/.hermes/data/signals_hermes_runtime.db` — signals table (runtime DB with signal history)
- `/root/.hermes/data/candles.db` — candles_1m table (backfill/analysis only)