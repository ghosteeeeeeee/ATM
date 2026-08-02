# Plan: Binance Futures Volume Alert Script

## Goal
Build a script that monitors all Binance USDT-margined futures symbols and alerts (pings) when a coin's current volume exceeds **5x (500%)** its 10-period volume moving average.

---

## Current Context / Assumptions
- Target: All Binance USDT-margined futures (`fapi` endpoint)
- Timeframe: 1-minute candles (most responsive for alerts)
- Volume metric: Quote asset volume (e.g., USDT traded)
- Alert threshold: Current volume >= 5.0 × 10-period SMA(volume)
- Ping mechanism: **TBD** — options include Telegram bot, Discord webhook, email, or a simple log + pushover. Need to ask the friend.
- Run mode: Continuous loop (every ~10-30 seconds) or one-shot scan

---

## Proposed Approach

### Architecture
1. **Fetch all futures symbols** via `fapi/v1/exchangeInfo` — filter for `quoteAsset==USDT` and `contractType==PERPETUAL`
2. **For each symbol**, fetch the last N 1-minute candles via `fapi/klines` (N=10 for the MA, plus 1 current)
3. **Calculate 10-period SMA** of volume over the last 10 closed candles
4. **Compare** the current (most recent) candle's volume against the SMA × 5.0
5. **Ping** if threshold exceeded — log it, send notification

### Data Source
- Binance Futures REST API: `https://fapi.binance.com`
- No authentication needed for public endpoints
- Rate limit: 1200 requests/minute for klines — batch or throttle if needed

### Script Language
- Python 3 (recommended for reliability and easy async/http libs)

---

## Step-by-Step Plan

### Step 1: Scaffold
- Create `volume_alert.py` in `~/.hermes/scripts/` or a dedicated folder
- Add requirements: `requests`, `python-dotenv` (if bot token needed)

### Step 2: Symbol Discovery
- Call `GET /fapi/v1/exchangeInfo`
- Filter symbols: `quoteAsset=USDT`, `status=TRADING`, `contractType=PERPETUAL`
- Cache the symbol list (refresh every hour)

### Step 3: Volume Fetch & MA Calculation
- For each symbol, call `GET /fapi/v1/klines?symbol=X&interval=1m&limit=11`
- Extract volumes from the last 11 candles (10 closed + 1 current/unclosed)
- Compute SMA of the first 10 closed candle volumes
- Current volume = most recent candle's volume

### Step 4: Threshold Check & Alert
- If `current_volume >= sma_volume * 5.0` → trigger alert
- Alert should include: symbol, current volume, SMA, ratio, timestamp

### Step 5: Notification (Ping)
- **Option A (Telegram):** Use Bot API — needs bot token + chat ID
- **Option B (Discord webhook):** Simple POST to webhook URL
- **Option C (Pushover):** Simple API push
- **Option D (Log only):** Print to stdout — friend can pipe to their own notifier
- **Recommended default:** Telegram bot — most reliable for real-time alerts

### Step 6: Run Loop
- Sleep 10–30 seconds between scans
- Graceful shutdown on SIGINT
- Log every cycle: scanned N symbols, found M alerts

---

## Files Likely to Change / Create

| File | Purpose |
|------|---------|
| `~/.hermes/scripts/volume_alert.py` | Main script |
| `~/.hermes/scripts/requirements.txt` | Dependencies |
| `~/.env` (optional) | Telegram bot token / chat ID / Discord webhook |

---

## Verification Steps
1. Run script in dry-log mode (print-only, no ping) against a few known active symbols
2. Verify volume numbers match Binance UI for a known coin
3. Test alert fires correctly when artificially lowering threshold to 1.0× (should fire on every coin)
4. Confirm ping delivered to Telegram/Discord when threshold genuinely exceeded

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|-----------|
| Binance rate limits (1200/min) | Batch symbols, cache exchangeInfo, limit scan frequency |
| Some symbols have 0/low volume | Filter out symbols with avg volume < threshold (e.g., < $10k/day) |
| Script crashes on bad symbol data | Add try/except per symbol, skip failures gracefully |
| Alert spam if many coins pump simultaneously | Cooldown per symbol (don't re-alert same coin within 5 min) |
| API change | Pin to specific API version path `/fapi/v1/` |

---

## Decisions (Friend Confirmed)

| Question | Answer |
|----------|--------|
| Ping method | Print to terminal |
| Run frequency | Every **60 seconds** |
| Startup mode | **Continuous daemon** |
| Notification detail | Full detail: symbol, current vol, SMA vol, ratio, price, % change, timestamp |

## Next Action
Write `volume_alert.py` — see plan above. Then ask friend to test run.

---

## Output Deliverable
- `volume_alert.py` — self-contained Python script
- `requirements.txt` — `requests`, `python-dotenv`
- Optional: `.env` template for tokens
