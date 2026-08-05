---
name: verify-prices-extras
description: Comprehensive candle and price data integrity audit for Hermes — absorbed into hermes-pipeline-debug as a reference. Quick guide retained here.
---

# Verify Prices — Absorbed into hermes-pipeline-debug

Detailed audit procedures are in `hermes-pipeline-debug` → `references/pipeline-investigation.md`.
Quick reference below.

## When to Run
Run whenever signals appear wrong, prices seem stale, or as a routine health check.

## What to Check

1. **Candle chain continuity** — no missing windows for any active token across 1m/5m/15m/1h/4h
2. **OHLC validity** — high ≥ low, high ≥ open/close, low ≤ open/close, prices > 0
3. **is_closed correctness** — latest candle should be `is_closed=0` (developing) or very recent
4. **Stale candle detection** — tokens with `is_closed=1` but age > 3x tf
5. **price_history freshness** — allMids polling active tokens, no gaps in last 5 min

## ⚠ CRITICAL: is_closed Interpretation
- `is_closed=0` on higher TFs (1h/4h) is **NORMAL**, not stale. It means the candle is still developing and will close at the natural interval boundary. A 1h candle with `is_closed=0` at 01:05 closes at 02:00.
- Only `is_closed=1` with age > 3× interval is **actually stale**.

## Data Source Freshness Map

| Source | Location | Freshness | Use For |
|--------|----------|-----------|---------|
| Live prices | `signals_hermes.db` → `price_history` | **< 1 min** | Signal generation ONLY |
| Live speeds | `signals_hermes_runtime.db` → `token_speeds` | **< 5 min** | Wave/speed calculations |
| 1m candles | `candles.db` → `candles_1m` | ~3h (2 tokens/run) | gap300_5m warmup only |
| 5m/15m/1h/4h | `candles.db` → `candles_*m` | **< 10 min** | Indicator computation |
| `hl_cache.json` | `/var/www/hermes/data/` | **< 30s** | Has schema bugs — see below |
| `speed_history.json` | `/root/.hermes/data/` | **STALE since ~Apr 29** | DO NOT USE |
| `price_history.db` | `/root/.hermes/data/` | **0 bytes — EMPTY** | DO NOT USE |

## Known Root Causes

1. **is_closed=0 on higher TFs = FALSE ALARM.** Normal — candle is still developing.
2. **`_aggregate_1m.py` hardcodes `volume=0`** — use Binance klines instead.
3. **`price_collector.py` Binance seed rate-limited** — only ~2 tokens per run cycling through 230.
4. **5m aggregator timer drift** — aggregator takes ~20s to run, completing 14-29 min behind real time.
5. **`gap300_5m_signals.py` reading wrong 1m source** — should read from `price_history` (signals_hermes.db), not `candles_1m` (candles.db).
6. **`hl_cache.json` THREE schema traps:**
   - Reader uses `mids` but live API stores `allMids`
   - `cache_age` key doesn't exist in live file
   - Stale token mappings from delisted coins
7. **`signal_gen` timeout at 180s** — `scan_rs_signals` was O(N²); fixed with NumPy vectorization.

## Schema Reference (Verified 2026-04-30)

| Table | `is_closed`? | Notes |
|-------|-------------|-------|
| `candles_1m` | **YES** | Developing candles correctly tracked |
| `candles_5m` | **YES** | Same |
| `candles_15m` | YES | |
| `candles_1h` | YES | |
| `candles_4h` | YES | |

## Key Commands

```bash
# Check candles DB health
python3 << 'EOF'
import sqlite3
db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
for tf in ['candles_1m','candles_5m','candles_15m','candles_1h','candles_4h']:
    cur.execute(f"SELECT COUNT(DISTINCT token), COUNT(*) FROM {tf}")
    ntok, nrows = cur.fetchone()
    print(f"{tf}: {ntok} tokens, {nrows} rows")
EOF

# Check OHLC violations
python3 << 'EOF'
import sqlite3
db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
for tf in ['candles_1m','candles_5m','candles_15m','candles_1h','candles_4h']:
    cur.execute(f"SELECT token, ts FROM {tf} WHERE high < low OR high < open OR high < close OR low > open OR low > close OR open <= 0 OR close <= 0 LIMIT 5")
    rows = cur.fetchall()
    print(f"{tf} violations: {len(rows)}")
EOF
```

## Files
- Candles DB: `/root/.hermes/data/candles.db`
- Price history DB: `/root/.hermes/data/signals_hermes.db`
- Price collector: `/root/.hermes/scripts/price_collector.py`
- Speed source (LIVE): `/root/.hermes/data/signals_hermes_runtime.db` → `token_speeds`
- Speed source (STALE): `/root/.hermes/data/speed_history.json` — abandoned, do not use