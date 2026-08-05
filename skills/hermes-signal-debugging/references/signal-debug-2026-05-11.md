# Signal Debugging — Session Notes (2026-05-11)

## Confluence Gate — Root Cause of Thin Hot-Set

**What we found:**
- 69 signals in 5-min window
- 64 BLOCKED by confluence gate (single source)
- Only 5 pass (all accel-300+ + rs-s### combos)
- Result: hot-set has 5-8 tokens, mostly LONG

**The gate (signal_compactor.py ~line 559-593):**
```python
unique_signal_types = len(set(_signal_type_key(p) for p in source_parts))
# _signal_type_key: rs-s386 → 'rs-s', rs-r1774 → 'rs-r'
# Then: if unique_signal_types < 2: BLOCK
```

**Why only 2 signal types fire at all:**
- `accel_300.py` — momentum acceleration after EMA cross (ACTIVE)
- `rs.py` — support/resistance bounce (ACTIVE)
- All other ~20 signals are either disabled or not generating

**Why shorts barely fire:**
- accel-300- (bearish) rarely triggers
- RS SHORT fires but alone → blocked by confluence gate
- Short combos almost never form

## _get_regime_1m() — Exists But Not Wired

decider_run.py lines 76-109 has linear regression on 100 1m candles returning:
- LONG_BIAS / SHORT_BIAS / NEUTRAL
- Confidence = R² * 100

Not called anywhere in the hot-set path. T wants it wired into decider_run as a filter.

## WR Gate — Queries Empty PostgreSQL

`_get_token_wr()` in signal_compactor.py line 37-73 queries `brain.trades` PostgreSQL.
After archive cleared it, most tokens have 0 trades → `wr_count=0 < 3` → returns 50% (neutral).
Fix: query `trades_analysis.db` (SQLite) instead.

## Quick Diagnostic
```bash
cd /root/.hermes/scripts && python3 signal_compactor.py --verbose 2>&1 | head -80
# Look for 🔒 [CONFLUENCE-GATE-BLOCK]
```