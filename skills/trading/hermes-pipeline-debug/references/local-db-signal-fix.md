---
name: local-db-signal-fix
description: "Fix: macd_rules making too many API calls — local DB first with warmup enforcement"
triggers:
  - signal_gen rate-limit 429
  - pattern_scanner only signals
  - compute_mtf_macd_alignment returning None
---

# Local-DB-First API Call Pattern for Hermes

## Context
When fixing signal_gen.py where `macd_rules.compute_mtf_macd_alignment()` was making 570 Binance API calls per cycle (3 TFs × 190 tokens), causing 429 rate limits and silencing all MTF signals.

## Root Cause
`macd_rules._fetch_binance_candles()` checked `len(rows) >= warmup_min` to decide local DB sufficiency. But callers passed small limits (e.g. `limit=40`), so the query returned fewer rows than `warmup_min`, making the check fail even when the DB had enough data. This caused silent fallback to Binance API → rate limits.

## Pattern: Local-DB-First with Warmup Enforcement

```python
def _fetch_candles_local_first(token: str, interval: str, limit: int = None) -> Optional[list]:
    warmup_min = SLOW_PARAM + SIGNAL_PARAM + 20  # e.g. 55+15+20 = 90

    # Always fetch at least warmup_min rows (fix: don't trust caller's small limit)
    if limit is None:
        limit = max(150, warmup_min)
    else:
        limit = max(limit, warmup_min)  # enforce minimum

    # Read local DB
    try:
        rows = local_db_query(limit)
        # Accept if close to warmup_min (allow slight deficit)
        if len(rows) >= warmup_min - 5:
            return rows
    except Exception:
        pass

    # Fallback to external API (only if DB empty/stale)
    return external_api_fetch()
```

## Key Lesson
**Never trust a caller's `limit` to satisfy your computation's minimum requirements.** Always enforce `max(caller_limit, warmup_min)` before the DB query. The caller may pass a small limit for a different reason (e.g. just checking recent data), but your sufficiency check must use the true minimum needed for computation.

## Files Involved
- `/root/.hermes/scripts/macd_rules.py` — `_fetch_binance_candles()` fixed
- `/root/.hermes/scripts/price_collector.py` — `_seed_universe_candles()` added
