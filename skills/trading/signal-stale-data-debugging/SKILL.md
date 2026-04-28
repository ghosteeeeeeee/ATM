---
name: signal-stale-data-debugging
description: Debug stale data causing false signals in Hermes — gap-300-, ma-cross, macd rules, etc. Use when signals fire with wrong direction or excessive frequency with no clear market cause.
category: trading
---

# Signal Stale Data Debugging

## Symptom
A signal (commonly `gap-300-`, `ma-cross-5m`, `macd_rules`) fires in the wrong direction or at the wrong time. Checking price data reveals stale prices (minutes apart) in `price_history`. The signal falsely interprets a resumed data feed as a price gap.

## Root Cause Pattern
`price_history` (1m bars) can have **data gaps** — missing bars when the HL `allMids` endpoint rate-limits or returns partial data. Only ~191 of 542 tokens get updated each minute. When a token's data is stale:
1. EMA/SMA freeze at the last known values
2. When fresh data arrives (minutes later), the price jump looks like a real gap
3. `detect_gap_cross()` interprets this as a gap crossing and fires the signal in the wrong direction

## Diagnostic Steps

### Step 1: Check which tokens are stale
```python
# In gap300_signals.py or relevant script, add diagnostic:
from analytics import price_history
import time

token = 'XMR'
bars = price_history.get(token, [])
if bars:
    last = bars[-1]
    age = time.time() - last['timestamp']
    print(f'{token}: {len(bars)} bars, last age={age:.0f}s')
    
    # Check for bar gaps
    for i in range(1, len(bars)):
        gap = bars[i]['timestamp'] - bars[i-1]['timestamp']
        if gap > 150:
            print(f"  BAR GAP at index {i}: {gap:.0f}s")
```

### Step 2: Verify with live candles.db
```bash
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/candles_1m.db')
cur = conn.cursor()
cur.execute(\"SELECT symbol, ts, c FROM candles WHERE symbol='XMR' ORDER BY ts DESC LIMIT 5\")
for row in cur.fetchall():
    print(f'{row[0]} ts={row[1]} age={time.time()-row[1]:.0f}s close={row[2]}')
"
```

### Step 3: Check journal for collector behavior
```bash
journalctl -u price-collector -n 50 --no-pager
```

## Two-Part Fix

### Fix 1: Statistical bar-gap guard (ROOT FIX)
In `gap300_signals.py` `detect_gap_cross()`, add after fetching bars:

```python
# Compute bar gaps to detect data gaps (not market gaps)
bar_gaps = [bars[i]['timestamp'] - bars[i-1]['timestamp'] 
            for i in range(1, len(bars))]
mean_gap = sum(bar_gaps) / len(bar_gaps)
std_gap = (sum((g - mean_gap)**2 for g in bar_gaps) / len(bar_gaps)) ** 0.5
max_acceptable = max(150, mean_gap + 3 * std_gap)
if any(g > max_acceptable for g in bar_gaps):
    return None  # Data gap — not a real price gap
```

**Key insight**: HL API normal jitter is 60-120s bars. Data gaps are >150s. The threshold must be adaptive (mean + 3σ) since some tokens trade at 60s intervals, others at 120s.

### Fix 2: Stale threshold — 5 min → 2 min
Apply to ALL signal scripts reading from `price_history` or aggregating from candles:
- `zscore_momentum.py`
- `volume_1m_signals.py`
- `pattern_scanner.py`
- `ma_cross_signals.py`
- `ma_fast_signals.py`
- `rs_signals.py`
- `r2_trend_signals.py`
- `macd_rules.py`
- `macd_1m_signals.py`
- `ma300_candle_confirm_signals.py`
- `ma_cross_5m.py` ← also has fallback aggregation path (see below)

Change: `> 300` → `> 120` (seconds)

```python
# Before
if time.time() - bars[-1]['timestamp'] > 300:
    return None

# After  
if time.time() - bars[-1]['timestamp'] > 120:
    return None
```

### Fix 3: FALLBACK PATH bug — the hidden staleness bypass
**Critical**: Some signals have **two data paths** — a primary source and a fallback aggregator. The primary has a staleness check, but the fallback often doesn't — creating a bypass vector.

**Example — `ma_cross_5m.py`**:
- Primary path (`_get_candles_5m`): reads from `candles_5m` (Binance, 5m candles), staleness was `> 900` (15 min) — too loose
- **Fallback path** (`_aggregate_5m_from_1m`): reads from `candles_1m`, aggregates to 5m — **had NO staleness check at all**

When `candles_5m` was empty or stale, the signal fell through to the 1m aggregator with zero protection against stale data.

Fix: Add staleness check to the fallback path before aggregating:

```python
def _aggregate_5m_from_1m(token, lookback_1m):
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    c = conn.cursor()
    # Staleness check on candles_1m before using them
    c.execute("SELECT MAX(ts) FROM candles_1m WHERE token = ?", (token.upper(),))
    row = c.fetchone()
    if row and row[0] and (time.time() - row[0]) > 120:
        conn.close()
        return []  # Refuse stale 1m data
    # ... then proceed with aggregation
```

Also change primary path from `> 900` → `> 120` since `candles_5m` is Binance 5m candles (refreshes every 5 min, not 15).

**Always check for fallback/aggregation paths** when fixing staleness — the primary path protection is useless if the fallback bypasses it.

## Verification
After applying fixes, test live:
```python
import gap300_signals
prices = gap300_signals._get_1m_prices('XMR', 350)
if prices:
    closes = [p['price'] for p in prices]
    result = gap300_signals.detect_gap_cross('XMR', prices, closes[-1])
    print(f'gap-300 result: {result}')
```

Expected: `gap-300 result: {'direction': 'LONG', ...}` for stale tokens (no false SHORT).

## Files Modified (2026-04-23)
- `/root/.hermes/scripts/gap300_signals.py` — bar-gap guard + stale=120s
- `/root/.hermes/scripts/ma_cross_5m.py` — stale=120s (primary + fallback), fallback had NO staleness check
- All signal scripts above — stale=120s
