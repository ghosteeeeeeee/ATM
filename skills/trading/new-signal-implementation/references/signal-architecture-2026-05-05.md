# Signal Architecture — 2026-05-05 Migration

## Old Architecture

```
signal_gen.py (2742 lines) — monolith with 8+ inline signals:
  pct-hermes, vel-hermes, hzscore, hmacd, mtf-momentum, 
  phase_accel, fast_momentum, momentum
      ↓
signal_schema.add_signal() → blacklist only
      ↓
signal_compactor → hotset.json
      ↓
guardian → execution
```

**Problem:** Inline signals are hard to disable individually. Kill-switch only at blacklist level, no per-direction control.

## New Architecture

```
scripts/signals/ — 24 standalone signal scripts:
  pct_hermes.py, vel_hermes.py, hzscore.py, hmacd.py, mtf_momentum.py,
  phase_accel.py, fast_momentum.py, accel_300.py, rs.py, gap_300.py,
  ma_cross.py, ma_cross_5m.py, hh_hl.py, guppy.py, macd_accel.py,
  trend_purity.py, ema9_sma20.py, r2_rev.py, r2_trend.py, volume_hl.py,
  ma300_candle_confirm.py, atr_compression.py, exhaustion.py, counter_flip.py
      ↓
signals/__init__.py — SIGNAL_REGISTRY, get_registered_signals(), run_all_signals()
      ↓
signal_schema.add_signal() — Layer 2 kill-switch + blacklist
      ↓
decider_run.py — Layer 3 execution gate
      ↓
guardian → execution
```

## 3-Layer Kill-Switch

### Layer 1: hermes_constants.py `*_ENABLED` flags

```python
PCT_HERMES_ENABLED        = True   # master (optional)
PCT_HERMES_PLUS_ENABLED   = True   # LONG direction
PCT_HERMES_MINUS_ENABLED  = False  # SHORT direction
```

Each signal has a flag. Directional signals have PLUS/MINUS variants.

### Layer 2: signal_schema.py add_signal()

After `validate_source()` blacklist check passes, `add_signal()` checks `*_ENABLED`:

```python
if _comp == 'pct-hermes+' and not PCT_HERMES_PLUS_ENABLED:
    return None
```

This catches signals even if Layer 1 (script-level) fails.

### Layer 3: decider_run.py execution gate

Before any trade executes, decider_run checks the flag again:

```python
if not GAP_300_ENABLED:
    continue  # skip this signal
```

## Blacklist vs Flags

| Config | Blacklist | Flag | Result |
|--------|-----------|------|--------|
| Permitted | Not in list | True | Signal passes |
| Kill-switch | Not in list | False | Blocked by flag |
| Permanent | In list | Any | Blocked by blacklist |

**Never:** Put signal in blacklist AND set flag=True — blacklist wins.

## Migration Status

- `scripts/signals/` directory: CREATED with 24 scripts
- `__init__.py` registry: CREATED (22/24 wired with valid run() functions)
- `signal_gen.py` inline signals: NOT YET migrated (still the active entry point)
- `run_pipeline.py`: NOT YET updated to call signals/ registry

## Current Kill-Switch Settings (2026-05-05)

| Signal | Flag | Setting | Notes |
|--------|------|---------|-------|
| pct-hermes+ | PCT_HERMES_PLUS_ENABLED | True | 100% WR, +$2.31 |
| pct-hermes- | PCT_HERMES_MINUS_ENABLED | False | Catches knives |
| vel-hermes- | VEL_HERMES_MINUS_ENABLED | True | 45% WR, +0.404% avg |
| vel-hermes+ | VEL_HERMES_PLUS_ENABLED | False | 31% WR |
| hzscore+ | HZSCORE_PLUS_ENABLED | True | 31.3% WR, +13.92% PnL |
| hzscore- | HZSCORE_MINUS_ENABLED | True | — |
| accel-300+ | ACCEL_300_ENABLED | True | 42.2% WR, +24.72% PnL |
| gap-300 | GAP_300_ENABLED | False | 14.3% WR, worst signal |
| ma_cross+ | MA_CROSS_PLUS_ENABLED | False | Blocked at Layer 2 |
| r2_rev | R2_REV_ENABLED | False | Blocked |

## How to Add a New Signal

1. Create `scripts/signals/{name}.py` with `run()` function
2. Add Layer 1 kill-switch at top:
   ```python
   from hermes_constants import MY_SIGNAL_ENABLED, MY_SIGNAL_PLUS_ENABLED, MY_SIGNAL_MINUS_ENABLED

   def run(prices_dict):
       if not MY_SIGNAL_ENABLED:
           return 0
       # ... signal logic ...
       if direction == 'LONG' and not MY_SIGNAL_PLUS_ENABLED:
           return 0
   ```
3. Add `*_ENABLED` flags to `hermes_constants.py`
4. Import and register in `scripts/signals/__init__.py`
5. Verify: `python3 -c "from signals import get_registered_signals; print(len(get_registered_signals()))"`

## How to Disable a Signal

**Temporary (flag):** Set `MY_SIGNAL_ENABLED = False` in hermes_constants.py. Takes effect on next pipeline run.

**Permanent (blacklist):** Add `'my-signal'` to `SIGNAL_SOURCE_BLACKLIST` in hermes_constants.py. Takes effect immediately.

**Directional:** Use `MY_SIGNAL_PLUS_ENABLED` / `MY_SIGNAL_MINUS_ENABLED` for per-direction control.
