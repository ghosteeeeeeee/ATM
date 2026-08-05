# ZSCORE-PUMP Staleness Bug (2026-05-17)

## Symptom
SUI SHORT opened at 02:44:07, closed by SL at 02:44:12 (~5 seconds). Entry $1.0509, exit $1.05165 (price went UP against SHORT). Loss -0.07% at 5× leverage.

Signal in runtime DB:
```
SUI|SHORT|rs-r210,zscore-pump-|83.72||2026-05-17 02:44:03
SUI|SHORT|rs-r210,zscore-pump-|78.92|-1.801|2026-05-17 02:44:03
```

`close_reason: atr_sl_hit` — SL hit immediately on open.

## Root Cause

`signals/zscore_pump.py` line ~145:
```python
if (time.time() - most_recent_ts) > 120:
    _log(f"  [zscore-pump] {token}: stale price_history (last ts {most_recent_ts}), skipping")
    return []
```

Price for SUI in `signals_hermes.db` was **57 seconds stale** when signal fired — passed the 120s gate.
By the time signal propagated through signal_compactor → hotset.json → guardian → fill:
- signal_compactor: ~0-60s lag (synchronous, same pipeline cycle)
- hotset.json write: immediate
- guardian reads hotset, fires HL order: ~0-30s
- HL order fill: ~0-10s

Total propagation: **30-100s**. A 57s-stale price is already 30-70s into the past by the time fill happens.

## Signal Propagation Timeline
```
t=0s:     price moves against SHORT
t=57s:    signal scans price_history — data 57s stale, PASSES 120s gate
t=0-60s:  signal_compactor runs (same cycle)
t=60s:    next cycle: guardian reads hotset, fires order
t=70-90s: HL fill — market has moved since the stale scan
t=70-75s: SL hit immediately
```

## Fix

Change staleness threshold from 120s to 30s:
```python
if (time.time() - most_recent_ts) > 30:  # was 120
```

This gives 30s of freshness headroom against a ~30s propagation path — barely enough, but tighter than 120s which gives a false sense of safety.

## Why the 120s Threshold Exists

The 120s guard was designed to catch completely dead feeds (no data for 2+ minutes). But it backfires in the live pipeline because:
1. `signals_hermes.db` price_history is updated by `price_collector` which runs every ~20-30s per token (cycling through ~230 tokens)
2. A token that just got polled may show a fresh price, but tokens not yet polled in the current cycle show their last poll time
3. 120s catches truly dead feeds but also passes marginally-stale feeds that are dangerous in live trading

## Trade-Off

| Threshold | Dead Feed Safety | Live Trading Safety |
|-----------|-----------------|---------------------|
| 120s | ✅ 2min dead → skip | ❌ 57s stale → pass, phantom signal |
| 30s | ⚠️ 30s dead → skip | ✅ tighter freshness gate |

## Related
- `signals/zscore_pump.py` — `_get_1m_prices()` function
- `hermes_constants.py` → `ZSCORE_PUMP_USE_TUNER` flag added 2026-05-17
- zscore signal direction flip (z → -z) applied 2026-05-17