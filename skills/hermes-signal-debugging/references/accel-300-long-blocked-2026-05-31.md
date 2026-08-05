# accel_300 LONG Blocked by Stale candles.db — 2026-05-31

## Root Cause
LONG signals blocked by regime filter (lines 379-380):
`slope < 0 → return None` — but slope is wrong because candles_1m is weeks stale.

## Tokens Affected
| Token | candles_1m newest | slope | LONG blocked |
|-------|-------------------|-------|--------------|
| XLM | 2026-05-28 (3d stale) | -0.00004 | YES |
| ONDO | 2026-04-17 (6w stale) | -0.00009 | YES |
| GALA | 2026-05-28 (3d stale) | -0.00000 | YES |
| BRETT | 2026-04-28 (~1m stale) | +0.00000 | NO |
| GRASS | 2026-04-28 (~1m stale) | +0.00003 | NO |

## Mechanism
1. detect_accel_300() queries `candles_1m WHERE ts > datetime('now', '-2 hours')`
2. candles.db weeks stale → 0 recent rows OR old rows
3. If 0 rows: regime check skipped (safe)
4. If stale rows: slope wrong sign → blocks valid LONG signals

## Debug Script
`/tmp/trace_regime2.py` — trace regime slopes for all tokens.

## Fix
Regime filter: when `len(rows) < 20`, skip regime block (don't assume SHORT_BIAS).
Or use price_history (live) instead of candles_1m (stale) for regime.

## Separate: Hot-set Delivery Blocker
signal_compactor.py line 671 requires `rs` co-signal:
```python
has_rs = any(p.startswith('rs') for p in source_parts)
if not has_rs: log(f"SKIP: no rs signal")
```
`accel-300-` alone blocked; `accel-300-,rs-r8` passes. Two separate bugs.