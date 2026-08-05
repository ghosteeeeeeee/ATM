# accel-300 Duplicate Implementation Bug (2026-05-31)

## Bug Summary
**Status:** VERIFIED — signal_gen.py bypassed fixed signals/ version
**Root cause:** Two files, one deprecated but still imported by signal_gen

## Files
| File | Status | Path |
|------|--------|------|
| `accel_300_signals.py` | OLD deprecated, BROKEN | `/root/.hermes/scripts/accel_300_signals.py` |
| `signals/accel_300.py` | NEW, FIXED | `/root/.hermes/scripts/signals/accel_300.py` |

signal_gen.py line 2673: `from accel_300_signals import scan_accel_300_signals` — imports OLD, bypasses NEW.

## Bugs in OLD version

**Bug 1 (Condition 2) — blocks ALL SHORT signals:**
```python
# OLD line 220:
if gap_now < min_gap:
    continue

# For SHORT: min_gap=0.20 (positive), gap_now is negative (e.g. -0.30)
# -0.30 < 0.20 → True → BLOCKED
# This was meant to block signals with insufficient gap magnitude, but the sign check is wrong for SHORT.
# Fix: for SHORT use `if direction == 'SHORT' and gap_now > -min_gap`
```

**Bug 2 (Condition 4a) — gap growth formula wrong sign for SHORT:**
```python
# OLD line 245:
avg_gap_growth = gap_now - gap_then  # same formula for both directions!

# Example SHORT: gap_now=-0.30, gap_then=-0.20 (gap was widening)
# avg_gap_growth = -0.30 - (-0.20) = -0.10
# -0.10 <= 0.03 → True → BLOCKED (should pass since gap is widening)
# Correct SHORT: avg_gap_growth = gap_then - gap_now = -0.20 - (-0.30) = +0.10
```

**Bug 3 — No staleness gate:**
The NEW version (signals/accel_300.py) has a staleness gate that re-checks the newest bar after detection. The OLD version has no such gate — a signal detected at bar i is emitted without verifying the price at the newest bar still confirms the direction.

## Detection commands

```bash
# Find direct imports in signal_gen.py
grep -n "from accel_300_signals\|from gap300_signals\|from macd_accel\|from rs_signals\|from macd_1m_signals" /root/.hermes/scripts/signal_gen.py

# Check if signals/ version exists
ls /root/.hermes/scripts/signals/accel_300.py   # should exist
ls /root/.hermes/scripts/signals/gap300_signals.py  # etc.
```

## Fix

In signal_gen.py line 2673, change:
```python
from accel_300_signals import scan_accel_300_signals
```
to:
```python
from signals.accel_300 import scan_accel_300_signals
```

Then delete or rename the root-level `accel_300_signals.py` so it cannot be imported directly.

## Prevention

When migrating a signal to the signals/ folder: **delete or rename the root-level file**. Do not leave duplicates in place — signal_gen imports from the root directly and bypasses the signals/ registry entirely.