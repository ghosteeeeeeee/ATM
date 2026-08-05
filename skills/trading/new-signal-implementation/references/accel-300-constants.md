# accel-300 Signal Constants

Signal: `accel_300_signals.py` — persistent gap above EMA(300) with growing gap.

## Constant Location

**All direction-specific gap thresholds MUST live in `hermes_constants.py`, not locally.**

Import pattern:
```python
from hermes_constants import MIN_GAP_PCT_LONG, MIN_GAP_PCT_SHORT
```

Never define direction-specific thresholds locally in the signal script.

## Current Values

```python
# hermes_constants.py
MIN_GAP_PCT_LONG  = 0.25   # gap vs EMA300 to fire LONG (raised from 0.10)
MIN_GAP_PCT_SHORT = 0.10   # gap vs EMA300 to fire SHORT
```

## Why Asymmetric?

LONG over-fires with the same threshold as SHORT. Raising LONG to 0.25% (2.5x the SHORT value) reduces false breakouts while SHORT keeps the looser 0.10% threshold.

## Files

| File | Role |
|------|------|
| `/root/.hermes/scripts/accel_300_signals.py` | Detection engine + scanner |
| `/root/.hermes/scripts/hermes_constants.py` | Canonical values for MIN_GAP_PCT_LONG/SHORT |
| `/root/.hermes/data/signals_hermes_runtime.db` | Signal output |
