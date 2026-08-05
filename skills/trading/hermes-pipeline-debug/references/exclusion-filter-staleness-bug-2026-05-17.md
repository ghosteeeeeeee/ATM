# Exclusion Filter Staleness Bug — position_manager + pump signals
**Date:** 2026-05-17
**Severity:** Critical — wrong SL/TP on live positions

## Bug Pattern

When a signal is **partially migrated** (signal function runs in pipeline, but the old standalone executor still existed), it was excluded from `position_manager.py`'s ATR management in 3 SQL queries (lines ~258, ~282, ~306):
```python
WHERE signal NOT IN ('pump_hunter', 'zscore_pump')  # OLD
```

`zscore_pump` was excluded because the OLD standalone executor (`zscore_pump_hunter.py`) managed its own SL/TP. But after migration to pipeline signal (`signals/zscore_pump.py`), the exclusion became wrong — the pipeline signal doesn't manage SL/TP, so it needs PM to manage it.

## How It Broke

1. `decider_run.py` opens a `zscore-pump-` trade with pump-mode SL/TP:
   - `PUMP_SL_PCT = 1.5%`, `PUMP_TP_PCT = 2.5%` (hardcoded)
   - Writes these to DB on entry → stale values from day one

2. `position_manager._collect_atr_updates()` queries DB but skips `zscore-pump-` trades due to exclusion filter

3. PM computes correct ATR levels (~0.30% SL) but can't write them because the filter says "don't touch zscore_pump"

4. **Result**: Trade has SL=1.5% instead of ATR-based SL=0.30%. Two ETH SHORT trades closed at $2185 (ATR would have hit ~$2183) — unnecessary losses.

## The Fix

Remove `zscore_pump` from PM's exclusion filter. Keep only `pump_hunter`:
```python
WHERE signal NOT IN ('pump_hunter')  # CORRECT — zscore_pump now uses ATR via PM
```

For existing trades with stale SL/TP, force reset to 0 so the stale-detection in `_collect_atr_updates()` triggers a fresh write:
```sql
UPDATE trades SET stop_loss = 0, target = 0, atr_managed = FALSE
WHERE status='open' AND token IN ('ETH','AVAX',...)
```

## Files Touched

- `/root/.hermes/scripts/position_manager.py` — lines 258, 282, 306
  - Changed `('pump_hunter', 'zscore_pump')` → `('pump_hunter')`

## How to Detect This Bug

Two symptoms together:
1. Open positions show SL/TP values that don't match what `tpsl_utils.compute_atr_sl_tp()` would produce
2. PM output shows those trades never appear in `_collect_atr_updates()`

Check PM logs for TPSL entries — if a trade with `zscore-pump-` signal never shows a TPSL log line, the exclusion filter is blocking it.

## Prevention Rule

When migrating a standalone executor to pipeline signal:
1. **Remove the signal from PM's exclusion filter immediately** — this is the first action after migration
2. **Don't wait** — the old executor being gone means PM MUST manage the SL/TP
3. The `signals/__init__.py` and `hermes_constants` are correct (signal runs in pipeline) but the exclusion filter is a separate SQL query that must also be updated