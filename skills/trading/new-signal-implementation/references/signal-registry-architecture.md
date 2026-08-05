# Signal Registry Architecture — Post-Migration Reference

**Date:** 2026-05-05
**What:** Mass migration of inline signals from `signal_gen.py` into `scripts/signals/` individual scripts with `SIGNAL_REGISTRY` dispatch.

---

## Architecture Overview

```
scripts/signals/
├── __init__.py          # SIGNAL_REGISTRY + run_all_signals() dispatcher
├── pct_hermes.py        # pct-hermes+/-
├── vel_hermes.py        # vel-hermes+/-
├── hzscore.py           # hzscore+/-
├── hmacd.py             # hmacd+/-
├── mtf_momentum.py      # mtf-momentum+/-
├── momentum.py          # momentum (standalone)
├── phase_accel.py       # phase_accel+ (standalone)
├── fast_momentum.py     # fast-momentum+ (standalone)
├── accel_300.py         # accel-300+ (standalone)
├── rs.py                # rs (standalone)
├── gap_300.py           # gap-300+ (standalone)
├── ma_cross.py          # ma_cross+ (standalone)
├── ma_cross_5m.py       # ma_cross_5m+ (standalone)
├── hh_hl.py             # hh_hl (standalone)
├── guppy.py             # guppy (standalone)
├── macd_accel.py        # macd_accel (standalone)
├── trend_purity.py      # trend_purity (standalone)
├── ema9_sma20.py        # ema9_sma20 (standalone)
├── r2_rev.py            # r2_rev (standalone)
├── r2_trend.py          # r2_trend (standalone)
├── volume_hl.py         # volume_hl (standalone)
├── ma300_candle_confirm.py
├── atr_compression.py
├── exhaustion.py
└── counter_flip.py
```

---

## The Three-Layer Kill-Switch Architecture

Every signal passes through three independent gates before reaching execution.

### Layer 1 — hermes_constants.py (*_ENABLED flags)

```python
# In hermes_constants.py — script-level kill-switch
PCT_HERMES_PLUS_ENABLED   = True   # pct-hermes+ ON
PCT_HERMES_MINUS_ENABLED  = False  # pct-hermes- OFF (catches knives)
VEL_HERMES_PLUS_ENABLED   = False  # 31% WR — blocked
VEL_HERMES_MINUS_ENABLED  = True   # 45% WR — unblocked
GAP_300_ENABLED           = False  # worst active loser
ACCEL_300_ENABLED         = True   # 42.2% WR, +24.72% PnL
FAST_MOMENTUM_MINUS_ENABLED = False # blocked
MA_CROSS_PLUS_ENABLED     = False  # blocked at Layer 2
```

**Pattern for directional signals:** `*_PLUS_ENABLED` / `*_MINUS_ENABLED` for independent per-direction control.

These flags are checked in `signal_schema.py add_signal()` BEFORE any signal is written to the DB. If the flag is False, the `add_signal()` call returns early without writing.

### Layer 2 — signal_schema.py add_signal() per-source guard

```python
# In signal_schema.py add_signal() — after blacklist check
def add_signal(...):
    # ... blacklist check ...
    source = kwargs.get('source', '')
    
    # Per-source kill-switch (Layer 2)
    flag_map = {
        'pct-hermes+':  PCT_HERMES_PLUS_ENABLED,
        'pct-hermes-':  PCT_HERMES_MINUS_ENABLED,
        'vel-hermes+':  VEL_HERMES_PLUS_ENABLED,
        'vel-hermes-':  VEL_HERMES_MINUS_ENABLED,
        'hzscore+':     HZSCORE_PLUS_ENABLED,
        'hzscore-':     HZSCORE_MINUS_ENABLED,
        'ma_cross+':    MA_CROSS_PLUS_ENABLED,
        'ma_cross-':    MA_CROSS_MINUS_ENABLED,
        'accel-300+':   ACCEL_300_ENABLED,
        'gap-300+':     GAP_300_ENABLED,
        'gap-300-':     GAP_300_MINUS_ENABLED,
    }
    flag = flag_map.get(source)
    if flag is not None and not flag:
        if DEBUG_MODE:
            print(f"  DEBUG add_signal BLOCKED: {token} {direction} source={source!r} {flag_name}=False")
        return None  # blocked silently
```

**This is why blacklist is redundant:** blacklist blocks at DB write time (validate_source called inside add_signal). The per-source kill-switch also blocks inside add_signal(), just checking a different condition. Both run in the same function. The blacklist was a second layer on top of an already-sufficient single layer.

### Layer 3 — decider_run.py execution gate

```python
# In decider_run.py _execute_hot_set() — before any HL API call
# Same flag checks — final gate before real money moves
if not COIN:
    source_flags = {
        'pct-hermes+':  PCT_HERMES_PLUS_ENABLED,
        'pct-hermes-':  PCT_HERMES_MINUS_ENABLED,
        ...
    }
    flag = source_flags.get(source)
    if flag is not None and not flag:
        log(f"SKIP {token} {direction} — {source} blocked by kill-switch")
        return None
```

---

## run_all_signals() Signature Dispatch

The `SIGNAL_REGISTRY` contains `run` entries that point to different function types. `run_all_signals()` must dispatch correctly:

```python
def _needs_prices_dict(fn):
    """Check if a function has a 'prices_dict' parameter."""
    import inspect
    try:
        sig = inspect.signature(fn)
        return 'prices_dict' in sig.parameters
    except Exception:
        return False

def run_all_signals(prices_dict=None, **kwargs):
    """
    Architecture:
      - Signals needing prices_dict (accel_300, rs, ma_cross, etc.):
          call: fn(prices_dict)
      - Signals fetching internally (guppy, hh_hl, trend_purity, momentum):
          call: fn()  — they call get_all_latest_prices() themselves
      - Signals needing no args (exhaustion, counter_flip):
          call: fn()
    """
    from signal_schema import get_all_latest_prices
    _prices = prices_dict

    for signal in get_registered_signals():
        fn = signal['run']
        if fn is None:
            continue

        # Lazily fetch only if needed
        if _prices is None and _needs_prices_dict(fn):
            _prices = get_all_latest_prices()

        if _needs_prices_dict(fn):
            result = fn(_prices, **kwargs)
        else:
            result = fn(**kwargs)

        results[signal['name']] = result
    return results
```

**Common signatures by signal type:**

| Signal type | Signature | Example |
|-------------|-----------|---------|
| Prices dict scanner | `fn(prices_dict: dict)` | accel_300, rs, ma_cross, gap_300 |
| Variants scanner | `fn(prices_dict: dict, variant: str)` | hh_hl |
| Internal fetch | `fn()` | momentum, mtf_momentum, guppy, trend_purity |
| No args | `fn(conf_min, token)` | exhaustion |

---

## Bugs Encountered During Migration

### Bug: compute_regime() returns 5 values, not 3

**Symptom:** `ValueError: too many values to unpack (expected 3)` in momentum.py and mtf_momentum.py

**Root cause:** `compute_regime()` returns `(regime, long_mult, short_mult, atr_pct_1h, adx_1h)` — 5 values. Scripts extracted from signal_gen.py unpacked only 3.

**Fix:** Use variadic unpack: `regime, long_mult, short_mult, *_ = compute_regime()`

### Bug: get_cooldown() returns bool, not dict

**Symptom:** `AttributeError: 'bool' object has no attribute 'get'` in accel_300.py

**Root cause:** `get_cooldown(token)` with no direction arg returns a `bool` for some tokens (True when cooldown is active, not a cooldown dict). The code did `cd = get_cooldown(token) or {}` then `cd.get(key)` — but `True or {} = True`, and `True.get()` fails.

**Fix:** Call `get_cooldown(token, direction=direction)` which returns `True/False` directly. Never use the result of the no-arg form as a dict.

### Bug: Missing get_cooldown import in accel_300.py

**Symptom:** `NameError: name 'get_cooldown' is not defined`

**Root cause:** When accel_300.py was migrated, it only imported `add_signal` and `price_age_minutes` from signal_schema. The `get_cooldown` call was added later without updating the import line.

**Fix:** Always use `replace_all=True` when patching import lines, or check import sections after every migration.

### Bug: run_all_signals() tried/except dispatch failed silently

**Symptom:** Scan functions that needed `prices_dict` got no args and returned errors, but the try/except hid them.

**Root cause:** The original try-with-prices-then-fallback pattern relied on TypeError being raised, but if the function accepted `**kwargs` it would accept any args and fail later inside the function body, not at the call site.

**Fix:** Use `inspect.signature()` to determine upfront whether the function needs `prices_dict`, rather than guessing by exception handling.

### Bug: pct-hermes+ still in blacklist despite "REMOVED" comment

**Symptom:** pct-hermes+ (100% WR, +$2.31) was still blocked even though comment said it was removed.

**Root cause:** Comment at one location said "REMOVED" but the actual entry was still at a different line. Conflicting comments across two sections of the blacklist.

**Fix:** Always verify actual code, not comments. When removing from blacklist, remove the entry itself, don't just comment it or move the comment.

---

## Blacklist is Redundant — But Keep Structure

The `SIGNAL_SOURCE_BLACKLIST` in hermes_constants.py is now commented out entirely. The 3-layer kill-switch architecture makes it redundant:

- Layer 1 (hermes_constants *_ENABLED flags) gates generation
- Layer 2 (add_signal() per-source check) gates DB writes  
- Layer 3 (decider_run execution gate) gates execution

**However:** The blacklist structure (commented out) is worth keeping as documentation of what was tried and failed. It provides historical context for why certain signals were blocked. When ready to delete, just `git rm` the commented section.

**Redundant entries found:**
- `pct-hermes+` — blocked by `PCT_HERMES_PLUS_ENABLED=False` (Layer 2) — removed
- `vel-hermes+` — blocked by `VEL_HERMES_PLUS_ENABLED=False` (Layer 2) — still in blacklist but redundant
- `hzscore` bare — no such signal fires (only hzscore+ and hzscore-) — safe to remove

---

## Migration Checklist (Per Signal Script)

When extracting an inline signal from signal_gen.py into scripts/signals/{name}.py:

1. **Import check:** Verify all symbols referenced from signal_gen.py are imported (add_signal, get_cooldown, compute_regime, price_age_minutes, etc.)
2. **compute_regime() unpack:** If calling `compute_regime()`, use `regime, long_mult, short_mult, *_ = compute_regime()` not 3-value unpack
3. **get_cooldown() usage:** If using `get_cooldown`, always pass `direction=direction` keyword arg
4. **prices_dict parameter:** If the scan function needs prices, take `prices_dict: dict` as first parameter; if it fetches internally, take no args
5. **Register in __init__.py:** Add to `SIGNAL_REGISTRY` with correct import name (scan_hh_hl_signals, not scan_all_tokens)
6. **Verify compilation:** `python3 -m py_compile scripts/signals/{name}.py`
7. **Verify runtime:** Call the function and confirm no errors
8. **Update kill-switch:** If directional, add `*_PLUS_ENABLED` / `*_MINUS_ENABLED` to hermes_constants.py and import in add_signal()
