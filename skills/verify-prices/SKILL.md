---
name: verify-prices
description: Comprehensive candle and price data integrity audit for Hermes. Verifies no gaps, no stale data, no OHLC violations across all active tokens and timeframes. Run whenever signals appear wrong, prices seem stale, or as a routine health check.
category: trading
author: T
created: 2026-04-25
---

# Verify Prices — Candle & Price Data Integrity Audit

Checks candle chain continuity, OHLC validity, stale data, and price_history freshness across all active tokens. Diagnoses the root cause of mis-firing signals.

## What This Checks

1. **Candle chain continuity** — no missing windows for any active token across 1m/5m/15m/1h/4h
2. **OHLC validity** — high ≥ low, high ≥ open/close, low ≤ open/close, prices > 0
3. **is_closed correctness** — latest candle should be `is_closed=0` (developing) or very recent
4. **Stale candle detection** — tokens with `is_closed=1` but age > 3x tf (gap indicator)
5. **price_history freshness** — allMids polling active tokens, no gaps in last 5 min
6. **Schema consistency** — `is_closed` column present where expected

## How to Run

### Step 1 — Quick Health Summary (fast)

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime

db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
conn.text_factory = str
cur = conn.cursor()
now = datetime.now().timestamp()

print("=== CANDLES DB HEALTH SUMMARY ===\n")
for tf_name in ['candles_1m', 'candles_5m', 'candles_15m', 'candles_1h', 'candles_4h']:
    cur.execute(f"SELECT COUNT(DISTINCT token) FROM {tf_name}")
    token_count = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tf_name}")
    total_rows = cur.fetchone()[0]
    print(f"{tf_name}: {total_rows} rows, {token_count} tokens")

print()
# Schema check
for tf_name in ['candles_1m', 'candles_5m', 'candles_15m', 'candles_1h', 'candles_4h']:
    cur.execute(f"PRAGMA table_info({tf_name})")
    cols = [r[1] for r in cur.fetchall()]
    has_closed = 'is_closed' in cols
    print(f"{tf_name}: is_closed={'YES' if has_closed else 'NO'}")

conn.close()
EOF
```

### Step 2 — Active Token Chain Check (most important)

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime

db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
conn.text_factory = str
cur = conn.cursor()
now = datetime.now().timestamp()

sig_conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
sig_cur = sig_conn.cursor()

# Get active tokens (price_history updated < 5 min ago)
sig_cur.execute("""
    SELECT token, MAX(timestamp)
    FROM price_history
    GROUP BY token
    HAVING MAX(timestamp) > ?
    ORDER BY MAX(timestamp) DESC
""", (now - 300,))
active_tokens = [r[0] for r in sig_cur.fetchall()]
print(f"Active tokens (price_history < 5min old): {len(active_tokens)}")

# Check 15m chain continuity for all active tokens
print(f"\n=== 15m CHAIN CONTINUITY (all active tokens) ===")
tf = 900
gaps = []
for token in active_tokens:
    cur.execute(f"""
        SELECT ts, is_closed FROM candles_15m
        WHERE token=? AND ts >= ?
        ORDER BY ts
    """, (token, now - 14400))  # last 4h
    rows = cur.fetchall()
    if not rows:
        print(f"  {token}: NO 15m DATA")
        continue
    for i in range(1, len(rows)):
        if rows[i][0] != rows[i-1][0] + tf:
            dt_prev = datetime.fromtimestamp(rows[i-1][0]).strftime('%H:%M')
            dt_curr = datetime.fromtimestamp(rows[i][0]).strftime('%H:%M')
            gaps.append(f"  GAP {token}: {dt_prev} -> {dt_curr}")

if not gaps:
    print(f"  All {len(active_tokens)} active tokens: NO GAPS")
else:
    print(f"  GAPS FOUND ({len(gaps)}):")
    for g in gaps[:20]:
        print(g)

sig_conn.close()
conn.close()
EOF
```

### Step 3 — OHLC Violations Check

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime

db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
conn.text_factory = str
cur = conn.cursor()
now = datetime.now().timestamp()

print("=== OHLC INVALIDITY CHECK ===\n")
for tf_name in ['candles_1m', 'candles_5m', 'candles_15m', 'candles_1h', 'candles_4h']:
    cur.execute(f"""
        SELECT token, ts, high, low, open, close
        FROM {tf_name}
        WHERE high < low OR high < open OR high < close OR low > open OR low > close OR open <= 0 OR close <= 0
        LIMIT 10
    """)
    rows = cur.fetchall()
    if rows:
        print(f"{tf_name} violations:")
        for r in rows:
            dt = datetime.fromtimestamp(r[1]).strftime('%Y-%m-%d %H:%M')
            print(f"  {r[0]} {dt}: H={r[2]} L={r[3]} O={r[4]} C={r[5]}")
    else:
        print(f"{tf_name}: OK (no violations)")

conn.close()
EOF
```

### Step 4 — Stale Closed Candles (possible gap indicators)

**⚠ CRITICAL: `is_closed=0` on higher TFs is NORMAL, not stale.**
A 1h candle with `is_closed=0` at 01:05 means it's still building — it closes at 02:00.
Only `is_closed=1` with age > 3× tf is actually stale.
The naive query `MAX(ts)` will return the developing window as "last" — always filter by `is_closed=1` when checking for staleness.

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime

db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
conn.text_factory = str
cur = conn.cursor()
now = datetime.now().timestamp()

sig_conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
sig_cur = sig_conn.cursor()

# CORRECT stale check: only is_closed=1 rows, age > 3x tf
print("=== STALE CLOSED CANDLES (is_closed=1 + age > 3x tf) ===\n")
for tf_name, tf_sec in [('candles_15m', 900), ('candles_1h', 3600), ('candles_4h', 14400)]:
    threshold = tf_sec * 3  # 3x tf = definitely stale
    stale = []
    # CORRECT: filter is_closed=1 AND age > 3x tf
    cur.execute(f"""
        SELECT a.token, a.ts, a.is_closed,
               (SELECT COUNT(*) FROM {tf_name} WHERE token=a.token AND ts > a.ts) as future_count
        FROM {tf_name} a
        INNER JOIN (
            SELECT token, MAX(ts) as max_ts
            FROM {tf_name}
            WHERE is_closed = 1
            GROUP BY token
        ) b ON a.token = b.token AND a.ts = b.max_ts
        WHERE a.is_closed = 1 AND a.ts < ?
    """, (now - threshold,))
    stale = cur.fetchall()

    active_stale = []
    ancient_stale = []
    for token, ts, is_closed, future_count in stale:
        sig_cur.execute("SELECT COUNT(*) FROM price_history WHERE token=?", (token,))
        in_ph = sig_cur.fetchone()[0] > 0
        age = now - ts
        if in_ph:
            active_stale.append((token, ts, age))
        else:
            ancient_stale.append((token, ts, age))

    print(f"{tf_name} (stale if is_closed=1 AND age > {threshold}s = {threshold/3600:.1f}h):")
    if active_stale:
        print(f"  ACTIVE (in price_history) - NEEDS INVESTIGATION:")
        for token, ts, age in sorted(active_stale, key=lambda x: -x[2])[:5]:
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            print(f"    {token}: {dt} age={age/3600:.1f}h")
    if ancient_stale:
        print(f"  ANCIENT (not in price_history) - likely blacklist/inactive:")
        for token, ts, age in sorted(ancient_stale, key=lambda x: -x[2])[:5]:
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            print(f"    {token}: {dt} age={age/86400:.0f} days")
    if not active_stale and not ancient_stale:
        print(f"  No stale closed candles")
    print()

sig_conn.close()
conn.close()
EOF
```

**Why `MAX(ts) WHERE is_closed=0` is misleading:**
- 1h: `MAX(ts) WHERE is_closed=0` = current open window (e.g., 20:00 for 20:00-21:00 window) — this is NOT stale, it's developing
- 4h: same — the 20:00 developing window will close at 24:00
- Always use `MAX(ts) WHERE is_closed=1` to find the last truly closed window

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime

db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
conn.text_factory = str
cur = conn.cursor()
now = datetime.now().timestamp()

sig_conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
sig_cur = sig_conn.cursor()

# Get all tokens with their latest candle per TF
print("=== STALE is_closed=1 CHECK (all TFs) ===\n")
for tf_name, tf_sec in [('candles_15m', 900), ('candles_1h', 3600), ('candles_4h', 14400)]:
    threshold = tf_sec * 3  # 3x tf age = definitely stale
    stale = []
    cur.execute(f"""
        SELECT a.token, a.ts, a.is_closed,
               (SELECT COUNT(*) FROM {tf_name} WHERE token=a.token AND ts > a.ts) as future_count
        FROM {tf_name} a
        INNER JOIN (
            SELECT token, MAX(ts) as max_ts
            FROM {tf_name}
            GROUP BY token
        ) b ON a.token = b.token AND a.ts = b.max_ts
        WHERE a.is_closed = 1 AND a.ts < ?
    """, (now - threshold,))
    stale = cur.fetchall()
    
    active_stale = []
    ancient_stale = []
    for token, ts, is_closed, future_count in stale:
        # Check if token is in price_history (active)
        sig_cur.execute("SELECT COUNT(*) FROM price_history WHERE token=?", (token,))
        in_ph = sig_cur.fetchone()[0] > 0
        age = now - ts
        if in_ph:
            active_stale.append((token, ts, age))
        else:
            ancient_stale.append((token, ts, age))
    
    print(f"{tf_name} (stale if age > {threshold}s = {threshold/3600:.1f}h):")
    if active_stale:
        print(f"  ACTIVE (in price_history) - NEEDS INVESTIGATION:")
        for token, ts, age in sorted(active_stale, key=lambda x: -x[2])[:5]:
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            print(f"    {token}: {dt} age={age/3600:.1f}h")
    if ancient_stale:
        print(f"  ANCIENT (not in price_history) - likely blacklist/inactive:")
        for token, ts, age in sorted(ancient_stale, key=lambda x: -x[2])[:5]:
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            print(f"    {token}: {dt} age={age/86400:.0f} days")
    if not active_stale and not ancient_stale:
        print(f"  No stale candles")

sig_conn.close()
conn.close()
EOF
```

### Step 5 — price_history Freshness

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime

sig_conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
sig_cur = sig_conn.cursor()
now = datetime.now().timestamp()

sig_cur.execute("""
    SELECT token, MAX(timestamp), COUNT(*)
    FROM price_history
    GROUP BY token
    ORDER BY MAX(timestamp) ASC
""")
all_tokens = sig_cur.fetchall()

# Tokens with no updates in 1h
stale = [(t, max_ts, cnt) for t, max_ts, cnt in all_tokens if now - max_ts > 3600]
fresh = [(t, max_ts, cnt) for t, max_ts, cnt in all_tokens if now - max_ts <= 3600]

print(f"=== price_history FRESHNESS ===\n")
print(f"Total tokens in price_history: {len(all_tokens)}")
print(f"Fresh (< 1h old): {len(fresh)}")
print(f"Stale (> 1h old): {len(stale)}")

if stale:
    print(f"\nStale tokens:")
    for token, max_ts, cnt in sorted(stale, key=lambda x: x[1])[:10]:
        dt = datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M')
        age = now - max_ts
        print(f"  {token}: last={dt} age={age/3600:.1f}h entries={cnt}")

sig_conn.close()
EOF
```

### Step 6 — BTC (Canary) Deep Dive

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime
import math

db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
conn.text_factory = str
cur = conn.cursor()
now = datetime.now().timestamp()

print("=== BTC CANDLE DEEP DIVE (canary) ===\n")

# Current window boundaries
for tf_name, tf_sec in [('candles_1m',60),('candles_5m',300),('candles_15m',900),('candles_1h',3600),('candles_4h',14400)]:
    current_window = math.floor(now / tf_sec) * tf_sec
    age = now - current_window
    print(f"{tf_name}: current_window={datetime.fromtimestamp(current_window).strftime('%H:%M')} started={age:.0f}s ago")

print()
for tf_name, tf_sec in [('candles_1m',60),('candles_5m',300),('candles_15m',900),('candles_1h',3600),('candles_4h',14400)]:
    cur.execute(f"""
        SELECT ts, is_closed, open, high, low, close
        FROM {tf_name}
        WHERE token='BTC' AND ts >= ?
        ORDER BY ts
    """, (now - tf_sec * 10,))
    rows = cur.fetchall()
    print(f"\n{tf_name} (last 10 windows):")
    gaps = 0
    for r in rows:
        dt = datetime.fromtimestamp(r[0]).strftime('%H:%M')
        age = now - r[0]
        if r[1] == 1:
            status = f"CLOSED age={age:.0f}s"
        else:
            status = f"OPEN   age={age:.0f}s"
        if len(rows) > 1:
            prev_idx = rows.index(r) - 1
            if prev_idx >= 0 and rows[prev_idx][0] != r[0] - tf_sec:
                gaps += 1
                status += " ** GAP **"
        print(f"  {dt}: {status} O={r[2]:.2f} C={r[5]:.2f}")
    print(f"  Gaps: {gaps}")

conn.close()
EOF
```

### Step 7 — 1m Candle Freshness (gap300_5m warmup check)

**`gap300_5m` needs 400 recent 1m bars for EMA300 warmup.** If `candles_1m` is stale, the signal silently returns `None`.

```bash
cd /root/.hermes && python3 << 'EOF'
import sqlite3
from datetime import datetime

candles_conn = sqlite3.connect('/root/.hermes/data/candles.db')
candles_conn.text_factory = str
ccur = candles_conn.cursor()
now = datetime.now().timestamp()

print("=== candles_1m FRESHNESS (gap300_5m warmup) ===\n")
print("gap300_5m needs LOOKBACK_1M=400 bars (~6.5h). Stale 1m = silent None.\n")

ccur.execute("SELECT COUNT(DISTINCT token) FROM candles_1m")
total_tokens = ccur.fetchone()[0]
print(f"Tokens with 1m candles: {total_tokens}")

# CORRECT: candles_1m (candles.db) and price_history (signals_hermes.db) are TWO DIFFERENT DBs
# Cross-schema SQL (e.g. signals_hermes_runtime.price_history) causes SQL errors
# Always use two separate connections and join in Python
sig_conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
sig_conn.text_factory = str
scur = sig_conn.cursor()

stale = []
fresh = []
for token, max_ts, cnt in ccur.execute(
    "SELECT token, MAX(ts), COUNT(*) FROM candles_1m GROUP BY token ORDER BY MAX(ts) ASC"
).fetchall():
    age = now - max_ts
    if age > 7200:  # 2h
        stale.append((token, max_ts, age, cnt))
    else:
        fresh.append((token, max_ts, age, cnt))

print(f"Fresh (1m < 2h old): {len(fresh)}")
print(f"Stale (1m > 2h old): {len(stale)}")
if stale:
    print(f"\nSTALE 1m tokens (gap300_5m will fail silently):")
    for token, max_ts, age, cnt in sorted(stale, key=lambda x: -x[2])[:10]:
        dt = datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M')
        print(f"  {token}: last_1m={dt} age={age/3600:.1f}h bars={cnt}")
    print(f"\n  Root cause: _seed_universe_candles only seeds 2 tokens/run")
    print(f"  Fix: increase TOKENS_PER_RUN in price_collector._seed_universe_candles")

candles_conn.close()
sig_conn.close()
EOF
```

## Schema Reference (Verified 2026-04-30)

| Table | `is_closed`? | Notes |
|-------|-------------|-------|
| `candles_1m` | **YES** | Developing candles correctly tracked. `is_closed=0` means current window, `is_closed=1` means closed. |
| `candles_5m` | **YES** | Same as 1m — developing candles correctly tracked. |
| `candles_15m` | YES | Closed window tracking |
| `candles_1h` | YES | Closed window tracking |
| `candles_4h` | YES | Closed window tracking |

**Important:** `is_closed=0` on higher TFs (1h/4h) does NOT mean stale — it means the candle is still developing and will close at the natural interval boundary. A 1h candle with `is_closed=0` at 01:05 is perfectly normal (it closes at 02:00). Only `is_closed=1` with age > 3× interval is stale.

The old skill said "1m and 5m have NO `is_closed`" — this is incorrect. They do have it.

## Expected States

- Latest candle should be `is_closed=0` (developing) or closed within the current window period
- `is_closed=1` with age > 3× tf = **stale** (possible gap)
- Any token NOT in `price_history` = not in signal pipeline (blacklist or inactive)
- OHLC violations = **never acceptable** (data corruption)

## Known Root Causes (Updated 2026-04-30)

1. **"Stale developing candles" — FALSE ALARM.** `is_closed=0` on higher TFs means the candle is still developing, not stale. A 1h candle at 01:05 with `is_closed=0` closes at 02:00 — this is normal. The system is working correctly.

2. **`_aggregate_1m.py` hardcodes `volume=0`** — this is the real volume problem. The aggregator reads price-only ticks from `price_history` and writes `volume=0`. Fix: source OHLCV from Binance klines. See `binance-volume-refresh` skill.

3. **`price_collector.py` Binance seed rate-limited** — only ~2 tokens per run cycling through 230 tokens. This causes higher-TF staleness for most tokens (not 1m, which is fresh from price_history). See `binance-volume-refresh` skill.

4. **5m aggregator timer drift** — `hermes-5m-candle.timer` fires every 5 min but the aggregator takes ~20s to run, causing it to complete 14-29 min behind real time. The 5m candles are always the developing window; 15m candles derived from them never close on schedule.

5. **`gap300_5m_signals.py` reading wrong 1m source** — `_aggregate_tf` aggregates `{5m,15m,1h,4h}` from `price_history` but **never touches `candles_1m`**. Only `_seed_universe_candles` (Binance API, 2 tokens/run) writes 1m candles. With 170+ tokens, a given token gets ~85 min between refreshes. **gap300_5m signal silently returns `None`** when 1m warmup is insufficient (needs 400 bars ~6.5h).

   **The correct fix:** Change `gap300_5m_signals.py` `_get_1m_closes_for_ema300()` to read from `price_history` (signals_hermes.db) instead of `candles_1m` (candles.db). Data comparison for AAVE:
   - `candles_1m`: 16,411 rows, most recent bar ~3.5h stale
   - `price_history`: 30,988 rows, most recent bar CURRENT (fresh)

   `price_history` has continuous 1m data — far more than the 400 bars needed for EMA300 warmup.

6. **`hl_cache.json` has THREE schema traps:**
   - **Wrong key:** code reads `mids` but live HL API stores mids under `allMids`. Always check `d.get('allMids', {})` not `d.get('mids', {})`.
   - **Wrong age check:** `cache_age` key does not exist in the live file. If the file exists but reads as 0 tokens, dump the first 500 chars of the file to inspect the actual schema.
   - **Stale token mappings cause phantom signals:** A token in `hl_cache.json` may no longer exist on Hyperliquid (e.g., ILV was in cache at $12.118 but HL returned None for ILV). `price_collector.py` refreshes `allMids` but never removes delisted tokens. When a signal fires for a coin at price ~$4.66, the token name resolves to a stale mapping from cache (ILV) while the actual HL coin is FRIEND. Guardian cannot execute because the token doesn't exist on HL.

   **Diagnosis:** Always verify token existence against live HL API, never trust `hl_cache.json`:
   ```bash
   python3 -c "
   import urllib.request, json
   req = urllib.request.Request('https://api.hyperliquid.xyz/info',
       headers={'Content-Type': 'application/json'},
       data=json.dumps({'type': 'allMids'}).encode())
   with urllib.request.urlopen(req, timeout=5) as r:
       mids = json.loads(r.read()).get('allMids', {})
       print('TOKEN in live HL:', mids.get('TOKEN', 'NOT ON HL'))
   "
   ```
   ```bash
   head -c 500 /var/www/hermes/data/hl_cache.json
   # Should show "allMids" not "mids"
   ```
   This causes `speed_history.json` to go stale — price polling writes to `speed_history.json` but reads from `hl_cache.json` which may have the wrong key.

**Critical: always cross-check speed data against `token_speeds` table, never `speed_history.json`.**

7. **`signal_gen` timeout at 180s — ROOT CAUSE FOUND (2026-05-04)**

**Symptom**: `signal_gen` taking 134-140s, causing pipeline to start new runs before previous ones finish.

**Root cause**: `scan_rs_signals` in `rs_signals.py` doing O(N²) swing detection + O(M×N) level touch counting. Pre-fix: 211.5s for 191 tokens. cProfile showed 1.16 billion `abs()` calls.

**Actual fix**: NumPy vectorization of `_find_swing_highs_lows` and `_build_level_touches` in `rs_signals.py`. Result: ~9s for scan_rs_signals, ~25s total signal_gen. See `hermes-signal-debugging` skill → `references/signal-gen-perf-fix.md`.

### 7. `scan_rs_signals` Stale-Looking but Actually Fine (2026-05-04)

**Symptom**: `scan_rs_signals` taking 134-140s, pipeline log shows `Running signal_gen...` then waits 2+ minutes.

**NOT a data freshness issue.** The RS scanner reads from `candles.db` → `candles_1m` which IS fresh (price_collector runs every 1 min). The staleness impression came from confusing the **developing vs closed window** display issue above.

**Actual root cause**: `scan_rs_signals` was doing O(N²) swing detection + O(M×N) touch counting for 191 tokens = 211 seconds. Fixed by NumPy vectorization in `rs_signals.py`. See `hermes-signal-debugging` skill → `references/signal-gen-perf-fix.md`.

## Data Source Freshness Map

| Source | Location | Freshness | Use For |
|--------|----------|-----------|---------|
| Live prices | `signals_hermes.db` → `price_history` | **< 1 min** | Signal generation ONLY |
| Live speeds | `signals_hermes_runtime.db` → `token_speeds` | **< 5 min** | Wave/speed calculations |
- `hermes-5m-candle.timer` — every 5 min

### References

See `references/price-collector-timing.md` for full cycle timing breakdown, staleness threshold analysis, and lock contention reproduction steps.

---

## Price Freshness Thresholds

**Measured cycle time: ~87s total.** Breakdown:
- Imports: ~2.0s
- `fetch_all_prices()` (HL API): ~0.1s
- `save_prices()` (signals_hermes.db write + backfill): ~2.0s
- `_aggregate_tf()` for 4 TFs (5m/15m/1h/4h): **~82s** — candles.db aggregation is the bottleneck
- `_seed_universe_candles()`: ~0.0s

### Lock Contention — candles.db

`price_collector` and `hermes-1m-candle.timer` → `_aggregate_1m.py` BOTH write to candles.db simultaneously. This causes "database is locked" errors for price_collector's 5m/15m/1h/4h aggregation steps. The two processes fight over candles.db WAL locks.

**Effect on signal scripts:** The 120s staleness threshold used in signal scripts (e.g., zscore_pump.py `_get_1m_prices()`) is barely sufficient at 87s nominal cycle time — a single lock contention event pushes effective cycle past 120s, triggering false stale warnings.

**Fix:** Raise staleness threshold from 120s → **180s** in signal scripts that read `price_history`. This absorbs the lock-contention variance without architecture changes.

### Timer Files

- `hermes-price-collector.timer` — every 1 min (fires price_collector.py)
- `hermes-1m-candle.timer` — every 1 min (fires _aggregate_1m.py) — **redundant**, adds lock contention, consider disabling
- `hermes-5m-candle.timer` — every 5 min
| 5m/15m/1h/4h | `candles.db` → `candles_*m` | **< 10 min** | Indicator computation |
| `hl_cache.json` | `/var/www/hermes/data/` | **< 30s** | Has schema bugs (see above) |
| `speed_history.json` | `/root/.hermes/data/` | **STALE since ~Apr 29** | DO NOT USE |
| `price_history.db` | `/root/.hermes/data/` | **0 bytes — EMPTY** | DO NOT USE |

## 1m Data — Critical Discovery (2026-05-04)

**`ohlcv_1m` in `signals_hermes.db` is REAL 1m data but extremely sparse:**
- Only ~0.5–0.8 days of data per token (650-1133 rows)
- Covers Apr 1–30, 2026
- Most tokens: ~650 rows ≈ 10 hours of 1m candles
- NOT suitable for backtesting 1m speed thresholds — 100% of the 2566 trades had ZERO usable 1m candles in their entry windows

**`price_history.db` is 0 bytes — EMPTY. Do not use.**

**`price_history` TABLE in `signals_hermes.db` is 1-MINUTE resolution, NOT hourly:**
- 7.6M rows, 191 tokens, spanning 2024-Jan to 2026-May
- ~40,000 rows per traded token ≈ 28 days of 1m data
- **98% of the 2566 trades have >= 30 usable 1m candles in ±30min entry window**
- Timestamps are in SECONDS (unlike ohlcv_1m which uses milliseconds)
- Use this for 1m speed threshold validation

**Key finding from 1m vs 5m speed sweep:**
- 1m turns profitable at speed >= 2.0% (better discrimination than 5m)
- 5m turns profitable at speed >= 2.5%
- Both timeframes converge: speed >= 2.0-2.5% is the key threshold
- 1m produces ~33% fewer trades with better WR at the profitable zone

**DB paths summary:**
- `signals_hermes.db` → `price_history`: 1m resolution, use for 1m analysis ✓
- `signals_hermes.db` → `ohlcv_1m`: real 1m but sparse, use sparingly
- `candles.db` → `candles_5m`: 5m resolution, primary for live signal speed

## Files

- Candles DB: `/root/.hermes/data/candles.db`
- Price history DB: `/root/.hermes/data/signals_hermes.db`
- Price collector: `/root/.hermes/scripts/price_collector.py`
- Speed source (LIVE): `/root/.hermes/data/signals_hermes_runtime.db` → `token_speeds` table — **use this, NOT speed_history.json**
- Speed source (STALE): `/root/.hermes/data/speed_history.json` — abandoned since ~2026-04-29, do not use
- Speed source (LIVE): `/root/.hermes/data/signals_hermes_runtime.db` → `token_speeds` table — **use this, NOT speed_history.json**
- Speed source (STALE): `/root/.hermes/data/speed_history.json` — abandoned since ~2026-04-29, do not use
