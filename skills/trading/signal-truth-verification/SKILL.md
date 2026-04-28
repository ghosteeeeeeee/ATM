---
name: signal-truth-verification
description: Verify each signal component empirically — find the script, run the math against live data, check freshness. Used when T asks to audit a trade signal.
trigger: When T says "verify", "check if signal is valid", "audit signal" or asks to investigate why a trade fired.
---

# Signal Truth Verification — Verify Each Signal Component Empirically

## When to Use
When T asks to "verify" or "audit" a signal that triggered a trade — find the actual script, run the math, check the data. Don't assume, don't speculate. Verify each component independently.

## The Method (4-Step)

### Step 1 — Find the signal script
```bash
# Signal type → script mapping:
grep -r "signal_type.*zscore_momentum" scripts/signal_gen.py
grep -r "oc_mtf_macd\|oc_mtf_macd" scripts/oc_signal_importer.py
grep -r "import_pending_signals" scripts/oc_signal_importer.py

# Common signal script locations:
/root/.hermes/scripts/zscore_momentum.py
/root/.hermes/scripts/oc_signal_importer.py
/root/.hermes/scripts/macd_rules.py
/root/.hermes/scripts/signal_gen.py (search for _run_* functions)
```

### Step 2 — Read the actual logic
- Read the full signal computation function (not just the docstring)
- Key things to find: lookback window, threshold, std type (sample vs population), data source (candles.db vs price_history vs external)
- Check freshness guards: does the script skip stale data?

### Step 3 — Verify math against live data
```python
# Compute MACD from candles.db
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
for tf, table in [('15m','candles_15m'),('1h','candles_1h'),('4h','candles_4h')]:
    cur.execute(f'SELECT close FROM {table} WHERE token=\"TOKEN\" ORDER BY ts DESC LIMIT 100')
    closes = list(reversed([r[0] for r in cur.fetchall()]))
    def ema(data, period):
        k = 2/(period+1); e = data[0]
        for p in data[1:]: e = p*k + e*(1-k)
        return e
    macd_line = ema(closes, 12) - ema(closes, 26)
    # ... compute signal line + histogram
    print(f'{tf}: hist={histogram:.6f}, bullish={histogram>0}')
"

# Compute z-score from price_history
python3 -c "
import sqlite3, math, statistics
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute('SELECT price FROM price_history WHERE token=\"TOKEN\" ORDER BY timestamp DESC LIMIT 60')
closes = list(reversed([r[0] for r in cur.fetchall()]))
mean = statistics.mean(closes)
std = statistics.stdev(closes)  # sample stdev
z = (closes[-1] - mean) / std
print(f'n={len(closes)}, mean={mean}, std={std}, z={z}')
"
```

### Step 4 — Verify compactor confluence
Check signal_compactor.py for how the source string is built:
```python
# GROUP BY merges sources:
GROUP_CONCAT(DISTINCT source) AS merged_source
# Confluence gate: 2+ sources required
source_parts = [p.strip() for p in source.split(',') if p.strip()]
if len(source_parts) < 2:  # skip single-source
# Directional conflict check:
long_srcs = [p for p in source_parts if p.endswith('+')]
short_srcs = [p for p in source_parts if p.endswith('-')]
```

## Key Traps

**1. Don't assume mean-reversion vs momentum**
zscore_momentum says "unlike mean-reversion, we treat high |z| as momentum confirmation." Read the docstring AND the code — they're different strategies.

**2. oc-zscore-v9 is external — can't fully verify**
OC pending signals come from OpenClaw workspace. We can check the JSON file and confidence/value but not their internal calculation. Treat as partially verifiable.

**3. OC pending entry price is stale — but local price override was added 2026-04-25**
oc_signal_importer.py line 429: `if oc_source == 'zscore-v9' and token: fresh = _get_fresh_price(token); price = fresh`
The stale price issue was fixed. But the z-score itself is still OC's.

**4. val=2.0 means AT threshold, not exceeding it**
If oc-zscore-v9 has val=2.0 and threshold=2.0, it's barely a signal. Check the actual value in the OC pending JSON.

**5. MACD can stay bearish in ranging markets**
MACD(12,26,9) lags — in a choppy range, the fast EMA stays below slow EMA even as price drifts up. Triple-TF MACD bearish doesn't mean price will drop — it means recent prices are below the rolling average.

**6. candles_1m and candles_5m may be stale while higher TFs are fresh**
Check each TF independently with `SELECT MAX(ts) FROM {table} WHERE token='TOKEN'`.

## Signals DB Schema (signals_hermes_runtime.db)
```sql
id, token, direction, signal_type, source, confidence, value, price,
executed, decision, created_at, compact_rounds, hot_cycle_count, ...
```
Query: `SELECT id, signal_type, source, direction, confidence, value, price, executed, created_at FROM signals WHERE token='ATOM' ORDER BY id DESC LIMIT 20`

## OC Pending Signals File
`/var/www/hermes/data/oc_pending_signals.json`
Format: `{"pending_signals": [{"token":"ATOM","side":"short","source":"zscore-v9","confidence":81.0,"entry":1.7177}]}`

## OC Indicators File
`/var/www/hermes/data/oc_indicators.json`
Format: `{ATOM: {"price":1.67,"macd_1h":{...},"macd_4h":{...},"mt_tf_bullish":1,"mt_tf_bearish":2,...}}`

## Example: ATOM SHORT Signal Audit (April 2026)
- oc-mtf-macd-: VERIFIED — 3/3 TFs bearish, fresh candles
- oc-zscore-v9-: PARTIAL — external, val=2.0=at threshold, confidence=81.0 (minimum)
- zscore-momentum-: VERIFIED — z=-2.047 < -2.0 = downward momentum, sample stdev, momentum NOT mean-reversion

Result: All three signals are doing what they say. The compactor's 99% confidence is real confluence from 3 independent generators.
