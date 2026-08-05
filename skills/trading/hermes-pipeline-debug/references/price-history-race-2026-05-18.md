# Price History Staleness — Pipeline Race Condition (2026-05-18)

## Symptom

zscore-pump and rs report "stale price_history" for MORPHO/SNX/UMA. Also causes
`_collect_atr_updates` to receive no ATR for affected tokens → guardian's initial
fallback SL/TP (0.5%/1.5%) persist unchallenged.

## Root Cause — Pipeline Timing Race

**Not a price feed failure. Not a price_collector crash.**

```
price_collector.timer fires
  └─ price_collector.py:2148-2153  ── writes current prices to signals_hermes.db FIRST
      price_collector.py:2148-2310  ── then does expensive Binance candle backfills (90s)
                                      ── while backfills run, signals_runner fires
                                      ── signals_runner reads signals_hermes.db ── SEES STALE DATA
```

The price_history INSERT happens in the first seconds of price_collector.
Binance candle backfills (~500 tokens × 5 TFs) take ~90 seconds.
When price_collector.timer fires the next cycle, signals_runner is launched in the
background — both run concurrently. Signals scan signals_hermes.db while Binance
backfills are still in progress → last committed write is 60-90s old → fails 120s gate.

**Confirmation:**
- price_history was FRESH (79s old) when queried directly after the race passed
- ALL tokens showed the same last_ts simultaneously — global timing gap, not token-specific
- price_collector service was healthy (no errors in journalctl)

## Staleness Thresholds

| Check | Threshold | MORPHO/SNX/UMA at incident time |
|-------|-----------|----------------------------------|
| price_history stale | 120s | ~140-160s (failing) |
| ATR cache stale | 300s | 334s-5916s |
| ATR cache max | 3600s | all within range |

## Interaction with ATR Cache

MORPHO (5674s) and UMA (5916s) ATR cache entries are beyond `_STALE_MAX=3600s` in
`_force_fresh_atr()` — the stale copy is discarded. On next `_force_fresh_atr()` call:
1. HL API attempt → may rate-limit
2. Binance fallback fires only if `atr is None AND stale_cached_atr is None` (line 1396)
3. If HL fails and stale_cached_atr was discarded → `atr=None` returned
4. `_collect_atr_updates` line 1629: `if atr is None: continue` → token skipped
5. Guardian's initial 0.5%/1.5% fallback SL/TP persists

## Fixes Needed (Two Separate Issues)

### Fix A — Pipeline coordination (root cause)
Make signals_runner wait for price_collector to finish, OR add a "data_updated_at" marker
that signals check before running. Current architecture runs both concurrently.

### Fix B — ATR cache Binance fallback
`_force_fresh_atr()` line 1396: `if atr is None and stale_cached_atr is None:` should be
`if atr is None:` — attempt Binance even when a stale cache exists but HL failed.
This ensures atr_cache.json stays current and `_collect_atr_updates` never skips tokens
for lack of ATR.

## Diagnostic Commands

```bash
# Check price_history freshness
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
c = conn.cursor()
for token in ['MORPHO', 'SNX', 'UMA']:
    c.execute('SELECT MAX(timestamp) FROM price_history WHERE token=?', (token,))
    row = c.fetchone()
    if row[0]:
        age = time.time() - row[0]
        print(f'{token}: age={age:.0f}s stale={age>120}')
conn.close()
"

# Check ATR cache ages
python3 -c "
import json, time
with open('/root/.hermes/data/atr_cache.json') as f:
    d = json.load(f)
for token in ['MORPHO', 'SNX', 'UMA']:
    e = d.get(token, {})
    age = time.time() - e.get('ts', 0)
    print(f'{token}: ATR={e.get(\"atr\")} age={age:.0f}s stale={age>300}')
"

# Check signal logs for staleness
grep "stale price_history" /var/www/hermes/logs/signals.log | tail -20
```

## Key Files

| File | Role |
|------|------|
| `price_collector.py:2148-2153` | Writes price_history FIRST, before Binance backfills |
| `signals_runner.py` | Runs signals in background via `run_bg()` — races with price_collector |
| `zscore_pump.py:147` | `if (time.time() - most_recent_ts) > 120` — stale gate |
| `rs.py:609` | Same stale gate |
| `position_manager.py:1339-1448` | `_force_fresh_atr()` — ATR cache + HL + Binance fallback |
| `position_manager.py:1629` | `if atr is None: continue` — blocks token when ATR unavailable |