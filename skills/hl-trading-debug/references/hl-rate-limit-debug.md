---
name: hl-rate-limit-debug
description: Trace and fix HL API rate limit (429) issues in Hermes — stale allMids prices from systemic rate limit exhaustion across multiple callers
tags: [hyperliquid, rate-limit, 429, debugging, price-collection, stale-data]
---

# HL Rate Limit (429) Debugging — Hermes

## When to Use

Stale prices, `allMids` gaps, price_collection failing silently, or `price_history` shows identical gaps across ALL tokens at the same times. This skill traces the root cause of HL API rate limits (429 errors) across the Hermes pipeline.

## Symptom Pattern

- ALL 191 tokens have identical gaps at the same timestamps
- Price collector logs show `429 Too Many Requests`
- Gaps are exactly 121 seconds (one missed collection + one normal cycle)
- Systematic pattern: gaps occur every ~15 minutes

## Investigation Steps

### Step 1: Confirm the gap pattern is systemic

```python
# Check ALL tokens for gaps > 2 min in last 2 hours
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
now_ts = int(time.time())
two_hours_ago = now_ts - 7200
c.execute('SELECT DISTINCT token FROM price_history')
all_tokens = [r[0] for r in c.fetchall()]
gapped = []
for token in all_tokens:
    c.execute('''SELECT timestamp FROM price_history WHERE token=? AND timestamp >= ? ORDER BY timestamp ASC''',
              (token, two_hours_ago))
    rows = c.fetchall()
    if not rows: continue
    timestamps = [r[0] for r in rows]
    for i in range(1, len(timestamps)):
        if timestamps[i] - timestamps[i-1] > 120:
            gapped.append((token, timestamps[i-1], timestamps[i]))
            break
print(f'All tokens with gaps: {len(gapped)}')
# If ALL 191 tokens have a gap at the SAME timestamp → systemic (not per-token)
"
```

### Step 2: Identify ALL callers of HL /info endpoint

```bash
grep -rn "requests.post.*hyperliquid\|Info(\|candleSnapshot\|allMids\|get_open_hype_positions_curl" \
  /root/.hermes/scripts/*.py | grep -v "hype_cache\|#"
```

Key callers:
- `price_collector.py` → `allMids` + `meta` (2 calls per run, 1/min)
- `4h_regime_scanner.py` → `candleSnapshot` × N tokens (134 calls per run!)
- `15m_regime_scanner.py` → `candleSnapshot` × N tokens
- `hl_sync_guardian.py` → `user_state` via SDK (1 call / 2 min)
- `hype_paper_sync.py` → `user_state` via SDK (1 call / 10 min)

### Step 3: Check journalctl for 429 source

```bash
journalctl -u hermes-price-collector.service --since "1 hour ago" | grep 429
journalctl -u hermes-pipeline.service --since "1 hour ago" | grep 429
```

### Step 4: Count HL calls per hour from each source

```
price_collector:  2 × 60  =   120 calls/hr
4h_regime:       134 × 12 = 1,608 calls/hr  ← CAUSE
15m_regime:       134 × 4  =   536 calls/hr
hl_guardian:       1 × 30   =    30 calls/hr
hype_paper_sync:  1 × 6    =     6 calls/hr
─────────────────────────────────────────────────
HL rate limit: ~60 req/min = 3,600 calls/hr
But burst limit can trigger at ~36 req/min
```

### Step 5: Check timer intervals for burst overlap

```bash
systemctl list-timers --no-pager | grep -E "regime|collector|guardian"
```

## The Pattern

HL `/info` rate limit is **60 req/min**. The `4h_regime_scanner` runs in the pipeline EVERY MINUTE calling `candleSnapshot` for 134 tokens — **134 req/min** from one source. When its burst exhausts the budget, ALL scripts get 429 including price_collector. The `allMids` stale prices are a SYMPTOM, not the cause.

## The Fix

**Regime scanners → Binance-only.** Regime trend bias doesn't need HL precision. Binance `GET /api/v3/klines` has ~1200 req/min, 20× more headroom.

```python
# BEFORE (HL primary, Binance fallback — causes 429s)
def fetch_candles(token):
    try:
        r = requests.post(INFO_URL, json={"type": "candleSnapshot", ...})
        if r.ok: return r.json()
    except: pass
    # Binance fallback never reached until HL budget exhausted
    return fetch_binance(token)

# AFTER (Binance-only — zero HL rate limit impact)
def fetch_candles(token):
    return fetch_binance(token)
```

## Files Changed

- `4h_regime_scanner.py`: removed HL candleSnapshot try block, Binance primary
- `15m_regime_scanner.py`: removed HL candleSnapshot try block, Binance primary

## Verification

```bash
# Verify 0 new 429s from price_collector
journalctl -u hermes-price-collector.service --since "30 minutes ago" | grep -c 429
# Expected: 0

# Verify regime scanner still produces output
cat /var/www/html/regime_4h.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d[\"regimes\"])} tokens')"
```

## Key Insight

HL rate limit is a **shared budget**. The highest-volume caller (4h_regime_scanner: 134 candleSnapshot calls/min) exhausts it and causes ALL scripts — including price_collector — to get 429s. Always identify ALL callers before assuming price_collector is the source.
