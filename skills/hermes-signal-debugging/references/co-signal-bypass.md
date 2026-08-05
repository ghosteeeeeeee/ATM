# Co-Signal Bypass: How `accel-300+,ema9-sma20+` Bypasses Flag Checks

## The Confusion

User sees: `EMA9_SMA20_PLUS_ENABLED = False` but `accel-300+,ema9-sma20+ LONG` fires in the pipeline log.

User assumes: `ema9_sma20.py` is violating the flag.

## Root Cause

The `ema9-sma20+` tag is a **co-signal**, NOT a standalone `ema9_sma20.py` signal.

When `accel_300.py` fires, it calls `add_signal(source='accel-300+,ema9-sma20+', ...)` directly — it never calls `ema9_sma20.py`'s `scan_ema9_sma20_signals()` function.

The `ema9_sma20` directional flags (`EMA9_SMA20_PLUS_ENABLED`, `EMA9_SMA20_MINUS_ENABLED`) in `hermes_constants` only gate the **standalone scan path** in `signals/ema9_sma20.py` (lines 439–443). That code is never reached when `accel_300` writes the co-signal tag directly.

## How to Verify

```bash
# grep accel_300.py for add_signal calls with ema9-sma20
grep -n "ema9-sma20\|add_signal" /root/.hermes/scripts/signals/accel_300.py | head -30

# grep ema9_sma20.py for the flag check
grep -n "EMA9_SMA20_PLUS_ENABLED\|EMA9_SMA20_MINUS_ENABLED" /root/.hermes/scripts/signals/ema9_sma20.py | head -10
```

## The Signal Generation Flow

```
accel_300.py fires → add_signal(source='accel-300+,ema9-sma20+')
                        ↓
                   signal_compactor sees both tags
                   EMA9_SMA20_PLUS_ENABLED check in ema9_sma20.py is NEVER executed
                   (ema9_sma20.py scan function is not called)
```

## What This Means

- `EMA9_SMA20_PLUS_ENABLED = False` does NOT block the co-signal tag
- To suppress the `ema9-sma20+` co-signal, you must either:
  1. Disable `accel_300.py` entirely (`ACCEL_300_ENABLED = False`), OR
  2. Modify `accel_300.py` to not include `ema9-sma20+` in its source string
  3. Add a check in `signal_compactor` or `signals_runner` to filter co-signal tags based on flag state

## MON Example from 2026-05-12

Pipeline log showed:
```
[2026-05-12 02:42:08] accel-300+,ema9-sma20+ LONG MON conf=78%
[2026-05-12 02:43:03] accel-300+,ema9-sma20+ LONG MON conf=76%
```

`EMA9_SMA20_PLUS_ENABLED = False` in hermes_constants line 442.

`accel_300.py` was the actual signal — `ema9_sma20.py` was just a tag appended by `accel_300`.

After trade close at 03:04:12, `SHORT-ema9sma20 MON` signals fired correctly (flag correctly blocking LONG, allowing SHORT).

## ATR Cache Reset Verification (2026-05-12)

Confirmed: ATR TP/SL does NOT persist across trade closes.

- `_collect_atr_updates()` (position_manager.py lines 1465–1789) calls `_force_fresh_atr()` every cycle — fresh fetch or re-read from cache if <300s old
- `close_position()` writes `status='closed'` to DB — does NOT carry SL/TP forward
- New trades use `get_trade_params()` which calls `_pm_get_atr()` fresh
- Cache path: `/root/.hermes/data/atr_cache.json` (confirmed via `paths.py:73`)
- MON ATR at time of check: 0.0002875 (age ~35min, fresh within 300s TTL)
- No stale ATR carryover between trades