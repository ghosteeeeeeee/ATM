# Pipeline Race: "stale price_history" in zscore-pump and rs (2026-05-18)

## TL;DR

Two bugs working together:
1. **price_collector writes prices to signals_hermes.db then does 90s Binance backfills**
   — signals_runner races against the backfill, sees stale data, skips tokens
2. **_force_fresh_atr() doesn't call Binance when a stale cache exists and HL fails**
   — ATR becomes None → `_collect_atr_updates` skips the token → guardian's 0.5%/1.5%
   fallback SL/TP persist

## Bug 1 — Pipeline Race (signals skip tokens)

**Location:** `price_collector.py:2148-2153` (writes prices first, then backfills)

**Location:** `zscore_pump.py:147` and `rs.py:609`:
```python
if (time.time() - most_recent_ts) > 120:
    _log(f"  [zscore-pump] {token}: stale price_history (last ts {most_recent_ts}), skipping")
    return []
```

**Timeline of a price_collector cycle:**
```
T+0s:   price_collector.timer fires
T+0-5s: price_history written to signals_hermes.db (FRESH)
T+5s:   signals_runner.py fires via run_bg() — races with collector
T+5-90s: Binance candle backfills running
T+30-90s: signals_runner scans DB → sees T+5s timestamp → ~25-85s old → may fail 120s gate
```

**Fix A options:**
1. signals_runner waits for price_collector lock/semaphore before scanning
2. Add "backfill_complete" marker file signals_runner checks
3. Reduce 120s threshold to 30s (already suggested in zscore-staleness-bug.md but not applied)

## Bug 2 — ATR Binance Fallback Never Fires (guardian fallback persists)

**Location:** `position_manager.py:1396`:
```python
if atr is None and stale_cached_atr is None:
    # Only HERE does Binance get attempted
```

When `stale_cached_atr is not None` (age 300s–3600s), Binance is never called.
MORPHO ATR cache age: 5674s (> 3600s, stale copy discarded) → `stale_cached_atr = None`.
UMA ATR cache age: 5916s (> 3600s) → same.
SNX ATR cache age: 334s (300s–3600s, stale copy saved) → `stale_cached_atr = 0.002080`.

When HL fails for MORPHO/UMA: `atr = None`, `stale_cached_atr = None` → Binance fires ✓
But when HL fails for SNX: `atr = None`, `stale_cached_atr = 0.002080` → Binance never fires.

**Fix B:** Change line 1396 from `if atr is None and stale_cached_atr is None:` to `if atr is None:`.
This is safe — Binance is a public API, no auth needed.

## Impact

| Token | price_history stale? | ATR cache age | ATR fetched? | Guardian fallback persists? |
|-------|---------------------|---------------|-------------|---------------------------|
| MORPHO | Yes (transient) | 5674s (>3600s) | HL→Binance | No (Binance fires when HL fails) |
| UMA | Yes (transient) | 5916s (>3600s) | HL→Binance | No (same) |
| SNX | No (was fresh) | 334s (<3600s) | HL only (no Binance) | **Yes** — HL rate-limited, Binance skipped |

SNX is the live concern: `atr_managed=f`, HL API may rate-limit, Binance never tried,
`atr=None` → `_collect_atr_updates` skips SNX → SL stays at 0.5% instead of ATR-based.

## Diagnostic

```bash
# Check ATR cache ages
python3 -c "
import json, time
with open('/root/.hermes/data/atr_cache.json') as f:
    d = json.load(f)
for t in ['MORPHO','SNX','UMA']:
    e = d.get(t,{})
    age = time.time() - e.get('ts',0)
    print(f'{t}: ATR={e.get(\"atr\")} age={age:.0f}s stale={age>300} discard={age>3600}')
"

# Check price_history
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
c = conn.cursor()
for token in ['MORPHO','SNX','UMA','BTC','ETH']:
    c.execute('SELECT MAX(timestamp) FROM price_history WHERE token=?', (token,))
    row = c.fetchone()
    if row[0]:
        age = time.time() - row[0]
        print(f'{token}: age={age:.0f}s stale={age>120}')
"
```