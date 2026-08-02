# Plan: Volume Alert → Hyperliquid Signal

## Goal
Fire a LONG or SHORT signal on Hyperliquid whenever a Binance futures coin's 1m volume exceeds Nx its 10-period SMA, then feed that into Hermes's existing signal pipeline → guardian → HL execution.

---

## How the Existing Pipeline Works

```
Binance Kline API
      ↓
signal_gen.py  (or standalone script)
      ↓
add_signal()   →  signals DB  (signals_hermes_runtime.db)
      ↓
signal_compactor.py  →  hotset.json
      ↓
guardian.py  reads hotset.json  →  executes trades on Hyperliquid
```

---

## Two Integration Options

### Option A: Standalone script (recommended for this use case)

Create a new `volume_binance_signals.py` that:
1. Scans all Binance USDT-perp symbols every 60s
2. Calls `add_signal(token, direction, 'volume_binance', source='volume_binance', confidence=N, price=cur_price)`
3. Runs **completely independently** from signal_gen.py (no conflict, no import issues)

**Pros:** Isolated, no risk of breaking signal_gen.py, easy to tune/kill independently
**Cons:** Another cron/script to manage

### Option B: Add to signal_gen.py

Add volume check to existing per-token loop in signal_gen.py alongside RSI/MACD/zscore.

**Pros:** Single script to manage
**Cons:** signal_gen.py is complex — adding Binance API calls risks breaking the main pipeline

**Recommendation: Option A**

---

## Step-by-Step: Option A

### 1. New file: `volume_binance_signals.py`

Key differences from the friend script:
- Use `add_signal()` from `signal_schema.py` instead of `print()`
- Determine direction from price change: `pct_change > 0` → LONG, `< 0` → SHORT
- Map Binance symbol to HL symbol (e.g. `BTCUSDT` → `BTC`, `1000SHIBUSDT` → `1000SHIB`)
- Confidence = `min(100, ratio * 10)` — e.g. 6x vol → 60% confidence, 10x → 100% (capped)
- Min volume threshold to avoid noise on tiny caps

### 2. Symbol mapping

HL uses full Binance-style tickers (e.g. `BTC`, `ETH`, `1000SHIB`). Need to strip `USDT` from Binance symbol. Also note HL uses `1000SHIB` not `1000SHIBUSDT`.

### 3. Run it on Tokyo server

Since friend is geo-blocked from Binance, the script must run on Tokyo (already has non-blocked IP). Can run as:
- `python3 volume_binance_signals.py &` (background, nohup)
- Or as a systemd service

### 4. Key config params at top

```python
BINANCE_BASE_URL = "https://fapi.binance.com"
SCAN_SECS        = 60
VOL_MULT         = 5.0        # fire threshold
MIN_VOL          = 100_000    # minimum current vol (USD)
MIN_CONFIDENCE   = 50         # HL requires ≥50
HL_EXCHANGE      = "hyperliquid"
TIMEFRAME        = "1m"
```

---

## Files to Create/Change

| File | Action |
|------|--------|
| `/root/.hermes/scripts/volume_binance_signals.py` | CREATE — new standalone signal emitter |
| `/root/.hermes/brain/trading.md` | UPDATE — document the new signal source |

---

## Validation

1. Run script on Tokyo: `python3 volume_binance_signals.py`
2. Watch `signals_hermes_runtime.db` for new rows with `source='volume_binance'`
3. Check hotset.json after compaction cycle
4. Confirm guardian picks it up and attempts HL trade
5. Paper trade first to verify direction/sizing

---

## Risks

- Binance API geo-block: must run on Tokyo server (not friend's machine)
- Signal spam if many coins pump simultaneously — but that's what the cooldown/guardian dedup handles
- Symbol mapping edge cases: some Binance symbols don't map 1:1 to HL (e.g. `BTCUSDT` → `BTC` is fine, but `1000SHIBUSDT` → `1000SHIB` works)
- Volume in USDT on Binance vs USD on HL — need to ensure price * quantity is comparable

---

## Open Question

Should this run as a **systemd service** (auto-restart on crash) or as a **cron-triggered script** (like pump_hunter)?
