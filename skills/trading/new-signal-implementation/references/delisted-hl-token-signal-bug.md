---
name: delisted-hl-token-signal-bug
description: "Bug #15 (2026-05-05): breakout_engine fires signal for ILV — delisted on Hyperliquid but seeded into candles.db from Binance. Root cause chain, fix, and verification."
category: trading
tags: [signals, bug, hyperliquid, delisted-token, breakout]
created: 2026-05-05
---

# Bug #15: Signal Fires for Delisted HL Token (ILV case, 2026-05-05)

## Symptom

`breakout_engine` fires a LONG signal for ILV at price ~$4.66, conf=95%, vol=27.7x. Guardian cannot execute — HL `allMids` returns `None` for ILV. Signal appears as masked token `***` in `oc_pending_signals.json`.

## Root Cause Chain

```
1. price_collector._seed_universe_candles()
   → iterates HL universe (includes isDelisted=True tokens)
   → fetches Binance candles for ALL of them
   → ILV trades on Binance → ILV at ~$4.66 written to candles.db

2. breakout_engine (line ~557)
   → token list = SELECT DISTINCT token FROM candles_1m WHERE ts > now-30min
   → NO check: "is this token currently on Hyperliquid?"
   → ILV passes because it has recent candles in candles.db

3. detect_breakout() fires on stale vol spike from 03:40 UTC
   → ILV 5m: vol=782 at 03:40 (real Binance volume, not HL)
   → ILV candles stop at 03:42 UTC (HL feed went stale)

4. Guardian tries to place order
   → HL allMids[ILV] = None → order rejected
   → signal shows as *** in oc_pending_signals.json
```

## Two Fix Points

### Fix 1: price_collector.py — filter delisted tokens before Binance backfill

```python
# Line ~143 in _seed_universe_candles()
all_tokens = sorted(set(
    u['name'] for u in universe
    if u.get('name')
    and not u['name'].startswith('@')
    and len(u['name']) <= 10
    and not u.get('isDelisted', False)   # ← ADD THIS
))
```

### Fix 2: breakout_engine.py — validate against live HL allMids before emitting

```python
# In run() or detect_breakout_for_token(), before writing signal:
import requests
API = "https://api.hyperliquid.xyz/info"
headers = {'Content-Type': 'application/json'}
try:
    mids = requests.post(API, json={'type': 'allMids'}, headers=headers, timeout=10).json()
    if not mids.get(token):
        log(f"[{token}] SKIP — not on Hyperliquid (allMids=None)", 'WARN')
        return None
except Exception as e:
    log(f"[{token}] Could not verify HL status: {e}", 'WARN')
```

**Filter order for any signal scanner reading from candles.db:**
1. candles.db token list
2. Remove `@`-prefixed tokens
3. **Cross-check live HL `allMids` — skip if None/missing** ← this step
4. Apply SHORT_BLACKLIST / LONG_BLACKLIST
5. Apply Binance availability check

## Why Staleness Exit Worked Correctly

`entry_origin_ts=~03:58`, staleness decrements 0.2 per compaction cycle:
- `staleness = max(0, 1.0 - age_min * 0.2)`
- Exit threshold: staleness ≤ 0.01
- ILV exited at ~04:13 (age ≈ 25 min → staleness ≈ 0)

No bug in exit logic — the staleness timer is correct. The bug was at signal **emission**, not at the exit mechanism.

## Verification Queries

```bash
# Check which tokens in candles.db are delisted on HL
python3 -c "
import sqlite3, json, requests
API = 'https://api.hyperliquid.xyz/info'
headers = {'Content-Type': 'application/json'}
mids = requests.post(API, json={'type': 'allMids'}, headers=headers, timeout=10).json()
conn = sqlite3.connect('/root/.hermes/data/candles.db')
c = conn.cursor()
c.execute('SELECT DISTINCT token FROM candles_5m')
for (tok,) in c.fetchall():
    if not mids.get(tok):
        print(f'Delisted on HL (not in allMids): {tok}')
conn.close()
"

# Confirm ILV is delisted
python3 -c "
import json
with open('/var/www/hermes/data/hl_cache.json') as f:
    d = json.load(f)
universe = d.get('meta', {}).get('universe', [])
for u in universe:
    if u['name'] == 'ILV':
        print(f'ILV: isDelisted={u.get(\"isDelisted\")}, allMids={d[\"allMids\"].get(\"ILV\")}')
"

# Check ILV in candles.db
sqlite3 /root/.hermes/data/candles.db "SELECT token, MAX(ts), COUNT(*) FROM candles_5m WHERE token='ILV' GROUP BY token"
```

## Related Files

- `/root/.hermes/scripts/breakout_engine.py` — breakout signal scanner (needs Fix 2)
- `/root/.hermes/scripts/price_collector.py` — candles backfill (needs Fix 1)
- `/var/www/hermes/data/hl_cache.json` — HL universe cache (delisted tokens listed)
- `/root/.hermes/data/candles.db` — local candle storage (may contain stale/delisted tokens)
