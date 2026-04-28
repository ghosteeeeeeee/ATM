---
name: gap-300-warmup-debug
description: Debug gap-300 signal firing with insufficient warmup data — diagnose when SMA(300) is actually SMA(N) where N << 300
triggers:
  - gap-300 firing on a new or low-data token
  - gap-300 emitting signals that don't match market action
  - gap-300 signal name mismatch (effective period vs configured period)
---

# gap-300 Warmup Bug — Insufficient Data Causes Premature Firing

## Symptom
gap-300 fires for a token when it only has ~5 hours of 1m price_history, producing only 111 valid EMA/SMA bars instead of the required 300. The signal is mechanically correct (gap crossed threshold and widened) but semantically wrong — it's actually a gap-111 signal with an incorrectly calibrated threshold.

## Root Cause
`price_history` in `signals_hermes.db` is populated by `price_collector.py` running every minute, but for many tokens the historical depth is insufficient. When `gap300_signals.py` requests 400 bars via `_get_1m_prices()`, only 410 total rows exist (5.2 hours), yielding 111 valid EMA/SMA values after the PERIOD-1 warmup gap.

The SMA(111) vs EMA(10) gap is NOT a long-term momentum signal — it's a short-term cross using a misnamed indicator.

## How to Diagnose

```python
from gap300_signals import _ema_series, _sma_series, PERIOD
import sqlite3

# At signal time
c.execute('SELECT timestamp, price FROM price_history WHERE token=? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 410', (token, sig_ts))
rows = list(c.fetchall())
rows.reverse()
closes = [r[1] for r in rows]

ema_s = _ema_series(closes, PERIOD)
valid_count = sum(1 for e in ema_s if e is not None)
print(f"Valid bars: {valid_count} (need {PERIOD} for true gap-300)")

if valid_count < PERIOD:
    print(f"BUG: gap-{valid_count} not gap-300! SMA is only {valid_count}-period.")
```

## The Fix
In `gap300_signals.py`, add a minimum warmup guard in `detect_gap_cross`:

```python
# Require at least 150% of PERIOD to ensure SMA is meaningful
MIN_WARMUP_BARS = int(PERIOD * 1.5)  # 450 for PERIOD=300
if n < MIN_WARMUP_BARS:
    return None  # not enough data for reliable gap-300
```

Or alternatively: name the signal by its effective period, e.g., `gap-111-` when only 111 valid bars exist.

## Verification
- DYM had 410 total rows → 111 valid bars → fired gap-300- despite insufficient warmup
- `price_history` cadence: ~1 row per 60s (correct)
- `price_history` source: HL allMids mid-prices (correct, different from Binance last trade ~0.5%)
- Widening check: mechanically correct — gap went 0.051% → 0.078% over 8 bars (real widening on wrong-period data)

## Files Involved
- `/root/.hermes/scripts/gap300_signals.py` — needs MIN_WARMUP_BARS guard
- `/root/.hermes/data/signals_hermes.db` — `price_history` table, source for gap-300 signals
- `/root/.hermes/data/candles.db` — `candles_1m` table, Binance source (ground truth for price)

## Key Insight
gap-300 requires 300 warmup bars. The `LOOKBACK_1M = 400` in gap300_signals.py is insufficient for tokens with sparse or shallow price_history. A true SMA(300) needs at least 450-500 bars of 1m data (300 warmup + signal window + buffer).
