---
name: hermes-signal-debug
description: Debug Hermes signal_gen when only pattern_scanner signals appear, covering is_delisted rate limits, NameError crashes, and pipeline log analysis
triggers:
  - signal_gen broken
  - only pattern_scanner signals
  - 429 rate limit signal_gen
  - hot-set empty
---

# Hermes Signal Generation Debugging

## Context
When signal_gen produces only `pattern_scanner` signals and no MTF-MACD/momentum/confluence signals, the root causes are typically:

1. **Crash in `compute_score`** — a `NameError` or exception on the first token kills the entire main loop before other signal types run. Pattern scanner runs first and survives.
2. **Per-token `is_delisted()` calls** — 190 tokens × 1 `_get_meta()` call = 190 `_http_post` calls to HL → 429 rate limits
3. **`hotset.json` stale** — causes empty hot-set fallback to only 4 tokens from DB
4. **Binance API rate limits in macd_rules** — 570 calls per cycle (3 TFs × 190 tokens) → 429s

## Debugging Checklist

### Step 1 — Check the pipeline log first
```bash
tail -100 /root/.hermes/logs/pipeline.log | grep -E "ERR|signal_gen|Active universe"
```
This tells you:
- Whether signal_gen is crashing, rate-limiting, or running clean
- How many tokens are in the active universe
- Whether pattern signals are being written

### Step 2 — Find ALL HTTP calls in signal_gen
```bash
grep -rn "_hl_info\|_http_post\|requests\.\|urllib" /root/.hermes/scripts/signal_gen.py
grep -rn "def is_delisted\|def _get_meta" /root/.hermes/scripts/hyperliquid_exchange.py
```
`is_delisted()` calls `_get_meta()` → `_hl_info()` → `_http_post()` — one call per token.

### Step 3 — Find where stderr/ERR lines originate
`run_pipeline.py` line 74 prefixes `ERR {name}:` to any stderr line from signal_gen. Inside signal_gen, look for:
- `sys.stderr.write(f"[_http_post] 429 rate-limited..."` in hyperliquid_exchange
- Any print/write that starts with `ERR signal_gen:`

### Step 4 — Trace HTTP calls at runtime
```python
import hyperliquid_exchange as hl
_orig = hl._http_post
def trace_post(endpoint, payload, timeout=10):
    import traceback; traceback.print_stack()
    return _orig(endpoint, payload, timeout)
hl._http_post = trace_post
```
This shows exactly which line triggered each HTTP call.

### Step 5 — Check is_delisted call count
`grep -c "is_delisted(" /root/.hermes/scripts/signal_gen.py` — if > 1, it's being called per-token.

## Known Bugs

### Bug: `z_dir` undefined in compute_score
**File:** signal_gen.py line ~1066  
**Symptom:** `NameError: name 'z_dir' is not defined` crashes compute_score on first token  
**Fix:** `z_dir != 'rising'` → `mom['z_direction'] != 'rising'`

### Bug: Per-token is_delisted() calls
**File:** signal_gen.py — 6 call sites  
**Symptom:** 190 `_get_meta()` → `_hl_info()` → `_http_post()` calls per run → 429 rate limits  
**Fix:** Add `_DELISTED_SET` loaded once via `get_tradeable_tokens()` at run() start. Replace `is_delisted()` with `_is_delisted_cached()` everywhere.

### Bug: MTF-MACD reading from wrong data source (price_history vs candles.db)
**File:** signal_gen.py `_macd_crossover()`  
**Symptom:** MTF-MACD produces no signals for most tokens (only ~4 previous 4H bars from price_history hourly ticks). Works on high-volume tokens with enough price_history rows.  
**Root cause:** `_macd_crossover()` was aggregating `price_history` (HL hourly ticks, 2000 row cap) instead of reading directly from `candles.db` 4H table. For BTC: ~2000 price_history rows ≈ 4 x 4H bars (not enough for MACD slow=65). candles.db 4H table: 568 rows ≈ 97 x 4H bars (sufficient).  
**Fix:** `_macd_crossover()` now reads from `candles.db` 4H table via `fetch_candles_db(token, "4h")`. Falls back to 1m aggregation only if 4H is sparse.  
**Also fix:** Add `'1m': 1000` to candle seeding intervals in `price_collector.py` so 1m candles are available for fallback.

### Bug: `get_ohlcv_1m()` unit mismatch (ms vs seconds)
**File:** `signal_schema.py` line ~1968
**Symptom:** Noisy signals or no signals for any script using this function. SQL query: `WHERE open_time > ?` compares millisecond timestamps against Unix seconds.
**Root cause:** `ohlcv_1m.open_time` stored in **milliseconds** but `cutoff = int(time.time()) - (lookback_minutes * 60)` is in **seconds**. Result: `WHERE open_time > 1776953468` matches all 24,717 rows instead of ~60.
**Dormant:** No active signal script calls `get_ohlcv_1m()` — all use their own `_get_candles_1m` reading `price_history`. If re-enabled, MUST divide `cutoff` by 1000.
**Fix:** Change cutoff calculation to `cutoff = int(time.time() * 1000) - (lookback_minutes * 60 * 1000)`

### Bug: macd_rules hitting Binance on every signal_gen
**File:** macd_rules.py `_fetch_binance_candles()`  
**Symptom:** 570 Binance API calls per cycle → 429 rate limits  
**Fix:** Read from local `candles.db` first, Binance only as fallback. See `macd_rules._fetch_binance_candles()`.

## Critical: Cooldown Cross-Contamination Bug (Empty Hot-Set)

**Symptom:** Hot-set shows 0 entries despite signals being generated. `signal_compactor` finds signals, scores them, but ALL get blocked by `LOSS-COOLDOWN skip`.

**Root Cause:** Two bugs compounding:
1. `set_cooldown()` in `signal_schema.py` writes cooldowns to `loss_cooldowns.json` with `reason='signal'` (from signal generators like gap300/ma_cross_5m/zscore_momentum)
2. `_is_loss_cooldown_active()` (called by `signal_compactor`) was blocking ALL entries in `loss_cooldowns.json` regardless of `reason` field

**Effect:** 182 signal-generator cooldowns (reason='signal') blocked all 10 multi-source confluence signals, leaving hot-set empty.

**Fix (2026-04-23):**
- `_is_loss_cooldown_active()` now only blocks entries where `reason='loss'` (actual guardian losses). Entries with `reason='signal'` are ignored.
- `loss_cooldowns.json` purged of all 178 stale 'signal' entries.

**Key files:**
- `signal_schema.py` `_is_loss_cooldown_active()` — only blocks `reason='loss'`
- `loss_cooldowns.json` — purge command:
  ```python
  import json, time
  now = time.time()
  with open('/root/.hermes/data/loss_cooldowns.json') as f:
      cooldowns = json.load(f)
  cleaned = {k:v for k,v in cooldowns.items()
             if v.get('reason') == 'loss' and v.get('expires', 0) > now}
  with open('/root/.hermes/data/loss_cooldowns.json', 'w') as f:
      json.dump(cleaned, f)
  ```

**Design rule:** `loss_cooldowns.json` is shared by BOTH signal generators (set cooldown after emitting) AND guardian (set cooldown after losing trade). The `reason` field is the only way to distinguish them. Always use the correct reason value when calling `set_cooldown`.

## Architecture Constraint
- **price_collector**: 1 HL API call/min (prices + candle seeding for all TFs: 1m, 15m, 1h, 4h)
- **signal_gen**: 0 HL API calls for signals (delisted check batched to 1 call at start)
  - MTF-MACD (`_macd_crossover`): reads from `candles.db` 4H table — NOT from price_history
  - macd_rules: 0 Binance API calls (local candles.db first, Binance only as fallback)
  - pattern_scanner: pure local computation

**Active signal scripts (2026-04-23):**
| Script | Source in signal_gen | Data Source |
|--------|---------------------|-------------|
| gap300_signals.py | `from gap300_signals import scan_gap300_signals` | `price_history` direct |
| ma_cross_5m.py | `from ma_cross_5m import scan_ma_cross_5m_signals` | `candles_5m` (fresh <5min) |
| zscore_momentum.py | `from zscore_momentum import _run_zscore_momentum_signals` | `price_history` via `get_price_history()` |
| volume_1m_signals.py | `from volume_1m_signals import scan_volume_1m_signals` | `price_history` (price) + `candles_1m` (volume) |
| pattern_scanner.py | inline `_run_pattern_signals()` | `price_history` direct |

**DISABLED signal scripts:**
- `macd_1m_signals.py` — DISABLED 2026-04-22
- `rs_signals.py` — DISABLED 2021-04-21
- `r2_trend_signals.py` — DISABLED 2026-04-22
- `ma300_candle_confirm_signals.py` — DISABLED 2026-04-22
- `ma_cross_signals.py`, `ma_fast_signals.py` — standalone only, NOT in signal_gen
- `signal_schema.get_ohlcv_1m()` — NOT called by any active signal script (ms/sec bug — see below)

## Known Bugs

**Symptom:** A signal type fires (visible in DB) but never reaches the hot-set/execution. Confluence versions work, solo versions don't.

### Known Bug: OpenClaw gap-300 signals firing wrong direction (2026-04-23)

**Symptom:** `gap-300-` fires SHORT for tokens that should be LONG (ATOM, DOT, REZ). Signals show `source='gap-300-,oc-zscore-v9-'` and `oc-` prefix means OpenClaw.

**Root Cause:** OpenClaw's `oc_signal_importer.py` merges signals from OpenClaw's analysis. Its gap-300 computation reads from a stale data source (`ohlcv_1m` in signals_hermes.db is 7+ days stale for low-volume tokens). When `price_history` resumes after a data gap (e.g., 78 minutes of missing bars for ATOM), the OpenClaw gap-300 sees the price jump from old stale price to new fresh price as a massive gap widening — firing SHORT when it should be LONG.

**Evidence:**
- ATOM: `price_history` has 30-min timestamp gaps. Last bar before gap: 14:20 UTC ($1.86). First bar after gap: 15:38 UTC ($1.88). The 78-min gap in price_history = data gap, not market gap.
- ATOM gap-300 signal price in DB: $1.7177 (stale, OpenClaw's feed). Live price_history at same time: $1.8791.
- Signals show: `('ATOM', 'SHORT', 'gap-300-,oc-zscore-v9-', 1.7177, '2026-04-23 15:03-15:38')` — oc- prefix confirms OpenClaw source.

**Immediate Fix:** Add `gap-300+` and `gap-300-` to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` to block all gap-300 signals (both Hermes AND OpenClaw) until:
1. OpenClaw's gap-300 is fixed to read fresh data
2. OR the `price_history` data pipeline is fixed to eliminate 30-min gaps

**Long-term Fix:** OpenClaw's `oc_signal_importer.py` needs the same data source audit that Hermes' own signal scripts received — ensure gap detection reads from `price_history` (fresh) not from any stale table.

### Step 1 — Check if signals are firing at all
```sql
-- Recent signals of this type
SELECT token, signal_type, source, decision, confidence, survival_score, created_at
FROM signals WHERE source LIKE '%pct-hermes%'
ORDER BY created_at DESC LIMIT 20;

-- Decision breakdown
SELECT decision, COUNT(*) FROM signals
WHERE source LIKE '%pct-hermes%' GROUP BY decision;

-- Rejection reasons
SELECT rejection_reason, COUNT(*) FROM signals
WHERE source LIKE '%pct-hermes%' AND decision='REJECTED'
GROUP BY rejection_reason ORDER BY COUNT(*) DESC;
```

### Step 2 — Check what's beating them in hot-set
```sql
-- Top-scoring active signals (survival_score governs hot-set ranking)
SELECT source, direction, AVG(confidence) as avg_conf, COUNT(*) as cnt
FROM signals WHERE decision IN ('PENDING','APPROVED','HOT')
AND created_at > datetime('now','-24 hours')
GROUP BY source, direction ORDER BY avg_conf DESC LIMIT 20;

-- What's currently PENDING/APPROVED
SELECT token, signal_type, source, decision, survival_score, created_at
FROM signals WHERE created_at > datetime('now','-10 minutes')
AND decision IN ('PENDING','APPROVED') ORDER BY survival_score DESC LIMIT 20;
```

### Known Issue: pct-hermes Dying in Hot-Set Compactor
**Finding (2026-04-22):** pct-hermes signals are generated (confidence 50-60, capped) but rejected at hot-set compactor:
- `pct-hermes+` (LONG): 5144 fired, most REJECTED with `hotset_compactor_not_in_top20`
- Root cause: confidence capped at 60% (`signal_gen.py` line ~1704: `min(60, max(50, (pct_val - 72) * 1.25 + 50))`)
- Other signals dominate: `mtf_zscore` at 80-87%, `ma_cross_5m` at 73%
- Solo pct-hermes can't compete in top-20 hot-set ranking
- **Workaround:** pct-hermes survives as part of a confluence combo (e.g. `ma-cross-5m-long,pct-hermes+`)

**Fix options:**
1. Raise confidence ceiling (e.g. 75%) so solo signals can compete
2. Lower `PCT_RANK_THRESH` (currently 72) so more pct-hermes fire at higher volumes
3. Add a compactor boost for standalone pct-hermes in `signal_compactor.py`

## Systematic Signal File Audit (Root Cause: Stale Data + Wrong Return Shapes)

**Symptom:** `gap-300-` (or any signal) fires for a coin where price hasn't moved (e.g., XMR SHORT at $371 while real price is ~$105). Signals reach the DB and hot-set but are phantom entries based on stale local data.

**Root Causes Found (2026-04-23):**
1. `get_ohlcv_1m()` reads from `ohlcv_1m` table which can be 7+ days stale → stale price fed to gap logic → phantom signals
2. Signal files returning `{close}` dict when caller reads `['high']`/`['low']` → KeyError silently caught, signal dropped
3. SQL subqueries selecting only `price` but outer query does `ORDER BY timestamp` → OperationalError silently caught
4. Missing `time` or `sqlite3` imports → NameError/ImportError silently caught

**Audit Checklist — Run After Any Signal File Change:**

```bash
# 1. Verify all signal files compile cleanly
python3 -m py_compile /root/.hermes/scripts/*_signals.py

# 2. Verify imports are complete (no missing time/sqlite3)
grep -n "^import\|^from" /root/.hermes/scripts/*_signals.py | sort

# 3. Check what get_ohlcv_1m() actually returns (is it stale?)
python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.hermes/data/candles.db')
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute(\"SELECT symbol, timeframe, close, timestamp FROM ohlcv_1m WHERE symbol='XMR' ORDER BY timestamp DESC LIMIT 3\")
for row in cur.fetchall(): print(row)
"

# 4. Verify signal output shape (should return open/high/low/close not just close)
# Run signal directly and print keys:
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from gap300_signals import *
result = compute_gap300_signal('XMR', 'short', '5m')
print('keys:', result[0].keys() if result else 'EMPTY')
"
```

**Common Signal File Bug Patterns:**

| Bug | Symptom | Fix |
|-----|---------|-----|
| Return `{close}` only | Caller reads `['high']`/`['low']` → KeyError → signal silently dropped | Return `{open, high, low, close}` |
| Missing `time` import | `NameError: name 'time' is not defined` → signal silently fails | Add `import time` at top |
| Missing `sqlite3` import | `NameError: name 'sqlite3' is not defined` | Add `import sqlite3` |
| SQL subquery selects wrong cols | Outer `ORDER BY timestamp` but subquery only selects `price` → OperationalError | Subquery must select all columns the outer query needs |
| `get_ohlcv_1m()` used in gap logic | Reads stale `ohlcv_1m` table (7+ days old for low-volume coins) → phantom signals | Use `candles_1m` table or `price_history` instead |

## How to Trace a Phantom Signal to its Source

The most important rule: **check the actual signals DB first, not the source code.** A signal appearing to be from one type (e.g., `gap-300-`) may actually be from another (OpenClaw's `oc_signal_importer`).

### Step 1 — Query the signals DB directly

```sql
-- Find signals of a specific type, look at source + price
SELECT token, direction, source, price, created_at
FROM signals
WHERE source LIKE '%gap-300%'
ORDER BY created_at DESC LIMIT 20;
```

**Why:** The `source` column shows the actual emitter. A source like `gap-300-,oc-zscore-v9-` means OpenClaw's importer merged a gap-300 with an oc-zscore. A source of just `gap-300-` means Hermes' own gap300_signals.py emitted it.

**Key diagnostic:** If `price` in the DB differs wildly from the current market price, the signal came from stale data (either OpenClaw or Hermes reading wrong source).

### Step 2 — Cross-reference signal price with live price

```python
# Signal price from DB vs current price_history
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute("SELECT price FROM latest_prices WHERE token='ATOM'")
live = cur.fetchone()
print(f"Live price: {live[0] if live else 'NOT IN latest_prices'}")

cur.execute("SELECT timestamp, price FROM price_history WHERE token='ATOM' ORDER BY timestamp DESC LIMIT 1")
ph = cur.fetchone()
from datetime import datetime
print(f"price_history last: {datetime.fromtimestamp(ph[0]) if ph else 'NONE'} = {ph[1] if ph else 'N/A'}")
```

**If signal price ≠ live price:** The signal used a different price source than `price_history`. Likely OpenClaw's `oc_signal_importer` (which uses its own price feed) OR a signal reading from stale `ohlcv_1m`.

### Step 3 — Check for OpenClaw prefix (oc-)

```sql
SELECT DISTINCT source FROM signals WHERE source LIKE '%,oc-%' OR source LIKE 'oc-%';
```

**`oc-` prefix = from OpenClaw signal importer**, not Hermes' own gap300_signals.py. OpenClaw's gap-300 may use different data sources and timing than Hermes' own signal scripts.

### Step 4 — Trace OpenClaw signal importer

```bash
grep -rn "gap-300\|detect_gap\|gap_cross" /root/.hermes/scripts/oc_signal_importer.py
```

OpenClaw's importer may have its own gap computation that reads from a different (potentially stale) data source.

### Common Phantom Signal Patterns

| Pattern | Likely Source | Fix |
|---------|--------------|-----|
| `gap-300-,oc-zscore-v9-` SHORT but price should be LONG | OpenClaw's `oc_signal_importer` reading stale data | Block `gap-300+`, `gap-300-` in SIGNAL_SOURCE_BLACKLIST until OC fixes their data |
| Signal price in DB ≠ current market price | External signal importer with stale feed | Check source column; block if misbehaving |
| `price_history` has 30-min timestamp gaps | Pipeline data gaps for low-volume tokens | Add bar-to-bar gap detection in `_get_1m_prices` |

```python
# In the signal file, add debug print:
print(f"DEBUG get_candles: p_rows={len(p_rows)}, c_rows={len(c_rows)}")

# Check if data is stale:
python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.hermes/data/candles.db')
conn = sqlite3.connect(db)
cur = conn.cursor()
# Check price_history staleness
cur.execute(\"SELECT symbol, price, timestamp FROM price_history WHERE symbol='XMR' ORDER BY timestamp DESC LIMIT 1\")
print('price_history:', cur.fetchone())
# Check ohlcv_1m staleness  
cur.execute(\"SELECT symbol, close, timestamp FROM ohlcv_1m WHERE symbol='XMR' ORDER BY timestamp DESC LIMIT 1\")
print('ohlcv_1m:', cur.fetchone())
"
```

**Files Audited (2026-04-23):**
- `gap300_signals.py` — OK (reads from candles.db 1m)
- `ma_cross_signals.py` — OK
- `ma_fast_signals.py` — Missing `time` + `sqlite3` imports (fixed)
- `rs_signals.py` — Returns `{close}` only, expected `{high}`/`{low}` (fixed)
- `ma300_candle_confirm_signals.py` — Returns `{close}` only, expected `{high}`/`{low}` (fixed)
- `volume_1m_signals.py` — Volume always 0 (price_history has no volume) → merged with candles_1m (fixed)
- `macd_1m_signals.py` — Missing `time` import + SQL subquery selecting wrong cols (fixed)
- `macd_rules.py` — `PRICE_DB` typo → NameError (fixed)
- `pattern_scanner.py` — OK
- `volume_hl_signals.py` — OK

## Relevant Files
- `/root/.hermes/scripts/signal_gen.py` — main signal generation, confidence formula at ~line 1704
- `/root/.hermes/scripts/hyperliquid_exchange.py` — HL API wrapper, is_delisted, _get_meta
- `/root/.hermes/scripts/run_pipeline.py` — pipeline orchestrator, logs errors
- `/root/.hermes/logs/pipeline.log` — live pipeline output
- `/root/.hermes/scripts/signal_compactor.py` — hot-set compactor, top-20 filtering at ~line 569
- `/root/.hermes/data/signals_hermes_runtime.db` — signal DB (query directly for investigation)
