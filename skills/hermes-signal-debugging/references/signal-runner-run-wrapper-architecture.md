# Signal Runner — `run()` Wrapper Architecture
# Hermes signals_runner uses getattr(mod, 'run') to fire signals
# This is the definitive entry point — registry is NOT used at runtime

## The Mechanism

```
signals_runner._run_signal(args):
  → mod = __import__(f'signals.{module_name}', fromlist=['run'])
  → fn = getattr(mod, 'run', None)
  → if fn is None: return None  ← SIGNAL SILENTLY DIES
  → return fn(prices) or fn()
```

The registry in `signals/__init__.py` only controls ENABLED at startup via `_resolve_enabled()`.
At runtime, `_run_signal` does a fresh import and looks for `mod.run` directly.

## The `run()` Wrapper Pattern

Every signal module in `signals/` needs a `run()` wrapper for `signals_runner` to find it:

```python
# signals/<name>.py — at the bottom of the file

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    from signals.<name> import scan_<name>_signals
    result = scan_<name>_signals(prices_dict)
    # Normalize return: list/dict/tuple → int count
    if isinstance(result, int):
        return result
    elif isinstance(result, tuple):
        return result[0]  # (count, tokens_set)
    elif isinstance(result, list):
        return len(result)
    return 0
```

## Modules That Now Have `run()` Wrappers

All 15 that were broken (added in 2026-05-12 session):
- ma_cross, atr_compression, trend_purity, hh_hl, macd_accel
- ema9_sma20, volume_hl, ma300_candle_confirm, r2_trend, r2_rev
- gap_300, macd_1m, ema20_50, exhaustion, guppy

Modules that already had `run()` (working fine):
- accel_300, rs, vel_hermes, pct_hermes, hzscore, phase_accel
- momentum, fast_momentum, mtf_macd, mtf_momentum, hmacd
- ma_cross_5m, counter_flip, tl_break

## Per-Direction Kill-Switch Pattern

Signals with `*_PLUS_ENABLED` / `*_MINUS_ENABLED` variants MUST check direction
before emitting. Registry-level `enabled` flag only gates the whole signal — it
does NOT filter direction. Pattern:

```python
# In scan_<name>_signals(), BEFORE calling add_signal():
from hermes_constants import <NAME>_PLUS_ENABLED, <NAME>_MINUS_ENABLED
if direction == 'LONG' and not <NAME>_PLUS_ENABLED:
    continue
if direction == 'SHORT' and not <NAME>_MINUS_ENABLED:
    continue
```

**Signals that required this fix:**
- `ma_cross` — MA_CROSS_PLUS_ENABLED=False was being ignored (golden cross still firing)
- `gap_300` — GAP_300_PLUS/GAP_300_MINUS added
- `ma_cross_5m` — MA_CROSS_5M_PLUS/MA_CROSS_5M_MINUS added

**Signals correctly checking direction flags already:**
- vel_hermes, pct_hermes, hzscore, hmacd, momentum, phase_accel, fast_momentum
- mtf_macd, mtf_momentum, r2_trend, r2_rev, hh_hl, guppy, macd_accel

## ma300_candle_confirm — Special Case

This signal's scan function lives in the PARENT directory, not in `signals/`.
The `signals/ma300_candle_confirm.py` wrapper must re-export it:

```python
# signals/ma300_candle_confirm.py
from ma300_candle_confirm_signals import scan_ma300_candle_signals

def run(prices_dict=None):
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    added, results = scan_ma300_candle_signals(prices_dict)
    return added
```

Without the re-export, `__import__('signals.ma300_candle_confirm')` finds the
wrapper file but not the scan function — ImportError at runtime.

## All Kill-Switch Flags (hermes_constants.py)

Single-flag signals (kill whole signal, no direction split):
| Flag | Default | Signal |
|------|---------|--------|
| ACCEL_300_ENABLED | True | accel_300 |
| RS_ENABLED | True | rs |
| VEL_HERMES_ENABLED | True | vel_hermes |
| HH_HL_ENABLED | True | hh_hl |
| MACD_ACCEL_ENABLED | True | macd_accel |
| TREND_PURITY_ENABLED | True | trend_purity |
| EMA9_SMA20_ENABLED | True | ema9_sma20 |
| VOLUME_HL_ENABLED | True | volume_hl |
| MA300_CANDLE_ENABLED | True | ma300_candle_confirm |
| ATR_COMPRESSION_ENABLED | True | atr_compression |
| EXHAUSTION_ENABLED | True | exhaustion |
| R2_TREND_ENABLED | False | r2_trend |
| R2_REV_ENABLED | False | r2_rev |
| GUPPY_ENABLED | False | guppy |

Per-direction signals (MUST check direction in scan function):
| Flag | Default | Direction |
|------|---------|-----------|
| MA_CROSS_PLUS_ENABLED | False | LONG |
| MA_CROSS_MINUS_ENABLED | True | SHORT |
| MA_CROSS_5M_PLUS_ENABLED | False | LONG |
| MA_CROSS_5M_MINUS_ENABLED | False | SHORT |
| GAP_300_PLUS_ENABLED | False | LONG |
| GAP_300_MINUS_ENABLED | False | SHORT |
| PCT_HERMES_PLUS_ENABLED | False | LONG |
| PCT_HERMES_MINUS_ENABLED | True | SHORT |
| VEL_HERMES_PLUS_ENABLED | False | LONG |
| VEL_HERMES_MINUS_ENABLED | True | SHORT |
| HZSCORE_PLUS_ENABLED | True | LONG |
| HZSCORE_MINUS_ENABLED | True | SHORT |
| HMACD_PLUS_ENABLED | True | LONG |
| HMACD_MINUS_ENABLED | True | SHORT |
| MOMENTUM_PLUS_ENABLED | False | LONG |
| MOMENTUM_MINUS_ENABLED | False | SHORT |
| MTF_MOMENTUM_PLUS_ENABLED | False | LONG |
| MTF_MOMENTUM_MINUS_ENABLED | False | SHORT |
| PHASE_ACCEL_PLUS_ENABLED | True | LONG |
| PHASE_ACCEL_MINUS_ENABLED | True | SHORT |
| FAST_MOMENTUM_PLUS_ENABLED | True | LONG |
| FAST_MOMENTUM_MINUS_ENABLED | False | SHORT |

## Missing Flags (should be added to hermes_constants.py)

- `EMA20_50_ENABLED` — no flag exists for ema20_50 signal
- `MACD_1M_ENABLED` — no flag exists for macd_1m signal

Both signals check their `scan_*` function's return but have no killswitch
in hermes_constants. TBD whether to add flags or treat as always-on.