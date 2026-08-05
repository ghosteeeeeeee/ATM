# Per-Direction Signal Killswitches — Implementation Audit

**Date:** 2026-05-12
**Context:** Added per-direction flags (+ for LONG, - for SHORT) to all signal modules.

---

## What Was Added

### hermes_constants.py — 26 new flags (lines ~437-465)

```python
# ── Per-Direction Signal Killswitches ─────────────────────────────────────────
# For each signal: _PLUS_ENABLED controls LONG, _MINUS_ENABLED controls SHORT.
# Default True so existing signals continue working. Set False to block one direction.
ATR_COMPRESSION_PLUS_ENABLED   = True    # atr_compression+ LONG
ATR_COMPRESSION_MINUS_ENABLED   = True    # atr_compression- SHORT
...
```

### signals/__init__.py — Updated imports to include all new flags

All new flags are now imported at the top of `signals/__init__.py`.

---

## Patterns Used Across Modules

### Pattern A: Simple direction variable (ema9_sma20, macd_accel, r2_rev, r2_trend, ema20_50)
```python
# ── Per-direction kill-switch ─────────────────────────────────────────
from hermes_constants import {NAME}_PLUS_ENABLED, {NAME}_MINUS_ENABLED
if direction == 'LONG' and not {NAME}_PLUS_ENABLED:
    continue
if direction == 'SHORT' and not {NAME}_MINUS_ENABLED:
    continue
sid = add_signal(...)
```

### Pattern B: Loop over ['LONG', 'SHORT'] (exhaustion, trend_purity, guppy)
```python
for direction in ['LONG', 'SHORT']:
    # ── Per-direction kill-switch ─────────────────────────────────────────
    from hermes_constants import {NAME}_PLUS_ENABLED, {NAME}_MINUS_ENABLED
    if direction == 'LONG' and not {NAME}_PLUS_ENABLED:
        continue
    if direction == 'SHORT' and not {NAME}_MINUS_ENABLED:
        continue
    sig = detect_{name}(token, direction, ...)
```

### Pattern C: Signal dict with 'direction' key (atr_compression, volume_hl)
```python
if sig is None:
    continue
# ── Per-direction kill-switch ─────────────────────────────────────────
from hermes_constants import {NAME}_PLUS_ENABLED, {NAME}_MINUS_ENABLED
if sig['direction'] == 'LONG' and not {NAME}_PLUS_ENABLED:
    continue
if sig['direction'] == 'SHORT' and not {NAME}_MINUS_ENABLED:
    continue
sid = add_signal(...)
```

### Pattern D: Two-variant signals (hh_hl breakout + pullback)
```python
if sig:
    # ── Per-direction kill-switch ─────────────────────────────────────────
    from hermes_constants import HH_HL_PLUS_ENABLED, HH_HL_MINUS_ENABLED
    blocked = (
        (sig['direction'] == 'LONG' and not HH_HL_PLUS_ENABLED) or
        (sig['direction'] == 'SHORT' and not HH_HL_MINUS_ENABLED)
    )
    if blocked:
        pass  # skip this variant, fall through to next
    else:
        sid = add_signal(...)
```

**WARNING:** The `pass` approach only works when wrapped in `if blocked: pass / else:`. Never use `if/elif/else` with bare `pass` for blocked directions — the `else` fires even when `pass` was taken. The `blocked = (...)` boolean variable pattern is the correct fix.

---

## Verified Correct (11 files)

- `exhaustion.py` ✓
- `guppy.py` ✓
- `macd_accel.py` ✓
- `r2_rev.py` ✓
- `r2_trend.py` ✓
- `trend_purity.py` ✓
- `ema20_50.py` ✓
- `ema9_sma20.py` ✓
- `atr_compression.py` ✓
- `ma300_candle_confirm_signals.py` ✓
- `ma300_candle_confirm.py` (wrapper only, no kill-switch) ✓

---

## Bug Found: hh_hl.py `pass` bug (P0 — fixed)

**Symptom:** When HH_HL_PLUS_ENABLED=False, LONG breakout signals still fired.

**Root cause:** `if/elif/else` with bare `pass` — the `else` fired even when `if` matched and `pass` executed.

```python
# WRONG:
if sig['direction'] == 'LONG' and not HH_HL_PLUS_ENABLED:
    pass  # still run pullback check
elif sig['direction'] == 'SHORT' and not HH_HL_MINUS_ENABLED:
    pass
else:
    sid = add_signal(...)  # ← FIRES EVEN WHEN PASS WAS TAKEN!
```

**Fix:** Boolean `blocked` variable + single `if/else`:

```python
# CORRECT:
blocked = (
    (sig['direction'] == 'LONG' and not HH_HL_PLUS_ENABLED) or
    (sig['direction'] == 'SHORT' and not HH_HL_MINUS_ENABLED)
)
if blocked:
    pass  # skip breakout, fall through to pullback check
else:
    sid = add_signal(...)
```

---

## Pre-existing P0: SIGNAL_SOURCE_BLACKLIST = {} (unfixed)

**Location:** hermes_constants.py line 104

**Problem:** All source-based blocking is completely bypassed. The dict is opened but only commented-out entries follow (lines 105-139).

**Impact:** Any signal with a blacklisted source name will not be blocked at the signal_schema.py level.

---

## Flag Naming Convention

| Flag suffix | Direction | Meaning |
|-------------|-----------|---------|
| `*_PLUS_ENABLED` | LONG | Signal fires for LONG direction |
| `*_MINUS_ENABLED` | SHORT | Signal fires for SHORT direction |

Naming rationale: `+` = LONG (bullish), `-` = SHORT (bearish) — consistent with source name convention (`source+` = LONG, `source-` = SHORT).

---

## Compile Verification Command

```bash
cd /root/.hermes/scripts && python3 -m py_compile \
  signals/ma_cross.py signals/gap_300.py signals/ma_cross_5m.py \
  signals/atr_compression.py signals/ema9_sma20.py signals/exhaustion.py \
  signals/guppy.py signals/hh_hl.py signals/macd_accel.py \
  signals/r2_rev.py signals/r2_trend.py signals/trend_purity.py \
  signals/volume_hl.py signals/ma300_candle_confirm.py \
  signals/ema20_50.py signals/macd_1m.py \
  ma300_candle_confirm_signals.py signals/__init__.py hermes_constants.py
```

---

## Runtime Verification (ma_cross as example)

```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import hermes_constants as hc
import importlib

# Block LONG, allow SHORT
hc.MA_CROSS_PLUS_ENABLED = False
hc.MA_CROSS_MINUS_ENABLED = True

import signals.ma_cross as mc
importlib.reload(mc)
result = mc.run()
print(f"LONG blocked, SHORT allowed: result={result}")
```