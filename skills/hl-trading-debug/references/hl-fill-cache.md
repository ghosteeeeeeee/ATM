---
name: hl-fill-cache
description: Consolidate duplicate Hyperliquid get_trade_history API calls using an in-memory cache with rate-limit guard. Prevents duplicate calls from multiple functions for the same token/timewindow, protects against HL rate limits, and enables PHANTOM_CLOSE retries to find fills from cache.
author: Hermes Agent
tags: [hyperliquid, rate-limit, cache, api-calls, guardian]
date: 2026-04-14
---

# HL Fill Cache — Consolidate Hyperliquid API Calls

## Problem
`hl-sync-guardian.py` calls `get_trade_history` from multiple places for the same token and time window:
- `_get_hl_exit_price()` — polls for exit fills when closing
- `_close_paper_trade_db()` — fetches HL realized PnL for the same token
- `_poll_hl_fills_for_close()` — same pattern

Result: **2 duplicate API calls per close**, and when HL fills take 5+ minutes to propagate, guardian uses market price fallback, corrupting trade data.

**Related root cause:** Also used to detect phantom closes via `phantom-trade-detection` skill (BLUR: 1 real HL close, 36 DB records).

## Solution Pattern
Single shared cache function with rate-limit guard:

```python
# ── In-memory fill cache — prevents duplicate get_trade_history calls ───────────
_FILL_CACHE = {}          # {(token, w_start, w_end): {'fills': [...], 'fetched_at': ts}}
_FILL_CACHE_TTL = 300     # Keep cached fills for 5 minutes
_MAX_API_CALLS_PER_CYCLE = 3  # Conservative rate-limit guard

def _get_fills_cached(token: str, window_start_ms: int, window_end_ms: int):
    cache_key = (token.upper(), window_start_ms, window_end_ms)
    now = time.time()

    # Cache hit
    if cache_key in _FILL_CACHE:
        cached = _FILL_CACHE[cache_key]
        if now - cached['fetched_at'] < _FILL_CACHE_TTL:
            return cached['fills']

    # Rate-limit guard — max 3 calls per 60s cycle
    cycle_key = f"_cycle_{int(now // 60)}"
    if not hasattr(_get_fills_cached, '_call_count'):
        _get_fills_cached._call_count = {}
    count = _get_fills_cached._call_count.get(cycle_key, 0)
    if count >= _MAX_API_CALLS_PER_CYCLE:
        return []  # graceful fallback

    _get_fills_cached._call_count[cycle_key] = count + 1
    try:
        fills = get_trade_history(window_start_ms, window_end_ms)
        _FILL_CACHE[cache_key] = {'fills': fills, 'fetched_at': now}
        return fills
    except Exception:
        return []
```

Then replace every direct `get_trade_history` call with `_get_fills_cached`:
- `_get_hl_exit_price()` — uses `_get_fills_cached`
- `_poll_hl_fills_for_close()` — uses `_get_fills_cached`
- `_close_paper_trade_db()` — uses `_get_fills_cached` for HL PnL lookup (eliminates duplicate API call)

**Result: One close = 1 API call instead of 2.**

## Key Benefits
- One close = 1 API call instead of 2 (consolidated from `_get_hl_exit_price` + `_close_paper_trade_db`)
- Same token within 5 min = cache hit = 0 API calls
- PHANTOM_CLOSE retried next cycle = may find fills from cache (no API call needed)
- Rate-limit guard prevents hitting HL limits

## Files
- `/root/.hermes/scripts/hl-sync-guardian.py`

## When to Use This Pattern
- Any time multiple functions need the same API data within a short window
- HL fill retrieval, position queries, price fetches — all good candidates
- Cache TTL should match the data's refresh requirements (5 min for fills, shorter for prices)

## Verification
```bash
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py && echo "SYNTAX OK"
```
