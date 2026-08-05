# TON ATR TP/SL Case Study — 2026-05-27

## Question
T asked: "can you figure out what ATR TP/SL k-value and phase multipliers are currently for TON"

## Approach
**Critical lesson**: `get_atr()` returns `None` when the cache is stale (TTL=300s, cache age was 377,904s).
When cache is stale, read it directly from the JSON file:

```python
import json
cache_file = '/root/.hermes/data/atr_cache.json'
with open(cache_file) as f:
    data = json.load(f)
ton_atr = data['TON']['atr']  # returns float even if stale
```

Then compute manually using `tpsl_utils._atr_tier()` logic, NOT via the cached getter.

## TON Data

| Field | Value |
|-------|-------|
| Price (from signals_hermes.db latest_prices) | $1.92155 |
| ATR (15m, from atr_cache.json) | $0.01415 |
| Cache timestamp | 1779476045 (~377,904s ago — STALE) |
| ATR% = ATR / entry | 0.736% |

## Base k Tier — LOW_VOL

`ATR_PCT_LOW_THRESH = 0.01 (1%)`, `ATR_PCT_HIGH_THRESH = 0.015 (1.5%)`

- ATR% (0.736%) < 1% → `ATR_K_LOW_VOL = 0.5`
- NOT using NORMAL_VOL or HIGH_VOL tiers

## k_tp = base_k × ATR_TP_K_MULT

```
k_tp = 0.5 × 1.25 = 0.625
```

## Raw SL/TP Percentages

```
sl_pct = base_k × atr_pct = 0.5 × 0.00736 = 0.00368 = 0.368%
tp_pct = k_tp × atr_pct = 0.625 × 0.00736 = 0.00460 = 0.460%
```

## NEW Trade Floors (is_new_trade = True)

| Parameter | Floor | Applied? | Result |
|-----------|-------|----------|--------|
| `ATR_SL_MIN_INIT = 0.01` (1.0%) | max(0.368%, 1.0%) = 1.0% | ✓ SL floored UP to 1.0% |
| `ATR_SL_MAX_INIT = 0.015` (1.5%) | SL capped at 1.5% | ✓ within cap |
| `ATR_TP_MIN = 0.015` (1.5%) | max(0.460%, 1.5%) = 1.5% | ✓ TP floored UP to 1.5% |

**Effective SL% for new TON trade: 1.00%**
**Effective TP% for new TON trade: 1.50%**

## ESTABLISHED Trade Floors (is_new_trade = False)

| Parameter | Floor | Applied? | Result |
|-----------|-------|----------|--------|
| `ATR_SL_MIN_ACCEL = 0.05` (5.0%) | max(0.368%, 5.0%) = 5.0% | ✓ SL floored UP to 5.0% |
| `ATR_TP_MIN_ACCEL = 0.015` (1.5%) | max(0.460%, 1.5%) = 1.5% | ✓ TP floored UP to 1.5% |

**Effective SL% for established TON trade: 5.00%**
**Effective TP% for established TON trade: 1.50%**

Note: ATR_SL_MIN_ACCEL=0.05 means 5.0%, NOT 0.05%. The constant name is misleading.

## Phase Multipliers

Phase multipliers only apply when `momentum_stats` is provided to `compute_atr_sl_tp()`.
They scale the base_k (0.5 for TON):

| Phase | Stall (vel < 0) | Fast (speed_pctl ≥ 70) | Slow (speed_pctl < 70) |
|-------|----------------|------------------------|-------------------------|
| neutral / building | 1.0 | 1.0 | 1.0 |
| accelerating | 0.06 → k=0.0300 | 0.05 → k=0.0250 | 0.04 → k=0.0200 |
| exhaustion | 0.02 → k=0.0100 | 0.03 → k=0.0150 | 0.02 → k=0.0100 |
| extreme | 0.01 → k=0.0050 | 0.02 → k=0.0100 | — |

## Key Constants from hermes_constants.py (lines 273–354)

```python
# TP multiplier
ATR_TP_K_MULT = 1.25   # TP tighter than SL: k_tp = k × 1.25

# SL floors/caps
ATR_SL_MIN = 0.007      # 0.50% — generic trailing SL floor
ATR_SL_MAX = 0.012      # 1% cap
ATR_TP_MIN = 0.015      # 1.5% floor
ATR_TP_MAX = 0.05       # 5% cap

# New trade
ATR_SL_MIN_INIT = 0.01  # 1.0% — new trade SL floor
ATR_SL_MAX_INIT = 0.015 # 1.5% — new trade SL cap

# Established trade
ATR_SL_MIN_ACCEL = 0.05  # 5.0% — established trade SL floor (0.05 = 5.0%)
ATR_TP_MIN_ACCEL = 0.015 # 1.5% — established trade TP floor

# Base k tiers
ATR_K_LOW_VOL = 0.5     # < 1% ATR
ATR_K_NORMAL_VOL = 1.0  # 1%–1.5% ATR (note: old value was 2.0, current 1.0 per T's tweak)
ATR_K_HIGH_VOL = 0.25   # > 1.5% ATR

# Phase tiers (numeric)
PHASE_TIER_NEUTRAL = 0
PHASE_TIER_BUILDING = 1
PHASE_TIER_ACCELERATING = 2
PHASE_TIER_EXHAUSTION = 3
PHASE_TIER_EXTREME = 4

# Phase multipliers (applied to base_k)
K_PHASE_ACCEL_STALL = 0.06
K_PHASE_ACCEL_FAST = 0.05
K_PHASE_ACCEL_SLOW = 0.04
K_PHASE_EXH_STALL = 0.02
K_PHASE_EXH_FAST = 0.03
K_PHASE_EXH_SLOW = 0.02
K_PHASE_EXT_STALL = 0.01
K_PHASE_EXT_FAST = 0.02
```

## Diagnostic Script

```python
import json, os
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import (
    ATR_K_LOW_VOL, ATR_K_NORMAL_VOL, ATR_K_HIGH_VOL,
    ATR_PCT_LOW_THRESH, ATR_PCT_HIGH_THRESH,
    ATR_TP_K_MULT, ATR_SL_MIN_INIT, ATR_TP_MIN,
    ATR_SL_MIN_ACCEL, ATR_TP_MIN_ACCEL,
)

cache_file = '/root/.hermes/data/atr_cache.json'
with open(cache_file) as f:
    data = json.load(f)
ton = data['TON']
atr = ton['atr']
ts = ton['ts']
age = 1779853949 - ts  # current time - cache time

entry = 1.92155  # from latest_prices
atr_pct = atr / entry

if atr_pct < ATR_PCT_LOW_THRESH:
    base_k = ATR_K_LOW_VOL
elif atr_pct > ATR_PCT_HIGH_THRESH:
    base_k = ATR_K_HIGH_VOL
else:
    base_k = ATR_K_NORMAL_VOL

k_tp = base_k * ATR_TP_K_MULT
sl_pct = base_k * atr_pct
tp_pct = k_tp * atr_pct

eff_sl_new = max(sl_pct, ATR_SL_MIN_INIT)
eff_tp_new = max(tp_pct, ATR_TP_MIN)
eff_sl_est = max(sl_pct, ATR_SL_MIN_ACCEL)
eff_tp_est = max(tp_pct, ATR_TP_MIN_ACCEL)

print(f"TON ATR: {atr:.6f}, age: {age:.0f}s, ATR%: {atr_pct*100:.3f}%")
print(f"base_k={base_k}, k_tp={k_tp}, raw_sl={sl_pct*100:.3f}%, raw_tp={tp_pct*100:.3f}%")
print(f"NEW → SL: {eff_sl_new*100:.2f}%, TP: {eff_tp_new*100:.2f}%")
print(f"EST → SL: {eff_sl_est*100:.2f}%, TP: {eff_tp_est*100:.2f}%")
```

## Key Learning: Cache Staleness

`get_atr()` in `atr_cache.py` returns `None` when cache age > 300s (TTL).
Even when it returns `None`, the ATR value is still in the JSON file (just stale).
Always read from the JSON file directly for historical/audit purposes.
`get_atr()` is for live trading decisions where you need fresh data.

## Relevant Source Files

- `tpsl_utils.py` — `_atr_tier()`, `_phase_from_pct()`, `_atr_sl_k_scaled()`, `compute_atr_sl_tp()`
- `atr_cache.py` — `get_atr()` (returns None if stale), `save_atr()`
- `hermes_constants.py` lines 273–354 — all ATR TP/SL constants
- `/root/.hermes/data/atr_cache.json` — raw ATR cache (direct read for stale data)
- `/root/.hermes/data/signals_hermes.db` latest_prices — current price for entry_price