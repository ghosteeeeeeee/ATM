# accel-300 + RS Bounce Gate — June 15 2026 Session Notes

## accel-300 V-Shape False Positive Investigation

**What happened:** User expected LONG signal on UMA June 14 14:00-17:05 EST V-shaped rally (0.3936 → 0.4114 peak → 0.4087).
System fired SHORT at 14:01 and 17:30 but no LONG at 17:05 peak.

**Root cause of no LONG at 17:05:** Four simultaneous gate failures:
1. **Cross gap too thin:** gap at cross = +0.026% (min LONG = +0.20%)
2. **Cross-back occurred:** Price dipped below EMA at 16:15 (gap=-0.351%), breaking 20-bar persistence
3. **Gap expansion too large:** gap_now (+2.455%) vs gap_at_cross (+0.026%) = +2.43% expansion (max ~0.60%)
4. **Regime slope:** Short-term slope pulling back from peak

**Lesson:** V-shape recoveries crossing EMA look like signals but aren't. accel-300 requires sustained clean gap above EMA with growing separation. The system's filtering is working correctly — this is not a bug.

**Gap_val interpretation:** `val=-0.2883` in accel_300_short signals is the EMA gap growth rate, not price. Confusing naming but correct behavior.

## RS Bounce Gate Bug — Implementation Status

**Audit completed:** June 15 2026. Bug 3 (bounce hard gate blocking broken-path) confirmed.
**Fix not yet implemented** — was in progress when session pivoted to accel-300 analysis.

**Bug 3 fix pattern (from rs-audit-jun-2026.md):**
```
# BEFORE:
if not bounces:
    nearest_support = None
else:
    if broken: ...       # unreachable when bounces=False
    else: ...

# AFTER:
if broken: ...           # fires regardless of bounces
elif bounces: ...        # normal bounce path gated by bounce confirmation
```

## Ground-Truth Debugging Recipe

When signal didn't fire but seems like it should have:
1. Pull 5m candles: `SELECT ts, close FROM candles_5m WHERE token='X' AND ts >= ? ORDER BY ts`
2. Compute EMA_300: `ema = alpha*close + (1-alpha)*ema` with `alpha = 2/(300+1)`
3. Compute gap: `(close - ema) / ema * 100`
4. Check each gate manually at the signal time

**DB paths:**
- `candles.db/candles_5m`: ts = Unix int
- `signals_hermes_runtime.db/signals`: ts = ISO string
- `gap300_state` and `momentum_cache` are in signals_hermes_runtime.db

**Timezone:** EST = UTC-5. Use `datetime.fromtimestamp(ts_int, tz=timezone(timedelta(hours=-5)))`
