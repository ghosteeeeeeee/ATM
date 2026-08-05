# Signal Migration: Registry, Kill-Switches & Slow Signal Split (2026-05-06)

## Problem: Registry Showing 15 Instead of 23 Signals

**Symptom:** `get_registered_signals()` returns 15, not 23. The 8 migrated signals (pct_hermes, vel_hermes, hzscore, hmacd, mtf_momentum, momentum, phase_accel, fast_momentum) are silently dropped.

**Root Cause:** `SIGNAL_REGISTRY` used `PCT_HERMES_ENABLED` (etc.) as the `enabled` field value. When these master flags were flipped to `False` to block inline signal_gen.py, `get_registered_signals()` started filtering them out:

```python
SIGNAL_REGISTRY: list[dict] = [
    {'name': 'pct_hermes', 'enabled': PCT_HERMES_ENABLED, 'run': _pct_hermes_run},  # False!
]
def get_registered_signals():
    return [s for s in SIGNAL_REGISTRY if s['enabled'] and s['run'] is not None]  # filtered out
```

**Fix:** Hardcode `enabled=True` for migrated signals in the registry. Layer 2 `add_signal()` per-source filtering handles the real gate:

```python
SIGNAL_REGISTRY: list[dict] = [
    # NOTE: *_ENABLED master flags are False for these 8 (inline signal_gen blocked).
    # Registry versions always enabled here — Layer 2 add_signal() guard handles per-source filtering.
    {'name': 'pct_hermes', 'enabled': True, 'run': _pct_hermes_run},
    ...
]
```

## Problem: signals_runner Blocking Pipeline (120s Timeout)

**Symptom:** `signals_runner` takes ~120s for 21 fast signals. Pipeline step timeout was too tight.

**Root Cause:** (1) timeout was too tight, (2) `signal_gen` was still in STEPS_EVERY_MIN running in parallel with `signals_runner`, doubling compute, (3) slow signals (momentum, mtf_momentum) scanning 191 tokens take 180s each.

**Fix:**
1. Removed `signal_gen` from STEPS_EVERY_MIN (all inline flags were False — doing expensive computation for zero output)
2. Split into fast (every 1 min) / slow (every 5 min via STEPS_EVERY_5M)
3. Increased timeout to 300s for signals_runner

## Architecture: signal_gen → signals_runner Migration

**Before:** `run_pipeline.py` → `signal_gen.py` (inline signals embedded in one file)
**After:** `run_pipeline.py` → `signals_runner.py` → `run_all_signals()` → `scripts/signals/<name>.py`

**Kill-switch layers:**
- Layer 1: `hermes_constants.py` `*_ENABLED` flags — block inline signal_gen.py
- Layer 2: `signal_schema.py` `add_signal()` — per-source filtering via per-direction `*_PLUS_ENABLED`/`*_MINUS_ENABLED` flags
- Layer 3: `decider_run.py` — execution gate

**Key rule:** For migrated signals, registry entry = `enabled: True`. The master flag (`PCT_HERMES_ENABLED=False`) only blocks inline signal_gen.py. Registry scripts bypass Layer 1 entirely.

## Slow Signal Split

```python
# signals/__init__.py
_SLOW_SIGNALS = {'momentum', 'mtf_momentum'}

def get_fast_signals():
    return [s for s in get_registered_signals() if s['name'] not in _SLOW_SIGNALS]

def get_slow_signals():
    return [s for s in get_registered_signals() if s['name'] in _SLOW_SIGNALS]
```

```python
# run_pipeline.py
STEPS_EVERY_5M = ['signals_runner_slow']  # momentum, mtf_momentum

# In run():
if name == 'signals_runner_slow':
    name = 'signals_runner'
    args = ['--slow']
```

## Verified Kill-Switch Behavior

| Signal | Flag | Result |
|--------|------|--------|
| `pct-hermes-` | `PCT_HERMES_MINUS_ENABLED=False` | BLOCKED (Layer 2 confirmed) |
| `vel-hermes+` | `VEL_HERMES_PLUS_ENABLED=False` | BLOCKED (Layer 2 confirmed) |
| `vel-hermes-` | `VEL_HERMES_MINUS_ENABLED=True` | PASS |
| `pct-hermes+` | `PCT_HERMES_PLUS_ENABLED=True` | PASS |
| `accel-300+` | `ACCEL_300_ENABLED=True` | PASS |
| `hzscore+` | `HZSCORE_PLUS_ENABLED=True` | PASS |
| `momentum+` | `MOMENTUM_PLUS_ENABLED=True` | PASS |
| `momentum-` | `MOMENTUM_MINUS_ENABLED=True` | PASS |

## Files Changed

- `signals/__init__.py` — registry with `enabled=True` for migrated signals, fast/slow split
- `signals_runner.py` — `--slow` flag for slow signals
- `run_pipeline.py` — removed signal_gen, added signals_runner_slow to STEPS_EVERY_5M
- `scripts/signals/pct_hermes.py` — removed Layer 1 guard (commented)
- `scripts/signals/vel_hermes.py` — removed Layer 1 guard
- `scripts/signals/hzscore.py` — removed Layer 1 guard
- `scripts/signals/hmacd.py` — removed Layer 1 guard
- `scripts/signals/mtf_momentum.py` — removed Layer 1 guard
- `scripts/signals/momentum.py` — removed Layer 1 guard
- `scripts/signals/phase_accel.py` — removed Layer 1 guard
- `scripts/signals/fast_momentum.py` — removed Layer 1 guard
- `hermes_constants.py` — PCT_HERMES_ENABLED, VEL_HERMES_ENABLED, etc. set to False
- `signal_schema.py` — added `r2_rev+` and `r2_rev-` directional kill-switch checks

## Remaining Issue: Slow Signals Redundant Compute

`momentum` and `mtf_momentum` both scan 191 tokens and both call `get_all_latest_prices()` and `compute_regime()` independently. They run separately every 5 min but could share results. Optimization deferred to future session.
